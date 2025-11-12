import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('../../../combined.csv')

# convert numeric columns
for col in ['magic','hbmA','AvgParallelism']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['speedup'] = df['magic'] / df['hbmA']

# create 3 groups based on quantiles
quantiles = df['AvgParallelism'].quantile([0, 1/3, 2/3, 1]).values
labels = ['low','medium','high']
df['parallel_group'] = pd.cut(df['AvgParallelism'], bins=quantiles, labels=labels, include_lowest=True)

# plot
plt.figure(figsize=(8,6))
colors = {'low':'red','medium':'green','high':'blue'}

for group in labels:
    subset = df[df['parallel_group'] == group]
    plt.scatter(subset['AvgParallelism'], subset['speedup'], label=group, color=colors[group])

plt.xlabel('Avg T parallelism')
plt.ylabel('HBM speedup')
plt.title('HBM with direct connectivity (hbm arch_A) over planar (magic)')
plt.legend()
plt.tight_layout()

# plt.show()
plt.savefig("speedup_vs_AvgTParallelism.pdf", dpi=300, bbox_inches='tight')

