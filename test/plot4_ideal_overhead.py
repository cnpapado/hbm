"""
Plot 4: Routing Overhead Relative to Ideal Circuit Depth
Y-axis: routed_steps / ideal_depth  (1.0 = perfect, higher = more overhead)
X-axis: Architecture config
One subplot per p value. One line per qubit count n.
Shows how close each architecture gets to ideal (DAG) execution.
"""

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parse_utils import parse_results, parse_analysis, compute_ideal_overhead

RESULTS_FILE  = 'new_benchmarks_gathered.txt'
ANALYSIS_FILE = 'analyzed_benchmarks.txt'
OUTPUT_FILE   = 'plots_new/plot4_ideal_overhead.pdf'

CONFIGS  = ['NO_HBM', 'C_S16', 'C_S8', 'C_S4', 'C_S2', 'ARCH_A']
X_LABELS = ['NO_HBM', 'S16',   'S8',   'S4',   'S2',  'A(1:1)']
P_VALUES = [10, 50, 90]
P_TITLES = {10: 'p=10% T-gates', 50: 'p=50% T-gates', 90: 'p=90% T-gates'}


def main():
    df_res = parse_results(RESULTS_FILE)
    df_ana = parse_analysis(ANALYSIS_FILE)
    df     = compute_ideal_overhead(df_res, df_ana)

    n_values  = sorted(df['n'].unique())
    colors    = cm.viridis(np.linspace(0.1, 0.9, len(n_values)))
    color_map = {n: colors[i] for i, n in enumerate(n_values)}

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=False)
    fig.suptitle('Routing Overhead vs Ideal Circuit Depth', fontsize=13)

    for ax, p in zip(axes, P_VALUES):
        sub = df[df['p'] == p]
        for n in n_values:
            row = sub[sub['n'] == n]
            if row.empty:
                continue
            row = row.iloc[0]
            overheads = [row[f'overhead_{col}'] for col in CONFIGS]
            ax.plot(range(len(CONFIGS)), overheads, marker='o',
                    color=color_map[n], label=f'n={n}', linewidth=1.5, markersize=4)

        ax.set_title(P_TITLES[p])
        ax.set_xticks(range(len(CONFIGS)))
        ax.set_xticklabels(X_LABELS)
        ax.axhline(1.0, linestyle='--', color='gray', linewidth=0.8, label='Ideal (1.0)')
        ax.set_ylabel('Overhead (routed steps / ideal depth)')
        ax.grid(True, alpha=0.3)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center right', bbox_to_anchor=(1.0, 0.5),
               fontsize=8, title='Qubits (n)')

    plt.tight_layout(rect=[0, 0, 0.88, 1])
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f'Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
