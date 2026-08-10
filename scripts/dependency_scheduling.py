"""
Compute the minimum number of timesteps for a wisq .out file when only gate
dependencies are considered (ignoring all mapping/routing constraints). This
is the "ideal" denominator of the paper's Cost Ratio (Eq. 2).

Usage:
    python dependency_scheduling.py <wisq_out.json> [--with-cnot-routing]
    python dependency_scheduling.py <dir_of_outs>/ [--with-cnot-routing]

Notes:
- wisq strips single-qubit Cliffords before mapping/routing, so the input to
  this script already excludes H/S/etc. It considers only cx, t, tdg — matching
  circ.depth(filter=[cx,t,tdg]).
- With --with-cnot-routing, two gates that share a routing-path node are also
  treated as dependent. This turns the metric into a lower bound sensitive to
  how the router used the grid — useful for comparing ARCH_C vs ARCH_D since
  ARCH_D's upper-plane payloads (>= width*height) count as distinct resources.
"""

import argparse
import json
import sys
from pathlib import Path


def extract_gates_from_wisq_out(filename):
    with open(filename, "r") as f:
        data = json.load(f)

    ops = []
    qubits = []
    paths = []
    for step in data.get("steps", []):
        if isinstance(step, str):
            return None, None, None
        for gate in step:
            ops.append(gate.get("op"))
            qubits.append(gate.get("qubits", []))
            paths.append(gate.get("path", []))
    return ops, qubits, paths


def min_timesteps(wisq_out_filename, take_cnot_routing_into_account=False):
    _ops, qubits, paths = extract_gates_from_wisq_out(wisq_out_filename)
    if qubits is None:
        return None

    levels = []
    for i, qi in enumerate(qubits):
        qi_set = set(qi)
        pi_set = set(paths[i]) if take_cnot_routing_into_account else None
        best = 0
        for j in range(i):
            share_qubit = bool(qi_set & set(qubits[j]))
            share_path = (
                take_cnot_routing_into_account
                and bool(pi_set & set(paths[j]))
            )
            if share_qubit or share_path:
                if levels[j] + 1 > best:
                    best = levels[j] + 1
        levels.append(best)

    return (max(levels) + 1) if levels else 0


def report(path, with_cnot_routing):
    ideal = min_timesteps(path, take_cnot_routing_into_account=False)
    if ideal is None:
        print(f"{path.name}: TIMEOUT/no-steps")
        return
    line = f"{path.name}: ideal={ideal}"
    if with_cnot_routing:
        ideal_r = min_timesteps(path, take_cnot_routing_into_account=True)
        line += f"  ideal_w_routing={ideal_r}"
    print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("target", help="wisq .out file or directory of .out files")
    ap.add_argument(
        "--with-cnot-routing",
        action="store_true",
        help="also treat gates whose routing paths intersect as dependent",
    )
    args = ap.parse_args()

    target = Path(args.target)
    if target.is_dir():
        outs = sorted(p for p in target.iterdir() if p.suffix in (".out", ".json"))
        if not outs:
            print(f"no .out/.json files in {target}", file=sys.stderr)
            sys.exit(1)
        for p in outs:
            report(p, args.with_cnot_routing)
    elif target.is_file():
        report(target, args.with_cnot_routing)
    else:
        print(f"not found: {target}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
