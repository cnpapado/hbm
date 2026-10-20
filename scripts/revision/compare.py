"""Compare the baselines against HBM (cultivation on top) by space-time volume.

Three pairs, all with HBM = D3 (cultivation patches on the top layer):

  P1  DASCOT + cultivation (D2, patches in the data plane)        vs HBM
  P2  DASCOT + factories   (D0, factories around the data block)  vs HBM
  P3  Litinski PPM (ppm_baseline.py, cultivation patches)          vs HBM

ratio = STV(baseline) / STV(HBM): > 1 means HBM wins. STV is the only metric. Both sides
of a pair are at the same code distance d (the d the runs were simulated at, 13), as in the
HBMS paper; the vertical-link error p' does not enter STV.

Knobs. Each family is reported at its best knob (lowest STV among feasible, finished runs):
D2 layout (wide/tight), D3 k, D0 factory count, PPM block. The cultivation recharge time R
is a knob too: every pair is reported at each R that was run (both sides at the same R,
D0 at its own factory period) and at R = "best", where each side picks its best R. "best"
matters when the low-fidelity grade (R = 60, 3e-6) is infeasible for a circuit's T count.

Runs that cannot matter are not queued (submit_revision.sh): an R whose grade alone breaks
the target (T count x T error > --target) is infeasible without running it, and counts here
as run and infeasible wherever the family ran on that circuit. For R = best a side needs only
the R values that can win: the feasible grades not beaten by a feasible grade with shorter
recharge and no more qubits (with the default grades, the shortest feasible R).

P1 and P2 are plotted against T density (T per qubit per ideal step); P3 against T gates
per ideal step (lambda = T count / ideal depth), because PPM runs one T gate per step and
HBM one ideal step per step, so lambda is their time ratio before stalls.

Outputs: <prefix>_pairs.csv, <prefix>_regimes.csv and <prefix>_pairs.png (at --R).

Usage:
  python compare.py rev.csv ppm.csv --prefix rev            # plot at R = best
  python compare.py rev.csv ppm.csv --prefix rev --R 60     # plot at R = 60
  python compare.py rev.csv ppm.csv --prefix rev --rows     # also print every pair row
  python compare.py rev.csv --knobs                         # how often each layout/count wins
"""

import argparse
import csv
import math
import statistics
from collections import defaultdict

from analyze import parse_grades

PAIRS = [  # (name, baseline families, HBM families, x variable)
    ("P1 DASCOT + cultivation vs HBM", ("D2",), ("D3",), "t_density"),
    ("P2 DASCOT + factories vs HBM", ("D0",), ("D3",), "t_density"),
    ("P3 PPM vs HBM", ("PPM",), ("D3",), "t_per_step"),
]
X_LABEL = {"t_density": "T density (T per qubit per ideal step)",
           "t_per_step": "T gates per ideal step (T count / ideal depth)"}
BEST = "best"


def load(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("STV", "t_density", "recharge_rounds", "steps", "n_t", "ideal_depth"):
            try:
                r[k] = float(r[k])
            except (KeyError, TypeError, ValueError):
                r[k] = math.nan
        r["d"] = int(float(r["d_sim"])) if r.get("d_sim") else None
        r["feasible"] = r.get("feasible") == "True"
    return rows


def slots(r):
    """Recharge settings a row competes in: its own R and "best" for cultivation rows, the
    single factory setting (None) for factory rows."""
    return (r["recharge_rounds"], BEST) if r["source"] == "cultivation" else (None,)


def best_by_family(rows):
    """(bench, d, family, R slot) -> lowest-STV feasible row."""
    best = {}
    for r in rows:
        if r.get("status") != "ok" or not r["feasible"] or math.isnan(r["STV"]):
            continue
        for slot in slots(r):
            key = (r["bench"], r["d"], r["family"], slot)
            if key not in best or r["STV"] < best[key]["STV"]:
                best[key] = r
    return best


def r_label(R):
    return R if R == BEST else f"{R:g}"


def r_order(label):
    return (1, 0) if label == BEST else (0, float(label))


def pair_rows(rows, grades, target):
    best = best_by_family(rows)
    ok = [r for r in rows if r.get("status") == "ok"]
    factory = {r["family"] for r in ok if r["source"] == "factory"}
    ran = {(r["bench"], r["d"], r["family"], s) for r in ok for s in slots(r) if s != BEST}
    benches = sorted({r["bench"] for r in ok})
    ds = sorted({r["d"] for r in ok})
    sweep = sorted({r["recharge_rounds"] for r in ok if r["source"] == "cultivation"})
    n_t = {r["bench"]: r["n_t"] for r in ok if not math.isnan(r["n_t"])}

    def feasible(bench, R):  # the grade alone meets the target (unknown grade: assume so)
        R = int(R)
        return R not in grades or bench not in n_t or n_t[bench] * grades[R][0] <= target

    for (bench, d, fam, _) in list(ran):  # infeasible R values count as run, see docstring
        if fam not in factory:
            ran |= {(bench, d, fam, R) for R in sweep if not feasible(bench, R)}

    def best_needs(bench):  # the R values that can give a side its lowest STV
        feas = [R for R in sweep if feasible(bench, R)]
        qubits = lambda R: grades[int(R)][1] if int(R) in grades else math.inf  # noqa: E731
        need = [R for R in feas if not any(R2 < R and qubits(R2) <= qubits(R) for R2 in feas)]
        return need or sweep

    out = []
    for name, base_fams, hbm_fams, _ in PAIRS:
        for bench in benches:
            for d in ds:
                for R in sweep + [BEST]:
                    key = lambda f, R: (bench, d, f, None if f in factory else R)  # noqa: E731
                    keys = lambda fams: [key(f, R) for f in fams]  # noqa: E731
                    # At R = best a side must have run every R that can be its best.
                    needs = best_needs(bench) if R == BEST else [R]
                    was_run = lambda fams: any(  # noqa: E731
                        all(key(f, R2) in ran for R2 in needs) for f in fams)
                    if not was_run(base_fams) or not was_run(hbm_fams):
                        continue  # one side was not run here: no pair (unlike "infeasible")
                    pick = lambda fams: min(  # noqa: E731
                        (best[k] for k in keys(fams) if k in best),
                        key=lambda r: r["STV"], default=None)
                    b, p = pick(base_fams), pick(hbm_fams)
                    if b is None and p is None:
                        continue
                    ref = p or b
                    side = lambda r, k: r[k] if r else ""  # noqa: E731
                    out.append(dict(
                        pair=name, bench=bench, d=d, recharge_rounds=r_label(R),
                        N=ref["N"], t_density=ref["t_density"],
                        t_per_step=(ref["n_t"] / ref["ideal_depth"] if ref["ideal_depth"] > 0
                                    else math.nan),
                        baseline=b["spec"] if b else "infeasible",
                        baseline_source=side(b, "source"),
                        baseline_R=side(b, "recharge_rounds"), baseline_steps=side(b, "steps"),
                        baseline_STV=b["STV"] if b else math.nan,
                        hbm=p["spec"] if p else "infeasible",
                        hbm_R=side(p, "recharge_rounds"), hbm_steps=side(p, "steps"),
                        hbm_STV=p["STV"] if p else math.nan,
                        ratio=(b["STV"] / p["STV"]) if b and p else (math.inf if p else 0.0),
                    ))
    return out


def regimes(pairs, n_bins=3):
    """Fraction of benchmarks where HBM wins, per tercile of the pair's x."""
    out = []
    xkey = {name: x for name, _, _, x in PAIRS}
    by = defaultdict(list)
    for r in pairs:
        by[(r["pair"], r["d"], r["recharge_rounds"])].append(r)
    for (pair, d, R) in sorted(by, key=lambda k: (k[0], k[1], r_order(k[2]))):
        x = xkey[pair]
        rs = [r for r in by[(pair, d, R)] if not math.isnan(r[x])]
        if not rs:
            continue
        dens = sorted(r[x] for r in rs)
        cuts = [dens[int(len(dens) * i / n_bins)] for i in range(1, n_bins)]
        for i in range(n_bins):
            lo = cuts[i - 1] if i > 0 else -math.inf
            hi = cuts[i] if i < n_bins - 1 else math.inf
            sel = [r for r in rs if lo <= r[x] < hi]
            if not sel:
                continue
            wins = sum(r["ratio"] > 1 for r in sel)
            ratios = sorted(r["ratio"] for r in sel if math.isfinite(r["ratio"]) and r["ratio"] > 0)
            out.append(dict(pair=pair, d=d, recharge_rounds=R, x=x,
                            x_bin=["low", "mid", "high"][i] if n_bins == 3 else i,
                            n=len(sel), hbm_wins=wins, win_fraction=wins / len(sel),
                            median_ratio=ratios[len(ratios) // 2] if ratios else math.nan))
    return out


def knob_table(rows):
    """Per spec: on how many (bench, d, R) it is its family's lowest STV, and its STV over the
    family's lowest (median, worst). Shows which knob values never matter."""
    ok = [r for r in rows if r.get("status") == "ok" and r["feasible"]
          and not math.isnan(r["STV"])]
    key = lambda r: (r["bench"], r["d"], r["family"], r["recharge_rounds"])  # noqa: E731
    low = {}
    for r in ok:
        low[key(r)] = min(low.get(key(r), math.inf), r["STV"])
    by = defaultdict(list)
    for r in ok:
        by[(r["family"], r["spec"])].append(r["STV"] / low[key(r)])
    print(f"\n{'spec':16s} {'lowest':>8s} {'median':>7s} {'worst':>7s}  (STV / family's lowest, "
          f"same circuit and R)")
    for fam, spec in sorted(by):
        v = sorted(by[(fam, spec)])
        print(f"{spec:16s} {sum(x == 1 for x in v):3d}/{len(v):<4d} {statistics.median(v):6.2f}x "
              f"{v[-1]:6.2f}x")


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#6d6d6d"]  # one per code distance, in order


def plot(pairs, path, R):
    import matplotlib.pyplot as plt

    shown = [p for p in PAIRS if any(r["pair"] == p[0] for r in pairs)]
    fig, axes = plt.subplots(1, len(shown), figsize=(5.2 * len(shown), 4.2), sharey=True,
                             squeeze=False)
    for ax, (name, _, _, x) in zip(axes[0], shown):
        sel = [r for r in pairs if r["pair"] == name and r["recharge_rounds"] == R
               and math.isfinite(r["ratio"]) and r["ratio"] > 0]
        for i, d in enumerate(sorted({r["d"] for r in sel})):
            pts = [r for r in sel if r["d"] == d]
            ax.scatter([r[x] for r in pts], [r["ratio"] for r in pts], s=30,
                       color=COLORS[min(i, len(COLORS) - 1)], edgecolor="white", linewidth=1,
                       label=f"d = {d}", zorder=3)
        ax.axhline(1, color="#52514e", lw=1, ls="--", zorder=2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(X_LABEL[x])
        ax.grid(True, color="#e6e5e1", lw=0.8)
        ax.set_title(name, fontsize=10, loc="left")
    axes[0][0].set_ylabel("STV(baseline) / STV(HBM)\n> 1: HBM wins")
    axes[0][0].legend(frameon=False, fontsize=9)
    what = "each side at its best R" if R == BEST else f"R = {R} rounds"
    fig.suptitle(f"Cultivation recharge: {what} (D0 uses the factory period)",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+", help="output of analyze.py (and of ppm_baseline.py)")
    ap.add_argument("--prefix", default="revision")
    ap.add_argument("--R", default=BEST,
                    help='cultivation recharge rounds to plot, or "best" (default)')
    ap.add_argument("--rows", action="store_true", help="also print every pair row")
    ap.add_argument("--knobs", action="store_true",
                    help="also print how often each layout / factory count is its family's best")
    ap.add_argument("--target", type=float, default=0.01, help="as in analyze.py")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463",
                    help="as in analyze.py")
    args = ap.parse_args()
    plot_R = args.R if args.R == BEST else r_label(float(args.R))

    rows = [r for path in args.csv for r in load(path)]
    pairs = pair_rows(rows, args.cult_grades, args.target)
    write_csv(f"{args.prefix}_pairs.csv", pairs)
    reg = regimes(pairs)
    write_csv(f"{args.prefix}_regimes.csv", reg)
    if pairs:
        plot(pairs, f"{args.prefix}_pairs.png", plot_R)
    print(f"{len(pairs)} pair rows -> {args.prefix}_pairs.csv, {args.prefix}_regimes.csv, "
          f"{args.prefix}_pairs.png")
    for r in reg:
        print(f"{r['pair'][:2]} d={r['d']} R={r['recharge_rounds']:>4s} "
              f"{r['x']} {r['x_bin']:>4}: HBM wins {r['hbm_wins']}/{r['n']} "
              f"(median STV ratio {r['median_ratio']:.2f})")
    if args.rows:
        def side(spec, R, steps):
            tag = f"{spec}@R{R:g}" if isinstance(R, float) and spec.startswith(("D2", "D3", "PPM")) \
                else spec
            steps = f"{steps:.0f}" if isinstance(steps, float) else ""
            return f"{tag:>22s} {steps:>6s}"
        print(f"\n{'':2s} {'bench':16s} {'d':>3s} {'R':>4s} {'baseline':>22s} {'steps':>6s} "
              f"{'HBM':>22s} {'steps':>6s} {'ratio':>6s}  (STV baseline / STV HBM)")
        for r in pairs:
            print(f"{r['pair'][:2]} {r['bench']:16s} {r['d']:3d} {r['recharge_rounds']:>4s} "
                  f"{side(r['baseline'], r['baseline_R'], r['baseline_steps'])} "
                  f"{side(r['hbm'], r['hbm_R'], r['hbm_steps'])} {r['ratio']:6.2f}")
    if args.knobs:
        knob_table(rows)


if __name__ == "__main__":
    main()
