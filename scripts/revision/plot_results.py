"""Paper figures for a revision campaign (analyze.py's CSV), drawn at their printed size.

  python plot_results.py rev.csv --out figs/ [--circuit ising_n66 ...] [--fmt pdf,png]

ISCA style (IEEEtran: column 3.49 in, text 7.14 in): every text at 8 pt or more, axis labels
9 pt, no in-plot titles, legend in a frameless row above the axes or direct labels, colours
ordered by lightness plus hatching / markers so they survive grayscale, fonts embedded as
TrueType. Include each PDF at width=\\columnwidth (heatmap: \\textwidth) so nothing rescales.

  ratios        baseline STV / HBM STV per circuit and their geometric mean (> 1: HBM wins)
  heatmap       (two columns) every configuration's STV over the best on its circuit
  sharing       same-source 2D baseline's STV over HBM's against the sharing ratio
  spacetime_X   one circuit: qubits (data, other tiles, T sources) and rounds, per layout
  tradeoff_X    one circuit: qubits against rounds, with lines of equal STV
  scaling       each family's best STV against N, Ising and Heisenberg apart
  split         (v2) ratios_same's STV ratios split into qubit and round ratios
  split_s2      (v2) the same for HBM's Shared-2 layouts
  plane_cost    (v2) the planar baselines' timesteps over the circuit's ideal depth
  captions.md   a draft caption per figure: what it shows, no findings
Cells are those of stv_table.py (cultivation at its lowest-STV R). A run whose program error
breaks the target at the simulated d (meets_target False) is marked with a dagger or a hollow
marker: at the larger d it needs, its STV would grow. Circuits marked * have too many T gates
for the fast cultivation grade, so cultivation runs at R = 360.
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
from fit_d import patch_qubits, refit  # noqa: E402
from stv_table import COLS, CULT, HBM, HBMC, cell, num  # noqa: E402

COL, FULL = 3.45, 7.1  # inches: one column, both columns
INK, MUTED, GRID = "#1a1a1a", "#555555", "#d9d9d9"
# Fill colours ordered by lightness (grayscale-safe), the proposal darkest.
FILL = {"HBM": "#1B4F9C", "HBM-Cult": "#2CA27A", "2D-Cult": "#F0A33A", "Planar-2D": "#D4D4D4"}
LINE = dict(FILL, **{"Planar-2D": "#808080"})
HATCH = {"HBM": None, "HBM-Cult": "////", "2D-Cult": None, "Planar-2D": None}
STYLE = {  # line plots: marker, line style
    "HBM": ("o", "-"), "HBM-Cult": ("s", "--"), "2D-Cult": ("^", "-."), "Planar-2D": ("D", ":"),
}
SHORT = {  # spec -> (family, sharing label)
    "D2-wide": ("2D-Cult", ""), "D2-tight": ("2D-Cult", "½"), "D0-alt": ("Planar-2D", ""),
    "D3-k1-fact": ("HBM", "Ded"), "D3-s2-fact": ("HBM", "S2"), "D3-s4-fact": ("HBM", "S4"),
    "D3-s8-fact": ("HBM", "S8"), "D3-s16-fact": ("HBM", "S16"),
    "D3-k1": ("HBM-Cult", "Ded"), "D3-s2": ("HBM-Cult", "S2"), "D3-s4": ("HBM-Cult", "S4"),
    "D3-s8": ("HBM-Cult", "S8"), "D3-s16": ("HBM-Cult", "S16"),
}
SHARING = ["k1", "s2", "s4", "s8", "s16"]
SHARE_LABEL = ["Ded", "S2", "S4", "S8", "S16"]
SPACETIME_SPECS = ["D2-wide", "D0-alt", "D3-k1-fact", "D3-s4-fact", "D3-s16-fact", "D3-k1",
                   "D3-s4", "D3-s16"]

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.minor.size": 1.5,
    "ytick.minor.size": 1.5, "lines.linewidth": 1.1, "lines.markersize": 4,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "legend.frameon": False, "legend.handlelength": 1.5, "legend.handletextpad": 0.4,
    "legend.columnspacing": 1.0, "legend.borderaxespad": 0.2, "hatch.linewidth": 0.6,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def shade(hex_color, k, n):
    """The k-th of n shades of a colour, from full (k = 0) towards white."""
    rgb = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    return tuple(rgb + (1 - rgb) * 0.6 * k / max(1, n - 1))


def name(spec):
    fam, share = SHORT[spec]
    return fam + share if fam == "2D-Cult" else (f"{fam}-{share}" if share else fam)


def circuit(bench):
    """'ising_n10' -> ('Ising', 10); 'heisenberg_qedc_n16' -> ('Heisenberg', 16)."""
    m = re.match(r"([a-z]+)\D*?(\d+)$", bench)
    return (m.group(1).capitalize(), int(m.group(2))) if m else (bench, 0)


def read_rows(path, fit=None, grades=None):
    """analyze.py's rows; with fit = m, each run at its own d for vertical links at m * p."""
    rows = list(csv.DictReader(open(path)))
    return refit(rows, fit, grades) if fit else rows


def to_cells(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["bench"], r["spec"])].append(r)
    cells = defaultdict(dict)
    for (bench, spec), rows in groups.items():
        c = cell(rows)
        if isinstance(c, dict):
            cells[bench][spec] = c
    benches = sorted(cells, key=lambda b: (circuit(b)[0] != "Ising", circuit(b)))
    return cells, benches


def load(path, fit=None, grades=None):
    return to_cells(read_rows(path, fit, grades))


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


def d_sim(cells):
    """The code distance the runs were simulated at."""
    return int(next(iter(next(iter(cells.values())).values()))["d_sim"])


def fitted(cells):
    return any("d_sim_run" in c for cs in cells.values() for c in cs.values())


def d_note(cells):
    """How the code distance was chosen, for captions."""
    if not fitted(cells):
        return f"code distance d = {d_sim(cells)}"
    ds = sorted({int(c["d_sim"]) for cs in cells.values() for c in cs.values()})
    return (f"the smallest odd code distance that meets the program-error target, chosen "
            f"per run (d = {ds[0]}-{ds[-1]})")


def miss_note(cells, mark):
    """The caption note for runs that miss the target, or nothing when every run meets it."""
    if fitted(cells):
        return ""
    return f" {mark}: the run exceeds the program-error target at d = {d_sim(cells)}."


STAR = " *: the circuit's T count requires the slower cultivation grade (R = 360 rounds)."


def shares(cells):
    """[(key, label)] of the HBM sharing ratios present in the data (Ded first)."""
    return [(k, lab) for k, lab in zip(SHARING, SHARE_LABEL)
            if any(f"D3-{k}-fact" in cs or f"D3-{k}" in cs for cs in cells.values())]


def most_shared(cells):
    """The largest sharing ratio present, as a number (16 for S16)."""
    return int(shares(cells)[-1][1][1:])


def n_t(cs):
    return num(next(iter(cs.values()))["n_t"])


def gmean(xs):
    xs = [x for x in xs if x and math.isfinite(x) and x > 0]
    return math.exp(sum(map(math.log, xs)) / len(xs)) if xs else math.nan


def times(v):
    return f"{v:.2f}×" if v < 10 else f"{v:.0f}×"


def plain_log(ax, axis="y", scale=1.0, minor="25"):
    """Log axis labelled 0.5, 1, 2, ... (values / scale); minor labels on leading digits."""
    a = getattr(ax, f"{axis}axis")
    a.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / scale:g}"))
    a.set_minor_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v / scale:g}" if f"{v:.1e}"[0] in minor else ""))


def legend_above(ax, ncol, **kw):
    ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=ncol, **kw)


# --------------------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------------------

PAIRS = [  # key, legend, fill family
    ("P1", "HBM vs 2D-Cult", "HBM"),
    ("P1c", "HBM-Cult vs 2D-Cult", "HBM-Cult"),
    ("P2", "HBM vs Planar-2D", "Planar-2D"),
]


def pair_values(cs):
    cult, hbm, hbmc, d0 = best(cs, CULT), best(cs, HBM), best(cs, HBMC), cs.get("D0-alt")
    return {"P1": stv(cult) / stv(hbm) if cult and hbm else None,
            "P1c": stv(cult) / stv(hbmc) if cult and hbmc else None,
            "P2": stv(d0) / stv(hbm) if d0 and hbm else None}


def ratios(cells, benches, path):
    vals = {b: pair_values(cells[b]) for b in benches}
    names = [label(b, cells[b]) for b in benches] + ["GMean"]
    fig, ax = plt.subplots(figsize=(COL, 1.45))
    w = 0.27
    gm = {}
    for k, (key, legend, fam) in enumerate(PAIRS):
        ys = [vals[b][key] for b in benches]
        gm[key] = gmean(ys)
        ys.append(gm[key])
        ax.bar(np.arange(len(ys)) + (k - 1) * w, [y or np.nan for y in ys], width=w,
               color=FILL[fam], hatch=HATCH[fam], edgecolor=INK, linewidth=0.4, label=legend)
    ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=1)
    ax.axvline(len(benches) - 0.5, color=INK, lw=0.6, ls=":")
    ax.set_yscale("log")
    ax.set_ylim(0.6, 20)
    plain_log(ax, minor="25")
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("STV ratio")
    ax.grid(True, axis="y", which="major", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    legend_above(ax, 2)
    fig.savefig(path)
    plt.close(fig)
    return ("Space-time volume (STV) of each baseline divided by that of HBM, per circuit and "
            "as the geometric mean (GMean), with each side at its best layout: HBM (factories "
            "on top) against 2D cultivation (2D-Cult), HBM-Cult (cultivation on top) against "
            "2D-Cult, and HBM against the planar factory layout (Planar-2D). Above the dashed "
            f"line (1), HBM has the lower STV; log scale. All runs at {d_note(cells)}." + STAR)


def heatmap(cells, benches, path):
    specs = [s for _, s in COLS if any(s in cells[b] for b in benches)]
    m = np.full((len(benches), len(specs)), np.nan)
    for i, b in enumerate(benches):
        lo = min(stv(c) for c in cells[b].values())
        for j, s in enumerate(specs):
            if s in cells[b]:
                m[i, j] = stv(cells[b][s]) / lo
    top = np.nanmax(m)
    fig, ax = plt.subplots(figsize=(FULL, 2.6))
    ax.imshow(m, cmap="YlOrRd", norm=LogNorm(1, top), aspect="auto")
    for i, b in enumerate(benches):
        for j, s in enumerate(specs):
            v = m[i, j]
            if np.isnan(v):
                continue
            dark = math.log(v) > 0.55 * math.log(top)
            text = (f"{v:.2f}" if v < 10 else f"{v:.0f}") + ("†" if misses(cells[b][s]) else "")
            ax.text(j, i, text, ha="center", va="center", fontsize=8,
                    color="white" if dark else INK, fontweight="bold" if v == 1 else None)
            if v == 1:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=INK, lw=1.3))
    groups = []  # [family, first column, last column]
    for j, s in enumerate(specs):
        fam = "2D baselines" if SHORT[s][0] in ("2D-Cult", "Planar-2D") else SHORT[s][0]
        if groups and groups[-1][0] == fam:
            groups[-1][2] = j
        else:
            groups.append([fam, j, j])
    heads = {"HBM": "HBM (factories on top)", "HBM-Cult": "HBM-Cult (cultivation on top)"}
    for fam, a, z in groups:
        if a:
            ax.axvline(a - 0.5, color="white", lw=2.5)
        ax.annotate(heads.get(fam, fam), ((a + z) / 2, -1.5), ha="center", va="bottom",
                    fontsize=9, annotation_clip=False)
        ax.plot([a - 0.42, z + 0.42], [-1.42, -1.42], color=INK, lw=0.6, clip_on=False)
    short2d = {"D2-wide": "Cult", "D2-tight": "Cult½", "D0-alt": "Planar"}
    for j, s in enumerate(specs):
        ax.annotate(short2d.get(s, SHORT[s][1]), (j, -0.62), ha="center", va="bottom",
                    fontsize=8, annotation_clip=False)
    ax.set_xticks([])
    ax.set_yticks(range(len(benches)),
                  [f"{label(b, cells[b])} ({n_t(cells[b]):,.0f} T)" for b in benches])
    ax.tick_params(length=0, pad=1.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(path)
    plt.close(fig)
    return ("STV of every configuration (columns) on every circuit (rows), divided by the "
            "lowest STV on that circuit; the boxed cell (1.00) is the circuit's best "
            "configuration. Columns: the 2D baselines (2D-Cult with one or half a cultivation "
            "patch per data qubit, Planar-2D), HBM with factories on top and HBM-Cult with "
            "cultivation patches on top, each with one source per data qubit (Ded) or one "
            f"source shared by 2 to {most_shared(cells)} data qubits (S2-S{most_shared(cells)}). "
            "Row labels give the circuit's T "
            f"count. All runs at {d_note(cells)}." + miss_note(cells, "†") + STAR)


def sharing(cells, benches, path):
    fig, ax = plt.subplots(figsize=(COL, 1.5))
    keys = shares(cells)
    x = np.arange(len(keys))
    # Each HBM source type against the 2D layout with the same source type.
    lines = [("HBM", "D3-{}-fact", ("D0-alt",), "Planar-2D / HBM (factories)"),
             ("HBM-Cult", "D3-{}", ("D2-wide",), "2D-Cult / HBM-Cult (cultivation)")]
    for fam, fmt, base_specs, legend in lines:
        per = []  # per sharing ratio: the ratio on each circuit
        for key, _ in keys:
            rs = []
            for b in benches:
                base, c = best(cells[b], base_specs), cells[b].get(fmt.format(key))
                if base and c:
                    rs.append(stv(base) / stv(c))
            per.append(rs)
        mk, ls = STYLE[fam]
        ax.fill_between(x, [min(r) for r in per], [max(r) for r in per], color=LINE[fam],
                        alpha=0.15, lw=0)
        ax.plot(x, [gmean(r) for r in per], color=LINE[fam], marker=mk, ls=ls, label=legend)
    ax.axhline(1, color=INK, lw=0.7, ls="--")
    ax.set_yscale("log")
    plain_log(ax, minor="")
    ax.set_xticks(x, [lab for _, lab in keys])
    ax.set_xlabel("data qubits per T source")
    ax.set_ylabel("STV ratio")
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.legend(loc="lower left")
    fig.savefig(path)
    plt.close(fig)
    return ("STV of a 2D baseline divided by that of HBM with the same kind of T source, "
            "against HBM's sharing ratio (Ded: one T source per data qubit; "
            f"S2-S{most_shared(cells)}: one source per 2 to {most_shared(cells)} data qubits): "
            "Planar-2D over HBM, both with factories "
            "(solid), and 2D-Cult (one patch per data qubit) over HBM-Cult, both with "
            "cultivation patches (dashed). Lines: geometric mean over the circuits; bands: "
            "range. The two lines use different baselines, so their heights are not comparable "
            "with each other. Above the dashed line (1), HBM has the lower STV; log scale.")


SHARE_MARK = {"k1": "o", "s2": "s", "s4": "^", "s8": "D", "s16": "v"}


def source_grid(cells, benches, path, pairs):
    """One panel per circuit: STV ratio against the T-source count ratio, a marker per
    sharing ratio. pairs: (family, HBM spec format, baseline spec, HBM count column,
    baseline count column, legend)."""
    ncol = 6
    nrow = math.ceil((len(benches) + 1) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(FULL, 1.2 * nrow + 0.25), sharex=True,
                             sharey=True, squeeze=False,
                             gridspec_kw=dict(wspace=0.1, hspace=0.38))
    xs, ys = [], []
    for ax, b in zip(axes.flat, benches):
        cs = cells[b]
        for fam, fmt, base, count, base_count, _ in pairs:
            if base not in cs:
                continue
            n0 = int(cs[base][base_count])
            pts = sorted((int(cs[fmt.format(k)][count]) / n0,
                          stv(cs[base]) / stv(cs[fmt.format(k)]), k)
                         for k in SHARING if fmt.format(k) in cs)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=LINE[fam],
                    ls=STYLE[fam][1], lw=0.9, zorder=2)
            for x, y, k in pts:
                ax.scatter(x, y, s=18, marker=SHARE_MARK[k], color=LINE[fam], edgecolor=INK,
                           lw=0.3, zorder=3)
                xs.append(x)
                ys.append(y)
        ax.axhline(1, color=INK, lw=0.6, ls="--")
        ax.axvline(1, color=INK, lw=0.6, ls=":")
        ax.set_title(label(b, cs), fontsize=8, pad=2)
        ax.grid(True, color=GRID, lw=0.4)
        ax.set_axisbelow(True)
    ax0 = axes.flat[0]
    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlim(min(0.03, min(xs) / 1.5), max(3, max(xs) * 1.5))
    ax0.set_ylim(min(0.5, min(ys) / 1.6), max(2, max(ys) * 1.6))
    plain_log(ax0, "x", minor="")
    plain_log(ax0, "y", minor="")
    for ax in axes.flat[len(benches):]:
        ax.axis("off")
    key = axes.flat[-1]
    handles = [Line2D([], [], color=LINE[fam], ls=STYLE[fam][1], lw=1.1, label=name)
               for fam, _, _, _, _, name in pairs]
    handles += [Line2D([], [], ls="", marker=SHARE_MARK[k], ms=4.5, color="#9a9a9a",
                       mec=INK, mew=0.3, label=lab) for k, lab in shares(cells)]
    key.legend(handles=handles, loc="center", fontsize=8, handlelength=1.8,
               borderaxespad=0)
    fig.supxlabel("T sources in HBM / T sources in the 2D baseline", fontsize=9, y=-0.05)
    fig.supylabel("STV ratio", fontsize=9, x=0.06)
    fig.savefig(path)
    plt.close(fig)


def sources(cells, benches, path):
    source_grid(cells, benches, path, [
        ("HBM", "D3-{}-fact", "D0-alt", "n_factories", "n_factories", "factories"),
        ("HBM-Cult", "D3-{}", "D2-wide", "n_patches", "n_patches", "cultivation")])
    return ("STV of a 2D baseline divided by that of HBM with the same kind of T source, "
            "against the number of T sources in HBM over that in the baseline, one panel per "
            "circuit: Planar-2D against HBM, both with factories (solid), and 2D-Cult (one "
            "cultivation patch per data qubit) against HBM-Cult, both with cultivation patches "
            "(dashed). Markers give HBM's layout, from one source per data qubit (Ded) to one "
            f"per {most_shared(cells)} (S{most_shared(cells)}). Above the dashed line (1), HBM "
            "has the lower STV; on the dotted line both use the same number of sources; "
            "log-log. The two lines use different baselines, so their heights are not "
            "comparable with each other. All runs at "
            f"{d_note(cells)}." + STAR)


def sources_vs_2dcult(cells, benches, path):
    source_grid(cells, benches, path, [
        ("HBM", "D3-{}-fact", "D2-wide", "n_factories", "n_patches", "HBM (factories)")])
    return ("STV of 2D-Cult (one cultivation patch per data qubit) divided by that of HBM "
            "with factories on top, against the number of factories in HBM over the number of "
            "cultivation patches in 2D-Cult, one panel per circuit. The two sides use "
            "different T sources: factories are always ready, while a cultivation patch "
            "recharges after each T state. Markers give HBM's layout, from one factory per "
            f"data qubit (Ded) to one per {most_shared(cells)} (S{most_shared(cells)}). Above "
            "the dashed line (1), HBM has the lower STV; on the dotted line both use the same "
            f"number of T sources; log-log. All runs at {d_note(cells)}." + STAR)


def space_parts(c, grades):
    """Qubits split into data tiles, other tiles and T sources (factories at 22 d^2)."""
    d = int(c["d_sim"])
    data = int(c["N"]) * 2 * d * d
    d_fact = int(c.get("d_sim_run") or d)  # factories keep their simulated size (fit_d.py)
    src = int(c["n_factories"]) * 22 * d_fact * d_fact
    if int(c["n_patches"]):
        src += int(c["n_patches"]) * patch_qubits(grades[int(c["recharge_rounds"])][1], d)
    return data, num(c["Q"]) - data - src, src


def rows_with_gaps(specs):
    """y positions, top to bottom, with a gap between 2D, HBM and HBM-Cult."""
    group = lambda s: SHORT[s][0] if SHORT[s][0].startswith("HBM") else "2D"  # noqa: E731
    ys, y = [], 0.0
    for k, s in enumerate(specs):
        if k and group(s) != group(specs[k - 1]):
            y += 0.5
        ys.append(y)
        y += 1
    return np.array(ys)


def spacetime(cells, bench, grades, path):
    cs = cells[bench]
    top = shares(cells)[-1][0]
    specs = [s.replace("s16", top) for s in SPACETIME_SPECS]
    specs = [s for i, s in enumerate(specs) if s in cs and s not in specs[:i]]
    y = rows_with_gaps(specs)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(COL - 0.1, 1.95), sharey=True,
                                 gridspec_kw=dict(wspace=0.22))
    parts = np.array([space_parts(cs[s], grades) for s in specs]) / 1e3
    left = np.zeros(len(specs))
    for k, (part, col, hatch) in enumerate([("data", "#1a1a1a", None),
                                            ("other tiles", "#d4d4d4", None),
                                            ("T sources", "#9B72B0", "....")]):
        a1.barh(y, parts[:, k], left=left, color=col, hatch=hatch, edgecolor=INK, lw=0.4,
                height=0.75, label=part)
        left += parts[:, k]
    a1.set_xlabel("qubits (thousands)")
    a1.set_yticks(y, [name(s) for s in specs])
    a1.invert_yaxis()
    legend_above(a1, 3, handlelength=1.0, columnspacing=0.8)
    rounds = np.array([num(cs[s]["rounds"]) for s in specs])
    ds = [int(cs[s]["d_sim"]) for s in specs]
    ideals = np.array([num(cs[s]["ideal_depth"]) * d for s, d in zip(specs, ds)])
    ideal = ideals.min()
    fills = [shade(FILL[SHORT[s][0]], SHARE_LABEL.index(SHORT[s][1]), 5)
             if SHORT[s][1] in SHARE_LABEL else FILL[SHORT[s][0]] for s in specs]
    a2.barh(y, rounds, color=fills, hatch=[HATCH[SHORT[s][0]] for s in specs], edgecolor=INK,
            lw=0.4, height=0.75)
    if len(set(ds)) == 1:
        a2.axvline(ideal, color=INK, lw=0.7, ls="--")
    else:  # the stall-free time depends on each run's d
        a2.vlines(ideals, y - 0.5, y + 0.5, color=INK, lw=0.8, ls=(0, (2, 1)))
    lo = min(stv(cs[s]) for s in cs)
    for k, s in enumerate(specs):
        text = times(stv(cs[s]) / lo) + ("†" if misses(cs[s]) else "")
        if fitted(cells):
            text += f" d{ds[k]}"
        a2.text(rounds[k] * 1.25, y[k], text, va="center", fontsize=8)
    a2.set_xscale("log")
    a2.set_xlim(ideal / 1.6, rounds.max() * (16 if fitted(cells) else 9))
    a2.xaxis.set_major_locator(mticker.LogLocator(numticks=10))
    plain_log(a2, "x", scale=1e3, minor="")
    a2.set_xlabel("rounds (thousands)")
    a2.text(1, 1.02, "STV", transform=a2.transAxes, ha="right", va="bottom", fontsize=8)
    for ax in (a1, a2):
        ax.tick_params(axis="y", length=0)
        ax.grid(True, axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
    a2.spines["left"].set_visible(False)
    fig.savefig(path)
    plt.close(fig)
    return (f"Space and time of representative configurations on {label(bench)}. Left: physical "
            "qubits, split into data tiles, other tiles (routing and unused) and T-state "
            "sources (factories or cultivation patches). Right: runtime in rounds (log scale); "
            "the dashed line is the stall-free runtime (ideal depth × d). Labels: the "
            "configuration's STV relative to the lowest on this circuit"
            + (" and its code distance" if fitted(cells) else "") + "."
            + miss_note(cells, "†"))


TRADEOFF_LABEL = {  # spec -> (text, offset in points, ha, va)
    "D2-wide": ("2D-Cult", (0, 5), "center", "bottom"),
    "D2-tight": ("2D-Cult½", (0, 5), "center", "bottom"),
    "D0-alt": ("Planar-2D", (-6, -2), "right", "top"),
    "D3-k1-fact": ("HBM-Ded", (6, -2), "left", "top"),
    "D3-k1": ("HBM-Cult-Ded", (0, -6), "center", "top"),
}


def tradeoff(cells, bench, path):
    cs = cells[bench]
    key, lab = shares(cells)[-1]
    labels = dict(TRADEOFF_LABEL, **{f"D3-{key}-fact": (f"HBM-{lab}", (6, 0), "left", "center"),
                                     f"D3-{key}": (f"HBM-Cult-{lab}", (6, 0), "left", "center")})
    fig, ax = plt.subplots(figsize=(COL, 1.9))
    qs = [num(c["Q"]) for c in cs.values()]
    rs = [num(c["rounds"]) for c in cs.values()]
    x = np.geomspace(min(qs) / 2, max(qs) * 2, 50)
    for e in range(math.floor(math.log10(min(map(stv, cs.values())))) - 1,
                   math.ceil(math.log10(max(map(stv, cs.values())))) + 2):
        ax.plot(x, 10.0 ** e / x, color=GRID, lw=0.6, zorder=0)
    series = [("2D-Cult", list(CULT)), ("Planar-2D", ["D0-alt"]),
              ("HBM", [f"D3-{k}-fact" for k in SHARING]),
              ("HBM-Cult", [f"D3-{k}" for k in SHARING])]
    for fam, specs in series:
        specs = [s for s in specs if s in cs]
        mk, ls = STYLE[fam]
        px = [num(cs[s]["Q"]) for s in specs]
        py = [num(cs[s]["rounds"]) for s in specs]
        ax.plot(px, py, color=LINE[fam], ls=ls, lw=0.9, zorder=2)
        for s, a, b in zip(specs, px, py):
            ax.scatter(a, b, s=20, marker=mk, facecolor="white" if misses(cs[s]) else LINE[fam],
                       edgecolor=LINE[fam], linewidth=1.0, zorder=3)
            if s in labels:
                text, off, ha, va = labels[s]
                ax.annotate(text, (a, b), xytext=off, textcoords="offset points", ha=ha, va=va,
                            fontsize=8, color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(min(qs) / 1.5, max(qs) * 2.2)
    ax.set_ylim(min(rs) / 2.2, max(rs) * 1.8)
    plain_log(ax, "x", scale=1e3, minor="25")
    plain_log(ax, "y", scale=1e3, minor="")
    ax.set_xlabel("qubits (thousands)")
    ax.set_ylabel("rounds (thousands)")
    fig.savefig(path)
    plt.close(fig)
    return (f"Physical qubits against runtime in rounds for every configuration on "
            f"{label(bench)} (log-log). Lines join the layouts of a family (2D-Cult: one and "
            f"half a cultivation patch per data qubit; HBM and HBM-Cult: Ded to S{most_shared(cells)}). Grey "
            "lines join points of equal STV, ten times apart; points further to the lower "
            f"left have lower STV. All runs at {d_note(cells)}." + miss_note(cells, "Hollow"))


def scaling(cells, benches, path):
    lines = [("2D-Cult", CULT), ("Planar-2D", ("D0-alt",)), ("HBM", HBM), ("HBM-Cult", HBMC)]
    fams = sorted({circuit(b)[0] for b in benches}, key=lambda f: f != "Ising")
    fig, axes = plt.subplots(1, len(fams), figsize=(COL, 1.5), sharey=True, squeeze=False,
                             gridspec_kw=dict(wspace=0.12))
    for ax, fam in zip(axes[0], fams):
        bs = [b for b in benches if circuit(b)[0] == fam]
        for line, specs in lines:
            pts = [(circuit(b)[1], best(cells[b], specs)) for b in bs]
            pts = [(n, c) for n, c in pts if c]
            mk, ls = STYLE[line]
            ax.plot([n for n, _ in pts], [stv(c) for _, c in pts], color=LINE[line], ls=ls,
                    label=line, zorder=2)
            for n, c in pts:
                ax.scatter(n, stv(c), s=16, marker=mk, facecolor="white" if misses(c)
                           else LINE[line], edgecolor=LINE[line], linewidth=1.0, zorder=3)
        ax.set_yscale("log")
        plain_log(ax, scale=1e9, minor="25")
        ax.set_xlabel(f"{fam} qubits")
        ax.grid(True, axis="y", color=GRID, lw=0.5)
    axes[0][0].set_ylabel("STV (billions)")
    legend_above(axes[0][0], 4, handlelength=2.0, columnspacing=0.8)
    fig.savefig(path)
    plt.close(fig)
    return ("Lowest STV of each family (2D-Cult, Planar-2D, HBM, HBM-Cult) against the "
            "number of logical qubits, for the Ising (left) and Heisenberg (right) circuits; "
            f"log scale. All runs at {d_note(cells)}." + miss_note(cells, "Hollow"))


# --------------------------------------------------------------------------------------
# v2: like-for-like at fixed layouts
# --------------------------------------------------------------------------------------

SAME = [  # key, legend, baseline spec, HBM spec, fill family (fixed layouts, same T source)
    ("fact", "factories: Planar-2D / HBM-Ded", "D0-alt", "D3-k1-fact", "HBM"),
    ("cult", "cultivation: 2D-Cult / HBM-Cult-Ded", "D2-wide", "D3-k1", "HBM-Cult"),
]


def same_ratio(cs, base, hbm):
    return stv(cs[base]) / stv(cs[hbm]) if base in cs and hbm in cs else None


def ratios_same(cells, benches, path):
    names = [label(b, cells[b]) for b in benches] + ["GMean"]
    fig, ax = plt.subplots(figsize=(COL, 1.45))
    w = 0.38
    for k, (_, legend, base, hbm, fam) in enumerate(SAME):
        ys = [same_ratio(cells[b], base, hbm) for b in benches]
        ys.append(gmean(ys))
        ax.bar(np.arange(len(ys)) + (k - 0.5) * w, [y or np.nan for y in ys], width=w,
               color=FILL[fam], hatch=HATCH[fam], edgecolor=INK, linewidth=0.4, label=legend)
    ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=1)
    ax.axvline(len(benches) - 0.5, color=INK, lw=0.6, ls=":")
    ax.set_ylim(0, None)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("STV ratio")
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    legend_above(ax, 1)
    fig.savefig(path)
    plt.close(fig)
    return ("STV of a 2D baseline divided by that of HBM with the same kind of T source and "
            "a layout fixed for all circuits, per circuit and as the geometric mean (GMean): "
            "Planar-2D against HBM-Ded, both with factories, and 2D-Cult (one cultivation "
            "patch per data qubit) against HBM-Cult-Ded, both with cultivation patches. Ded: "
            "one T source per data qubit. Above the dashed line (1), HBM has the lower STV. All "
            f"runs at {d_note(cells)}." + STAR)


def split(cells, benches, path, knob="k1", curve_label=(0.81, 1.25),
          place=(("Ising-26", "left"),)):
    """The like-for-like STV ratios of ratios_same, split into qubits (x) and rounds (y), for
    HBM's layout `knob` (k1: Ded, s2: S2, ...) against the fixed 2D baselines. `place` moves
    labels ("left" or "below-left" of their marker) clear of the curve and of each other."""
    pairs = [("D0-alt", f"D3-{knob}-fact", "HBM"), ("D2-wide", f"D3-{knob}", "HBM-Cult")]
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    xs_all, ys_all = [], []
    for base, hbm, fam in pairs:
        pts = [(num(cells[b][base]["Q"]) / num(cells[b][hbm]["Q"]),
                num(cells[b][base]["rounds"]) / num(cells[b][hbm]["rounds"]), b)
               for b in benches if base in cells[b] and hbm in cells[b]]
        marker = STYLE[fam][0]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=18, marker=marker,
                   facecolor=FILL[fam], edgecolor=INK, linewidth=0.4, zorder=3,
                   label=f"{name(base)} / {name(hbm)}")
        xs_all += [p[0] for p in pts]
        ys_all += [p[1] for p in pts]
        groups = []  # points that coincide get one label; a narrow column gets one too
        if len(pts) > 2 and max(p[0] for p in pts) - min(p[0] for p in pts) < 0.05:
            groups.append(list(pts))
            pts = []
        for x, y, b in pts:
            for g in groups:
                if abs(g[0][0] - x) < 0.03 and abs(g[0][1] - y) < 0.04:
                    g.append((x, y, b))
                    break
            else:
                groups.append([(x, y, b)])
        for g in groups:
            x = (max if len(g) > 2 else min)(p[0] for p in g)  # a column: right of it
            y = min(p[1] for p in g)
            ns = [circuit(p[2])[1] for p in g]
            text = (label(g[0][2], cells[g[0][2]]) if len(g) == 1 else
                    ", ".join(label(p[2], cells[p[2]]) for p in g) if len(g) == 2 else
                    f"N ≤ {max(ns)}" if max(ns) <= 16 else f"{len(g)} circuits")
            where = dict(place).get(text, "")
            below = (fam == "HBM" and len(g) > 2) or where == "below-left"
            on_left = where in ("left", "below-left")
            ax.annotate(text, (x, y), xytext=(-4 if on_left else 4, -10 if below else 3),
                        textcoords="offset points", fontsize=8,
                        ha="right" if on_left else "left", va="bottom", color=MUTED)
    lo, hi = min(xs_all + [1]) - 0.08, max(xs_all) + 0.25
    xx = np.linspace(lo, hi, 200)
    ax.plot(xx, 1 / xx, color=INK, lw=0.7, ls="--", zorder=1)
    ax.text(curve_label[0], curve_label[1], "equal STV", fontsize=8, ha="left", va="center",
            color=INK)
    ax.axvline(1, color=GRID, lw=0.6, zorder=0)
    ax.axhline(1, color=GRID, lw=0.6, zorder=0)
    ax.set_xlim(lo, hi)
    ax.set_ylim(min(ys_all + [1]) - 0.08, max(ys_all) + 0.1)
    ax.set_xlabel("Qubit ratio (2D / HBM)")
    ax.set_ylabel("Round ratio (2D / HBM)")
    legend_above(ax, 2)
    fig.savefig(path)
    plt.close(fig)
    hbm, cult = name(pairs[0][1]), name(pairs[1][1])
    what = ("The STV ratios of Fig. ratios_same split into their two factors" if knob == "k1"
            else f"As Fig. split, for HBM's {SHARE_LABEL[SHARING.index(knob)]} layout")
    return (f"{what}: physical qubits (x) and rounds (y; timesteps × code distance) of the 2D "
            f"baseline divided by those of HBM, one marker per circuit. Circles: Planar-2D over "
            f"{hbm} (factories); squares: 2D-Cult (one cultivation patch per data qubit) over "
            f"{cult} (cultivation). Beyond 1 on an axis, HBM uses fewer qubits or rounds; "
            "above the dashed curve (x·y = 1), HBM has the lower STV. Markers that coincide "
            f"share one label. All runs at {d_note(cells)}." + STAR)


PLANE = [("D0-alt", "HBM"), ("D2-wide", "HBM-Cult")]  # baseline spec, colour of its kind


def plane_cost(cells, benches, path):
    """What the planar baselines pay in time for keeping their magic-state resources in the
    data plane: per circuit, timesteps over the circuit's ideal depth (one run each), one
    panel per baseline on its own linear scale."""
    names = [label(b, cells[b]) for b in benches]
    fig, axes = plt.subplots(2, 1, figsize=(COL, 2.35), sharex=True,
                             gridspec_kw=dict(hspace=0.35))
    x = np.arange(len(benches))
    for ax, (spec, fam), (top, step), tag in zip(axes, PLANE, ((2, 0.5), (30, 10)),
                                                 ("(a) Factories: Planar-2D",
                                                  "(b) Cultivation: 2D-Cult")):
        ratio = [num(cells[b][spec]["steps"]) / num(cells[b][spec]["ideal_depth"])
                 if spec in cells[b] else math.nan for b in benches]
        ax.bar(x, ratio, width=0.6, color=FILL[fam], edgecolor=INK, linewidth=0.3)
        ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=3)
        ax.set_ylim(0, top)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(step))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_ylabel("Timesteps / ideal")
        ax.text(0.0, 1.03, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    axes[-1].set_xticks(x, names, rotation=45, ha="right", rotation_mode="anchor")
    axes[-1].set_xlim(-0.6, len(benches) - 0.4)
    axes[-1].tick_params(axis="x", length=0)
    fig.savefig(path)
    plt.close(fig)
    ds = sorted({int(cells[b][s]["d_sim_run"] if "d_sim_run" in cells[b][s] else
                     cells[b][s]["d_sim"]) for b in benches for s, _ in PLANE if s in cells[b]})
    return ("Timesteps of the two planar baselines divided by the circuit's ideal depth (its "
            "critical path at one timestep per gate), one run per circuit: (a) Planar-2D, with "
            "factory ports on a ring around the data region, and (b) 2D-Cult, with one "
            "cultivation patch beside each data qubit. Each panel has its own linear scale; "
            "on the dashed line (1), the circuit runs at its ideal depth. Timesteps as "
            f"simulated at d = {ds[0]}." + STAR)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--set", choices=["v1", "v2"], default="v1",
                    help="v1: all runs at the simulated d, best layouts; v2: each run at its "
                         "own d, like-for-like fixed layouts")
    ap.add_argument("--out", help="directory for the figures (default figs, or figs_v2)")
    ap.add_argument("--drop", nargs="+", default=[], metavar="SPEC",
                    help="leave these configurations out, e.g. D3-s16-fact D3-s16")
    ap.add_argument("--circuit", nargs="+",
                    help="circuits for spacetime and tradeoff (default: the largest at each R)")
    ap.add_argument("--fmt", default="pdf,png", help="comma-separated file types")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463",
                    help="as in analyze.py (for the patch qubits)")
    args = ap.parse_args()

    v2 = args.set == "v2"
    out_dir = args.out or ("figs_v2" if v2 else "figs")
    rows = [r for r in read_rows(args.csv) if r["spec"] not in args.drop]
    cells, benches = to_cells(refit(rows, 1, args.cult_grades) if v2 else rows)
    if not benches:
        raise SystemExit("no finished, feasible runs in " + args.csv)
    os.makedirs(out_dir, exist_ok=True)
    chosen = args.circuit or [
        max((b for b in benches if grade(cells[b]) == g), key=lambda b: circuit(b)[1])
        for g in sorted({grade(cells[b]) for b in benches}, key=str)]
    if v2:
        figs = [("plane_cost", lambda p: plane_cost(cells, benches, p)),
                ("ratios_same", lambda p: ratios_same(cells, benches, p)),
                ("split", lambda p: split(cells, benches, p)),
                ("split_s2", lambda p: split(
                    cells, benches, p, "s2", (1.62, 0.7),
                    (("Ising-34", "left"), ("Ising-16, Heis-16", "below-left")))),
                ("heatmap", lambda p: heatmap(cells, benches, p)),
                ("sharing", lambda p: sharing(cells, benches, p)),
                ("sources", lambda p: sources(cells, benches, p)),  # two columns
                ("sources_vs_2dcult", lambda p: sources_vs_2dcult(cells, benches, p))]
    else:
        figs = [("ratios", lambda p: ratios(cells, benches, p)),
                ("heatmap", lambda p: heatmap(cells, benches, p)),
                ("sharing", lambda p: sharing(cells, benches, p)),
                ("scaling", lambda p: scaling(cells, benches, p))]
    for b in chosen:
        tag = label(b).lower()
        figs.append((f"spacetime_{tag}", lambda p, b=b: spacetime(cells, b, args.cult_grades, p)))
        figs.append((f"tradeoff_{tag}", lambda p, b=b: tradeoff(cells, b, p)))
    captions = []
    for fig_name, draw in figs:
        for ext in args.fmt.split(","):
            caption = draw(os.path.join(out_dir, f"{fig_name}.{ext}"))
        captions.append(f"## {fig_name}\n\n{caption}\n")
    with open(os.path.join(out_dir, "captions.md"), "w") as f:
        f.write(f"# Draft captions ({os.path.basename(args.csv)}, {args.set})\n\n"
                + "\n".join(captions))
    print("wrote", len(figs), "figures (" + args.fmt + ") and captions.md to", out_dir)


if __name__ == "__main__":
    main()
