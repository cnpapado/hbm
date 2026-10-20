# Shared by submit_revision.sh and run_design.sh. Both source it from test/.

run_tag() {  # run_tag <design> <cultivation_rounds> <d>: the run's tag in its output file name
    # Cultivation designs depend on the recharge rounds; factory designs on the factory
    # period and size.
    case "$1" in
        D2*|D3*|D4*) echo "${1}__d${3}_R${2}" ;;
        *)           echo "${1}__d${3}_F${HBM_FACTORY_ROUNDS:-43}q${HBM_FACTORY_QUBITS:-4620}" ;;
    esac
}

finished_run() {  # finished_run <bench> <tag>: print a finished run's output (any suite), or fail
    local f
    for f in outs_rev/*/"${1}__${2}.out"; do
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
    # A running task's log (logs_rev/%x_%A_%a.out, run_design.sh) starts with
    # "Task <i> | <tag> | <qasm>".
    command -v squeue >/dev/null || return 0
    local job
    squeue -u "$USER" -h -r -t RUNNING,COMPLETING -o "%j_%i" 2>/dev/null | while read -r job; do
        [ -f "logs_rev/${job}.out" ] || continue
        awk -F' [|] ' '/^Task / { n = split($3, p, "/"); sub(/\.qasm$/, "", p[n]); print p[n], $2; exit }' \
            "logs_rev/${job}.out"
    done
}
