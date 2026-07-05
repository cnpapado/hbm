import os
import glob
import re

def verify_universal_cx_counts(directory="benchmarks_universal_cx"):
    """
    Scans the directory for QASM files, counts the CNOT ('cx') gates,
    and prints a table verifying that all files have the exact same CX count.
    Skips any benchmark configuration that is missing a file.
    """
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    qasm_files = glob.glob(os.path.join(directory, "*.qasm"))
    
    if not qasm_files:
        print(f"No .qasm files found in '{directory}'.")
        return

    # Dictionary to hold the counts: results[N][P] = total_cx_count
    results = {}

    for filepath in qasm_files:
        filename = os.path.basename(filepath)
        
        # Extract N and P from the new filename format (e.g., bench_n100_p90.qasm)
        match = re.search(r'bench_n(\d+)_p(\d+)\.qasm', filename)
        if not match:
            continue
            
        n = int(match.group(1))
        p = int(match.group(2))
        
        # Count lines that start with 'cx '
        cx_count = 0
        with open(filepath, 'r') as f:
            for line in f:
                if line.lstrip().startswith('cx '):
                    cx_count += 1
                    
        # Store in nested dictionary
        if n not in results:
            results[n] = {}
            
        results[n][p] = cx_count

    # --- PRINT THE VERIFICATION TABLE ---
    print("================ UNIVERSAL TWO-QUBIT GATE (CX) VERIFICATION ================")
    print(f"{'Grid (N)':<10} | {'P=10 (CX Count)':<17} | {'P=50 (CX Count)':<17} | {'P=90 (CX Count)':<17} | {'Status'}")
    print("-" * 85)

    for n in sorted(results.keys()):
        counts = results[n]
        
        # Get counts (default to 'N/A' if missing)
        c_10 = counts.get(10, 'N/A')
        c_50 = counts.get(50, 'N/A')
        c_90 = counts.get(90, 'N/A')
        
        # If any entry for this grid size is missing (N/A), skip this benchmark entirely
        if 'N/A' in [c_10, c_50, c_90]:
            continue
            
        # Check if all three traffic levels share the exact same count
        if c_10 == c_50 == c_90:
            status = "✓ MATCH"
        else:
            status = "✗ MISMATCH"
            
        print(f"N={n:<8} | {c_10:<17} | {c_50:<17} | {c_90:<17} | {status}")
            
    print("============================================================================")

if __name__ == "__main__":
    verify_universal_cx_counts()