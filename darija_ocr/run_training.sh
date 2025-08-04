#!/bin/bash
#SBATCH --job-name=darija_ocr_training
#SBATCH --output=slurm_output_%j.out
#SBATCH --error=slurm_output_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32GB
#SBATCH --time=24:00:00
#SBATCH --gres=gpu:1

# Load necessary modules (adjust as per your cluster's setup)
# module load cuda/11.7
# module load anaconda/2023.03

# Activate your Python environment (if any)
# source activate your_env_name

# Navigate to your project directory
# cd /path/to/your/darija_ocr/project

# Execute your Python training script
python train.py