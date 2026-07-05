import pandas as pd
import matplotlib.pyplot as plt
import re
import numpy as np

def parse_results(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract benchmark data patterns: bench_n(\d+)_p(\d+) | val | val ...
    lines = content.split('\n')
    rows = []
    headers = ['Benchmark', 'Baseline', 'Arch A', 'C_S2', 'C_S2_P', 'C_S4', 'C_S4_P']
    
    for line in lines:
        if 'bench_n' in line and '|' in line:
            parts = line.split('|')
            bench = parts[0].strip()
            # Extract numerical values from segments
            values = [int(re.search(r'\d+', p).group()) for p in parts[1:] if re.search(r'\d+', p)]
            if len(values) >= 6:
                rows.append([bench] + values[:6])
    
    df = pd.DataFrame(rows, columns=headers)
    df['N'] = df['Benchmark'].apply(lambda x: int(re.search(r'n(\d+)', x).group(1)))
    df['P'] = df['Benchmark'].apply(lambda x: int(re.search(r'p(\d+)', x).group(1)))
    return df

def parse_analysis(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    reports = content.split('------------------------------------------------------------')
    data = []
    for report in reports:
        match_bench = re.search(r'BENCHMARK ANALYSIS REPORT: bench_n(\d+)_p(\d+)', report)
        if match_bench:
            n, p = int(match_bench.group(1)), int(match_bench.group(2))
            depth_match = re.search(r'Circuit Depth:\s+(\d+)', report)
            data.append({'N': n, 'P': p, 'Ideal_Depth': int(depth_match.group(1)) if depth_match else None})
    return pd.DataFrame(data)

# Data Processing
df_res = parse_results('benchmarks_updated_results.txt')
df_analysis = parse_analysis('analyzed_synth_bench_new_updated_scheduler.txt')
df = pd.merge(df_res, df_analysis, on=['N', 'P'])

# Metrics
df['Slowdown'] = df['Baseline'] / df['Ideal_Depth']
for arch in ["Arch A", "C_S2", "C_S2_P", "C_S4", "C_S4_P"]:
    df[f'Speedup_{arch}'] = df['Baseline'] / df[arch]

df.to_csv('final_merged_data.csv', index=False)

# Figure A: Heatmap
pivot_df = df.pivot(index='P', columns='N', values='Slowdown').sort_index(ascending=False)
plt.imshow(pivot_df.values, cmap='YlOrRd', aspect='auto')
for i in range(len(pivot_df.index)):
    for j in range(len(pivot_df.columns)):
        plt.text(j, i, f'{pivot_df.values[i, j]:.2f}', ha='center', va='center')
plt.colorbar(label='Slowdown Factor (Baseline / Ideal)')
plt.xticks(range(len(pivot_df.columns)), pivot_df.columns)
plt.yticks(range(len(pivot_df.index)), pivot_df.index)
plt.xlabel('Qubit Count (N)'); plt.ylabel('T-gate Density (P %)')
plt.title('Figure A: 2D Baseline Performance Slowdown')
plt.savefig('plots_new/figure_a_heatmap.png', bbox_inches='tight')

# Figure B: Speedup
p90 = df[df['P'] == 90].sort_values('N')
x = np.arange(len(p90['N']))
width = 0.15
plt.bar(x - 2*width, p90['Speedup_Arch A'], width, label='Arch A')
plt.bar(x - width, p90['Speedup_C_S2_P'], width, label='C_S2_P')
plt.bar(x + width, p90['Speedup_C_S4_P'], width, label='C_S4_P')
plt.xticks(x, p90['N'])
plt.ylabel('Speedup (vs Baseline)'); plt.legend()
plt.title('Figure B: Speedup at High Traffic (P=90)')
plt.savefig('plots_new/figure_b_speedup.png', bbox_inches='tight')

# Figure C: Perimeter Benefit
for p in [10, 50, 90]:
    subset = df[df['P'] == p].sort_values('N')
    benefit = (subset['C_S4'] - subset['C_S4_P']) / subset['C_S4'] * 100
    plt.plot(subset['N'], benefit, marker='o', label=f'P={p}')
plt.xlabel('Qubit Count (N)'); plt.ylabel('% Cycles Reduced'); plt.legend()
plt.title('Figure C: Impact of Perimeter-Free Layout')
plt.savefig('plots_new/figure_c_perimeter_benefit.png', bbox_inches='tight')