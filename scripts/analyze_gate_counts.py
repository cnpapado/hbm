import os
import numpy as np

# === CONFIG ===
benchmarks = "../quantum-compiler-benchmark-circuits/scmr_ko/known_optimal_varied_density_larger"

# derive output filename from the last folder in benchmarks
benchmark_folder_name = os.path.basename(os.path.normpath(benchmarks))
output_file = f"gate_statistics_summary_{benchmark_folder_name}.txt"

def count_gate_ratios(filepath):
    """Compute ratios of CNOT/CZ and T (T+Tdg) gates relative to total gate count."""
    with open(filepath, "r") as f:
        text = f.read().lower()

    # Count gate types
    cnot_count = text.count("cx") + text.count("cz")

    # Aggregate T and Tdg gates
    t_count = (
        text.count("\nt ") + text.count(" t(") + text.count("\tt ") +
        text.count("\ntdg") + text.count(" tdg(") + text.count("\ttdg")
    )

    # Approximate total gate count (any common gate keyword)
    total_gates = sum([
        text.count(k) for k in [
            "cx", "cz", "t ", "tdg", "h", "x", "y", "z",
            "u1", "u2", "u3", "rz", "rx", "ry"
        ]
    ])

    # Avoid divide-by-zero
    if total_gates == 0:
        return 0.0, 0.0

    cnot_ratio = cnot_count / total_gates
    t_ratio = t_count / total_gates
    return cnot_ratio, t_ratio

# Step 1: collect all benchmarks and ratios
gate_data = []  # list of (name, cnot_ratio, t_ratio)
for dirpath, _, filenames in os.walk(benchmarks):
    for filename in filenames:
        if filename.endswith(".qasm"):
            path = os.path.join(dirpath, filename)
            cnot_ratio, t_ratio = count_gate_ratios(path)
            gate_data.append((filename, cnot_ratio, t_ratio))

if not gate_data:
    print("No .qasm files found.")
    exit()

# Step 2: extract all ratios
cnot_ratios = [c for _, c, _ in gate_data]
t_ratios = [t for _, _, t in gate_data]

# Step 3: compute percentile thresholds
def percentile_thresholds(values):
    return np.percentile(values, [33, 66])

cnot_low, cnot_high = percentile_thresholds(cnot_ratios)
t_low, t_high = percentile_thresholds(t_ratios)

# Step 4: classify each benchmark
categories = {"A": [], "B": [], "C": [], "Misc": []}

for name, cnot_r, t_r in gate_data:
    if cnot_r >= cnot_high and t_r <= t_low:
        categories["A"].append((name, cnot_r, t_r))  # High CNOT, Low T
    elif cnot_low <= cnot_r <= cnot_high and t_low <= t_r <= t_high:
        categories["B"].append((name, cnot_r, t_r))  # Medium both
    elif cnot_r <= cnot_low and t_r >= t_high:
        categories["C"].append((name, cnot_r, t_r))  # Low CNOT, High T
    else:
        categories["Misc"].append((name, cnot_r, t_r))  # does not fit neatly

# Step 5: print and save results
with open(output_file, "w") as f:
    f.write(f"=== QASM Benchmark Gate Composition Statistics ({benchmark_folder_name}) ===\n\n")
    f.write(f"CNOT ratio thresholds (low={cnot_low*100:.2f}%, high={cnot_high*100:.2f}%)\n")
    f.write(f"T (T+Tdg) ratio thresholds (low={t_low*100:.2f}%, high={t_high*100:.2f}%)\n\n")

    for label, desc in [
        ("A", "High CNOT/CZ %, Low T %"),
        ("B", "Medium CNOT/T %"),
        ("C", "Low CNOT %, High T %"),
        ("Misc", "Other / Unclassified")
    ]:
        f.write(f"--- Group {label}: {desc} ---\n")
        for name, cnot_r, t_r in categories[label]:
            f.write(f"{name:25s}  CNOT/CZ%={cnot_r*100:6.2f}%  T%={t_r*100:6.2f}%\n")
        f.write("\n")

print(f"Statistics saved to {output_file}")
