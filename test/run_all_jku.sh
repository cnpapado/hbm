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
# The array bound is derived from the benchmark count (161 circuits -> 0-160,
# so 3 x 161 = 483 tasks) rather than hardcoded, so it can't drift.
#
# Benchmarks live in ../quantum-compiler-benchmark-circuits/jku_suite/ and
# ARE tracked in git, unlike test/benchmarks_bursty_cx.
#
# Run from inside test/ :  ./run_all_jku.sh

BENCH_DIR="../quantum-compiler-benchmark-circuits/jku_suite"
FILES=("$BENCH_DIR"/*.qasm)
if [ ! -e "${FILES[0]}" ]; then
    echo "ERROR: no .qasm files in $BENCH_DIR" >&2
    exit 1
fi
ARRAY="0-$(( ${#FILES[@]} - 1 ))"
echo "Submitting array $ARRAY (${#FILES[@]} benchmarks from $BENCH_DIR)"

sbatch --array=$ARRAY run_jku_no_hbm.sh
sbatch --array=$ARRAY run_jku_arch_C_shared_4.sh
sbatch --array=$ARRAY run_jku_arch_D_shared_4.sh
