#!/bin/bash
#SBATCH -A p33086
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH -t 48:00:00
#SBATCH --mem=16G
#SBATCH --job-name=hbm-seam
#SBATCH --output=logs_seam/%x_%A_%a.out
#
# The cross-layer merge in Stim (seam_merge.py), one code distance per array task. Each task
# writes results_seam/seam_d<d>.csv (and a .sinter file that lets a resubmitted task resume).
#
#   cd ~/hbm/lattice_surgery && mkdir -p logs_seam results_seam
#   source ~/hbm/.venv/bin/activate && pip install stim sinter pymatching   # once
#   python seam_merge.py --check --d 3 5 --mode seam whole                  # quick sanity check
#   sbatch --array=0-4 seam_merge.sh                                        # d = 3 5 7 9 11
#   python seam_merge.py --fit 'results_seam/seam_d*.csv'                   # when all are done
#
# Environment overrides (pass with sbatch --export=ALL,VAR=...):
#   DISTANCES   "3 5 7 9 11"   the array index picks one of these
#   MODES       "seam whole"   seam: p' on the 2d - 1 cross-layer CNOTs only; whole: the old
#                              model, p' on the whole coupler patch and bridge
#   MS          "1 5 10"       p' = m p
#   SHOTS       10000000       max shots per circuit
#   ERRORS      500            stop a circuit after this many logical errors
#   EXTRA       ""             more seam_merge.py flags, e.g. "--old-offset" or "--p 1e-3 2e-3"
#   VENV        ~/hbm/.venv    the Python venv, e.g. VENV=$HOME/seam-venv (stim, sinter, pymatching,
#                              numpy<2) if sinter fails with numpy 2 (AssertionError in AnonTaskStats)
# Large d at small p will hit SHOTS with few or no errors: that is expected, the fit uses only
# points with at least --min-errors errors. For better low-p points at small d, rerun e.g.
#   sbatch --array=0-1 --export=ALL,DISTANCES="3 5",SHOTS=200000000,EXTRA="--p 1e-3 1.5e-3 2e-3" seam_merge.sh
# (those tasks write the same seam_d<d>.csv names: move the first results aside before.)

module load python/3.12.10
source "${VENV:-$HOME/hbm/.venv}/bin/activate"
cd ~/hbm/lattice_surgery || exit 1
python3 -c 'import stim, sinter, pymatching' || { echo "ERROR: pip install stim sinter pymatching" >&2; exit 1; }

read -r -a DS <<< "${DISTANCES:-3 5 7 9 11}"
D="${DS[$SLURM_ARRAY_TASK_ID]:?no distance for array index $SLURM_ARRAY_TASK_ID}"
echo "Task $SLURM_ARRAY_TASK_ID | d=$D | modes ${MODES:-seam whole} | m ${MS:-1 5 10}"

# shellcheck disable=SC2086  # word splitting of the lists is intended
python3 seam_merge.py --d "$D" --m ${MS:-1 5 10} --mode ${MODES:-seam whole} \
    --max-shots "${SHOTS:-10000000}" --max-errors "${ERRORS:-500}" \
    --workers "${SLURM_CPUS_PER_TASK:-8}" --csv "results_seam/seam_d${D}.csv" ${EXTRA:-}
