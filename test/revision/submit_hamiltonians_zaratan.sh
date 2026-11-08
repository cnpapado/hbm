#!/bin/bash
#
# Submit the Hamiltonian-simulation campaign on Zaratan (UMD): the 18 circuits in
# benchmarks_real/hamiltonians_eps1e-2/ (one Trotter step of the simulation_hamiltonians
# families, regenerated with scripts/hamiltonians/gen_trotter.py and synthesized at eps 1e-2,
# 167-22k T gates) x the 13 configurations of submit_revision.sh: 2D-Cult (D2-wide, D2-tight),
# Planar-2D (D0-alt), HBM with factories (D3-k1-fact, D3-s{2,4,8,16}-fact) and HBM-Cult
# (D3-k1, D3-s{2,4,8,16}). Cultivation runs (D2, HBM-Cult) are queued at the shortest R whose
# T states meet the 1% target (ROUNDS=best). For N < S, Shared-S has no source and fails at
# start (h2, heisxyz_n5, surface_d3 at S8/S16): not applicable, not a timeout.
#
#   bash test/revision/submit_hamiltonians_zaratan.sh ham [--dry-run]
#
# These are no larger than the real campaign (<= 34k T), so they use its TIME (4 h; its probes
# finished in <= 2 h 19 min with <= 530 MB) and MEM 4G for margin. Keep TIME at 4 h so placement
# gets the same budget as the real campaign and the two compare.
# Default campaign runs/hamiltonians-fb: runs/hamiltonians holds the earlier 8-configuration runs
# from the jessica branch, which the finished-run check would otherwise reuse.
# Finished runs are skipped, so rerunning with a larger TIME only resubmits timeouts —
# but keep TIME fixed within a campaign (placement time changes the results).
#
# Overrides: ACCOUNT, PART, TIME (HH:MM:SS, wisq gets TIME - 30 min), MEM, REV_DIR,
# CULT_SPECS / FACT_SPECS.
set -euo pipefail
HBM_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export HBM_ROOT HBM_VENV="${HBM_VENV:-$HBM_ROOT/wisq/.venv}"
PHASE="${1:-ham}"
DEF_MEM=4G; DEF_TIME=04:00:00
export ACCOUNT="${ACCOUNT:-xiaodiwu-prj-cmsc}"
export PART="${PART:-standard}"
export TIME="${TIME:-$DEF_TIME}"
export MEM="${MEM:-$DEF_MEM}"
export REV_DIR="${REV_DIR:-runs/hamiltonians-fb}"
export ROUNDS=best
[ -x "$HBM_VENV/bin/wisq" ] || { echo "no wisq in $HBM_VENV (see CLAUDE.md, Install)" >&2; exit 1; }
export PATH="$HBM_VENV/bin:$PATH"  # plan_d0.py and the finished-run check; system python3 is 3.6
exec bash "$HBM_ROOT/test/revision/submit_revision.sh" "$PHASE" "${2:-}"
