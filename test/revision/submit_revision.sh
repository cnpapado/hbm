#!/bin/bash
#
# Submit the revision sweep as Slurm array jobs. See REVISION.md.
# Designs: D0 (DASCOT + factories around the data block), D2 (DASCOT + cultivation in the
# plane), D3 (HBM: cultivation on top). Cultivation designs run at every recharge time R.
#
#   ./submit_revision.sh mini  [--dry-run]   quick: N=16 p10 and p50, short partition (< 4 h)
#   ./submit_revision.sh pilot [--dry-run]   N = 16, 25, 49, 64 (12 circuits)
#   ./submit_revision.sh core  [--dry-run]   all 33 synthetic circuits
#   ./submit_revision.sh full  [--dry-run]   core + the JKU suite + the -borrow/-route variants
#
# --dry-run prints the sbatch commands without submitting. Phases overlap on purpose:
# run_design.sh skips a task whose run already finished (in any outs_rev/ suite), so each
# phase only adds the missing runs. Unfinished (timed-out) runs are retried.
# Top-layer designs route T gates with Upper-First only (routing "TOP").
# Runs are simulated at HBM_D=13 (what the small/medium circuits need at p=1e-3 and a 1%
# target) unless you export HBM_D first. After analysis, rerun the rows whose d_req differs:
#   python ../scripts/revision/make_reruns.py rev.csv > revision/reruns.sh && bash revision/reruns.sh
#
# Parameter choices (see wisq/src/wisq/designs.py for the citations):
#   cultivation recharge  60 rounds (d1=3, T error 3e-6) and 360 rounds (d1=5, 2e-9):
#                         Tour de gross App. A.6, Table 5.
#   factory count         X<m> = m x F*, the break-even count for the circuit's T demand
#                         (Litinski, A Game of Surface Codes, Sec. 4.4); m in {1/4,1/2,1,2}
#                         brackets the space-time optimum; each design is reported at its best.
SIM_D="${HBM_D:-13}"

set -euo pipefail
cd "$(dirname "$0")/.."  # -> test/
PHASE="${1:-pilot}"
DRY="${2:-}"
mkdir -p logs_rev revision/lists

# mini skips p90 (9,900 T gates): pilot runs it on the normal partition (48 h), not 4 h.
ls benchmarks_bursty_cx/bench_n16_p{10,50}.qasm > revision/lists/synth_n16.txt
ls benchmarks_bursty_cx/bench_n{16,25,49,64}_p*.qasm > revision/lists/synth_small.txt
ls benchmarks_bursty_cx/*.qasm > revision/lists/synth_all.txt
ls ../quantum-compiler-benchmark-circuits/jku_suite/*.qasm > revision/lists/jku.txt

submit() {  # submit <bench_list> <design> [cultivation_rounds]
    local list="$1" design="$2" rounds="${3:-60}"
    local n
    n=$(wc -l < "$list" | tr -d ' ')
    local cmd=(sbatch ${SBATCH_EXTRA[@]+"${SBATCH_EXTRA[@]}"} --array="0-$((n - 1))" --job-name="rev-${design}-R${rounds}"
               --export="ALL,DESIGN=${design},BENCH_LIST=${list},HBM_CULT_ROUNDS=${rounds},HBM_D=${SIM_D}"
               revision/run_design.sh)
    if [ "$DRY" = "--dry-run" ]; then echo "${cmd[*]}"; else "${cmd[@]}"; fi
}

CULT=(D2-wide D2-tight D3-k1 D3-khalf D3-k2 D3-kquarter)
ROUNDS=(60 360)
FACT=(D0-X0.25 D0-X0.5 D0-X1 D0-X2)
EXTRA=(D2-wide-borrow D2-tight-borrow D3-k1-route)
SBATCH_EXTRA=()

run_set() {  # run_set <bench_list>: every design, cultivation at every R
    for d in "${CULT[@]}"; do
        for r in "${ROUNDS[@]}"; do submit "$1" "$d" "$r"; done
    done
    for d in "${FACT[@]}"; do submit "$1" "$d"; done
}

case "$PHASE" in
    mini)
        SBATCH_EXTRA=(-p short -t 04:00:00)
        export TMR=13800  # wisq gives up (writes a timeout file) before Slurm kills the job
        run_set revision/lists/synth_n16.txt
        ;;
    pilot)
        run_set revision/lists/synth_small.txt
        ;;
    core|full)
        lists=(revision/lists/synth_all.txt)
        [ "$PHASE" = "full" ] && lists+=(revision/lists/jku.txt)
        for list in "${lists[@]}"; do
            run_set "$list"
            if [ "$PHASE" = "full" ]; then
                for d in "${EXTRA[@]}"; do submit "$list" "$d" 60; done
            fi
        done
        ;;
    *)
        echo "usage: $0 mini|pilot|core|full [--dry-run]" >&2
        exit 1
        ;;
esac
