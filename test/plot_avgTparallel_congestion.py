"""
plot_congestion.py
------------------
Parse analyzed_benchmarks.txt and plot per-subfigure (p=10, 50, 90):
  Left  Y-axis : Avg Simultaneous T-gates  +  2D Perimeter Limit (reference)
  Right Y-axis : % of layers where demand exceeds 2D perimeter bandwidth
"""

import re
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path
from collections import defaultdict

# ================== HPCA/ISCA PUBLICATION STYLE ==================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 50,
    "axes.titlesize": 50,
    "axes.labelsize": 50,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 2.0,
    "xtick.labelsize": 50,
    "ytick.labelsize": 50,
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

DATA_FILE = Path(__file__).parent / "analyzed_benchmarks.txt"

# ---------------------------------------------------------------------------
# Parse analyzed_benchmarks.txt
# ---------------------------------------------------------------------------
# data[p][N] = {avg_simul_t, perim_limit, bottleneck_pct}
data = defaultdict(dict)

NAME_RE  = re.compile(r"bench_n(\d+)_p(\d+)\.qasm")
AVG_RE   = re.compile(r"Avg Simul T:\s+([\d.]+)")
LIM_RE   = re.compile(r"2D Perim Limit:\s+(\d+)")
PCT_RE   = re.compile(r"In\s+\d+\s+layers\s+\((\d+(?:\.\d+)?)%")

with open(DATA_FILE) as f:
    lines = f.readlines()

cur_n = cur_p = cur_avg = cur_lim = None
cur_pct = 0.0

for line in lines:
    m = NAME_RE.search(line)
    if m:
        cur_n, cur_p = int(m.group(1)), int(m.group(2))
        cur_avg = cur_lim = None
        cur_pct = 0.0
        continue
    if cur_n is None:
        continue
    m = AVG_RE.search(line)
    if m:
        cur_avg = float(m.group(1)); continue
    m = LIM_RE.search(line)
    if m:
        cur_lim = int(m.group(1)); continue
    m = PCT_RE.search(line)
    if m:
        cur_pct = float(m.group(1)); continue
    if "---" in line and cur_avg is not None and cur_lim is not None:
        data[cur_p][cur_n] = {"avg": cur_avg, "lim": cur_lim, "pct": cur_pct}
        cur_n = cur_p = cur_avg = cur_lim = None
        cur_pct = 0.0

# Debug: verify parsing
for p in sorted(data):
    print(f"p={p}: {len(data[p])} benchmarks, pcts={[data[p][n]['pct'] for n in sorted(data[p])]}")

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
probabilities = [10, 50, 90]
titles = ["Low T-Intensity (P=10%)", "Medium T-Intensity (P=50%)", "High T-Intensity (P=90%)"]
x_ticks = [16, 64, 100, 144, 225, 256, 289, 361, 400]

COLOR_AVG   = "#1f77b4"   # blue   — Avg Simul T
COLOR_PCT   = "#ff7f0e"   # orange — % bottleneck layers

fig, axes = plt.subplots(1, 3)

for i, p in enumerate(probabilities):
    ax_l = axes[i]
    ax_r = ax_l.twinx()

    pdata  = data[p]
    ns     = sorted(pdata.keys())
    xs     = list(range(len(ns)))          # uniform indices
    avgs   = [pdata[n]["avg"] for n in ns]
    pcts   = [pdata[n]["pct"] for n in ns]

    W = 0.2   # half-width offset in index units

    # Left axis: Avg Simul T bars (shifted left)
    ax_l.bar([x - W for x in xs], avgs, width=W*1.8, color=COLOR_AVG, alpha=0.85,
             label="Avg. Simul. T-gates", zorder=3)

    # Right axis: % bottleneck bars (shifted right)
    ax_r.bar([x + W for x in xs], pcts, width=W*1.8, color=COLOR_PCT, alpha=0.85,
             label="% Layers Exceeding\n2D Bandwidth", zorder=2)

    # Axes labels
    ax_l.set_xlabel("Grid Size (N)")
    ax_l.set_title(titles[i], pad=30)
    ax_l.set_xticks(xs)
    ax_l.set_xticklabels(ns, rotation=45)
    ax_l.set_xlim(-0.5, len(ns) - 0.5)
    ax_r.set_xlim(ax_l.get_xlim())
    ax_l.grid(True, which="major", linestyle="--", alpha=0.4, zorder=0)
    ax_l.set_ylim(bottom=0)

    ax_r.set_ylim(0, 105)
    ax_r.yaxis.set_major_formatter(ticker.PercentFormatter())

    if i == 0:
        ax_l.set_ylabel("Avg. Simultaneous T-gates")
        # Combined legend
        lines_l, labels_l = ax_l.get_legend_handles_labels()
        lines_r, labels_r = ax_r.get_legend_handles_labels()
        ax_l.legend(lines_l + lines_r, labels_l + labels_r,
                    frameon=True, loc="upper left", fontsize=36, ncol=1)

    if i == 2:
        ax_r.set_ylabel("% Layers Exceeding\n2D Bandwidth", color=COLOR_PCT)
        ax_r.tick_params(axis="y", labelcolor=COLOR_PCT)
    else:
        ax_r.set_yticklabels([])

plt.tight_layout()
out_path = Path(__file__).parent / "congestion_vs_N.pdf"
plt.savefig(out_path, bbox_inches="tight")
print(f"Saved: {out_path}")
