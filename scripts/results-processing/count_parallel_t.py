import os
import pandas as pd
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag

target_gates = {"t", "tdg", "tgs", "tgsdg"}


def load_circuit(path):
    return QuantumCircuit.from_qasm_file(path)


def compute_parallelism(circuit):
    dag = circuit_to_dag(circuit)

    # Store the earliest layer each node can be scheduled
    node_layers = {}
    for node in dag.topological_op_nodes():
        pred_layers = [node_layers[pred] for pred in dag.predecessors(node) if pred in node_layers]
        layer = max(pred_layers) + 1 if pred_layers else 0
        node_layers[node] = layer

    # Collect T/TGS nodes by layer
    parallel_dict = {}
    for node, layer in node_layers.items():
        if hasattr(node, "name") and node.name and node.name.lower() in target_gates:
            parallel_dict.setdefault(layer, []).append(node)

    # Count parallelism
    parallel_counts = []
    for nodes in parallel_dict.values():
        cnt = len(nodes)
        parallel_counts.extend([cnt] * len(nodes))

    if not parallel_counts:
        avg_parallel = 0
        max_parallel = 0
    else:
        avg_parallel = sum(parallel_counts) / len(parallel_counts)
        max_parallel = max(parallel_counts)

    return avg_parallel, max_parallel


def process_benchmarks(input_csv, output_csv, qasm_dir):
    df = pd.read_csv(input_csv)
    benchmarks = df["Benchmark"].tolist()

    results = []

    for bm in benchmarks:
        qasm_path = os.path.join(qasm_dir, bm) + ".qasm"
        # try:
        circuit = load_circuit(qasm_path)
        avg_p, max_p = compute_parallelism(circuit)
        depth = circuit.depth()
        num_qubits = circuit.num_qubits
        results.append([bm, avg_p, max_p, depth, num_qubits])
        # except Exception as e:
        #     results.append([bm, "error", "error", "error", "error"])

    out = pd.DataFrame(results, columns=["Benchmark", "AvgParallelism", "MaxParallelism", "Depth", "NumQubits"])
    out.to_csv(output_csv, index=False)
    return out


# Example usage:
process_benchmarks(
    "results_summary_1800.csv",
    "t_parallelism.csv",
    "/home/c/hbm/quantum-compiler-benchmark-circuits/jku_suite"
)
