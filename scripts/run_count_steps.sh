#!/bin/bash
#SBATCH --account=p33086
#SBATCH --job-name=count_steps         # Job name
#SBATCH --output=count_steps_%j.log    # Standard output and error log
#SBATCH --time=12:00:00                # Maximum runtime (hh:mm:ss)
#SBATCH --cpus-per-task=1              # Number of CPUs
#SBATCH --mem=4G                      # Memory
#SBATCH --partition=normal           

module load python/3.12.10
source ~/hbm/.venv/bin/activate

cd ~/hbm/scripts
python count_steps_csv.py
