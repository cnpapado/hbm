"""
t_density.py
------------
T density of QASM circuits as DASCOT sees them.

DASCOT routes only cx and t/tdg (extract_gates_from_file in wisq/src/wisq/dascot.py);
every other gate is free and does not take a timestep. So:

  1. Keep only cx and T gates and ASAP-schedule them: a gate goes in the layer after
     the latest layer used by any of its qubits.
  2. L        = number of layers (the cx/T depth; the cost-ratio denominator)
     N        = qubits touched by a cx or T (what DASCOT places on the grid)
     density  = T count / (N * L)      fraction of qubit-layer slots holding a T
     frac_T   = fraction of layers containing at least one T
     avg_T    = mean T gates per layer that has a T
     max_T    = most T gates in one layer
     cong     = max_T / (4*sqrt(N))    peak demand over the 2D perimeter supply
     cong_avg = avg_T / (4*sqrt(N))    sustained demand over the 2D perimeter supply

Circuits that are not yet Clifford+T are handled as follows:

  * rotations (rz, rx, ry, u1, p, and the Euler angles of u2/u3/u):
      angle within eps of a multiple of pi/2 -> Clifford, free
      odd multiple of pi/4              -> 1 T
      anything else                     -> K sequential T on that qubit,
    where K = --t-per-rotation, or ceil(3*log2(1/eps)) for --eps (gridsynth-style T count:
    ~20 at 1e-2, ~30 at 1e-3, ~80 at 1e-8). Without either option, non-Clifford rotations
    are ignored (use this for circuits that are already Clifford+T).
    --rz-as-t is kept for compatibility: K = 1.
  * ccx / ccz -> 7 T, as the textbook decomposition (Nielsen & Chuang Fig. 4.9) or, with
    --toffoli tdepth3, a T-depth-3 phase-polynomial form (T layers of 3, 3, 1).

Any register name works (several registers are concatenated). DASCOT itself only reads
gates on a register called `q`; files using another name are flagged with `*`.

Usage:
  python t_density.py file1.qasm [file2.qasm ...] [--eps 1e-2 | --t-per-rotation K]
                      [--toffoli textbook|tdepth3] [--csv out.csv]
"""

import argparse
import csv
import math
import os
import re
import sys
from collections import defaultdict

GATE = re.compile(r"^\s*([a-zA-Z_]\w*)\s*(?:\(([^)]*)\))?\s+([^;]+);")
QREG = re.compile(r"^\s*qreg\s+(\w+)\s*\[(\d+)\]\s*;")
ARG = re.compile(r"^\s*(\w+)\s*\[(\d+)\]\s*$")

TWO_QUBIT = {"cx", "cz", "cy", "swap"}
ROT_Z = {"rz", "u1", "p"}
ROT_XY = {"rx", "ry"}
SKIP = {"openqasm", "include", "creg", "qreg", "barrier", "measure", "reset", "if", "gate", "opaque"}


def _angle(expr):
    try:
        return float(eval(expr.replace("pi", "math.pi"), {"__builtins__": {}}, {"math": math}))
    except Exception:
        return None


def rotation_cost(expr, k, eps=None):
    """T gates needed for one rotation by `expr` (k = T per generic rotation, None = ignore).

    A rotation within eps of a Clifford (|sin(delta/2)| <= eps, delta = distance to the
    nearest multiple of pi/2) is synthesized as that Clifford and is free."""
    v = _angle(expr)
    if v is None:
        return k or 0
    quarter = v / (math.pi / 4)
    if abs(quarter - round(quarter)) < 1e-9:
        return 0 if round(quarter) % 2 == 0 else 1
    delta = abs(math.remainder(v, math.pi / 2))
    if abs(math.sin(delta / 2)) <= (eps or 1e-12):
        return 0
    return k or 0


# Toffoli decompositions on (a, b, c) with target c, as (gate, qubits) in circuit order.
def toffoli_textbook(a, b, c):
    return [("cx", b, c), ("t", c), ("cx", a, c), ("t", c), ("cx", b, c), ("t", c), ("cx", a, c),
            ("t", b), ("t", c), ("cx", a, b), ("t", a), ("t", b), ("cx", a, b)]


def toffoli_tdepth3(a, b, c):
    # Toffoli = H_c CCZ H_c with the CCZ phase pi*abc = pi/4 (a + b + c - a^b - a^c - b^c + a^b^c):
    # T on {a, b, c}, then on {a^b, a^c, a^b^c}, then on {b^c}, with CX between to move the
    # parities onto wires. Checked against the exact Toffoli unitary; H gates omitted (free).
    return [("t", a), ("t", b), ("t", c),
            ("cx", a, b), ("cx", c, a), ("cx", b, c),
            ("t", a), ("t", b), ("t", c),
            ("cx", b, a),
            ("t", a),
            ("cx", c, a), ("cx", b, c), ("cx", a, b)]


TOFFOLI = {"textbook": toffoli_textbook, "tdepth3": toffoli_tdepth3}


def analyze(path, rz_as_t=False, t_per_rotation=None, toffoli="textbook", eps=None):
    k = 1 if rz_as_t else t_per_rotation
    offsets, q_named = {}, True
    clock = defaultdict(int)
    t_per_layer = defaultdict(int)
    used = set()
    n_t = n_cx = n_rot = n_ccx = 0
    depth = 0

    def cx(a, b):
        nonlocal depth, n_cx
        start = max(clock[a], clock[b])
        clock[a] = clock[b] = start + 1
        depth = max(depth, start + 1)
        used.update((a, b))
        n_cx += 1

    def t(q, count=1):
        nonlocal depth, n_t
        for _ in range(count):
            start = clock[q]
            clock[q] = start + 1
            depth = max(depth, start + 1)
            t_per_layer[start] += 1
            n_t += 1
        used.add(q)

    total = 0
    with open(path) as f:
        for line in f:
            line = line.split("//")[0]
            m = QREG.match(line)
            if m:
                offsets[m.group(1)] = total
                total += int(m.group(2))
                q_named = q_named and m.group(1) == "q"
                continue
            m = GATE.match(line)
            if not m or m.group(1).lower() in SKIP:
                continue
            name, params = m.group(1).lower(), m.group(2) or ""
            qs = []
            for arg in m.group(3).split(","):
                a = ARG.match(arg)
                if not a or a.group(1) not in offsets:
                    raise ValueError(f"{path}: unsupported argument {arg.strip()!r} in {line.strip()!r}")
                qs.append(offsets[a.group(1)] + int(a.group(2)))

            if name in TWO_QUBIT:
                for _ in range(3 if name == "swap" else 1):
                    cx(*qs)
            elif name in ("t", "tdg"):
                t(qs[0])
            elif name in ("ccx", "ccz"):
                n_ccx += 1
                for op in TOFFOLI[toffoli](*qs):
                    cx(op[1], op[2]) if op[0] == "cx" else t(op[1])
            elif name in ROT_Z or name in ROT_XY:
                cost = rotation_cost(params, k, eps)
                n_rot += cost > 1
                t(qs[0], cost) if cost else None
            elif name in ("u3", "u", "u2"):
                angles = params.split(",")
                for expr in angles:  # Euler angles: each non-Clifford one is a rotation
                    cost = rotation_cost(expr, k, eps)
                    n_rot += cost > 1
                    t(qs[0], cost) if cost else None
            elif len(qs) > 1 and name not in ("barrier",):
                raise ValueError(f"{path}: unsupported multi-qubit gate {name!r}")
            # other single-qubit gates (h, s, sdg, x, y, z, sx, ...) are Clifford and free

    n = len(used)
    layers_with_t = len(t_per_layer)
    max_t = max(t_per_layer.values(), default=0)
    avg_t = n_t / layers_with_t if layers_with_t else 0.0
    perimeter = 4 * math.sqrt(n) if n else 1.0
    return {
        "name": os.path.splitext(os.path.basename(path))[0] + ("" if q_named else "*"),
        "N": n,
        "cx": n_cx,
        "T": n_t,
        "rotations": n_rot,
        "toffolis": n_ccx,
        "L": depth,
        "density": n_t / (n * depth) if depth else 0.0,
        "frac_T": layers_with_t / depth if depth else 0.0,
        "avg_T": avg_t,
        "max_T": max_t,
        "cong": max_t / perimeter,
        "cong_avg": avg_t / perimeter,
    }


COLUMNS = [("name", "{:<34}"), ("N", "{:>4}"), ("cx", "{:>6}"), ("T", "{:>8}"), ("rotations", "{:>5}"),
           ("toffolis", "{:>5}"), ("L", "{:>7}"), ("density", "{:>8.3f}"), ("frac_T", "{:>7.2f}"),
           ("max_T", "{:>6}"), ("cong_avg", "{:>9.2f}"), ("cong", "{:>8.2f}")]
HEADER = ["Benchmark", "N", "cx", "T", "rots", "tofs", "L", "density", "frac_T", "max_T", "cong_avg", "cong_pk"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--eps", type=float, help="per-rotation synthesis precision; K = ceil(3*log2(1/eps))")
    g.add_argument("--t-per-rotation", type=int, help="T gates per non-Clifford rotation")
    g.add_argument("--rz-as-t", action="store_true", help="count each non-Clifford rotation as 1 T")
    ap.add_argument("--toffoli", choices=sorted(TOFFOLI), default="textbook")
    ap.add_argument("--csv", help="also write the results to this CSV file")
    args = ap.parse_args()
    k = args.t_per_rotation
    if args.eps:
        k = math.ceil(3 * math.log2(1 / args.eps))

    rows = []
    for p in args.files:
        try:
            rows.append(analyze(p, args.rz_as_t, k, args.toffoli, args.eps))
        except ValueError as e:
            print(f"skipped: {e}", file=sys.stderr)
    widths = [len(fmt.format(0 if c != "name" else "")) for c, fmt in COLUMNS]
    print(" ".join(h.rjust(w) if i else h.ljust(w) for i, (h, w) in enumerate(zip(HEADER, widths))))
    for r in rows:
        print(" ".join(fmt.format(r[c]) for c, fmt in COLUMNS))
    if k:
        print(f"(non-Clifford rotations counted as {k} T each)")
    if any(r["name"].endswith("*") for r in rows):
        print("* register is not named q: DASCOT would not see these gates", file=sys.stderr)
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
