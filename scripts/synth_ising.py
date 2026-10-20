"""
synth_ising.py
--------------
Synthesize the rz/rx rotations of a QASM circuit to Clifford+T using the same
path wisq takes in guoq.transpile_if_needed:

    BasisTranslator -> NAM {rz, h, x, cx}  ->  QualtranRS (Qualtran's
    diagonal_unitary_approx, dps=200, max_t=400)  ->  wisq's sequence_to_circ

Differences from calling `wisq --mode opt -ot 0` directly:
  * epsilon is given per rotation (wisq takes a total budget and uses
    eps_total / (2 * num_rz) per rotation),
  * each distinct angle is synthesized once and cached (Trotter circuits reuse
    angles, and Qualtran takes seconds per call at small epsilon),
  * measurements/barriers are dropped (DASCOT ignores them anyway),
  * with --merge, rz(0) is dropped and back-to-back rz on the same qubit are
    fused before synthesis (a lossless peephole that any optimizer applies).

The pinned Qualtran (fa5a8ec) exposes `to_sequence(matrix, fmt)` as a module
function rather than the `SU2CliffordT.to_sequence()` method that
wisq/qualtran_rotation_synthesis.py calls, so the method is shimmed here.

Usage:
  python synth_ising.py in.qasm out.qasm --eps 1e-3 [--merge]
"""

import argparse
import json
import math
import sys
import time

import mpmath
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.equivalence_library import StandardEquivalenceLibrary as sel
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import BasisTranslator, RemoveBarriers
from qualtran.rotation_synthesis import math_config as mc
from qualtran.rotation_synthesis.matrix import su2_ct, to_sequence
from qualtran.rotation_synthesis.protocols import clifford_t_synthesis as cts

from wisq.guoq import GATE_SETS
from wisq.qualtran_rotation_synthesis import sequence_to_circ

su2_ct.SU2CliffordT.to_sequence = lambda self: to_sequence(self, "xyz")

TWO_PI = 2 * math.pi


def merge_rz(circ):
    """Fuse consecutive rz on the same qubit and drop rz(0 mod 2pi)."""
    out = QuantumCircuit(*circ.qregs)
    pending = {}

    def flush(q):
        a = pending.pop(q, None)
        if a is not None and abs(math.remainder(a, TWO_PI)) > 1e-12:
            out.rz(a, q)

    for inst in circ.data:
        qs = [circ.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == "rz":
            pending[qs[0]] = pending.get(qs[0], 0.0) + float(inst.operation.params[0])
            continue
        for q in qs:
            flush(q)
        out.append(inst.operation, [out.qubits[q] for q in qs])
    for q in list(pending):
        flush(q)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--eps", type=float, required=True, help="per-rotation approximation epsilon")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--stats", help="write synthesis stats as JSON here")
    args = ap.parse_args()

    circ = QuantumCircuit.from_qasm_file(args.input)
    circ.remove_final_measurements(inplace=True)
    circ = PassManager([RemoveBarriers()]).run(circ)
    nam = PassManager([BasisTranslator(equivalence_library=sel, target_basis=GATE_SETS["NAM"])]).run(circ)
    num_rz_raw = nam.count_ops().get("rz", 0)
    if args.merge:
        nam = merge_rz(nam)

    config = mc.with_dps(200)
    eps = mpmath.mpf(args.eps)
    cache = {}
    t_per_rot = []
    out = QuantumCircuit(*nam.qregs)
    t0 = time.time()
    for inst in nam.data:
        qs = [out.qubits[nam.find_bit(q).index] for q in inst.qubits]
        if inst.operation.name != "rz":
            out.append(inst.operation, qs)
            continue
        angle = float(inst.operation.params[0])
        if angle not in cache:
            diag = cts.diagonal_unitary_approx(theta=angle, eps=eps, max_n=400, config=config)
            if diag is None:
                sys.exit(f"could not synthesize rz({angle}) at eps={args.eps}")
            cache[angle] = sequence_to_circ(diag.to_matrix().to_sequence())
        seq = cache[angle]
        t_per_rot.append(seq.count_ops().get("t", 0) + seq.count_ops().get("tdg", 0))
        for s in seq.data:
            out.append(s.operation, qs)

    qasm2.dump(out, args.output)
    stats = {
        "input": args.input,
        "eps_per_rotation": args.eps,
        "merge": args.merge,
        "num_rz_raw": num_rz_raw,
        "num_rz_synthesized": len(t_per_rot),
        "distinct_angles": len(cache),
        "t_count": sum(t_per_rot),
        "t_per_rotation_mean": sum(t_per_rot) / len(t_per_rot) if t_per_rot else 0,
        "t_per_rotation_min": min(t_per_rot, default=0),
        "t_per_rotation_max": max(t_per_rot, default=0),
        "seconds": round(time.time() - t0, 1),
        "ops": dict(out.count_ops()),
    }
    print(json.dumps(stats))
    if args.stats:
        with open(args.stats, "w") as f:
            json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
