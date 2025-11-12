import pandas as pd
import matplotlib.pyplot as plt

# reload data
df = pd.read_csv('../../combined.csv')

# convert relevant columns to numeric
for col in ['ideal','magic','hbmA']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# sort by ideal ascending
df_sorted = df.sort_values(by='ideal').reset_index(drop=True)

# normalize magic and hbmA by ideal
df_sorted['magic_norm'] = df_sorted['magic'] / df_sorted['ideal']
df_sorted['hbmA_norm'] = df_sorted['hbmA'] / df_sorted['ideal']

# scatter plot (normalized)
plt.figure(figsize=(10,6))
plt.scatter(df_sorted.index, df_sorted['magic_norm'], label='planar (square sparse, all sides)', marker='s', s=50)
plt.scatter(df_sorted.index, df_sorted['hbmA_norm'], label='HBM w direct connectivity', marker='^', s=50)

plt.axhline(y=1, color='r', linestyle='--', label='Ideal (baseline)')

plt.xlabel('Benchmark')
plt.ylabel('Execution steps relative to dependency-only baseline')
plt.title('HBM with direct connectivity (hbm arch_A) over planar (magic) normalized to ideal execution steps considering only dependencies')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
# plt.show()
plt.savefig("ideal_vs_magic_hbmA.pdf", dpi=300, bbox_inches='tight')
