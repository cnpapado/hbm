#!/bin/bash
#
# Quick end-to-end check of every design on one small circuit, without Slurm. Run this on
# an interactive node before submitting anything:
#
#   cd ~/hbm && source .venv/bin/activate && bash test/revision/smoke_test.sh
#
# It (1) runs the design unit tests, (2) draws every design for N=16 into
# test/revision/smoke/figs, (3) routes bench_n16_p50 with every design (10 min cap each),
# and (4) runs the analysis on the outputs. Check the figures and the printed table.

set -uo pipefail
cd "$(dirname "$0")/../.."  # -> repo root
OUT=test/revision/smoke
mkdir -p "$OUT/figs"
BENCH=test/benchmarks_bursty_cx/bench_n16_p50.qasm
export HBM_D="${HBM_D:-25}" HBM_CULT_ROUNDS="${HBM_CULT_ROUNDS:-70}"
unset HBM_CONFIG

echo "== 1. unit tests"
python -m pytest -q wisq/tests/test_designs.py || echo "!! unit tests failed"

SPECS=(D0-S4 D1-S4 D2-wide D2-tight D2-wide-borrow D3-k1 D3-khalf D3-k2 D3-kquarter
       D3-k1-route D4-k1 D4-k1p5 D5-S4 D5-S8 D5-S8-3d)

echo "== 2. drawings"
for s in "${SPECS[@]}"; do
    python scripts/revision/draw_design.py "$s" 16 "$OUT/figs/$s.png" || echo "!! draw $s failed"
done

echo "== 3. routing bench_n16_p50"
for s in "${SPECS[@]}"; do
    start=$(date +%s)
    if HBM_DESIGN="$s" wisq "$BENCH" -op "$OUT/bench_n16_p50__$s.out" --mode scmr -tmr 600 \
        > "$OUT/$s.log" 2>&1; then
        steps=$(python test/print_timesteps.py "$OUT/bench_n16_p50__$s.out" --summary)
        echo "   $s: $steps steps ($(( $(date +%s) - start ))s)"
    else
        echo "!! $s failed, see $OUT/$s.log"; tail -5 "$OUT/$s.log"
    fi
done

echo "== 4. analysis"
python scripts/revision/analyze.py "$OUT" --csv "$OUT/smoke.csv"
python scripts/revision/compare.py "$OUT/smoke.csv" --prefix "$OUT/smoke"
echo "done: inspect $OUT/figs/*.png, $OUT/smoke.csv, $OUT/smoke_pairs.png"
