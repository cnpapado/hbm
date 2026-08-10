# test/ — benchmarks and per-arch runners

Benchmark inputs, per-config run scripts, and analysis outputs. See the root
`CLAUDE.md` for the HBM_CONFIG contract and metric definitions.

## Benchmark directories

- `benchmarks_bursty_cx/` — synthetic bursty-CNOT benchmarks
  (`bench_nN_pP.qasm` where `N`=qubits, `P`=T-gate intensity in percent).
  Used for the paper's Fig-8/9/10 sweeps.
- `benchmarks_universal_cx_2/` — a broader synthetic mix used in older runs.
- `qft/` — Quantum Fourier Transform circuits at various sizes. Very
  T-heavy and deep; **not tractable locally**. Files named
  `qft_qNNN_dDDDDD.qasm` where NNN=qubits, DDDDD=depth.
- `shor/` — Shor's algorithm circuits (small).

Names encode circuit shape:
- `random_qNN_dDD` → N qubits, ideal depth = DD (verified against
  `circ.depth(filter=[cx,t,tdg])`).
- `bench_nN_pP` → N qubits, T-intensity P%.

## Run scripts (Slurm)

All `run_*.sh` scripts are Slurm array jobs. They are **meant to be submitted
to a cluster, not run locally** — each array task picks one benchmark via
`$SLURM_ARRAY_TASK_ID` and runs with a 24-48h `-tmr`.

```
sbatch --array=0-32 run_arch_C_shared_4.sh
```

Each script hardcodes `BENCH_DIR`, a results dir, an `ARCH_NAME`, and the
`HBM_CONFIG` it exports. Modify the top of the file to point at a different
benchmark suite. The array upper bound must match the file count in
`BENCH_DIR`.

- `run_no_hbm.sh` → `HBM_CONFIG=no_hbm` (2D baseline), compact_layout.
- `run_arch_A.sh` → `HBM_CONFIG=shared_none` (dedicated 1:1).
- `run_arch_C_shared_{2,4,8,16}.sh` → `shared_N-route_upper` (Upper-First).
- `run_arch_C_shared_{2,4}_perimeter.sh` → same + `-anchilla_perimeter`.
- `run_arch_D_shared_{2,4,8,16}.sh` → `shared_N-route_3d` (generic 3D
  routing). Results land in `results_temp_3d/`.
- `run_all.sh` — the sbatch submission driver; uncomment which archs to
  submit.
- `run.sh`, `submit_benchmarks.sh` — two-config comparison sweep + its
  sbatch wrapper (loads `python/3.12.10` module, activates `~/hbm/.venv`).
- `run_array.sh` — dual-config array job over `benchmarks_universal_cx_2/`.

Note `submit_benchmarks.sh` and `scripts/run_count_steps.sh` assume the repo
lives at `~/hbm` on the cluster and that a venv exists at `~/hbm/.venv`.

## Analysis scripts under `test/`

- `print_timesteps.py <out.json> [--summary]` — reports `len(steps)` (and
  optionally the ideal timestep count if wisq wrote one). This is what
  `run_*.sh` calls to build the `.res` result files.
- `parse_utils.py` — result-file parsing helpers used by the plotting
  scripts.
- `plot*.py`, `plot_*.py` — figure generation for the paper (Cost Ratio,
  STV, MSRD, congestion trends, etc.).
- `stv_analysis.py`, `scaling_advantage.py`, `calculate_depth.py` —
  aggregate metric computation across a `.res` set.

## Where results land

- Per-run output JSONs: paths named `{base}_{ARCH_NAME}.out` in `test/`.
- Per-run summaries (one line per benchmark): `results_temp_*/` dirs, as
  set by each `run_*.sh`.
- Merged CSVs / txts (`final_merged_data.csv`, `summary_results*.txt`,
  `benchmark_report*.txt`) come from ad-hoc aggregation runs. Not
  regenerated automatically.

## Tips

- To iterate on a routing change, prefer `random_qNN_dDD` benchmarks under
  `../quantum-compiler-benchmark-circuits/random/random_circuits/` over the
  bursty-cx synthetics. They're smaller, faster, and CNOT-heavy — which is
  the regime where ARCH_D's 3D CNOT routing actually shows up (paper's
  synthetics were designed to stress T-supply, not CNOT congestion).
- The `.out` files here are large. If you need to compare N benchmarks × M
  configs, redirect outputs to `/tmp/` or another scratch dir rather than
  committing them.
