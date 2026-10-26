"""
injection_model.py
------------------
Turn a Clifford+rotation QASM circuit into a DASCOT routing model for a surface-code machine
with arbitrary-angle injection (no Clifford+T synthesis).

DASCOT routes only `cx` and `t`/`tdg` (extract_gates_from_file in wisq/src/wisq/dascot.py), with
every `t` served by a magic-state patch. Here a `t` stands for "consume one injected resource
state on this qubit":

  * cx                                       -> cx
  * rotation by an odd multiple of pi/4      -> 1 t (an ordinary T gate)
  * rotation by any other non-Clifford angle -> A t on that qubit, however small the angle:
        --attempts 1   deterministic injection, one resource state per rotation
        --attempts 2   repeat-until-success (RUS) at its expected cost: each attempt succeeds
                       with probability 1/2, so a rotation takes 2 attempts on average
        --rus-sample   draw each rotation's attempts from Geometric(1/2) (mean 2), --seed fixes it
  * multiples of pi/2 and all other single-qubit Cliffords -> dropped (free in DASCOT)

Rotations are rz, rx, ry, u1, p, and each Euler angle of u2/u3/u. Two-qubit Cliffords cz/cy are
written as cx (same cost for DASCOT); swap as 3 cx. Toffolis are rejected.

The output is a resource model for routing, not an executable circuit. Its register is always `q`.

Usage:
  python injection_model.py in.qasm out.qasm [--attempts 1|2 | --rus-sample --seed 0]
"""

import argparse
import math
import random
import re
import sys

GATE = re.compile(r"^\s*([a-zA-Z_]\w*)\s*(?:\(([^)]*)\))?\s+([^;]+);")
QREG = re.compile(r"^\s*qreg\s+(\w+)\s*\[(\d+)\]\s*;")
ARG = re.compile(r"^\s*(\w+)\s*\[(\d+)\]\s*$")
SKIP = {"openqasm", "include", "creg", "qreg", "barrier", "measure", "reset", "if", "gate", "opaque"}
ROTATIONS = {"rz", "rx", "ry", "u1", "p"}


def classify(expr):
    """'clifford', 't', or 'rotation' for one rotation angle."""
    try:
        v = float(eval(expr.replace("pi", "math.pi"), {"__builtins__": {}}, {"math": math}))
    except Exception:
        return "rotation"
    quarter = v / (math.pi / 4)
    if abs(quarter - round(quarter)) < 1e-9:
        return "clifford" if round(quarter) % 2 == 0 else "t"
    return "rotation"


def convert(path, attempts=1, rng=None):
    offsets, total = {}, 0
    out, stats = [], {"cx": 0, "t_gates": 0, "rotations": 0, "injections": 0}

    def inject(q, kind):
        if kind == "clifford":
            return
        if kind == "t":
            n = 1
            stats["t_gates"] += 1
        else:
            n = attempts
            if rng is not None:
                n = 1
                while rng.random() >= 0.5:
                    n += 1
            stats["rotations"] += 1
            stats["injections"] += n
        out.extend([f"t q[{q}];"] * n)

    with open(path) as f:
        for line in f:
            line = line.split("//")[0]
            m = QREG.match(line)
            if m:
                offsets[m.group(1)] = total
                total += int(m.group(2))
                continue
            m = GATE.match(line)
            if not m or m.group(1).lower() in SKIP:
                continue
            name, params = m.group(1).lower(), m.group(2) or ""
            qs = []
            for arg in m.group(3).split(","):
                a = ARG.match(arg)
                if not a or a.group(1) not in offsets:
                    raise ValueError(f"unsupported argument {arg.strip()!r} in {line.strip()!r}")
                qs.append(offsets[a.group(1)] + int(a.group(2)))
            if name in ("cx", "cz", "cy", "swap"):
                for _ in range(3 if name == "swap" else 1):
                    out.append(f"cx q[{qs[0]}],q[{qs[1]}];")
                    stats["cx"] += 1
            elif name in ("t", "tdg"):
                inject(qs[0], "t")
            elif name in ROTATIONS:
                inject(qs[0], classify(params))
            elif name in ("u3", "u", "u2"):
                for expr in params.split(","):
                    inject(qs[0], classify(expr))
            elif len(qs) > 1:
                raise ValueError(f"unsupported multi-qubit gate {name!r}")
    header = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{total}];"]
    return "\n".join(header + out) + "\n", stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--attempts", type=int, default=1, help="resource states per rotation (2 = RUS expectation)")
    g.add_argument("--rus-sample", action="store_true", help="sample attempts per rotation from Geometric(1/2)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed) if args.rus_sample else None
    try:
        text, stats = convert(args.input, args.attempts, rng)
    except ValueError as e:
        sys.exit(f"{args.input}: {e}")
    with open(args.output, "w") as f:
        f.write(text)
    print(f"{args.input}: {stats}")


if __name__ == "__main__":
    main()
