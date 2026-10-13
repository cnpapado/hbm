#!/bin/bash
#
# Quick end-to-end check of every design on one small circuit, without Slurm. Run this on
# an interactive node before submitting anything:
#
#   cd ~/hbm && source .venv/bin/activate && bash test/revision/smoke_test.sh
#
# It (1) runs the design unit tests, (2) draws every design for N=16 into
# test/revision/smoke/figs, (3) routes one circuit (default bench_n16_p50) with every design
# (10 min cap each),
# (4) runs the analysis on the outputs, and (5) adds the Litinski PPM baseline (pair P4).
# Check the figures and the printed table.
#
# Overrides (environment): SMOKE_SPECS="D3-k1 D3-kquarter" picks designs, SMOKE_BENCH picks
# the circuit, HBM_D the simulation distance (default 25: checks code paths only).

set -uo pipefail
cd "$(dirname "$0")/../.."  # -> repo root
OUT=test/revision/smoke
mkdir -p "$OUT/figs"
rm -f "$OUT"/*.out "$OUT"/*.log  # outputs of earlier smoke runs (older format)
BENCH="${SMOKE_BENCH:-test/benchmarks_bursty_cx/bench_n16_p50.qasm}"
NAME="$(basename "$BENCH" .qasm)"
# d=25 here only checks the code paths: at d=13 a factory is 4x4 tiles and bench_n16_p50
# needs F*=13 of them, which do not fit on the top layer of a 16-qubit chip (D5 is rejected,
# as it should be). The sweep itself runs at d=13.
export HBM_D="${HBM_D:-25}" HBM_CULT_ROUNDS="${HBM_CULT_ROUNDS:-60}"
unset HBM_CONFIG

echo "== 1. unit tests"
python -m pytest -q wisq/tests/test_designs.py || echo "!! unit tests failed"

# Top-layer designs use Upper-First; general 3D routing (-3d) is not run.
SPECS=(D0-X1 D1-band-X1 D1-mesh-X1 D2-wide D2-tight D2-wide-borrow D3-k1 D3-khalf D3-k2
       D3-kquarter D3-k1-route D4-k1 D4-k1p5 D5-X1 D5-X0.5)
[ -n "${SMOKE_SPECS:-}" ] && read -r -a SPECS <<< "$SMOKE_SPECS"

echo "== 2. drawings"
for s in "${SPECS[@]}"; do
    python scripts/revision/draw_design.py "$s" 16 "$OUT/figs/$s.png" "$BENCH" \
        || echo "!! draw $s failed"
done

echo "== 3. routing $NAME"
for s in "${SPECS[@]}"; do
    start=$(date +%s)
    if HBM_DESIGN="$s" wisq "$BENCH" -op "$OUT/${NAME}__$s.out" --mode scmr -tmr 600 \
        > "$OUT/$s.log" 2>&1; then
        steps=$(python test/print_timesteps.py "$OUT/${NAME}__$s.out" --summary)
        echo "   $s: $steps steps ($(( $(date +%s) - start ))s)"
    else
        echo "!! $s failed, see $OUT/$s.log"; tail -5 "$OUT/$s.log"
    fi
done

echo "== 4. analysis"
python scripts/revision/analyze.py "$OUT" --csv "$OUT/smoke.csv"

echo "== 5. PPM baseline (formula, no routing)"
python scripts/revision/ppm_baseline.py "$BENCH" --rounds "$HBM_CULT_ROUNDS" --csv "$OUT/ppm.csv"
python scripts/revision/compare.py "$OUT/smoke.csv" "$OUT/ppm.csv" --prefix "$OUT/smoke" \
    --R "$HBM_CULT_ROUNDS"
echo "done: inspect $OUT/figs/*.png, $OUT/smoke.csv, $OUT/smoke_pairs.png, $OUT/smoke_ppm.png"
