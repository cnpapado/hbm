import sys
import os
import re
import math
from collections import defaultdict, Counter

# ==========================================
# 1. TOPOLOGY LOGIC (Square Sparse)
# ==========================================
def get_sparse_topology_specs(n_qubits):
    """
    Calculates physical grid size and 2D capacity for Square Sparse layout.
    Logic based on user definition:
    1. Logical Grid: Smallest kx k square to fit N data qubits.
    2. Physical Grid: Side S = 2k + 1 (Checkerboard + borders as seen in image_0.png).
    3. Perimeter: 4S - 4 physical slots on the boundary.
    4. Capacity: 50% of perimeter (alternating Ancilla/Magic constraint).
    """
    if n_qubits == 0: return 0, 0, 0

    # 1. Find logical side k (e.g., N=100 -> k=10)
    k = math.ceil(math.sqrt(n_qubits))
        
    # 2. Physical dimension S (e.g., k=10 -> S=21)
    phys_side = 2 * k + 1
    
    # 3. Calculate Perimeter physical slots
    perimeter_slots = (phys_side * 4) - 4
    
    # 4. Apply 50% Efficiency Constraint
    capacity = int(perimeter_slots * 0.5)
    
    return k, phys_side, capacity

# ==========================================
# 2. CORE ANALYSIS FUNCTION
# ==========================================
def analyze_file(filepath):
    # --- State Tracking ---
    qubit_clock = defaultdict(int)      # When is qubit Q free?
    t_gates_per_layer = defaultdict(int)# T-count per layer
    total_gates = 0
    total_t_gates = 0
    detected_qubits = 0
    max_layer_index = 0

    print(f"Processing: {os.path.basename(filepath)}...")

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip().lower()
                
                # --- Header Parsing (Find N) ---
                if line.startswith('qreg'):
                    match = re.search(r'\[(\d+)\]', line)
                    if match: detected_qubits = int(match.group(1))
                    continue

                # Skip non-gate lines
                if not line or line.startswith('//') or line.startswith('openqasm') or \
                   line.startswith('include') or line.startswith('creg') or line.startswith('barrier'):
                    continue
                
                # --- Parse Instruction ---
                qubit_matches = re.findall(r'\[(\d+)\]', line)
                if not qubit_matches: continue
                involved_qubits = [int(q) for q in qubit_matches]
                
                # --- ASAP Scheduling Logic ---
                start_time = 0
                for q in involved_qubits:
                    start_time = max(start_time, qubit_clock[q])
                
                end_time = start_time + 1
                for q in involved_qubits:
                    qubit_clock[q] = end_time
                
                if start_time > max_layer_index: max_layer_index = start_time
                total_gates += 1

                # --- T-Gate Counting ---
                parts = line.split()
                if parts[0] in ['t', 'tdg']:
                    total_t_gates += 1
                    t_gates_per_layer[start_time] += 1

    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    # --- Finalize Specs based on detected N ---
    if detected_qubits == 0:
        print("[Error] Could not detect 'qreg' size. Skipping.")
        return

    logical_k, phys_S, capacity_limit = get_sparse_topology_specs(detected_qubits)
    circuit_depth = max_layer_index + 1 if total_gates > 0 else 0

    # --- Calculate Aggregate Stats ---
    if t_gates_per_layer:
        max_simul = max(t_gates_per_layer.values())
        avg_simul = sum(t_gates_per_layer.values()) / len(t_gates_per_layer)
    else:
        max_simul = 0; avg_simul = 0

    magic_ratio = (total_t_gates / total_gates * 100) if total_gates > 0 else 0
    
    # Count overloaded layers
    overloaded_layers = sum(1 for count in t_gates_per_layer.values() if count > capacity_limit)

    # ==========================================
    # 3. PRINT THE REPORT (Matching image_2.png style)
    # ==========================================
    print(f"\n{'='*60}")
    print(f" BENCHMARK ANALYSIS REPORT: {os.path.basename(filepath)}")
    print(f"{'='*60}")
    
    print(f"\n[1] ARCHITECTURE SPECS (Square Sparse Topology)")
    print(f"   - Data Qubits:     {detected_qubits} (Logical {logical_k}x{logical_k} arrangement)")
    print(f"   - Physical Grid:   {phys_S}x{phys_S} (Includes required gaps/borders)")
    print(f"   - Circuit Depth:   {circuit_depth} Layers (Reconstructed via ASAP Schedule)")
    
    print(f"\n[2] GATE STATISTICS")
    print(f"   - Total Gates:     {total_gates}")
    print(f"   - Total T-Gates:   {total_t_gates}")
    print(f"   - Magic Ratio:     {magic_ratio:.2f}% (T-gates / Total)")
    
    print(f"\n[3] CONGESTION METRICS (2D vs 3D)")
    print(f"   - Max Simultaneous T-Gates: {max_simul}")
    print(f"   - Avg Simultaneous T-Gates: {avg_simul:.2f}")
    print(f"   - 2D Perimeter Limit:       {capacity_limit} per cycle (Calculated for {phys_S}x{phys_S} grid)")
    
    if overloaded_layers > 0:
        pct_overload = (overloaded_layers / circuit_depth * 100) if circuit_depth > 0 else 0
        print(f"\n   [!] CRITICAL BOTTLENECK DETECTED")
        print(f"       In {overloaded_layers} layers ({pct_overload:.1f}% of execution),")
        print(f"       demand exceeds the 2D perimeter bandwidth.")
        print(f"       (These layers would stall in 2D, but run instantly in 3D)")

    print(f"\n[4] DEMAND HISTOGRAM (First 20 Active Layers)")
    print(f"   Layer ID | Requests | Visualization")
    print(f"   ---------+----------+-----------------------------------")
    
    sorted_layers = sorted(t_gates_per_layer.keys())
    shown_count = 0
    for layer_idx in sorted_layers:
        if shown_count >= 20: break
        
        count = t_gates_per_layer[layer_idx]
        # Visual bar: 1 hash = 1 gate requested
        bar = '#' * count 
        
        alert = " <!! OVERLOAD" if count > capacity_limit else ""
        print(f"   {layer_idx:8d} | {count:8d} | {bar}{alert}")
        shown_count += 1
        
    if len(sorted_layers) > 20:
        print(f"   ... (and {len(sorted_layers) - 20} more active layers)")
    print("\n" + "-"*60 + "\n")

# ==========================================
# 4. MAIN BATCH EXECUTION
# ==========================================
if __name__ == "__main__":
    input_dir = "benchmarks_bursty_cx"
    
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' not found.")
        print("Please run the generator script first.")
        sys.exit(1)
        
    files = [f for f in os.listdir(input_dir) if f.endswith('.qasm')]
    
    if not files:
        print("No .qasm files found in the directory.")
        sys.exit(1)
        
    # Sort files for cleaner output order (optional)
    # Sorting by N, then L, then P requires complex key sorting, 
    # simple alphabetical sort is fine for now.
    files.sort()

    print(f"Found {len(files)} benchmarks. Starting batch analysis...\n")

    for filename in files:
        filepath = os.path.join(input_dir, filename)
        analyze_file(filepath)
        
    print("Batch Analysis Complete.")