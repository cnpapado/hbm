"""
Plot 3: Scaling with Qubit Count
X-axis: Number of qubits (n)
Y-axis: Normalized timestep reduction
One subplot per p value. One line per ARCH_C config + ARCH_A.
Shows how HBM benefit scales as circuits grow larger.
"""

import matplotlib.pyplot as plt
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parse_utils import parse_results, compute_reduction

RESULTS_FILE = 'new_benchmarks_gathered.txt'
OUTPUT_FILE  = 'plots_new/plot3_scaling.pdf'

P_VALUES     = [10, 50, 90]
P_TITLES     = {10: 'p=10% T-gates', 50: 'p=50% T-gates', 90: 'p=90% T-gates'}

CONFIGS = {
    'ARCH_A': ('ARCH_A (1:1)',  'black',   '-',  'o'),
    'C_S2':   ('Shared 2 (1:2)','#1f77b4', '-',  's'),
    'C_S4':   ('Shared 4 (1:4)','#ff7f0e', '-',  '^'),
    'C_S8':   ('Shared 8 (1:8)','#2ca02c', '--', 'D'),
    'C_S16':  ('Shared16 (1:16)','#d62728','--', 'v'),
}


def get_reduction(row, col):
    denom = row['NO_HBM'] - row['ARCH_A']
    if denom == 0 or np.isnan(denom):
        return float('nan')
    return (row['NO_HBM'] - row[col]) / denom


def main():
    df = parse_results(RESULTS_FILE)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    fig.suptitle('HBM Benefit Scaling with Qubit Count', fontsize=13)

    for ax, p in zip(axes, P_VALUES):
        sub = df[df['p'] == p].sort_values('n')
        for col, (label, color, ls, marker) in CONFIGS.items():
            reductions = [get_reduction(row, col) for _, row in sub.iterrows()]
            ax.plot(sub['n'], reductions, label=label, color=color,
                    linestyle=ls, marker=marker, linewidth=1.8, markersize=5)

        ax.set_title(P_TITLES[p])
        ax.set_xlabel('Number of Data Qubits (n)')
        ax.axhline(1.0, linestyle='--', color='gray', linewidth=0.8)
        ax.axhline(0.0, linestyle=':', color='lightgray', linewidth=0.8)
        ax.set_ylim(-0.2, 1.3)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel('Normalised Reduction\n(NO_HBM - config) / (NO_HBM - ARCH_A)')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=len(CONFIGS),
               fontsize=9, bbox_to_anchor=(0.5, -0.04))

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f'Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
