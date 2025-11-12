import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv("../../../combined.csv")
sort_by = "AvgParallelism" #MaxParallelism
# Columns that should be integers
int_cols = ["magic", "hbmA"]

# Convert to numeric, coerce errors, fill NaN, then convert to int
for col in int_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# keep as float (sorting works better)
df[sort_by] = pd.to_numeric(df[sort_by], errors="coerce")

# Compute speedup
df["speedup_hbmA_over_magic"] = df["magic"] / df["hbmA"]

# Sort 
df_sorted = df.sort_values(by=sort_by)

# Plot
plt.figure(figsize=(10,6))
plt.plot(df_sorted["Benchmark"], df_sorted["speedup_hbmA_over_magic"], marker='o')
plt.xticks(rotation=90)
plt.title(f"HBM with direct connectivity (hbm arch_A) over planar (magic) (sorted by {sort_by})")
plt.xlabel("Benchmark")
plt.ylabel("HBM Speedup")

plt.tight_layout()
# plt.show()
plt.savefig("speedup_vs_sorted_benches_AvgParallelism.pdf", dpi=300, bbox_inches='tight')

