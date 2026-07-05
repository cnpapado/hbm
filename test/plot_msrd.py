"""
plot_msrd.py
------------
Parse routing_steps.txt and plot MSRD vs N for p=10, 50, 90
as three subfigures in one publication-quality figure.
"""

import re
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# ================== HPCA/ISCA PUBLICATION STYLE ==================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 58,
    "axes.titlesize": 58,
    "axes.labelsize": 58,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 2.0,
    "xtick.labelsize": 58,
    "ytick.labelsize": 58,
    "xtick.major.size": 10,
    "xtick.major.width": 2,
    "ytick.major.size": 10,
    "ytick.major.width": 2,
    "figure.figsize": (45, 15),
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "text.usetex": False,
})

DATA_FILE = Path(__file__).parent / "routing_steps_v2.txt"

ARCH_STYLE = {
    "ARCH_A":           ("Dedicated",      '#1f77b4', "-",  "s"),
    "ARCH_C_shared_2":  ("Shared-2",       '#2ca02c', "-",  "^"),
    "ARCH_C_shared_4":  ("Shared-4",       '#9467bd', "-",  "v"),
    "ARCH_C_shared_8":  ("Shared-8",       "#ff7f0e", "--", "D"),
    "ARCH_C_shared_16": ("Shared-16",      '#e377c2', "--", "p"),
    "no_hbm":           ("2D Baseline",       "#d62728", "-",  "o"),
}

PATTERN = re.compile(
    r"bench_n(\d+)_p(\d+)_(ARCH_A|ARCH_C_shared_\d+|no_hbm)\.out"
)

# ---------------------------------------------------------------------------
# Parse all data
# ---------------------------------------------------------------------------
# data[p][arch][N] = MSRD
data = defaultdict(lambda: defaultdict(dict))

with open(DATA_FILE) as f:
    for line in f:
        line = line.strip()
        m = PATTERN.match(line)
        if not m:
            continue
        n, p, arch = int(m.group(1)), int(m.group(2)), m.group(3)
        parts = line.split()
        try:
            msrd = float(parts[3])
        except (IndexError, ValueError):
            continue
        data[p][arch][n] = msrd

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
probabilities = [10, 50, 90]
titles = ["Low T Intensity (P=10%)", "Medium T Intensity (P=50%)", "High T Intensity (P=90%)"]
x_ticks = [16, 64, 100, 144, 225, 256, 289, 361, 400]

fig, axes = plt.subplots(1, 3, sharey=True)

for i, p in enumerate(probabilities):
    ax = axes[i]
    pdata = data[p]

    for arch, (label, color, ls, marker) in ARCH_STYLE.items():
        if arch not in pdata:
            continue
        points = sorted(pdata[arch].items())
        ns    = [pt[0] for pt in points]
        msrds = [pt[1] for pt in points]
        ax.plot(ns, msrds, color=color, linestyle=ls, marker=marker,
                label=label, linewidth=6, markersize=20)


    ax.set_title(titles[i], pad=30)
    ax.set_xlabel("Grid Size (N)")
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_ticks, rotation=45)
    ax.grid(True, which="major", linestyle="--", alpha=0.4)

    if i == 0:
        ax.set_ylabel("Average MSRD")
        ax.legend(frameon=True, loc="upper left", fontsize=46, ncol=1)

plt.tight_layout()
out_path = Path(__file__).parent / "msrd_vs_N_v2.pdf"
plt.savefig(out_path, bbox_inches="tight")
print(f"Saved: {out_path}")
