"""Layout invariants for the revision designs (wisq/src/wisq/designs.py).

Run: python -m pytest -q wisq/tests/test_designs.py
"""

import math

import pytest

from wisq.designs import build_arch, direct_sources, parse_design

SPECS = ["D0-S4", "D0-S8", "D1-S4", "D1-S8", "D1-S16", "D2-wide", "D2-tight", "D2-wide-borrow",
         "D3-k1", "D3-khalf", "D3-k2", "D3-kquarter", "D3-k1-route", "D4-k1", "D4-k1p5",
         "D5-S4", "D5-S8", "D5-S16", "D5-S8-3d"]
SIZES = [16, 25, 49, 100]


def design(spec, **kw):
    params = dict(d=25, cult_rounds=70, factory_rounds=43, factory_qubits=4620)
    params.update(kw)
    return parse_design(spec, **params)


def neighbors(p, w, h):
    r, c = divmod(p, w)
    vert = [x * w + c for x in (r - 1, r + 1) if 0 <= x < h]
    horiz = [r * w + x for x in (c - 1, c + 1) if 0 <= x < w]
    return vert, horiz


@pytest.mark.parametrize("bad", ["D9-S4", "D0", "D0-k1", "D2-medium", "D3-k3", "D5-S3",
                                 "D2-wide-route", "D3-k1-borrow"])
def test_invalid_specs_rejected(bad):
    with pytest.raises(ValueError):
        design(bad)


def test_recharge_steps():
    assert design("D3-k1").recharge_steps == 3  # ceil(70 / 25)
    assert design("D3-k1", cult_rounds=360).recharge_steps == 15
    assert design("D5-S8").recharge_steps == 2  # ceil(43 / 25)
    assert design("D5-S8").factory_tiles == 4  # ceil(4620 / 1250)


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

    # Designs without routing must give every data qubit a direct source.
    if not des.allow_route:
        direct = direct_sources(arch, des)
        assert all(direct[q] for q in data), (spec, n)

    acct = arch["design"]
    assert acct["lower_tiles"] == w * h
    assert acct["n_sources"] == len(sources)


@pytest.mark.parametrize("n", SIZES)
def test_d0_ports_on_ring(n):
    arch = build_arch(design("D0-S4"), n)
    w, h = arch["width"], arch["height"]
    assert len(arch["magic_states"]) == math.ceil(n / 4)
    for p in arch["magic_states"]:
        r, c = divmod(p, w)
        assert r in (0, h - 1) or c in (0, w - 1)


@pytest.mark.parametrize("n", SIZES)
def test_d1_factory_counts(n):
    des = design("D1-S4")
    arch = build_arch(des, n)
    n_fact = math.ceil(n / 4)
    block = 2 * math.ceil(des.factory_tiles / 2)
    assert len(arch["magic_states"]) == n_fact
    assert len(arch["blocked"]) == n_fact * (block - 1)
    assert arch["design"]["lower_factory_tiles"] == n_fact * block


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
def test_d5_factories_leave_access(spec, n):
    des = design(spec)
    arch = build_arch(des, n)
    w, h = arch["width"], arch["height"]
    data = set(arch["alg_qubits"])
    elevators = {v for q in data for v in neighbors(q, w, h)[0]}
    blocked_top = set(arch["blocked_top"])
    assert len(arch["magic_states"]) == math.ceil(n / des.sharing)
    assert not blocked_top & (data | elevators)
    assert len(blocked_top) == len(arch["magic_states"]) * (des.factory_tiles - 1)
    for port in arch["magic_states"]:
        _, horiz = neighbors(port, w, h)
        assert any(x not in blocked_top for x in horiz)


@pytest.mark.parametrize("n", SIZES)
def test_d5_one_factory_per_qubit_does_not_fit(n):
    with pytest.raises(ValueError):
        build_arch(design("D5-S1"), n)


def test_d5_unfit_factory_raises():
    with pytest.raises(ValueError):
        build_arch(design("D5-S4", factory_qubits=200000), 16)
