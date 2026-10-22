"""Generate first-order Trotter circuits for the Fermi-Hubbard model in Clifford+Rz OpenQASM 2.0.

    H = -t * sum_<ij>,s (a+_is a_js + h.c.)  +  U * sum_i n_i,up n_i,down

Jordan-Wigner encoding, spin-blocked: qubit = site + spin * n_sites, sites in snake order on 2D lattices
(horizontal bonds have no Z string, vertical bonds carry one). Open boundaries.

Two term orderings for the same Hamiltonian:
  parallel   - bonds are grouped into layers whose JW supports are disjoint; each hopping term
               exp(-i b (XZ..ZX + YZ..ZY)) is one gadget with its two Rz rotations on both endpoints
               at once; the on-site layer applies Rz on every qubit, then all ZZ gadgets.
  sequential - every Pauli string gets its own CX-ladder gadget, emitted bond by bond
               (the style of the FTCircuitBench Hamiltonian circuits).

Usage:
    python gen_fermi_hubbard.py --lattice 1d --sites 8 --steps 1 --order parallel -o out.qasm
    python gen_fermi_hubbard.py --batch            # regenerate this directory's circuits
    python gen_fermi_hubbard.py --verify           # statevector check of the gadgets
"""
import argparse
import cmath
import math
import os
import random


# ---------------------------------------------------------
# Lattice and Hamiltonian terms
# ---------------------------------------------------------
def snake_index(x, y, lx):
    return y * lx + (x if y % 2 == 0 else lx - 1 - x)


def lattice_bonds(lattice, lx, ly):
    """Return (n_sites, list of (r_i, r_j)) with r in JW order."""
    if lattice == "1d":
        return lx, [(i, i + 1) for i in range(lx - 1)]
    bonds = []
    for y in range(ly):
        for x in range(lx):
            r = snake_index(x, y, lx)
            if x + 1 < lx:
                bonds.append((r, snake_index(x + 1, y, lx)))
            if y + 1 < ly:
                bonds.append((r, snake_index(x, y + 1, lx)))
    return lx * ly, [tuple(sorted(b)) for b in bonds]


def color_bonds(bonds):
    """Greedy interval coloring: bonds in one layer have disjoint JW intervals [i, j]."""
    layers = []
    for b in sorted(bonds, key=lambda b: (b[1] - b[0], b[0])):
        for layer in layers:
            if all(b[1] < c[0] or c[1] < b[0] for c in layer):
                layer.append(b)
                break
        else:
            layers.append([b])
    return layers


# ---------------------------------------------------------
# Gate emission
# ---------------------------------------------------------
class Circuit:
    def __init__(self, n):
        self.n = n
        self.ops = []  # (name, qubits, angle)

    def g(self, name, *qs, angle=None):
        self.ops.append((name, qs, angle))

    def qasm(self):
        lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{self.n}];"]
        for name, qs, angle in self.ops:
            args = ",".join(f"q[{q}]" for q in qs)
            lines.append(f"{name}({angle:.12f}) {args};" if angle is not None else f"{name} {args};")
        return "\n".join(lines) + "\n"


def parity_ladder(c, string, sink, undo=False):
    """CX chain folding the Z-parity of `string` onto `sink` (the last string qubit)."""
    pairs = [(string[k], string[k + 1]) for k in range(len(string) - 1)]
    for a, b in (reversed(pairs) if undo else pairs):
        c.g("cx", a, b)


def hop_parallel(c, a, b, string, beta):
    """exp(-i beta (X_a Z_S X_b + Y_a Z_S Y_b)): CX, Rz on a and b together, CX."""
    if string:
        s = string[-1]
        parity_ladder(c, string, s)
        c.g("h", b); c.g("cx", s, b); c.g("h", b)  # CZ(s, b)
    c.g("h", a); c.g("s", a); c.g("h", b); c.g("s", b)
    c.g("cx", a, b)
    c.g("h", a); c.g("rz", a, angle=2 * beta); c.g("h", a)
    c.g("rz", b, angle=2 * beta)
    c.g("cx", a, b)
    c.g("sdg", a); c.g("h", a); c.g("sdg", b); c.g("h", b)
    if string:
        c.g("h", b); c.g("cx", s, b); c.g("h", b)
        parity_ladder(c, string, s, undo=True)


def pauli_gadget(c, paulis, beta):
    """exp(-i beta P) for P = {qubit: 'X'|'Y'|'Z'}, as basis change + CX chain + Rz."""
    qs = sorted(paulis)
    for q in qs:
        if paulis[q] == "X":
            c.g("h", q)
        elif paulis[q] == "Y":
            c.g("sdg", q); c.g("h", q)
    for k in range(len(qs) - 1):
        c.g("cx", qs[k], qs[k + 1])
    c.g("rz", qs[-1], angle=2 * beta)
    for k in reversed(range(len(qs) - 1)):
        c.g("cx", qs[k], qs[k + 1])
    for q in qs:
        if paulis[q] == "X":
            c.g("h", q)
        elif paulis[q] == "Y":
            c.g("h", q); c.g("s", q)


def hopping_paulis(a, b, string):
    xx = {a: "X", b: "X", **{q: "Z" for q in string}}
    yy = {a: "Y", b: "Y", **{q: "Z" for q in string}}
    return xx, yy


# ---------------------------------------------------------
# Trotter circuit
# ---------------------------------------------------------
def build(lattice, lx, ly, steps, t, u, dt, order):
    """Return (Circuit, terms) where terms is the emitted list of (paulis, beta) for verification."""
    n_sites, bonds = lattice_bonds(lattice, lx, ly)
    c = Circuit(2 * n_sites)
    terms = []
    beta_hop = -t * dt / 2
    bond_layers = color_bonds(bonds) if order == "parallel" else [bonds]

    def qubit(r, spin):
        return r + spin * n_sites

    for _ in range(steps):
        for layer in bond_layers:
            for spin in (0, 1):
                for i, j in layer:
                    a, b = qubit(i, spin), qubit(j, spin)
                    string = list(range(a + 1, b))
                    xx, yy = hopping_paulis(a, b, string)
                    if order == "parallel":
                        hop_parallel(c, a, b, string, beta_hop)
                    else:
                        pauli_gadget(c, xx, beta_hop)
                        pauli_gadget(c, yy, beta_hop)
                    terms += [(xx, beta_hop), (yy, beta_hop)]
        if u:
            # U n_up n_dn = U/4 (1 - Z_up - Z_dn + Z_up Z_dn)
            for r in range(n_sites):
                for spin in (0, 1):
                    q = qubit(r, spin)
                    if order == "parallel":
                        c.g("rz", q, angle=-u * dt / 2)
                    else:
                        pauli_gadget(c, {q: "Z"}, -u * dt / 4)
                    terms.append(({q: "Z"}, -u * dt / 4))
            for r in range(n_sites):
                zz = {qubit(r, 0): "Z", qubit(r, 1): "Z"}
                pauli_gadget(c, zz, u * dt / 4)
                terms.append((zz, u * dt / 4))
    return c, terms


# ---------------------------------------------------------
# Statevector verification (small sizes only)
# ---------------------------------------------------------
def apply_gate(psi, n, name, qs, angle):
    s2 = 1 / math.sqrt(2)
    out = psi[:]
    if name == "cx":
        ctl, tgt = qs
        for i in range(len(psi)):
            if (i >> ctl) & 1:
                out[i] = psi[i ^ (1 << tgt)]
        return out
    q = qs[0]
    m = 1 << q
    for i in range(len(psi)):
        if i & m:
            continue
        a0, a1 = psi[i], psi[i | m]
        if name == "h":
            out[i], out[i | m] = s2 * (a0 + a1), s2 * (a0 - a1)
        elif name == "s":
            out[i | m] = 1j * a1
        elif name == "sdg":
            out[i | m] = -1j * a1
        elif name == "rz":
            out[i], out[i | m] = cmath.exp(-0.5j * angle) * a0, cmath.exp(0.5j * angle) * a1
        else:
            raise ValueError(name)
    return out


def apply_pauli_exp(psi, paulis, beta):
    """exp(-i beta P) psi = cos(beta) psi - i sin(beta) P psi."""
    p_psi = [0j] * len(psi)
    for i, amp in enumerate(psi):
        j, phase = i, 1
        for q, p in paulis.items():
            bit = (i >> q) & 1
            if p in "XY":
                j ^= 1 << q
            if p == "Y":
                phase *= 1j if bit == 0 else -1j
            if p == "Z" and bit:
                phase *= -1
        p_psi[j] += phase * amp
    return [math.cos(beta) * a - 1j * math.sin(beta) * b for a, b in zip(psi, p_psi)]


def verify():
    rng = random.Random(1)
    cases = [("1d", 3, 1), ("1d", 4, 1), ("2d", 2, 2), ("2d", 3, 2)]
    for lattice, lx, ly in cases:
        for order in ("parallel", "sequential"):
            c, terms = build(lattice, lx, ly, steps=2, t=1.0, u=4.0, dt=0.13, order=order)
            dim = 1 << c.n
            psi = [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(dim)]
            norm = math.sqrt(sum(abs(a) ** 2 for a in psi))
            psi = [a / norm for a in psi]
            ref = psi
            for paulis, beta in terms:
                ref = apply_pauli_exp(ref, paulis, beta)
            out = psi
            for name, qs, angle in c.ops:
                out = apply_gate(out, c.n, name, qs, angle)
            overlap = abs(sum(a.conjugate() * b for a, b in zip(ref, out)))
            status = "ok" if abs(overlap - 1) < 1e-9 else "FAIL"
            print(f"{lattice} {lx}x{ly} {order:<10} qubits={c.n:<3} |<ref|circ>| = {overlap:.12f} {status}")
            assert status == "ok"


# ---------------------------------------------------------
# Batch generation for the benchmark directory
# ---------------------------------------------------------
# Logical-qubit counts match even grid sizes of the synthetic suite (2 qubits per site),
# kept below 100 qubits so DASCOT runs stay tractable.
BATCH_SIZES = {16: (2, 4), 64: (4, 8)}
BATCH = [("parallel", 1), ("sequential", 1)]


def batch(outdir):
    for n, (lx2, ly2) in BATCH_SIZES.items():
        for lattice, lx, ly in (("1d", n // 2, 1), ("2d", lx2, ly2)):
            for order, steps in BATCH:
                c, _ = build(lattice, lx, ly, steps, t=1.0, u=4.0, dt=0.1, order=order)
                name = f"fermi_hubbard_{lattice}_{n}q_{steps}step_{order}.qasm"
                with open(os.path.join(outdir, name), "w") as f:
                    f.write(c.qasm())
                print("wrote", name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lattice", choices=["1d", "2d"], default="1d")
    ap.add_argument("--sites", type=int, default=8, help="1D chain length")
    ap.add_argument("--lx", type=int, default=2)
    ap.add_argument("--ly", type=int, default=2)
    ap.add_argument("--steps", type=int, default=1)
    ap.add_argument("--t", type=float, default=1.0)
    ap.add_argument("--u", type=float, default=4.0)
    ap.add_argument("--dt", type=float, default=0.1)
    ap.add_argument("--order", choices=["parallel", "sequential"], default="parallel")
    ap.add_argument("-o", "--output")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--batch", action="store_true")
    args = ap.parse_args()
    if args.verify:
        verify()
        return
    if args.batch:
        batch(os.path.dirname(os.path.abspath(__file__)))
        return
    lx, ly = (args.sites, 1) if args.lattice == "1d" else (args.lx, args.ly)
    c, _ = build(args.lattice, lx, ly, args.steps, args.t, args.u, args.dt, args.order)
    text = c.qasm()
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
