from tqdm import tqdm
import torch
import wandb
from unsloth import FastVisionModel # FastLanguageModel for LLMs
from unsloth import is_bf16_supported
from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset
from dotenv import load_dotenv
import argparse
import yaml

load_dotenv()

prompt = ("Below is the image of one page of a document written in arabic."
        "Just return the plain text representation of this document as if you were reading it naturally. Do not hallucinate.")
def convert_to_conversation(sample):
    global prompt
    conversation = [
        { "role": "user",
          "content" : [
            {"type" : "text",  "text"  : prompt},
            {"type" : "image", "image" : sample["image"]} ]
        },
        { "role" : "assistant",
          "content" : [
            {"type" : "text",  "text"  : sample["text"]} ]
        },
    ]
    return { "messages" : conversation }

def load_process_datasets(dataset_name: str, train_split: str, validation_split: str):
    train_dataset = load_dataset(dataset_name, split=train_split)
    val_dataset = load_dataset(dataset_name, split=validation_split)
    
    converted_train_dataset = []
    for sample in tqdm(train_dataset):
        converted_train_dataset.append(convert_to_conversation(sample))
    converted_val_dataset = []
    for sample in tqdm(val_dataset):
        converted_val_dataset.append(convert_to_conversation(sample))
    return converted_train_dataset,converted_val_dataset


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to YAML config file")
    parser.add_argument("--use_lora", action="store_true", help="Enable LoRA finetuning (overrides config)")
    cli_args = parser.parse_args()

    # Load config
    try:
        with open(cli_args.config, "r") as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"[WARN] Config file '{cli_args.config}' not found. Using defaults.")
        config = {}

    print("[INFO] Load Dataset & Preprocessing ...")
    # Configure prompt and dataset parameters
    prompt = config.get("dataset", {}).get("prompt", prompt)
    dataset_name = config.get("dataset", {}).get("name", "atlasia/atlasOCR-data")
    train_split = config.get("dataset", {}).get("train_split", "train")
    val_split = config.get("dataset", {}).get("validation_split", "validation")
    converted_train_dataset, converted_val_dataset = load_process_datasets(dataset_name, train_split, val_split)

    print("[INFO] Load Model & Tokenizer ...")
    model_name = config.get("model", {}).get("name", "unsloth/gemma-3n-E4B-it")
    device_map = config.get("model", {}).get("device_map", "auto")
    load_in_4bit = config.get("model", {}).get("load_in_4bit", True)
    use_gradient_checkpointing = config.get("model", {}).get("use_gradient_checkpointing", "unsloth")
    model, tokenizer = FastVisionModel.from_pretrained(
        model_name,
        device_map=device_map,
        load_in_4bit=load_in_4bit,
        use_gradient_checkpointing=use_gradient_checkpointing,
    )

    use_lora = True if cli_args.use_lora else config.get("lora", {}).get("enabled", False)
    if use_lora:
        print("[INFO] Get Peft Model ...")
        lora_cfg = config.get("lora", {})
        model = FastVisionModel.get_peft_model(
            model,
            finetune_vision_layers     = lora_cfg.get("finetune_vision_layers", True),
            finetune_language_layers   = lora_cfg.get("finetune_language_layers", True),
            finetune_attention_modules = lora_cfg.get("finetune_attention_modules", True),
            finetune_mlp_modules       = lora_cfg.get("finetune_mlp_modules", True),
            r = lora_cfg.get("r", 16),
            lora_alpha = lora_cfg.get("lora_alpha", 16),
            lora_dropout = lora_cfg.get("lora_dropout", 0.05),
            bias = lora_cfg.get("bias", "none"),
            random_state = lora_cfg.get("random_state", 7),
            use_rslora = lora_cfg.get("use_rslora", False),
            loftq_config = lora_cfg.get("loftq_config", None),
            target_modules = lora_cfg.get("target_modules", "all-linear"),
            modules_to_save=lora_cfg.get("modules_to_save", ["lm_head", "embed_tokens"]),
        )
    
    print("[INFO] Collator ...")
    collator = UnslothVisionDataCollator(model, tokenizer)
    collator.truncation = False

    print("[INFO] Enable Training Mode ...")
    FastVisionModel.for_training(model)

    print("[INFO] Set Training Args ...")
    train_cfg = config.get("training", {})
    # Determine precision flags with sensible defaults when unspecified (None)
    cfg_fp16 = train_cfg.get("fp16", None)
    cfg_bf16 = train_cfg.get("bf16", None)
    fp16_val = cfg_fp16 if cfg_fp16 is not None else (not is_bf16_supported())
    bf16_val = cfg_bf16 if cfg_bf16 is not None else is_bf16_supported()

    args = SFTConfig(
        per_device_train_batch_size = train_cfg.get("per_device_train_batch_size", 16),
        per_device_eval_batch_size = train_cfg.get("per_device_eval_batch_size", 16),
        gradient_accumulation_steps = train_cfg.get("gradient_accumulation_steps", 1),
        warmup_ratio = train_cfg.get("warmup_ratio", 0.03),
        num_train_epochs = train_cfg.get("num_train_epochs", 1),
        learning_rate = train_cfg.get("learning_rate", 2e-4),
        fp16 = fp16_val,
        bf16 = bf16_val,
        logging_steps = train_cfg.get("logging_steps", 1),
        optim = train_cfg.get("optim", "adamw_torch_fused"),
        weight_decay = train_cfg.get("weight_decay", 0.01),
        lr_scheduler_type = train_cfg.get("lr_scheduler_type", "cosine"),
        seed = train_cfg.get("seed", 7),
        output_dir = train_cfg.get("output_dir", "outputs"),
        overwrite_output_dir = train_cfg.get("overwrite_output_dir", True),
        save_total_limit = train_cfg.get("save_total_limit", 1),
        report_to = train_cfg.get("report_to", "wandb"),
        push_to_hub = train_cfg.get("push_to_hub", True),
        max_grad_norm = train_cfg.get("max_grad_norm", 0.3 if use_lora else None),
        load_best_model_at_end = train_cfg.get("load_best_model_at_end", True),
        metric_for_best_model = train_cfg.get("metric_for_best_model", "eval_loss"),
        eval_strategy = train_cfg.get("eval_strategy", "steps"),
        save_strategy = train_cfg.get("save_strategy", "steps"),
        eval_steps = train_cfg.get("eval_steps", 0.1),
        save_steps = train_cfg.get("save_steps", 0.1),
        remove_unused_columns = train_cfg.get("remove_unused_columns", False),
        dataset_text_field = train_cfg.get("dataset_text_field", ""),
        dataset_kwargs = train_cfg.get("dataset_kwargs", {"skip_prepare_dataset": True}),
        dataset_num_proc = train_cfg.get("dataset_num_proc", 4),
        max_length = train_cfg.get("max_length", 2048),
    )

    print("[INFO] Init Trainer ...")
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        data_collator = collator,
        train_dataset = converted_train_dataset,
        eval_dataset= converted_val_dataset,
        # compute_metrics=compute_metrics,
        args = args,
        # callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )
    print("[INFO] GPU Status ...")
    gpu_stats = torch.cuda.get_device_properties(0)
    start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
    print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
    print(f"{start_gpu_memory} GB of memory reserved.")

    print("[INFO] Init WANDB ...")
    wandb_project = config.get("wandb", {}).get("project", "ocr-v2")
    wandb_name = config.get("wandb", {}).get("name", "experiment-gemma")
    wandb.init(project=wandb_project, name=wandb_name)
    # Log config to wandb
    try:
        wandb.config.update(config)
    except Exception:
        pass

    print("[INFO] Begin Training ...")
    trainer_stats = trainer.train()

    hub_cfg = config.get("hub", {})
    if hub_cfg.get("enabled", True):
        print("[INFO] Push Model To HUB ...")
        repo_id = hub_cfg.get("repo", "abdeljalilELmajjodi/darija_ocr_gemma_E4B_it")
        private = hub_cfg.get("private", True)
        model.push_to_hub(repo_id, private=private)
        tokenizer.push_to_hub(repo_id, private=private)

    print("[DONE] ✅")