import csv
import re

input_file = "results_summary_1800.txt"
output_file = "results_summary_1800.csv"

rows = []

with open(input_file, "r") as f:
    for line in f:
        line = line.strip()

        # Skip separator lines
        if not line or set(line) == {"-"}:
            continue

        # Split on the first "|"
        if "|" in line:
            left, right = line.split("|", 1)
            left = left.strip()

            # right-hand side: split by ANY whitespace
            right_parts = re.split(r"\s+", right.strip())
            parts = [left] + right_parts
        else:
            # no '|' → just split by whitespace (should not happen but safe)
            parts = re.split(r"\s+", line)

        rows.append(parts)

# Write CSV
with open(output_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("Saved CSV:", output_file)
