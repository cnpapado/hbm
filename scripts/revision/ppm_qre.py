"""Cross-check ppm_baseline.py's fast block against the Microsoft Azure Quantum Resource Estimator.

The estimator's layout (PSSPC, Beverland et al. 2022, arXiv:2211.07629) is Litinski's fast block
run sequentially. In its source (microsoft/qsharp,
source/resource_estimator/src/system/data/logical_counts.rs):
    logical qubits = 2n + ceil(sqrt(8n)) + 1
    logical depth  = (measurements + rotations + T count) * 1   (+ 3 per CCZ)
We give it the same circuit counts (measurementCount 0: HBMS does not count final
measurements either), the same surface-code constants (threshold --p-th, prefactor --A,
2d^2 qubits per tile) and the same error budget. It prints its logical qubits and logical depth
next to ours; these two must match. Its code distance and physical qubits are listed for
reference only: it splits the error budget differently, charges error per logical cycle
instead of per round, and makes T states with its own 15-to-1 factories, not cultivation.

Install: pip install qsharp   (newer releases ship the same module as 'qdk')
Usage:   python ppm_qre.py test/benchmarks_bursty_cx/bench_n16_p50.qasm [...] --csv ppm_qre.csv
"""

import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppm_baseline import BLOCKS, circuit_stats, read_circuit  # noqa: E402

try:
    from qdk.estimator import LogicalCounts
except ImportError:
    from qsharp.estimator import LogicalCounts


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", help=".qasm files or directories of them")
    ap.add_argument("--csv", default="ppm_qre.csv")
    ap.add_argument("--target", type=float, default=0.01, help="error budget")
    ap.add_argument("--A", type=float, default=0.1)
    ap.add_argument("--p-th", dest="p_th", type=float, default=0.01)
    args = ap.parse_args()

    params = {
        "qubitParams": {"name": "qubit_gate_ns_e3"},  # p = 1e-3 for every operation
        "qecScheme": {"name": "surface_code", "crossingPrefactor": args.A,
                      "errorCorrectionThreshold": args.p_th},
        "errorBudget": args.target,
    }
    files = []
    for x in args.inputs:
        files += sorted(glob.glob(os.path.join(x, "*.qasm"))) if os.path.isdir(x) else [x]
    rows = []
    for path in files:
        cs = circuit_stats(*read_circuit(path))
        n = cs["N"]
        r = LogicalCounts({"numQubits": n, "tCount": cs["n_t"], "measurementCount": 0}).estimate(
            params)
        bd = r["physicalCounts"]["breakdown"]
        ours_q, ours_depth = BLOCKS["fast"][0](n), cs["n_t"]
        rows.append(dict(
            bench=os.path.basename(path)[:-len(".qasm")], N=n, n_t=cs["n_t"],
            ours_tiles=ours_q, qre_logical_qubits=bd["algorithmicLogicalQubits"],
            ours_steps=ours_depth, qre_logical_depth=bd["algorithmicLogicalDepth"],
            qre_depth_with_factories=bd["logicalDepth"],
            match=(ours_q == bd["algorithmicLogicalQubits"]
                   and ours_depth == bd["algorithmicLogicalDepth"]),
            qre_code_distance=r["logicalQubit"]["codeDistance"],
            qre_tfactories=bd["numTfactories"],
            qre_physical_qubits=r["physicalCounts"]["physicalQubits"],
            qre_runtime_ns=r["physicalCounts"]["runtime"],
        ))
        x = rows[-1]
        print(f"{x['bench']:24s} tiles {x['ours_tiles']} vs {x['qre_logical_qubits']}, "
              f"steps {x['ours_steps']} vs {x['qre_logical_depth']} "
              f"({'match' if x['match'] else 'MISMATCH'}), QRE d={x['qre_code_distance']}")
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} circuits -> {args.csv}")


if __name__ == "__main__":
    main()
