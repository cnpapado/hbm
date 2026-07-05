"""
analyze_wisq_routing.py
-----------------------
Compute magic state routing metrics from all WISQ simulator .out files
in the same directory as this script.

Metrics:
  MSRD  -- Average Magic State Routing Distance:
            mean path length across all T/Tdg operations.
            In a 2D layout this scales as O(sqrt(N)); for HBM it is O(1).

  C_T   -- T-gate qubit coverage fraction:
            fraction of data qubits that have at least one T/Tdg operation.
            High C_T means T-gates touch most of the chip, making local
            2D factory placement impossible and motivating HBM.

Skips any benchmark where "steps" is not a list (e.g. "timeout").

Usage:
  python analyze_wisq_routing.py
"""

import json
from pathlib import Path


def analyze(path: Path) -> dict | None:
    with open(path) as f:
        data = json.load(f)

    # Skip timed-out benchmarks
    if not isinstance(data.get("steps"), list):
        return None

    n_qubits = len(data["map"])

    path_lengths = []
    t_qubits = set()

    for step in data["steps"]:
        for op in step:
            if op["op"] in ("t", "tdg"):
                path_lengths.append(len(op["path"]))
                t_qubits.add(op["qubits"][0])

    n_t_ops = len(path_lengths)
    msrd = (sum(path_lengths) / n_t_ops + 1) if n_t_ops > 0 else 0.0
    c_t = len(t_qubits) / n_qubits if n_qubits > 0 else 0.0

    return {
        "file": path.name,
        "n_qubits": n_qubits,
        "n_t_ops": n_t_ops,
        "msrd": round(msrd, 3),
        "c_t": round(c_t, 3),
        "t_qubit_count": len(t_qubits),
        "min_path": min(path_lengths) +1 if path_lengths else None,
        "max_path": max(path_lengths) +1 if path_lengths else None,
    }


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    out_files = sorted(script_dir.glob("*.out"))

    if not out_files:
        print(f"No .out files found in {script_dir}")
        raise SystemExit

    results = []
    skipped = []
    for f in out_files:
        r = analyze(f)
        if r is None:
            skipped.append(f.name)
        else:
            results.append(r)

    if skipped:
        print(f"Skipped (timeout): {', '.join(skipped)}\n")

    if not results:
        print("No valid benchmarks to report.")
        raise SystemExit

    col = max(len(r["file"]) for r in results)
    header = (
        f"{'File':<{col}}  {'N':>4}  {'T-ops':>6}  "
        f"{'MSRD':>7}  {'C_T':>6}  {'min_path':>8}  {'max_path':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['file']:<{col}}  {r['n_qubits']:>4}  {r['n_t_ops']:>6}  "
            f"{r['msrd']:>7.3f}  {r['c_t']:>6.3f}  "
            f"{str(r['min_path']):>8}  {str(r['max_path']):>8}"
        )
    print(f"\nTotal: {len(results)} benchmarks processed, {len(skipped)} skipped.")
