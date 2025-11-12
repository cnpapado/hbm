import os
import re
import csv

def count_t_and_total_gates(folder_path, output_file="gate_counts.csv"):
    # Patterns for T/Tdg and any gate
    t_pattern = re.compile(r"\bt\s")
    tdg_pattern = re.compile(r"\btdg\s")
    gate_pattern = re.compile(r"^\s*([a-z]+)\b", re.MULTILINE)  # matches gate names at line start

    results = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".qasm"):
                full_path = os.path.join(root, file)

                try:
                    with open(full_path, "r") as f:
                        content = f.read()
                except Exception as e:
                    print(f"Could not read {full_path}: {e}")
                    continue

                filename_no_ext = os.path.splitext(file)[0]

                # Count T and Tdg
                t_count = len(t_pattern.findall(content)) + len(tdg_pattern.findall(content))

                # Count all gates (excluding qreg, creg, include, and comments)
                all_gate_lines = [
                    match.group(1) for match in gate_pattern.finditer(content)
                    if match.group(1) not in ["qreg", "creg", "include"]
                ]
                total_gates = len(all_gate_lines)

                results.append((filename_no_ext, t_count, total_gates))

    # Save CSV
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Benchmark", "t_count", "total_gates"])
        writer.writerows(results)

    print(f"CSV results saved to {output_file}")


# Example usage:
if __name__ == "__main__":
    folder = "/home/c/hbm/quantum-compiler-benchmark-circuits/jku_suite"  # change to your directory
    count_t_and_total_gates(folder, output_file="gate_counts.csv")
