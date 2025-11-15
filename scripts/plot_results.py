import pandas as pd
import matplotlib.pyplot as plt
import argparse
import re
import json
import os

# ================== ARGUMENT PARSER ==================
parser = argparse.ArgumentParser(description="Generate speedup plots or improvement of time-delay product")
parser.add_argument(
    "--normalize_qubits",
    action="store_true",
    help="Normalize average T parallelism by number of qubits"
)
parser.add_argument(
    "--normalize_magic_states",
    action="store_true",
    help="Normalize average T parallelism by number of magic states"
)
parser.add_argument(
    "--time_delay_product",
    action="store_true",
    help="Plot improvement of time-delay product instead of speedup of timesteps"
)
args = parser.parse_args()

normalize_qubits = args.normalize_qubits
normalize_magic_states = args.normalize_magic_states
time_delay_product = args.time_delay_product

# ================== HPCA/ISCA PUBLICATION STYLE ==================
plt.rcParams.update({
    # Fonts
    "font.family": "serif",
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",

    # Axis + ticks
    "axes.linewidth": 1.8,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "xtick.major.size": 6,
    "xtick.major.width": 1.6,
    "ytick.major.size": 6,
    "ytick.major.width": 1.6,

    # Figure
    "figure.figsize": (7, 5),
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,

    # Colormap
    "image.cmap": "viridis"
})

# ======================= LOAD DATA ==========================
t = pd.read_csv('t_gate_analysis_summary_smaller_v3.csv')
num_steps = pd.read_csv('num_steps.csv')
routing = pd.read_csv('routing_footprint.csv')

# Ensure bench_name is the index for easy lookup
num_steps.set_index('bench_name', inplace=True)
routing.set_index('bench_name', inplace=True)

t['bench_name'] = t['file'].str.replace('.qasm','', regex=False)

# ======================= EXTRACT NUMBER OF QUBITS ==========================
def extract_qubits(name):
    m = re.search(r'_n(\d+)_', name)
    if m:
        return int(m.group(1))
    else:
        raise ValueError(f"Cannot extract qubit count from: {name}")

t["num_qubits"] = t["bench_name"].apply(extract_qubits)

# ======================= EXTRACT NUMBER OF MAGIC STATES ==================
def extract_magic_states(bench_name, layout):
    json_path = f"/home/c/hbm/scripts/output_parallel_3600/output_parallel_3600/bench_suite_2025-11-15_05-34-13/{bench_name}{layout}_run1.out"
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Cannot find magic state file: {json_path}")
    with open(json_path, "r") as f:
        data = json.load(f)
    return len(data["arch"]["magic_states"])

# ======================= LAYOUTS TO COMPARE ==========================
layout_pairs = [
    ("shared_none-compact_layout",
     "shared_none",
     "speedup_shared_none"),

    ("shared_2-route_bottom-anchilla_perimeter-compact_layout",
     "shared_2-route_bottom_anchilla_perimeter",
     "speedup_bottom_anchilla_perimeter"),

    ("shared_2-route_bottom-compact_layout",
     "shared_2-route_bottom",
     "speedup_bottom"),

    ("shared_2-route_upper-anchilla_perimeter-compact_layout",
     "shared_2-route_upper_anchilla_perimeter",
     "speedup_upper_anchilla_perimeter"),

    ("shared_none-anchilla_perimeter-compact_layout",
     "shared_none_anchilla_perimeter",
     "speedup_none_anchilla_perimeter")
]

# ======================= GENERATE PLOTS ==========================
for layout, title, basefilename in layout_pairs:

    if layout not in num_steps.columns:
        print(f"Skipping missing column: {layout}")
        continue

    # Compute "speedup" or "time-delay product improvement"
    if time_delay_product:
        sp = (num_steps['no_hbm-compact_layout'] * routing['no_hbm-compact_layout']) / (
             num_steps[layout] * routing[layout])
        ylabel_extra = " (time-delay product improvement)"
        filename_suffix = "_tdp"
    else:
        sp = num_steps['no_hbm-compact_layout'] / num_steps[layout]
        ylabel_extra = ""
        filename_suffix = ""

    # Compute y_value depending on normalization
    if normalize_qubits:
        t["y_value"] = t["avg_t_parallelism"] / t["num_qubits"]
        ylabel = "Avg. T-parallelism / qubits" + ylabel_extra
        suffix = "_normalized_qubits" + filename_suffix
    elif normalize_magic_states:
        t["y_value"] = t.apply(lambda row: row["avg_t_parallelism"] / extract_magic_states(row["bench_name"], layout), axis=1)
        ylabel = "Avg. T-parallelism / magic states" + ylabel_extra
        suffix = "_normalized_magic_states" + filename_suffix
    else:
        t["y_value"] = t["avg_t_parallelism"]
        ylabel = "Average T parallelism" + ylabel_extra
        suffix = filename_suffix

    plt.figure()
    sc = plt.scatter(
        t['t_density'],
        t['y_value'],
        c=sp,
        cmap='viridis',
        marker='o',
        s=40,
        edgecolors='none'
    )

    # Labels & title
    plt.xlabel("T density")
    plt.ylabel(ylabel)
    plt.title(title)

    # Colorbar
    cbar = plt.colorbar(sc)
    cbar.set_label("tdp improvement" if time_delay_product else "speedup")

    plt.tight_layout()

    # Save as PDF — add suffix for normalized case
    filename = f"{basefilename}{suffix}.pdf"
    plt.savefig(filename, format="pdf", bbox_inches="tight")
    plt.close()

print("All PDF figures saved successfully.")
