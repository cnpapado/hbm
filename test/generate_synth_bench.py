# import random
# import os

# # ==========================================
# # 1. CORE GENERATOR FUNCTION
# # ==========================================
# def generate_benchmark(filepath, num_qubits, num_layers, t_gate_prob):
#     """
#     Generates a single QASM file at the specific 'filepath'.
#     """
#     with open(filepath, 'w') as f:
#         f.write('OPENQASM 2.0;\n')
#         f.write('include "qelib1.inc";\n')
#         f.write(f'qreg q[{num_qubits}];\n')
        
#         for layer in range(num_layers):
#             # Randomize qubit order
#             qubits = list(range(num_qubits))
#             random.shuffle(qubits)
            
#             used_qubits = set()
            
#             for q in qubits:
#                 if q in used_qubits:
#                     continue
                
#                 # --- KNOB 1: T-Gate Probability ---
#                 if random.random() < t_gate_prob:
#                     f.write(f't q[{q}];\n')
#                     used_qubits.add(q)
                
#                 # --- KNOB 2: CNOT Probability ---
#                 elif random.random() < 0.4:
#                     partner = -1
#                     for p in qubits:
#                         if p not in used_qubits and p != q:
#                             partner = p
#                             break
#                     if partner != -1:
#                         f.write(f'cx q[{q}],q[{partner}];\n')
#                         used_qubits.add(q)
#                         used_qubits.add(partner)
                
#                 # --- KNOB 3: Filler (Clifford) ---
#                 else:
#                     gate = random.choice(['h', 'x', 'z', 's'])
#                     f.write(f'{gate} q[{q}];\n')
#                     used_qubits.add(q)

# # ==========================================
# # 2. BATCH EXECUTION
# # ==========================================
# def main():
#     # --- CONFIGURATION KNOBS ---
#     qubit_counts = [16, 25, 49, 64, 100, 144, 225]  # Grid sizes
#     layer_counts = [10, 50, 100]                    # Depths
#     probabilities = [0.1, 0.5, 0.9]                 # Traffic Intensity

#     # --- FOLDER CREATION LOGIC ---
#     # This is the folder name where files will be saved
#     output_dir = "benchmarks_batch"
    
#     # Check if it exists; if not, create it.
#     os.makedirs(output_dir, exist_ok=True)
#     print(f"Target Folder: {os.path.abspath(output_dir)}\n")

#     total_files = len(qubit_counts) * len(layer_counts) * len(probabilities)
#     current_count = 0

#     print(f"Starting batch generation of {total_files} benchmarks...")

#     # --- NESTED LOOPS ---
#     for n in qubit_counts:
#         for l in layer_counts:
#             for p in probabilities:
#                 # Construct readable filename
#                 # e.g., bench_n100_l50_p90.qasm
#                 prob_str = int(p * 100)
#                 filename = f"bench_n{n}_l{l}_p{prob_str}.qasm"
                
#                 # Combine folder + filename (e.g., benchmarks_batch/bench_n100...)
#                 full_path = os.path.join(output_dir, filename)
                
#                 # Generate
#                 generate_benchmark(full_path, n, l, p)
                
#                 current_count += 1
#                 # Print progress every 5 files to keep terminal clean
#                 if current_count % 5 == 0:
#                     print(f"[{current_count}/{total_files}] Generated: {filename}")

#     print(f"\n[Success] All {total_files} benchmarks are saved in '{output_dir}/'")

# if __name__ == "__main__":
#     main()
import random
import os

# ==========================================
# 1. CORE GENERATOR FUNCTION
# ==========================================
def generate_benchmark(filepath, num_qubits, t_gate_prob):
    """
    Generates a single QASM file.
    The absolute total number of CX gates is strictly fixed across ALL benchmarks.
    T-gates are injected to achieve the exact target density P.
    """
    
    # --- GLOBAL FIXED COUNTS ---
    TOTAL_CX = 1000
    TOTAL_CLIFFORDS = 100  # Fixed to keep the base non-T routing constant
    
    # Calculate T-gates needed to achieve the exact target density P.
    # Formula: P = T / (TOTAL_CX + TOTAL_CLIFFORDS + T)
    # T = (P / (1 - P)) * (TOTAL_CX + TOTAL_CLIFFORDS)
    target_t_gates = int((t_gate_prob / (1.0 - t_gate_prob)) * (TOTAL_CX + TOTAL_CLIFFORDS))

    with open(filepath, 'w') as f:
        f.write('OPENQASM 2.0;\n')
        f.write('include "qelib1.inc";\n')
        f.write(f'qreg q[{num_qubits}];\n')
        
        all_gates = []
        
        # 1. Add EXACTLY TOTAL_CX CNOTs
        for _ in range(TOTAL_CX):
            q1, q2 = random.sample(range(num_qubits), 2)
            all_gates.append(f'cx q[{q1}],q[{q2}];\n')
            
        # 2. Add EXACTLY TOTAL_CLIFFORDS Filler Gates
        for _ in range(TOTAL_CLIFFORDS):
            q = random.choice(range(num_qubits))
            gate = random.choice(['h', 'x', 'z', 's'])
            all_gates.append(f'{gate} q[{q}];\n')
            
        # 3. Add EXACTLY target_t_gates T-Gates
        for _ in range(target_t_gates):
            q = random.choice(range(num_qubits))
            all_gates.append(f't q[{q}];\n')
            
        # Shuffle the entire list of gates so they are uniformly mixed
        random.shuffle(all_gates)
        
        # Write everything to file
        for gate in all_gates:
            f.write(gate)

# ==========================================
# 2. BATCH EXECUTION
# ==========================================
def main():
    # --- CONFIGURATION KNOBS ---
    qubit_counts = [16, 25, 49, 64, 100, 144, 225]  # Grid sizes
    probabilities = [0.1, 0.5, 0.9]                 # Traffic Intensity

    # --- FOLDER CREATION LOGIC ---
    output_dir = "/home/ycx0376/hbm/test/benchmarks_universal_cx_2"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Target Folder: {os.path.abspath(output_dir)}\n")

    total_files = len(qubit_counts) * len(probabilities)
    current_count = 0

    print(f"Starting batch generation of {total_files} benchmarks...")

    # --- NESTED LOOPS ---
    for n in qubit_counts:
        for p in probabilities:
            prob_str = int(p * 100)
            # Notice the 'l' (layers) variable is completely removed
            filename = f"bench_n{n}_p{prob_str}.qasm"
            full_path = os.path.join(output_dir, filename)
            
            # Generate
            generate_benchmark(full_path, n, p)
            
            current_count += 1
            if current_count % 3 == 0:
                print(f"[{current_count}/{total_files}] Generated: {filename}")

    print(f"\n[Success] All {total_files} benchmarks are saved in '{output_dir}/'")

if __name__ == "__main__":
    main()