"""
Plot 5: Summary Heatmap
One heatmap per ARCH_C config.
Rows: qubit count n, Columns: T-gate probability p
Color: normalized reduction (0=no benefit, 1=as good as ARCH_A)
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from parse_utils import parse_results, compute_reduction

RESULTS_FILE = 'new_benchmarks_gathered.txt'
OUTPUT_FILE  = 'plots_new/plot5_heatmap.pdf'

ARCH_C_COLS = ['C_S2', 'C_S4', 'C_S8', 'C_S16']
TITLES      = {
    'C_S2':  'Shared 2 (1:2)',
    'C_S4':  'Shared 4 (1:4)',
    'C_S8':  'Shared 8 (1:8)',
    'C_S16': 'Shared 16 (1:16)',
}


def main():
    df = parse_results(RESULTS_FILE)
    df = compute_reduction(df)

    n_values = sorted(df['n'].unique())
    p_values = sorted(df['p'].unique())

    fig, axes = plt.subplots(1, 4, figsize=(18, 6))
    fig.suptitle('Normalised Timestep Reduction Heatmap\n(0 = no benefit, 1 = same as ARCH_A)', fontsize=13)

    cmap = plt.cm.RdYlGn
    norm = mcolors.Normalize(vmin=0, vmax=1)

    for ax, col in zip(axes, ARCH_C_COLS):
        matrix = np.full((len(n_values), len(p_values)), np.nan)
        for i, n in enumerate(n_values):
            for j, p in enumerate(p_values):
                row = df[(df['n'] == n) & (df['p'] == p)]
                if not row.empty:
                    matrix[i, j] = row.iloc[0][f'reduction_{col}']

        im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect='auto')

        # Annotate cells
        for i in range(len(n_values)):
            for j in range(len(p_values)):
                val = matrix[i, j]
                if not np.isnan(val):
                    text_color = 'black' if 0.3 < val < 0.8 else 'white'
                    ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                            fontsize=8, color=text_color)

        ax.set_title(TITLES[col])
        ax.set_xticks(range(len(p_values)))
        ax.set_xticklabels([f'p={p}%' for p in p_values])
        ax.set_yticks(range(len(n_values)))
        ax.set_yticklabels([f'n={n}' for n in n_values])
        ax.set_xlabel('T-gate Probability')

    axes[0].set_ylabel('Qubit Count (n)')

    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap),
                 ax=axes, orientation='vertical', fraction=0.02, pad=0.02,
                 label='Normalised Reduction')

    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f'Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
