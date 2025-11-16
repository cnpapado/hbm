import pandas as pd
import matplotlib.pyplot as plt
import argparse
import re
import json
import os

# architecture = "compact_layout"
# wisq_outputs_dir = "results/output_parallel_3600_compact/output_parallel_3600/bench_suite_2025-11-15_05-34-13"
# num_steps = pd.read_csv('results/num_steps.csv')
# routing = pd.read_csv('results/routing_footprint.csv')

architecture = "compact_layout"
wisq_outputs_dir = "results/output_parallel_3600_square_sparse/output_parallel_3600_square_sparse/bench_suite_2025-11-15_05-34-13"
num_steps = pd.read_csv('results/num_steps_square_sparse.csv')
routing = pd.read_csv('results/routing_footprint_square_sparse.csv')

# ================== ARGUMENT PARSER ==================
parser = argparse.ArgumentParser(description="Generate speedup plots or improvement metrics")
parser.add_argument(
    "--metric",
    choices=["speedup", "footprint", "tdp"],
    required=True,
    help="Metric to plot: speedup, footprint, or tdp"
)
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
args = parser.parse_args()

normalize_qubits = args.normalize_qubits
normalize_magic_states = args.normalize_magic_states
metric = args.metric

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
    "figure.figsize": (8, 5),
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,

    # Colormap
    "image.cmap": "viridis"
})
plt.rcParams["text.usetex"] = False

# ======================= LOAD DATA ==========================
t = pd.read_csv('t_gate_analysis_summary_smaller_v3.csv')

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
    json_path = f"{wisq_outputs_dir}/{bench_name}{layout}_run1.out"
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Cannot find magic state file: {json_path}")
    with open(json_path, "r") as f:
        data = json.load(f)
    return len(data["arch"]["magic_states"])

# ======================= LAYOUTS TO COMPARE ==========================
layout_pairs = [
    ("shared_none-"+architecture,
     "Shared-0 HBM organization",
     "shared_none"),

    ("shared_2-route_bottom-anchilla_perimeter-"+architecture,
     "Shared-2 HBM organization with Lower-First Routing",
     "bottom_anchilla_perimeter"),

    ("shared_2-route_bottom-"+architecture,
     "Shared-2 HBM organization with Lower-First Routing",
     "bottom"),

    ("shared_2-route_upper-anchilla_perimeter-"+architecture,
     "Shared-2 HBM organization with Upper-First Routing",
     "upper_anchilla_perimeter"),

    ("shared_none-anchilla_perimeter-"+architecture,
     "Shared-0 HBM organization",
     "shared_none_anchilla_perimeter")
]

# ======================= GENERATE PLOTS ==========================
for layout, title, basefilename in layout_pairs:

    if layout not in num_steps.columns:
        print(f"Skipping missing column: {layout}")
        continue

    if metric == "speedup":
        sp = num_steps['no_hbm-'+architecture] / num_steps[layout]

    elif metric == "tdp":
        sp = (num_steps['no_hbm-'+architecture] * routing['no_hbm-'+architecture]) / (
             num_steps[layout] * routing[layout])

    elif metric == "footprint":
        sp = routing['no_hbm-'+architecture] / routing[layout]

    # Compute y_value depending on normalization
    if normalize_qubits:
        t["y_value"] = t["avg_t_parallelism"] / t["num_qubits"]
        ylabel = "Avg. T-parallelism normalized to num of qubits"
        normalization_mode = "normalized_qubits"
    elif normalize_magic_states:
        t["y_value"] = t.apply(lambda row: row["avg_t_parallelism"] / extract_magic_states(row["bench_name"], layout), axis=1)
        ylabel = "Avg. T-parallelism normalized to num of magic states"
        normalization_mode = "normalized_magic_states"
    else:
        t["y_value"] = t["avg_t_parallelism"]
        ylabel = "Average T parallelism"
        normalization_mode = "not_normalized"

    plt.figure(constrained_layout=True)
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
    plt.ylabel(ylabel, wrap=True)
    plt.title(title, wrap=True)

    # Colorbar
    cbar = plt.colorbar(sc)
    colorbar_label = {
        "speedup": "Speedup over planar architecture",
        "footprint": "Routing footprint improvement over planar architecture",
        "tdp": "Time-area product improvement over planar architecture"
    }
    cbar.set_label(colorbar_label[metric], wrap=True)

    # plt.subplots_adjust(left=0.20)
    # plt.tight_layout()

    # Save as PDF — add suffix for normalized case
    outdir = f"plots/square_sparse/{metric}/{normalization_mode}"
    os.makedirs(outdir, exist_ok=True)
    filename = f"{outdir}/{basefilename}.pdf"
    plt.savefig(filename, format="pdf", bbox_inches="tight")
    plt.close()

print("All PDF figures saved successfully.")
