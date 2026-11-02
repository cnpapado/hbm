"""Paper figures for a revision campaign (analyze.py's CSV), sized for a two-column paper.

  python plot_results.py rev.csv --out figs/ [--circuit ising_n66] [--fmt pdf,png]

Single-column (3.35 in) unless noted; no titles (the caption carries them):
  ratios      P1, P1c, P2 per circuit and their geometric mean (> 1: HBM wins)
  heatmap     (two columns) every configuration's STV over the best on its circuit
  sharing     best 2D baseline's STV over HBM's, against the sharing ratio (geomean, range)
  spacetime   one circuit: qubits (data, other tiles, T sources) and rounds per configuration
  tradeoff    one circuit: qubits against rounds, with lines of equal STV
  scaling     each family's best STV against N, Ising and Heisenberg apart
Cells are those of stv_table.py (cultivation at its lowest-STV R). A run whose program error
breaks the target at the simulated d (meets_target False) is marked: a dagger, or a hollow
marker. At the larger d it needs, its STV would grow. Circuits marked * have more T gates than
the fast cultivation grade allows (R = 360). Fonts are embedded as TrueType (no Type 3).
"""

import argparse
import csv
import logging
import math
import os
import re
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from analyze import parse_grades  # noqa: E402
from stv_table import COLS, CULT, HBM, HBMC, cell, num  # noqa: E402

COL, FULL = 3.35, 7.0  # inches: one column, both columns
INK, MUTED, GRID = "#222222", "#6b6b6b", "#dddddd"
# Okabe-Ito hues per family (colour-blind safe), lighter with more sharing.
FAMILY = {"2D-Cult": "#D55E00", "Planar-2D": "#7a7a7a", "HBM": "#0072B2", "HBM-Cult": "#009E73"}
SHORT = {  # spec -> (family, short label)
    "D2-wide": ("2D-Cult", "2D-Cult"), "D2-tight": ("2D-Cult", "2D-Cult½"),
    "D0-alt": ("Planar-2D", "Planar-2D"),
    "D3-k1-fact": ("HBM", "Ded"), "D3-s2-fact": ("HBM", "S2"), "D3-s4-fact": ("HBM", "S4"),
    "D3-s8-fact": ("HBM", "S8"), "D3-s16-fact": ("HBM", "S16"),
    "D3-k1": ("HBM-Cult", "Ded"), "D3-s2": ("HBM-Cult", "S2"), "D3-s4": ("HBM-Cult", "S4"),
    "D3-s8": ("HBM-Cult", "S8"), "D3-s16": ("HBM-Cult", "S16"),
}
SHARING = ["k1", "s2", "s4", "s8", "s16"]
SHARE_LABEL = ["Ded", "S2", "S4", "S8", "S16"]

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.minor.size": 1.5,
    "ytick.minor.size": 1.5, "lines.linewidth": 1.0, "lines.markersize": 3.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "legend.frameon": False, "legend.handlelength": 1.3, "legend.handletextpad": 0.4,
    "legend.columnspacing": 0.9, "legend.borderaxespad": 0.2, "hatch.linewidth": 0.5,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def shade(hex_color, k, n):
    """The k-th of n shades of a colour, from full (k = 0) towards white."""
    rgb = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    return tuple(rgb + (1 - rgb) * 0.62 * k / max(1, n - 1))


def color(spec):
    fam, short = SHORT[spec]
    if fam in ("HBM", "HBM-Cult"):
        return shade(FAMILY[fam], SHARE_LABEL.index(short), 5)
    return shade(FAMILY[fam], 1, 2) if spec == "D2-tight" else FAMILY[fam]


def circuit(bench):
    """'ising_n10' -> ('Ising', 10); 'heisenberg_qedc_n16' -> ('Heisenberg', 16)."""
    m = re.match(r"([a-z]+)\D*?(\d+)$", bench)
    return (m.group(1).capitalize(), int(m.group(2))) if m else (bench, 0)


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
    got = [cs[s] for s in specs if s in cs]
    return min(got, key=stv) if got else None


def grade(cs):
    """The recharge rounds of a circuit's cultivation runs (60 or 360), or None."""
    for s in CULT + HBMC:
        if s in cs:
            return int(cs[s]["recharge_rounds"])
    return None


def label(bench, cs=None):
    fam, n = circuit(bench)
    star = "*" if cs is not None and grade(cs) == 360 else ""
    return f"{'Heis' if fam == 'Heisenberg' else fam}-{n}{star}"


def gmean(xs):
    xs = [x for x in xs if x and math.isfinite(x) and x > 0]
    return math.exp(sum(map(math.log, xs)) / len(xs)) if xs else math.nan


def times(v):
    return f"{v:.2f}×" if v < 10 else f"{v:.0f}×"


def mark(ax, x, y, col, miss, **kw):
    ax.scatter(x, y, s=kw.pop("s", 14), facecolor="white" if miss else col, edgecolor=col,
               linewidth=0.9, zorder=kw.pop("zorder", 3), **kw)


def plain_log(ax, axis="y"):
    """Log axis labelled 1, 2, 10, ... instead of 10^0."""
    a = getattr(ax, f"{axis}axis")
    a.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    a.set_minor_formatter(mticker.NullFormatter())


# --------------------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------------------

PAIRS = [  # key, legend, colour, hatch
    ("P1", "2D-Cult / HBM", FAMILY["HBM"], None),
    ("P1c", "2D-Cult / HBM-Cult", FAMILY["HBM-Cult"], "////"),
    ("P2", "Planar-2D / HBM", FAMILY["Planar-2D"], None),
]


def pair_values(cs):
    cult, hbm, hbmc, d0 = best(cs, CULT), best(cs, HBM), best(cs, HBMC), cs.get("D0-alt")
    return {"P1": stv(cult) / stv(hbm) if cult and hbm else None,
            "P1c": stv(cult) / stv(hbmc) if cult and hbmc else None,
            "P2": stv(d0) / stv(hbm) if d0 and hbm else None}


def ratios(cells, benches, path):
    vals = {b: pair_values(cells[b]) for b in benches}
    names = [label(b, cells[b]) for b in benches] + ["GMean"]
    fig, ax = plt.subplots(figsize=(COL, 1.55))
    w = 0.27
    for k, (key, legend, col, hatch) in enumerate(PAIRS):
        ys = [vals[b][key] for b in benches]
        ys.append(gmean(ys))
        xs = np.arange(len(ys)) + (k - 1) * w
        ax.bar(xs, [y or np.nan for y in ys], width=w, color="white" if hatch else col,
               edgecolor=col, hatch=hatch, linewidth=0.6,
               label=f"{key} {legend} ({ys[-1]:.2f}×)")
    ax.axhline(1, color=INK, lw=0.6, ls="--", zorder=1)
    ax.axvline(len(benches) - 0.5, color=MUTED, lw=0.5)
    ax.set_yscale("log")
    ax.set_ylim(0.6, 20)
    plain_log(ax)
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("STV ratio (higher:\nHBM better)")
    ax.grid(True, axis="y", which="major", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=2, fontsize=6)
    fig.savefig(path)
    plt.close(fig)


def heatmap(cells, benches, path):
    specs = [s for _, s in COLS if any(s in cells[b] for b in benches)]
    m = np.full((len(benches), len(specs)), np.nan)
    for i, b in enumerate(benches):
        lo = min(stv(c) for c in cells[b].values())
        for j, s in enumerate(specs):
            if s in cells[b]:
                m[i, j] = stv(cells[b][s]) / lo
    top = np.nanmax(m)
    fig, ax = plt.subplots(figsize=(FULL, 2.45))
    ax.imshow(m, cmap="YlOrRd", norm=LogNorm(1, top), aspect="auto")
    for i, b in enumerate(benches):
        for j, s in enumerate(specs):
            v = m[i, j]
            if np.isnan(v):
                continue
            dark = math.log(v) > 0.55 * math.log(top)
            text = (f"{v:.2f}" if v < 10 else f"{v:.0f}") + ("†" if misses(cells[b][s]) else "")
            ax.text(j, i, text, ha="center", va="center", fontsize=6,
                    color="white" if dark else INK, fontweight="bold" if v == 1 else None)
            if v == 1:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=INK, lw=1.2))
    groups = []  # [family, first column, last column]
    for j, s in enumerate(specs):
        fam = "2D baselines" if SHORT[s][0] in ("2D-Cult", "Planar-2D") else SHORT[s][0]
        if groups and groups[-1][0] == fam:
            groups[-1][2] = j
        else:
            groups.append([fam, j, j])
    names = {"HBM": "HBM (factories on top)", "HBM-Cult": "HBM-Cult (cultivation on top)"}
    for fam, a, z in groups:
        if a:
            ax.axvline(a - 0.5, color="white", lw=2.5)
        ax.annotate(names.get(fam, fam), ((a + z) / 2, -1.45), ha="center", va="bottom",
                    fontsize=7, annotation_clip=False)
        ax.plot([a - 0.42, z + 0.42], [-1.38, -1.38], color=INK, lw=0.6, clip_on=False)
    short2d = {"D2-wide": "Cult", "D2-tight": "Cult½", "D0-alt": "Planar"}
    for j, s in enumerate(specs):
        ax.annotate(short2d.get(s, SHORT[s][1]), (j, -0.62), ha="center", va="bottom",
                    fontsize=6.5, annotation_clip=False)
    ax.set_xticks([])
    ax.set_yticks(range(len(benches)),
                  [f"{label(b, cells[b])} ({num(next(iter(cells[b].values()))['n_t']):,.0f} T)"
                   for b in benches])
    ax.tick_params(length=0, pad=1.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(path)
    plt.close(fig)


def sharing(cells, benches, path):
    fig, ax = plt.subplots(figsize=(COL, 1.55))
    x = np.arange(len(SHARING))
    for fam, fmt in (("HBM", "D3-{}-fact"), ("HBM-Cult", "D3-{}")):
        per = []  # per sharing ratio: the ratio on each circuit
        for key in SHARING:
            rs = []
            for b in benches:
                base, c = best(cells[b], CULT + ("D0-alt",)), cells[b].get(fmt.format(key))
                if base and c:
                    rs.append(stv(base) / stv(c))
            per.append(rs)
        ax.fill_between(x, [min(r) for r in per], [max(r) for r in per], color=FAMILY[fam],
                        alpha=0.15, lw=0)
        ax.plot(x, [gmean(r) for r in per], color=FAMILY[fam], marker="o", ms=3,
                label=f"{fam} ({'factories' if fam == 'HBM' else 'cultivation'})")
    ax.axhline(1, color=INK, lw=0.6, ls="--")
    ax.set_yscale("log")
    plain_log(ax)
    ax.set_xticks(x, SHARE_LABEL)
    ax.set_xlabel("data qubits per T source")
    ax.set_ylabel("STV(best 2D) / STV(HBM)\n(higher: HBM better)")
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.legend(loc="lower left")
    fig.savefig(path)
    plt.close(fig)


def space_parts(c, grades):
    """Qubits split into data tiles, other tiles and T sources (factories at 22 d^2)."""
    d = int(c["d_sim"])
    data = int(c["N"]) * 2 * d * d
    src = int(c["n_factories"]) * 22 * d * d
    if int(c["n_patches"]):
        src += int(c["n_patches"]) * grades[int(c["recharge_rounds"])][1]
    return data, num(c["Q"]) - data - src, src


def rows_with_gaps(specs):
    """y positions, top to bottom, with a gap between 2D, HBM and HBM-Cult."""
    group = lambda s: SHORT[s][0] if SHORT[s][0].startswith("HBM") else "2D"  # noqa: E731
    ys, y = [], 0.0
    for k, s in enumerate(specs):
        if k and group(s) != group(specs[k - 1]):
            y += 0.6
        ys.append(y)
        y += 1
    return np.array(ys)


def row_label(s):
    fam, short = SHORT[s]
    return short if fam in ("2D-Cult", "Planar-2D") else f"{fam}-{short}"


def spacetime(cells, bench, grades, path):
    cs = cells[bench]
    specs = [s for _, s in COLS if s in cs]
    y = rows_with_gaps(specs)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(COL, 2.3), sharey=True,
                                 gridspec_kw=dict(wspace=0.2))
    parts = np.array([space_parts(cs[s], grades) for s in specs]) / 1e3
    left = np.zeros(len(specs))
    for k, (name, col) in enumerate([("data", "#333333"), ("other tiles", "#bdbdbd"),
                                     ("T sources", "#E69F00")]):
        a1.barh(y, parts[:, k], left=left, color=col, height=0.78, label=name, lw=0)
        left += parts[:, k]
    a1.set_xlabel("physical qubits (thousands)")
    a1.set_yticks(y, [row_label(s) for s in specs])
    a1.invert_yaxis()
    a1.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=3, fontsize=6,
              handlelength=0.9)
    rounds = np.array([num(cs[s]["rounds"]) for s in specs])
    ideal = num(cs[specs[0]]["ideal_depth"]) * int(cs[specs[0]]["d_sim"])
    a2.barh(y, rounds, color=[color(s) for s in specs], height=0.78, lw=0)
    a2.axvline(ideal, color=INK, lw=0.6, ls="--")
    lo = min(stv(cs[s]) for s in specs)
    for k, s in enumerate(specs):
        a2.text(rounds[k] * 1.2, y[k], times(stv(cs[s]) / lo) + ("†" if misses(cs[s]) else ""),
                va="center", fontsize=5.5)
    a2.set_xscale("log")
    a2.set_xlim(ideal / 1.5, rounds.max() * 7)
    a2.set_xlabel("rounds (log)")
    a2.text(1, 1.01, "STV / best", transform=a2.transAxes, ha="right", va="bottom",
            fontsize=6, color=MUTED)
    for ax in (a1, a2):
        ax.tick_params(axis="y", length=0)
        ax.grid(True, axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
    a2.spines["left"].set_visible(False)
    fig.savefig(path)
    plt.close(fig)


def tradeoff(cells, bench, path):
    cs = cells[bench]
    fig, ax = plt.subplots(figsize=(COL, 1.9))
    qs = [num(c["Q"]) for c in cs.values()]
    rs = [num(c["rounds"]) for c in cs.values()]
    x = np.geomspace(min(qs) / 1.6, max(qs) * 1.6, 50)
    for e in range(math.floor(math.log10(min(map(stv, cs.values())))) - 1,
                   math.ceil(math.log10(max(map(stv, cs.values())))) + 2):
        ax.plot(x, 10.0 ** e / x, color=GRID, lw=0.6, zorder=0)
    series = [("2D-Cult", list(CULT)), ("Planar-2D", ["D0-alt"]),
              ("HBM", [f"D3-{k}-fact" for k in SHARING]),
              ("HBM-Cult", [f"D3-{k}" for k in SHARING])]
    for fam, specs in series:
        specs = [s for s in specs if s in cs]
        if not specs:
            continue
        px = [num(cs[s]["Q"]) for s in specs]
        py = [num(cs[s]["rounds"]) for s in specs]
        ax.plot(px, py, color=FAMILY[fam], lw=0.8, zorder=2)
        for s, a, b in zip(specs, px, py):
            mark(ax, a, b, FAMILY[fam], misses(cs[s]), s=16)
        if fam in ("HBM", "HBM-Cult"):
            for s, a, b in ((specs[0], px[0], py[0]), (specs[-1], px[-1], py[-1])):
                ax.annotate(SHORT[s][1], (a, b), xytext=(4, -1), textcoords="offset points",
                            fontsize=5.5, color=FAMILY[fam], va="top")
        if fam == "2D-Cult":
            for s, a, b in zip(specs, px, py):
                ax.annotate("k½" if s == "D2-tight" else "k1", (a, b), xytext=(-4, 2),
                            textcoords="offset points", fontsize=5.5, color=FAMILY[fam],
                            ha="right")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(min(qs) / 1.3, max(qs) * 1.4)
    ax.set_ylim(min(rs) / 1.6, max(rs) * 1.6)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 1e3:g}k"))
    ax.xaxis.set_minor_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v / 1e3:g}k" if f"{v:.0f}"[0] in "25" else ""))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v / 1e3:g}k" if v >= 1e3 else f"{v:g}"))
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_xlabel("physical qubits")
    ax.set_ylabel("rounds")
    handles = [Line2D([], [], color=FAMILY[f], marker="o", ms=3, lw=0.8, label=f)
               for f, _ in series]
    handles.append(Line2D([], [], color=MUTED, marker="o", ms=3, mfc="white", lw=0,
                          label="misses target"))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=5,
              fontsize=6, handlelength=1.0, columnspacing=0.7)
    fig.savefig(path)
    plt.close(fig)


def scaling(cells, benches, path):
    lines = [("2D-Cult", CULT), ("Planar-2D", ("D0-alt",)), ("HBM", HBM), ("HBM-Cult", HBMC)]
    fams = sorted({circuit(b)[0] for b in benches}, key=lambda f: f != "Ising")
    fig, axes = plt.subplots(1, len(fams), figsize=(COL, 1.55), sharey=True, squeeze=False,
                             gridspec_kw=dict(wspace=0.12))
    for ax, fam in zip(axes[0], fams):
        bs = [b for b in benches if circuit(b)[0] == fam]
        for name, specs in lines:
            pts = [(circuit(b)[1], best(cells[b], specs)) for b in bs]
            pts = [(n, c) for n, c in pts if c]
            ax.plot([n for n, _ in pts], [stv(c) for _, c in pts], color=FAMILY[name],
                    label=name, zorder=2)
            for n, c in pts:
                mark(ax, n, stv(c), FAMILY[name], misses(c), s=10)
        ax.set_yscale("log")
        one_two_five = mticker.FuncFormatter(
            lambda v, _: f"{v / 1e9:g}" if f"{v:.1e}"[0] in "125" else "")
        ax.yaxis.set_major_formatter(one_two_five)
        ax.yaxis.set_minor_formatter(one_two_five)
        ax.set_xlabel(f"{fam}: logical qubits")
        ax.grid(True, axis="y", color=GRID, lw=0.5)
    axes[0][0].set_ylabel(r"STV ($10^9$ qubit-rounds)")
    axes[0][0].legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=4, fontsize=6)
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--out", default="figs", help="directory for the figures")
    ap.add_argument("--circuit", nargs="+",
                    help="circuits for spacetime and tradeoff (default: the largest at each R)")
    ap.add_argument("--fmt", default="pdf,png", help="comma-separated file types")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463",
                    help="as in analyze.py (for the patch qubits in spacetime)")
    args = ap.parse_args()

    cells, benches = load(args.csv)
    if not benches:
        raise SystemExit("no finished, feasible runs in " + args.csv)
    os.makedirs(args.out, exist_ok=True)
    chosen = args.circuit or [
        max((b for b in benches if grade(cells[b]) == g), key=lambda b: circuit(b)[1])
        for g in sorted({grade(cells[b]) for b in benches}, key=str)]
    written = []
    for ext in args.fmt.split(","):
        def out(name):
            written.append(f"{name}.{ext}")
            return os.path.join(args.out, f"{name}.{ext}")
        ratios(cells, benches, out("ratios"))
        heatmap(cells, benches, out("heatmap"))
        sharing(cells, benches, out("sharing"))
        scaling(cells, benches, out("scaling"))
        for b in chosen:
            tag = label(b).lower()
            spacetime(cells, b, args.cult_grades, out(f"spacetime_{tag}"))
            tradeoff(cells, b, out(f"tradeoff_{tag}"))
    print("wrote", ", ".join(written), "to", args.out)


if __name__ == "__main__":
    main()
