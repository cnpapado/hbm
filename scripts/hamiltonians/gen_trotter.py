"""
gen_trotter.py
--------------
Write first-order Trotter circuits for the simulation_hamiltonians families, at the
rotation level (rz + Cliffords + cx), small enough to synthesize and route. Synthesize them
to Clifford+T afterwards with synth_ising.py, the same way as benchmarks_real/:

    python scripts/synth_ising.py in.qasm out.qasm --eps 1e-2 --merge

No dependencies beyond the standard library (molecules need a Pauli list from
molecule_paulis.py, which needs PennyLane).

Families, as described for the simulation_hamiltonians source circuits (one Trotter step,
evolution time 1; random weights fixed by --seed, so files are reproducible):
  heisxyz   1D open chain  sum_i a_i XX + b_i YY + c_i ZZ on neighbours, a, b, c ~ U(-1, 1)
  chain     1D open chain of random Pauli interactions: on every three neighbouring qubits
            (i, i+1, i+2) a random Pauli word in {X, Y, Z}^3 with weight ~ U(-1, 1), plus
            X on every qubit with weight 1
  sk        transverse-field Sherrington-Kirkpatrick (TFSK): sum_{i<j} J_ij ZZ, J ~ U(-1, 1),
            plus X on every qubit with weight 1
  surface   rotated surface code (RSC) on a d x d grid of data qubits: its d^2 - 1 X and Z
            check operators (weight 4 in the bulk, 2 on the boundary), weights ~ U(0, 1)
  paulis    any Hamiltonian given as a JSON list of [coefficient, "XIZY..."] (qubit 0 first)

Each term exp(-i c dt P) is a basis change (h for X, sdg h for Y), a CNOT ladder onto the
last qubit of P, rz(2 c dt), and the inverse. Within a step, terms are packed greedily into
layers of disjoint support, so terms on different qubits sit next to each other and can run
in parallel. Any term order is a valid first-order Trotter step; --no-layering keeps the
order the terms are listed in (bond by bond along the chain), which is more serial.

Usage:
  python gen_trotter.py heisxyz --n 10 --steps 1 -o heisxyz_n10_r1.qasm
  python gen_trotter.py chain --n 20 -o chain_n20.qasm
  python gen_trotter.py surface --d 5 --steps 5 -o surface_d5_r5.qasm
  python gen_trotter.py paulis --paulis lih.json --steps 1 -o lih_r1.qasm
"""

import argparse
import json
import random
import sys


def heisxyz(n, rng):
    return n, [(rng.uniform(-1, 1), {i: p, i + 1: p})
               for i in range(n - 1) for p in "XYZ"]


def chain(n, rng):
    terms = [(rng.uniform(-1, 1), {i + k: rng.choice("XYZ") for k in range(3)})
             for i in range(n - 2)]
    terms += [(1.0, {i: "X"}) for i in range(n)]
    return n, terms


def sk(n, rng):
    terms = [(rng.uniform(-1, 1), {i: "Z", j: "Z"})
             for i in range(n) for j in range(i + 1, n)]
    terms += [(1.0, {i: "X"}) for i in range(n)]
    return n, terms


def surface(d, rng):
    q = lambda r, c: r * d + c
    stabs = []
    for r in range(-1, d):
        for c in range(-1, d):
            kind = "X" if (r + c) % 2 == 0 else "Z"
            cells = [(r + a, c + b) for a in (0, 1) for b in (0, 1)
                     if 0 <= r + a < d and 0 <= c + b < d]
            bulk = 0 <= r < d - 1 and 0 <= c < d - 1
            top_bottom = r in (-1, d - 1) and 0 <= c < d - 1 and kind == "X"
            left_right = c in (-1, d - 1) and 0 <= r < d - 1 and kind == "Z"
            if bulk or top_bottom or left_right:
                stabs.append({q(*x): kind for x in cells})
    assert len(stabs) == d * d - 1, len(stabs)
    return d * d, [(rng.uniform(0, 1), s) for s in stabs]


def from_paulis(path):
    with open(path) as f:
        raw = json.load(f)
    n = len(raw[0][1])
    terms = []
    for c, s in raw:
        p = {i: x for i, x in enumerate(s) if x != "I"}
        if p:  # the identity term is a global phase
            terms.append((float(c), p))
    return n, terms


def layers(terms):
    out = []  # [(support, [terms])]
    for t in terms:
        sup = set(t[1])
        for used, group in out:
            if not used & sup:
                used |= sup
                group.append(t)
                break
        else:
            out.append((sup, [t]))
    return [t for _, group in out for t in group]


def emit(c, dt, pauli, lines):
    qs = sorted(pauli)
    pre, post = [], []
    for q in qs:
        if pauli[q] == "X":
            pre.append(f"h q[{q}];")
            post.append(f"h q[{q}];")
        elif pauli[q] == "Y":
            pre += [f"sdg q[{q}];", f"h q[{q}];"]
            post += [f"h q[{q}];", f"s q[{q}];"]
    ladder = [f"cx q[{a}],q[{b}];" for a, b in zip(qs, qs[1:])]
    lines += pre + ladder + [f"rz({2 * c * dt!r}) q[{qs[-1]}];"] + ladder[::-1] + post


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("family", choices=["heisxyz", "chain", "sk", "surface", "paulis"])
    ap.add_argument("--n", type=int, help="qubits (heisxyz, chain, sk)")
    ap.add_argument("--d", type=int, help="code distance (surface)")
    ap.add_argument("--paulis", help="JSON Pauli list (paulis)")
    ap.add_argument("--steps", type=int, default=1, help="Trotter steps (default 1)")
    ap.add_argument("--time", type=float, default=1.0, help="total evolution time (default 1)")
    ap.add_argument("--no-layering", action="store_true", help="keep the listed term order")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    if a.family == "surface":
        n, terms = surface(a.d or sys.exit("--d is required"), rng)
    elif a.family == "paulis":
        n, terms = from_paulis(a.paulis or sys.exit("--paulis is required"))
    else:
        n, terms = globals()[a.family](a.n or sys.exit("--n is required"), rng)
    step = terms if a.no_layering else layers(terms)
    dt = a.time / a.steps
    lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{n}];"]
    for _ in range(a.steps):
        for c, p in step:
            emit(c, dt, p, lines)
    with open(a.output, "w") as f:
        f.write("\n".join(lines) + "\n")
    rz = sum(l.startswith("rz") for l in lines)
    cx = sum(l.startswith("cx") for l in lines)
    print(f"{a.output}: {n} qubits, {len(terms)} terms, {a.steps} steps, {rz} rz, {cx} cx")


if __name__ == "__main__":
    main()
