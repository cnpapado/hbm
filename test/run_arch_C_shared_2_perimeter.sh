#!/bin/bash
#SBATCH -A p33086
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 24:00:00
#SBATCH --mem=8G
#SBATCH --job-name=wisq_arch_C_shared_2_perimeter
#SBATCH --output=logs_%x_%A_%a.out

# --- Environment -----------------------------------------------------------
# Slurm does not inherit an activated venv from the submitting shell, so the
# job must set it up itself or `wisq` will not be on PATH.
module load python/3.12.10
source ~/hbm/.venv/bin/activate
cd ~/hbm/test || exit 1
command -v wisq >/dev/null || { echo "ERROR: wisq not on PATH - check module load / venv activate" >&2; exit 1; }

# --- CONFIGURATION ---
# Change this variable for each of your 5 scripts
# Options: no_hbm, shared_none, shared_2, shared_4, etc.
ARCH_NAME="ARCH_C_shared_2_perimeter"

# Directory containing your universal benchmarks
# BENCH_DIR="benchmarks_universal_cx_2"
BENCH_DIR="qft"
# mkdir -p logs_new
mkdir -p results_temp_qft

# 1. Identify all benchmarks
FILES=($BENCH_DIR/*.qasm)

if [ ! -e "${FILES[0]}" ]; then
    echo "ERROR: No .qasm files found in $BENCH_DIR"
    exit 1
fi

# 2. Assign file based on the Array Task ID
if [ "$SLURM_ARRAY_TASK_ID" -ge "${#FILES[@]}" ]; then
    echo "ERROR: task $SLURM_ARRAY_TASK_ID out of range for ${#FILES[@]} benchmarks in $BENCH_DIR" >&2
    exit 1
fi

current_file=${FILES[$SLURM_ARRAY_TASK_ID]}
filename=$(basename "$current_file")
base="${filename%.*}"

echo "Task ID $SLURM_ARRAY_TASK_ID | Arch: $ARCH_NAME | File: $base"

# 3. Execution Logic
# Set the specific HBM_CONFIG required by your WISQ tool
export HBM_CONFIG="shared_2-route_upper-anchilla_perimeter"

# Output naming convention: bench_n16_p10_no_hbm.out
output_file="${base}_${ARCH_NAME}.out"

# Run WISQ
wisq "$current_file" -op "$output_file" --mode scmr -tmr 86400

# Extract timesteps (Ideal Timesteps / Actual Timesteps)
TIME_RESULT=$(python3 print_timesteps.py "$output_file" --summary)
[ -z "$TIME_RESULT" ] && TIME_RESULT="ERROR"

# 4. Systematic Result Saving
# Format: [Benchmark] | [Arch] | [Timesteps]
# Saved to: results_temp_qft/bench_n16_p10.no_hbm.res
echo "$base | $ARCH_NAME | $TIME_RESULT" > "results_temp_qft/${base}.${ARCH_NAME}.res"

echo "Completed $base on $ARCH_NAME"
