"""Candidate figures for a revision campaign (analyze.py's CSV), to pick how to show it.

  python plot_results.py rev.csv --out figs/ [--circuit ising_n66]

One PNG per view:
  heatmap.png     every configuration's STV over the best on its circuit
  ratios.png      P1, P1c, P2 per circuit (> 1: HBM wins), as in stv_table.py
  scaling.png     each family's best STV against N, Ising and Heisenberg apart
  sharing.png     the best 2D baseline's STV over each HBM layout's, factories and cultivation
  spacetime.png   one circuit: where the qubits go and how many rounds, per configuration
  tradeoff.png    qubits against rounds per configuration, with lines of equal STV
Cells are those of stv_table.py (cultivation at its lowest-STV R). A run whose program error
breaks the target at the simulated d (meets_target False, mostly idling over many steps) is
marked with a dagger or a hollow marker: at the larger d it needs its STV would grow.
"""

import argparse
import csv
import math
import os
import re
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from analyze import parse_grades  # noqa: E402
from stv_table import COLS, CULT, HBM, HBMC, cell, num  # noqa: E402

NAME = dict((s, c) for c, s in COLS)
COLOR = {
    "D2-wide": "#c4501b", "D2-tight": "#ef9a62", "D0-alt": "#6b6a66",
    "D3-k1-fact": "#173f84", "D3-s2-fact": "#2f64b8", "D3-s4-fact": "#5288d6",
    "D3-s8-fact": "#82aee6", "D3-s16-fact": "#b6d1f2",
    "D3-k1": "#0f6a48", "D3-s2": "#22936a", "D3-s4": "#47b48a", "D3-s8": "#7fcfae",
    "D3-s16": "#b5e5d0",
}
SHARING = [("Ded", "k1"), ("S2", "s2"), ("S4", "s4"), ("S8", "s8"), ("S16", "s16")]
INK, GRID = "#2b2a27", "#e4e2dc"
plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK,
    "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 10, "axes.titlelocation": "left", "savefig.dpi": 170,
    "savefig.bbox": "tight",
})


def circuit(bench):
    """'ising_n10' -> ('Ising', 10); 'heisenberg_qedc_n16' -> ('Heisenberg', 16)."""
    m = re.match(r"([a-z]+)\D*?(\d+)$", bench)
    return (m.group(1).capitalize(), int(m.group(2))) if m else (bench, 0)


def label(bench):
    fam, n = circuit(bench)
    return f"{fam} n{n}"


def load(path):
    groups = defaultdict(list)
    for r in csv.DictReader(open(path)):
        groups[(r["bench"], r["spec"])].append(r)
    cells = defaultdict(dict)
    for (bench, spec), rows in groups.items():
        c = cell(rows)
        if isinstance(c, dict):
            cells[bench][spec] = c
    benches = sorted(cells, key=lambda b: (circuit(b)[0] != "Ising", circuit(b)))
    return cells, benches


def stv(c):
    return num(c["STV"])


def misses(c):
    return c.get("meets_target") != "True"


def best(cs, specs):
    """The lowest-STV cell among specs, or None."""
    got = [cs[s] for s in specs if s in cs]
    return min(got, key=stv) if got else None


def grade(cs):
    """The recharge rounds of a circuit's cultivation runs (60 or 360), or None."""
    for s in CULT + HBMC:
        if s in cs:
            return int(cs[s]["recharge_rounds"])
    return None


def marker(ax, x, y, color, miss, **kw):
    ax.scatter(x, y, s=kw.pop("s", 34), color="white" if miss else color, edgecolor=color,
               linewidth=1.3, zorder=3, **kw)


def specs_in(cells, benches):
    return [s for _, s in COLS if any(s in cells[b] for b in benches)]


def heatmap(cells, benches, path):
    specs = specs_in(cells, benches)
    m = np.full((len(benches), len(specs)), np.nan)
    for i, b in enumerate(benches):
        lo = min(stv(c) for c in cells[b].values())
        for j, s in enumerate(specs):
            if s in cells[b]:
                m[i, j] = stv(cells[b][s]) / lo
    top = np.nanmax(m)
    fig, ax = plt.subplots(figsize=(1.2 + 0.64 * len(specs), 0.8 + 0.36 * len(benches)))
    im = ax.imshow(m, cmap="YlOrRd", norm=LogNorm(1, top), aspect="auto")
    for i, b in enumerate(benches):
        for j, s in enumerate(specs):
            v = m[i, j]
            if np.isnan(v):
                ax.text(j, i, ".", ha="center", va="center", color=INK)
                continue
            text = (f"{v:.2f}" if v < 10 else f"{v:.0f}") + ("†" if misses(cells[b][s]) else "")
            dark = math.log(v) > 0.55 * math.log(top)
            ax.text(j, i, text, ha="center", va="center", fontsize=7.5,
                    color="white" if dark else INK, fontweight="bold" if v == 1 else None)
            if v == 1:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=INK, lw=1.6))
    for k, s in enumerate(specs[:-1]):  # rules between the families
        if (s in CULT + ("D0-alt",)) != (specs[k + 1] in CULT + ("D0-alt",)) or \
                (s in HBM) != (specs[k + 1] in HBM):
            ax.axvline(k + 0.5, color="white", lw=3)
    ax.set_xticks(range(len(specs)), [NAME[s] for s in specs], rotation=40, ha="right")
    ax.set_yticks(range(len(benches)),
                  [f"{label(b)}  T={num(next(iter(cells[b].values()))['n_t']):,.0f}  "
                   f"R{grade(cells[b])}" for b in benches])
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01, label="STV / best STV on the circuit")
    ax.set_title("STV relative to the best configuration per circuit (boxed = best; "
                 "† misses the error target at this d)")
    fig.savefig(path)
    plt.close(fig)


def pairs(cs):
    cult, hbm, hbmc = best(cs, CULT), best(cs, HBM), best(cs, HBMC)
    d0 = cs.get("D0-alt")
    out = {}
    if cult and hbm:
        out["P1  2D-Cult / HBM"] = stv(cult) / stv(hbm)
    if cult and hbmc:
        out["P1c 2D-Cult / HBM-Cult"] = stv(cult) / stv(hbmc)
    if d0 and hbm:
        out["P2  Planar-2D / HBM"] = stv(d0) / stv(hbm)
    return out


def ratios(cells, benches, path):
    names = ["P1  2D-Cult / HBM", "P1c 2D-Cult / HBM-Cult", "P2  Planar-2D / HBM"]
    colors = ["#c4501b", "#0f6a48", "#6b6a66"]
    fig, ax = plt.subplots(figsize=(1.5 + 0.62 * len(benches), 3.6))
    for i, b in enumerate(benches):
        if grade(cells[b]) == 360:
            ax.axvspan(i - 0.5, i + 0.5, color="#f3efe6", zorder=0)
    for k, (name, color) in enumerate(zip(names, colors)):
        xs, ys = [], []
        for i, b in enumerate(benches):
            r = pairs(cells[b]).get(name)
            if r is not None:
                xs.append(i + (k - 1) * 0.22)
                ys.append(r)
        ax.scatter(xs, ys, s=38, color=color, edgecolor="white", lw=0.8, zorder=3,
                   label=name)
        for x, y in zip(xs, ys):
            ax.annotate(f"{y:.2f}" if y < 10 else f"{y:.0f}", (x, y),
                        xytext=(7, -3) if k == 2 else (0, 5), textcoords="offset points",
                        ha="left" if k == 2 else "center", fontsize=6.5, color=color)
    ax.axhline(1, color=INK, lw=0.9, ls="--", zorder=2)
    ax.set_yscale("log")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo / 1.15, hi * 3)  # room for the legend
    ax.set_xticks(range(len(benches)), [label(b) for b in benches], rotation=35, ha="right")
    ax.set_xlim(-0.6, len(benches) - 0.4)
    ax.set_ylabel("STV(baseline) / STV(HBM)\n> 1: HBM wins")
    ax.grid(True, axis="y", color=GRID, lw=0.8)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    ax.set_title("STV ratios per circuit (shaded: T count needs the R = 360 cultivation grade)")
    fig.savefig(path)
    plt.close(fig)


def scaling(cells, benches, path):
    lines = [("best 2D-Cult", CULT, "#c4501b"), ("Planar-2D", ("D0-alt",), "#6b6a66"),
             ("best HBM", HBM, "#173f84"), ("best HBM-Cult", HBMC, "#0f6a48")]
    fams = sorted({circuit(b)[0] for b in benches}, key=lambda f: f != "Ising")
    fig, axes = plt.subplots(1, len(fams), figsize=(4.4 * len(fams), 3.5), sharey=True,
                             squeeze=False)
    for ax, fam in zip(axes[0], fams):
        bs = [b for b in benches if circuit(b)[0] == fam]
        for name, specs, color in lines:
            pts = [(circuit(b)[1], best(cells[b], specs)) for b in bs]
            pts = [(n, c) for n, c in pts if c]
            ax.plot([n for n, _ in pts], [stv(c) for _, c in pts], color=color, lw=1.4,
                    label=name, zorder=2)
            for n, c in pts:
                marker(ax, n, stv(c), color, misses(c))
        for b in bs:
            if grade(cells[b]) == 360:
                ax.axvline(circuit(b)[1], color=GRID, lw=6, zorder=0)
        ax.set_yscale("log")
        ax.set_xlabel("logical qubits N")
        ax.grid(True, color=GRID, lw=0.8)
        ax.set_title(fam)
    axes[0][0].set_ylabel("STV (qubits x rounds)")
    axes[0][0].legend(frameon=False, fontsize=8)
    fig.suptitle("Best STV per family (hollow: misses the error target; grey band: R = 360)",
                 x=0.01, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def sharing(cells, benches, path):
    panels = [("factories on top (HBM)", "D3-{}-fact"), ("cultivation on top (HBM-Cult)", "D3-{}")]
    cmap = plt.get_cmap("viridis")
    ns = [circuit(b)[1] for b in benches]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, (title, fmt) in zip(axes, panels):
        for b in benches:
            base = best(cells[b], CULT + ("D0-alt",))
            pts = [(k, cells[b].get(fmt.format(key))) for k, (_, key) in enumerate(SHARING)]
            pts = [(k, c) for k, c in pts if c]
            if not base or not pts:
                continue
            color = cmap((circuit(b)[1] - min(ns)) / max(1, max(ns) - min(ns)))
            ls = "-" if circuit(b)[0] == "Ising" else "--"
            ys = [stv(base) / stv(c) for _, c in pts]
            ax.plot([k for k, _ in pts], ys, color=color, lw=1.2, ls=ls, zorder=2)
            for (k, c), y in zip(pts, ys):
                marker(ax, k, y, color, misses(c), s=22)
        ax.axhline(1, color=INK, lw=0.9, ls="--")
        ax.set_yscale("log")
        ax.set_xticks(range(len(SHARING)), [s for s, _ in SHARING])
        ax.set_xlabel("sharing (data qubits per source)")
        ax.grid(True, color=GRID, lw=0.8)
        ax.set_title(title)
    axes[0].set_ylabel("STV(best 2D baseline) / STV(HBM)\n> 1: HBM wins")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(min(ns), max(ns)))
    fig.colorbar(sm, ax=axes, shrink=0.85, pad=0.01, label="N (solid Ising, dashed Heisenberg)")
    fig.savefig(path)
    plt.close(fig)


def space_parts(c, grades):
    """Qubits split into data tiles, other tiles and magic-state sources."""
    d = int(c["d_sim"])
    data = int(c["N"]) * 2 * d * d
    src = int(c["n_factories"]) * 22 * d * d  # HBM_FACTORY_QUBITS default (22d^2)
    if int(c["n_patches"]):
        src += int(c["n_patches"]) * grades[int(c["recharge_rounds"])][1]
    return data, num(c["Q"]) - data - src, src


def spacetime(cells, bench, grades, path):
    cs = cells[bench]
    specs = [s for _, s in COLS if s in cs][::-1]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 0.6 + 0.3 * len(specs)), sharey=True,
                                 gridspec_kw=dict(width_ratios=[1.1, 1]))
    y = np.arange(len(specs))
    parts = np.array([space_parts(cs[s], grades) for s in specs]) / 1e3
    left = np.zeros(len(specs))
    for k, (name, color) in enumerate([("data tiles", "#3b3a36"), ("other tiles", "#b9b5aa"),
                                       ("T sources", "#d9a521")]):
        a1.barh(y, parts[:, k], left=left, color=color, height=0.7, label=name)
        left += parts[:, k]
    a1.set_xlabel("physical qubits Q (thousands)")
    a1.set_yticks(y, [NAME[s] for s in specs])
    a1.legend(frameon=False, fontsize=8, loc="lower right")
    rounds = [num(cs[s]["rounds"]) for s in specs]
    ideal = [num(cs[s]["ideal_depth"]) * int(cs[s]["d_sim"]) for s in specs]
    a2.barh(y, rounds, color=[COLOR[s] for s in specs], height=0.7)
    a2.scatter(ideal, y, marker="|", s=160, color=INK, lw=1.5, zorder=3)
    a2.set_xscale("log")
    a2.set_xlim(min(ideal) / 1.6, max(rounds) * 9)
    a2.set_xlabel("rounds (steps x d), log")
    for k, s in enumerate(specs):
        a2.text(rounds[k] * 1.08, k, f"STV {stv(cs[s]):.2g}" + (" †" if misses(cs[s]) else ""),
                va="center", fontsize=7)
    for ax in (a1, a2):
        ax.grid(True, axis="x", color=GRID, lw=0.8)
        ax.tick_params(axis="y", length=0)
    n_t = num(next(iter(cs.values()))["n_t"])
    fig.suptitle(f"{label(bench)} (T = {n_t:,.0f}, cultivation R = {grade(cs)}): space and time "
                 f"per configuration (| no-stall floor = ideal depth x d; † misses the error target)", x=0.01, ha="left",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def tradeoff(cells, chosen, path):
    fig, axes = plt.subplots(1, len(chosen), figsize=(4.6 * len(chosen), 4), squeeze=False)
    for ax, b in zip(axes[0], chosen):
        cs = cells[b]
        qs = [num(c["Q"]) for c in cs.values()]
        rs = [num(c["rounds"]) for c in cs.values()]
        x = np.geomspace(min(qs) / 1.5, max(qs) * 1.5, 50)
        lo, hi = math.floor(math.log10(min(map(stv, cs.values())))), \
            math.ceil(math.log10(max(map(stv, cs.values()))))
        for e in np.arange(lo, hi + 0.01, 0.5):
            ax.plot(x, 10 ** e / x, color=GRID, lw=0.8, zorder=0)
        for s in [s for _, s in COLS if s in cs]:
            c = cs[s]
            marker(ax, num(c["Q"]), num(c["rounds"]), COLOR[s], misses(c), s=44,
                   label=NAME[s])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(min(qs) / 1.3, max(qs) * 1.6)
        ax.set_ylim(min(rs) / 1.6, max(rs) * 1.6)
        ax.set_xlabel("physical qubits Q")
        ax.set_title(f"{label(b)} (cultivation R = {grade(cs)})")
    axes[0][0].set_ylabel("rounds (steps x d)")
    axes[0][-1].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle("Space against time (grey: equal STV, half-decade apart; lower left wins; "
                 "hollow misses the error target)", x=0.01, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--out", default="figs", help="directory for the PNGs")
    ap.add_argument("--circuit", help="circuit for spacetime.png (default: the largest N)")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463",
                    help="as in analyze.py (for the patch qubits in spacetime.png)")
    args = ap.parse_args()

    cells, benches = load(args.csv)
    if not benches:
        raise SystemExit("no finished, feasible runs in " + args.csv)
    os.makedirs(args.out, exist_ok=True)
    largest = max(benches, key=lambda b: circuit(b)[1])
    chosen = []  # tradeoff: the largest circuit at each cultivation grade
    for g in sorted({grade(cells[b]) for b in benches}, key=str):
        chosen.append(max((b for b in benches if grade(cells[b]) == g),
                          key=lambda b: circuit(b)[1]))
    out = lambda name: os.path.join(args.out, name)  # noqa: E731
    heatmap(cells, benches, out("heatmap.png"))
    ratios(cells, benches, out("ratios.png"))
    scaling(cells, benches, out("scaling.png"))
    sharing(cells, benches, out("sharing.png"))
    spacetime(cells, args.circuit or largest, args.cult_grades, out("spacetime.png"))
    tradeoff(cells, chosen, out("tradeoff.png"))
    print("wrote", ", ".join(sorted(os.listdir(args.out))), "to", args.out)


if __name__ == "__main__":
    main()
