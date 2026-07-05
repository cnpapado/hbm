import sys
import os
import re
import math
import argparse
from collections import defaultdict

# ==========================================
# 1. TOPOLOGY LOGIC (Square Sparse)
# ==========================================
def get_sparse_topology_specs(n_qubits):
    if n_qubits == 0: return 0, 0, 0
    k = math.ceil(math.sqrt(n_qubits))
    phys_side = 2 * k + 1
    perimeter_slots = (phys_side * 4) - 4
    capacity = int(perimeter_slots * 0.5)
    return k, phys_side, capacity

# ==========================================
# 2. CORE ANALYSIS FUNCTION
# ==========================================
def analyze_file(filepath, show_hist=False):
    qubit_clock = defaultdict(int)
    t_gates_per_layer = defaultdict(int)
    total_gates = 0
    total_t_gates = 0
    detected_qubits = 0
    max_layer_index = 0

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip().lower()
                
                # --- Header Parsing ---
                if line.startswith('qreg'):
                    match = re.search(r'\[(\d+)\]', line)
                    if match: detected_qubits = int(match.group(1))
                    continue
                
                # Skip metadata and structural lines
                if not line or any(line.startswith(s) for s in ['//', 'openqasm', 'include', 'creg', 'barrier']):
                    continue
                
                # --- Parse Instruction ---
                parts = line.split()
                if not parts: continue
                opcode = parts[0].replace(';', '')
                
                qubit_matches = re.findall(r'\[(\d+)\]', line)
                if not qubit_matches: continue
                involved_qubits = [int(q) for q in qubit_matches]
                
                # --- FILTER: Depth only tracks T-gates and Two-Qubit gates ---
                is_t_gate = opcode in ['t', 'tdg']
                is_2q_gate = len(involved_qubits) == 2
                
                if is_t_gate or is_2q_gate:
                    # ASAP Scheduling Logic
                    start_time = max([qubit_clock[q] for q in involved_qubits], default=0)
                    end_time = start_time + 1
                    
                    for q in involved_qubits:
                        qubit_clock[q] = end_time
                    
                    if start_time > max_layer_index: 
                        max_layer_index = start_time
                    
                    total_gates += 1 # Only counts T/2Q
                    
                    if is_t_gate:
                        total_t_gates += 1
                        t_gates_per_layer[start_time] += 1
                        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    if detected_qubits == 0: return

    logical_k, phys_S, capacity_limit = get_sparse_topology_specs(detected_qubits)
    circuit_depth = max_layer_index + 1 if total_gates > 0 else 0
    
    # Congestion Stats
    if t_gates_per_layer:
        max_simul = max(t_gates_per_layer.values())
        avg_simul = sum(t_gates_per_layer.values()) / len(t_gates_per_layer)
    else:
        max_simul = 0; avg_simul = 0

    magic_ratio = (total_t_gates / total_gates * 100) if total_gates > 0 else 0
    overloaded_layers = sum(1 for count in t_gates_per_layer.values() if count > capacity_limit)

    # --- REPORT GENERATION ---
    print(f"\n{'='*60}")
    print(f" BENCHMARK ANALYSIS REPORT: {os.path.basename(filepath)}")
    print(f" (Filtering: Depth = T-gates + 2Q-gates only)")
    print(f"{'='*60}")
    
    print(f"\n[1] ARCHITECTURE SPECS (Square Sparse)")
    print(f"   - Data Qubits:     {detected_qubits} (Logical {logical_k}x{logical_k})")
    print(f"   - Physical Grid:   {phys_S}x{phys_S}")
    print(f"   - Circuit Depth:   {circuit_depth} Critical Layers")
    
    print(f"\n[2] GATE STATISTICS")
    print(f"   - Critical Gates:  {total_gates} (T + 2Q)")
    print(f"   - Total T-Gates:   {total_t_gates}")
    print(f"   - Magic Ratio:     {magic_ratio:.2f}% (T / Critical Gates)")
    
    print(f"\n[3] CONGESTION METRICS")
    print(f"   - Max Simul T:     {max_simul}")
    print(f"   - Avg Simul T:     {avg_simul:.2f}")
    print(f"   - 2D Perim Limit:  {capacity_limit} per cycle")
    
    if overloaded_layers > 0:
        pct_overload = (overloaded_layers / circuit_depth * 100) if circuit_depth > 0 else 0
        print(f"\n   [!] CRITICAL BOTTLENECK DETECTED")
        print(f"       In {overloaded_layers} layers ({pct_overload:.1f}% of execution),")
        print(f"       demand exceeds the 2D perimeter bandwidth.")

    if show_hist:
        print(f"\n[4] DEMAND HISTOGRAM (First 20 Active Layers)")
        sorted_layers = sorted(t_gates_per_layer.keys())
        for layer_idx in sorted_layers[:20]:
            count = t_gates_per_layer[layer_idx]
            bar = '#' * count 
            alert = " <!! OVERLOAD" if count > capacity_limit else ""
            print(f"   {layer_idx:8d} | {count:8d} | {bar}{alert}")

    print("\n" + "-"*60)

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze QASM benchmarks focusing on critical gates.")
    parser.add_argument("--show-hist", action="store_true", help="Display the layer demand histogram.")
    parser.add_argument("--dir", type=str, default="benchmarks_bursty_cx", help="Directory of .qasm files.")
    args = parser.parse_args()

    if not os.path.exists(args.dir):
        print(f"Error: Directory '{args.dir}' not found.")
        sys.exit(1)
        
    files = sorted([f for f in os.listdir(args.dir) if f.endswith('.qasm')])
    for filename in files:
        analyze_file(os.path.join(args.dir, filename), show_hist=args.show_hist)