# Revision: fair magic-state baselines (designs #0–#5)

Branch `revision/fair-baselines` (based on `feature/generic-3d-routing`). Adds a new design
mode selected with `HBM_DESIGN`. **When `HBM_DESIGN` is unset, wisq behaves exactly as
before** (`HBM_CONFIG`, ARCH_A/C/D, all old scripts), so old results stay reproducible.

## The question

When is it worth putting magic-state sources on a second layer instead of in the data
plane? Each comparison keeps the source the same and changes only where it sits.

| Design | Spec | What | Role |
|---|---|---|---|
| #0 | `D0-S<k>` | square sparse + ring; `ceil(N/k)` ring ports, each fed by a factory outside the grid | baseline |
| #1 | `D1-S<k>` | square sparse with bands of factory blocks between data rows | baseline |
| #2 | `D2-wide`, `D2-tight` | cultivation patch beside each qubit (wide: own patch, grid grows; tight: 1 per 2 qubits in existing routing tiles) | baseline |
| #3 | `D3-k1`, `D3-khalf`, `D3-k2`, `D3-kquarter` | cultivation patches on top of square sparse (k = patches per qubit) | proposed |
| #4 | `D4-k1`, `D4-k1p5` | compact plane + cultivation patches on top | proposed |
| #5 | `D5-S4/S8/S16` | factories on top (current HBMS with real factory footprints) | proposed |

Flags: `-borrow` (D2: route in-plane to another qubit's ready patch), `-route` (D3/D4: add a
full routing top layer, counted in qubits), `-3d` (D5: generic 3D routing for T and CNOT).

The three comparisons (`scripts/revision/compare.py`):

- **P1** cultivation: D2 vs D3: what the top layer buys for cultivation.
- **P2** factories: best of D0/D1 vs D5: what it buys for factories.
- **P3** packing: D2 vs D4: whether the top layer lets the data plane be compact.

## Rules every design follows (`design_routing.py`)

1. **Finite sources.** Each source tile holds at most one T state and serves at most one
   T gate per step. Used at step `t`, it is ready again at `t + 1 + ceil(R/d)`.
   - Cultivation: R = `HBM_CULT_ROUNDS` (default 70).
   - Factory: R = `HBM_FACTORY_ROUNDS` (default 43).
2. **T gates cost one step.** A T gate takes one step, also when it is direct (no routing).
3. **Direct merges.** A T gate first uses a ready source on its vertical (Z) side or directly
   above it (no routing tiles); otherwise it routes to any free side of any ready source, if
   the design allows routing. If no source can serve it, it waits (`magic_wait` stall).
4. **CNOTs** route as in DASCOT: from a vertical neighbour of the control to a horizontal
   neighbour of the target. Every design leaves each data qubit a free vertical side and a
   free horizontal side; `wisq/tests/test_designs.py` checks this.
5. **Real factory footprints.**
   - Factories are `ceil(HBM_FACTORY_QUBITS / 2d²)` tiles (default 4620 qubits = 4 tiles at
     d=25).
   - On top (D5), they must fit around their port without covering the tiles above data
     qubits or their vertical neighbours. If they don't fit, the run fails immediately.
   - 1:1 factories on top do not fit, which is why D5 starts at S4.

Defaults (override per run with env vars):

| Env var | Default | Source |
|---|---|---|
| `HBM_D` | 25 | code distance used to convert rounds to steps and size factories |
| `HBM_CULT_ROUNDS` | 70 | Gidney 2025: ~30000 qubit-rounds per T at 1e-7 on a ~512-qubit patch, + ~10 rounds decoding |
| `HBM_FACTORY_ROUNDS` | 43 | Litinski 2019, (15-to-1)₁₇,₇,₇ at p=1e-3 (verify) |
| `HBM_FACTORY_QUBITS` | 4620 | same |

## Outputs

`wisq` JSON as before, plus:

- `arch.design`: spec, parameters and qubit accounting (tiles per layer, factories, sources).
- `stats`: steps, direct vs routed T gates, path tiles, vertical merges, stalls (`stall_magic_wait`, `stall_t_blocked`, `stall_cx_blocked`), empty steps.
- `source`: on each T gate, the source tile it consumed.
- Top-layer path tiles are offset by `width * height` (ARCH_D convention).
- Timeout files now also contain `arch` and `stats`.

## Analysis (`scripts/revision/`)

- `analyze.py OUT_DIR --csv rev.csv`: for each run and each p′ multiple (1, 5, 10 × p):
  - picks the smallest d that keeps the whole program under the target error (1%);
  - computes qubits, runtime in rounds, and STV = qubits × rounds;
  - marks runs **infeasible** when the T-state error alone exceeds the target (the cultivation fidelity floor);
  - flags `rerun_needed` when d_req changes the recharge steps or factory size used in the simulation. Rerun those with `HBM_D=<d_req>`.
- `compare.py rev.csv --prefix rev`: best setting per design, the three pair ratios vs T density (`rev_pairs.csv`, `rev_pairs.png`), and the win fraction per T-density tercile (`rev_regimes.csv`).
- `draw_design.py SPEC N out.png`: draws both layers of a design.

## How to run (on the server)

1. **Smoke test** (interactive node, a few minutes):
   `bash test/revision/smoke_test.sh`
   Unit tests, a drawing of every design (N=16), every design routed on `bench_n16_p50`, then the analysis. Check the drawings and that every design finishes.
2. **Pilot** (go/no-go, #2 vs #3 on 12 small synthetic circuits, R = 70 and 360):
   `bash test/revision/submit_revision.sh pilot --dry-run` (check), then without `--dry-run`.
   Then `analyze.py` + `compare.py` on `test/outs_rev/`. If D3 never beats D2, stop and rethink before the full sweep.
3. **Core**: `submit_revision.sh core` runs all designs on all synthetic circuits, R ∈ {30, 70, 360}.
4. **Full**: `submit_revision.sh full` adds the JKU suite and the `-borrow` / `-route` / `-3d` variants.
5. Rerun flagged rows at their `d_req`.

## Not implemented here (separate work)

- **Cross-layer merge in Stim (E5):** the real seam circuit with noise only on the vertical CNOTs. `analyze.py` models a seam as one tile at p′ per vertical merge until that circuit exists.
- **Litinski Pauli-product-measurement baseline:** it's a formula, not a simulation.
- **qLDPC comparison:** Tour de gross runs live outside this repo, in `~/qldpc-eval`.

## Modelling assumptions to state in the paper

- A source can be oriented to match the boundary it merges with, so direct merges and
  routed endpoints may use any free side of a source.
- A top-layer source above a data qubit's vertical neighbour is reached through a seam
  along that qubit's Z edge, without occupying the lower neighbour tile.
- One step = one lattice-surgery merge = d rounds, whatever the path length. Path length
  affects congestion and error, not time.
