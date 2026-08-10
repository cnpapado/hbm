# wisq/ — modified WISQ/DASCOT compiler

Fork of WISQ that adds HBM (High-Bandwidth Magic States) architecture
variants and a generic 3D routing strategy. See the root `CLAUDE.md` for
project context and env-var contract.

## Files under `src/wisq/`

- `__init__.py` — CLI (`main`), `map_and_route()`, HBM_CONFIG → sharing-token
  dispatch that picks the layout function to call.
- `architecture.py` — grid + layout constructors:
  - `square_sparse_layout(n, magic_states=...)`, `compact_layout(...)`.
  - `hbm_shared_{2,4,8,16}_positions(arch)` decide upper-layer magic-state
    positions for each sharing ratio.
  - `vertical_neighbors`, `horizontal_neighbors` — used to enumerate
    Dijkstra endpoint candidates in `sarouting.route_gate`.
- `sarouting.py` — **the routing brain.** `HBM_CONFIG` is parsed once at
  import into a global `HBM_ARCH ∈ {NO_HBM, ARCH_A, ARCH_B, ARCH_C, ARCH_D}`.
  `route_gate` dispatches on `HBM_ARCH` for both T-gates and CNOTs.
  `sim_anneal_route` drives the scheduler.
- `dascot.py` — sdriver: `run_dascot`, `run_sat_scmr`. Sets `signal.SIGALRM`
  for `-tmr`. `dump` serializes `{map, steps, arch, gates}` to JSON.
- `sat_scmr.py` — alternate SAT-based mapping/routing (mostly untouched by
  the HBM changes; DASCOT is the default).
- `phased_graph.py` — builds the initial qubit mapping via `build_phased_map`.
- `guoq.py`, `resynth.py`, `qualtran_rotation_synthesis.py`,
  `optimal_arb_layout.py` — upstream optimization pipeline; not touched.
- `lib/` — vendored external tooling (guoq JARs, synthetiq). **Do not
  modify.**

## HBM_ARCH semantics in `sarouting.route_gate`

The routing operates on two graphs of identical shape:

- `device_graph` — lower/data plane. Occupied lower cells (data qubits +
  routes already claimed this step) live in `to_remove`.
- `hbm_graph` — upper/MS plane. Occupied upper cells (magic-state faces +
  routes claimed this step) live in `to_remove_hbm`.

Per-arch behavior:

| HBM_ARCH | CNOT routing | T-gate routing |
|---|---|---|
| NO_HBM | lower plane | lower plane, targets = perimeter magic-state faces |
| ARCH_A (`shared_none`) | lower plane | not routed (1:1 vertical delivery, MSRD=1) |
| ARCH_B (`route_bottom`) | lower plane | lower plane, then implicit hop up (legacy) |
| ARCH_C (`route_upper`) | lower plane | Upper-First: source = data qubit neighbor, target = MS face neighbor on `hbm_graph` |
| ARCH_D (`route_3d`) | **3D graph, can detour through upper** | **3D graph, elevator up to reach upper-plane MS target** |

### ARCH_D internals

`_build_3d_graph(grid_len, grid_height, to_remove_lower, to_remove_upper)`
constructs a single rustworkx graph with:
- Lower-plane payloads `0 … N-1` (where `N = grid_len * grid_height`).
- Upper-plane payloads `N … 2N-1`.
- In-plane grid edges on each plane (skipping removed cells).
- **Elevator edges** `i ↔ i+N` at every cell where both endpoints exist.

Dijkstra runs on this graph. Endpoints:
- **T-gate**: source = lower-plane neighbor of data qubit; target =
  upper-plane neighbor of any magic-state face (payload `+ N`).
- **CNOT**: source = lower-plane vertical neighbor of `qubits[0]`; target =
  lower-plane horizontal neighbor of `qubits[1]`. Intermediate hops can go
  up/down via elevator edges — CNOTs may detour through the upper plane's
  free ancilla cells.

After routing, each traversed payload is charged: `payload < N` → `to_remove`
(lower); `payload >= N` → `to_remove_hbm` (upper, stripped of the `+ N`
offset). Downstream consumers (`count_steps.py`, `print_timesteps.py`) only
look at `len(steps)` so the `+ N` payload encoding is invisible to them.

## Testing changes

`sim_anneal_route` runs SA reordering within each timestep, so per-gate
routing calls are made hundreds of times per step. When editing
`route_gate`, verify:

1. Smoke test with a small circuit at `--mode scmr -tmr 60` to catch obvious
   crashes fast.
2. Both `ARCH_C` and `ARCH_D` produce the same `len(steps)` on trivial cases
   (e.g. random_q64_d05 — see numbers in root CLAUDE.md's history).
3. `scripts/dependency_scheduling.py --with-cnot-routing` reports a
   reasonable `ideal_w_routing` — huge values mean the router is baking in
   lots of path collisions.

Do **not** edit `lib/` or vendored files.
