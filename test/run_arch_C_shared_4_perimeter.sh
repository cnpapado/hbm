#!/bin/bash
#SBATCH -A p33086
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 24:00:00
#SBATCH --mem=8G
#SBATCH --job-name=wisq_arch_C_shared_4_perimeter
#SBATCH --output=/dev/null

# --- CONFIGURATION ---
# Change this variable for each of your 5 scripts
# Options: no_hbm, shared_none, shared_2, shared_4, etc.
ARCH_NAME="ARCH_C_shared_4_perimeter"

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
current_file=${FILES[$SLURM_ARRAY_TASK_ID]}
filename=$(basename "$current_file")
base="${filename%.*}"

echo "Task ID $SLURM_ARRAY_TASK_ID | Arch: $ARCH_NAME | File: $base"

# 3. Execution Logic
# Set the specific HBM_CONFIG required by your WISQ tool
export HBM_CONFIG="shared_4-route_upper-anchilla_perimeter"

# Output naming convention: bench_n16_p10_no_hbm.out
output_file="${base}_${ARCH_NAME}.out"

# Run WISQ
wisq "$current_file" -op "$output_file" --mode scmr -tmr 86400

# Extract timesteps (Ideal Timesteps / Actual Timesteps)
TIME_RESULT=$(python3 print_timesteps.py "$output_file" --summary)

# 4. Systematic Result Saving
# Format: [Benchmark] | [Arch] | [Timesteps]
# Saved to: results_temp/bench_n16_p10.no_hbm.res
echo "$base | $ARCH_NAME | $TIME_RESULT" > "results_temp_qft/${base}.${ARCH_NAME}.res"

echo "Completed $base on $ARCH_NAME"
