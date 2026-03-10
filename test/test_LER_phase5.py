# import numpy as np
# import matplotlib.pyplot as plt
# import pandas as pd

# # ── Load Phase 4 results ──────────────────────────────────────────────────────

# baseline    = np.load("e1_baseline.npy",    allow_pickle=True).item()
# results     = np.load("e1_results.npy",     allow_pickle=True).item()
# error_rates = np.load("e1_error_rates.npy", allow_pickle=True)

# # ── Load routing timestep results from wisq ───────────────────────────────────

# # Expected columns: benchmark, no_hbm_steps, arch_a_steps,
# #                   shared_2_steps, shared_4_steps, shared_8_steps, shared_16_steps
# routing_df = pd.read_csv("routing_results.csv")

# # Drop rows where any architecture timed out (marked as -1 or NaN)
# routing_df = routing_df.replace(-1, np.nan).dropna()

# print(f"Loaded {len(routing_df)} benchmarks")
# print(routing_df.head())
# print()

# # ── Parameters ────────────────────────────────────────────────────────────────

# # Operating point: realistic near-term hardware
# p_operating  = 0.001       # physical error rate
# d_operating  = 7           # code distance
# scenario     = "p'=5p"     # practical inter-layer scenario (main result)
# all_scenarios = ["p'=p", "p'=5p", "p'=10p"]

# sharing_ratios = [2, 4, 8, 16]
# sharing_cols   = {
#     2:  "shared_2_steps",
#     4:  "shared_4_steps",
#     8:  "shared_8_steps",
#     16: "shared_16_steps",
# }

# # ── Helper: get LER at operating point ───────────────────────────────────────

# def get_ler(results_dict, scenario_name, sharing_ratio, d, p_target):
#     """Look up LER at the closest error rate to p_target."""
#     p_idx = np.argmin(np.abs(error_rates - p_target))
#     return results_dict[scenario_name][sharing_ratio][d][p_idx]

# def get_baseline_ler(baseline_dict, d, p_target):
#     p_idx = np.argmin(np.abs(error_rates - p_target))
#     return baseline_dict[d][p_idx]

# # ── Compute total circuit error rate for each benchmark × architecture ────────

# def circuit_error_rate(n_steps, ler_per_step):
#     """Total logical error rate over N_steps rounds."""
#     if n_steps <= 0 or np.isnan(n_steps):
#         return np.nan
#     return 1.0 - (1.0 - ler_per_step) ** int(n_steps)


# # LER per step at operating point
# ler_baseline = get_baseline_ler(baseline, d_operating, p_operating)
# ler_hbm = {
#     sr: get_ler(results, scenario, sr, d_operating, p_operating)
#     for sr in sharing_ratios
# }

# print(f"Operating point: p={p_operating}, d={d_operating}, scenario={scenario}")
# print(f"LER per step — baseline:  {ler_baseline:.6f}")
# for sr in sharing_ratios:
#     print(f"LER per step — shared_{sr}: {ler_hbm[sr]:.6f}  "
#         f"(ratio: {ler_hbm[sr]/ler_baseline:.3f}x)")
# print()

# # Compute circuit-level error rates for all benchmarks
# records = []
# for _, row in routing_df.iterrows():
#     bench = row["benchmark"]
#     n_no_hbm = row["no_hbm_steps"]
#     n_arch_a = row["arch_a_steps"]

#     rec = {
#         "benchmark":        bench,
#         "no_hbm_p_circuit": circuit_error_rate(n_no_hbm, ler_baseline),
#         "arch_a_p_circuit":  circuit_error_rate(n_arch_a, ler_baseline),
#     }

#     for sr in sharing_ratios:
#         col = sharing_cols[sr]
#         if col in row:
#             n_steps = row[col]
#             rec[f"shared_{sr}_p_circuit"] = circuit_error_rate(n_steps, ler_hbm[sr])

#     records.append(rec)

# df = pd.DataFrame(records)

# # Normalise: express all circuit error rates relative to no_hbm baseline
# for sr in sharing_ratios:
#     col = f"shared_{sr}_p_circuit"
#     df[f"shared_{sr}_norm"] = df[col] / df["no_hbm_p_circuit"]

# df["arch_a_norm"] = df["arch_a_p_circuit"] / df["no_hbm_p_circuit"]

# print("Circuit-level error rate (normalised to no_hbm):")
# print(df[["benchmark", "arch_a_norm"] +
#         [f"shared_{sr}_norm" for sr in sharing_ratios]].to_string(index=False))
# print()

# df.to_csv("e1_phase5_results.csv", index=False)
# print("Saved e1_phase5_results.csv")
# print()


# # ── Plot 1: Normalised circuit error rate across benchmarks ───────────────────
# # Bar chart — one group per sharing ratio, bars = benchmarks

# fig, ax = plt.subplots(figsize=(14, 5))

# benchmarks = df["benchmark"].tolist()
# x = np.arange(len(benchmarks))
# cols_to_plot = ["arch_a_norm"] + [f"shared_{sr}_norm" for sr in sharing_ratios]
# labels       = ["ARCH_A (upper bound)"] + [f"shared_{sr}" for sr in sharing_ratios]
# colors       = ["#2ecc71", "#3498db", "#9b59b6", "#e67e22", "#e74c3c"]
# width        = 0.15

# for i, (col, label, color) in enumerate(zip(cols_to_plot, labels, colors)):
#     ax.bar(x + i * width, df[col], width, label=label, color=color, alpha=0.85)

# ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1.2, label="no_hbm baseline")
# ax.set_xticks(x + width * 2)
# ax.set_xticklabels(benchmarks, rotation=45, ha="right", fontsize=8)
# ax.set_ylabel("Circuit LER (normalised to no_hbm)")
# ax.set_title(f"Total Circuit Logical Error Rate — {scenario}  (d={d_operating}, p={p_operating})")
# ax.legend(fontsize=8)
# ax.grid(True, axis="y", alpha=0.3)
# plt.tight_layout()
# plt.savefig("e1_circuit_ler_benchmarks.png", dpi=150)
# print("Saved e1_circuit_ler_benchmarks.png")


# # ── Plot 2: Average normalised LER across all benchmarks ─────────────────────
# # Shows trade-off curve: sharing ratio vs circuit LER (averaged)

# fig, ax = plt.subplots(figsize=(7, 5))

# # One line per scenario
# markers = {"p'=p": "o", "p'=5p": "s", "p'=10p": "^"}
# line_colors = {"p'=p": "#2ecc71", "p'=5p": "#3498db", "p'=10p": "#e74c3c"}

# for scen in all_scenarios:
#     avg_norms = []
#     for sr in sharing_ratios:
#         ler_s = get_ler(results, scen, sr, d_operating, p_operating)
#         norms = []
#         for _, row in routing_df.iterrows():
#             col = sharing_cols[sr]
#             if col in row:
#                 n_steps  = row[col]
#                 n_no_hbm = row["no_hbm_steps"]
#                 p_hbm    = circuit_error_rate(n_steps, ler_s)
#                 p_base   = circuit_error_rate(n_no_hbm, ler_baseline)
#                 if p_base > 0:
#                     norms.append(p_hbm / p_base)
#         avg_norms.append(np.mean(norms))

#     ax.plot(sharing_ratios, avg_norms,
#             marker=markers[scen], color=line_colors[scen],
#             linewidth=2, markersize=7, label=scen)

# ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1.2, label="no_hbm baseline")
# ax.axhline(y=df["arch_a_norm"].mean(), color="#2ecc71",
#             linestyle=":", linewidth=1.5, label="ARCH_A mean")
# ax.set_xlabel("Sharing Ratio (1 magic state per N data qubits)")
# ax.set_ylabel("Avg circuit LER / baseline LER")
# ax.set_xticks(sharing_ratios)
# ax.set_xticklabels([f"shared_{sr}" for sr in sharing_ratios])
# ax.set_title(f"HBM Trade-off: Sharing Ratio vs Circuit LER  (d={d_operating}, p={p_operating})")
# ax.legend(fontsize=9)
# ax.grid(True, alpha=0.3)
# plt.tight_layout()
# plt.savefig("e1_tradeoff_curve.png", dpi=150)
# print("Saved e1_tradeoff_curve.png")


# # ── Plot 3: Two-axis plot — timesteps vs circuit LER ─────────────────────────
# # The key trade-off plot for the paper

# fig, ax1 = plt.subplots(figsize=(7, 5))
# ax2 = ax1.twinx()

# avg_steps_norm = []
# avg_ler_norm   = []

# for sr in sharing_ratios:
#     col   = sharing_cols[sr]
#     ler_s = get_ler(results, scenario, sr, d_operating, p_operating)

#     step_ratios = []
#     ler_ratios  = []
#     for _, row in routing_df.iterrows():
#         if col in row:
#             n_hbm    = row[col]
#             n_no_hbm = row["no_hbm_steps"]
#             p_hbm    = circuit_error_rate(n_hbm, ler_s)
#             p_base   = circuit_error_rate(n_no_hbm, ler_baseline)
#             if n_no_hbm > 0 and p_base > 0:
#                 step_ratios.append(n_hbm / n_no_hbm)
#                 ler_ratios.append(p_hbm / p_base)

#     avg_steps_norm.append(np.mean(step_ratios))
#     avg_ler_norm.append(np.mean(ler_ratios))

# x = np.arange(len(sharing_ratios))
# ax1.bar(x - 0.2, avg_steps_norm, 0.35, label="Routing timesteps (norm)",
#         color="#3498db", alpha=0.8)
# ax2.bar(x + 0.2, avg_ler_norm,   0.35, label="Circuit LER (norm)",
#         color="#e74c3c", alpha=0.8)

# ax1.axhline(y=1.0, color="black", linestyle="--", linewidth=1)
# ax2.axhline(y=1.0, color="black", linestyle="--", linewidth=1)
# ax1.set_xlabel("Sharing Ratio")
# ax1.set_ylabel("Normalised Routing Timesteps", color="#3498db")
# ax2.set_ylabel("Normalised Circuit LER",       color="#e74c3c")
# ax1.set_xticks(x)
# ax1.set_xticklabels([f"shared_{sr}" for sr in sharing_ratios])
# ax1.set_title(f"HBM: Timestep Reduction vs LER Impact  ({scenario})")

# lines1, labels1 = ax1.get_legend_handles_labels()
# lines2, labels2 = ax2.get_legend_handles_labels()
# ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8)
# ax1.grid(True, axis="y", alpha=0.2)
# plt.tight_layout()
# plt.savefig("e1_timesteps_vs_ler.png", dpi=150)
# print("Saved e1_timesteps_vs_ler.png")

# print()
# print("Phase 5 complete.")
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# ── Load Phase 4 results ──────────────────────────────────────────────────────

baseline    = np.load("e1_baseline.npy",    allow_pickle=True).item()
results     = np.load("e1_results.npy",     allow_pickle=True).item()
error_rates = np.load("e1_error_rates.npy", allow_pickle=True)

# ── Load routing timestep results from new_benchmarks_gathered.txt ────────────

def load_benchmarks_txt(filepath):
    """
    Parse the pipe-delimited benchmark results file.
    Columns: Benchmark | Baseline | Arch A | C_S2 | C_S4 | C_S8 | C_S16
    Maps to: benchmark | no_hbm_steps | arch_a_steps | shared_2_steps | ...
    Skips separator lines (=== and ---).
    """
    col_map = {
        "Benchmark": "benchmark",
        "Baseline":  "no_hbm_steps",
        "Arch A":    "arch_a_steps",
        "C_S2":      "shared_2_steps",
        "C_S4":      "shared_4_steps",
        "C_S8":      "shared_8_steps",
        "C_S16":     "shared_16_steps",
    }

    rows = []
    headers = None

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and separator lines
            if not line or set(line.replace("|", "").replace(" ", "")) <= {"=", "-"}:
                continue
            # Split on pipe and strip whitespace from each cell
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if headers is None:
                # First non-separator line is the header
                headers = [col_map.get(p, p) for p in parts]
            else:
                row = {}
                for col, val in zip(headers, parts):
                    if col == "benchmark":
                        row[col] = val
                    else:
                        try:
                            row[col] = int(val)
                        except ValueError:
                            row[col] = np.nan
                rows.append(row)

    return pd.DataFrame(rows, columns=headers)


routing_df = load_benchmarks_txt("new_benchmarks_gathered.txt")

# Drop rows where any architecture timed out (marked as -1 or NaN)
routing_df = routing_df.replace(-1, np.nan).dropna()

print(f"Loaded {len(routing_df)} benchmarks")
print(routing_df.head())
print()

# ── Parameters ────────────────────────────────────────────────────────────────

# Operating point: realistic near-term hardware
p_operating  = 0.005       # physical error rate
d_operating  = 7           # code distance
scenario     = "p'=5p"     # practical inter-layer scenario (main result)
all_scenarios = ["p'=p", "p'=5p", "p'=10p"]

sharing_ratios = [2, 4, 8, 16]
sharing_cols   = {
    2:  "shared_2_steps",
    4:  "shared_4_steps",
    8:  "shared_8_steps",
    16: "shared_16_steps",
}

# ── Helper: get LER at operating point ───────────────────────────────────────

def get_ler(results_dict, scenario_name, sharing_ratio, d, p_target):
    """Look up LER at the closest error rate to p_target."""
    p_idx = np.argmin(np.abs(error_rates - p_target))
    return results_dict[scenario_name][sharing_ratio][d][p_idx]

def get_baseline_ler(baseline_dict, d, p_target):
    p_idx = np.argmin(np.abs(error_rates - p_target))
    return baseline_dict[d][p_idx]

# ── Compute total circuit error rate for each benchmark × architecture ────────

def circuit_error_rate(n_steps, ler_per_step):
    """Total logical error rate over N_steps rounds."""
    if n_steps <= 0 or np.isnan(n_steps):
        return np.nan
    return 1.0 - (1.0 - ler_per_step) ** int(n_steps)


# LER per step at operating point
ler_baseline = get_baseline_ler(baseline, d_operating, p_operating)
ler_hbm = {
    sr: get_ler(results, scenario, sr, d_operating, p_operating)
    for sr in sharing_ratios
}

print(f"Operating point: p={p_operating}, d={d_operating}, scenario={scenario}")
print(f"LER per step — baseline:  {ler_baseline:.6f}")
for sr in sharing_ratios:
    print(f"LER per step — shared_{sr}: {ler_hbm[sr]:.6f}  "
        f"(ratio: {ler_hbm[sr]/ler_baseline:.3f}x)")
print()

# Compute circuit-level error rates for all benchmarks
records = []
for _, row in routing_df.iterrows():
    bench = row["benchmark"]
    n_no_hbm = row["no_hbm_steps"]

    rec = {
        "benchmark":        bench,
        "no_hbm_p_circuit": circuit_error_rate(n_no_hbm, ler_baseline),
    }

    for sr in sharing_ratios:
        col = sharing_cols[sr]
        if col in row:
            n_steps = row[col]
            rec[f"shared_{sr}_p_circuit"] = circuit_error_rate(n_steps, ler_hbm[sr])

    records.append(rec)

df = pd.DataFrame(records)

# Normalise: express all circuit error rates relative to no_hbm baseline
for sr in sharing_ratios:
    col = f"shared_{sr}_p_circuit"
    df[f"shared_{sr}_norm"] = df[col] / df["no_hbm_p_circuit"]

print("Circuit-level error rate (normalised to no_hbm):")
print(df[["benchmark"] +
        [f"shared_{sr}_norm" for sr in sharing_ratios]].to_string(index=False))
print()

df.to_csv("e1_phase5_results.csv", index=False)
print("Saved e1_phase5_results.csv")
print()


# ── Plot 1: Normalised circuit error rate across benchmarks ───────────────────
# Bar chart — one group per sharing ratio, bars = benchmarks

fig, ax = plt.subplots(figsize=(14, 5))

benchmarks = df["benchmark"].tolist()
x = np.arange(len(benchmarks))
cols_to_plot = [f"shared_{sr}_norm" for sr in sharing_ratios]
labels       = [f"shared_{sr}" for sr in sharing_ratios]
colors       = ["#3498db", "#9b59b6", "#e67e22", "#e74c3c"]
width        = 0.15

for i, (col, label, color) in enumerate(zip(cols_to_plot, labels, colors)):
    ax.bar(x + i * width, df[col], width, label=label, color=color, alpha=0.85)

ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1.2, label="no_hbm baseline")
ax.set_xticks(x + width * 2)
ax.set_xticklabels(benchmarks, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Circuit LER (normalised to no_hbm)")
ax.set_title(f"Total Circuit Logical Error Rate — {scenario}  (d={d_operating}, p={p_operating})")
ax.legend(fontsize=8)
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("e1_circuit_ler_benchmarks.png", dpi=150)
print("Saved e1_circuit_ler_benchmarks.png")


# ── Plot 2: Average normalised LER across all benchmarks ─────────────────────
# Shows trade-off curve: sharing ratio vs circuit LER (averaged)

fig, ax = plt.subplots(figsize=(7, 5))

# One line per scenario
markers = {"p'=p": "o", "p'=5p": "s", "p'=10p": "^"}
line_colors = {"p'=p": "#2ecc71", "p'=5p": "#3498db", "p'=10p": "#e74c3c"}

for scen in all_scenarios:
    avg_norms = []
    for sr in sharing_ratios:
        ler_s = get_ler(results, scen, sr, d_operating, p_operating)
        norms = []
        for _, row in routing_df.iterrows():
            col = sharing_cols[sr]
            if col in row:
                n_steps  = row[col]
                n_no_hbm = row["no_hbm_steps"]
                p_hbm    = circuit_error_rate(n_steps, ler_s)
                p_base   = circuit_error_rate(n_no_hbm, ler_baseline)
                if p_base > 0:
                    norms.append(p_hbm / p_base)
        avg_norms.append(np.mean(norms))

    ax.plot(sharing_ratios, avg_norms,
            marker=markers[scen], color=line_colors[scen],
            linewidth=2, markersize=7, label=scen)

ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1.2, label="no_hbm baseline")
ax.set_xlabel("Sharing Ratio (1 magic state per N data qubits)")
ax.set_ylabel("Avg circuit LER / baseline LER")
ax.set_xticks(sharing_ratios)
ax.set_xticklabels([f"shared_{sr}" for sr in sharing_ratios])
ax.set_title(f"HBM Trade-off: Sharing Ratio vs Circuit LER  (d={d_operating}, p={p_operating})")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("e1_tradeoff_curve.png", dpi=150)
print("Saved e1_tradeoff_curve.png")


# ── Plot 3: Two-axis plot — timesteps vs circuit LER ─────────────────────────
# The key trade-off plot for the paper

fig, ax1 = plt.subplots(figsize=(7, 5))
ax2 = ax1.twinx()

avg_steps_norm = []
avg_ler_norm   = []

for sr in sharing_ratios:
    col   = sharing_cols[sr]
    ler_s = get_ler(results, scenario, sr, d_operating, p_operating)

    step_ratios = []
    ler_ratios  = []
    for _, row in routing_df.iterrows():
        if col in row:
            n_hbm    = row[col]
            n_no_hbm = row["no_hbm_steps"]
            p_hbm    = circuit_error_rate(n_hbm, ler_s)
            p_base   = circuit_error_rate(n_no_hbm, ler_baseline)
            if n_no_hbm > 0 and p_base > 0:
                step_ratios.append(n_hbm / n_no_hbm)
                ler_ratios.append(p_hbm / p_base)

    avg_steps_norm.append(np.mean(step_ratios))
    avg_ler_norm.append(np.mean(ler_ratios))

x = np.arange(len(sharing_ratios))
ax1.bar(x - 0.2, avg_steps_norm, 0.35, label="Routing timesteps (norm)",
        color="#3498db", alpha=0.8)
ax2.bar(x + 0.2, avg_ler_norm,   0.35, label="Circuit LER (norm)",
        color="#e74c3c", alpha=0.8)

ax1.axhline(y=1.0, color="black", linestyle="--", linewidth=1)
ax2.axhline(y=1.0, color="black", linestyle="--", linewidth=1)
ax1.set_xlabel("Sharing Ratio")
ax1.set_ylabel("Normalised Routing Timesteps", color="#3498db")
ax2.set_ylabel("Normalised Circuit LER",       color="#e74c3c")
ax1.set_xticks(x)
ax1.set_xticklabels([f"shared_{sr}" for sr in sharing_ratios])
ax1.set_title(f"HBM: Timestep Reduction vs LER Impact  ({scenario})")

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8)
ax1.grid(True, axis="y", alpha=0.2)
plt.tight_layout()
plt.savefig("e1_timesteps_vs_ler.png", dpi=150)
print("Saved e1_timesteps_vs_ler.png")

print()
print("Phase 5 complete.")
