import random
import os

# ==========================================
# 1. CORE GENERATOR FUNCTION
# ==========================================
def generate_benchmark(filepath, num_qubits, num_layers, t_gate_prob):
    """
    Generates a single QASM file at the specific 'filepath'.
    """
    with open(filepath, 'w') as f:
        f.write('OPENQASM 2.0;\n')
        f.write('include "qelib1.inc";\n')
        f.write(f'qreg q[{num_qubits}];\n')
        
        for layer in range(num_layers):
            # Randomize qubit order
            qubits = list(range(num_qubits))
            random.shuffle(qubits)
            
            used_qubits = set()
            
            for q in qubits:
                if q in used_qubits:
                    continue
                
                # --- KNOB 1: T-Gate Probability ---
                if random.random() < t_gate_prob:
                    f.write(f't q[{q}];\n')
                    used_qubits.add(q)
                
                # --- KNOB 2: CNOT Probability ---
                elif random.random() < 0.4:
                    partner = -1
                    for p in qubits:
                        if p not in used_qubits and p != q:
                            partner = p
                            break
                    if partner != -1:
                        f.write(f'cx q[{q}],q[{partner}];\n')
                        used_qubits.add(q)
                        used_qubits.add(partner)
                
                # --- KNOB 3: Filler (Clifford) ---
                else:
                    gate = random.choice(['h', 'x', 'z', 's'])
                    f.write(f'{gate} q[{q}];\n')
                    used_qubits.add(q)

# ==========================================
# 2. BATCH EXECUTION
# ==========================================
def main():
    # --- CONFIGURATION KNOBS ---
    qubit_counts = [16, 25, 49, 64, 100, 144, 225]  # Grid sizes
    layer_counts = [10, 50, 100]                    # Depths
    probabilities = [0.1, 0.5, 0.9]                 # Traffic Intensity

    # --- FOLDER CREATION LOGIC ---
    # This is the folder name where files will be saved
    output_dir = "benchmarks_batch"
    
    # Check if it exists; if not, create it.
    os.makedirs(output_dir, exist_ok=True)
    print(f"Target Folder: {os.path.abspath(output_dir)}\n")

    total_files = len(qubit_counts) * len(layer_counts) * len(probabilities)
    current_count = 0

    print(f"Starting batch generation of {total_files} benchmarks...")

    # --- NESTED LOOPS ---
    for n in qubit_counts:
        for l in layer_counts:
            for p in probabilities:
                # Construct readable filename
                # e.g., bench_n100_l50_p90.qasm
                prob_str = int(p * 100)
                filename = f"bench_n{n}_l{l}_p{prob_str}.qasm"
                
                # Combine folder + filename (e.g., benchmarks_batch/bench_n100...)
                full_path = os.path.join(output_dir, filename)
                
                # Generate
                generate_benchmark(full_path, n, l, p)
                
                current_count += 1
                # Print progress every 5 files to keep terminal clean
                if current_count % 5 == 0:
                    print(f"[{current_count}/{total_files}] Generated: {filename}")

    print(f"\n[Success] All {total_files} benchmarks are saved in '{output_dir}/'")

if __name__ == "__main__":
    main()