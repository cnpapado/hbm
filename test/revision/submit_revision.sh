#!/bin/bash
#
# Submit the revision sweep (designs #0-#5) as Slurm array jobs. See REVISION.md.
#
#   ./submit_revision.sh pilot [--dry-run]   go/no-go: #2 vs #3 on small synthetic circuits
#   ./submit_revision.sh core  [--dry-run]   all designs on all synthetic circuits
#   ./submit_revision.sh full  [--dry-run]   core + the JKU suite + optional variants
#
# --dry-run prints the sbatch commands without submitting.
# Every run uses HBM_D=25 unless you export HBM_D before calling this script. After
# analysis, rows flagged rerun_needed should be rerun with HBM_D set to their d_req.

set -euo pipefail
cd "$(dirname "$0")/.."  # -> test/
PHASE="${1:-pilot}"
DRY="${2:-}"
mkdir -p logs_rev revision/lists

ls benchmarks_bursty_cx/bench_n{16,25,49,64}_p*.qasm > revision/lists/synth_small.txt
ls benchmarks_bursty_cx/*.qasm > revision/lists/synth_all.txt
ls ../quantum-compiler-benchmark-circuits/jku_suite/*.qasm > revision/lists/jku.txt

submit() {  # submit <bench_list> <design> [cultivation_rounds]
    local list="$1" design="$2" rounds="${3:-70}"
    local n
    n=$(wc -l < "$list" | tr -d ' ')
    local cmd=(sbatch --array="0-$((n - 1))" --job-name="rev-${design}-R${rounds}"
               --export="ALL,DESIGN=${design},BENCH_LIST=${list},HBM_CULT_ROUNDS=${rounds}"
               revision/run_design.sh)
    if [ "$DRY" = "--dry-run" ]; then echo "${cmd[*]}"; else "${cmd[@]}"; fi
}

CULT_P1=(D2-wide D2-tight D3-k1 D3-khalf D3-k2 D3-kquarter)
CULT_P3=(D4-k1 D4-k1p5)
FACT=(D0-S4 D0-S8 D0-S16 D1-S4 D1-S8 D1-S16 D5-S4 D5-S8 D5-S16)
EXTRA=(D2-wide-borrow D2-tight-borrow D3-k1-route D5-S8-3d)
ROUNDS=(30 70 360)  # cultivation recharge: Gidney optimistic / typical, IBM pessimistic

case "$PHASE" in
    pilot)
        for d in D2-wide D2-tight D3-k1 D3-khalf D3-k2; do
            for r in 70 360; do submit revision/lists/synth_small.txt "$d" "$r"; done
        done
        ;;
    core|full)
        lists=(revision/lists/synth_all.txt)
        [ "$PHASE" = "full" ] && lists+=(revision/lists/jku.txt)
        for list in "${lists[@]}"; do
            for d in "${CULT_P1[@]}" "${CULT_P3[@]}"; do
                for r in "${ROUNDS[@]}"; do submit "$list" "$d" "$r"; done
            done
            for d in "${FACT[@]}"; do submit "$list" "$d"; done
            if [ "$PHASE" = "full" ]; then
                for d in "${EXTRA[@]}"; do submit "$list" "$d" 70; done
            fi
        done
        ;;
    *)
        echo "usage: $0 pilot|core|full [--dry-run]" >&2
        exit 1
        ;;
esac
