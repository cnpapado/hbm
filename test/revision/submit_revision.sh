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
# --dry-run prints the sbatch commands without submitting. Each sbatch line covers only the
# runs not finished yet (in any outs_rev/ suite), so the phases overlap and each adds what
# is missing; timed-out runs are retried. Cancel your pending jobs before resubmitting a
# phase, or the runs they hold are queued twice.
#
# Slurm request (environment variables; defaults: mini short/04:00:00, others normal/48:00:00):
#   PART=<partition>  TIME=HH:MM:SS  MEM=<memory per run, default 8G>
#   e.g.  PART=short TIME=04:00:00 MEM=2G bash revision/submit_revision.sh pilot
# wisq's own timeout (TMR) is set to TIME minus 30 min, so a run that is too slow writes a
# timeout file (retried by the next submission) instead of being killed with no trace.
# Top-layer designs route T gates with Upper-First only (routing "TOP").
# Runs are simulated at HBM_D=13 (what the small/medium circuits need at p=1e-3 and a 1%
# target) unless you export HBM_D first; analyze.py computes STV at that d for every design.
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
source revision/common.sh
PHASE="${1:-pilot}"
DRY="${2:-}"
case "$PHASE" in
    mini) PART="${PART:-short}";  TIME="${TIME:-04:00:00}" ;;
    *)    PART="${PART:-normal}"; TIME="${TIME:-48:00:00}" ;;
esac
MEM="${MEM:-8G}"
IFS=: read -r H M S <<< "$TIME"
TMR=$(( 10#$H * 3600 + 10#$M * 60 + 10#$S - 1800 ))
[ "$TMR" -gt 0 ] || { echo "TIME must be HH:MM:SS and over 30 min" >&2; exit 1; }
STAMP="$(date +%Y%m%d-%H%M%S)"  # each submission gets its own to-do lists
mkdir -p logs_rev revision/lists/todo
command -v python3 >/dev/null ||
    echo "warning: no python3 here, so finished runs are not left out (run_design.sh skips them)" >&2

# mini skips p90 (9,900 T gates): pilot runs it on the normal partition (48 h), not 4 h.
ls benchmarks_bursty_cx/bench_n16_p{10,50}.qasm > revision/lists/synth_n16.txt
ls benchmarks_bursty_cx/bench_n{16,25,49,64}_p*.qasm > revision/lists/synth_small.txt
ls benchmarks_bursty_cx/*.qasm > revision/lists/synth_all.txt
ls ../quantum-compiler-benchmark-circuits/jku_suite/*.qasm > revision/lists/jku.txt

submit() {  # submit <bench_list> <design> [cultivation_rounds]: the runs not finished yet
    local list="$1" design="$2" rounds="${3:-60}"
    local suite tag todo b n
    suite="$(basename "$list" .txt)"
    tag="$(run_tag "$design" "$rounds" "$SIM_D")"
    todo="revision/lists/todo/${suite}__${tag}__${STAMP}.txt"
    : > "$todo"
    while read -r b; do
        finished_run "$(basename "$b" .qasm)" "$tag" >/dev/null || echo "$b" >> "$todo"
    done < "$list"
    n=$(wc -l < "$todo" | tr -d ' ')
    if [ "$n" -eq 0 ]; then
        echo "# ${suite} ${tag}: all finished"
        rm -f "$todo"
        return
    fi
    local cmd=(sbatch -p "$PART" -t "$TIME" --mem="$MEM" --array="0-$((n - 1))"
               --job-name="rev-${design}-R${rounds}"
               --export="ALL,DESIGN=${design},BENCH_LIST=${todo},SUITE=${suite},HBM_CULT_ROUNDS=${rounds},HBM_D=${SIM_D},TMR=${TMR}"
               revision/run_design.sh)
    echo "# ${suite} ${tag}: ${n} of $(wc -l < "$list" | tr -d ' ') to run"
    if [ "$DRY" = "--dry-run" ]; then echo "${cmd[*]}"; else "${cmd[@]}"; fi
}

CULT=(D2-wide D2-tight D3-k1 D3-khalf D3-k2 D3-kquarter)
ROUNDS=(60 360)
FACT=(D0-X0.25 D0-X0.5 D0-X1 D0-X2)
EXTRA=(D2-wide-borrow D2-tight-borrow D3-k1-route)

run_set() {  # run_set <bench_list>: every design, cultivation at every R
    for d in "${CULT[@]}"; do
        for r in "${ROUNDS[@]}"; do submit "$1" "$d" "$r"; done
    done
    for d in "${FACT[@]}"; do submit "$1" "$d"; done
}

case "$PHASE" in
    mini)
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
