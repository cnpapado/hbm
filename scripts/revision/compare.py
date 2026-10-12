"""Compare baselines against the proposed designs from analyze.py's CSV.

For each benchmark, vertical-noise multiplier p' and source setting (recharge rounds), every
design family is reported at its best knob (lowest STV among feasible, finished runs).
Four pairs, each isolating what the top layer buys:

  P1  cultivation: D2 (next door)            vs D3 (on top)
  P2  factories:   best of D0/D1 (in-plane)  vs D5 (on top)
  P3  packing:     D2 (next door)            vs D4 (compact + on top)
  P4  PPM:         Litinski PPM (ppm_baseline.py) vs best of D3/D4 (on top)

ratio = STV(baseline) / STV(proposed): > 1 means the proposed design wins.
P1-P3 are plotted against T density (T per qubit per ideal step); P4 against T gates per
ideal step (lambda = T count / ideal depth), because PPM runs one T gate per step and
HBMS runs one ideal step per step, so lambda is their time ratio before stalls.

Outputs: <prefix>_pairs.csv, <prefix>_regimes.csv, <prefix>_pairs.png and <prefix>_ppm.png
(P4 split into STV, time and qubit ratios).

Usage:
  python compare.py rev.csv --prefix rev --R 60
  python compare.py rev.csv ppm.csv --prefix rev --R 60     # with the PPM rows
"""

import argparse
import csv
import math
from collections import defaultdict

PAIRS = [  # (name, baseline families, proposed families, x variable)
    ("P1 cultivation: next door vs on top", ("D2",), ("D3",), "t_density"),
    ("P2 factories: in-plane vs on top", ("D0", "D1"), ("D5",), "t_density"),
    ("P3 packing: next door vs compact + on top", ("D2",), ("D4",), "t_density"),
    ("P4 Pauli-product measurements vs on top", ("PPM",), ("D3", "D4"), "t_per_step"),
]
X_LABEL = {"t_density": "T density (T per qubit per ideal step)",
           "t_per_step": "T gates per ideal step (T count / ideal depth)"}


def load(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("STV", "Q", "rounds", "t_density", "pprime_mult", "recharge_rounds", "steps",
                  "n_t", "ideal_depth"):
            try:
                r[k] = float(r[k])
            except (KeyError, TypeError, ValueError):
                r[k] = math.nan
        r["feasible"] = r.get("feasible") == "True"
        r["rerun_needed"] = r.get("rerun_needed") == "True"
    return rows


def best_by_family(rows):
    """(bench, pprime, source, recharge_rounds, family) -> best feasible row.

    Rows simulated at their own d_req are preferred; a row whose simulation d differs from
    its d_req (rerun_needed) is used only when no consistent row exists for that key.
    """
    best = {}
    for r in rows:
        if r.get("status") != "ok" or not r["feasible"] or math.isnan(r["STV"]):
            continue
        key = (r["bench"], r["pprime_mult"], r["source"], r["recharge_rounds"], r["family"])
        rank = (r["rerun_needed"], r["STV"])
        if key not in best or rank < (best[key]["rerun_needed"], best[key]["STV"]):
            best[key] = r
    return best


def pair_rows(rows):
    best = best_by_family(rows)
    benches = sorted({r["bench"] for r in rows if r.get("status") == "ok"})
    settings = sorted({(r["pprime_mult"], r["source"], r["recharge_rounds"]) for r in rows
                       if r.get("status") == "ok"})
    ran = {(r["bench"], r["pprime_mult"], r["source"], r["recharge_rounds"], r["family"])
           for r in rows if r.get("status") == "ok"}
    out = []
    for name, base_fams, prop_fams, _ in PAIRS:
        for bench in benches:
            for pp, source, rr in settings:
                keys = lambda fams: [(bench, pp, source, rr, f) for f in fams]  # noqa: E731
                if not any(k in ran for k in keys(base_fams)) or not any(
                        k in ran for k in keys(prop_fams)):
                    continue  # one side was not run here: no pair (unlike "infeasible")
                pick = lambda fams: min(  # noqa: E731
                    (best[k] for k in keys(fams) if k in best),
                    key=lambda r: r["STV"], default=None)
                b, p = pick(base_fams), pick(prop_fams)
                if b is None and p is None:
                    continue
                ref = p or b
                out.append(dict(
                    pair=name, bench=bench, pprime_mult=pp, source=source,
                    recharge_rounds=rr, N=ref["N"], t_density=ref["t_density"],
                    t_per_step=(ref["n_t"] / ref["ideal_depth"] if ref["ideal_depth"] > 0
                                else math.nan),
                    baseline=b["spec"] if b else "infeasible",
                    proposed=p["spec"] if p else "infeasible",
                    baseline_STV=b["STV"] if b else math.nan,
                    proposed_STV=p["STV"] if p else math.nan,
                    ratio=(b["STV"] / p["STV"]) if b and p else (math.inf if p else 0.0),
                    qubit_ratio=(b["Q"] / p["Q"]) if b and p else math.nan,
                    time_ratio=(b["rounds"] / p["rounds"]) if b and p else math.nan,
                    provisional=any(x is not None and x["rerun_needed"] for x in (b, p)),
                ))
    return out


def regimes(pairs, n_bins=3):
    """Fraction of benchmarks where the proposed design wins, per tercile of the pair's x."""
    out = []
    xkey = {name: x for name, _, _, x in PAIRS}
    by = defaultdict(list)
    for r in pairs:
        by[(r["pair"], r["pprime_mult"], r["recharge_rounds"])].append(r)
    for (pair, pp, rr), rs in sorted(by.items()):
        x = xkey[pair]
        rs = [r for r in rs if not math.isnan(r[x])]
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
            out.append(dict(pair=pair, pprime_mult=pp, recharge_rounds=rr, x=x,
                            x_bin=["low", "mid", "high"][i] if n_bins == 3 else i,
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


COLORS = {1.0: "#2a78d6", 5.0: "#eb6834", 10.0: "#1baf7a"}  # fixed categorical order


def _scatter(ax, sel, x, y):
    for pp in sorted({r["pprime_mult"] for r in sel}):
        pts = [r for r in sel if r["pprime_mult"] == pp and math.isfinite(r[y]) and r[y] > 0]
        ax.scatter([r[x] for r in pts], [r[y] for r in pts], s=30,
                   color=COLORS.get(pp, "#6d6d6d"), edgecolor="white", linewidth=1,
                   label=f"p' = {pp:g}p", zorder=3)
    ax.axhline(1, color="#52514e", lw=1, ls="--", zorder=2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(X_LABEL[x])
    ax.grid(True, color="#e6e5e1", lw=0.8)


def _at_R(pairs, name, R):
    return [r for r in pairs if r["pair"] == name and math.isfinite(r["ratio"]) and r["ratio"] > 0
            and (r["source"] == "factory" or r["recharge_rounds"] == R)]


def plot(pairs, path, R):
    import matplotlib.pyplot as plt

    shown = [p for p in PAIRS if any(r["pair"] == p[0] for r in pairs)]
    fig, axes = plt.subplots(1, len(shown), figsize=(5.2 * len(shown), 4.2), sharey=True,
                             squeeze=False)
    for ax, (name, _, _, x) in zip(axes[0], shown):
        _scatter(ax, _at_R(pairs, name, R), x, "ratio")
        ax.set_title(name, fontsize=10, loc="left")
    axes[0][0].set_ylabel("STV(baseline) / STV(proposed)\n> 1: proposed wins")
    axes[0][0].legend(frameon=False, fontsize=9)
    fig.suptitle(f"Cultivation recharge R = {R:g} rounds (factory pairs use the factory period)",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_ppm(pairs, path, R):
    """P4 split into its two factors: STV ratio = time ratio x qubit ratio."""
    import matplotlib.pyplot as plt

    name, _, _, x = PAIRS[3]
    sel = _at_R(pairs, name, R)
    if not sel:
        return False
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.2))
    for ax, (y, title) in zip(axes, [("ratio", "STV: PPM / on top"),
                                     ("time_ratio", "runtime: PPM / on top"),
                                     ("qubit_ratio", "qubits: PPM / on top")]):
        _scatter(ax, sel, x, y)
        ax.set_title(title, fontsize=10, loc="left")
    axes[0].set_ylabel("> 1: on top wins")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle(f"{name}, cultivation R = {R:g} rounds", fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+", help="output of analyze.py (and of ppm_baseline.py)")
    ap.add_argument("--prefix", default="revision")
    ap.add_argument("--R", type=float, default=60, help="cultivation recharge rounds to plot")
    args = ap.parse_args()

    pairs = pair_rows([r for path in args.csv for r in load(path)])
    write_csv(f"{args.prefix}_pairs.csv", pairs)
    reg = regimes(pairs)
    write_csv(f"{args.prefix}_regimes.csv", reg)
    if pairs:
        plot(pairs, f"{args.prefix}_pairs.png", args.R)
        if plot_ppm(pairs, f"{args.prefix}_ppm.png", args.R):
            print(f"P4 breakdown -> {args.prefix}_ppm.png")
    print(f"{len(pairs)} pair rows -> {args.prefix}_pairs.csv, {args.prefix}_regimes.csv, "
          f"{args.prefix}_pairs.png")
    for r in reg:
        print(f"{r['pair'][:2]} p'={r['pprime_mult']:g}p R={r['recharge_rounds']:g} "
              f"{r['x']} {r['x_bin']:>4}: proposed wins {r['proposed_wins']}/{r['n']} "
              f"(median ratio {r['median_ratio']:.2f})")


if __name__ == "__main__":
    main()
