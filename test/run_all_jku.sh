#!/bin/bash
#
# Submits the JKU-suite comparison as Slurm array jobs.
#
# Three configs on the same 161 benchmarks, same layout (square_sparse),
# same timeout (48h), all writing to results_jku/ :
#   - 2D planar baseline        (no_hbm)
#   - HBM Upper-First,  S=4     (shared_4-route_upper)
#   - HBM generic 3D,   S=4     (shared_4-route_3d)
#
# 161 benchmarks -> --array=0-160, so 3 x 161 = 483 tasks total.
#
# Benchmarks live in ../quantum-compiler-benchmark-circuits/jku_suite/ and
# ARE tracked in git, unlike test/benchmarks_bursty_cx.
#
# Run from inside test/ :  ./run_all_jku.sh

ARRAY="0-160"

sbatch --array=$ARRAY run_jku_no_hbm.sh
sbatch --array=$ARRAY run_jku_arch_C_shared_4.sh
sbatch --array=$ARRAY run_jku_arch_D_shared_4.sh
