#!/bin/bash
#SBATCH -A p33086
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH -t 48:00:00
#SBATCH --mem=8G
#SBATCH --job-name=hbm-rev
#SBATCH --output=logs_rev/%x_%A_%a.out
#
# One revision run per array task: one benchmark x one design spec.
# Submitted by submit_revision.sh, which passes these through --export:
#   DESIGN      design spec, e.g. D3-k1 (see wisq/src/wisq/designs.py)
#   BENCH_LIST  file with one .qasm path per line (relative to test/)
#   HBM_D, HBM_CULT_ROUNDS, HBM_FACTORY_ROUNDS, HBM_FACTORY_QUBITS  (optional)
#   TMR         wisq -tmr in seconds (default 172800 = 48h)

module load python/3.12.10
source ~/hbm/.venv/bin/activate
cd ~/hbm/test || exit 1
command -v wisq >/dev/null || { echo "ERROR: wisq not on PATH" >&2; exit 1; }

: "${DESIGN:?DESIGN not set}"
: "${BENCH_LIST:?BENCH_LIST not set}"
TMR="${TMR:-172800}"
export HBM_DESIGN="$DESIGN"
export HBM_D="${HBM_D:-25}"
export HBM_CULT_ROUNDS="${HBM_CULT_ROUNDS:-70}"
export HBM_FACTORY_ROUNDS="${HBM_FACTORY_ROUNDS:-43}"
export HBM_FACTORY_QUBITS="${HBM_FACTORY_QUBITS:-4620}"
unset HBM_CONFIG

mapfile -t FILES < "$BENCH_LIST"
if [ "$SLURM_ARRAY_TASK_ID" -ge "${#FILES[@]}" ]; then
    echo "ERROR: task $SLURM_ARRAY_TASK_ID out of range (${#FILES[@]} benchmarks)" >&2
    exit 1
fi
current_file="${FILES[$SLURM_ARRAY_TASK_ID]}"
base="$(basename "$current_file" .qasm)"

# Tag: design + the parameters that change its timing. Cultivation designs depend on the
# recharge rounds; factory designs on the factory period and size.
case "$DESIGN" in
    D2*|D3*|D4*) SRC="R${HBM_CULT_ROUNDS}" ;;
    *)           SRC="F${HBM_FACTORY_ROUNDS}q${HBM_FACTORY_QUBITS}" ;;
esac
TAG="${DESIGN}__d${HBM_D}_${SRC}"
SUITE="$(basename "$BENCH_LIST" .txt)"
mkdir -p "outs_rev/$SUITE" "results_rev/$SUITE"
output_file="outs_rev/$SUITE/${base}__${TAG}.out"

echo "Task $SLURM_ARRAY_TASK_ID | $TAG | $current_file"
wisq "$current_file" -op "$output_file" --mode scmr -tmr "$TMR"

TIME_RESULT=$(python3 print_timesteps.py "$output_file" --summary)
[ -z "$TIME_RESULT" ] && TIME_RESULT="ERROR"
echo "$base | $TAG | $TIME_RESULT" > "results_rev/$SUITE/${base}__${TAG}.res"
echo "Completed $base | $TAG | $TIME_RESULT"
