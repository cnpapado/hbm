import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv('../../../combined.csv')

# Convert relevant columns to numeric
cols_lower = ['magic', 'hbmA', 'hbmB_shared2', 'hbmB_shared4']
cols_upper = ['magic', 'hbmA', 'hbmC_shared2', 'hbmC_shared4']
for col in set(cols_lower + cols_upper):
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Create numeric x-axis
x = range(1, len(df) + 1)
xticks = x[::max(1, len(x)//10)]  # roughly 10 ticks for readability

# Create figure with 2 subplots horizontally
fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

# Determine y-axis limits for same scale
# Compute speedups for all series first
speedups_lower = [
    df['magic'] / df['hbmA'],
    df['magic'] / df['hbmB_shared2'],
    df['magic'] / df['hbmB_shared4']
]

speedups_upper = [
    df['magic'] / df['hbmA'],
    df['magic'] / df['hbmC_shared2'],
    df['magic'] / df['hbmC_shared4']
]

# Combine all speedups to find global min/max
all_speedups = pd.concat(speedups_lower + speedups_upper)
y_min = all_speedups.min() * 0.95  # add 5% padding
y_max = all_speedups.max() * 1.05

# ----------- Lower-level routing (hbmB) -----------
axes[0].scatter(x, df['magic'] / df['hbmA'], marker='o', label='1 data qubit sharing single magic state')
axes[0].scatter(x, df['magic'] / df['hbmB_shared2'], marker='s', label='2 data qubits sharing single magic state')
axes[0].scatter(x, df['magic'] / df['hbmB_shared4'], marker='^', label='4 data qubits sharing single magic state')
axes[0].set_title('Routing on lower level')
axes[0].grid(True)
axes[0].set_xticks(xticks)
axes[0].set_ylim(y_min*0.95, y_max*1.05)  # small padding

# ----------- Upper-level routing (hbmC) -----------
axes[1].scatter(x, df['magic'] / df['hbmA'], marker='o', label='1 data qubit sharing single magic state')
axes[1].scatter(x, df['magic'] / df['hbmC_shared2'], marker='s', label='2 data qubits sharing single magic state')
axes[1].scatter(x, df['magic'] / df['hbmC_shared4'], marker='^', label='4 data qubits sharing single magic state')
axes[1].set_title('Routing on upper level')
axes[1].grid(True)
axes[1].set_xticks(xticks)
axes[1].set_ylim(y_min*0.95, y_max*1.05)  # same y-axis

# Common labels
fig.text(0.5, 0.04, 'Benchmark Index', ha='center', fontsize=12)
fig.text(0.04, 0.5, 'Speedup over planar baseline', va='center', rotation='vertical', fontsize=12)

# Shared legend
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', ncol=3)

plt.tight_layout(rect=[0.03, 0.03, 1, 0.95])  # leave space for legend
plt.savefig('different_sharing_in_one_plot.pdf', dpi=300)
# plt.show()
