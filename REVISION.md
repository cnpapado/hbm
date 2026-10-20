# Revision: fair magic-state baselines (D0, D2, D3 and PPM; STV)

Branch `revision/fair-baselines` (based on `feature/generic-3d-routing`). Adds a new design
mode selected with `HBM_DESIGN`. **When `HBM_DESIGN` is unset, wisq behaves exactly as
before** (`HBM_CONFIG`, ARCH_A/C/D, all old scripts), so old results stay reproducible.

## The question

Is it worth putting magic-state sources on a second layer (HBM) instead of running DASCOT
with them in the data plane? **Metric: space-time volume (STV) only.**

| Name | Spec | What | Role |
|---|---|---|---|
| 2D-Cult-k1 | `D2-wide` | DASCOT with a cultivation patch beside each qubit (own patch, grid grows) | baseline |
| 2D-Cult-k½ | `D2-tight` | DASCOT with 1 patch per 2 qubits, in existing routing tiles | baseline |
| Planar-2D | `D0-alt` | DASCOT's original perimeter: every other tile of the ring around the data block is a magic-state port fed by a factory, the tiles between are free ancillas (4√N + 4 ports) | baseline |
| HBM-Cult-Dedicated, -Shared-2/4/8/16 | `D3-k1`, `D3-s2`, `D3-s4`, `D3-s8`, `D3-s16` | The HBMS paper's configurations, cultivation patches on the top layer: one per data qubit (Dedicated) or one per S data qubits (Shared-S, positions from `architecture.py`, full top routing layer) | proposed |
| HBM-Fact-Dedicated, -Shared-2/4/8/16 | `D3-k1-fact` … `D3-s16-fact` | The same layouts with a factory as each top magic-state qubit (drawn on one top tile, charged 22d²) | proposed |
| PPM | `PPM-<block>` (`ppm_baseline.py`) | Litinski Pauli-product measurements: one data block, cultivation patches at its ancilla region, T gates one at a time (see below) | baseline |

Factories are always ready (one state per port per step), cost 22d² qubits and have error
35p³ (the 15-to-1 block of *A Game of Surface Codes*). Cultivation keeps its recharge time.

Not run (the code still builds them and `test_designs.py` still tests them): D0 `X<m>` and
`Xmax` factory counts, D3 `khalf`, `k2`, `kquarter`, D1 (factories inside the data plane),
D4 (compact plane + cultivation on top), D5 (factories on top with their full footprint; with
Upper-First it does not fit at d=13, rule 5 below).

**Knobs.** Each family is reported at its best knob:
- 2D-Cult: layout (wide, tight). HBM: sharing ratio (Dedicated, Shared-2/4/8/16). Planar-2D: none. PPM: data block, units, source count.
- **Recharge time R (cultivation: 2D-Cult, HBM-Cult, PPM):** 60 and 360 rounds, the two published cultivation grades (table below). Each pair is reported at each R (both sides at the same R) and at R = best (each side at its own best R). R = best matters for T-heavy circuits, where the 60-round grade (3×10⁻⁶ per T state) breaks the 1% target by itself.
- D0 `X<m>` counts (optional, `FACT_SPECS`): `ceil(m·F*)` factories with F\* = ⌈λ⌉, λ = T count / ideal depth (*A Game of Surface Codes* Sec. 4.4). Ports must fit on the ring (36 tiles at N=16 to 164 at N=400); `plan_d0.py` queues only counts that fit, plus `Xmax` (every ring tile) where X2 does not.

**Flags** (`full` phase only): `-borrow` (D2): route in-plane to another qubit's ready patch. `-route` (D3): add a full routing top layer, counted in qubits.

**Routing on the top layer is Upper-First everywhere** (the paper's ARCH_C). A routed T gate goes up above the qubit or above one of its vertical neighbours, then along the top layer to a source. CNOTs stay in the data plane. General 3D routing (`-3d`) is not run.

**The three comparisons** (`scripts/revision/compare.py`), ratio = STV(baseline) / STV(HBM), > 1: HBM wins. Each pair uses the same source on both sides, so only the placement changes:
- **P1:** 2D-Cult (D2) vs HBM-Cult (D3).
- **P2:** Planar-2D (D0-alt) vs HBM-Fact (D3 `-fact`, family `D3F` in `rev.csv`). The HBMS paper's original comparison, with factories always ready on both sides.
- **P3:** PPM vs HBM-Cult (D3). Whether a different compilation model (PPM) makes the top layer unnecessary.

## Parameters and their sources (p = 10⁻³)

| Env var | Default | Source |
|---|---|---|
| `HBM_D` | 13 | data code distance; converts rounds to steps, sizes factories in tiles |
| `HBM_CULT_ROUNDS` | 60 (also run 360) | Tour de gross (arXiv:2506.03094) App. A.6, Table 5, at 6 gate layers per round. d₁=3: 351 layers ≈ 60 rounds, T error 3×10⁻⁶, 454 qubits. d₁=5: 2,167 layers ≈ 360 rounds, 2×10⁻⁹, 463 qubits. Cross-check for d₁=3: Gidney 2025 (arXiv:2505.15917) Sec. 3, 30,000 qubit-rounds per T state / ~512 qubits ≈ 59 rounds. |
| `HBM_FACTORY_ROUNDS` | 0 | Factories are always ready: a port delivers one state per step, the most generous supply for the factory baseline. (43 would model Litinski 2019, arXiv:1905.06903, Table 1, (15-to-1)₁₇,₇,₇: 42.6 cycles per output.) |
| `HBM_FACTORY_QUBITS` | 22d² (3,718 at d=13) | Litinski, *A Game of Surface Codes* (arXiv:1808.02892) Sec. 3.3, p. 14: the 15-to-1 block uses 11 tiles; 2d² qubits per tile (footnote 1, p. 4). Output error 35p³ = 3.5×10⁻⁸ (Sec. 4.1, p. 16; `analyze.py --factory-error`). |
| `HBM_FACTORY_SITES` | 45x51 | Footprint of factories inside the layout (D1, D5; not run). Litinski 2019 Fig. 11: (d_X+4d_Z)×3d_X lattice sites; 4×4 tiles at d=13, 2×3 at d=25. D0 factories sit outside the layout. |

**d₁ vs d:** d₁ is cultivation's internal fault distance. d₁=7 has no published data at p=10⁻³ (Gidney–Shutty–Jones Sec. 3), so it is not modelled. A circuit that needs T states better than 2×10⁻⁹ is marked infeasible for cultivation; distillation (D0) covers that regime.

## Rules every design follows (`design_routing.py`)

1. **Finite sources.** Each source tile holds at most one T state and serves at most one T gate per step. Used at step t, it is ready again at t + 1 + ⌈R/d⌉: R = 60 or 360 for cultivation, R = 0 for factories (always ready).
2. **T gates cost one step,** also when they are direct (no routing).
3. **Direct merges.** A T gate first uses a ready source on its vertical (Z) side or directly above it. Otherwise it routes to any free side of any ready source, if the design allows routing. If no source can serve it, it waits (`magic_wait` stall).
4. **CNOTs** route as in DASCOT: from a vertical neighbour of the control to a horizontal neighbour of the target. Every design leaves each data qubit a free vertical side and a free horizontal side; `wisq/tests/test_designs.py` checks this.
5. **Factory layouts.**
   - **D0:** the square sparse data block plus a ring of output ports around it, each fed by its own factory outside the grid.
   - **D5 (not run):** factories on the top layer. With Upper-First, every data qubit needs a free top tile above itself or a vertical neighbour that connects to a port. Data sits on odd rows, so a factory 4+ tiles tall seals some qubit off. At d=13 a factory is 4×4 tiles, so **D5 does not fit at d=13** (it fits at d=25, 2×3 tiles). The builder checks this and fails immediately.
6. **Qubit accounting.** Tiles at 2d² qubits, factories at 22d² (11 tiles), cultivation patches at 454 or 463 qubits (depending on their grade).

## Outputs

`wisq` JSON as before, plus:
- `arch.design`: spec, parameters, demand λ and F\*, qubit accounting.
- `stats`: steps, direct vs routed T gates, path tiles, vertical merges, stalls (`stall_magic_wait`, `stall_t_blocked`, `stall_cx_blocked`), empty steps.
- `source`: on each T gate, the source tile it consumed.
- Top-layer path tiles are offset by `width * height` (ARCH_D convention).
- Timeout files also contain `arch` and `stats`.

## Analysis (`scripts/revision/`)

- `analyze.py OUT_DIR --csv rev.csv`, one row per run:
  - computes qubits, runtime in rounds, and STV = qubits × rounds at the d the run was simulated at (**d = 13 for every design**, as in the HBMS paper, so designs are compared at the same d);
  - marks runs **infeasible** when the T-state error alone exceeds the target (1%); they get no STV;
  - pairs each cultivation run with its grade (`--cult-grades`, default `60:3e-6:454,360:2e-9:463`);
  - reports the program's logical error at that d (`logical_error`, `meets_target`);
  - for the p′ note only (not in STV): `d_need_1p`, `d_need_5p`, `d_need_10p`, the d the run would need if the vertical links had error p′ = 1, 5, 10 × p. A vertical merge uses the lower threshold the HBMS Stim runs measured for it (`--seam-pth`, default `1:0.01,5:0.004,10:0.002`, paper Fig. 11).
- `compare.py rev.csv [ppm.csv] --prefix rev [--R best|60|360] [--rows]`: best knob per design family; the pair STV ratios at each R and at R = best (`rev_pairs.csv`; `rev_pairs.png` at `--R`, default best); the HBM win fraction per tercile of the x-axis (`rev_regimes.csv`). P1 and P2 use T density as the x-axis, P3 T gates per ideal step. Both sides of a pair are at the same d. A pair is skipped where one side was not run (as opposed to run but infeasible). `--rows` prints every pair with each side's spec, R and steps.
- `ppm_baseline.py BENCH_DIR --csv ppm.csv`: the PPM rows at d = 13 (`--d`; below).
- `ppm_qre.py FILES --csv ppm_qre.csv`: cross-checks the PPM fast block against the Microsoft resource estimator.
- `draw_design.py SPEC N out.png [circuit.qasm]`: draws both layers of a design. `X<m>` counts need the circuit.

## How to run (on the server)

Outputs of configurations no longer in the sweep (D0 `X<m>`/`Xmax`, D3 `khalf`, `k2`,
`kquarter`) would compete as a family's best knob in `analyze.py`/`compare.py`: move them out
of `outs_rev/` first (`mkdir -p test/outs_rev_old && mv test/outs_rev/*/*__D0-X*.out
test/outs_rev/*/*__D3-k{half,2,quarter}__*.out test/outs_rev_old/`).

Every phase submits D0 (4 factory counts) and D2, D3 (2 layouts, 4 k's). Cultivation runs
are queued only where they can change the results:
- An R whose grade alone breaks the 1% target is never run (it is infeasible for any
  design): R = 60 for the p90 circuits (9,900 T gates × 3×10⁻⁶ = 3%). `compare.py` counts
  it as run and infeasible.
- `ROUNDS=best` (default) runs each circuit only at its shortest feasible R. That grade also
  has the fewest qubits (454 vs 463), so it gives the lowest STV, and R = best needs only it.
  `ROUNDS="60 360"` adds the slower R for the per-R comparison (the recharge-time knob).

Each sbatch line covers only the runs not finished yet in any `outs_rev/` suite and not
running now (found through their logs), so the phases overlap and each only adds what is
missing (timed-out and cancelled runs are retried: a killed run leaves no output). The script
refuses to submit while revision tasks are pending, since they would queue twice; cancel them
with `squeue -u $USER -h -r -t PENDING -o '%i %j' | awk '$2 ~ /^rev-/ {print $1}' | xargs -r scancel`.
Add `--dry-run` to print the sbatch lines first.

The Slurm request is set by `PART`, `TIME` (HH:MM:SS), `MEM` and `ACCOUNT` (defaults:
`short`, 4 h for mini; `normal`, 48 h for the others; 8G; p33086). wisq's timeout is `TIME` minus 30 min, so a run
that needs longer leaves a timeout file and the next submission retries it. Shorter requests
start sooner (Slurm backfill), so a cheap order is: everything at `PART=short TIME=04:00:00`,
then the same phase again at the defaults, which submits only what timed out.

1. **Mini** (short partition, < 4 h): `bash test/revision/submit_revision.sh mini`, on `bench_n16_p10` and `bench_n16_p50`.
2. **Pilot** (normal partition, 48 h): `submit_revision.sh pilot`, the 12 circuits with N = 16, 25, 49, 64 (adds `bench_n16_p90`).
3. **Core:** `submit_revision.sh core`, all 33 synthetic circuits.
4. **Full:** `submit_revision.sh full` adds the JKU suite and the `-borrow` / `-route` variants.
5. **After each phase:** `python scripts/revision/analyze.py test/outs_rev --csv rev.csv`, then `python scripts/revision/ppm_baseline.py test/benchmarks_bursty_cx --csv ppm.csv` (seconds), then `python scripts/revision/compare.py rev.csv ppm.csv --prefix rev --rows`.

`smoke_test.sh` (interactive node) is an optional pre-flight check of the same designs on one circuit.

## Not implemented here

- **Cross-layer merge in Stim (E5):** the real seam circuit, with noise only on the vertical CNOTs. Until then, `analyze.py` uses the Stim thresholds above.
- **Routed PPM:** PPM is a formula (Litinski's own cost model), not a routing simulation. No open-source lattice-surgery compiler routes multi-qubit Pauli-product measurements: liblsqecc (Watkins et al., Quantum 2024), the obvious candidate, rejects them (`dense_patch_computation.cpp`: "Multi patch measurement only supports 2 patches currently"), and its QASM front end compiles gate by gate. The formula gives PPM the benefit of the doubt (below).
- **qLDPC comparison:** Tour de gross runs live outside this repo, in `~/qldpc-eval`.

## PPM baseline (reviewer 2's PPM comment)

**What it is.** Litinski, *A Game of Surface Codes* (GoSC, Quantum 3, 128, 2019):
- The Litinski transformation commutes all Cliffords to the end. Every T gate becomes a π/8 rotation about a multi-qubit Pauli product, done by one Pauli-product measurement plus one magic state.
- GoSC p. 4: "A data block combined with a distillation block constitutes a quantum computer in which T gates are performed one after the other". So runtime = T count × steps per rotation (GoSC Sec. 4: "a time proportional to the T count", p. 18).

**Data blocks** (GoSC Sec. 2 summary, p. 9). One step (GoSC's ⏲) = d code cycles, the same as one HBMS step.

| Block | Tiles | Steps per T |
|---|---|---|
| compact | 1.5n + 3 | ≤ 9 |
| intermediate | 2n + 4 (Fig. 13 caption: 2.5n + 4) | ≤ 5 |
| fast | 2n + ⌈√(8n)⌉ + 1 | 1 |

**Sources.** The same cultivation grades and recharge rule as D2 and D3: one state per 1 + ⌈R/d⌉ steps per patch.
- Full supply = ⌈(1 + ⌈R/d⌉) / steps per T⌉ patches, so the block never waits.
- `--source-fracs` also tries ½ and ¼ of that. The block then waits, which mirrors the D3 k sweep.

**Units (GoSC Sec. 5).** Parallel T layers are modelled only as a lower bound on the fast block: u copies, steps = max(T depth, ⌈T/u⌉), u = 1, 2, 4.
- Ignored: the doubled data, the Bell pairs and the correction-qubit storage.
- So at the same d, u units have about the same STV as the sequential fast block (u× the tiles for 1/u of the steps). GoSC p. 24, counting the overheads ignored here: "going from the fast setup to parallelized units is, initially, not a favorable space-time trade-off".

**Benefit of the doubt for PPM:**
- no tiles for wiring the patches to the ancilla region;
- worst case ("up to") only on the compact and intermediate blocks;
- compare.py picks the best PPM row per benchmark.

**Independent check.** `ppm_qre.py` feeds the same counts to the Microsoft Azure Quantum Resource Estimator. Its layout is the GoSC fast block run sequentially: microsoft/qsharp `logical_counts.rs`, logical qubits = 2n + ⌈√(8n)⌉ + 1, depth = T count + rotations + measurements. Logical qubits and depth must equal our fast-block row.

**What to expect (back-of-envelope, d = 13, 2d² = 338 qubits per tile).**
- *Time.* PPM takes T count steps. HBMS takes c × ideal depth steps (c = cost ratio). So runtime ratio PPM/HBMS ≈ λ / c, with λ = T count / ideal depth = T gates per ideal step.
- *Space.* D3-k1 uses ≈ (2√n+1)² tiles + n patches. PPM-fast uses ≈ 2n + √(8n) + 1 tiles + a few patches. Ratio ≈ 2 (n = 16) to 2.4 (n = 100).
- *Result.* The top layer should win STV when λ ≳ 2–2.5·c, and PPM when λ is lower. P3's x-axis is λ for this reason. These are predictions; the runs decide.

**Paper text (draft, Sec. on baselines + discussion).**

> *Pauli-product measurements.* Litinski's Pauli-based compilation [GoSC] removes Clifford gates and runs each T gate as one multi-qubit Pauli-product measurement on a data block. It consumes magic states one after the other (GoSC p. 4). It therefore needs only one magic state per step, which a few sources on the data block's boundary supply. Its runtime is the T count, not the circuit depth.
>
> The vertical layer targets the opposite regime. Lattice-surgery execution keeps the circuit's parallelism and consumes up to λ = T count / depth magic states per step, which a 2D perimeter cannot supply when λ ≫ 1.
>
> We compare both on the same circuits, sources (cultivation, same grades and recharge) and code distance. PPM uses its best data block (compact, intermediate or fast). Its source wiring is free. Fig. X shows the space-time volume ratio against λ:
> - PPM wins for circuits with λ ≲ [measured];
> - the vertical layer wins above it, by up to [measured]×.
>
> GoSC's time-optimal units (Sec. 5) recover T-depth runtime, but only by replicating the fast block. They do not lower space-time volume (GoSC p. 24), so the crossover stands.

## Modelling assumptions to state in the paper

- A source can be oriented to match the boundary it merges with, so direct merges and routed endpoints may use any free side of a source.
- A top-layer source above a data qubit's vertical neighbour is reached through a seam along that qubit's Z edge, without occupying the lower neighbour tile.
- One step = one lattice-surgery merge = d rounds, whatever the path length. Path length affects congestion and error, not time.
- Each factory port holds one state; production restarts when it is taken. This holds for D0.
