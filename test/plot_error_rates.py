import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# ================== HPCA/ISCA PUBLICATION STYLE ==================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 39,
    "axes.titlesize": 39,
    "axes.labelsize": 39,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 2.0,
    "xtick.labelsize": 39,
    "ytick.labelsize": 39,
    "xtick.major.size": 6,
    "xtick.major.width": 6,
    "ytick.major.size": 6,
    "ytick.major.width": 6,
    "figure.figsize": (15, 15),
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "text.usetex": False
})

# ================== 1. DATASET ==================
data = [
    ["bench_n100_l100_p10", 244, 215], ["bench_n100_l10_p10", 22, 19],
    ["bench_n100_l10_p50", 26, 13],    ["bench_n100_l10_p90", 41, 10],
    ["bench_n100_l50_p10", 118, 101],  ["bench_n100_l50_p50", 136, 74],
    ["bench_n144_l10_p10", 29, 25],    ["bench_n144_l10_p50", 32, 19],
    ["bench_n144_l10_p90", 50, 10],    ["bench_n144_l50_p10", 151, 132],
    ["bench_n16_l100_p10", 96, 96],    ["bench_n16_l100_p50", 105, 98],
    ["bench_n16_l100_p90", 101, 99],   ["bench_n16_l10_p10", 10, 10],
    ["bench_n16_l10_p50", 10, 10],     ["bench_n16_l10_p90", 11, 10],
    ["bench_n16_l50_p10", 49, 49],     ["bench_n16_l50_p50", 53, 49],
    ["bench_n16_l50_p90", 50, 50],     ["bench_n225_l10_p10", 39, 37],
    ["bench_n225_l10_p50", 47, 23],     ["bench_n225_l10_p90", 59, 11],
    ["bench_n25_l100_p10", 113, 104],  ["bench_n25_l100_p50", 119, 100],
    ["bench_n25_l100_p90", 128, 100],  ["bench_n25_l10_p10", 10, 11],
    ["bench_n25_l10_p50", 11, 10],     ["bench_n25_l10_p90", 13, 10],
    ["bench_n25_l50_p10", 59, 54],     ["bench_n25_l50_p50", 60, 51],
    ["bench_n25_l50_p90", 62, 50],     ["bench_n49_l100_p10", 158, 144],
    ["bench_n49_l100_p50", 171, 111],  ["bench_n49_l100_p90", 211, 100],
    ["bench_n49_l10_p10", 15, 13],     ["bench_n49_l10_p50", 16, 11],
    ["bench_n49_l10_p90", 22, 10],     ["bench_n49_l50_p10", 75, 69],
    ["bench_n49_l50_p50", 87, 53],     ["bench_n49_l50_p90", 106, 50],
    ["bench_n64_l100_p10", 182, 165],  ["bench_n64_l100_p50", 211, 120],
    ["bench_n64_l10_p10", 18, 15],     ["bench_n64_l10_p50", 20, 12],
    ["bench_n64_l10_p90", 30, 10],     ["bench_n64_l50_p10", 86, 77],
    ["bench_n64_l50_p50", 101, 60],    ["bench_n64_l50_p90", 143, 50]
]

df = pd.DataFrame(data, columns=["Name", "NO_HBM", "ARCH_A"])

def parse_name(name):
    parts = name.split('_')
    n = int(parts[1].replace('n', ''))
    p = int(parts[3].replace('p', ''))
    return n, p

df[['N', 'P']] = df['Name'].apply(lambda x: pd.Series(parse_name(x)))

# ================== 2. RELIABILITY PARAMETERS ==================
# Adjust these based on your target technology
P_PHYS = 1e-3   # Physical error rate (0.01%)
P_TH = 0.01     # Surface code threshold (1%)
D = 7           # Code distance
SCALE = 10000   # Cycle multiplier (1 unit in data = 10k physical cycles)

# Logical error per cycle: P_L = 0.1 * (p_phys/p_th)^((d+1)/2)
PL = 0.03 * (P_PHYS / P_TH)**((D + 1) / 2)

# Calculate Failure Prob: 1 - exp(-TotalCycles * P_L)
df['Fail_2D'] = 1 - np.exp(-df['NO_HBM'] * SCALE * PL)
df['Fail_3D'] = 1 - np.exp(-df['ARCH_A'] * SCALE * PL)

# ================== 3. PLOTTING ==================
fig, axes = plt.subplots(1, 3, figsize=(35, 12), sharey=True)
probabilities = [10, 50, 90]
titles = ["Low Traffic", "Medium Traffic", "High Traffic"]
color_2d = '#d62728' # Red
color_3d = '#1f77b4' # Blue

for i, p in enumerate(probabilities):
    ax = axes[i]
    # Aggregate by Grid Size N for the current Traffic Density P
    subset = df[df['P'] == p].groupby('N').mean(numeric_only=True)
    
    # 2D Planar Baseline
    ax.plot(subset.index, subset['Fail_2D'], marker='o', linestyle='--', 
            color=color_2d, linewidth=6, markersize=18, label='Planar')
    
    # 3D New Architecture
    ax.plot(subset.index, subset['Fail_3D'], marker='s', linestyle='-', 
            color=color_3d, linewidth=6, markersize=18, label='ARCH_A')
    
    ax.set_title(titles[i], pad=25, fontweight='bold')
    ax.set_xlabel("Grid Size (N Qubits)")
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xticks([16, 64, 100, 144, 225])
    
    if i == 0:
        ax.set_ylabel("Circuit Failure Probability")
        ax.legend(frameon=True, loc='upper left', fontsize=32)

plt.tight_layout()
plt.savefig('reliability_by_density.pdf', bbox_inches='tight')

# ================== 4. TERMINAL SUMMARY ==================
print("="*60)
print("RELIABILITY EVALUATION SUMMARY")
print("="*60)
print(f"Physical Error Rate: {P_PHYS}")
print(f"Code Distance (d):   {D}")
print(f"Logical Error/Cycle: {PL:.2e}")
print("-"*60)
for p in probabilities:
    p_fail_2d = df[df['P'] == p]['Fail_2D'].mean()
    p_fail_3d = df[df['P'] == p]['Fail_3D'].mean()
    improvement = (p_fail_2d / p_fail_3d) if p_fail_3d > 0 else 1
    print(f"Traffic {p}%: Planar Fail={p_fail_2d:.4f}, ARCH_A Fail={p_fail_3d:.4f} ({improvement:.2f}x better)")
print("="*60)
print("[✓] Plot saved as: reliability_by_density.pdf")