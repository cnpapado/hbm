'''
Fill Theodoro's spreadsheet
'''

import csv
import re
import json
import os
import math


# ---------------------------------------------------------
# Extract num_logical_qubits from benchmark name
# ---------------------------------------------------------
def extract_num_logical_qubits(name):
    m = re.search(r'_n(\d+)_', name)
    if m:
        return int(m.group(1))
    else:
        raise ValueError(f"Cannot extract qubit count from: {name}")


# ---------------------------------------------------------
# Extract data from JSON
# ---------------------------------------------------------
def extract_json_data(bench_name, layout, wisq_outputs_dir):
    json_path = f"{wisq_outputs_dir}/{bench_name}{layout}-{architecture}_run1.out"
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Cannot find magic state file: {json_path}")
    with open(json_path, "r") as f:
        data = json.load(f)

    num_magic_states = len(data["arch"]["magic_states"])
    num_timesteps = len(data["steps"])

    bottom = data["arch"]["height"] * data["arch"]["width"]

    if "shared_none" in layout:
        top = extract_num_logical_qubits(bench_name)
    else:
        top = bottom

    num_total_patches = bottom + top

    return num_magic_states, num_timesteps, num_total_patches


# ---------------------------------------------------------
# Distillation utility
# ---------------------------------------------------------
def factories_required(n_magic, output_per_block):
    return math.ceil(n_magic / output_per_block)


def spacetime_product(area, timesteps):
    return area * timesteps


# ---------------------------------------------------------
# User parameters
# ---------------------------------------------------------

# # COMPACT
# architecture = "compact_layout"
# layout = "shared_2-route_bottom-anchilla_perimeter"
# wisq_outputs_dir = "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13"
# input_file = "results/num_steps.csv"
# output_file = "results/distillation_factories_compact.csv"

# SQUARE SPARSE
architecture = "compact_layout"
layout = "shared_2-route_bottom-anchilla_perimeter"
wisq_outputs_dir = "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13"
input_file = "results/num_steps_square_sparse.csv"
output_file = "results/distillation_factories_square_sparse.csv"

# ---------------------------------------------------------
# Main CSV generation
# ---------------------------------------------------------
with open(input_file, "r", newline="") as f_in, open(output_file, "w", newline="") as f_out:
    reader = csv.reader(f_in)
    writer = csv.writer(f_out)

    header = next(reader)  # skip first row

    writer.writerow([
        "bench_name", "logical_qubits", "total_patches", "magic_states", "timesteps",
        "factories_15to1", "spacetime_15to1",
        "factories_20to4", "spacetime_20to4",
        "factories_116to12", "spacetime_116to12"
    ])

    for row in reader:
        bench_name = row[0].strip()

        logical_qubits = extract_num_logical_qubits(bench_name)
        num_magic_states, num_timesteps, num_total_patches = extract_json_data(
            bench_name, layout, wisq_outputs_dir
        )

        # ---- Number of factories ----
        f15 = factories_required(num_magic_states, 1)      # 15→1
        f20 = factories_required(num_magic_states, 4)      # 20→4
        f116 = factories_required(num_magic_states, 12)    # 116→12

        # ---- Spacetime Products ----
        st15 = spacetime_product(num_total_patches+15*f15, num_timesteps)
        st20 = spacetime_product(num_total_patches+20*f20, num_timesteps)
        st116 = spacetime_product(num_total_patches+116*f116, num_timesteps)

        writer.writerow([
            bench_name, logical_qubits, num_total_patches, num_magic_states, num_timesteps,
            f15, st15,
            f20, st20,
            f116, st116
        ])

print(f"Wrote output to {output_file}")
