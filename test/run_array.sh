#!/bin/bash
#SBATCH -A p33086      
#SBATCH -p normal                # Partition
#SBATCH --nodes=1                # One node per task
#SBATCH --ntasks=1               # One task per array instance
#SBATCH --cpus-per-task=1        # Use 1 core per benchmark
#SBATCH -t 16:00:00              # Max time per benchmark
#SBATCH --mem=1G                 # Memory per benchmark
#SBATCH --job-name=wisq_63
#SBATCH --output=logs_new/job_%a.out # Logs will be stored in 'logs' folder

# module load python/3.12.10
# source ~/hbm/.venv/bin/activate
# cd ~/hbm/test

# Create logs directory if it doesn't exist
mkdir -p logs_new

# 1. Identify all benchmarks
FILES=(benchmarks_universal_cx_2/*.qasm)


# Safety Check: Ensure the array isn't empty
if [ ! -e "${FILES[0]}" ]; then
    echo "ERROR: No .qasm files found in benchmarks_universal_cx_2/"
    exit 1
fi

# 2. Assign file based on the Array Task ID
current_file=${FILES[$SLURM_ARRAY_TASK_ID]}

# Safety Check: Ensure the selected item is a file, not a directory
if [ -d "$current_file" ]; then
    echo "ERROR: $current_file is a directory, not a file. Check your globbing."
    exit 1
fi

# 2. Assign file based on the Array Task ID
# This ensures each of the 63 cores picks a different file
current_file=${FILES[$SLURM_ARRAY_TASK_ID]}

# 3. Extract filename for reporting
filename=$(basename "$current_file")
base="${filename%.*}"

echo "Task ID $SLURM_ARRAY_TASK_ID processing: $base"

# 4. Run NO_HBM configuration
export HBM_CONFIG="no_hbm"
# ./wisq "$current_file" -op "${base}_NO_HBM.out" --mode scmr -tmr 7200 > /dev/null 2>&1
wisq "$current_file" -op "${base}_NO_HBM.out" --mode scmr -tmr 28800
TIME_NO_HBM=$(python3 print_timesteps.py "${base}_NO_HBM.out" --summary)

# export HBM_CONFIG="shared_4-route_upper"
# # ./wisq "$current_file" -op "${base}_NO_HBM.out" --mode scmr -tmr 7200 > /dev/null 2>&1
# wisq "$current_file" -op "${base}_ARCH_C_shared_4.out" --mode scmr -tmr 14400
# TIME_ARCH_C_shared_4=$(python3 print_timesteps.py "${base}_ARCH_C_shared_4.out" --summary)

# 5. Run ARCH_A configuration
export HBM_CONFIG="shared_none"
wisq "$current_file" -op "${base}_ARCH_A.out" --mode scmr -tmr 28800
TIME_ARCH_A=$(python3 print_timesteps.py "${base}_ARCH_A.out" --summary)

# export HBM_CONFIG="shared_4-route_upper-anchilla_perimeter"
# wisq "$current_file" -op "${base}_ARCH_C_shared_4_perimeter.out" --mode scmr -tmr 14400
# TIME_ARCH_C_shared_4_perimeter=$(python3 print_timesteps.py "${base}_ARCH_C_shared_4_perimeter.out" --summary)

# 6. Save data to a temporary file
echo "$base | $TIME_NO_HBM | $TIME_ARCH_A" > "${base}.tmp_res"

echo "Completed $base"