import random
import os

# ==========================================
# 1. CORE GENERATOR FUNCTION
# ==========================================
def generate_benchmark(filepath, num_qubits, t_gate_prob):
    """
    Generates a single QASM file using Temporal Burstiness.
    Total gate counts are strictly fixed, but T-gates are injected
    in uneven "bursts" to create distributed bottleneck percentages.
    """
    
    # --- GLOBAL FIXED COUNTS ---
    TOTAL_CX = 1000
    TOTAL_CLIFFORDS = 100  
    
    # Calculate exact T-gates needed
    target_t_gates = int((t_gate_prob / (1.0 - t_gate_prob)) * (TOTAL_CX + TOTAL_CLIFFORDS))

    with open(filepath, 'w') as f:
        f.write('OPENQASM 2.0;\n')
        f.write('include "qelib1.inc";\n')
        f.write(f'qreg q[{num_qubits}];\n')
        
        # --- INTRODUCE TEMPORAL BURSTINESS ---
        # Divide the circuit into 5 to 15 random phases
        num_chunks = random.randint(5, 15) 
        
        # Distribute CX and Cliffords roughly evenly to maintain routing connectivity
        cx_per_chunk = [TOTAL_CX // num_chunks] * num_chunks
        cx_per_chunk[-1] += TOTAL_CX % num_chunks
        
        cliff_per_chunk = [TOTAL_CLIFFORDS // num_chunks] * num_chunks
        cliff_per_chunk[-1] += TOTAL_CLIFFORDS % num_chunks
        
        # Distribute T-gates UNEVENLY to create bursts
        # Squaring the random weights makes the peaks sharper and more localized
        weights = [random.random()**2 for _ in range(num_chunks)]
        total_weight = sum(weights)
        
        t_per_chunk = [int(target_t_gates * (w / total_weight)) for w in weights]
        # Fix any rounding differences on the last chunk
        t_per_chunk[-1] += target_t_gates - sum(t_per_chunk)
        
        # --- GENERATE AND WRITE CHUNKS ---
        for i in range(num_chunks):
            chunk_gates = []
            
            # 1. Add CX for this chunk
            for _ in range(cx_per_chunk[i]):
                q1, q2 = random.sample(range(num_qubits), 2)
                chunk_gates.append(f'cx q[{q1}],q[{q2}];\n')
                
            # 2. Add Cliffords for this chunk
            for _ in range(cliff_per_chunk[i]):
                q = random.choice(range(num_qubits))
                gate = random.choice(['h', 'x', 'z', 's'])
                chunk_gates.append(f'{gate} q[{q}];\n')
                
            # 3. Add T-Gates for this chunk
            for _ in range(t_per_chunk[i]):
                q = random.choice(range(num_qubits))
                chunk_gates.append(f't q[{q}];\n')
                
            # Shuffle ONLY within the local chunk, preserving the macro-bursts
            random.shuffle(chunk_gates)
            
            # Write chunk to file
            for gate in chunk_gates:
                f.write(gate)

# ==========================================
# 2. BATCH EXECUTION
# ==========================================
def main():
    # --- CONFIGURATION KNOBS ---
    qubit_counts = [16, 25, 49, 64, 100, 144, 225, 256, 289, 361, 400]  
    probabilities = [0.1, 0.5, 0.9]                 

    # --- FOLDER CREATION LOGIC ---
    output_dir = "benchmarks_bursty_cx"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Target Folder: {os.path.abspath(output_dir)}\n")

    total_files = len(qubit_counts) * len(probabilities)
    current_count = 0

    print(f"Starting batch generation of {total_files} benchmarks...")

    for n in qubit_counts:
        for p in probabilities:
            prob_str = int(p * 100)
            filename = f"bench_n{n}_p{prob_str}.qasm"
            full_path = os.path.join(output_dir, filename)
            
            generate_benchmark(full_path, n, p)
            
            current_count += 1
            if current_count % 3 == 0:
                print(f"[{current_count}/{total_files}] Generated: {filename}")

    print(f"\n[Success] All {total_files} benchmarks are saved in '{output_dir}/'")

if __name__ == "__main__":
    main()