"""
ising_one_step.py
-----------------
Keep only the first Trotter step of a transverse-field Ising circuit in the QASMBench /
JKU form (QASMBench ising_n10, JKU ising_model_13/16), so it matches QASMBench's one-step
ising_n26/n34/n66.

Those circuits are an h on every qubit, then per step:
  ZZ layer     rz / cx / rz / cx on each bond (2 (N-1) CNOTs),
  field layer  h, rz, h on every qubit, then one longitudinal rz per qubit
               (interleaved per qubit in QASMBench, in a block after the h's in JKU).
The cut is made at the first gate of step 2: a cx or h after the field layer started, or
a second rz on a qubit that already had its longitudinal rz. Measurements are dropped.

Usage:
  python ising_one_step.py in.qasm out.qasm
"""

import re
import sys

GATE = re.compile(r"^\s*([a-z]+)(\([^)]*\))?\s+(.*);")
QUBIT = re.compile(r"\[(\d+)\]")


def one_step(lines):
    header, body = [], []
    n = None
    for line in lines:
        m = GATE.match(line)
        if m is None or m.group(1) in ("qreg", "creg"):
            if m is not None and m.group(1) == "qreg":
                n = int(QUBIT.search(line).group(1))
            header.append(line)
            continue
        body.append((m.group(1), [int(q) for q in QUBIT.findall(m.group(3))], line))
    if n is None:
        sys.exit("no qreg")
    n = len({q for _, qs, _ in body for q in qs})  # JKU ising_model_13 declares q[16]

    out = []
    cx = 0
    field_h = {}  # qubit -> h gates seen in the field layer
    longitudinal = set()  # qubits whose longitudinal rz is kept
    for name, qs, line in body:
        if name in ("measure", "barrier"):
            continue
        in_field = cx == 2 * (n - 1)
        if not in_field:
            if name == "cx":
                cx += 1
            out.append(line)
            continue
        q = qs[0]
        if name == "cx":
            break  # step 2's ZZ layer
        if name == "h":
            if field_h.get(q, 0) >= 2:
                break
            field_h[q] = field_h.get(q, 0) + 1
        elif name == "rz" and field_h.get(q, 0) == 2:
            if q in longitudinal:
                break  # step 2 starts with an rz on this qubit
            longitudinal.add(q)
        out.append(line)
    if cx != 2 * (n - 1) or len(longitudinal) != n or any(field_h.get(q) != 2 for q in range(n)):
        sys.exit(f"unexpected structure: {cx} CNOTs, field h {field_h}, "
                 f"{len(longitudinal)} longitudinal rz (N={n})")
    return header + out


def main():
    src, dst = sys.argv[1:3]
    with open(src) as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    with open(dst, "w") as f:
        f.write("\n".join(one_step(lines)) + "\n")


if __name__ == "__main__":
    main()
