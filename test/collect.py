# {
#     echo -e "\n================ FINAL SUMMARY (63 Benchmarks) ================"
#     printf "%-25s | %-12s | %-12s\n" "Benchmark" "NO_HBM" "ARCH_A"
#     echo "---------------------------------------------------------------"
#     cat *.tmp_res 2>/dev/null | sort | while IFS=" | " read -r name no_hbm arch_a; do
#         printf "%-25s | %-12s | %-12s\n" "$name" "$no_hbm" "$arch_a"
#     done
#     echo "==============================================================="
# }
import os
import glob
import collections
import re

def gather_results(directory="results_temp_compact"):
    results = collections.defaultdict(dict)
    
    # This list stays exactly as it is for file access
    arch_order = [
        "no_hbm", 
        # "ARCH_A", 
        # "ARCH_C_shared_2", 
        # # "ARCH_C_shared_2_perimeter", 
        # "ARCH_C_shared_4", 
        # "ARCH_C_shared_8",
        # "ARCH_C_shared_16"
        # "ARCH_C_shared_4_perimeter"
    ]

    # Mapping long names to short display names for the table headers
    display_names = {
        "no_hbm": "Baseline",
        # "ARCH_A": "Arch A",
        # "ARCH_C_shared_2": "C_S2",
        # # "ARCH_C_shared_2_perimeter": "C_S2_P",
        # "ARCH_C_shared_4": "C_S4",
        # "ARCH_C_shared_8": "C_S8",
        # "ARCH_C_shared_16": "C_S16"
        # "ARCH_C_shared_4_perimeter": "C_S4_P"
    }

    # Set fixed widths for a compact look
    COL_WIDTH = 10
    BENCH_WIDTH = 25

    res_files = glob.glob(os.path.join(directory, "*.res"))
    
    for filepath in res_files:
        try:
            with open(filepath, 'r') as f:
                line = f.read().strip()
                if not line: continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == 3:
                    bench, arch, time = parts
                    results[bench][arch] = time
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    def benchmark_sort_key(name):
        nums = re.findall(r'\d+', name)
        return [int(n) for n in nums] if nums else name

    # --- PRINT TABLE ---
    # Construct header using display_names
    header_parts = [f"{'Benchmark':<{BENCH_WIDTH}}"]
    for arch in arch_order:
        short_name = display_names.get(arch, arch)
        header_parts.append(f"{short_name:<{COL_WIDTH}}")
    
    header = " | ".join(header_parts)
    separator = "-" * len(header)

    print("\n" + "=" * len(header))
    print(header)
    print(separator)

    sorted_benchmarks = sorted(results.keys(), key=benchmark_sort_key)

    for bench in sorted_benchmarks:
        row_parts = [f"{bench:<{BENCH_WIDTH}}"]
        for arch in arch_order:
            val = results[bench].get(arch, "N/A")
            row_parts.append(f"{val:<{COL_WIDTH}}")
        print(" | ".join(row_parts))

    print("=" * len(header) + "\n")

if __name__ == "__main__":
    gather_results()