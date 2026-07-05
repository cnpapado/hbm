"""
Plot 1: Trade-off Curve
X-axis: Magic state density (from most sparse to densest)
Y-axis: Normalized timestep reduction = (NO_HBM - ARCH_C) / (NO_HBM - ARCH_A)
One subplot per p value, one line per qubit count n.
"""

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parse_utils import parse_results, compute_reduction

RESULTS_FILE = 'new_benchmarks_gathered.txt'
OUTPUT_FILE  = 'plots_new/plot1_tradeoff_curve.pdf'

# Magic state density: fraction of data qubits that have a magic state above them
CONFIGS      = ['C_S16', 'C_S8', 'C_S4', 'C_S2', 'ARCH_A']
DENSITIES    = [1/16,    1/8,    1/4,    1/2,    1.0   ]
LABELS       = ['S16',   'S8',   'S4',   'S2',   'A(1:1)']

P_VALUES     = [10, 50, 90]
P_TITLES     = {10: 'p=10% T-gates', 50: 'p=50% T-gates', 90: 'p=90% T-gates'}


def get_reduction(row, col):
    denom = row['NO_HBM'] - row['ARCH_A']
    if denom == 0 or np.isnan(denom):
        return float('nan')
    return (row['NO_HBM'] - row[col]) / denom


def main():
    df = parse_results(RESULTS_FILE)

    n_values = sorted(df['n'].unique())
    colors = cm.viridis(np.linspace(0.1, 0.9, len(n_values)))
    color_map = {n: colors[i] for i, n in enumerate(n_values)}

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    fig.suptitle('HBM Trade-off: Magic State Density vs Normalised Timestep Reduction', fontsize=13)

    for ax, p in zip(axes, P_VALUES):
        sub = df[df['p'] == p]
        for n in n_values:
            row = sub[sub['n'] == n]
            if row.empty:
                continue
            row = row.iloc[0]
            reductions = []
            for col in CONFIGS:
                if col == 'ARCH_A':
                    reductions.append(get_reduction(row, 'ARCH_A'))
                else:
                    reductions.append(get_reduction(row, col))
            ax.plot(DENSITIES, reductions, marker='o', color=color_map[n],
                    label=f'n={n}', linewidth=1.5, markersize=4)

        ax.set_title(P_TITLES[p])
        ax.set_xlabel('Magic State Density (fraction of data qubits)')
        ax.set_xscale('log')
        ax.set_xticks(DENSITIES)
        ax.set_xticklabels(LABELS)
        ax.axhline(1.0, linestyle='--', color='gray', linewidth=0.8, label='ARCH_A ceiling')
        ax.axhline(0.0, linestyle=':', color='lightgray', linewidth=0.8)
        ax.set_ylim(-0.2, 1.3)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel('Normalised Reduction\n(NO_HBM - ARCH_C) / (NO_HBM - ARCH_A)')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center right', bbox_to_anchor=(1.0, 0.5),
               fontsize=8, title='Qubits (n)')

    plt.tight_layout(rect=[0, 0, 0.88, 1])
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f'Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
