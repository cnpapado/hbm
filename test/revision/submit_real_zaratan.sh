#!/bin/bash
#
# Submit the real-benchmark campaign on Zaratan (UMD): 11 circuits x 8 configurations.
#   Ising n10, n13, n16, n26, n34, n66      benchmarks_real/ising_eps1e-2/
#   QED-C Heisenberg n16, n20, n25, n49, n64  benchmarks_real/heisenberg_eps1e-2/
#   (Clifford+T at eps 1e-2 per rotation, scripts/synth_ising.py --merge)
# Configurations (REVISION.md): 2D-Cult-k1 (D2-wide), 2D-Cult-k1/2 (D2-tight), Planar-2D
# (D0-alt), HBM-Dedicated (D3-k1-fact), HBM-Shared-2/4/8/16 (D3-s{2,4,8,16}-fact).
# One Slurm array per configuration, one task per circuit; finished runs are skipped, so
# rerunning this only resubmits what is missing or timed out.
#
#   bash test/revision/submit_real_zaratan.sh [--dry-run]
#
# Overrides: ACCOUNT, PART, TIME (HH:MM:SS, wisq gets TIME - 30 min), MEM, REV_DIR, and
# CULT_SPECS / FACT_SPECS (submit_revision.sh). runs/real ran the 5-step Ising n10/n13/n16
# (now benchmarks_real/ising5_eps1e-2/); runs/real1 is the one-step set plus bottom routing:
#   REV_DIR=runs/real1 FACT_SPECS="D0-alt D3-k1-fact D3-s{2,4,8,16}-fact D3-s{2,4,8,16}-fact-bottom"
#
# TIME is 4 h: wisq gets 3.5 h, of which placement (simulated annealing) may use half and
# routing half. Timing probes (runs/real/probe, 5 circuits x 8 configurations at exactly
# these settings) all finished: longest 2 h 19 min (Heisenberg n64), peak memory 530 MB.
# Placement on the 5-step circuits stops at its 1.75 h cap rather than converging, so a
# longer TIME gives placement longer and changes results: keep TIME fixed within a campaign.
set -euo pipefail
HBM_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export HBM_ROOT HBM_VENV="${HBM_VENV:-$HBM_ROOT/wisq/.venv}"
export ACCOUNT="${ACCOUNT:-xiaodiwu-prj-cmsc}"
export PART="${PART:-standard}"
export TIME="${TIME:-04:00:00}"
export MEM="${MEM:-2G}"
export REV_DIR="${REV_DIR:-runs/real}"
export ROUNDS=best
[ -x "$HBM_VENV/bin/wisq" ] || { echo "no wisq in $HBM_VENV (see runs/real/setup/install_env.sh)" >&2; exit 1; }
export PATH="$HBM_VENV/bin:$PATH"  # plan_d0.py and the finished-run check; system python3 is 3.6
exec bash "$HBM_ROOT/test/revision/submit_revision.sh" real "${1:-}"
