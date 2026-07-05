import re
import pandas as pd


def parse_results(filepath):
    """Parse benchmarks_results.txt into a DataFrame."""
    data = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('bench_'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 7:
                    name = parts[0].strip()
                    m = re.match(r'bench_n(\d+)_p(\d+)', name)
                    if m:
                        def to_int(s):
                            try:
                                return int(s.strip())
                            except:
                                return None
                        data.append({
                            'benchmark': name,
                            'n': int(m.group(1)),
                            'p': int(m.group(2)),
                            'NO_HBM': to_int(parts[1]),
                            'ARCH_A': to_int(parts[2]),
                            'C_S2':   to_int(parts[3]),
                            'C_S4':   to_int(parts[4]),
                            'C_S8':   to_int(parts[5]),
                            'C_S16':  to_int(parts[6]),
                        })
    return pd.DataFrame(data)


def parse_analysis(filepath):
    """Parse analyzed_benchmarks.txt into a DataFrame."""
    data = []
    current = {}
    with open(filepath) as f:
        for line in f:
            m = re.search(r'BENCHMARK ANALYSIS REPORT: (bench_n\d+_p\d+)', line)
            if m:
                if current:
                    data.append(current)
                name = m.group(1)
                nm = re.match(r'bench_n(\d+)_p(\d+)', name)
                current = {
                    'benchmark': name,
                    'n': int(nm.group(1)),
                    'p': int(nm.group(2)),
                    'ideal_depth': None,
                    'magic_ratio': None,
                    'bottleneck_pct': 0.0,
                    'avg_simul_t': None,
                    'perim_limit': None,
                }
                continue

            if not current:
                continue

            m = re.search(r'Circuit Depth:\s+(\d+)', line)
            if m:
                current['ideal_depth'] = int(m.group(1))

            m = re.search(r'Magic Ratio:\s+([\d.]+)%', line)
            if m:
                current['magic_ratio'] = float(m.group(1))

            m = re.search(r'Avg Simul T:\s+([\d.]+)', line)
            if m:
                current['avg_simul_t'] = float(m.group(1))

            m = re.search(r'2D Perim Limit:\s+(\d+)', line)
            if m:
                current['perim_limit'] = int(m.group(1))

            m = re.search(r'In \d+ layers \(([\d.]+)% of execution\)', line)
            if m:
                current['bottleneck_pct'] = float(m.group(1))

    if current:
        data.append(current)
    return pd.DataFrame(data)


def compute_reduction(df):
    """Add normalized reduction columns for each ARCH_C config."""
    for col in ['C_S2', 'C_S4', 'C_S8', 'C_S16']:
        denom = df['NO_HBM'] - df['ARCH_A']
        numer = df['NO_HBM'] - df[col]
        df[f'reduction_{col}'] = numer / denom.replace(0, float('nan'))
    return df


def compute_ideal_overhead(df_results, df_analysis):
    """Merge results with ideal depth and compute overhead ratio."""
    merged = df_results.merge(df_analysis[['benchmark', 'ideal_depth']], on='benchmark', how='left')
    for col in ['NO_HBM', 'ARCH_A', 'C_S2', 'C_S4', 'C_S8', 'C_S16']:
        merged[f'overhead_{col}'] = merged[col] / merged['ideal_depth']
    return merged
