# Revision: fair magic-state baselines (designs #0–#5)

Branch `revision/fair-baselines` (based on `feature/generic-3d-routing`). Adds a new design
mode selected with `HBM_DESIGN`. **When `HBM_DESIGN` is unset, wisq behaves exactly as
before** (`HBM_CONFIG`, ARCH_A/C/D, all old scripts), so old results stay reproducible.

## The question

When is it worth putting magic-state sources on a second layer instead of in the data
plane? Each comparison keeps the source the same and changes only where it sits.

| Design | Spec | What | Role |
|---|---|---|---|
| #0 | `D0-<count>` | factories beside the data block, feeding ports on a ring around it (Litinski, *A Game of Surface Codes* Sec. 4; "peripheral placement" in Holmes et al. 2019) | baseline |
| #1 | `D1-band-<count>`, `D1-mesh-<count>` | factories inside the data plane. **mesh** = Holmes et al. 2019 Fig. 3b distributed factories, one at the centre of each of a×b sub-regions. **band** = bands between data rows. Both are run; the better counts as the baseline. | baseline |
| #2 | `D2-wide`, `D2-tight` | cultivation patch beside each qubit (wide: own patch, grid grows; tight: 1 per 2 qubits in existing routing tiles) | baseline |
| #3 | `D3-k1`, `D3-khalf`, `D3-k2`, `D3-kquarter` | cultivation patches on top of square sparse (k = patches per qubit) | proposed |
| #4 | `D4-k1`, `D4-k1p5` | compact plane + cultivation patches on top | proposed |
| #5 | `D5-<count>` | factories on top: the D1 mesh on the top layer | proposed |
| PPM | `PPM-<block>` (`ppm_baseline.py`) | Litinski Pauli-product measurements: one data block, cultivation patches at its ancilla region, T gates one at a time (see below) | baseline |

**Factory count `<count>`:**
- `X<m>`: `ceil(m·F*)` factories, where F\* is the break-even count for the circuit's T demand.
  - F\* = ⌈λ·(1 + ⌈R_f/d⌉)⌉, with λ = T count / ideal depth.
  - This is Litinski's sizing rule (*A Game of Surface Codes* Sec. 4.4: add distillation blocks until supply matches consumption), applied to the circuit's demand.
  - The sweep uses m ∈ {¼, ½, 1, 2} and reports each design at its best.
- `S<k>`: a fixed `ceil(N/k)` factories (kept for tests).

**Flags:**
- `-borrow` (D2): route in-plane to another qubit's ready patch.
- `-route` (D3/D4): add a full routing top layer, counted in qubits.
- `-3d` (D5): CNOTs may also use the top layer.

**The four comparisons** (`scripts/revision/compare.py`):
- **P1, cultivation:** D2 vs D3. What the top layer buys for cultivation.
- **P2, factories:** best of D0/D1 vs D5. What it buys for factories.
- **P3, packing:** D2 vs D4. Whether the top layer lets the data plane be compact.
- **P4, PPM:** best PPM block vs best of D3/D4. Whether a different compilation model (PPM) makes the top layer unnecessary.

## Parameters and their sources (p = 10⁻³)

| Env var | Default | Source |
|---|---|---|
| `HBM_D` | 13 | data code distance; converts rounds to steps, sizes factories in tiles |
| `HBM_CULT_ROUNDS` | 60 (also run 360) | Tour de gross (arXiv:2506.03094) App. A.6, Table 5, at 6 gate layers per round. d₁=3: 351 layers ≈ 60 rounds, T error 3×10⁻⁶, 454 qubits. d₁=5: 2,167 layers ≈ 360 rounds, 2×10⁻⁹, 463 qubits. Cross-check for d₁=3: Gidney 2025 (arXiv:2505.15917) Sec. 3, 30,000 qubit-rounds per T state / ~512 qubits ≈ 59 rounds. |
| `HBM_FACTORY_ROUNDS` | 43 | Litinski 2019 (arXiv:1905.06903) Table 1: (15-to-1)₁₇,₇,₇, the only single-level factory listed at p=10⁻³. 42.6 cycles per output, output error 4.5×10⁻⁸. |
| `HBM_FACTORY_QUBITS` | 4620 | same table |
| `HBM_FACTORY_SITES` | 45x51 | Litinski 2019 Fig. 11: (d_X+4d_Z)×3d_X lattice sites. In tiles: ⌈45/d⌉×⌈51/d⌉, i.e. 4×4 at d=13 and 2×3 at d=25. |

**d₁ vs d:** d₁ is cultivation's internal fault distance. d₁=7 has no published data at p=10⁻³ (Gidney–Shutty–Jones Sec. 3), so it is not modelled. A circuit that needs T states better than 2×10⁻⁹ is marked infeasible for cultivation; distillation (D0/D1/D5) covers that regime.

## Rules every design follows (`design_routing.py`)

1. **Finite sources.** Each source tile holds at most one T state and serves at most one T gate per step. Used at step t, it is ready again at t + 1 + ⌈R/d⌉.
2. **T gates cost one step,** also when they are direct (no routing).
3. **Direct merges.** A T gate first uses a ready source on its vertical (Z) side or directly above it. Otherwise it routes to any free side of any ready source, if the design allows routing. If no source can serve it, it waits (`magic_wait` stall).
4. **CNOTs** route as in DASCOT: from a vertical neighbour of the control to a horizontal neighbour of the target. Every design leaves each data qubit a free vertical side and a free horizontal side; `wisq/tests/test_designs.py` checks this.
5. **Factory layouts.**
   - **D1-band:** bands of factories (h rows + 1 routing row) between data rows, as many per band as fit while keeping a free middle column so routes can cross. Bands are spread evenly over the gaps between data rows.
   - **D1-mesh:** the data qubits are split into a×b near-square sub-regions (a·b ≥ F, as square as possible, empty cells spread evenly). A factory sits at the centre of each sub-region. Sub-regions narrower than a factory plus a crossing column get extra routing columns.
   - **D5:** the same mesh on the top layer, without extra columns: the top layer has the data plane's footprint. A near-square factory necessarily covers the top tiles above some data qubits, so T gates use the two-layer graph: in-plane to any free vertical link, then up. A D5 run fails immediately if its factories don't fit (`D5-S1` never does; at d=13 a factory is 4×4 tiles, so small chips only fit a few). Not fitting is a result for P2, not a bug.
6. **Qubit accounting.** Tiles at 2d² qubits, factories at 4,620 qubits, cultivation patches at 454 or 463 qubits (depending on their grade).

## Outputs

`wisq` JSON as before, plus:
- `arch.design`: spec, parameters, demand λ and F\*, qubit accounting.
- `stats`: steps, direct vs routed T gates, path tiles, vertical merges, stalls (`stall_magic_wait`, `stall_t_blocked`, `stall_cx_blocked`), empty steps.
- `source`: on each T gate, the source tile it consumed.
- Top-layer path tiles are offset by `width * height` (ARCH_D convention).
- Timeout files also contain `arch` and `stats`.

## Analysis (`scripts/revision/`)

- `analyze.py OUT_DIR --csv rev.csv`, for each run and each p′ multiple (1, 5, 10 × p):
  - picks the smallest d that keeps the whole program under the target error (1%);
  - computes qubits, runtime in rounds, and STV = qubits × rounds;
  - marks runs **infeasible** when the T-state error alone exceeds the target;
  - models a vertical merge with the lower threshold your Stim runs measured for it (`--seam-pth`, default `1:0.01,5:0.004,10:0.002`, HBMS paper Fig. 11);
  - pairs each cultivation run with its grade (`--cult-grades`, default `60:3e-6:454,360:2e-9:463`);
  - flags `rerun_needed` when d_req changes the recharge steps or factory size used in the simulation.
- `make_reruns.py rev.csv > revision/reruns.sh` (run from `test/`): writes sbatch arrays that rerun flagged rows at their d_req.
- `compare.py rev.csv [ppm.csv] --prefix rev --R 60`: best setting per design family, the pair ratios (`rev_pairs.csv`, `rev_pairs.png`), and the win fraction per tercile (`rev_regimes.csv`). P1–P3 use T density as the x-axis; P4 uses T gates per ideal step. With `ppm.csv` it also writes `rev_ppm.png` (P4 split into STV, runtime and qubit ratios). It prefers runs simulated at their own d_req and marks pairs that still use a mismatched run as `provisional`. A pair is skipped where one side was not run (as opposed to run but infeasible).
- `ppm_baseline.py BENCH_DIR --csv ppm.csv`: the PPM rows (below).
- `ppm_qre.py FILES --csv ppm_qre.csv`: cross-checks the PPM fast block against the Microsoft resource estimator.
- `draw_design.py SPEC N out.png [circuit.qasm]`: draws both layers of a design. `X<m>` counts need the circuit.

## How to run (on the server)

1. **Smoke test** (interactive node): `bash test/revision/smoke_test.sh`. It runs the unit tests, draws every design for N=16, routes `bench_n16_p50` with every design, then runs the analysis. It uses d=25 because it only checks code paths.
2. **Pilot** (go/no-go: D2 vs D3 on 12 small synthetic circuits, R = 60 and 360): `bash test/revision/submit_revision.sh pilot --dry-run`, then again without `--dry-run`. Then run `analyze.py` + `compare.py` on `test/outs_rev/`.
3. **Core:** `submit_revision.sh core` runs all designs on all synthetic circuits.
4. **Full:** `submit_revision.sh full` adds the JKU suite and the `-borrow` / `-route` / `-3d` variants.
5. **Reruns:** `cd test && python ../scripts/revision/make_reruns.py rev.csv > revision/reruns.sh && bash revision/reruns.sh`, then rerun `analyze.py` + `compare.py`.
6. **PPM (P4):** seconds, no Slurm. `python scripts/revision/ppm_baseline.py test/benchmarks_bursty_cx --csv ppm.csv`, then `python scripts/revision/compare.py rev.csv ppm.csv --prefix rev`. Cross-check once: `python scripts/revision/ppm_qre.py test/benchmarks_bursty_cx` on a laptop (needs `pip install "qsharp>=1.0"`, whose Linux wheels need glibc ≥ 2.31; on the cluster pip falls back to the broken legacy IQ# package). Every row must print `match`.

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

**Sources.** The same cultivation grades and recharge rule as D2–D4: one state per 1 + ⌈R/d⌉ steps per patch.
- Full supply = ⌈(1 + ⌈R/d⌉) / steps per T⌉ patches, so the block never waits.
- `--source-fracs` also tries ½ and ¼ of that. The block then waits, which mirrors the D3 k sweep.

**Units (GoSC Sec. 5).** Parallel T layers are modelled only as a lower bound on the fast block: u copies, steps = max(T depth, ⌈T/u⌉), u = 1, 2, 4.
- Ignored: the doubled data, the Bell pairs and the correction-qubit storage.
- So their STV never drops below the sequential fast block's. GoSC p. 24 agrees: "going from the fast setup to parallelized units is, initially, not a favorable space-time trade-off".

**Benefit of the doubt for PPM:**
- no tiles for wiring the patches to the ancilla region;
- no error charged for ancilla-region merges;
- worst case ("up to") only on the compact and intermediate blocks;
- compare.py picks the best PPM row per benchmark.

**Independent check.** `ppm_qre.py` feeds the same counts to the Microsoft Azure Quantum Resource Estimator. Its layout is the GoSC fast block run sequentially: microsoft/qsharp `logical_counts.rs`, logical qubits = 2n + ⌈√(8n)⌉ + 1, depth = T count + rotations + measurements. Logical qubits and depth must equal our fast-block row.

**What to expect (back-of-envelope, d = 13, 2d² = 338 qubits per tile).**
- *Time.* PPM takes T count steps. HBMS takes c × ideal depth steps (c = cost ratio). So runtime ratio PPM/HBMS ≈ λ / c, with λ = T count / ideal depth = T gates per ideal step.
- *Space.* D3-k1 uses ≈ (2√n+1)² tiles + n patches. PPM-fast uses ≈ 2n + √(8n) + 1 tiles + a few patches. Ratio ≈ 2 (n = 16) to 2.4 (n = 100).
- *Result.* The top layer should win STV when λ ≳ 2–2.5·c, and PPM when λ is lower. P4's x-axis is λ for this reason. These are predictions; the runs decide.

**Paper text (draft, Sec. on baselines + discussion).**

> *Pauli-product measurements.* Litinski's Pauli-based compilation [GoSC] removes Clifford gates and runs each T gate as one multi-qubit Pauli-product measurement on a data block. It consumes magic states one after the other (GoSC p. 4). It therefore needs only one magic state per step, which a few sources on the data block's boundary supply. Its runtime is the T count, not the circuit depth.
>
> The vertical layer targets the opposite regime. Lattice-surgery execution keeps the circuit's parallelism and consumes up to λ = T count / depth magic states per step, which a 2D perimeter cannot supply when λ ≫ 1.
>
> We compare both on the same circuits, sources (cultivation, same grades and recharge) and error model. PPM uses its best data block (compact, intermediate or fast). Its source wiring and ancilla merges are free. Fig. X shows the space-time volume ratio against λ:
> - PPM wins for circuits with λ ≲ [measured];
> - the vertical layer wins above it, by up to [measured]×.
>
> GoSC's time-optimal units (Sec. 5) recover T-depth runtime, but only by replicating the fast block. They do not lower space-time volume (GoSC p. 24), so the crossover in volume stands; in runtime, units need [measured]× more qubits to match the vertical layer.

## Modelling assumptions to state in the paper

- A source can be oriented to match the boundary it merges with, so direct merges and routed endpoints may use any free side of a source.
- A top-layer source above a data qubit's vertical neighbour is reached through a seam along that qubit's Z edge, without occupying the lower neighbour tile.
- One step = one lattice-surgery merge = d rounds, whatever the path length. Path length affects congestion and error, not time.
- Each factory port holds one state; production restarts when it is taken. This holds equally for D0, D1 and D5.
