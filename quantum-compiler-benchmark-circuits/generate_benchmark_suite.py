import os
import itertools
import json
from datetime import datetime
from randomized_benchs import RandomCliffordTBenchmark


# === CONFIGURATION ===
OUTPUT_ROOT = "random_benchmarks"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# Parameter sweeps
N_QUBITS = [25, 75, 150]
N_LAYERS = [20, 40, 80]
T_DENSITY = [0.1, 0.3, 0.6]
T_DEPENDENCY = [0.0, 0.5, 0.9]
CNOT_DENSITY = 0.5
CLIFFORD_MIX = 0.3

# === Metadata collection ===
summary = []
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
run_dir = os.path.join(OUTPUT_ROOT, f"bench_suite_{timestamp}")
os.makedirs(run_dir, exist_ok=True)

print(f"📦 Generating benchmark suite in {run_dir}\n")

# === Main generation loop ===
for (nq, nl, td, td_dep) in itertools.product(N_QUBITS, N_LAYERS, T_DENSITY, T_DEPENDENCY):
    name = f"randT_n{nq}_L{nl}_T{td}_dep{td_dep}.qasm"
    path = os.path.join(run_dir, name)

    gen = RandomCliffordTBenchmark(
        n_qubits=nq,
        n_layers=nl,
        t_density=td,
        cnot_density=CNOT_DENSITY,
        t_dependency=td_dep,
        clifford_mix=CLIFFORD_MIX,
        seed=42  # reproducible
    )

    gen.save_qasm(path)
    summary.append({
        "file": name,
        "n_qubits": nq,
        "n_layers": nl,
        "t_density": td,
        "t_dependency": td_dep,
        "cnot_density": CNOT_DENSITY,
        "clifford_mix": CLIFFORD_MIX
    })

# === Summary report ===
summary_txt = os.path.join(run_dir, "benchmark_summary.txt")
summary_json = os.path.join(run_dir, "benchmark_summary.json")

with open(summary_txt, "w") as f:
    f.write(f"Random Clifford+T Benchmark Suite ({timestamp})\n")
    f.write("=" * 70 + "\n")
    f.write(f"{'Benchmark':<35} {'Qubits':>6} {'Layers':>8} {'T_dens':>8} {'T_dep':>8}\n")
    f.write("-" * 70 + "\n")

    for entry in summary:
        f.write(f"{entry['file']:<35} {entry['n_qubits']:>6} {entry['n_layers']:>8} "
                f"{entry['t_density']:>8.2f} {entry['t_dependency']:>8.2f}\n")

    f.write("-" * 70 + "\n")
    f.write(f"Total benchmarks generated: {len(summary)}\n")

with open(summary_json, "w") as jf:
    json.dump(summary, jf, indent=2)

print(f"\n✅ Generated {len(summary)} benchmarks.")
print(f"📝 Summary saved to:\n  - {summary_txt}\n  - {summary_json}")
