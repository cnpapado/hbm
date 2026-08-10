# HBM: High-Bandwidth Magic States

Research repo for the MICRO 2026 submission "Magic on Top: A Vertically
Stacked Fault Tolerant Quantum Architecture for High-Bandwidth Magic State
Delivery". Modifies the WISQ/DASCOT lattice-surgery compiler to model a
two-layer FTQC architecture: logical data qubits on the lower plane, magic
state qubits on an upper plane connected via inter-layer couplings. Evaluates
several sharing ratios and routing strategies against a planar 2D baseline
(perimeter magic states, as in DASCOT).

## Layout

- `wisq/` — modified WISQ compiler; installed editable. See `wisq/CLAUDE.md`
  for routing internals.
- `test/` — benchmarks + per-arch run scripts (`benchmarks_bursty_cx/`,
  `qft/`, `benchmarks_universal_cx_2/`, ...). See `test/CLAUDE.md`.
- `scripts/` — analysis (gate stats, ideal-timestep calc, plotting).
- `quantum-compiler-benchmark-circuits/` — external benchmark suite
  (`random/`, `qft/`, `jku/`, etc.).
- `lattice_surgery/` — Stim/PyMatching circuit-level LER simulations for the
  vertical-coupling error model.
- `datasets/`, `figures/` — paper artifacts.
- `decoder-bench/` — decoder benchmarking (auxiliary, not part of the main
  compiler pipeline).

## Install

Python **3.13** required. Deps pin `numpy>=2.3`, `pennylane 0.43`, `qiskit>=2`
— the macOS system Python 3.9 will send pip into a multi-minute backtracking
resolve. Java 21 and a C compiler must also be present (checked by
`wisq/setup.py`).

```
cd wisq
uv venv --python 3.13 .venv
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install --upgrade pip build
.venv/bin/python -m build --sdist
.venv/bin/python -m pip install -e .
```

Editable install: `.py` edits under `wisq/src/wisq/` are live. Re-run
`pip install -e .` only after `pyproject.toml` or package-data changes.

Activate: `source wisq/.venv/bin/activate`.

## Run

Every wisq invocation is parameterized by the `HBM_CONFIG` env var:

```
HBM_CONFIG=<config> wisq bench.qasm -op out.json --mode scmr \
    -arch square_sparse_layout -tmr <seconds>
```

`HBM_CONFIG` is a `-`-separated token bundle:

- **Sharing ratio**: `no_hbm` (2D baseline, perimeter magic states),
  `shared_none` (1:1 dedicated, ARCH_A — no T-gate routing needed),
  `shared_2`, `shared_4`, `shared_8`, `shared_16`.
- **Routing strategy** (only used with a shared config):
  - `route_upper` → ARCH_C: paper's Upper-First. Elevator up first, then
    route laterally on the upper plane. Applies to T-gates only.
  - `route_3d` → ARCH_D: generic 3D routing added in this fork. Elevator
    up/down anywhere along the path; applies to both T-gates and CNOTs.
  - `route_bottom` → ARCH_B: legacy, largely unused.
- **Modifier**: `-anchilla_perimeter` adds an ancilla ring around the grid.

Examples:
- 2D baseline: `HBM_CONFIG=no_hbm`
- HBM Upper-First, sharing 4: `HBM_CONFIG=shared_4-route_upper`
- HBM generic 3D, sharing 4: `HBM_CONFIG=shared_4-route_3d`

Output is JSON: `{map, arch, gates, steps: [[{id, op, qubits, path}, ...]]}`.
For ARCH_D, `path` entries with payload `>= arch.width * arch.height` refer
to upper-plane cells (encoded as `original_idx + N`); everything else is a
lower-plane cell.

## Metrics

- **Ideal timesteps** = `circ.depth(filter=[cx,t,tdg])` — pure DAG depth over
  routed gates, no hardware constraints. Denominator of the paper's Cost
  Ratio (Eq. 2).
- **Cost ratio** = `actual_timesteps / ideal_timesteps`. Lower is better;
  1.0 is the theoretical floor.
- `scripts/dependency_scheduling.py <wisq_out.json>` computes both the pure
  DAG-depth ideal and, with `--with-cnot-routing`, a diagnostic variant that
  also counts routing-path collisions (higher = router baked in more path
  overlap).
- Space-Time Volume, MSRD, and logical-error-rate metrics are computed by
  scripts under `scripts/results-processing/` and `lattice_surgery/`.

## Gotchas

- `-tmr` is the internal SIGALRM timeout for mapping + routing, in seconds.
  Paper runs used `-tmr 172800` (48h) on Xeon nodes. Locally, anything above
  a few minutes on large benchmarks will hit it.
- When wisq hits `-tmr`, it writes a partial JSON with `"steps": "timeout"`.
  When the OS kills the process (Ctrl-C, task kill), **no file is written** —
  early kill loses the run entirely.
- QFT benchmarks under `test/qft/` and `quantum-compiler-benchmark-circuits/qft/`
  are T-heavy and deep (q010 has depth 14k, 45k T-gates). Not tractable
  locally in reasonable time; use the paper's timeout only if you're willing
  to burn hours.
- Random benchmarks under
  `quantum-compiler-benchmark-circuits/random/random_circuits/` (named
  `random_qNN_dDD` where `NN`=qubits, `DD`=depth) run in seconds to minutes
  and show the CNOT-side bottleneck clearly — good for iterating.
- `run_*.sh` under `test/` are **Slurm array jobs**, submitted with
  `sbatch --array=0-N run_<arch>.sh`. They are not intended to run locally —
  each task takes one benchmark and a 24-48h `-tmr`. Cluster-side scripts
  assume the repo at `~/hbm` with a venv at `~/hbm/.venv`.

## Fork notes

Upstream WISQ is the dependency-aware DASCOT compiler (Molavi, Xu, Tannu,
Albarghouthi 2025). HBMS-specific surgery lives in
`wisq/src/wisq/{architecture,sarouting,__init__}.py`. Do not modify the
`lib/` subtree (external tooling: guoq, synthetiq).
