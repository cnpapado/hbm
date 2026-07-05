"""
Plot 2: Bottleneck Severity vs HBM Benefit
X-axis: Bottleneck % (fraction of layers where T-gate demand exceeds 2D perimeter limit)
Y-axis: Normalized timestep reduction for each ARCH_C config
One subplot per ARCH_C config. Points colored by qubit count n.
"""

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parse_utils import parse_results, parse_analysis, compute_reduction

RESULTS_FILE  = 'new_benchmarks_gathered.txt'
ANALYSIS_FILE = 'analyzed_benchmarks.txt'
OUTPUT_FILE   = 'plots_new/plot2_bottleneck_scatter.pdf'

ARCH_C_COLS   = ['C_S2', 'C_S4', 'C_S8', 'C_S16']
TITLES        = {'C_S2': 'ARCH_C shared_2 (1:2)',
                 'C_S4': 'ARCH_C shared_4 (1:4)',
                 'C_S8': 'ARCH_C shared_8 (1:8)',
                 'C_S16':'ARCH_C shared_16 (1:16)'}
P_MARKERS     = {10: 'o', 50: 's', 90: '^'}
P_LABELS      = {10: 'p=10%', 50: 'p=50%', 90: 'p=90%'}


def main():
    df_res  = parse_results(RESULTS_FILE)
    df_ana  = parse_analysis(ANALYSIS_FILE)
    df_res  = compute_reduction(df_res)
    df      = df_res.merge(df_ana[['benchmark', 'bottleneck_pct']], on='benchmark', how='left')

    n_values = sorted(df['n'].unique())
    colors   = cm.plasma(np.linspace(0.1, 0.9, len(n_values)))
    color_map = {n: colors[i] for i, n in enumerate(n_values)}

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle('Bottleneck Severity vs Normalised HBM Benefit', fontsize=13)
    axes = axes.flatten()

    for ax, col in zip(axes, ARCH_C_COLS):
        for p, marker in P_MARKERS.items():
            sub = df[df['p'] == p]
            for _, row in sub.iterrows():
                ax.scatter(row['bottleneck_pct'], row[f'reduction_{col}'],
                           color=color_map[row['n']], marker=marker,
                           s=60, zorder=3)

        ax.set_title(TITLES[col])
        ax.set_xlabel('Bottleneck Severity (% of layers exceeding 2D perimeter limit)')
        ax.set_ylabel('Normalised Reduction')
        ax.axhline(1.0, linestyle='--', color='gray', linewidth=0.8)
        ax.axhline(0.0, linestyle=':', color='lightgray', linewidth=0.8)
        ax.set_xlim(-5, 100)
        ax.set_ylim(-0.2, 1.3)
        ax.grid(True, alpha=0.3)

    # Legend for p values (markers)
    marker_handles = [plt.Line2D([0], [0], marker=m, color='gray', linestyle='None',
                                  markersize=7, label=P_LABELS[p])
                      for p, m in P_MARKERS.items()]
    # Legend for n (colors)
    color_handles = [plt.Line2D([0], [0], marker='o', color=color_map[n], linestyle='None',
                                 markersize=7, label=f'n={n}')
                     for n in n_values]

    fig.legend(handles=marker_handles + color_handles,
               loc='lower center', ncol=len(marker_handles) + len(color_handles) // 2,
               fontsize=8, bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f'Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
