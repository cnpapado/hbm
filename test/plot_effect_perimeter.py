# import pandas as pd
# import matplotlib.pyplot as plt
# import numpy as np
# import re
# import os

# # ================== HPCA/ISCA PUBLICATION STYLE ==================
# plt.rcParams.update({
#     "font.family": "serif",
#     "font.size": 39,
#     "axes.titlesize": 45,
#     "axes.labelsize": 45,
#     "axes.labelweight": "bold",
#     "axes.titleweight": "bold",
#     "axes.linewidth": 4.0,     # Thick boxes
#     "xtick.labelsize": 42,     # Large tick labels
#     "ytick.labelsize": 42,
#     "xtick.major.size": 15,    # Large tick marks
#     "xtick.major.width": 4,
#     "ytick.major.size": 15,
#     "ytick.major.width": 4,
#     "figure.figsize": (32, 16),
#     "savefig.dpi": 300,
#     "pdf.fonttype": 42,
#     "ps.fonttype": 42,
#     "text.usetex": False
# })

# # --- 1. DATA PARSING ---
# def parse_results(file_path):
#     if not os.path.exists(file_path): return pd.DataFrame()
#     with open(file_path, 'r') as f:
#         lines = f.readlines()
#     header_idx = [i for i, l in enumerate(lines) if 'Benchmark' in l][0]
#     headers = [h.strip() for h in lines[header_idx].split('|') if h.strip()]
#     rows = []
#     data_started = False
#     for line in lines[header_idx+1:]:
#         if '---' in line: data_started = True; continue
#         if data_started and '|' in line:
#             parts = [p.strip() for p in line.split('|')]
#             if len(parts) >= len(headers): rows.append(parts[:len(headers)])
#     df = pd.DataFrame(rows, columns=headers)
#     for col in headers[1:]:
#         df[col] = pd.to_numeric(df[col], errors='coerce')
#     return df

# # --- 2. PRE-PROCESSING ---
# df = parse_results('benchmarks_updated_results.txt')
# # Extract N and P from filename
# df['N'] = df['Benchmark'].apply(lambda x: int(re.search(r'n(\d+)', x).group(1)))
# df['P'] = df['Benchmark'].apply(lambda x: int(re.search(r'p(\d+)', x).group(1)))

# # Calculate Benefit: (Standard - Perimeter_Free) / Standard * 100
# df['Benefit_S2'] = (df['C_S2'] - df['C_S2_P']) / df['C_S2'] * 100
# df['Benefit_S4'] = (df['C_S4'] - df['C_S4_P']) / df['C_S4'] * 100

# # --- 3. PLOTTING ---
# fig, axes = plt.subplots(1, 2, sharey=True)

# # Intensity configs
# probs = [10, 50, 90]
# labels = ["P=10% (Low)", "P=50% (Med)", "P=90% (High)"]
# colors = ['#1f77b4', '#ff7f0e', '#2ca02c'] # Blue, Orange, Green
# markers = ['o', 's', '^']

# # Subplot 1: Shared-2 Analysis
# ax1 = axes[0]
# for i, p in enumerate(probs):
#     subset = df[df['P'] == p].sort_values('N')
#     ax1.plot(subset['N'], subset['Benefit_S2'], label=labels[i], color=colors[i], 
#              marker=markers[i], linewidth=10, markersize=26)

# ax1.set_title("Shared-2 Magic States", pad=30)
# ax1.set_ylabel("Cycle Reduction (%)\n(Perimeter Benefit)", labelpad=20)
# ax1.set_xlabel("Grid Size (N)", labelpad=20)
# ax1.grid(True, linestyle='--', alpha=0.5, linewidth=2)
# ax1.set_xticks([16, 25, 49, 64, 100, 144, 225])
# ax1.set_xticklabels([16, 25, 49, 64, 100, 144, 225], rotation=45)

# # Subplot 2: Shared-4 Analysis
# ax2 = axes[1]
# for i, p in enumerate(probs):
#     subset = df[df['P'] == p].sort_values('N')
#     ax2.plot(subset['N'], subset['Benefit_S4'], label=labels[i], color=colors[i], 
#              marker=markers[i], linewidth=10, markersize=26)

# ax2.set_title("Shared-4 Magic States", pad=30)
# ax2.set_xlabel("Grid Size (N)", labelpad=20)
# ax2.grid(True, linestyle='--', alpha=0.5, linewidth=2)
# ax2.set_xticks([16, 25, 49, 64, 100, 144, 225])
# ax2.set_xticklabels([16, 25, 49, 64, 100, 144, 225], rotation=45)

# # Global Legend
# handles, labs = ax1.get_legend_handles_labels()
# leg = fig.legend(handles, labs, loc='upper center', bbox_to_anchor=(0.5, 1.08), 
#                  ncol=3, fontsize=40, frameon=True)
# leg.get_frame().set_linewidth(4.0)
# leg.get_frame().set_edgecolor('black')

# plt.tight_layout()
# plt.savefig('plots_new/figure_c_perimeter_effect.pdf', bbox_inches='tight')
# # plt.savefig('plots_new/figure_c_perimeter_effect.png', bbox_inches='tight')

# print("[✓] Figure C (Perimeter Effect) generated successfully.")


import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import os

# ================== HPCA/ISCA PUBLICATION STYLE ==================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 39,
    "axes.titlesize": 45,
    "axes.labelsize": 45,
    "axes.labelweight": "bold",
    "axes.titleweight": "bold",
    "axes.linewidth": 4.0,     # Thick boxes
    "xtick.labelsize": 42,     # Large tick labels
    "ytick.labelsize": 42,
    "xtick.major.size": 15,    # Large tick marks
    "xtick.major.width": 4,
    "ytick.major.size": 15,
    "ytick.major.width": 4,
    "figure.figsize": (45, 16), # Widened to accommodate 3 subplots
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "text.usetex": False
})

# --- 1. DATA PARSING ---
def parse_results(file_path):
    if not os.path.exists(file_path): return pd.DataFrame()
    with open(file_path, 'r') as f:
        lines = f.readlines()
    header_idx = [i for i, l in enumerate(lines) if 'Benchmark' in l][0]
    headers = [h.strip() for h in lines[header_idx].split('|') if h.strip()]
    rows = []
    data_started = False
    for line in lines[header_idx+1:]:
        if '---' in line: data_started = True; continue
        if data_started and '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= len(headers): rows.append(parts[:len(headers)])
    df = pd.DataFrame(rows, columns=headers)
    for col in headers[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# --- 2. PRE-PROCESSING ---
df = parse_results('benchmarks_updated_results.txt')
# Extract N and P from filename
df['N'] = df['Benchmark'].apply(lambda x: int(re.search(r'n(\d+)', x).group(1)))
df['P'] = df['Benchmark'].apply(lambda x: int(re.search(r'p(\d+)', x).group(1)))

# Calculate Benefit: (Standard - Perimeter_Free) / Standard * 100
df['Benefit_S2'] = (df['C_S2'] - df['C_S2_P']) / df['C_S2'] * 100
df['Benefit_S4'] = (df['C_S4'] - df['C_S4_P']) / df['C_S4'] * 100

# --- 3. PLOTTING ---
fig, axes = plt.subplots(1, 3, sharey=True)

# Traffic Intensities (Subplots)
probs = [10, 50, 90]
titles = ["Low Traffic (P=10%)", "Medium Traffic (P=50%)", "High Traffic (P=90%)"]

# Architectures to plot in each subplot
arch_cols = ['Benefit_S2', 'Benefit_S4']
labels = ['Shared-2 Magic States', 'Shared-4 Magic States']
colors = ['#1f77b4', '#ff7f0e'] # Blue for Shared-2, Orange for Shared-4
markers = ['o', 's']            # Circle for Shared-2, Square for Shared-4

for i, p in enumerate(probs):
    ax = axes[i]
    subset = df[df['P'] == p].sort_values('N')
    
    # Plot both architectures for the current traffic intensity
    for j, arch in enumerate(arch_cols):
        ax.plot(subset['N'], subset[arch], label=labels[j], color=colors[j], 
                 marker=markers[j], linewidth=10, markersize=26)

    ax.set_title(titles[i], pad=30)
    ax.set_xlabel("Grid Size (N)", labelpad=20)
    ax.grid(True, linestyle='--', alpha=0.5, linewidth=2)
    ax.set_xticks([16, 25, 49, 64, 100, 144, 225])
    ax.set_xticklabels([16, 25, 49, 64, 100, 144, 225], rotation=45)
    
    # Only add the Y-axis label to the leftmost plot to avoid clutter
    if i == 0:
        ax.set_ylabel("Cycle Reduction (%)\n(Perimeter Benefit)", labelpad=20)

# Global Legend
# Fetch handles and labels from the first subplot to create a single top legend
handles, leg_labels = axes[0].get_legend_handles_labels()
leg = fig.legend(handles, leg_labels, loc='upper center', bbox_to_anchor=(0.5, 1.08), 
                 ncol=2, fontsize=40, frameon=True)
leg.get_frame().set_linewidth(4.0)
leg.get_frame().set_edgecolor('black')

plt.tight_layout()

# Save the plot
os.makedirs('plots_new', exist_ok=True) # Ensure directory exists
plt.savefig('plots_new/figure_c_perimeter_effect.pdf', bbox_inches='tight')
# plt.savefig('plots_new/figure_c_perimeter_effect.png', bbox_inches='tight')

print("[✓] Figure C (Perimeter Effect) generated successfully as a 3-panel plot.")