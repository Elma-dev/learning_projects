from tqdm import tqdm
import torch
import wandb
import os
from unsloth import FastVisionModel # FastLanguageModel for LLMs
from unsloth import is_bf16_supported
from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig
from transformers import EarlyStoppingCallback
from datasets import load_dataset, Dataset, IterableDataset
from dotenv import load_dotenv

load_dotenv()

prompt=""
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

def load_process_datasets():
    train_dataset = load_dataset("atlasia/atlasOCR-data", split="train")
    val_dataset = load_dataset("atlasia/atlasOCR-data", split="validation")
    
    converted_train_dataset=[]
    for sample in tqdm(train_dataset):
        converted_train_dataset.append(convert_to_conversation(sample))
        converted_val_dataset=[]
    for sample in tqdm(val_dataset):
        converted_val_dataset.append(convert_to_conversation(sample))
    return converted_train_dataset,converted_val_dataset


if __name__=="__main__":
    print("[INFO] Load Dataset & Preprocessing ...")
    converted_train_dataset,converted_val_dataset = load_process_datasets()

    print("[INFO] Load Model & Tokenizer ...")
    model, tokenizer = FastVisionModel.from_pretrained(
        "unsloth/Qwen2.5-VL-3B-Instruct",
        device_map="auto",
        load_in_4bit = True, # Use 4bit to reduce memory use. False for 16bit LoRA.
        use_gradient_checkpointing = "unsloth", # True or "unsloth" for long context
    )

    print("[INFO] Get Peft Model ...")
    model = FastVisionModel.get_peft_model(
        model,
        finetune_vision_layers     = True, # False if not finetuning vision layers
        finetune_language_layers   = True, # False if not finetuning language layers
        finetune_attention_modules = True, # False if not finetuning attention layers
        finetune_mlp_modules       = True, # False if not finetuning MLP layers
        r = 16,           # The larger, the higher the accuracy, but might overfit
        lora_alpha = 16,  # Recommended alpha == r at least
        lora_dropout = 0.05,
        bias = "none",
        random_state = 7,
        use_rslora = False,  # We support rank stabilized LoRA
        loftq_config = None, # And LoftQ
        # target_modules = "all-linear", # Optional now! Can specify a list if needed
    )
    
    print("[INFO] Collator ...")
    collator = UnslothVisionDataCollator(model, tokenizer)
    collator.truncation = False

    print("[INFO] Enable Training Mode ...")
    FastVisionModel.for_training(model)

    print("[INFO] Set Training Args ...")
    args = SFTConfig(
        per_device_train_batch_size = 4,
        per_device_eval_batch_size = 4,
        gradient_accumulation_steps = 1,
        warmup_steps = 1,
        num_train_epochs = 1,
        learning_rate = 2e-5,
        fp16 = not is_bf16_supported(),
        bf16 = is_bf16_supported(),
        # fp16 = False,
        # bf16 = False,
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear", # "linear"
        seed = 7,
        output_dir = "outputs",
        overwrite_output_dir = True,
        save_total_limit = 1,
        report_to = "wandb",     # For Weights and Biases
        push_to_hub=True,
        #hub_private_repo=True,
        # max_grad_norm = 1.0,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        eval_strategy="steps",
        save_strategy="steps",
        eval_steps = 0.1,
        save_steps = 0.1,
        # You MUST put the below items for vision finetuning:
        remove_unused_columns = False,
        dataset_text_field = "",
        dataset_kwargs = {"skip_prepare_dataset": True},
        dataset_num_proc = 4,  
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
    wandb.init(
        project="ocr-v2"
    )

    print("[INFO] Begin Training ...")
    trainer_stats = trainer.train()

    print("[INFO] Push Model To HUB ...")

    model.push_to_hub("abdeljalilELmajjodi/darija_ocr_pleasant-silence-9", private = True)
    tokenizer.push_to_hub("abdeljalilELmajjodi/darija_ocr_pleasant-silence-9", private = True)

    print("[DONE] ✅")