#!/bin/bash
#SBATCH --job-name=count_steps         # Job name
#SBATCH --output=count_steps_%j.log    # Standard output and error log
#SBATCH --time=01:00:00                # Maximum runtime (hh:mm:ss)
#SBATCH --cpus-per-task=4              # Number of CPUs
#SBATCH --mem=8G                        # Memory
#SBATCH --partition=standard           # Change if your cluster has a different partition

# Load modules if needed (optional, depending on your cluster)
# module load python/3.11

# Activate your virtual environment
source ~/hbm/.venv/bin/activate

# Navigate to the scripts directory
cd ~/hbm/scripts

# Run your Python script
python count_steps_csv.py
