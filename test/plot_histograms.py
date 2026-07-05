# import pandas as pd
# import matplotlib.pyplot as plt
# import argparse
# import re
# import os
# import numpy as np

# # ================== HPCA/ISCA PUBLICATION STYLE ==================
# plt.rcParams.update({
#     "font.family": "serif",
#     "font.size": 14,
#     "axes.titlesize": 16,
#     "axes.labelsize": 14,
#     "axes.labelweight": "bold",
#     "axes.linewidth": 1.5,
#     "figure.figsize": (10, 6),
#     "savefig.dpi": 300,
#     "pdf.fonttype": 42,
#     "ps.fonttype": 42
# })

# def parse_data():
#     # 1. Parse analyzed_results.txt for X and Y values
#     metrics = []
#     if not os.path.exists("analyzed_results.txt"):
#         print("Error: analyzed_results.txt not found.")
#         return None

#     with open("analyzed_results.txt", "r") as f:
#         content = f.read()
#         # Split by report blocks
#         blocks = content.split("BENCHMARK ANALYSIS REPORT:")
#         for block in blocks[1:]:
#             name_match = re.search(r"^\s*([\w\d\-_]+)\.qasm", block, re.MULTILINE)
#             ratio_match = re.search(r"Magic Ratio:\s+([\d\.]+)\%", block)
#             para_match = re.search(r"Avg Simultaneous T-Gates:\s+([\d\.]+)", block)
            
#             if name_match and ratio_match and para_match:
#                 metrics.append({
#                     "bench_name": name_match.group(1).strip(),
#                     "t_density": float(ratio_match.group(1)),
#                     "avg_t_parallelism": float(para_match.group(1))
#                 })

#     # 2. Parse benchmark_report_final.txt for Speedup (Color)
#     speedups = []
#     if not os.path.exists("benchmark_report_final.txt"):
#         print("Error: benchmark_report_final.txt not found.")
#         return None

#     with open("benchmark_report_final.txt", "r") as f:
#         start_parsing = False
#         for line in f:
#             if "---" in line:
#                 start_parsing = True
#                 continue
#             if "===" in line and start_parsing:
#                 break
#             if start_parsing and "|" in line:
#                 parts = [p.strip() for p in line.split("|")]
#                 if len(parts) >= 3:
#                     name = parts[0]
#                     try:
#                         no_hbm = float(parts[1])
#                         arch_a = float(parts[2])
#                         speedup = no_hbm / arch_a if arch_a > 0 else 1.0
#                         speedups.append({"bench_name": name, "speedup": speedup})
#                     except ValueError:
#                         continue

#     df_m = pd.DataFrame(metrics)
#     df_s = pd.DataFrame(speedups)
#     return pd.merge(df_m, df_s, on="bench_name")

# def plot_speedup(df):
#     plt.figure(constrained_layout=True)
    
#     # Create the scatter plot
#     # X = T Density, Y = Avg T Parallelism, Color = Speedup
#     sc = plt.scatter(
#         df['t_density'],
#         df['avg_t_parallelism'],
#         c=df['speedup'],
#         cmap='viridis',
#         s=80,
#         edgecolors='black',
#         linewidths=0.5,
#         alpha=0.9
#     )

#     # Labeling
#     plt.xlabel("T-Density (Magic Ratio %)")
#     plt.ylabel("Average T-Parallelism")
#     plt.title("Speedup Analysis: Sparse Square Topology", pad=20)

#     # Add Colorbar
#     cbar = plt.colorbar(sc)
#     cbar.set_label("Speedup over Planar (NO_HBM / ARCH_A)", weight='bold')

#     # Optional: Grid for better readability
#     plt.grid(True, linestyle='--', alpha=0.6)

#     # Save output
#     os.makedirs("plots", exist_ok=True)
#     plt.savefig("plots/speedup_analysis.pdf", format="pdf", bbox_inches="tight")
#     print("Plot saved to plots/speedup_analysis.pdf")
#     plt.show()

# if __name__ == "__main__":
#     combined_df = parse_data()
#     if combined_df is not None and not combined_df.empty:
#         plot_speedup(combined_df)
#     else:
#         print("No data found to plot. Check your input file formats.")

import pandas as pd
import matplotlib.pyplot as plt
import re
import os
import math
import numpy as np
from matplotlib.lines import Line2D

# ================== HPCA/ISCA PUBLICATION STYLE ==================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "axes.labelweight": "bold",
    "axes.linewidth": 1.5,
    "figure.figsize": (16, 10),
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42
})

def parse_data():
    """Parses both files and extracts metadata from benchmark names."""
    metrics = []
    # 1. Parse analyzed_results.txt
    if os.path.exists("analyzed_results.txt"):
        with open("analyzed_results.txt", "r") as f:
            content = f.read()
            blocks = content.split("BENCHMARK ANALYSIS REPORT:")
            for block in blocks[1:]:
                name_match = re.search(r"^\s*([\w\d\-_]+)\.qasm", block, re.MULTILINE)
                if name_match:
                    name = name_match.group(1).strip()
                    # Extract n and p from filename
                    n_match = re.search(r'_n(\d+)_', name)
                    p_match = re.search(r'_p(\d+)', name)
                    
                    if n_match and p_match:
                        metrics.append({
                            "bench_name": name,
                            "n": int(n_match.group(1)),
                            "p_category": f"{p_match.group(1)}% Density"
                        })

    # 2. Parse benchmark_report_final.txt
    speedups = []
    if os.path.exists("benchmark_report_final.txt"):
        with open("benchmark_report_final.txt", "r") as f:
            start_parsing = False
            for line in f:
                if "---" in line:
                    start_parsing = True
                    continue
                if "===" in line and start_parsing: break
                if start_parsing and "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        try:
                            # Speedup = NO_HBM / ARCH_A
                            s_val = float(parts[1]) / float(parts[2]) if float(parts[2]) > 0 else 1.0
                            speedups.append({"bench_name": parts[0], "speedup": s_val})
                        except ValueError: continue

    df_m = pd.DataFrame(metrics)
    df_s = pd.DataFrame(speedups)
    
    if df_m.empty or df_s.empty:
        return pd.DataFrame()
        
    return pd.merge(df_m, df_s, on="bench_name")

# ================== MAIN EXECUTION ==================
if __name__ == "__main__":
    df = parse_data()

    if not df.empty:
        # Define categorical colors for T-Density
        color_map = {
            "10% Density": "#440154", # Purple
            "50% Density": "#21918c", # Teal
            "90% Density": "#fde725"  # Yellow
        }

        unique_n = sorted(df['n'].unique())
        cols = 3
        rows = math.ceil(len(unique_n) / cols)
        
        fig, axes = plt.subplots(rows, cols, sharey=True, figsize=(18, 5 * rows))
        axes = axes.flatten()

        for i, n_val in enumerate(unique_n):
            ax = axes[i]
            # Group by density and sort to keep colored bars together
            subset = df[df['n'] == n_val].copy()
            subset = subset.sort_values(by=["p_category", "speedup"])
            
            x_pos = np.arange(len(subset))
            bar_colors = [color_map.get(cat, "#808080") for cat in subset['p_category']]
            
            ax.bar(x_pos, subset['speedup'], color=bar_colors, edgecolor='black', linewidth=0.5)
            
            # Baseline line (Speedup = 1)
            ax.axhline(y=1.0, color='red', linestyle='-', linewidth=1.5, alpha=0.6, zorder=0)
            
            ax.set_title(f"Architectural Size: {n_val} Qubits", fontweight='bold')
            ax.set_xticks([]) # Clear x-ticks for a cleaner bar-look
            ax.grid(axis='y', linestyle=':', alpha=0.6)
            
            if i % cols == 0:
                ax.set_ylabel("Speedup (Planar vs. 3D)")

        # Hide empty subplots
        for j in range(i + 1, len(axes)):
            axes[j].axis('off')

        # --- CORRECTED LEGEND LOGIC ---
        # We iterate over items() so both 'l' (label) and 'c' (color) are defined
        legend_elements = [Line2D([0], [0], color=c, lw=6, label=l) for l, c in color_map.items()]
        
        fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.96), 
                   ncol=3, fontsize=14, frameon=False)

        plt.suptitle("Speedup Analysis: Sparse Square Topology\n(Bars grouped by T-Density)", 
                     fontsize=20, fontweight='bold', y=1.02)
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.93])
        
        os.makedirs("plots", exist_ok=True)
        plt.savefig("plots/speedup_bar_chart.pdf", bbox_inches="tight")
        print("Success: Bar chart saved to plots/speedup_bar_chart.pdf")
    else:
        print("Error: No valid data found to plot. Check your input filenames and file contents.")