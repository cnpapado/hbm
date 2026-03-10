# import numpy as np
# import matplotlib.pyplot as plt
# import pandas as pd
# import math
# from matplotlib.ticker import MultipleLocator

# # ── Load benchmark data ───────────────────────────────────────────────────────

# def load_benchmarks_txt(filepath):
#     col_map = {
#         "Benchmark": "benchmark",
#         "Baseline":  "no_hbm_steps",
#         "Arch A":    "arch_a_steps",
#         "C_S2":      "shared_2_steps",
#         "C_S4":      "shared_4_steps",
#         "C_S8":      "shared_8_steps",
#         "C_S16":     "shared_16_steps",
#     }
#     rows = []
#     headers = None
#     with open(filepath, "r") as f:
#         for line in f:
#             line = line.strip()
#             if not line or set(line.replace("|", "").replace(" ", "")) <= {"=", "-"}:
#                 continue
#             parts = [p.strip() for p in line.split("|") if p.strip()]
#             if headers is None:
#                 headers = [col_map.get(p, p) for p in parts]
#             else:
#                 row = {}
#                 for col, val in zip(headers, parts):
#                     if col == "benchmark":
#                         row[col] = val
#                     else:
#                         try:
#                             row[col] = int(val)
#                         except ValueError:
#                             row[col] = np.nan
#                 rows.append(row)
#     return pd.DataFrame(rows, columns=headers)


# routing_df = load_benchmarks_txt("new_benchmarks_gathered.txt")

# # ── STV coefficient formulas (all in units of d², which cancels in ratios) ───

# def q_2d_coeff(N):
#     """
#     2D baseline physical qubit coefficient (units of d²).
#     Grid: (2√N+1)² tiles × 2d² each
#     Factories: 4√N factories × 120d² each
#     """
#     sqN = int(round(math.sqrt(N)))
#     grid_dim   = 2 * sqN + 1
#     grid_coeff = (grid_dim ** 2) * 2
#     factory_coeff = (4 * sqN) * 120
#     return grid_coeff + factory_coeff


# def q_hbms_coeff(N, S):
#     """
#     3D HBMS physical qubit coefficient (units of d²) for sharing ratio S.
#     Lower layer:  (2√N-1)² tiles × 2d²
#     Upper ancilla: [(2√N-1)² - N] tiles × 2d²
#     Factories:    ceil(N/S) × 120d²
#     """
#     sqN = int(round(math.sqrt(N)))
#     lower_dim    = 2 * sqN - 1
#     lower_tiles  = lower_dim ** 2
#     lower_coeff  = lower_tiles * 2
#     upper_ancilla_coeff = (lower_tiles - N) * 2
#     factory_coeff = math.ceil(N / S) * 120
#     return lower_coeff + upper_ancilla_coeff + factory_coeff


# # ── Parse benchmark names ─────────────────────────────────────────────────────

# def parse_benchmark(name):
#     parts = name.split("_")
#     N = int(parts[1][1:])
#     p = int(parts[2][1:])
#     return N, p

# routing_df[["N", "intensity"]] = routing_df["benchmark"].apply(
#     lambda x: pd.Series(parse_benchmark(x))
# )

# # ── Compute STV for all benchmarks × configurations ──────────────────────────

# sharing_ratios = [2, 4, 8, 16]
# sharing_cols   = {
#     2:  "shared_2_steps",
#     4:  "shared_4_steps",
#     8:  "shared_8_steps",
#     16: "shared_16_steps",
# }

# records = []
# for _, row in routing_df.iterrows():
#     N         = row["N"]
#     intensity = row["intensity"]
#     bench     = row["benchmark"]

#     q2d      = q_2d_coeff(N)
#     stv_2d   = q2d * row["no_hbm_steps"]

#     rec = {
#         "benchmark":    bench,
#         "N":            N,
#         "intensity":    intensity,
#         "Q_2D":         q2d,
#         "steps_2D":     int(row["no_hbm_steps"]),
#         "STV_2D":       stv_2d,
#     }

#     # Arch A (S=1)
#     if not np.isnan(row["arch_a_steps"]):
#         qa   = q_hbms_coeff(N, 1)
#         stv_a = qa * row["arch_a_steps"]
#         rec["Q_ArchA"]    = qa
#         rec["steps_ArchA"] = int(row["arch_a_steps"])
#         rec["STV_ArchA"]  = stv_a
#         rec["ratio_ArchA"] = stv_2d / stv_a

#     # Sharing ratios
#     for S in sharing_ratios:
#         col = sharing_cols[S]
#         if col in row and not np.isnan(row[col]):
#             qh   = q_hbms_coeff(N, S)
#             stv_h = qh * row[col]
#             rec[f"Q_S{S}"]     = qh
#             rec[f"steps_S{S}"]  = int(row[col])
#             rec[f"STV_S{S}"]   = stv_h
#             rec[f"ratio_S{S}"] = stv_2d / stv_h   # > 1 → HBMS wins

#     records.append(rec)

# df = pd.DataFrame(records)

# # ── Print formatted table ─────────────────────────────────────────────────────

# ratio_cols = ["ratio_ArchA"] + [f"ratio_S{S}" for S in sharing_ratios]
# col_labels = ["Arch A", "C_S2", "C_S4", "C_S8", "C_S16"]

# print("=" * 90)
# print(f"Space-Time Volume Efficiency Ratio  STV_2D / STV_HBMS  (d² cancels — scale-invariant)")
# print(f"Values > 1.0 → HBMS more efficient | Values < 1.0 → 2D baseline more efficient")
# print("=" * 90)
# print(f"{'Benchmark':<22}", end="")
# for lbl in col_labels:
#     print(f"{lbl:>12}", end="")
# print()
# print("-" * 90)

# prev_N = None
# for _, row in df.iterrows():
#     if row["N"] != prev_N:
#         if prev_N is not None:
#             print()
#         prev_N = row["N"]
#     print(f"  {row['benchmark']:<20}", end="")
#     for col in ratio_cols:
#         val = row.get(col, np.nan)
#         if np.isnan(val):
#             print(f"{'—':>12}", end="")
#         else:
#             marker = " ✓" if val > 1.0 else "  "
#             print(f"{val:>10.2f}{marker}", end="")
#     print()

# print("=" * 90)

# df.to_csv("stv_results.csv", index=False)
# print("\nFull results saved to stv_results.csv")

# # ── Plot ──────────────────────────────────────────────────────────────────────

# intensities      = [10, 50, 90]
# intensity_labels = {10: "Low Intensity (P=10%)", 50: "Medium Intensity (P=50%)", 90: "High Intensity (P=90%)"}

# colors  = {"ArchA": "#2ecc71", 2: "#3498db", 4: "#9b59b6", 8: "#e67e22", 16: "#e74c3c"}
# markers = {"ArchA": "D",       2: "o",       4: "s",       8: "^",       16: "v"}
# labels  = {"ArchA": "Arch A",  2: "C\_S2",   4: "C\_S4",   8: "C\_S8",   16: "C\_S16"}

# fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=False)

# for ax, intensity in zip(axes, intensities):
#     subset = df[df["intensity"] == intensity].sort_values("N")

#     # Arch A
#     ax.plot(subset["N"], subset["ratio_ArchA"],
#             color=colors["ArchA"], marker=markers["ArchA"],
#             linewidth=2, markersize=7, linestyle="--",
#             label="Arch A (upper bound)")

#     # Sharing ratios
#     for S in sharing_ratios:
#         col = f"ratio_S{S}"
#         ax.plot(subset["N"], subset[col],
#                 color=colors[S], marker=markers[S],
#                 linewidth=2, markersize=7,
#                 label=f"C\_S{S}")

#     ax.axhline(y=1.0, color="black", linestyle=":", linewidth=1.5, label="Break-even (2D baseline)")
#     ax.set_xlabel("Grid Size N (logical qubits)", fontsize=11)
#     ax.set_ylabel(r"$\mathrm{STV_{2D}\ /\ STV_{HBMS}}$", fontsize=11)
#     ax.set_title(intensity_labels[intensity], fontsize=12, fontweight="bold")
#     ax.set_xticks(subset["N"].tolist())
#     ax.set_xticklabels([str(n) for n in subset["N"].tolist()], rotation=45, fontsize=8)
#     ax.legend(fontsize=8, loc="upper left")
#     ax.grid(True, alpha=0.3)
#     ax.yaxis.set_minor_locator(MultipleLocator(0.25))

# fig.suptitle(
#     r"HBM Space-Time Volume Efficiency Ratio — $d^2$-invariant" "\n"
#     r"(ratio $> 1$ means HBMS requires less total qubit$\times$cycle resources than 2D baseline)",
#     fontsize=13, fontweight="bold"
# )
# plt.tight_layout()
# plt.savefig("stv_efficiency.pdf", dpi=200, bbox_inches="tight")
# print("Saved stv_efficiency.pdf")
# print("\nDone.")


import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import math
from matplotlib.ticker import MultipleLocator

# ── Load benchmark data ───────────────────────────────────────────────────────

def load_benchmarks_txt(filepath):
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
            if not line or set(line.replace("|", "").replace(" ", "")) <= {"=", "-"}:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if headers is None:
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

# ── STV coefficient formulas (all in units of d², which cancels in ratios) ───

def q_2d_coeff(N):
    """
    2D baseline physical qubit coefficient (units of d²).
    Grid: (2√N+1)² tiles × 2d² each
    Factories: 4√N factories × 120d² each
    """
    sqN = int(round(math.sqrt(N)))
    grid_dim   = 2 * sqN + 1
    grid_coeff = (grid_dim ** 2) * 2
    factory_coeff = (4 * sqN) * 120
    return grid_coeff + factory_coeff


def q_hbms_coeff(N, S):
    """
    3D HBMS physical qubit coefficient (units of d²) for sharing ratio S.
    Lower layer:  (2√N-1)² tiles × 2d²
    Upper ancilla: [(2√N-1)² - N] tiles × 2d²
    Factories:    ceil(N/S) × 120d²
    """
    sqN = int(round(math.sqrt(N)))
    lower_dim    = 2 * sqN - 1
    lower_tiles  = lower_dim ** 2
    lower_coeff  = lower_tiles * 2
    upper_ancilla_coeff = (lower_tiles - N) * 2
    factory_coeff = math.ceil(N / S) * 120
    return lower_coeff + upper_ancilla_coeff + factory_coeff


# ── Parse benchmark names ─────────────────────────────────────────────────────

def parse_benchmark(name):
    parts = name.split("_")
    N = int(parts[1][1:])
    p = int(parts[2][1:])
    return N, p

routing_df[["N", "intensity"]] = routing_df["benchmark"].apply(
    lambda x: pd.Series(parse_benchmark(x))
)

# ── Compute STV for all benchmarks × configurations ──────────────────────────

sharing_ratios = [2, 4, 8, 16]
sharing_cols   = {
    2:  "shared_2_steps",
    4:  "shared_4_steps",
    8:  "shared_8_steps",
    16: "shared_16_steps",
}

records = []
for _, row in routing_df.iterrows():
    N         = row["N"]
    intensity = row["intensity"]
    bench     = row["benchmark"]

    q2d      = q_2d_coeff(N)
    stv_2d   = q2d * row["no_hbm_steps"]

    rec = {
        "benchmark":    bench,
        "N":            N,
        "intensity":    intensity,
        "Q_2D":         q2d,
        "steps_2D":     int(row["no_hbm_steps"]),
        "STV_2D":       stv_2d,
    }

    # Arch A (S=1)
    if not np.isnan(row["arch_a_steps"]):
        qa   = q_hbms_coeff(N, 1)
        stv_a = qa * row["arch_a_steps"]
        rec["Q_ArchA"]    = qa
        rec["steps_ArchA"] = int(row["arch_a_steps"])
        rec["STV_ArchA"]  = stv_a
        rec["ratio_ArchA"] = stv_2d / stv_a

    # Sharing ratios
    for S in sharing_ratios:
        col = sharing_cols[S]
        if col in row and not np.isnan(row[col]):
            qh   = q_hbms_coeff(N, S)
            stv_h = qh * row[col]
            rec[f"Q_S{S}"]     = qh
            rec[f"steps_S{S}"]  = int(row[col])
            rec[f"STV_S{S}"]   = stv_h
            rec[f"ratio_S{S}"] = stv_2d / stv_h   # > 1 → HBMS wins

    records.append(rec)

df = pd.DataFrame(records)

# ── Print formatted table ─────────────────────────────────────────────────────

ratio_cols = ["ratio_ArchA"] + [f"ratio_S{S}" for S in sharing_ratios]
col_labels = ["Arch A", "C_S2", "C_S4", "C_S8", "C_S16"]

print("=" * 90)
print(f"Space-Time Volume Efficiency Ratio  STV_2D / STV_HBMS  (d² cancels — scale-invariant)")
print(f"Values > 1.0 → HBMS more efficient | Values < 1.0 → 2D baseline more efficient")
print("=" * 90)
print(f"{'Benchmark':<22}", end="")
for lbl in col_labels:
    print(f"{lbl:>12}", end="")
print()
print("-" * 90)

prev_N = None
for _, row in df.iterrows():
    if row["N"] != prev_N:
        if prev_N is not None:
            print()
        prev_N = row["N"]
    print(f"  {row['benchmark']:<20}", end="")
    for col in ratio_cols:
        val = row.get(col, np.nan)
        if np.isnan(val):
            print(f"{'—':>12}", end="")
        else:
            marker = " ✓" if val > 1.0 else "  "
            print(f"{val:>10.2f}{marker}", end="")
    print()

print("=" * 90)

df.to_csv("stv_results.csv", index=False)
print("\nFull results saved to stv_results.csv")

# ── Plot ──────────────────────────────────────────────────────────────────────

intensities      = [10, 50, 90]
intensity_labels = {10: "Low Intensity (P=10%)", 50: "Medium Intensity (P=50%)", 90: "High Intensity (P=90%)"}

colors  = {"ArchA": "#2ecc71", 2: "#3498db", 4: "#9b59b6", 8: "#e67e22", 16: "#e74c3c"}
markers = {"ArchA": "D",       2: "o",       4: "s",       8: "^",       16: "v"}
labels  = {"ArchA": "Arch A",  2: "C_S2",   4: "C_S4",   8: "C_S8",   16: "C_S16"}

fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=False)

for ax, intensity in zip(axes, intensities):
    subset = df[df["intensity"] == intensity].sort_values("N")

    # Arch A
    ax.plot(subset["N"], subset["ratio_ArchA"],
            color=colors["ArchA"], marker=markers["ArchA"],
            linewidth=2, markersize=7, linestyle="--",
            label="Arch A (upper bound)")

    # Sharing ratios
    for S in sharing_ratios:
        col = f"ratio_S{S}"
        ax.plot(subset["N"], subset[col],
                color=colors[S], marker=markers[S],
                linewidth=2, markersize=7,
                label=f"C_S{S}")

    ax.axhline(y=1.0, color="black", linestyle=":", linewidth=1.5, label="Break-even (2D baseline)")
    ax.set_xlabel("Grid Size N (logical qubits)", fontsize=11)
    ax.set_ylabel(r"$\mathrm{STV_{2D}\ /\ STV_{HBMS}}$", fontsize=11)
    ax.set_title(intensity_labels[intensity], fontsize=12, fontweight="bold")
    ax.set_xticks(subset["N"].tolist())
    ax.set_xticklabels([str(n) for n in subset["N"].tolist()], rotation=45, fontsize=8)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_minor_locator(MultipleLocator(0.25))

fig.suptitle(
    r"HBM Space-Time Volume Efficiency Ratio — $d^2$-invariant" "\n"
    r"(ratio $> 1$ means HBMS requires less total qubit$\times$cycle resources than 2D baseline)",
    fontsize=13, fontweight="bold"
)
plt.tight_layout()
plt.savefig("stv_efficiency.png", dpi=200, bbox_inches="tight")
print("Saved stv_efficiency.png")
print("\nDone.")
