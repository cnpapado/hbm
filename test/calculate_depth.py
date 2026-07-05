import os
import glob
import re

def get_circuit_depth(filepath, num_qubits):
    """
    Calculates the DAG depth (longest path) of an existing QASM file.
    """
    # Each index represents a qubit; the value is its current 'time' (layer)
    qubit_layers = [0] * num_qubits
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip().lower()
            if not line or line.startswith(('openqasm', 'include', 'qreg', 'creg')):
                continue
            
            # --- TWO-QUBIT GATE (CX) ---
            if line.startswith('cx'):
                indices = re.findall(r'q\[(\d+)\]', line)
                if len(indices) == 2:
                    q1, q2 = int(indices[0]), int(indices[1])
                    # Dependency: CX must wait for BOTH qubits to be free
                    # Then it takes 1 timestep
                    finish_time = max(qubit_layers[q1], qubit_layers[q2]) + 1
                    qubit_layers[q1] = finish_time
                    qubit_layers[q2] = finish_time
            
            # --- SINGLE-QUBIT GATE (T, H, X, S, Z) ---
            else:
                index_match = re.search(r'q\[(\d+)\]', line)
                if index_match:
                    q = int(index_match.group(1))
                    # Dependency: This gate must wait for this specific qubit
                    qubit_layers[q] += 1
                    
    return max(qubit_layers)

def main():
    directory = "benchmarks_universal_cx"
    if not os.path.exists(directory):
        print(f"Error: Folder '{directory}' not found.")
        return

    # Find all .qasm files
    files = glob.glob(os.path.join(directory, "*.qasm"))
    
    # Store results: results[N][P] = depth
    results = {}

    for f in files:
        filename = os.path.basename(f)
        match = re.search(r'bench_n(\d+)_p(\d+)\.qasm', filename)
        if match:
            n, p = int(match.group(1)), int(match.group(2))
            depth = get_circuit_depth(f, n)
            
            if n not in results: results[n] = {}
            results[n][p] = depth

    # --- PRINT THE RESULTS ---
    print(f"{'Grid (N)':<10} | {'P=10 Depth':<12} | {'P=50 Depth':<12} | {'P=90 Depth':<12}")
    print("-" * 55)

    for n in sorted(results.keys()):
        # Only print if we have all three files for a balanced comparison
        if all(p in results[n] for p in [10, 50, 90]):
            d10 = results[n][10]
            d50 = results[n][50]
            d90 = results[n][90]
            print(f"N={n:<8} | {d10:<12} | {d50:<12} | {d90:<12}")

if __name__ == "__main__":
    main()