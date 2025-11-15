import pandas as pd
import matplotlib.pyplot as plt
import argparse
import re

# ================== ARGUMENT PARSER ==================
parser = argparse.ArgumentParser(description="Generate speedup plots with optional qubit normalization")
parser.add_argument(
    "--normalize_qubits",
    action="store_true",
    help="Normalize average T parallelism by number of qubits"
)
args = parser.parse_args()

normalize = args.normalize_qubits

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
s = pd.read_csv('num_steps.csv')

t['bench_name'] = t['file'].str.replace('.qasm','', regex=False)
merged = pd.merge(t, s, on='bench_name')

# ======================= EXTRACT NUMBER OF QUBITS ==========================
def extract_qubits(name):
    m = re.search(r'_n(\d+)_', name)
    if m:
        return int(m.group(1))
    else:
        raise ValueError(f"Cannot extract qubit count from: {name}")

merged["num_qubits"] = merged["bench_name"].apply(extract_qubits)

# Normalize if requested
if normalize:
    merged["y_value"] = merged["avg_t_parallelism"] / merged["num_qubits"]
    ylabel = "Avg. T-parallelism / qubits"
    suffix = "_normalized"
else:
    merged["y_value"] = merged["avg_t_parallelism"]
    ylabel = "Average T parallelism"
    suffix = ""

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

    if layout not in merged.columns:
        print(f"Skipping missing column: {layout}")
        continue

    # Compute speedup
    sp = merged['no_hbm-compact_layout'] / merged[layout]

    plt.figure()
    sc = plt.scatter(
        merged['t_density'],
        merged['y_value'],
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
    cbar.set_label("speedup")

    plt.tight_layout()

    # Save as PDF — add suffix for normalized case
    filename = f"{basefilename}{suffix}.pdf"
    plt.savefig(filename, format="pdf", bbox_inches="tight")
    plt.close()

print("All PDF figures saved successfully.")
