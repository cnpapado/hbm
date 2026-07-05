import os

def parse_benchmark_file(filename):
    """Parses a benchmark report file and returns a dictionary of benchmark data."""
    data = {}
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found.")
        return data
        
    with open(filename, 'r') as f:
        lines = f.readlines()
        
    start_parsing = False
    for line in lines:
        # Skip to the data section after the separator line
        if '---' in line:
            start_parsing = True
            continue
        # Stop at the final summary separator
        if '===' in line and start_parsing:
            break
        if start_parsing:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                benchmark_name = parts[0]
                values = parts[1:]
                data[benchmark_name] = values
    return data

def format_table(headers, rows):
    """Formats headers and rows into a fixed-width text table."""
    # Determine column widths based on longest content
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
            
    # Construct the table parts
    summary_title = f"================ FINAL SUMMARY ({len(rows)} Benchmarks) ================"
    header_line = " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
    separator = "-" * len(header_line)
    
    output = [summary_title, header_line, separator]
    for row in rows:
        formatted_row = " | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))
        output.append(formatted_row)
    
    output.append("=" * len(header_line))
    return "\n".join(output)

# 1. Define filenames
file1 = 'benchmark_report_final.txt'
file2 = 'benchmark_report_final_square_shared_2.txt'
file3 = 'benchmark_report_final_square_shared_4.txt'

# 2. Parse the files
data1 = parse_benchmark_file(file1)
data2 = parse_benchmark_file(file2)
data3 = parse_benchmark_file(file3)

# 3. Collect all unique benchmark names and sort them
all_benchmarks = sorted(list(set(data1.keys()) | set(data2.keys()) | set(data3.keys())))

# 4. Combine rows in the requested column order:
# Benchmark, NO_HBM, ARCH_A, ARCH_C-s2, ARCH_C-s2-p, ARCH_C-s4, ARCH_C-s4-p
headers = ["Benchmark", "NO_HBM", "ARCH_A", "ARCH_C-s2", "ARCH_C-s2-p", "ARCH_C-s4", "ARCH_C-s4-p"]

combined_rows = []
for bench in all_benchmarks:
    row = [bench]
    # Add values from file 1 (NO_HBM, ARCH_A)
    row.extend(data1.get(bench, ["N/A", "N/A"]))
    # Add values from file 2 (ARCH_C-s2, ARCH_C-s2-p)
    row.extend(data2.get(bench, ["N/A", "N/A"]))
    # Add values from file 3 (ARCH_C-s4, ARCH_C-s4-p)
    row.extend(data3.get(bench, ["N/A", "N/A"]))
    combined_rows.append(row)

# 5. Generate and save the final text output
final_output = format_table(headers, combined_rows)
with open('benchmark_report_combined.txt', 'w') as f:
    f.write(final_output)

print("Combined report saved to 'benchmark_report_combined.txt'.")