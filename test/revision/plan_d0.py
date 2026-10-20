"""Which D0 factory counts to queue per circuit (used by submit_revision.sh).

Prints "<qasm> <spec>" for each D0 spec worth running on each circuit of LIST:
  X<m>  when its ceil(m * F*) ports fit on the ring around the data block (D0 rejects more);
  Xmax  (a port on every ring tile) when X2 does not fit, so the sweep has the most supply
        DASCOT's perimeter allows;
  alt   (DASCOT's perimeter, every other ring tile) always: it fits by construction.
Specs that are not D0 are ignored.
Gates and N are read as wisq reads them (dascot.extract_gates_from_file). Only the standard
library is needed: designs.py is loaded without the rest of the wisq package.

Usage: python3 plan_d0.py LIST --d 13 --specs D0-X0.25 D0-X0.5 D0-X1 D0-X2 D0-Xmax
"""

import argparse
import importlib
import os
import re
import sys
import types

WISQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "wisq", "src",
                    "wisq")


def load_designs():
    pkg = types.ModuleType("wisq_designs_only")
    pkg.__path__ = [WISQ]
    sys.modules[pkg.__name__] = pkg
    return importlib.import_module(f"{pkg.__name__}.designs")


def read_gates(path):  # as wisq.dascot.extract_gates_from_file
    gates = []
    with open(path) as f:
        for line in f:
            m = re.match(r"(cx)\s+q\[(\d+)\],\s*q\[(\d+)\];", line)
            if m:
                gates.append((int(m.group(2)), int(m.group(3))))
            m = re.match(r"(t|tdg)\s+q\[(\d+)\];", line)
            if m:
                gates.append((int(m.group(2)),))
    return gates


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("list", help="file with one .qasm path per line")
    ap.add_argument("--d", type=int, required=True)
    ap.add_argument("--specs", nargs="+", required=True)
    args = ap.parse_args()
    D = load_designs()
    designs = {s: D.parse_design(s, d=args.d) for s in args.specs if s.startswith("D0-")}
    with open(args.list) as f:
        paths = [line.strip() for line in f if line.strip()]
    for path in paths:
        gates = read_gates(path)
        n = len({q for g in gates for q in g})
        cap = D.d0_ring_capacity(n)
        counts = {s: D.factory_count(des, n, gates)[0] for s, des in designs.items()}
        x2_fits = all(c is not None and c <= cap for s, c in counts.items()
                      if designs[s].count_mode == "X")
        for s, c in counts.items():
            mode = designs[s].count_mode
            if mode == "alt" or (mode == "max" and not x2_fits) or (c is not None and c <= cap):
                print(path, s)


if __name__ == "__main__":
    main()
