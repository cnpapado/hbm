import json
from pathlib import Path

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# -----------------------------
# Helpers: parse + classify causes
# -----------------------------
def get_timesteps(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return data["steps"]

def dependency(gate, gate_prev):
    return bool(set(gate["qubits"]) & set(gate_prev["qubits"]))

def routing_conflict(gate, gate_prev):
    return bool(set(gate["path"]) & set(gate_prev["path"]))

def routing_cx_conflict(gate, gate_prev):
    return routing_conflict(gate, gate_prev) and (gate["op"] == "cx" and gate_prev["op"] == "cx")

def routing_t_conflict(gate, gate_prev):
    is_t_like = (gate["op"] in ["t", "tdg"]) or (gate_prev["op"] in ["t", "tdg"])
    return routing_conflict(gate, gate_prev) and is_t_like

def count_cause(wisq_out):
    timesteps = get_timesteps(wisq_out)

    counts = dict(
        dep_only=0, cx_only=0, t_only=0,
        both_dep_cx=0, both_dep_t=0, both_cx_t=0,
        both_all=0, neither=0,
    )

    for n in range(len(timesteps) - 1, 0, -1):
        dep_exists = False
        cx_conflict_exists = False
        t_conflict_exists = False

        for gate in timesteps[n]:
            for gate_prev in timesteps[n - 1]:
                if dependency(gate, gate_prev):
                    dep_exists = True
                if routing_cx_conflict(gate, gate_prev):
                    cx_conflict_exists = True
                if routing_t_conflict(gate, gate_prev):
                    t_conflict_exists = True

        flags = (dep_exists, cx_conflict_exists, t_conflict_exists)

        if flags == (True, False, False):
            counts["dep_only"] += 1
        elif flags == (False, True, False):
            counts["cx_only"] += 1
        elif flags == (False, False, True):
            counts["t_only"] += 1
        elif flags == (True, True, False):
            counts["both_dep_cx"] += 1
        elif flags == (True, False, True):
            counts["both_dep_t"] += 1
        elif flags == (False, True, True):
            counts["both_cx_t"] += 1
        elif flags == (True, True, True):
            counts["both_all"] += 1
        else:
            counts["neither"] += 1

    return counts


# -----------------------------
# Collect per-benchmark series
# -----------------------------
folder = Path("output_parallel_3602/random_benchmarks_smaller_v3/")

# NOTE: exclude "neither" from plotting keys
keys_plot = [
    "t_only", "both_dep_t", "both_cx_t", "both_all",
    "dep_only", "cx_only", "both_dep_cx",
]
keys_all = keys_plot + ["neither"]

series = {k: [] for k in keys_all}

cnt = 0
for out_file in sorted(folder.glob("*.out")):
    with open(out_file, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            continue
    if data.get("steps") == "timeout":
        continue

    c = count_cause(out_file)
    for k in keys_all:
        series[k].append(c[k])

    cnt += 1
    if cnt > 40:
        break

n_bench = len(series[keys_all[0]])
if n_bench == 0:
    raise RuntimeError("No valid benchmarks found.")

# -----------------------------
# Convert to percentages
# IMPORTANT: normalize by *plotted* causes only (excluding 'neither')
# -----------------------------
totals_plot = np.zeros(n_bench, dtype=float)
for k in keys_plot:
    totals_plot += np.array(series[k], dtype=float)

totals_safe = np.where(totals_plot == 0, 1.0, totals_plot)
pct = {k: (np.array(series[k], dtype=float) / totals_safe) * 100.0 for k in keys_plot}

# Sort by magic-state share among plotted causes
ms_share = pct["t_only"] + pct["both_dep_t"] + pct["both_cx_t"] + pct["both_all"]
order = np.argsort(-ms_share)  # descending

for k in keys_plot:
    pct[k] = pct[k][order]

# After sorting, index is simply 1..N left-to-right
x = np.arange(n_bench)
sorted_index = np.arange(1, n_bench + 1)

# -----------------------------
# Publication styling
# -----------------------------
mpl.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

label_map = {
    "dep_only":      "Dependency",
    "cx_only":       "CNOT routing \nconflict",
    "t_only":        "Magic-state \nrouting conflict",
    "both_dep_cx":   "Dependency \n+CNOT routing conflict",
    "both_dep_t":    "Magic-state conflict\n+dependency",
    "both_cx_t":     "Magic-state conflict \n+CNOT routing conflict",
    "both_all":      "magic-state conflict\n+dependency \n+CNOT routing conflict",
    "neither":       "No detected cause",
}

color_map = {
    "t_only":     "#67000D",  # dark red
    "both_cx_t":  "#E6550D",  # orange
    "both_dep_t":  "#08306B",
    "both_all":    "#08519C",
    "dep_only":    "#2171B5",
    "cx_only":     "#4292C6",
    "both_dep_cx": "#6BAED6",
}

hatch_map = {
    "t_only": "",
    "both_dep_t": "///",
    "both_cx_t": "xx",
    "both_all": "\\\\",
    "dep_only": "..",
    "cx_only": "--",
    "both_dep_cx": "oo",
}

# -----------------------------
# Plot: 100% stacked bars (without 'neither')
# -----------------------------
fig, ax = plt.subplots(figsize=(7.0, 2.6), constrained_layout=True)

bottom = np.zeros(n_bench, dtype=float)
for k in keys_plot:
    vals = pct[k]
    bars = ax.bar(
        x, vals, width=0.88,
        bottom=bottom,
        label=label_map[k],
        color=color_map[k],
        edgecolor="black",
        linewidth=0.35,
    )
    for b in bars:
        b.set_hatch(hatch_map[k])
    bottom += vals

ax.set_ylim(0, 100)
ax.set_ylabel("Percentage of timestep boundaries")
ax.set_xlabel("Benchmark index")

# Sparse x ticks (indices after sorting)
if n_bench <= 20:
    tick_pos = np.arange(n_bench)
else:
    tick_pos = np.linspace(0, n_bench - 1, 10).round().astype(int)
ax.set_xticks(tick_pos)
ax.set_xticklabels([str(sorted_index[i]) for i in tick_pos])

ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
ax.yaxis.grid(True, linestyle=":", linewidth=0.6)
ax.set_axisbelow(True)

ax.legend(
    ncol=1,
    frameon=False,
    bbox_to_anchor=(1.02, 1.0),
    loc="upper left",
    borderaxespad=0.0,
    handlelength=1.6,
    labelspacing=0.6,   # more vertical room for multi-line labels
)

fig.savefig("conflicts.pdf", bbox_inches="tight")
# fig.savefig("fig_merge_causes_percent_no_neither.png", dpi=600, bbox_inches="tight")
plt.show()




'''

Causes preventing merging of consecutive timesteps in the routed surface-code schedules. 
Each bar corresponds to one benchmark, and the stacked segments count timestep boundaries 
where gates could not be co-scheduled into a single timestep. 
Segments indicate whether merging was blocked by (i) logical dependencies between gates across the boundary 
(“Dependency"), (ii) two-qubit routing resource conflicts among CNOT routes that contend for the same 
ancilla-mediated path (“CNOT routing conflict”), (iii) magic-state routing conflicts for 
distillation factory traffic (“Magic-state routing conflict”), or combinations thereof.

'''