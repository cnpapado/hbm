import csv
import re
from pathlib import Path

# ------------------------------------------------------------
# Parse QASM: extract operations + qubits
# ------------------------------------------------------------

def parse_qasm(qasm_path):
    ops = []
    qubits = []

    with open(qasm_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            # match gates like: cx q[1],q[2];
            m = re.match(r"(\w+)\s+(.*);", line)
            if not m:
                continue

            op = m.group(1)
            rest = m.group(2)
            qs = re.findall(r"q\[(\d+)\]", rest)
            qs = [int(x) for x in qs]

            ops.append(op)
            qubits.append(qs)

    return ops, qubits

# ------------------------------------------------------------
# Compute minimal timesteps (dependencies only)
# ------------------------------------------------------------

def min_timesteps_from_ops(ops, qubits):
    dependencies = []

    for i in range(len(ops)):
        deps = []
        for j in range(i):
            # if they share a qubit
            if set(qubits[i]) & set(qubits[j]):
                deps.append(j)
        dependencies.append(deps)

    if not dependencies:
        return 0

    levels = [0] * len(dependencies)

    for i, deps in enumerate(dependencies):
        if deps:
            levels[i] = 1 + max(levels[d] for d in deps)
        else:
            levels[i] = 0

    return max(levels) + 1

# ------------------------------------------------------------
# Main processing: CSV → QASM → CSV
# ------------------------------------------------------------

def process_benchmarks(input_csv, output_csv):
    input_csv = Path(input_csv)
    output_csv = Path(output_csv)

    qasm_base = Path("/home/c/hbm/quantum-compiler-benchmark-circuits/jku_suite")

    rows_out = []

    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)

        if "Benchmark" not in reader.fieldnames:
            raise ValueError(f"Input CSV missing required 'Benchmark' column. Found: {reader.fieldnames}")

        for row in reader:
            bench = row["Benchmark"].strip()
            qasm_path = qasm_base / f"{bench}.qasm"

            try:
                ops, qubits = parse_qasm(qasm_path)
                steps = min_timesteps_from_ops(ops, qubits)
            except Exception as e:
                steps = None
                print(f"Error processing {bench}: {e}")

            rows_out.append([bench, steps])

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Benchmark", "min_timesteps"])
        writer.writerows(rows_out)

    print(f"✅ Done. Output written to {output_csv}")

# Example:
process_benchmarks("results_summary_1800.csv", "ideal_timesteps.csv")
