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
# The array bound is derived from the benchmark count so it can't drift out
# of sync if circuits are added or removed.
#
# Comment out any config you don't need.

BENCH_DIR="benchmarks_bursty_cx"
FILES=("$BENCH_DIR"/*.qasm)
if [ ! -e "${FILES[0]}" ]; then
    echo "ERROR: no .qasm files in $BENCH_DIR" >&2
    exit 1
fi
ARRAY="0-$(( ${#FILES[@]} - 1 ))"
echo "Submitting array $ARRAY (${#FILES[@]} benchmarks from $BENCH_DIR)"

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
#     qft/ holds 20 circuits -> indices 0-19. (Was 1-20, which skipped
#     index 0 and ran one out-of-range task.) These are deep and very
#     T-heavy; expect most to exhaust the 24h timeout.
# sbatch --array=0-19 run_arch_C_shared_2_perimeter.sh
# sbatch --array=0-19 run_arch_C_shared_4_perimeter.sh
