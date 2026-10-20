"""
t_density.py
------------
T density of QASM circuits as DASCOT sees them: only cx and t/tdg are kept
(same regexes as extract_gates_from_file in wisq/src/wisq/dascot.py), every
other gate is free. Gates are ASAP-scheduled into layers.

  L        = cx/T depth (the ideal depth used as the cost-ratio denominator)
  density  = T count / (N * L)
  max_T    = most T gates in one layer
  cong     = max_T / (4 * sqrt(N))   (2D perimeter limit)

For a circuit that has only rz rotations (pre-synthesis), --rz-as-t counts
each non-zero rz as a single T.

Usage:
  python t_density.py file1.qasm [file2.qasm ...] [--rz-as-t]
"""

import argparse
import math
import os
import re
from collections import defaultdict

CX = re.compile(r"(cx)\s+q\[(\d+)\],\s*q\[(\d+)\];")
T = re.compile(r"(t|tdg)\s+q\[(\d+)\];")
RZ = re.compile(r"rz\(([^)]*)\)\s+q\[(\d+)\];")
QREG = re.compile(r"qreg\s+\w+\[(\d+)\];")


def analyze(path, rz_as_t=False):
    n = 0
    clock = defaultdict(int)
    t_per_layer = defaultdict(int)
    n_t = n_cx = 0
    depth = 0
    with open(path) as f:
        for line in f:
            m = QREG.match(line)
            if m:
                n += int(m.group(1))
                continue
            m = CX.match(line)
            if m:
                a, b = int(m.group(2)), int(m.group(3))
                start = max(clock[a], clock[b])
                clock[a] = clock[b] = start + 1
                depth = max(depth, start + 1)
                n_cx += 1
                continue
            m = T.match(line)
            q = None
            if m:
                q = int(m.group(2))
            elif rz_as_t:
                m = RZ.match(line)
                if m and m.group(1).strip() not in ("0", "0.0"):
                    q = int(m.group(2))
            if q is not None:
                start = clock[q]
                clock[q] = start + 1
                depth = max(depth, start + 1)
                t_per_layer[start] += 1
                n_t += 1
    max_t = max(t_per_layer.values(), default=0)
    return {
        "name": os.path.splitext(os.path.basename(path))[0],
        "N": n,
        "cx": n_cx,
        "T": n_t,
        "L": depth,
        "density": n_t / (n * depth) if depth else 0.0,
        "max_T": max_t,
        "cong": max_t / (4 * math.sqrt(n)) if n else 0.0,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--rz-as-t", action="store_true")
    args = ap.parse_args()
    print(f"{'Benchmark':<22} {'N':>4} {'cx':>6} {'T':>8} {'L':>7} {'density':>8} {'max_T':>6} {'max_T/4sqrtN':>12}")
    for p in args.files:
        r = analyze(p, args.rz_as_t)
        print(f"{r['name']:<22} {r['N']:>4} {r['cx']:>6} {r['T']:>8} {r['L']:>7} {r['density']:>8.3f} {r['max_T']:>6} {r['cong']:>12.2f}")
