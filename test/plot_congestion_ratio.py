# """
# plot_congestion_ratio.py
# ------------------------
# Parse analyzed_benchmarks.txt and plot the T-gate Congestion Ratio:

#     Congestion Ratio = Avg Simul T / 2D Perimeter Limit

# Ratio < 1 : 2D architecture copes (blue bars)
# Ratio > 1 : demand exceeds 2D bandwidth — motivates HBM (red bars)

# Three subfigures: P=10%, P=50%, P=90%.
# """

# import re
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker
# from pathlib import Path
# from collections import defaultdict

# # ================== HPCA/ISCA PUBLICATION STYLE ==================
# plt.rcParams.update({
#     "font.family": "serif",
#     "font.size": 50,
#     "axes.titlesize": 50,
#     "axes.labelsize": 50,
#     "axes.labelweight": "bold",
#     "axes.titleweight": "bold",
#     "axes.linewidth": 2.0,
#     "xtick.labelsize": 50,
#     "ytick.labelsize": 50,
#     "xtick.major.size": 10,
#     "xtick.major.width": 2,
#     "ytick.major.size": 10,
#     "ytick.major.width": 2,
#     "figure.figsize": (45, 15),
#     "savefig.dpi": 300,
#     "pdf.fonttype": 42,
#     "ps.fonttype": 42,
#     "text.usetex": False,
# })

# DATA_FILE = Path(__file__).parent / "analyzed_benchmarks.txt"

# COLOR_OK  = "#1f77b4"   # blue  — ratio < 1 (within bandwidth)
# COLOR_OVR = "#d62728"   # red   — ratio > 1 (exceeds bandwidth)

# # ---------------------------------------------------------------------------
# # Parse
# # ---------------------------------------------------------------------------
# data = defaultdict(dict)

# NAME_RE = re.compile(r"bench_n(\d+)_p(\d+)\.qasm")
# AVG_RE  = re.compile(r"Avg Simul T:\s+([\d.]+)")
# LIM_RE  = re.compile(r"2D Perim Limit:\s+(\d+)")

# with open(DATA_FILE) as f:
#     lines = f.readlines()

# cur_n = cur_p = cur_avg = cur_lim = None

# for line in lines:
#     m = NAME_RE.search(line)
#     if m:
#         cur_n, cur_p = int(m.group(1)), int(m.group(2))
#         cur_avg = cur_lim = None
#         continue
#     if cur_n is None:
#         continue
#     m = AVG_RE.search(line)
#     if m:
#         cur_avg = float(m.group(1)); continue
#     m = LIM_RE.search(line)
#     if m:
#         cur_lim = int(m.group(1)); continue
#     if "---" in line and cur_avg is not None and cur_lim is not None:
#         data[cur_p][cur_n] = cur_avg / cur_lim
#         cur_n = cur_p = cur_avg = cur_lim = None

# # ---------------------------------------------------------------------------
# # Plot
# # ---------------------------------------------------------------------------
# probabilities = [10, 50, 90]
# titles = ["Low T-Intensity (P=10%)", "Medium T-Intensity (P=50%)", "High T-Intensity (P=90%)"]

# fig, axes = plt.subplots(1, 3, sharey=False)

# for i, p in enumerate(probabilities):
#     ax = axes[i]
#     pdata  = data[p]
#     ns     = sorted(pdata.keys())
#     xs     = list(range(len(ns)))
#     ratios = [pdata[n] for n in ns]
#     colors = [COLOR_OVR if r > 1.0 else COLOR_OK for r in ratios]

#     bars = ax.bar(xs, ratios, color=colors, alpha=0.85, width=0.6, zorder=3)

#     # Reference line at ratio = 1
#     ax.axhline(1.0, color="black", linestyle="--", linewidth=4,
#                label="2D Bandwidth Limit", zorder=4)

#     ax.set_title(titles[i], pad=30)
#     ax.set_xlabel("Grid Size (N)")
#     ax.set_xticks(xs)
#     ax.set_xticklabels(ns, rotation=45)
#     ax.set_ylim(bottom=0)
#     ax.grid(True, which="major", linestyle="--", alpha=0.4, zorder=0)

#     if i == 0:
#         ax.set_ylabel("Congestion Ratio\n(Avg Simul T / 2D Limit)")
#         # Manual legend
#         import matplotlib.patches as mpatches
#         import matplotlib.lines as mlines
#         patch_ok  = mpatches.Patch(color=COLOR_OK,  alpha=0.85, label="Within bandwidth")
#         patch_ovr = mpatches.Patch(color=COLOR_OVR, alpha=0.85, label="Exceeds 2D bandwidth")
#         line_ref  = mlines.Line2D([], [], color="black", linestyle="--",
#                                   linewidth=4, label="2D Bandwidth Limit")
#         ax.legend(handles=[patch_ok, patch_ovr, line_ref],
#                   frameon=True, loc="upper left", fontsize=36)

# plt.tight_layout()
# out_path = Path(__file__).parent / "congestion_ratio_vs_N.pdf"
# plt.savefig(out_path, bbox_inches="tight")
# print(f"Saved: {out_path}")


"""
plot_congestion_ratio.py
------------------------
Parse analyzed_benchmarks.txt and plot the T-gate Congestion Ratio:

    Congestion Ratio = Avg Simul T / 2D Perimeter Limit

Ratio < 1 : 2D architecture copes (blue bars)
Ratio > 1 : demand exceeds 2D bandwidth — motivates HBM (red bars)

Three subfigures: P=10%, P=50%, P=90%.
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

DATA_FILE = Path(__file__).parent / "analyzed_benchmarks.txt"

COLOR_OK  = "#1f77b4"   # blue  — ratio < 1 (within bandwidth)
COLOR_OVR = "#d62728"   # red   — ratio > 1 (exceeds bandwidth)

# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------
data = defaultdict(dict)

NAME_RE = re.compile(r"bench_n(\d+)_p(\d+)\.qasm")
AVG_RE  = re.compile(r"Avg Simul T:\s+([\d.]+)")
MAX_RE  = re.compile(r"Max Simul T:\s+([\d.]+)")
LIM_RE  = re.compile(r"2D Perim Limit:\s+(\d+)")

with open(DATA_FILE) as f:
    lines = f.readlines()

cur_n = cur_p = cur_avg = cur_max = cur_lim = None

for line in lines:
    m = NAME_RE.search(line)
    if m:
        cur_n, cur_p = int(m.group(1)), int(m.group(2))
        cur_avg = cur_max = cur_lim = None
        continue
    if cur_n is None:
        continue
    m = AVG_RE.search(line)
    if m:
        cur_avg = float(m.group(1)); continue
    m = MAX_RE.search(line)
    if m:
        cur_max = float(m.group(1)); continue
    m = LIM_RE.search(line)
    if m:
        cur_lim = int(m.group(1)); continue
    if "---" in line and cur_avg is not None and cur_lim is not None:
        data[cur_p][cur_n] = {
            "avg_ratio": cur_avg / cur_lim,
            "max_ratio": cur_max / cur_lim if cur_max else cur_avg / cur_lim,
        }
        cur_n = cur_p = cur_avg = cur_max = cur_lim = None

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
probabilities = [10, 50, 90]
titles = ["Low T-Intensity (P=10%)", "Medium T-Intensity (P=50%)", "High T-Intensity (P=90%)"]

fig, axes = plt.subplots(1, 3, sharey=False)

for i, p in enumerate(probabilities):
    ax = axes[i]
    pdata      = data[p]
    ns         = sorted(pdata.keys())
    xs         = list(range(len(ns)))
    avg_ratios = [pdata[n]["avg_ratio"] for n in ns]
    max_ratios = [pdata[n]["max_ratio"] for n in ns]
    colors     = [COLOR_OVR if r > 1.0 else COLOR_OK for r in avg_ratios]

    bars = ax.bar(xs, avg_ratios, color=colors, alpha=0.85, width=0.6, zorder=3)

    # Whisker caps: upper error bar showing Max Simul T / 2D Limit
    yerr_upper = [max(0.0, mx - avg) for avg, mx in zip(avg_ratios, max_ratios)]
    ax.errorbar(xs, avg_ratios, yerr=[
                    [0.0] * len(xs),   # no lower whisker
                    yerr_upper,
                ],
                fmt="none", ecolor="black", elinewidth=3, capsize=10, capthick=3,
                zorder=5)

    # Reference line at ratio = 1
    ax.axhline(1.0, color="black", linestyle="--", linewidth=4,
               label="2D Bandwidth Limit", zorder=4)

    ax.set_title(titles[i], pad=30)
    ax.set_xlabel("Grid Size (N)")
    ax.set_xticks(xs)
    ax.set_xticklabels(ns, rotation=45)
    ax.set_ylim(bottom=0)
    ax.grid(True, which="major", linestyle="--", alpha=0.4, zorder=0)

    if i == 0:
        # ax.set_ylabel("Congestion Ratio\n(Avg Simul T / 2D Limit)")
        ax.set_ylabel("Congestion Ratio")
        # Manual legend
        import matplotlib.patches as mpatches
        import matplotlib.lines as mlines
        patch_ok  = mpatches.Patch(color=COLOR_OK,  alpha=0.85, label="Avg within 2D bandwidth")
        patch_ovr = mpatches.Patch(color=COLOR_OVR, alpha=0.85, label="Avg exceeds 2D bandwidth")
        line_ref  = mlines.Line2D([], [], color="black", linestyle="--",
                                  linewidth=4, label="2D Bandwidth Limit")
        line_wsk  = mlines.Line2D([], [], color="black", linestyle="-",
                                  linewidth=3, marker="_", markersize=16,
                                  label="Max layer demand")
        ax.legend(handles=[patch_ok, patch_ovr, line_ref, line_wsk],
                  frameon=True, loc="upper left", fontsize=44,
                  bbox_to_anchor=(0.0, 0.88))

plt.tight_layout()
out_path = Path(__file__).parent / "congestion_ratio_vs_N_v3.pdf"
plt.savefig(out_path, bbox_inches="tight")
print(f"Saved: {out_path}")
