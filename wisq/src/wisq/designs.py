"""Fair-baseline designs for the revision (designs #0-#5).

A design is selected with the HBM_DESIGN env var. When HBM_DESIGN is unset nothing in
this module is used and the legacy HBM_CONFIG behaviour is unchanged.

Spec grammar: "<family>-<knob>[-<flag>...]"

  D0-S<k>     Edge (baseline). Square sparse plane plus a ring; ceil(N/k) output ports on
              the ring, each fed by its own distillation factory outside the grid.
  D1-S<k>     Factories inside (baseline). Square sparse plane with bands of factory blocks
              between data rows; ceil(N/k) factories, each with one output port.
  D2-wide     Cultivation next door (baseline). One cultivation patch directly above every
              data qubit; one extra row per data row keeps the routing channels.
  D2-tight    Cultivation next door, shared (baseline). Patches replace the routing tiles
              between pairs of data rows: one patch per 2 data qubits, no extra area.
  D3-k1       Cultivation on top (proposed). A patch directly above every data qubit.
  D3-khalf    Patches above the routing tiles between pairs of data rows (1 per 2 qubits).
  D3-k2       Patches above every data qubit and above every routing tile that touches a
              data qubit's vertical (Z) side.
  D3-kquarter One patch per 2x2 data block (shared_4 positions), reached by routing on a
              full top routing layer.
  D4-k1       Compact plane + a cultivation patch above every data qubit (proposed).
  D4-k1p5     D4-k1 plus patches above the routing tile shared by the two data rows.
  D5-S<k>     Factories on top (proposed; the current HBMS with real factory footprints).
              Ports at the shared_<k> positions, Upper-First routing on the top layer.

Flags:
  -borrow     (D2) a T gate whose own patch is recharging may route in-plane to any other
              ready patch.
  -route      (D3-k1/k2/khalf, D4) add a full routing top layer (counted in the qubit total)
              so a T gate may route on top to any ready patch.
  -3d         (D5) generic 3D routing (as ARCH_D) for T gates and CNOTs.

Physical parameters (env vars, all optional):
  HBM_D                 code distance used to convert rounds to timesteps (default 25)
  HBM_CULT_ROUNDS       rounds for a cultivation patch to produce its next T state, decoder wait
                        included (default 70; Gidney 2025: ~30000 qubit-rounds per T at 1e-7 on
                        a ~512-qubit patch, plus ~10 rounds of decoding)
  HBM_FACTORY_ROUNDS    rounds between factory outputs (default 43; Litinski 2019,
                        (15-to-1)_{17,7,7} at p=1e-3 -- verify against the table)
  HBM_FACTORY_QUBITS    physical qubits per factory (default 4620, same source)

One timestep is one lattice-surgery step of d rounds. A source used at timestep t is
ready again at t + 1 + ceil(rounds / d).

Lattice-surgery boundary convention (DASCOT): a CNOT runs from a vertical neighbour of the
control to a horizontal neighbour of the target, and a T gate leaves from the data qubit's
vertical (Z) side. Every design therefore leaves each data qubit at least one free vertical
side, and "direct" sources (consumed without routing) sit on a data qubit's vertical side or
directly above it.
"""

import math
import os
from dataclasses import dataclass

from .architecture import (
    hbm_shared_2_positions,
    hbm_shared_4_positions,
    hbm_shared_8_positions,
    hbm_shared_16_positions,
)

FAMILIES = ("D0", "D1", "D2", "D3", "D4", "D5")
SHARED_POSITIONS = {
    2: hbm_shared_2_positions,
    4: hbm_shared_4_positions,
    8: hbm_shared_8_positions,
    16: hbm_shared_16_positions,
}


@dataclass(frozen=True)
class Design:
    spec: str
    family: str
    knob: str
    flags: frozenset
    layout: str  # "square_sparse" | "compact"
    placement: str  # "plane" | "top"
    source: str  # "factory" | "cultivation"
    routing: str  # "PLANE" | "TOP" | "TOP_3D"
    allow_direct: bool
    allow_route: bool
    top_routing_layer: bool
    d: int
    cult_rounds: int
    factory_rounds: int
    factory_qubits: int
    sharing: int = 0  # k in "S<k>" for factory designs

    @property
    def recharge_rounds(self):
        return self.cult_rounds if self.source == "cultivation" else self.factory_rounds

    @property
    def recharge_steps(self):
        return math.ceil(self.recharge_rounds / self.d)

    @property
    def tile_qubits(self):
        return 2 * self.d * self.d

    @property
    def factory_tiles(self):
        return math.ceil(self.factory_qubits / self.tile_qubits)


def _env_int(name, default):
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


def parse_design(spec, d=None, cult_rounds=None, factory_rounds=None, factory_qubits=None):
    """Parse a design spec. Physical parameters default to the HBM_* env vars."""
    parts = spec.strip().split("-")
    family, knob, flags = parts[0], (parts[1] if len(parts) > 1 else ""), frozenset(parts[2:])
    if family not in FAMILIES:
        raise ValueError(f"unknown design family {family!r} in {spec!r}")
    params = dict(
        d=d if d is not None else _env_int("HBM_D", 25),
        cult_rounds=cult_rounds if cult_rounds is not None else _env_int("HBM_CULT_ROUNDS", 70),
        factory_rounds=(factory_rounds if factory_rounds is not None
                        else _env_int("HBM_FACTORY_ROUNDS", 43)),
        factory_qubits=(factory_qubits if factory_qubits is not None
                        else _env_int("HBM_FACTORY_QUBITS", 4620)),
    )

    def sharing():
        if not knob.startswith("S") or not knob[1:].isdigit() or int(knob[1:]) < 1:
            raise ValueError(f"{family} needs a knob S<k> with k >= 1, got {spec!r}")
        return int(knob[1:])

    def check(allowed_knobs, allowed_flags):
        if allowed_knobs is not None and knob not in allowed_knobs:
            raise ValueError(f"{family} knob must be one of {allowed_knobs}, got {spec!r}")
        unknown = flags - set(allowed_flags)
        if unknown:
            raise ValueError(f"flags {sorted(unknown)} not valid for {family} in {spec!r}")

    if family in ("D0", "D1"):
        check(None, ())
        return Design(spec, family, knob, flags, "square_sparse", "plane", "factory", "PLANE",
                      allow_direct=True, allow_route=True, top_routing_layer=False,
                      sharing=sharing(), **params)
    if family == "D2":
        check(("wide", "tight"), ("borrow",))
        return Design(spec, family, knob, flags, "square_sparse", "plane", "cultivation",
                      "PLANE", allow_direct=True, allow_route="borrow" in flags,
                      top_routing_layer=False, **params)
    if family == "D3":
        check(("k1", "k2", "khalf", "kquarter"), ("route",))
        routed = knob == "kquarter" or "route" in flags
        return Design(spec, family, knob, flags, "square_sparse", "top", "cultivation", "TOP",
                      allow_direct=True, allow_route=routed, top_routing_layer=routed, **params)
    if family == "D4":
        check(("k1", "k1p5"), ("route",))
        routed = "route" in flags
        return Design(spec, family, knob, flags, "compact", "top", "cultivation", "TOP",
                      allow_direct=True, allow_route=routed, top_routing_layer=routed, **params)
    # D5
    check(None, ("3d",))
    k = sharing()
    if k not in SHARED_POSITIONS:
        raise ValueError(f"D5 supports S2/S4/S8/S16 (the shared_<k> positions), got {spec!r}")
    return Design(spec, family, knob, flags, "square_sparse", "top", "factory",
                  "TOP_3D" if "3d" in flags else "TOP", allow_direct=True, allow_route=True,
                  top_routing_layer=True, sharing=k, **params)


_DESIGN_CACHE = {}


def get_design():
    """The design selected by HBM_DESIGN, or None (legacy HBM_CONFIG mode)."""
    spec = os.getenv("HBM_DESIGN")
    if not spec:
        return None
    if spec not in _DESIGN_CACHE:
        _DESIGN_CACHE[spec] = parse_design(spec)
    return _DESIGN_CACHE[spec]


# --------------------------------------------------------------------------------------
# Grid helpers. Positions are row-major indices: pos = row * width + col.
# --------------------------------------------------------------------------------------

def _rc(pos, width):
    return divmod(pos, width)


def _pos(row, col, width):
    return row * width + col


def _vertical_neighbors(pos, width, height):
    row, col = _rc(pos, width)
    return [_pos(r, col, width) for r in (row - 1, row + 1) if 0 <= r < height]


def _horizontal_neighbors(pos, width, height):
    row, col = _rc(pos, width)
    return [_pos(row, c, width) for c in (col - 1, col + 1) if 0 <= c < width]


def _neighbors(pos, width, height):
    return _vertical_neighbors(pos, width, height) + _horizontal_neighbors(pos, width, height)


def _grid_from_rows(row_kinds, width, data_cols):
    """Build a plane from a list of row kinds. 'D' rows hold data at data_cols."""
    alg = []
    for r, kind in enumerate(row_kinds):
        if kind == "D":
            alg.extend(_pos(r, c, width) for c in data_cols)
    return {"height": len(row_kinds), "width": width, "alg_qubits": alg}


def _square_sparse_rows(n):
    s = math.ceil(math.sqrt(n))
    return ["R"] + ["D", "R"] * s, 2 * s + 1, list(range(1, 2 * s, 2))


def _square_sparse(n):
    rows, width, data_cols = _square_sparse_rows(n)
    return _grid_from_rows(rows, width, data_cols)


def _compact(n):
    width = 2 * math.ceil(n / 2) - 1
    data_cols = list(range(0, width, 2))
    return _grid_from_rows(["D", "R", "D"], width, data_cols)


def _paired_row_positions(arch):
    """Positions in the routing row between each pair of data rows (1st&2nd, 3rd&4th, ...).

    Each data qubit then has one vertical side on such a row and keeps the other free. A
    leftover last data row gets its down-neighbour row (or up-neighbour if there is none).
    Positions are at data columns.
    """
    width = arch["width"]
    by_row = {}
    for q in arch["alg_qubits"]:
        r, c = _rc(q, width)
        by_row.setdefault(r, []).append(c)
    rows = sorted(by_row)
    out = []
    for i in range(0, len(rows), 2):
        if i + 1 < len(rows):
            between = (rows[i] + rows[i + 1]) // 2
            cols = sorted(set(by_row[rows[i]]) | set(by_row[rows[i + 1]]))
            out.extend(_pos(between, c, width) for c in cols)
        else:
            r = rows[i]
            target = r + 1 if r + 1 < arch["height"] else r - 1
            out.extend(_pos(target, c, width) for c in by_row[r])
    return sorted(set(out))


def _perimeter_slots(width, height):
    top = [_pos(0, c, width) for c in range(width)]
    right = [_pos(r, width - 1, width) for r in range(1, height)]
    bottom = [_pos(height - 1, c, width) for c in range(width - 2, -1, -1)]
    left = [_pos(r, 0, width) for r in range(height - 2, 0, -1)]
    return top + right + bottom + left


def _add_ring(arch):
    w, h = arch["width"], arch["height"]
    shift = lambda p: _pos(p // w + 1, p % w + 1, w + 2)  # noqa: E731
    return {"height": h + 2, "width": w + 2, "alg_qubits": [shift(q) for q in arch["alg_qubits"]]}


# --------------------------------------------------------------------------------------
# Design builders
# --------------------------------------------------------------------------------------

def _d0_edge(design, n):
    arch = _add_ring(_square_sparse(n))
    slots = _perimeter_slots(arch["width"], arch["height"])
    n_ports = math.ceil(n / design.sharing)
    if n_ports > len(slots):
        raise ValueError(f"{design.spec}: {n_ports} ports do not fit on a ring of "
                         f"{len(slots)} tiles")
    step = len(slots) / n_ports
    ports = sorted({slots[int(i * step)] for i in range(n_ports)})
    arch.update(magic_states=ports, blocked=[], blocked_top=[])
    acct = dict(n_factories=len(ports), lower_factory_tiles=0, top_tiles=0, top_factory_tiles=0,
                outside_factory_tiles=len(ports) * design.factory_tiles)
    return arch, acct


def _d1_inside(design, n):
    rows, width, data_cols = _square_sparse_rows(n)
    s = len(data_cols)
    n_fact = math.ceil(n / design.sharing)
    block_w = math.ceil(design.factory_tiles / 2)  # blocks are 2 rows tall
    per_band = (width - 2) // block_w  # columns 0 and width-1 stay free for routing
    if per_band < 1:
        raise ValueError(f"{design.spec}: a {design.factory_tiles}-tile factory does not fit "
                         f"in a {width}-wide grid")
    n_bands = math.ceil(n_fact / per_band)

    # Distribute bands over the s+1 gaps around data rows: interior gaps first (closest to
    # the middle first), then the top and bottom edges; wrap around if more bands remain.
    order = sorted(range(1, s), key=lambda g: abs(g - s / 2)) + [0, s]
    bands_at = {}
    for i in range(n_bands):
        g = order[i % len(order)]
        bands_at[g] = bands_at.get(g, 0) + 1

    # Row sequence: gap g sits after the routing row that follows data row g-1.
    seq = ["R"]
    for g in range(s + 1):
        seq += ["F", "F", "R"] * bands_at.get(g, 0)
        if g < s:
            seq += ["D", "R"]
    arch = _grid_from_rows(seq, width, data_cols)

    ports, blocked, placed = [], [], 0
    band_tops = [r for r in range(len(seq) - 1) if seq[r] == "F" and seq[r + 1] == "F"
                 and (r == 0 or seq[r - 1] != "F")]
    for top in band_tops:
        for j in range(per_band):
            if placed == n_fact:
                break
            c0 = 1 + j * block_w
            tiles = [_pos(top + dr, c0 + dc, width) for dr in (0, 1) for dc in range(block_w)]
            port = _pos(top if placed % 2 == 0 else top + 1, c0, width)
            ports.append(port)
            blocked.extend(t for t in tiles if t != port)
            placed += 1
    arch.update(magic_states=sorted(ports), blocked=sorted(blocked), blocked_top=[])
    acct = dict(n_factories=placed, lower_factory_tiles=placed * 2 * block_w, top_tiles=0,
                top_factory_tiles=0, outside_factory_tiles=0)
    return arch, acct


def _d2_cultivation_plane(design, n):
    if design.knob == "wide":
        rows, width, data_cols = _square_sparse_rows(n)
        seq = ["R"] + ["P", "D", "R"] * len(data_cols)
        arch = _grid_from_rows(seq, width, data_cols)
        patches = [_pos(r, c, width) for r, kind in enumerate(seq) if kind == "P"
                   for c in data_cols]
    else:  # tight
        arch = _square_sparse(n)
        patches = _paired_row_positions(arch)
    arch.update(magic_states=sorted(patches), blocked=[], blocked_top=[])
    acct = dict(n_factories=0, lower_factory_tiles=0, top_tiles=0, top_factory_tiles=0,
                outside_factory_tiles=0)
    return arch, acct


def _d3_cultivation_top(design, n):
    arch = _square_sparse(n)
    width, height = arch["width"], arch["height"]
    data = arch["alg_qubits"]
    if design.knob == "k1":
        patches = list(data)
    elif design.knob == "khalf":
        patches = _paired_row_positions(arch)
    elif design.knob == "k2":
        side = {v for q in data for v in _vertical_neighbors(q, width, height)}
        patches = sorted(set(data) | side)
    else:  # kquarter
        patches = hbm_shared_4_positions(arch)
    arch.update(magic_states=sorted(patches), blocked=[], blocked_top=[])
    top_tiles = width * height if design.top_routing_layer else len(patches)
    acct = dict(n_factories=0, lower_factory_tiles=0, top_tiles=top_tiles, top_factory_tiles=0,
                outside_factory_tiles=0)
    return arch, acct


def _d4_compact_top(design, n):
    arch = _compact(n)
    width = arch["width"]
    patches = list(arch["alg_qubits"])
    if design.knob == "k1p5":
        patches += [_pos(1, c, width) for c in range(0, width, 2)]
    arch.update(magic_states=sorted(set(patches)), blocked=[], blocked_top=[])
    top_tiles = width * arch["height"] if design.top_routing_layer else len(arch["magic_states"])
    acct = dict(n_factories=0, lower_factory_tiles=0, top_tiles=top_tiles, top_factory_tiles=0,
                outside_factory_tiles=0)
    return arch, acct


def _d5_factories_top(design, n):
    arch = _square_sparse(n)
    width, height = arch["width"], arch["height"]
    ports = SHARED_POSITIONS[design.sharing](arch)
    data = set(arch["alg_qubits"])
    elevators = {v for q in data for v in _vertical_neighbors(q, width, height)}
    port_access = {h for p in ports for h in _horizontal_neighbors(p, width, height)}
    reserved = data | elevators | set(ports) | port_access

    # Grow each factory from its port by BFS over top tiles that are not reserved: tiles
    # above data qubits and their vertical neighbours stay free so every qubit can reach the
    # top layer, and each port keeps its horizontal neighbours free so it can be reached.
    taken, blocked_top = set(), []
    need = design.factory_tiles - 1
    for port in ports:
        frontier, seen, mine = [port], {port}, []
        while frontier and len(mine) < need:
            nxt = []
            for p in frontier:
                for nb in _neighbors(p, width, height):
                    if nb in seen:
                        continue
                    seen.add(nb)
                    if nb in reserved or nb in taken:
                        continue
                    mine.append(nb)
                    nxt.append(nb)
                    if len(mine) == need:
                        break
                if len(mine) == need:
                    break
            frontier = nxt
        if len(mine) < need:
            raise ValueError(
                f"{design.spec} does not fit: a {design.factory_tiles}-tile factory cannot be "
                f"placed on the top layer next to port {port} (N={n}, d={design.d}). Use a "
                f"larger sharing ratio or a smaller factory.")
        taken.update(mine)
        blocked_top.extend(mine)
    arch.update(magic_states=sorted(ports), blocked=[], blocked_top=sorted(blocked_top))
    acct = dict(n_factories=len(ports), lower_factory_tiles=0, top_tiles=width * height,
                top_factory_tiles=len(ports) * design.factory_tiles, outside_factory_tiles=0)
    return arch, acct


BUILDERS = {
    "D0": _d0_edge,
    "D1": _d1_inside,
    "D2": _d2_cultivation_plane,
    "D3": _d3_cultivation_top,
    "D4": _d4_compact_top,
    "D5": _d5_factories_top,
}


def build_arch(design, n_qubits):
    """Build the architecture dict for a design.

    Keys: height, width, alg_qubits, magic_states (source tiles: lower-plane positions for
    plane designs, top-layer positions for top designs), blocked (lower tiles occupied by
    factories), blocked_top (top tiles occupied by factories), design (accounting).
    """
    arch, acct = BUILDERS[design.family](design, n_qubits)
    if not arch["magic_states"]:
        raise ValueError(f"{design.spec}: no magic-state sources for N={n_qubits}")
    lower_tiles = arch["width"] * arch["height"]
    arch["design"] = dict(
        spec=design.spec, family=design.family, knob=design.knob, flags=sorted(design.flags),
        layout=design.layout, placement=design.placement, source=design.source,
        routing=design.routing, allow_direct=design.allow_direct,
        allow_route=design.allow_route, top_routing_layer=design.top_routing_layer,
        d=design.d, recharge_rounds=design.recharge_rounds,
        recharge_steps=design.recharge_steps, factory_qubits=design.factory_qubits,
        factory_rounds=design.factory_rounds, factory_tiles=design.factory_tiles,
        cult_rounds=design.cult_rounds, tile_qubits=design.tile_qubits,
        n_logical=n_qubits, n_sources=len(arch["magic_states"]),
        lower_tiles=lower_tiles, **acct,
    )
    return arch


def direct_sources(arch, design):
    """Map each data position to the source tiles it can consume without routing.

    Plane designs: sources on the data qubit's vertical (Z) side. Top designs: the source
    directly above the qubit first, then sources above its vertical neighbours.
    """
    width, height = arch["width"], arch["height"]
    sources = set(arch["magic_states"])
    out = {}
    for q in arch["alg_qubits"]:
        if design.placement == "plane":
            cand = _vertical_neighbors(q, width, height)
        else:
            cand = [q] + _vertical_neighbors(q, width, height)
        out[q] = [p for p in cand if p in sources]
    return out
