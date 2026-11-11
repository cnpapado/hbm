"""
collect_results.py
------------------
Gather timesteps, cost ratio and MSRD from the wisq .out files written by
run_ising_archs.py, in the layout of test/new_benchmarks_gathered.txt.

  Timesteps  = len(steps)                         (print_timesteps.py --summary)
  Cost ratio = max(timesteps / L, 1)              (plot_congestion_trends.py)
  MSRD       = mean T path length + 1             (analyze_routing_steps.py)

L is the cx/T-only ASAP depth from scripts/t_density.py.

Usage:
  python collect_results.py <bench_dir> <out_dir>
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from t_density import analyze as density  # noqa: E402

ARCHS = [
    ("no_hbm", "Baseline"),
    ("ARCH_A", "Arch A"),
    ("ARCH_C_shared_2", "C_S2"),
    ("ARCH_C_shared_4", "C_S4"),
    ("ARCH_C_shared_8", "C_S8"),
    ("ARCH_C_shared_16", "C_S16"),
]


def load(out):
    """(timesteps, msrd) or None for a missing / timed-out run."""
    if not out.exists():
        return None
    try:
        data = json.loads(out.read_text())
    except json.JSONDecodeError:
        return None
    steps = data.get("steps")
    if not isinstance(steps, list):
        return None
    paths = [len(op["path"]) for step in steps for op in step if op["op"] in ("t", "tdg")]
    msrd = sum(paths) / len(paths) + 1 if paths else 0.0
    return len(steps), msrd


def table(title, rows, fmt):
    w = 103
    lines = [title, "=" * w]
    lines.append(f"{'Benchmark':<25} | " + " | ".join(f"{a:<10}" for _, a in ARCHS))
    lines.append("-" * w)
    for name, vals in rows:
        lines.append(f"{name:<25} | " + " | ".join(f"{fmt(v):<10}" for v in vals))
    lines.append("=" * w)
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("bench_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    benches = sorted(args.bench_dir.glob("*.qasm"), key=lambda p: int(p.stem.split("_n")[-1]))
    steps_rows, cost_rows, msrd_rows, info = [], [], [], []
    for b in benches:
        d = density(str(b))
        res = [load(args.out_dir / f"{b.stem}_{a}.out") for a, _ in ARCHS]
        steps_rows.append((b.stem, [r[0] if r else None for r in res]))
        cost_rows.append((b.stem, [max(r[0] / d["L"], 1.0) if r else None for r in res]))
        msrd_rows.append((b.stem, [r[1] if r else None for r in res]))
        info.append(f"{b.stem:<25} | N={d['N']:<4} T={d['T']:<7} cx={d['cx']:<5} L={d['L']:<6} "
                    f"density={d['density']:.3f}  max_T/4sqrtN={d['cong']:.2f}")

    na = "TIMEOUT"
    print(table("Timesteps", steps_rows, lambda v: na if v is None else str(v)))
    print()
    print(table("Cost ratio (timesteps / L)", cost_rows, lambda v: na if v is None else f"{v:.2f}"))
    print()
    print(table("MSRD", msrd_rows, lambda v: na if v is None else f"{v:.3f}"))
    print()
    print("Circuit stats (DASCOT view: cx + t/tdg only)")
    print("\n".join(info))
