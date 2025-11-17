"""
Generate multiple configurations and save them as sheets in one Excel file.
"""

import csv
import re
import json
import os
import math
from openpyxl import Workbook


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
def extract_json_data(bench_name, layout, architecture, wisq_outputs_dir):
    json_path = f"{wisq_outputs_dir}/{bench_name}{layout}-{architecture}_run1.out"
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Cannot find file: {json_path}")

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
# Configuration groups (YOUR LIST)
# ---------------------------------------------------------
CONFIGS = [
    (
        "S0 no_perimeter, compact",
        "shared_none",
        "compact_layout",
        "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13",
        "results/num_steps.csv",
    ),
    (
        "S0 no_perimeter, square_sparse",
        "shared_none",
        "compact_layout",
        "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13",
        "results/num_steps_square_sparse.csv",
    ),
    (
        "S2 LFR no_perimeter, compact",
        "shared_2-route_bottom",
        "compact_layout",
        "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13",
        "results/num_steps.csv",
    ),
    (
        "S2 LFR no_perimeter, square_sparse",
        "shared_2-route_bottom",
        "compact_layout",
        "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13",
        "results/num_steps_square_sparse.csv",
    ),
    (
        "S2 LFR perimeter, compact",
        "shared_2-route_bottom-anchilla_perimeter",
        "compact_layout",
        "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13",
        "results/num_steps.csv",
    ),
    (
        "S2 LFR perimeter, square_sparse",
        "shared_2-route_bottom-anchilla_perimeter",
        "compact_layout",
        "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13",
        "results/num_steps_square_sparse.csv",
    ),
    
    # (
    #     "S2 UFR no_perimeter, compact",
    #     "shared_2-route_upper",
    #     "compact_layout",
    #     "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13",
    #     "results/num_steps.csv",
    # ),
    # (
    #     "S2 UFR no_perimeter, square_sparse",
    #     "shared_2-route_upper",
    #     "compact_layout",
    #     "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13",
    #     "results/num_steps_square_sparse.csv",
    # ),
    (
        "S2 UFR perimeter, compact",
        "shared_2-route_upper-anchilla_perimeter",
        "compact_layout",
        "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13",
        "results/num_steps.csv",
    ),
    # (
    #     "S2 UFR perimeter, square_sparse",
    #     "shared_2-route_upper-anchilla_perimeter",
    #     "compact_layout",
    #     "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13",
    #     "results/num_steps_square_sparse.csv",
    # ),
]


# ---------------------------------------------------------
# Create Excel workbook
# ---------------------------------------------------------
wb = Workbook()
first_sheet = True


# ---------------------------------------------------------
# Main Loop
# ---------------------------------------------------------
for sheet_name, layout, architecture, wisq_dir, input_csv in CONFIGS:

    print(f"Processing: {sheet_name}")

    if first_sheet:
        ws = wb.active
        ws.title = sheet_name
        first_sheet = False
    else:
        ws = wb.create_sheet(title=sheet_name)

    # Write header
    ws.append([
        "bench_name", "logical_qubits", "total_patches",
        "magic_states", "timesteps",
        "factories_15to1", "spacetime_15to1",
        "factories_20to4", "spacetime_20to4",
        "factories_116to12", "spacetime_116to12"
    ])

    # Read input steps CSV
    with open(input_csv, "r") as f_in:
        reader = csv.reader(f_in)
        next(reader)  # skip header

        for row in reader:
            bench_name = row[0].strip()

            logical_qubits = extract_num_logical_qubits(bench_name)
            num_magic_states, num_timesteps, num_total_patches = extract_json_data(
                bench_name, layout, architecture, wisq_dir
            )

            # Factories
            f15 = factories_required(num_magic_states, 1)
            f20 = factories_required(num_magic_states, 4)
            f116 = factories_required(num_magic_states, 12)

            # Spacetime
            st15 = spacetime_product(num_total_patches + 15*f15, num_timesteps)
            st20 = spacetime_product(num_total_patches + 20*f20, num_timesteps)
            st116 = spacetime_product(num_total_patches + 116*f116, num_timesteps)

            ws.append([
                bench_name, logical_qubits, num_total_patches,
                num_magic_states, num_timesteps,
                f15, st15,
                f20, st20,
                f116, st116
            ])

# Save final workbook
output_xlsx = "results/distillation_factories_all_configs.xlsx"
wb.save(output_xlsx)

print(f"✔ Wrote Excel file with all sheets to: {output_xlsx}")
