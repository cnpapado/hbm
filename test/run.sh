#!/bin/bash

BENCH_DIR="benchmarks_universal_cx_2"
# This is the file where the data will be saved
RESULT_FILE="summary_results_new_benchs.txt"

# Clear the file if it already exists from a previous run
> "$RESULT_FILE"

echo "Starting benchmarks..."

for filepath in "$BENCH_DIR"/*.qasm; do
    filename=$(basename "$filepath")
    base="${filename%.*}"

    # Run NO_HBM
    export HBM_CONFIG="no_hbm"
    wisq "$filepath" -op "${base}_NO_HBM.out" --mode scmr -tmr 7200 > /dev/null 2>&1
    TIME_NO_HBM=$(python3 print_timesteps.py "${base}_NO_HBM.out" --summary)

    # Run ARCH_A
    export HBM_CONFIG="shared_none"
    wisq "$filepath" -op "${base}_ARCH_A.out" --mode scmr -tmr 7200 > /dev/null 2>&1
    TIME_ARCH_A=$(python3 print_timesteps.py "${base}_ARCH_A.out" --summary)

    # Append data to our text file
    echo "$base | $TIME_NO_HBM | $TIME_ARCH_A" >> "$RESULT_FILE"
    echo "Completed: $base"
done

# We will create a formatted report file for easy reading
REPORT_FILE="benchmark_report.txt"

{
    echo -e "\n================ SUMMARY TABLE ================"
    printf "%-25s | %-12s | %-12s\n" "Benchmark" "NO_HBM" "ARCH_A"
    echo "-----------------------------------------------"
    while IFS=" | " read -r name no_hbm arch_a; do
        printf "%-25s | %-12s | %-12s\n" "$name" "$no_hbm" "$arch_a"
    done < "$RESULT_FILE"
    echo "==============================================="
} | tee "$REPORT_FILE"

echo "Summary saved to $REPORT_FILE"

# #!/bin/bash

# # 1. Setup paths and files
# BENCH_DIR="benchmarks_batch"
# RESULT_FILE="final_results.txt"
# REPORT_FILE="benchmark_report_v2.txt"
# PROGRESS_LOG=$(mktemp)
# PYTHON_EXE=$(which python3)

# # 2. Get files and count
# FILES=("$BENCH_DIR"/*.qasm)
# TOTAL_FILES=${#FILES[@]}

# # 3. Define the function for one benchmark
# run_bench() {
#     filepath=$1
#     filename=$(basename "$filepath")
#     base="${filename%.*}"
#     progress_log=$2
#     total=$3
#     py_exe=$4

#     # Run NO_HBM
#     export HBM_CONFIG="no_hbm"
#     wisq "$filepath" -op "${base}_NO_HBM.out" --mode scmr -tmr 3600 > /dev/null 2>&1
#     TIME_NO_HBM=$($py_exe print_timesteps.py "${base}_NO_HBM.out" --summary)

#     # Run ARCH_A
#     export HBM_CONFIG="shared_none"
#     wisq "$filepath" -op "${base}_ARCH_A.out" --mode scmr -tmr 3600 > /dev/null 2>&1
#     TIME_ARCH_A=$($py_exe print_timesteps.py "${base}_ARCH_A.out" --summary)

#     # Print for the collector
#     echo "$base | $TIME_NO_HBM | $TIME_ARCH_A"
    
#     # Update Progress (sent to stderr so it shows in slurm log)
#     echo "done" >> "$progress_log"
#     curr=$(wc -l < "$progress_log")
#     echo "Progress: [$curr/$total] completed ($base)" >&2
# }

# # Export the function and variables so parallel can use them
# export -f run_bench

# echo "Starting benchmarks in parallel..."
# echo "Total benchmarks: $TOTAL_FILES"

# # 4. Execute in Parallel
# # $SLURM_CPUS_PER_TASK is automatically set by Slurm
# parallel --jobs ${SLURM_CPUS_PER_TASK:-1} run_bench {} "$PROGRESS_LOG" "$TOTAL_FILES" "$PYTHON_EXE" ::: "${FILES[@]}" > "$RESULT_FILE"

# # 5. Generate the Final TXT Report
# {
#     echo -e "\n================ FINAL SUMMARY ================"
#     printf "%-25s | %-12s | %-12s\n" "Benchmark" "NO_HBM" "ARCH_A"
#     echo "-----------------------------------------------"
#     sort "$RESULT_FILE" | while IFS=" | " read -r name no_hbm arch_a; do
#         printf "%-25s | %-12s | %-12s\n" "$name" "$no_hbm" "$arch_a"
#     done
#     echo "==============================================="
# } > "$REPORT_FILE"

# # Clean up
# rm "$PROGRESS_LOG" "$RESULT_FILE"
# echo "Done! Summary saved to $REPORT_FILE"