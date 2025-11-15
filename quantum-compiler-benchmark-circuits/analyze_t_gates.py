import os
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
import numpy as np

def analyze_benchmark(qasm_path):
    try:
        qc = QuantumCircuit.from_qasm_file(qasm_path)
        dag = circuit_to_dag(qc)

        total_gates = 0
        t_gates = 0
        t_parallelism_per_layer = []

        for layer in dag.layers():
            ops = layer["graph"].op_nodes()
            total_gates += len(ops)
            t_count = sum(1 for op in ops if op.name == "t")
            t_gates += t_count
            t_parallelism_per_layer.append(t_count)

        t_density = t_gates / total_gates if total_gates > 0 else 0
        avg_t_parallelism = np.mean([x for x in t_parallelism_per_layer if x > 0]) if t_parallelism_per_layer else 0

        return {
            "file": os.path.basename(qasm_path),
            "total_gates": total_gates,
            "t_gates": t_gates,
            "t_density": round(t_density*100, 2),
            "avg_t_parallelism": round(avg_t_parallelism, 2),
            "layers": len(t_parallelism_per_layer)
        }
    except Exception as e:
        print(f"[!] Failed to process {qasm_path}: {e}")
        return None

def analyze_all(folder):
    results = []
    for filename in os.listdir(folder):
        if filename.endswith(".qasm"):
            full_path = os.path.join(folder, filename)
            res = analyze_benchmark(full_path)
            if res:
                results.append(res)
    return results

if __name__ == "__main__":
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description="Analyze T-gate density and parallelism.")
    parser.add_argument("--sort", choices=["density", "parallelism"], help="Sort by t_density or avg_t_parallelism")
    args = parser.parse_args()

    BENCHMARK_DIR = os.path.join("random_benchmarks_smaller_v3", "bench_suite_2025-11-15_05-34-13")
    txt_output_path = "t_gate_analysis_summary_smaller_v3.txt"
    csv_output_path = "t_gate_analysis_summary_smaller_v3.csv"

    data = analyze_all(BENCHMARK_DIR)
    df = pd.DataFrame(data)

    if args.sort == "density":
        df.sort_values(by="t_density", inplace=True)
    elif args.sort == "parallelism":
        df.sort_values(by="avg_t_parallelism", inplace=True)

    # ---- TXT OUTPUT ----
    with open(txt_output_path, "w") as f:
        for _, row in df.iterrows():
            line = (f"{row['file']}: "
                    f"T-Density={row['t_density']}%, "
                    f"Avg T-Parallelism={row['avg_t_parallelism']}, "
                    f"Layers={row['layers']}")
            print(line)
            f.write(line + "\n")

    print(f"\n[✓] Saved summary to {txt_output_path}")

    # ---- CSV OUTPUT ----
    df.to_csv(csv_output_path, index=False)
    print(f"[✓] Saved CSV to {csv_output_path}")
