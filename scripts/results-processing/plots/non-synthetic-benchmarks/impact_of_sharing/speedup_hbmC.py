import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv('../../../combined.csv')

# Convert relevant columns to numeric
cols = ['magic', 'hbmA', 'hbmC_shared2', 'hbmC_shared4']
for col in cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Compute speedups
df['shared1'] = df['magic'] / df['hbmA']
df['shared2'] = df['magic'] / df['hbmC_shared2']
df['shared4'] = df['magic'] / df['hbmC_shared4']

# Create numeric x-axis
x = range(1, len(df) + 1)

# Plot as scatter
plt.figure(figsize=(12, 6))
plt.scatter(x, df['shared1'], marker='o', label='1 data qubit sharing single magic state')
plt.scatter(x, df['shared2'], marker='s', label='2 data qubits sharing single magic state')
plt.scatter(x, df['shared4'], marker='^', label='4 data qubits sharing single magic state')

# Show only a subset of x-axis numbers for readability
xticks = x[::max(1, len(x)//10)]  # roughly 10 ticks
plt.xticks(xticks)

plt.xlabel('Benchmark Index')
plt.ylabel('Speedup over planar baseline layout')
plt.title('Effect of different numbers of data qubits sharing a single magic state (routing on upper level)')
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save as 300 dpi PDF
plt.savefig('different_sharing_hbmC.pdf', dpi=300)
# plt.show()
