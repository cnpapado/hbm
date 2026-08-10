"""
Aggregate a results dir of .res files into a comparison table.

Each .res file holds one line:  <bench> | <ARCH_NAME> | <timesteps|TIMEOUT>

Cost ratio = actual timesteps / ideal timesteps, where ideal is the DAG depth
over cx/t/tdg gates (the paper's Eq. 2 denominator). Ideal is read from the
source .qasm, so the benchmark dir must be reachable.

Usage:
    python collect_jku.py                          # defaults below
    python collect_jku.py --results-dir results_jku \
                          --bench-dir ../quantum-compiler-benchmark-circuits/jku_suite
    python collect_jku.py --csv jku_summary.csv    # also write a CSV
"""

import argparse
import csv
import glob
import os
import re
import sys
from collections import defaultdict


def ideal_depth(qasm_path):
    """DAG depth counting only cx/t/tdg, computed without qiskit.

    Mirrors circ.depth(filter_function=...) for these gate names: track a
    per-qubit level and take the max.
    """
    level = defaultdict(int)
    pat_cx = re.compile(r"^\s*cx\s+(\w+)\[(\d+)\]\s*,\s*(\w+)\[(\d+)\]\s*;")
    pat_t = re.compile(r"^\s*(t|tdg)\s+(\w+)\[(\d+)\]\s*;")
    with open(qasm_path) as f:
        for line in f:
            m = pat_cx.match(line)
            if m:
                a, b = int(m.group(2)), int(m.group(4))
                nxt = max(level[a], level[b]) + 1
                level[a] = level[b] = nxt
                continue
            m = pat_t.match(line)
            if m:
                q = int(m.group(3))
                level[q] += 1
    return max(level.values()) if level else 0


def parse_res(path):
    with open(path) as f:
        line = f.read().strip()
    parts = [p.strip() for p in line.split("|")]
    if len(parts) != 3:
        return None
    bench, arch, val = parts
    return bench, arch, val


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--results-dir", default="results_jku")
    ap.add_argument(
        "--bench-dir", default="../quantum-compiler-benchmark-circuits/jku_suite"
    )
    ap.add_argument("--csv", help="also write the table to this CSV path")
    ap.add_argument(
        "--sort",
        choices=["name", "ideal", "gain"],
        default="ideal",
        help="row ordering (default: by ideal depth)",
    )
    args = ap.parse_args()

    res_files = sorted(glob.glob(os.path.join(args.results_dir, "*.res")))
    if not res_files:
        print(f"no .res files in {args.results_dir}/", file=sys.stderr)
        sys.exit(1)

    # bench -> arch -> value
    table = defaultdict(dict)
    archs = set()
    for p in res_files:
        parsed = parse_res(p)
        if parsed is None:
            print(f"  (skipping malformed {p})", file=sys.stderr)
            continue
        bench, arch, val = parsed
        table[bench][arch] = val
        archs.add(arch)

    # order archs: baseline, then ARCH_A, then C by ratio, then D by ratio
    def arch_key(a):
        if a == "no_hbm":
            return (0, 0)
        if a == "ARCH_A":
            return (1, 0)
        m = re.search(r"shared_(\d+)", a)
        n = int(m.group(1)) if m else 0
        fam = 2 if "ARCH_C" in a else 3 if "ARCH_D" in a else 4
        return (fam, n)

    archs = sorted(archs, key=arch_key)

    rows = []
    for bench, per_arch in table.items():
        qasm = os.path.join(args.bench_dir, f"{bench}.qasm")
        ideal = ideal_depth(qasm) if os.path.exists(qasm) else None
        row = {"benchmark": bench, "ideal": ideal}
        for a in archs:
            row[a] = per_arch.get(a, "-")
        rows.append(row)

    def cost(row, a):
        v = row.get(a)
        if v in (None, "-", "TIMEOUT") or not row.get("ideal"):
            return None
        try:
            return int(v) / row["ideal"]
        except ValueError:
            return None

    if args.sort == "name":
        rows.sort(key=lambda r: r["benchmark"])
    elif args.sort == "ideal":
        rows.sort(key=lambda r: (r["ideal"] is None, r["ideal"] or 0))
    else:  # gain: biggest ARCH_D-vs-ARCH_C improvement first
        def gain(r):
            c = cost(r, "ARCH_C_shared_4")
            d = cost(r, "ARCH_D_shared_4")
            return -(c - d) if (c is not None and d is not None) else 1e9
        rows.sort(key=gain)

    # ---- print ----
    w_b = max(len("benchmark"), max(len(r["benchmark"]) for r in rows))
    hdr = f"{'benchmark':<{w_b}}  {'ideal':>6}"
    for a in archs:
        hdr += f"  {a:>22}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        line = f"{r['benchmark']:<{w_b}}  {str(r['ideal'] or '?'):>6}"
        for a in archs:
            c = cost(r, a)
            cell = f"{r[a]} ({c:.2f})" if c is not None else str(r[a])
            line += f"  {cell:>22}"
        print(line)

    # ---- aggregate ----
    print()
    print(f"{'config':<24}{'n':>5}{'timeouts':>10}{'mean cost':>12}{'median cost':>13}")
    print("-" * 64)
    for a in archs:
        costs = [c for r in rows if (c := cost(r, a)) is not None]
        n_to = sum(1 for r in rows if r.get(a) == "TIMEOUT")
        if costs:
            s = sorted(costs)
            med = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
            print(f"{a:<24}{len(costs):>5}{n_to:>10}{sum(costs)/len(costs):>12.3f}{med:>13.3f}")
        else:
            print(f"{a:<24}{0:>5}{n_to:>10}{'-':>12}{'-':>13}")

    # head-to-head on benchmarks where both C and D completed
    c_name, d_name = "ARCH_C_shared_4", "ARCH_D_shared_4"
    if c_name in archs and d_name in archs:
        both = [
            (cost(r, c_name), cost(r, d_name))
            for r in rows
            if cost(r, c_name) is not None and cost(r, d_name) is not None
        ]
        if both:
            wins = sum(1 for c, d in both if d < c)
            ties = sum(1 for c, d in both if d == c)
            print()
            print(f"ARCH_D vs ARCH_C on {len(both)} benchmarks where both completed:")
            print(f"  3D better: {wins}   tie: {ties}   worse: {len(both)-wins-ties}")
            mc = sum(c for c, _ in both) / len(both)
            md = sum(d for _, d in both) / len(both)
            print(f"  mean cost ratio  C={mc:.3f}  D={md:.3f}  (speedup {mc/md:.3f}x)")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["benchmark", "ideal"] + archs + [f"cost_{a}" for a in archs])
            for r in rows:
                costs = [cost(r, a) for a in archs]
                w.writerow(
                    [r["benchmark"], r["ideal"]]
                    + [r[a] for a in archs]
                    + [f"{c:.4f}" if c is not None else "" for c in costs]
                )
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
