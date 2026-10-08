"""Compare baselines against the proposed designs from analyze.py's CSV.

For each benchmark, vertical-noise multiplier p' and source setting (recharge rounds), every
design family is reported at its best knob (lowest STV among feasible, finished runs).
Three pairs, each isolating what the top layer buys:

  P1  cultivation: D2 (next door)            vs D3 (on top)
  P2  factories:   best of D0/D1 (in-plane)  vs D5 (on top)
  P3  packing:     D2 (next door)            vs D4 (compact + on top)

ratio = STV(baseline) / STV(proposed): > 1 means the proposed design wins.

Outputs: <prefix>_pairs.csv, <prefix>_regimes.csv and <prefix>_pairs.png.

Usage:
  python compare.py revision_results.csv --prefix rev --R 70
"""

import argparse
import csv
import math
from collections import defaultdict

PAIRS = [
    ("P1 cultivation: next door vs on top", ("D2",), ("D3",)),
    ("P2 factories: in-plane vs on top", ("D0", "D1"), ("D5",)),
    ("P3 packing: next door vs compact + on top", ("D2",), ("D4",)),
]


def load(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("STV", "Q", "rounds", "t_density", "pprime_mult", "recharge_rounds", "steps"):
            try:
                r[k] = float(r[k])
            except (KeyError, TypeError, ValueError):
                r[k] = math.nan
        r["feasible"] = r.get("feasible") == "True"
    return rows


def best_by_family(rows):
    """(bench, pprime, source, recharge_rounds, family) -> best feasible row."""
    best = {}
    for r in rows:
        if r.get("status") != "ok" or not r["feasible"] or math.isnan(r["STV"]):
            continue
        key = (r["bench"], r["pprime_mult"], r["source"], r["recharge_rounds"], r["family"])
        if key not in best or r["STV"] < best[key]["STV"]:
            best[key] = r
    return best


def pair_rows(rows):
    best = best_by_family(rows)
    benches = sorted({r["bench"] for r in rows if r.get("status") == "ok"})
    settings = sorted({(r["pprime_mult"], r["source"], r["recharge_rounds"]) for r in rows
                       if r.get("status") == "ok"})
    out = []
    for name, base_fams, prop_fams in PAIRS:
        for bench in benches:
            for pp, source, rr in settings:
                pick = lambda fams: min(  # noqa: E731
                    (best[k] for k in ((bench, pp, source, rr, f) for f in fams) if k in best),
                    key=lambda r: r["STV"], default=None)
                b, p = pick(base_fams), pick(prop_fams)
                if b is None and p is None:
                    continue
                ref = b or p
                out.append(dict(
                    pair=name, bench=bench, pprime_mult=pp, source=source,
                    recharge_rounds=rr, N=ref["N"], t_density=ref["t_density"],
                    baseline=b["spec"] if b else "infeasible",
                    proposed=p["spec"] if p else "infeasible",
                    baseline_STV=b["STV"] if b else math.nan,
                    proposed_STV=p["STV"] if p else math.nan,
                    ratio=(b["STV"] / p["STV"]) if b and p else (math.inf if p else 0.0),
                    qubit_ratio=(b["Q"] / p["Q"]) if b and p else math.nan,
                    time_ratio=(b["rounds"] / p["rounds"]) if b and p else math.nan,
                ))
    return out


def regimes(pairs, n_bins=3):
    """Fraction of benchmarks where the proposed design wins, per T-density tercile."""
    out = []
    by = defaultdict(list)
    for r in pairs:
        by[(r["pair"], r["pprime_mult"], r["recharge_rounds"])].append(r)
    for (pair, pp, rr), rs in sorted(by.items()):
        dens = sorted(r["t_density"] for r in rs)
        cuts = [dens[int(len(dens) * i / n_bins)] for i in range(1, n_bins)]
        for i in range(n_bins):
            lo = cuts[i - 1] if i > 0 else -math.inf
            hi = cuts[i] if i < n_bins - 1 else math.inf
            sel = [r for r in rs if lo <= r["t_density"] < hi]
            if not sel:
                continue
            wins = sum(r["ratio"] > 1 for r in sel)
            ratios = sorted(r["ratio"] for r in sel if math.isfinite(r["ratio"]) and r["ratio"] > 0)
            out.append(dict(pair=pair, pprime_mult=pp, recharge_rounds=rr,
                            t_density_bin=["low", "mid", "high"][i] if n_bins == 3 else i,
                            n=len(sel), proposed_wins=wins, win_fraction=wins / len(sel),
                            median_ratio=ratios[len(ratios) // 2] if ratios else math.nan))
    return out


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def plot(pairs, path, R):
    import matplotlib.pyplot as plt

    colors = {1.0: "#2a78d6", 5.0: "#eb6834", 10.0: "#1baf7a"}  # fixed categorical order
    fig, axes = plt.subplots(1, len(PAIRS), figsize=(5.2 * len(PAIRS), 4.2), sharey=True)
    for ax, (name, _, _) in zip(axes, PAIRS):
        sel = [r for r in pairs if r["pair"] == name and math.isfinite(r["ratio"])
               and r["ratio"] > 0 and (r["source"] == "factory" or r["recharge_rounds"] == R)]
        for pp in sorted({r["pprime_mult"] for r in sel}):
            pts = [r for r in sel if r["pprime_mult"] == pp]
            ax.scatter([r["t_density"] for r in pts], [r["ratio"] for r in pts], s=30,
                       color=colors.get(pp, "#6d6d6d"), edgecolor="white", linewidth=1,
                       label=f"p' = {pp:g}p", zorder=3)
        ax.axhline(1, color="#52514e", lw=1, ls="--", zorder=2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(name, fontsize=10, loc="left")
        ax.set_xlabel("T density (T per qubit per ideal step)")
        ax.grid(True, color="#e6e5e1", lw=0.8)
    axes[0].set_ylabel("STV(baseline) / STV(proposed)\n> 1: proposed wins")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle(f"Cultivation recharge R = {R:g} rounds (factory pairs use the factory period)",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=170)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--prefix", default="revision")
    ap.add_argument("--R", type=float, default=70, help="cultivation recharge rounds to plot")
    args = ap.parse_args()

    pairs = pair_rows(load(args.csv))
    write_csv(f"{args.prefix}_pairs.csv", pairs)
    reg = regimes(pairs)
    write_csv(f"{args.prefix}_regimes.csv", reg)
    if pairs:
        plot(pairs, f"{args.prefix}_pairs.png", args.R)
    print(f"{len(pairs)} pair rows -> {args.prefix}_pairs.csv, {args.prefix}_regimes.csv, "
          f"{args.prefix}_pairs.png")
    for r in reg:
        print(f"{r['pair'][:2]} p'={r['pprime_mult']:g}p R={r['recharge_rounds']:g} "
              f"{r['t_density_bin']:>4}: proposed wins {r['proposed_wins']}/{r['n']} "
              f"(median ratio {r['median_ratio']:.2f})")


if __name__ == "__main__":
    main()
