#!/bin/bash
#
# Run the PPM cross-check (scripts/revision/ppm_qre.py) on the cluster inside a container.
# The cluster's glibc is too old for the modern qsharp wheels (they need glibc >= 2.31), so
# pip there falls back to the legacy IQ# package, which fails on import. A python:3.12-slim
# container has a newer glibc. The venv is kept in ~/.cache/hbm-qre-venv and reused.
#
#   module load apptainer      # or: module load singularity (see: module avail)
#   bash test/revision/run_qre.sh [qasm files or dirs]   # default: test/benchmarks_bursty_cx
#
# Writes ppm_qre.csv in the repo root.

set -euo pipefail
cd "$(dirname "$0")/../.."  # -> repo root
ARGS=("$@")
[ ${#ARGS[@]} -gt 0 ] || ARGS=(test/benchmarks_bursty_cx)

RUN=""
for c in apptainer singularity; do
    if command -v "$c" > /dev/null; then RUN=$c; break; fi
done
if [ -z "$RUN" ]; then
    echo "no apptainer/singularity on PATH: run 'module load apptainer' (or singularity) first"
    exit 1
fi

VENV="$HOME/.cache/hbm-qre-venv"
"$RUN" exec docker://python:3.12-slim bash -c "
    set -e
    [ -x '$VENV/bin/python' ] || python -m venv '$VENV'
    '$VENV/bin/pip' install -q 'qsharp>=1.0'
    '$VENV/bin/python' scripts/revision/ppm_qre.py $(printf '%q ' "${ARGS[@]}")"
