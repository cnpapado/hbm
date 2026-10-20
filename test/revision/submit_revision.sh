#!/bin/bash
#
# Submit the revision sweep as Slurm array jobs. See REVISION.md.
# Designs: D0 (DASCOT + factories around the data block), D2 (DASCOT + cultivation in the
# plane), D3 (HBM: cultivation on top).
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
# Recharge times R (ROUNDS, default "best"). A cultivation run is queued only where its grade
# can meet the 1% target on its own (T count x T error <= 0.01): the p90 circuits (9,900 T
# gates) fail at R = 60 (3e-6). ROUNDS=best queues, per circuit, only the shortest such R:
# it also has the fewest qubits (454 vs 463), so it has the lowest STV, and it is all that
# R = best in compare.py needs. ROUNDS="60 360" adds the other R (the per-R comparison).
#
# Slurm request (environment variables; defaults: mini short/04:00:00, others normal/48:00:00):
#   PART=<partition>  TIME=HH:MM:SS  MEM=<memory per run, default 8G>  ACCOUNT=<default p33086>
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
#                         Only counts whose ports fit on the ring are queued (plan_d0.py), and
#                         Xmax (a port on every ring tile) where X2 does not fit.
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
ACCOUNT="${ACCOUNT:-p33086}"
ROUNDS="${ROUNDS:-best}"
ALL_ROUNDS=(60 360)
TARGET=0.01  # analyze.py --target
PLAN=""      # D0 counts that fit, per bench list (run_set)
for r in $ROUNDS; do
    [ "$r" = best ] || [[ " ${ALL_ROUNDS[*]} " == *" $r "* ]] ||
        { echo "ROUNDS must be best or a list from: ${ALL_ROUNDS[*]}" >&2; exit 1; }
done
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

cult_error() {  # T error per state at R rounds (analyze.py --cult-grades)
    case "$1" in 60) echo 3e-6 ;; 360) echo 2e-9 ;; esac
}

feasible() {  # feasible <qasm> <R>: the circuit's T states alone meet the target at R
    local n_t
    n_t=$(grep -cE '^(t|tdg) ' "$1" || true)
    awk -v n="$n_t" -v e="$(cult_error "$2")" -v t="$TARGET" 'BEGIN { exit !(n * e <= t) }'
}

wanted() {  # wanted <qasm> <design> <R>: whether the run can change the results
    case "$2" in
        D0*) [ -z "$PLAN" ] || grep -qxF "$1 $2" "$PLAN"; return ;;  # fits on the ring
        D2*|D3*|D4*) ;;
        *) return 0 ;;
    esac
    feasible "$1" "$3" || return 1
    [ "$ROUNDS" = best ] || return 0
    local r
    for r in "${ALL_ROUNDS[@]}"; do
        if [ "$r" -lt "$3" ] && feasible "$1" "$r"; then return 1; fi  # a shorter R works
    done
    return 0
}

submit() {  # submit <bench_list> <design> [cultivation_rounds]: the wanted runs not finished
    local list="$1" design="$2" rounds="${3:-60}"
    local suite tag todo b n fin=0 skip=0
    suite="$(basename "$list" .txt)"
    tag="$(run_tag "$design" "$rounds" "$SIM_D")"
    todo="revision/lists/todo/${suite}__${tag}__${STAMP}.txt"
    : > "$todo"
    while read -r b; do
        if ! wanted "$b" "$design" "$rounds"; then skip=$((skip + 1))
        elif finished_run "$(basename "$b" .qasm)" "$tag" >/dev/null; then fin=$((fin + 1))
        else echo "$b" >> "$todo"
        fi
    done < "$list"
    n=$(wc -l < "$todo" | tr -d ' ')
    echo "# ${suite} ${tag}: ${n} to run (${fin} finished, ${skip} not needed)"
    if [ "$n" -eq 0 ]; then
        rm -f "$todo"
        return
    fi
    local cmd=(sbatch -A "$ACCOUNT" -p "$PART" -t "$TIME" --mem="$MEM" --array="0-$((n - 1))"
               --job-name="rev-${design}-R${rounds}"
               --export="ALL,DESIGN=${design},BENCH_LIST=${todo},SUITE=${suite},HBM_CULT_ROUNDS=${rounds},HBM_D=${SIM_D},TMR=${TMR}"
               revision/run_design.sh)
    if [ "$DRY" = "--dry-run" ]; then echo "${cmd[*]}"; else "${cmd[@]}"; fi
}

# Override with CULT_SPECS / FACT_SPECS (space-separated) to leave knob values out.
read -r -a CULT <<< "${CULT_SPECS:-D2-wide D2-tight D3-k1 D3-khalf D3-k2 D3-kquarter}"
read -r -a FACT <<< "${FACT_SPECS:-D0-X0.25 D0-X0.5 D0-X1 D0-X2 D0-Xmax}"
EXTRA=(D2-wide-borrow D2-tight-borrow D3-k1-route)

run_set() {  # run_set <bench_list>: every design; cultivation at the R that ROUNDS selects
    PLAN="revision/lists/todo/plan_d0__$(basename "$1" .txt)__${STAMP}.txt"
    python3 revision/plan_d0.py "$1" --d "$SIM_D" --specs "${FACT[@]}" > "$PLAN" || {
        echo "warning: plan_d0.py failed; queuing every D0 count (misfits fail at start)" >&2
        PLAN=""
    }
    for d in "${CULT[@]}"; do
        for r in "${ALL_ROUNDS[@]}"; do
            [ "$ROUNDS" = best ] || [[ " $ROUNDS " == *" $r "* ]] || continue
            submit "$1" "$d" "$r"
        done
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
