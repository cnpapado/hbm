#!/bin/bash

sbatch --array=0-32 run_no_hbm.sh

# sbatch --array=0-32 run_arch_A.sh

# sbatch --array=0-32 run_arch_C_shared_2.sh

# sbatch --array=1-20 run_arch_C_shared_2_perimeter.sh

# sbatch --array=0-32 run_arch_C_shared_4.sh

# sbatch --array=1-20 run_arch_C_shared_4_perimeter.sh

# sbatch --array=0-32 run_arch_C_shared_8.sh

# sbatch --array=0-32 run_arch_C_shared_16.sh