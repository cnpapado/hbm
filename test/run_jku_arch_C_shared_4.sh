#!/bin/bash
#SBATCH -A p33086
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 48:00:00
#SBATCH --mem=8G
#SBATCH --job-name=jku-archC4
#SBATCH --output=/dev/null

# HBM Upper-First (ARCH_C), sharing ratio 4, on the JKU suite.
ARCH_NAME="ARCH_C_shared_4"
BENCH_DIR="../quantum-compiler-benchmark-circuits/jku_suite"

mkdir -p results_jku outs_jku

FILES=($BENCH_DIR/*.qasm)

if [ ! -e "${FILES[0]}" ]; then
    echo "ERROR: No .qasm files found in $BENCH_DIR"
    exit 1
fi

if [ "$SLURM_ARRAY_TASK_ID" -ge "${#FILES[@]}" ]; then
    echo "ERROR: task $SLURM_ARRAY_TASK_ID out of range for ${#FILES[@]} benchmarks in $BENCH_DIR" >&2
    exit 1
fi

current_file=${FILES[$SLURM_ARRAY_TASK_ID]}
filename=$(basename "$current_file")
base="${filename%.*}"

echo "Task ID $SLURM_ARRAY_TASK_ID | Arch: $ARCH_NAME | File: $base"

export HBM_CONFIG="shared_4-route_upper"

output_file="outs_jku/${base}_${ARCH_NAME}.out"

wisq "$current_file" -op "$output_file" --mode scmr -tmr 172800

TIME_RESULT=$(python3 print_timesteps.py "$output_file" --summary)

echo "$base | $ARCH_NAME | $TIME_RESULT" > "results_jku/${base}.${ARCH_NAME}.res"

echo "Completed $base on $ARCH_NAME"
