"""Fair-baseline designs for the revision (designs #0-#5).

A design is selected with the HBM_DESIGN env var. When HBM_DESIGN is unset nothing in
this module is used and the legacy HBM_CONFIG behaviour is unchanged.

Spec grammar ("-"-separated tokens):

  Factory designs need a count token, S<k> or X<m>:
    S<k>   ceil(N/k) factories (fixed sharing ratio).
    X<m>   ceil(m * F*) factories, where F* = ceil(lambda * (1 + ceil(R_f / d))) is the
           break-even count: lambda = T count / ideal depth (the circuit's T demand per step)
           and one factory delivers a state every 1 + ceil(R_f / d) steps. This is
           Litinski's sizing rule (A Game of Surface Codes, Sec. 4.4: add distillation blocks
           until supply matches consumption), applied to the circuit's demand.

  D0-<count>         Edge (baseline; Litinski, A Game of Surface Codes, Sec. 4; "peripheral
                     placement" in Holmes et al. 2019). Square sparse plane plus a ring of
                     output ports, each fed by its own factory outside the grid.
  D1-band-<count>    Factories inside (baseline). Bands of factories between data rows.
  D1-mesh-<count>    Factories inside (baseline; Holmes et al. 2019, Fig. 3b, distributed
                     factories "each responsible for magic-state requests in a sub-region of
                     the lattice"). The data qubits are split into an a x b mesh of near-square
                     sub-regions with one factory at the centre of each.
  D5-<count>[-3d]    Factories on top (proposed). The same a x b mesh on the top layer.
                     A factory covers the top tiles above some data qubits, so T gates route
                     on the two-layer graph: in-plane to any free vertical link, then up
                     (CNOTs stay in-plane; -3d lets CNOTs use the top layer too).

  D2-wide | D2-tight[-borrow]           Cultivation next door (baseline). wide: a patch
                     directly above every data qubit, one extra row per data row; tight: patches
                     replace the routing tiles between pairs of data rows (1 per 2 qubits).
                     -borrow: a T gate may route in-plane to another qubit's ready patch.
  D3-k1 | D3-khalf | D3-k2 | D3-kquarter[-route]   Cultivation on top (proposed).
                     k1: patch above each data qubit; khalf: above the routing tiles between
                     pairs of data rows; k2: above every data qubit and every routing tile on a
                     data qubit's vertical side; kquarter: one per 2x2 data block, reached by a
                     full top routing layer. -route: add that routing layer to k1/k2/khalf.
  D4-k1 | D4-k1p5[-route]                Compact plane + cultivation on top (proposed).

Physical parameters (env vars; defaults are for p = 1e-3):
  HBM_D               data code distance; converts rounds to steps, sizes factories in tiles
                      (default 13).
  HBM_CULT_ROUNDS     mean rounds for one cultivation patch to deliver a kept T state
                      (default 60). Tour de gross (arXiv:2506.03094) App. A.6, Table 5: 351
                      gate layers for d1 = 3 (error 3e-6, 454 qubits) and 2167 for d1 = 5
                      (error 2e-9, 463 qubits), at 6 gate layers per surface-code round
                      (Sec. 3) -> ~60 and ~360 rounds. Cross-check for d1 = 3: Gidney 2025
                      (arXiv:2505.15917) Sec. 3, 30,000 qubit-rounds per T state at 1e-7
                      / ~512 qubits ~= 59 rounds.
  HBM_FACTORY_ROUNDS  rounds between factory outputs (default 43). Litinski 2019
                      (arXiv:1905.06903) Table 1: (15-to-1)_{17,7,7}, the only single-level
                      factory listed at p = 1e-3, 42.6 code cycles, output error 4.5e-8.
  HBM_FACTORY_QUBITS  physical qubits per factory (default 4620, same table).
  HBM_FACTORY_SITES   factory footprint in lattice sites, "WxH" (default 45x51): Litinski
                      2019 Fig. 11, (dX + 4dZ) x 3dX for (15-to-1)_{dX,dZ,dm}. In tiles:
                      ceil(45/d) x ceil(51/d), i.e. 4x4 at d = 13 and 2x3 at d = 25.

One step is one lattice-surgery step of d rounds. A source used at step t is ready again at
t + 1 + ceil(rounds / d).

Lattice-surgery boundary convention (DASCOT): a CNOT runs from a vertical neighbour of the
control to a horizontal neighbour of the target, and a T gate leaves from the data qubit's
vertical (Z) side. Every design leaves each data qubit a free vertical and a free horizontal
side, and "direct" sources (consumed without routing) sit on a data qubit's vertical side or
directly above it.
"""

import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass

from .architecture import hbm_shared_4_positions

FAMILIES = ("D0", "D1", "D2", "D3", "D4", "D5")
FACTORY_FAMILIES = ("D0", "D1", "D5")


@dataclass(frozen=True)
class Design:
    spec: str
    family: str
    knob: str  # reporting label, e.g. "mesh-X1", "X0.5", "k1"
    flags: frozenset
    layout: str  # "square_sparse" | "compact"
    placement: str  # "plane" | "top"
    source: str  # "factory" | "cultivation"
    routing: str  # "PLANE" | "TOP" (Upper-First) | "TOP_3D" (general 3D, opt-in "-3d" only)
    allow_direct: bool
    allow_route: bool
    top_routing_layer: bool
    d: int
    cult_rounds: int
    factory_rounds: int
    factory_qubits: int
    factory_sites: tuple  # (width, height) in lattice sites
    count_mode: str = ""  # "S" | "X" for factory designs
    count_value: float = 0.0
    variant: str = ""  # "band" | "mesh" for D1

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
    def factory_w(self):
        return math.ceil(self.factory_sites[0] / self.d)

    @property
    def factory_h(self):
        return math.ceil(self.factory_sites[1] / self.d)

    @property
    def factory_tiles(self):
        return self.factory_w * self.factory_h


def _env(name, default, cast=int):
    value = os.getenv(name)
    return default if value in (None, "") else cast(value)


def _sites(text):
    w, h = text.lower().split("x")
    return int(w), int(h)


def parse_design(spec, d=None, cult_rounds=None, factory_rounds=None, factory_qubits=None,
                 factory_sites=None):
    """Parse a design spec. Physical parameters default to the HBM_* env vars."""
    tokens = spec.strip().split("-")
    family, rest = tokens[0], tokens[1:]
    if family not in FAMILIES:
        raise ValueError(f"unknown design family {family!r} in {spec!r}")
    params = dict(
        d=d if d is not None else _env("HBM_D", 13),
        cult_rounds=cult_rounds if cult_rounds is not None else _env("HBM_CULT_ROUNDS", 60),
        factory_rounds=(factory_rounds if factory_rounds is not None
                        else _env("HBM_FACTORY_ROUNDS", 43)),
        factory_qubits=(factory_qubits if factory_qubits is not None
                        else _env("HBM_FACTORY_QUBITS", 4620)),
        factory_sites=(factory_sites if factory_sites is not None
                       else _env("HBM_FACTORY_SITES", (45, 51), _sites)),
    )

    if family in FACTORY_FAMILIES:
        counts = [t for t in rest if re.fullmatch(r"S[1-9]\d*|X\d+(\.\d+)?", t)]
        if len(counts) != 1 or (counts[0][0] == "X" and float(counts[0][1:]) <= 0):
            raise ValueError(f"{family} needs exactly one count token S<k> or X<m> (m > 0), "
                             f"got {spec!r}")
        count = counts[0]
        others = [t for t in rest if t != count]
        count_kw = dict(count_mode=count[0], count_value=float(count[1:]))
        if family == "D0":
            if others:
                raise ValueError(f"unexpected tokens {others} in {spec!r}")
            return Design(spec, family, count, frozenset(), "square_sparse", "plane", "factory",
                          "PLANE", allow_direct=True, allow_route=True,
                          top_routing_layer=False, **count_kw, **params)
        if family == "D1":
            variants = [t for t in others if t in ("band", "mesh")]
            if len(variants) != 1 or len(others) != 1:
                raise ValueError(f"D1 needs one layout token, band or mesh, got {spec!r}")
            return Design(spec, family, f"{variants[0]}-{count}", frozenset(), "square_sparse",
                          "plane", "factory", "PLANE", allow_direct=True, allow_route=True,
                          top_routing_layer=False, variant=variants[0], **count_kw, **params)
        # D5
        if set(others) - {"3d"}:
            raise ValueError(f"unexpected tokens {sorted(set(others) - {'3d'})} in {spec!r}")
        return Design(spec, family, count, frozenset(others), "square_sparse", "top", "factory",
                      "TOP_3D" if "3d" in others else "TOP", allow_direct=True,
                      allow_route=True, top_routing_layer=True, **count_kw, **params)

    knob, flags = (rest[0] if rest else ""), frozenset(rest[1:])

    def check(allowed_knobs, allowed_flags):
        if knob not in allowed_knobs:
            raise ValueError(f"{family} knob must be one of {allowed_knobs}, got {spec!r}")
        unknown = flags - set(allowed_flags)
        if unknown:
            raise ValueError(f"flags {sorted(unknown)} not valid for {family} in {spec!r}")

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
    # D4
    check(("k1", "k1p5"), ("route",))
    routed = "route" in flags
    return Design(spec, family, knob, flags, "compact", "top", "cultivation", "TOP",
                  allow_direct=True, allow_route=routed, top_routing_layer=routed, **params)


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
# Factory count
# --------------------------------------------------------------------------------------

def circuit_demand(gates):
    """(T count, ideal depth): depth is the DAG depth over CNOT and T gates."""
    level = defaultdict(int)
    n_t = 0
    for g in gates:
        if len(g) == 1:
            n_t += 1
            level[g[0]] += 1
        else:
            nxt = max(level[g[0]], level[g[1]]) + 1
            level[g[0]] = level[g[1]] = nxt
    return n_t, max(level.values(), default=0)


def factory_count(design, n, gates):
    """Number of factories, plus (lambda, F*) for X<m> counts."""
    if design.count_mode == "S":
        return math.ceil(n / design.count_value), None, None
    if gates is None:
        raise ValueError(f"{design.spec}: X<m> factory counts need the circuit's gates")
    n_t, depth = circuit_demand(gates)
    lam = n_t / depth if depth else 0.0
    f_star = max(1, math.ceil(lam * (1 + design.recharge_steps)))
    return max(1, math.ceil(design.count_value * f_star)), lam, f_star


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


def _grid(row_kinds, col_kinds):
    """A plane from row and column kinds; data sits where a 'D' row meets a 'D' column."""
    width = len(col_kinds)
    alg = [_pos(r, c, width) for r, rk in enumerate(row_kinds) if rk == "D"
           for c, ck in enumerate(col_kinds) if ck == "D"]
    return {"height": len(row_kinds), "width": width, "alg_qubits": alg}


def _square_sparse_kinds(n):
    s = math.ceil(math.sqrt(n))
    kinds = ["R"] + ["D", "R"] * s
    return kinds, list(kinds), s


def _square_sparse(n):
    rows, cols, _ = _square_sparse_kinds(n)
    return _grid(rows, cols)


def _compact(n):
    width = 2 * math.ceil(n / 2) - 1
    return _grid(["D", "R", "D"], ["D" if c % 2 == 0 else "R" for c in range(width)])


def _split(n, k):
    """n items into k groups, sizes as even as possible."""
    return [n // k + (1 if i < n % k else 0) for i in range(k)]


def _spread(items, k):
    """k items picked evenly from a list (0 < k <= len(items))."""
    return [items[int((i + 0.5) * len(items) / k)] for i in range(k)]


def _mesh_shape(f, s):
    """a x b sub-regions with a * b >= f, a, b <= s, least waste, then most square."""
    best = None
    for a in range(1, s + 1):
        b = math.ceil(f / a)
        if b > s:
            continue
        key = (a * b - f, abs(a - b))
        if best is None or key < best[0]:
            best = (key, a, b)
    if best is None:
        raise ValueError(f"{f} factories need more than {s} x {s} sub-regions")
    return best[1], best[2]


def _mesh_slots(a, b, f):
    """The f of the a*b mesh cells that hold a factory (empty cells spread evenly)."""
    cells = [(i, j) for i in range(a) for j in range(b)]
    empty = a * b - f
    skip = set(_spread(cells, empty)) if empty else set()
    return [c for c in cells if c not in skip]


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


def _block(top, left, h, w, width):
    return [_pos(top + dr, left + dc, width) for dr in range(h) for dc in range(w)]


# --------------------------------------------------------------------------------------
# Design builders. Each returns (arch, accounting).
# --------------------------------------------------------------------------------------

def _factory_acct(design, n_fact, lower=0, top=0, top_tiles=0):
    return dict(n_factories=n_fact, n_patches=0, lower_factory_tiles=lower,
                top_tiles=top_tiles, top_factory_tiles=top,
                outside_factory_tiles=0 if (lower or top) else n_fact * design.factory_tiles)


def _cult_acct(n_patches, top_tiles=0):
    return dict(n_factories=0, n_patches=n_patches, lower_factory_tiles=0, top_tiles=top_tiles,
                top_factory_tiles=0, outside_factory_tiles=0)


def _d0_edge(design, n, n_fact):
    """Ports evenly spaced on the ring, starting mid-top. Corner tiles are left out: they
    have only two neighbours and are farthest from the data."""
    arch = _add_ring(_square_sparse(n))
    width, height = arch["width"], arch["height"]
    corners = {_pos(0, 0, width), _pos(0, width - 1, width), _pos(height - 1, 0, width),
               _pos(height - 1, width - 1, width)}
    slots = [p for p in _perimeter_slots(width, height) if p not in corners]
    if n_fact > len(slots):
        raise ValueError(f"{design.spec}: {n_fact} ports do not fit on a ring of "
                         f"{len(slots)} tiles (N={n})")
    start = slots.index(_pos(0, (width - 1) // 2, width))  # middle of the top edge
    slots = slots[start:] + slots[:start]
    ports = sorted({slots[int(i * len(slots) / n_fact)] for i in range(n_fact)})
    arch.update(magic_states=ports, blocked=[], blocked_top=[])
    return arch, _factory_acct(design, len(ports))


def _d1_band(design, n, n_fact):
    """Bands of factories (h rows + 1 routing row) between data rows.

    As many factories per band as fit while keeping >= 1 free column in the middle so
    routes can cross the band. Bands are spread evenly over the gaps between data rows
    (stacking when there are more bands than gaps). Ports are top-edge tiles next to the
    free column, facing the routing row above.
    """
    rows0, cols, s = _square_sparse_kinds(n)
    width = len(cols)
    w, h = design.factory_w, design.factory_h
    per_band = (width - 1) // w
    if per_band < 1:
        raise ValueError(f"{design.spec}: a {w}-tile-wide factory does not fit in a "
                         f"{width}-wide grid (N={n}, d={design.d})")
    n_bands = math.ceil(n_fact / per_band)
    interior = list(range(1, s))
    if n_bands <= len(interior):
        chosen = _spread(interior, n_bands)
    else:
        order = sorted(interior, key=lambda g: abs(g - s / 2)) + [0, s]
        chosen = [order[j % len(order)] for j in range(n_bands)]

    rows = ["R"]
    for g in range(s + 1):  # gap g sits after data row g-1
        rows += (["F"] * h + ["R"]) * chosen.count(g)
        if g < s:
            rows += ["D", "R"]
    arch = _grid(rows, cols)

    left_n = math.ceil(per_band / 2)
    free = width - per_band * w
    starts = [i * w for i in range(left_n)] + [left_n * w + free + i * w
                                                for i in range(per_band - left_n)]
    order, lo, hi = [], 0, per_band - 1  # fill outside-in so partial bands stay symmetric
    while lo <= hi:
        order += [lo] if lo == hi else [lo, hi]
        lo, hi = lo + 1, hi - 1
    band_tops = [r for r in range(len(rows)) if rows[r] == "F" and (r == 0 or rows[r - 1] != "F")]

    ports, blocked, placed = [], [], 0
    for top in band_tops:
        for i in order:
            if placed == n_fact:
                break
            c0 = starts[i]
            port = _pos(top, c0 + w - 1 if i < left_n else c0, width)
            ports.append(port)
            blocked += [t for t in _block(top, c0, h, w, width) if t != port]
            placed += 1
    arch.update(magic_states=sorted(ports), blocked=sorted(blocked), blocked_top=[])
    return arch, _factory_acct(design, placed, lower=placed * w * h)


def _d1_mesh(design, n, n_fact):
    """Holmes et al. 2019 distributed factories: one factory at the centre of each of a x b
    near-square sub-regions of the data qubits.

    A band of factory rows (h rows + 1 routing row) is inserted after the middle data row of
    each sub-region row, and each factory is centred in its sub-region's columns. Sub-regions
    narrower than a factory plus one crossing column get extra routing columns. Ports are the
    factory's top-edge middle tile, facing the routing row next to its data.
    """
    s = math.ceil(math.sqrt(n))
    w, h = design.factory_w, design.factory_h
    a, b = _mesh_shape(n_fact, s)
    cols, spans = ["R"], []
    for k in _split(s, b):
        group = ["D", "R"] * k
        pad = max(0, w + 1 - len(group))
        group = ["R"] * (pad // 2) + group + ["R"] * (pad - pad // 2)
        spans.append((len(cols), len(cols) + len(group)))
        cols += group
    rows, band_tops = ["R"], []
    for m in _split(s, a):
        for i in range(m):
            rows += ["D", "R"]
            if i + 1 == max(1, m // 2):
                band_tops.append(len(rows))
                rows += ["F"] * h + ["R"]
    arch = _grid(rows, cols)
    width = len(cols)

    ports, blocked = [], []
    for i, j in _mesh_slots(a, b, n_fact):
        lo, hi = spans[j]
        c0 = lo + (hi - lo - w) // 2
        port = _pos(band_tops[i], c0 + w // 2, width)
        ports.append(port)
        blocked += [t for t in _block(band_tops[i], c0, h, w, width) if t != port]
    arch.update(magic_states=sorted(ports), blocked=sorted(blocked), blocked_top=[])
    acct = _factory_acct(design, n_fact, lower=n_fact * w * h)
    acct.update(mesh_a=a, mesh_b=b)
    return arch, acct


def _d2_cultivation_plane(design, n):
    if design.knob == "wide":
        _, cols, s = _square_sparse_kinds(n)
        rows = ["R"] + ["P", "D", "R"] * s
        arch = _grid(rows, cols)
        patches = [_pos(r, c, len(cols)) for r, rk in enumerate(rows) if rk == "P"
                   for c, ck in enumerate(cols) if ck == "D"]
    else:  # tight
        arch = _square_sparse(n)
        patches = _paired_row_positions(arch)
    arch.update(magic_states=sorted(patches), blocked=[], blocked_top=[])
    return arch, _cult_acct(len(patches))


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
    return arch, _cult_acct(len(patches), top_tiles)


def _d4_compact_top(design, n):
    arch = _compact(n)
    width = arch["width"]
    patches = list(arch["alg_qubits"])
    if design.knob == "k1p5":
        patches += [_pos(1, c, width) for c in range(0, width, 2)]
    arch.update(magic_states=sorted(set(patches)), blocked=[], blocked_top=[])
    top_tiles = width * arch["height"] if design.top_routing_layer else len(arch["magic_states"])
    return arch, _cult_acct(len(arch["magic_states"]), top_tiles)


def _spread_starts(length, size, k, spec):
    """Start offsets of k blocks of `size` spread evenly over `length`, without overlap."""
    starts = [min(max(0, round((j + 0.5) * length / k - size / 2)), length - size)
              for j in range(k)]
    if any(b < a + size for a, b in zip(starts, starts[1:])) or length < size:
        raise ValueError(f"{spec} does not fit: {k} factories of size {size} in {length} tiles")
    return starts


def _upper_first_rows(ys, h, height, design):
    """Factory row starts that keep Upper-First possible on a square-sparse top layer.

    Upper-First (routing "TOP") enters the top layer above a data qubit or above one of its
    vertical neighbours. Data sits on odd rows, so a factory covering rows r-1, r, r+1 of a
    data row r seals off the qubits below it. Factories of h <= 2 rows never do; h = 3 rows
    must start on a data row; h >= 4 always do, so the design does not fit.
    """
    if h <= 2:
        return ys
    if h > 3:
        raise ValueError(f"{design.spec} does not fit with Upper-First: a factory {h} tiles "
                         f"tall covers the top tiles above some data qubit and both of its "
                         f"vertical neighbours (needs <= 3 rows; d={design.d})")
    out = []
    for y in ys:
        y += 1 - y % 2  # next data (odd) row
        if out:
            y = max(y, out[-1] + h + 1)  # odd + 4: keeps the routing row between free
        if y > height - h:
            raise ValueError(f"{design.spec} does not fit with Upper-First: {len(ys)} rows of "
                             f"factories starting on data rows need more than {height} rows")
        out.append(y)
    return out


def _check_upper_first(design, arch, n):
    """Every data qubit needs a free top tile above itself or a vertical neighbour that is a
    port or reaches one through free top tiles; otherwise its T gates could never run."""
    width, height = arch["width"], arch["height"]
    ports = set(arch["magic_states"])
    free = set(range(width * height)) - set(arch["blocked_top"]) - ports
    reach = {p for p in free if any(x in ports for x in _neighbors(p, width, height))}
    stack = list(reach)
    while stack:
        for x in _neighbors(stack.pop(), width, height):
            if x in free and x not in reach:
                reach.add(x)
                stack.append(x)
    for q in arch["alg_qubits"]:
        if not any(p in ports or p in reach for p in [q] + _vertical_neighbors(q, width, height)):
            raise ValueError(f"{design.spec} does not fit with Upper-First: data qubit at "
                             f"{_rc(q, width)} cannot reach a factory on the top layer "
                             f"(N={n}, d={design.d})")


def _d5_factories_top(design, n, n_fact):
    """The D1 mesh on the top layer: one factory per sub-region, spread evenly.

    T gates use Upper-First (routing "TOP"): up above the qubit or a vertical neighbour, then
    along the top layer to a factory port. Factory rows are placed so that every qubit keeps
    such an entry (see _upper_first_rows). The run fails here if the factories do not fit;
    at d=13 a factory is 4x4 tiles and never fits. The opt-in "-3d" flag (routing TOP_3D)
    skips these Upper-First rules.
    """
    arch = _square_sparse(n)
    width, height = arch["width"], arch["height"]
    s = math.ceil(math.sqrt(n))
    w, h = design.factory_w, design.factory_h
    try:
        a, b = _mesh_shape(n_fact, s)
    except ValueError as e:
        raise ValueError(f"{design.spec} does not fit: {e}") from e
    xs = _spread_starts(width, w, b, design.spec)
    ys = _spread_starts(height, h, a, design.spec)
    if design.routing == "TOP":
        ys = _upper_first_rows(ys, h, height, design)

    blocks = [(ys[i], xs[j]) for i, j in _mesh_slots(a, b, n_fact)]
    taken = {t for top, left in blocks for t in _block(top, left, h, w, width)}
    ports, blocked = [], []
    for top, left in blocks:
        # Port: the middle tile of an edge (top, bottom, left, right) whose outside neighbour
        # is free, so the port can be reached.
        candidates = [((top, left + w // 2), (top - 1, left + w // 2)),
                      ((top + h - 1, left + w // 2), (top + h, left + w // 2)),
                      ((top + h // 2, left), (top + h // 2, left - 1)),
                      ((top + h // 2, left + w - 1), (top + h // 2, left + w))]
        port = None
        for (pr, pc), (orow, ocol) in candidates:
            if 0 <= orow < height and 0 <= ocol < width and _pos(orow, ocol, width) not in taken:
                port = _pos(pr, pc, width)
                break
        if port is None:
            raise ValueError(f"{design.spec} does not fit: factory at ({top}, {left}) has no "
                             f"free side for its port (N={n}, d={design.d})")
        ports.append(port)
        blocked += [t for t in _block(top, left, h, w, width) if t != port]
    arch.update(magic_states=sorted(ports), blocked=[], blocked_top=sorted(blocked))
    if design.routing == "TOP":
        _check_upper_first(design, arch, n)
    acct = _factory_acct(design, n_fact, top=n_fact * w * h, top_tiles=width * height)
    acct.update(mesh_a=a, mesh_b=b)
    return arch, acct


def build_arch(design, n_qubits, gates=None):
    """Build the architecture dict for a design.

    gates (list of qubit tuples) is needed for X<m> factory counts. Keys: height, width,
    alg_qubits, magic_states (source tiles: lower-plane positions for plane designs,
    top-layer positions for top designs), blocked (lower tiles occupied by factories),
    blocked_top (top tiles occupied by factories), design (parameters and accounting).
    """
    lam = f_star = None
    if design.source == "factory":
        n_fact, lam, f_star = factory_count(design, n_qubits, gates)
        builder = {"D0": _d0_edge, "D5": _d5_factories_top}.get(design.family)
        if design.family == "D1":
            builder = _d1_mesh if design.variant == "mesh" else _d1_band
        arch, acct = builder(design, n_qubits, n_fact)
    else:
        builder = {"D2": _d2_cultivation_plane, "D3": _d3_cultivation_top,
                   "D4": _d4_compact_top}[design.family]
        arch, acct = builder(design, n_qubits)
    if not arch["magic_states"]:
        raise ValueError(f"{design.spec}: no magic-state sources for N={n_qubits}")
    arch["design"] = dict(
        spec=design.spec, family=design.family, knob=design.knob, flags=sorted(design.flags),
        variant=design.variant, layout=design.layout, placement=design.placement,
        source=design.source, routing=design.routing, allow_direct=design.allow_direct,
        allow_route=design.allow_route, top_routing_layer=design.top_routing_layer,
        d=design.d, recharge_rounds=design.recharge_rounds,
        recharge_steps=design.recharge_steps, cult_rounds=design.cult_rounds,
        factory_qubits=design.factory_qubits, factory_rounds=design.factory_rounds,
        factory_sites=list(design.factory_sites), factory_w=design.factory_w,
        factory_h=design.factory_h, factory_tiles=design.factory_tiles,
        tile_qubits=design.tile_qubits, count_mode=design.count_mode,
        count_value=design.count_value, demand_lambda=lam, f_star=f_star,
        n_logical=n_qubits, n_sources=len(arch["magic_states"]),
        lower_tiles=arch["width"] * arch["height"], **acct,
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
