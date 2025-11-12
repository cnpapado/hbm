import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('../../../combined.csv')

# convert numeric columns
for col in ['magic','hbmA','t_count']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['speedup'] = df['magic'] / df['hbmA']

# create 3 groups based on quantiles
quantiles = df['t_count'].quantile([0, 1/3, 2/3, 1]).values
labels = ['low','medium','high']
df['parallel_group'] = pd.cut(df['t_count'], bins=quantiles, labels=labels, include_lowest=True)

# plot
plt.figure(figsize=(8,6))
colors = {'low':'red','medium':'green','high':'blue'}

for group in labels:
    subset = df[df['parallel_group'] == group]
    plt.scatter(subset['t_count'], subset['speedup'], label=group, color=colors[group])

plt.xlabel('T count')
plt.ylabel('HBM speedup')
plt.title('HBM with direct connectivity (hbm arch_A) over planar (magic)')
plt.legend()
plt.tight_layout()

# plt.show()
plt.savefig("speedup_vs_Tcount.pdf", dpi=300, bbox_inches='tight')

