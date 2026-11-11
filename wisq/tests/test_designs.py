"""Layout and sizing rules for the revision designs (wisq/src/wisq/designs.py).

Run: python -m pytest -q wisq/tests/test_designs.py
"""

import math

import pytest

from wisq.designs import (SHARED, build_arch, d0_ring_capacity, direct_sources, factory_count,
                          parse_design)

SPECS = ["D0-S4", "D0-S8", "D1-band-S4", "D1-band-S8", "D1-mesh-S4", "D1-mesh-S8",
         "D2-wide", "D2-tight", "D2-wide-borrow", "D3-k1", "D3-khalf", "D3-k2", "D3-kquarter",
         "D3-k1-route", "D4-k1", "D4-k1p5", "D5-S4", "D5-S8", "D5-S16", "D5-S8-3d",
         "D0-alt", "D3-s2", "D3-s4", "D3-s8", "D3-s16", "D3-k1-fact", "D3-s4-fact", "D3-s4-fact-bottom",
         "D3-s4-fact-active", "D3-s8-fact-bottom-active", "D3-rows", "D3-rows-bottom",
         "D3-ancilla-bottom", "D3-full-bottom"]
SIZES = [16, 25, 49, 100]


def design(spec, **kw):
    params = dict(d=25, cult_rounds=60, factory_rounds=43, factory_qubits=4620,
                  factory_sites=(45, 51))
    params.update(kw)
    return parse_design(spec, **params)


def neighbors(p, w, h):
    r, c = divmod(p, w)
    vert = [x * w + c for x in (r - 1, r + 1) if 0 <= x < h]
    horiz = [r * w + x for x in (c - 1, c + 1) if 0 <= x < w]
    return vert, horiz


@pytest.mark.parametrize("bad", ["D9-S4", "D0", "D0-k1", "D0-S4-X1", "D1-S4", "D1-grid-S4",
                                 "D1-band-mesh-S4", "D2-medium", "D3-k3", "D5-S0", "D5-X0",
                                 "D2-wide-route", "D3-k1-borrow", "D5-S4-route",
                                 "D1-band-Xmax", "D5-Xmax", "D0-Xmax-S4", "D1-band-alt",
                                 "D0-alt-X1", "D3-s3", "D2-wide-fact",
                                 "D3-k1-fact-bottom", "D2-wide-bottom",
                                 "D3-k1-fact-active", "D3-kquarter-active", "D2-wide-active",
                                 "D3-ancilla", "D3-rows-active", "D3-full"])
def test_invalid_specs_rejected(bad):
    with pytest.raises(ValueError):
        design(bad)


def test_recharge_and_footprint():
    # Cultivation grades (Tour de gross App. A.6): 60 and 360 rounds.
    assert design("D3-k1", d=13).recharge_steps == 5  # ceil(60 / 13)
    assert design("D3-k1", d=13, cult_rounds=360).recharge_steps == 28
    # (15-to-1)_{17,7,7}: 42.6 cycles, 45 x 51 lattice sites (Litinski 2019 Table 1, Fig. 11).
    assert design("D5-S8", d=13).recharge_steps == 4  # ceil(43 / 13)
    assert (design("D5-S8", d=13).factory_w, design("D5-S8", d=13).factory_h) == (4, 4)
    assert (design("D5-S8").factory_w, design("D5-S8").factory_h) == (2, 3)  # d = 25


def test_factory_count_from_demand():
    gates = [(0,)] * 10  # 10 T gates on one qubit: T count 10, ideal depth 10, lambda = 1
    expected = {"X1": 3, "X0.5": 2, "X2": 6, "X0.25": 1}  # F* = ceil(1 * (1 + ceil(43/25)))
    for token, n_fact in expected.items():
        count, lam, f_star = factory_count(design(f"D0-{token}"), 16, gates)
        assert (count, lam, f_star) == (n_fact, 1.0, 3)
    assert factory_count(design("D0-S4"), 16, None)[0] == 4


def test_factory_defaults(monkeypatch):
    # Factories are always ready and cost 22 d^2 (GoSC 15-to-1 block: 11 tiles of 2 d^2).
    for var in ("HBM_FACTORY_ROUNDS", "HBM_FACTORY_QUBITS"):
        monkeypatch.delenv(var, raising=False)
    des = parse_design("D0-X1", d=13)
    assert des.recharge_steps == 0 and des.factory_qubits == 22 * 13 * 13
    gates = [(0,)] * 10  # lambda = 1 -> F* = ceil(1 * (1 + 0)) = 1
    assert factory_count(des, 16, gates) == (1, 1.0, 1)


def test_x_count_needs_the_circuit():
    with pytest.raises(ValueError):
        build_arch(design("D0-X1"), 16)


def test_d0_ring_capacity_and_xmax():
    # N=16: square sparse 9x9 plus a ring -> 11x11, 40 ring tiles minus 4 corners.
    assert d0_ring_capacity(16) == 36
    assert build_arch(design("D0-Xmax"), 16)["design"]["n_factories"] == 36
    gates = [(0,)] * 100  # lambda = 1 at one qubit; F* = 3 at d = 25
    arch = build_arch(design("D0-Xmax"), 16, gates=gates)
    assert arch["design"]["n_factories"] == 36 and arch["design"]["f_star"] == 3
    heavy = [(q,) for q in range(16)] * 13  # lambda = 208 / 13 = 16 -> F* = 48 > 36 ports
    with pytest.raises(ValueError):
        build_arch(design("D0-X1"), 16, gates=heavy)
    assert build_arch(design("D0-Xmax"), 16, gates=heavy)["design"]["n_factories"] == 36


@pytest.mark.parametrize("spec", SPECS)
@pytest.mark.parametrize("n", SIZES)
def test_layout_invariants(spec, n):
    des = design(spec)
    arch = build_arch(des, n)
    w, h = arch["width"], arch["height"]
    data = arch["alg_qubits"]
    sources = arch["magic_states"]
    blocked, blocked_top = set(arch["blocked"]), set(arch["blocked_top"])

    assert len(data) >= n and len(set(data)) == len(data)
    assert all(0 <= p < w * h for p in data + sources + list(blocked) + list(blocked_top))
    assert sources and len(set(sources)) == len(sources)
    assert not blocked & set(data)
    assert not blocked_top & set(sources)
    if des.placement == "plane":
        assert not set(sources) & set(data)
        assert not blocked & set(sources)

    # Every data qubit keeps a free vertical side (CNOT control / T exit) and a free
    # horizontal side (CNOT target) on the lower plane.
    lower_taken = set(data) | blocked | (set(sources) if des.placement == "plane" else set())
    for q in data:
        vert, horiz = neighbors(q, w, h)
        assert any(v not in lower_taken for v in vert), (spec, n, q, "no free vertical side")
        assert any(x not in lower_taken for x in horiz), (spec, n, q, "no free horizontal side")

    # Every source can be reached: a free neighbour on its own layer (bottom routing: some
    # source has a free tile below it to merge down into).
    taken = (set(data) | blocked | set(sources)) if des.placement == "plane" else (
        blocked_top | set(sources))
    if des.allow_route and des.routing == "BOTTOM":
        assert any(p not in lower_taken for p in sources), (spec, n, "no source above a free tile")
    elif des.allow_route:
        for p in sources:
            vert, horiz = neighbors(p, w, h)
            assert any(x not in taken for x in vert + horiz), (spec, n, p, "unreachable source")

    # Designs without routing must give every data qubit a direct source.
    if not des.allow_route:
        direct = direct_sources(arch, des)
        assert all(direct[q] for q in data), (spec, n)

    acct = arch["design"]
    assert acct["lower_tiles"] == w * h
    assert acct["n_sources"] == len(sources)
    if des.source == "cultivation":
        assert acct["n_patches"] == len(sources) and acct["n_factories"] == 0
    else:
        assert acct["n_factories"] == len(sources) and acct["n_patches"] == 0
        if des.count_mode == "S":
            assert len(sources) == math.ceil(n / des.count_value)


@pytest.mark.parametrize("n", SIZES)
def test_d0_ports_on_ring(n):
    arch = build_arch(design("D0-S4"), n)
    w, h = arch["width"], arch["height"]
    for p in arch["magic_states"]:
        r, c = divmod(p, w)
        assert r in (0, h - 1) or c in (0, w - 1)


@pytest.mark.parametrize("n", SIZES)
def test_d0_alt_every_other_ring_tile(n):
    # DASCOT's perimeter (Planar-2D): every other ring tile is a port, 4 sqrt(N) + 4 of them.
    arch = build_arch(design("D0-alt"), n)
    w, h = arch["width"], arch["height"]
    ports = set(arch["magic_states"])
    assert len(ports) == 4 * math.isqrt(n) + 4
    corners = {0, w - 1, (h - 1) * w, h * w - 1}
    assert not ports & corners
    for p in ports:
        r, c = divmod(p, w)
        assert r in (0, h - 1) or c in (0, w - 1)
        vert, horiz = neighbors(p, w, h)
        assert not set(vert + horiz) & ports  # a free ancilla tile between any two ports


@pytest.mark.parametrize("knob", ["s2", "s4", "s8", "s16"])
@pytest.mark.parametrize("n", SIZES)
def test_d3_shared_matches_the_paper(knob, n):
    # HBMS paper's Shared-S: architecture.py's positions on a full top routing layer.
    arch = build_arch(design(f"D3-{knob}"), n)
    want = sorted(set(SHARED[knob]({k: arch[k] for k in ("width", "height", "alg_qubits")})))
    assert arch["magic_states"] == want
    acct = arch["design"]
    assert acct["top_tiles"] == arch["width"] * arch["height"]
    assert acct["n_patches"] == len(want) and acct["routing"] == "TOP"


def test_d3_fact_sources_are_factories():
    arch = build_arch(design("D3-s4-fact", d=13, factory_qubits=22 * 13 * 13), 16)
    acct = arch["design"]
    assert acct["source"] == "factory" and acct["n_factories"] == 4 == acct["top_factory_tiles"]
    assert acct["n_patches"] == 0 and acct["factory_qubits"] == 3718
    assert build_arch(design("D3-k1-fact"), 16)["design"]["n_factories"] == 16


@pytest.mark.parametrize("knob", ["s2", "s4", "s8", "s16"])
@pytest.mark.parametrize("n", SIZES)
def test_d3_bottom_drops_the_top_routing_layer(knob, n):
    # Same factories as Shared-S, but routed in the data plane: the top layer is factories only.
    top = build_arch(design(f"D3-{knob}-fact"), n)
    arch = build_arch(design(f"D3-{knob}-fact-bottom"), n)
    acct = arch["design"]
    assert arch["magic_states"] == top["magic_states"]
    assert acct["routing"] == "BOTTOM" and acct["allow_route"]
    assert not acct["top_routing_layer"] and acct["top_tiles"] == len(arch["magic_states"])


def test_bottom_routes_in_plane_to_the_tile_below_a_factory():
    from wisq import design_routing as dr

    des = design("D3-s16-fact-bottom", factory_rounds=0)
    arch = build_arch(des, 16)
    (f,) = arch["magic_states"]
    far = max(arch["alg_qubits"], key=lambda q: abs(q - f))
    dr.begin(des, arch, {0: far})
    step = dr.try_order([0], {7: (0,)})
    (_, _, path), = step
    assert path and path[-1] == f and all(p < arch["width"] * arch["height"] for p in path)
    dr.commit(step, {7: (0,)})
    s = dr.stats()
    assert s["t_routed"] == 1 and s["vertical_merges"] == 1 and s["t_path_tiles"] == len(path)



@pytest.mark.parametrize("knob", ["s2", "s4", "s8", "s16"])
@pytest.mark.parametrize("n", [10, 13, 16, 20, 25, 26, 34, 49, 64, 66, 100])
def test_d3_active_counts_sources_per_qubit_in_use(knob, n):
    # ceil(N / S) distinct sources for the N qubits in use, on top, wherever the grid pads N.
    arch = build_arch(design(f"D3-{knob}-fact-active"), n)
    ms = arch["magic_states"]
    assert len(ms) == len(set(ms)) == math.ceil(n / int(knob[1:]))
    assert all(0 <= p < arch["width"] * arch["height"] for p in ms)
    assert arch["design"]["n_factories"] == len(ms)
    full = build_arch(design(f"D3-{knob}-fact"), n)
    assert (arch["width"], arch["height"], arch["alg_qubits"]) == (
        full["width"], full["height"], full["alg_qubits"])


@pytest.mark.parametrize("spec", ["D3-rows", "D3-rows-bottom"])
def test_d3_rows_routes_to_a_neighbouring_patch_while_its_own_recharges(spec):
    from wisq import design_routing as dr

    des = design(spec)
    arch = build_arch(des, 16)
    q = arch["alg_qubits"][5]
    dr.begin(des, arch, {0: q})
    for t, mode in ((0, "direct"), (1, "routed")):
        dr.CTX.t = t
        step = dr.try_order([0], {7: (0,)})
        assert len(step) == 1 and step.state.mode[7] == mode
        dr.commit(step, {7: (0,)})
    (_, _, path), = step
    n = arch["width"] * arch["height"]
    assert path and (all(p >= n for p in path) if spec == "D3-rows" else all(p < n for p in path))


@pytest.mark.parametrize("n", [10, 16, 26, 49, 66])
def test_d3_rows_fills_the_data_rows_on_top(n):
    # A patch on every top tile of the odd (data) rows: one above each data qubit plus the
    # tiles between, ~2 per qubit; the even rows are the top routing layer.
    arch = build_arch(design("D3-rows"), n)
    w, h = arch["width"], arch["height"]
    ms = set(arch["magic_states"])
    assert ms == {r * w + c for r in range(1, h, 2) for c in range(w)}
    assert set(arch["alg_qubits"]) <= ms
    assert arch["design"]["n_patches"] == len(ms) == (h // 2) * w
    assert arch["design"]["top_tiles"] == w * h
    assert build_arch(design("D3-rows-bottom"), n)["design"]["top_tiles"] == len(ms)


@pytest.mark.parametrize("n", [10, 16, 26, 49, 66])
def test_d3_ancilla_puts_a_patch_above_every_routing_tile(n):
    arch = build_arch(design("D3-ancilla-bottom"), n)
    w, h = arch["width"], arch["height"]
    ms = set(arch["magic_states"])
    assert ms == set(range(w * h)) - set(arch["alg_qubits"])
    assert arch["design"]["routing"] == "BOTTOM" and arch["design"]["top_tiles"] == len(ms)


def test_d3_full_patch_above_a_data_qubit_serves_only_that_qubit():
    from wisq import design_routing as dr

    des = design("D3-full-bottom")
    arch = build_arch(des, 16)
    assert set(arch["magic_states"]) == set(range(arch["width"] * arch["height"]))
    q, other = arch["alg_qubits"][5], arch["alg_qubits"][6]
    dr.begin(des, arch, {0: q, 1: other})
    seen = set()
    for t in range(12):  # keep qubit 1 consuming; it must never take the patch above q
        dr.CTX.t = t
        step = dr.try_order([0], {7: (1,)})
        dr.commit(step, {7: (1,)})
        if step:
            seen.add(step.state.face_of[7])
    assert q not in seen and other in seen


def test_d3_ancilla_uses_both_vertical_sides_then_routes():
    # Patches above both vertical neighbours are direct; with both recharging, route in-plane.
    from wisq import design_routing as dr

    des = design("D3-ancilla-bottom")
    arch = build_arch(des, 16)
    dr.begin(des, arch, {0: arch["alg_qubits"][5]})
    for t, mode in ((0, "direct"), (1, "direct"), (2, "routed")):
        dr.CTX.t = t
        step = dr.try_order([0], {7: (0,)})
        assert len(step) == 1 and step.state.mode[7] == mode
        dr.commit(step, {7: (0,)})


@pytest.mark.parametrize("variant", ["band", "mesh"])
@pytest.mark.parametrize("n", SIZES)
def test_d1_factory_footprints(variant, n):
    des = design(f"D1-{variant}-S4")
    arch = build_arch(des, n)
    n_fact = math.ceil(n / 4)
    assert len(arch["blocked"]) == n_fact * (des.factory_tiles - 1)
    assert arch["design"]["lower_factory_tiles"] == n_fact * des.factory_tiles
    if variant == "mesh":
        acct = arch["design"]
        assert acct["mesh_a"] * acct["mesh_b"] >= n_fact


@pytest.mark.parametrize("n", SIZES)
def test_d2_tight_one_patch_per_qubit_side(n):
    arch = build_arch(design("D2-tight"), n)
    w, h = arch["width"], arch["height"]
    sources = set(arch["magic_states"])
    for q in arch["alg_qubits"]:
        vert, _ = neighbors(q, w, h)
        assert sum(v in sources for v in vert) == 1


@pytest.mark.parametrize("spec", ["D5-S4", "D5-S8", "D5-S16"])
@pytest.mark.parametrize("n", SIZES)
def test_d5_factories_on_top(spec, n):
    des = design(spec)
    arch = build_arch(des, n)
    blocked_top = set(arch["blocked_top"])
    assert len(arch["magic_states"]) == math.ceil(n / des.count_value)
    assert len(blocked_top) == len(arch["magic_states"]) * (des.factory_tiles - 1)
    assert arch["design"]["top_factory_tiles"] == len(arch["magic_states"]) * des.factory_tiles
    # Upper-First: every data qubit can go up above itself or a vertical neighbour.
    w, h = arch["width"], arch["height"]
    for q in arch["alg_qubits"]:
        vert, _ = neighbors(q, w, h)
        assert any(p not in blocked_top for p in [q] + vert), (spec, n, q, "sealed off")


def test_d5_upper_first_rejects_tall_factories():
    # d=13: a factory is 4x4 tiles, which always covers some data qubit's tile and both of its
    # vertical neighbours' tiles on the top layer, so Upper-First cannot reach a factory.
    with pytest.raises(ValueError, match="Upper-First"):
        build_arch(design("D5-S8", d=13), 16)


@pytest.mark.parametrize("n", SIZES)
def test_d5_one_factory_per_qubit_does_not_fit(n):
    with pytest.raises(ValueError):
        build_arch(design("D5-S1"), n)


def test_d5_unfit_factory_raises():
    with pytest.raises(ValueError):
        build_arch(design("D5-S4", factory_sites=(200, 200)), 16)
