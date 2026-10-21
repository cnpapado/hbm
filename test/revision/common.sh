# Shared by submit_revision.sh and run_design.sh. Both source it from test/.

# Where a campaign's files go (relative to test/). REV_DIR=runs/<name> keeps one campaign
# apart from every other: <REV_DIR>/outs, results, logs and lists. Finished runs are looked up
# only there. Unset: the original outs_rev/, results_rev/, logs_rev/, revision/lists/todo/.
if [ -n "${REV_DIR:-}" ]; then
    OUTS="$REV_DIR/outs" RESULTS="$REV_DIR/results" LOGS="$REV_DIR/logs" TODO="$REV_DIR/lists"
else
    OUTS=outs_rev RESULTS=results_rev LOGS=logs_rev TODO=revision/lists/todo
fi

run_tag() {  # run_tag <design> <cultivation_rounds> <d>: the run's tag in its output file name
    # Cultivation designs depend on the recharge rounds; factory designs on the factory
    # period and size.
    case "$1" in
        *-fact) echo "${1}__d${3}_F${HBM_FACTORY_ROUNDS:-0}q${HBM_FACTORY_QUBITS:-22d2}" ;;
        D2*|D3*|D4*) echo "${1}__d${3}_R${2}" ;;
        *)           echo "${1}__d${3}_F${HBM_FACTORY_ROUNDS:-0}q${HBM_FACTORY_QUBITS:-22d2}" ;;
    esac
}

finished_run() {  # finished_run <bench> <tag>: print a finished run's output (any suite), or fail
    local f
    for f in "$OUTS"/*/"${1}__${2}.out"; do
        if [ -f "$f" ] && python3 -c 'import json, sys
sys.exit(0 if isinstance(json.load(open(sys.argv[1])).get("steps"), list) else 1)' "$f" \
                2>/dev/null; then
            echo "$f"
            return 0
        fi
    done
    return 1
}

running_runs() {  # print "<bench> <tag>" for each revision task Slurm is running now
    # A running task's log ($LOGS/%x_%A_%a.out, submit_revision.sh) starts with
    # "Task <i> | <tag> | <qasm>".
    command -v squeue >/dev/null || return 0
    local job
    squeue -u "$USER" -h -r -t RUNNING,COMPLETING -o "%j_%i" 2>/dev/null | while read -r job; do
        [ -f "$LOGS/${job}.out" ] || continue
        awk -F' [|] ' '/^Task / { n = split($3, p, "/"); sub(/\.qasm$/, "", p[n]); print p[n], $2; exit }' \
            "$LOGS/${job}.out"
    done
}
