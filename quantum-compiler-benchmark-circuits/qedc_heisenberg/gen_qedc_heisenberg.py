"""Emit the QED-C Heisenberg Hamiltonian-simulation benchmark circuit as OpenQASM 2.0, without Qiskit.

Reproduces method 1 of the QED-C application-oriented benchmark
(SRI-International/QC-App-Oriented-Benchmarks, Apache-2.0, see LICENSE.QED-C):

  qedcbench/hamiltonian_simulation/hamiltonian_simulation_benchmark.py   (parameters)
  qedcbench/hamiltonian_simulation/qiskit/hamiltonian_simulation_kernel.py (circuit)

  * checkerboard initial state: X on every even qubit
  * K Trotter steps of: rx(2 tau w hx_i) and rz(2 tau w hz_i) on every qubit, then the
    XX+YY+ZZ interaction on bonds (0,1),(2,3),... then (1,2),(3,4),... of an open chain
  * tau = t / K; default interaction gate is the 3-CX xxyyzz_opt_gate
    (use_XX_YY_ZZ_gates=False); --separate-gates uses xx_gate, yy_gate, zz_gate instead
  * w, K, t, hx, hz are the values in qedcbench/hamiltonian_simulation/_common/precalculated_data.json

Gate sequences are transcribed from the kernel. Final measurements are omitted (DASCOT ignores them).

The published field lists have 20 entries, so the benchmark itself only goes up to 20 qubits.
For larger N this script cycles them (hx[i % 20]), which is a deviation from QED-C.

Usage:
    python gen_qedc_heisenberg.py 16 -o heisenberg_n16.qasm
    python gen_qedc_heisenberg.py --batch        # regenerate this directory
    python gen_qedc_heisenberg.py 16 --steps 1   # only the first of the K steps (tau = t / K)
"""
import argparse
import math
import os

PI = math.pi

# precalculated_data.json
W, K, T = 1, 5, 0.2
HX = [-0.3841300947500583, 0.03878295861060144, 0.5365953230759468, 0.5784414723417195, 0.7411241249516469,
      -0.6241572167558622, -0.4609895087661635, -0.007615718024277518, 0.4782434942274214, -0.6100960167167189,
      -0.6405095065481761, 0.07765251715030663, -0.4344687907780449, 0.5218797389241974, -0.46061411670810526,
      -0.41296098137198967, 0.9248110232255489, 0.8264286523422202, 0.1363496908115518, -0.029015291992941616]
HZ = [0.13788044023849122, -0.8680715448211151, 0.7762213398005142, 0.8593163543481379, 0.35938408275225986,
      0.08855163284966783, -0.6243013156839929, 0.2365269243700283, -0.2517444632292354, 0.867164336543846,
      0.296282404856135, 0.3435823547580954, 0.8631471356486622, 0.3399761708363991, -0.5357509772547095,
      -0.4883312979088732, -0.5500163526392827, -0.8385986892423059, -0.6319995154933682, 0.44989873651812795]


def heisenberg(n, separate_gates=False, k=K, t=T, w=W, steps=None):
    """steps: emit only the first `steps` of the k Trotter steps (tau stays t / k)."""
    tau = t / k
    lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{n}];"]
    g = lines.append

    def xx(a, b):
        for s in (f"h q[{a}];", f"h q[{b}];", f"cx q[{a}],q[{b}];", f"rz({PI * tau!r}) q[{b}];",
                  f"cx q[{a}],q[{b}];", f"h q[{a}];", f"h q[{b}];"):
            g(s)

    def yy(a, b):
        for s in (f"s q[{a}];", f"s q[{b}];", f"h q[{a}];", f"h q[{b}];", f"cx q[{a}],q[{b}];",
                  f"rz({PI * tau!r}) q[{b}];", f"cx q[{a}],q[{b}];", f"h q[{a}];", f"h q[{b}];",
                  f"sdg q[{a}];", f"sdg q[{b}];"):
            g(s)

    def zz(a, b):
        for s in (f"cx q[{a}],q[{b}];", f"rz({PI * tau!r}) q[{b}];", f"cx q[{a}],q[{b}];"):
            g(s)

    def xxyyzz_opt(a, b):  # alpha = beta = gamma = tau
        for s in (f"rz({PI / 2!r}) q[{b}];", f"cx q[{b}],q[{a}];", f"rz({PI * tau - PI / 2!r}) q[{a}];",
                  f"ry({-PI / 2 + PI * tau!r}) q[{b}];", f"cx q[{a}],q[{b}];", f"ry({-PI * tau + PI / 2!r}) q[{b}];",
                  f"cx q[{b}],q[{a}];", f"rz({-PI / 2!r}) q[{a}];"):
            g(s)

    hx = [HX[i % len(HX)] for i in range(n)]
    hz = [HZ[i % len(HZ)] for i in range(n)]
    for q in range(0, n, 2):
        g(f"x q[{q}];")
    bonds = [i for j in range(2) for i in range(j % 2, n - 1, 2)]
    for _ in range(k if steps is None else steps):
        for i in range(n):
            g(f"rx({2 * tau * w * hx[i]!r}) q[{i}];")
        for i in range(n):
            g(f"rz({2 * tau * w * hz[i]!r}) q[{i}];")
        if separate_gates:
            for gate in (xx, yy, zz):
                for i in bonds:
                    gate(i, i + 1)
        else:
            for i in bonds:
                xxyyzz_opt(i, i + 1)
    return "\n".join(lines) + "\n"


BATCH = [16, 20, 25, 49, 64, 100]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("n", type=int, nargs="?")
    ap.add_argument("--separate-gates", action="store_true", help="use_XX_YY_ZZ_gates=True in QED-C terms")
    ap.add_argument("--steps", type=int, help=f"emit only the first STEPS of the K={K} steps")
    ap.add_argument("-o", "--output")
    ap.add_argument("--batch", action="store_true")
    args = ap.parse_args()
    if args.batch:
        here = os.path.dirname(os.path.abspath(__file__))
        for n in BATCH:
            with open(os.path.join(here, f"heisenberg_qedc_n{n}.qasm"), "w") as f:
                f.write(heisenberg(n))
        return
    if args.n is None:
        ap.error("give a qubit count or --batch")
    text = heisenberg(args.n, args.separate_gates, steps=args.steps)
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
