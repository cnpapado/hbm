import pandas as pd
import matplotlib.pyplot as plt

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
    "pdf.fonttype": 42,   # Embed TrueType fonts
    "ps.fonttype": 42,

    # Colormap
    "image.cmap": "viridis"
})

# ======================= LOAD DATA ==========================
t = pd.read_csv('t_gate_analysis_summary_smaller_v3.csv')
s = pd.read_csv('num_steps.csv')

t['bench_name'] = t['file'].str.replace('.qasm','', regex=False)
merged = pd.merge(t, s, on='bench_name')

# ======================= LAYOUTS TO COMPARE ==========================
layout_pairs = [
    ("shared_none-compact_layout",
     "Speedup no_hbm → shared_none",
     "speedup_shared_none.pdf"),

    ("shared_2-route_bottom-anchilla_perimeter-compact_layout",
     "Speedup no_hbm → shared_2-route_bottom_anchilla_perimeter",
     "speedup_bottom_anchilla_perimeter.pdf"),

    ("shared_2-route_bottom-compact_layout",
     "Speedup no_hbm → shared_2-route_bottom",
     "speedup_bottom.pdf"),

    ("shared_2-route_upper-anchilla_perimeter-compact_layout",
     "Speedup no_hbm → shared_2-route_upper_anchilla_perimeter",
     "speedup_upper_anchilla_perimeter.pdf"),

    ("shared_none-anchilla_perimeter-compact_layout",
     "Speedup no_hbm → shared_none_anchilla_perimeter",
     "speedup_none_anchilla_perimeter.pdf")
]

# ======================= GENERATE PLOTS ==========================
for layout, title, filename in layout_pairs:

    if layout not in merged.columns:
        print(f"Skipping missing column: {layout}")
        continue

    # Compute speedup
    sp = merged['no_hbm-compact_layout'] / merged[layout]

    plt.figure()
    sc = plt.scatter(
        merged['t_density'],
        merged['avg_t_parallelism'],
        c=sp,
        cmap='viridis',
        marker='o',
        s=40,
        edgecolors='none'
    )

    # Labels & title
    plt.xlabel("T density")
    plt.ylabel("Average T parallelism")
    plt.title(title)

    # Colorbar
    cbar = plt.colorbar(sc)
    cbar.set_label("speedup")

    plt.tight_layout()

    # Save as PDF (vector graphics)
    plt.savefig(filename, format="pdf", bbox_inches="tight")
    plt.close()

print("All PDF figures saved successfully.")
