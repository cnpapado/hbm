# import pandas as pd
# import matplotlib.pyplot as plt
# import numpy as np
# import re
# import os

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
#     "text.usetex": False
# })

# # 1. LOAD ARCHITECTURE RESULTS
# def parse_benchmark_results(file_path):
#     with open(file_path, 'r') as f:
#         lines = f.readlines()
#     header_idx = -1
#     for i, line in enumerate(lines):
#         if 'Benchmark' in line and '|' in line:
#             header_idx = i
#             break
#     if header_idx == -1: return pd.DataFrame()
#     headers = [h.strip() for h in lines[header_idx].split('|') if h.strip()]
#     rows = []
#     data_started = False
#     for line in lines[header_idx+1:]:
#         if '---' in line:
#             data_started = True
#             continue
#         if data_started and '|' in line:
#             parts = [p.strip() for p in line.split('|')]
#             if len(parts) >= len(headers):
#                 rows.append(parts[:len(headers)])
#     df = pd.DataFrame(rows, columns=headers)
#     for col in headers[1:]:
#         df[col] = pd.to_numeric(df[col], errors='coerce')
        
#     # Crucial: Strip any hidden trailing spaces from "bench_n16_p10 "
#     df['Benchmark'] = df['Benchmark'].str.strip()
#     return df

# # 2. LOAD SCHEDULER DEPTHS (Variable L)
# def parse_scheduler_depths(file_path):
#     data = []
#     current_bench = None
#     with open(file_path, 'r') as f:
#         for line in f:
#             if 'BENCHMARK ANALYSIS REPORT:' in line:
#                 # Capture bench_nXXX_pYYY exactly, ignoring any .qasm extension
#                 match = re.search(r'(bench_n\d+_p\d+)', line)
#                 if match: 
#                     current_bench = match.group(1).strip()
#             if 'Circuit Depth:' in line and current_bench:
#                 match = re.search(r'(\d+)', line)
#                 if match:
#                     data.append({'Benchmark': current_bench, 'L': int(match.group(1))})
#                     current_bench = None
#     return pd.DataFrame(data)

# # Process Files
# RES_FILE = 'new_benchmarks_gathered.txt'
# ANA_FILE = 'analyzed_benchmarks.txt'

# df_res = parse_benchmark_results(RES_FILE)
# df_depth = parse_scheduler_depths(ANA_FILE)

# # Merge on exact string match
# df = pd.merge(df_res, df_depth, on='Benchmark')

# # --- DEBUG: Verify the merge was successful ---
# print(f"Dataframe rows after merge: {len(df)}")
# if len(df) == 0:
#     print("[!] ERROR: The merge failed. Check if benchmark names match exactly between files.")
# # ----------------------------------------------

# # Extract N and P
# df['N'] = df['Benchmark'].apply(lambda x: int(re.search(r'n(\d+)', x).group(1)))
# df['P'] = df['Benchmark'].apply(lambda x: int(re.search(r'p(\d+)', x).group(1)))

# # Dynamically find architecture columns (everything except Benchmark, N, P, L)
# arch_cols = [col for col in df.columns if col not in ['Benchmark', 'N', 'P', 'L']]

# # Normalize Execution Time by Ideal Depth L (Cost Ratios)
# for col in arch_cols:
#     df[f'Slowdown_{col}'] = df[col] / df['L']
#     df[f'Slowdown_{col}'] = df[f'Slowdown_{col}'].apply(lambda x: max(x, 1.0))

# # ================== PLOTTING ==================
# fig, axes = plt.subplots(1, 3, sharey=True)
# probabilities = [10, 50, 90]
# titles = ["Low T Intensity (P=10%)", "Medium T Intensity (P=50%)", "High T Intensity (P=90%)"]

# colors = {
#     'Baseline': '#d62728', 'Arch A': '#1f77b4', 'C_S2': '#2ca02c', 
#     'C_S4': '#9467bd', 'C_S8': '#ff7f0e', 'C_S16': '#e377c2'
# }
# markers = {
#     'Baseline': 'o', 'Arch A': 's', 'C_S2': '^', 
#     'C_S4': 'v', 'C_S8': 'D', 'C_S16': 'p'
# }

# for i, p in enumerate(probabilities):
#     ax = axes[i]
#     subset = df[df['P'] == p].sort_values('N')
    
#     for arch in arch_cols:
#         col_name = f'Slowdown_{arch}'
#         clean_arch = arch.strip()
        
#         ax.plot(subset['N'], subset[col_name], 
#                 marker=markers.get(clean_arch, 'X'), 
#                 linestyle='-', 
#                 color=colors.get(clean_arch, 'black'), 
#                 linewidth=6, markersize=20, label=clean_arch)
    
#     ax.axhline(1.0, color='black', linestyle=':', linewidth=5, label='Ideal')
#     ax.set_title(titles[i], pad=30)
#     ax.set_xlabel("Grid Size (N)")
#     ax.grid(True, which='major', linestyle='--', alpha=0.4)
    
#     # Rotated X-Ticks to prevent overlap
#     x_ticks = [16, 64, 100, 144, 225, 256, 289, 361, 400]
#     ax.set_xticks(x_ticks)
#     ax.set_xticklabels(x_ticks, rotation=45)
    
#     if i == 0:
#         ax.set_ylabel("Cost Ratio\n")
#         ax.legend(frameon=True, loc='upper left', fontsize=28, ncol=2)

# plt.tight_layout()
# os.makedirs('plots_new', exist_ok=True)
# plt.savefig('plots_new/publication_quality_trends_v4.pdf', bbox_inches='tight')
# print("[✓] Publication quality figures saved.")

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import os

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
    "text.usetex": False
})

# 1. LOAD ARCHITECTURE RESULTS
def parse_benchmark_results(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if 'Benchmark' in line and '|' in line:
            header_idx = i
            break
    if header_idx == -1: return pd.DataFrame()
    headers = [h.strip() for h in lines[header_idx].split('|') if h.strip()]
    rows = []
    data_started = False
    for line in lines[header_idx+1:]:
        if '---' in line:
            data_started = True
            continue
        if data_started and '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= len(headers):
                rows.append(parts[:len(headers)])
    df = pd.DataFrame(rows, columns=headers)
    for col in headers[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # Crucial: Strip any hidden trailing spaces from "bench_n16_p10 "
    df['Benchmark'] = df['Benchmark'].str.strip()
    return df

# 2. LOAD SCHEDULER DEPTHS (Variable L)
def parse_scheduler_depths(file_path):
    data = []
    current_bench = None
    with open(file_path, 'r') as f:
        for line in f:
            if 'BENCHMARK ANALYSIS REPORT:' in line:
                # Capture bench_nXXX_pYYY exactly, ignoring any .qasm extension
                match = re.search(r'(bench_n\d+_p\d+)', line)
                if match: 
                    current_bench = match.group(1).strip()
            if 'Circuit Depth:' in line and current_bench:
                match = re.search(r'(\d+)', line)
                if match:
                    data.append({'Benchmark': current_bench, 'L': int(match.group(1))})
                    current_bench = None
    return pd.DataFrame(data)

# Process Files
RES_FILE = 'new_benchmarks_gathered.txt'
ANA_FILE = 'analyzed_benchmarks.txt'

df_res = parse_benchmark_results(RES_FILE)
df_depth = parse_scheduler_depths(ANA_FILE)

# Merge on exact string match
df = pd.merge(df_res, df_depth, on='Benchmark')

# --- DEBUG: Verify the merge was successful ---
print(f"Dataframe rows after merge: {len(df)}")
if len(df) == 0:
    print("[!] ERROR: The merge failed. Check if benchmark names match exactly between files.")
# ----------------------------------------------

# Extract N and P
df['N'] = df['Benchmark'].apply(lambda x: int(re.search(r'n(\d+)', x).group(1)))
df['P'] = df['Benchmark'].apply(lambda x: int(re.search(r'p(\d+)', x).group(1)))

# Dynamically find architecture columns (everything except Benchmark, N, P, L)
arch_cols = [col for col in df.columns if col not in ['Benchmark', 'N', 'P', 'L']]

# Normalize Execution Time by Ideal Depth L (Cost Ratios)
for col in arch_cols:
    df[f'Slowdown_{col}'] = df[col] / df['L']
    df[f'Slowdown_{col}'] = df[f'Slowdown_{col}'].apply(lambda x: max(x, 1.0))

# ================== PLOTTING ==================
fig, axes = plt.subplots(1, 3, sharey=True)
probabilities = [10, 50, 90]
titles = ["Low T Intensity (P=10%)", "Medium T Intensity (P=50%)", "High T Intensity (P=90%)"]

colors = {
    'Baseline': '#d62728', 'Arch A': '#1f77b4', 'C_S2': '#2ca02c', 
    'C_S4': '#9467bd', 'C_S8': '#ff7f0e', 'C_S16': '#e377c2'
}
markers = {
    'Baseline': 'o', 'Arch A': 's', 'C_S2': '^',
    'C_S4': 'v', 'C_S8': 'D', 'C_S16': 'p'
}
labels = {
    'Baseline': '2D Baseline',
    'Arch A':   'Dedicated',
    'C_S2':     'Shared-2',
    'C_S4':     'Shared-4',
    'C_S8':     'Shared-8',
    'C_S16':    'Shared-16',
}

for i, p in enumerate(probabilities):
    ax = axes[i]
    subset = df[df['P'] == p].sort_values('N')
    
    for arch in arch_cols:
        col_name = f'Slowdown_{arch}'
        clean_arch = arch.strip()
        
        ax.plot(subset['N'], subset[col_name], 
                marker=markers.get(clean_arch, 'X'), 
                linestyle='-', 
                color=colors.get(clean_arch, 'black'), 
                linewidth=6, markersize=20, label=labels.get(clean_arch, clean_arch))
    
    ax.axhline(1.0, color='black', linestyle=':', linewidth=5, label='Ideal')
    ax.set_title(titles[i], pad=30)
    ax.set_xlabel("Grid Size (N)")
    ax.grid(True, which='major', linestyle='--', alpha=0.4)
    
    # Rotated X-Ticks to prevent overlap
    x_ticks = [16, 64, 100, 144, 225, 256, 289, 361, 400]
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_ticks, rotation=45)
    
    if i == 0:
        ax.set_ylabel("Cost Ratio\n")
        ax.legend(frameon=True, loc='upper left', fontsize=46)

plt.tight_layout()
os.makedirs('plots_new', exist_ok=True)
plt.savefig('plots_new/publication_quality_trends_v5.pdf', bbox_inches='tight')
print("[✓] Publication quality figures saved.")