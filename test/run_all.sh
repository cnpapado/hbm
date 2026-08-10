#!/bin/bash
#
# Submits the full architecture sweep as Slurm array jobs.
#
# All configs below run on the SAME benchmark dir (benchmarks_bursty_cx),
# the SAME layout (square_sparse_layout), and the SAME timeout (48h), and
# write their .res files to the SAME dir (results_sweep/) so the results
# are directly comparable. Do not change these per-script without changing
# them everywhere.
#
# The array bound must match the benchmark count: benchmarks_bursty_cx has
# 33 files -> --array=0-32.
#
# Comment out any config you don't need.

ARRAY="0-32"

# --- 2D planar baseline (perimeter magic states) ---
sbatch --array=$ARRAY run_no_hbm.sh

# --- HBM dedicated 1:1 (no T-gate routing needed) ---
sbatch --array=$ARRAY run_arch_A.sh

# --- HBM Upper-First (paper's strategy) ---
sbatch --array=$ARRAY run_arch_C_shared_2.sh
sbatch --array=$ARRAY run_arch_C_shared_4.sh
sbatch --array=$ARRAY run_arch_C_shared_8.sh
sbatch --array=$ARRAY run_arch_C_shared_16.sh

# --- HBM generic 3D routing (T gates AND CNOTs may use the upper plane) ---
sbatch --array=$ARRAY run_arch_D_shared_2.sh
sbatch --array=$ARRAY run_arch_D_shared_4.sh
sbatch --array=$ARRAY run_arch_D_shared_8.sh
sbatch --array=$ARRAY run_arch_D_shared_16.sh

# --- Separate QFT experiment: these use BENCH_DIR="qft", NOT the sweep
#     benchmark dir, so their numbers are not comparable to the above.
# sbatch --array=1-20 run_arch_C_shared_2_perimeter.sh
# sbatch --array=1-20 run_arch_C_shared_4_perimeter.sh
