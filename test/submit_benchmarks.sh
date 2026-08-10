#!/bin/bash
#SBATCH --account=p33086          # Your project account
#SBATCH --cpus-per-task=64        # Reserve 64 cores for your parallel runs
#SBATCH --mem=32G                 # Reserve 16GB of RAM (adjust if needed)
#SBATCH --time=12:00:00           # Max time (HH:MM:SS)
#SBATCH --job-name=qsim_bench     # Name of the job in the queue
#SBATCH --output=slurm_output.log # Where all terminal output goes
#SBATCH --partition=normal

# Load your environment
module load python/3.12.10
source ~/hbm/.venv/bin/activate
cd ~/hbm/test

# Run your script (Ensure run.sh is set to use parallel)
./run.sh
