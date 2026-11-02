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
    return (f"each run at the smallest odd code distance that meets the program-error target "
            f"(d = {ds[0]}-{ds[-1]})")


def miss_note(cells, mark):
    """The caption note for runs that miss the target, or nothing when every run meets it."""
    if fitted(cells):
        return ""
    return f" {mark}: the run exceeds the program-error target at d = {d_sim(cells)}."


STAR = " *: the circuit's T count requires the slower cultivation grade (R = 360 rounds)."


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
            "source shared by 2 to 16 data qubits (S2-S16). Row labels give the circuit's T "
            f"count. All runs at {d_note(cells)}." + miss_note(cells, "†") + STAR)


def sharing(cells, benches, path):
    fig, ax = plt.subplots(figsize=(COL, 1.5))
    x = np.arange(len(SHARING))
    # Each HBM source type against the 2D layout with the same source type.
    lines = [("HBM", "D3-{}-fact", ("D0-alt",), "Planar-2D / HBM (factories)"),
             ("HBM-Cult", "D3-{}", CULT, "2D-Cult / HBM-Cult (cultivation)")]
    for fam, fmt, base_specs, legend in lines:
        per = []  # per sharing ratio: the ratio on each circuit
        for key in SHARING:
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
    ax.set_xticks(x, SHARE_LABEL)
    ax.set_xlabel("data qubits per T source")
    ax.set_ylabel("STV ratio")
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.legend(loc="lower left")
    fig.savefig(path)
    plt.close(fig)
    return ("STV of a 2D baseline divided by that of HBM with the same kind of T source, "
            "against HBM's sharing ratio (Ded: one T source per data qubit; S2-S16: one "
            "source per 2 to 16 data qubits): Planar-2D over HBM, both with factories "
            "(solid), and 2D-Cult over HBM-Cult, both with cultivation patches (dashed), each "
            "2D baseline at its best layout. Lines: geometric mean over the circuits; bands: "
            "range. Above the dashed line (1), HBM has the lower STV; log scale.")


def space_parts(c, grades):
    """Qubits split into data tiles, other tiles and T sources (factories at 22 d^2)."""
    d = int(c["d_sim"])
    data = int(c["N"]) * 2 * d * d
    src = int(c["n_factories"]) * 22 * d * d
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
    specs = [s for s in SPACETIME_SPECS if s in cs]
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
    "D3-s16-fact": ("HBM-S16", (6, 0), "left", "center"),
    "D3-k1": ("HBM-Cult-Ded", (0, -6), "center", "top"),
    "D3-s16": ("HBM-Cult-S16", (6, 0), "left", "center"),
}


def tradeoff(cells, bench, path):
    cs = cells[bench]
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
            if s in TRADEOFF_LABEL:
                text, off, ha, va = TRADEOFF_LABEL[s]
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
            "half a cultivation patch per data qubit; HBM and HBM-Cult: Ded to S16). Grey "
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
# v2: like-for-like at fixed layouts, vertical-link sensitivity, T-density crossover
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
    ax.set_yscale("log")
    plain_log(ax, minor="2345678")
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("STV ratio")
    ax.grid(True, axis="y", which="both", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    legend_above(ax, 1)
    fig.savefig(path)
    plt.close(fig)
    return ("STV of a 2D baseline divided by that of HBM with the same kind of T source and "
            "a layout fixed for all circuits, per circuit and as the geometric mean (GMean): "
            "Planar-2D against HBM-Ded, both with factories, and 2D-Cult (one cultivation "
            "patch per data qubit) against HBM-Cult-Ded, both with cultivation patches. Ded: "
            "one T source per data qubit. Above the dashed line (1), HBM has the lower STV; log "
            f"scale. All runs at {d_note(cells)}." + STAR)


PPRIMES = (1, 5, 10)


def pprime(rows, grades, path):
    fig, ax = plt.subplots(figsize=(COL, 1.5))
    x = np.arange(len(PPRIMES))
    per_fit = [to_cells(refit(rows, m, grades))[0] for m in PPRIMES]
    for _, legend, base, hbm, fam in SAME:
        per = [[r for r in (same_ratio(cells[b], base, hbm) for b in cells) if r]
               for cells in per_fit]
        mk, ls = STYLE[fam]
        ax.fill_between(x, [min(r) for r in per], [max(r) for r in per], color=LINE[fam],
                        alpha=0.15, lw=0)
        ax.plot(x, [gmean(r) for r in per], color=LINE[fam], marker=mk, ls=ls, label=legend)
    ax.axhline(1, color=INK, lw=0.7, ls="--")
    ax.set_yscale("log")
    plain_log(ax, minor="25")
    ax.set_xticks(x, ["p" if m == 1 else f"{m}p" for m in PPRIMES])
    ax.set_xlabel("vertical-link error rate p′")
    ax.set_ylabel("STV ratio")
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.legend(loc="lower left")
    fig.savefig(path)
    plt.close(fig)
    ds = sorted({int(c["d_sim"]) for cells in per_fit for cs in cells.values()
                 for c in cs.values()})
    return ("STV of a 2D baseline divided by that of HBM with the same kind of T source and a "
            "fixed layout (as in the like-for-like ratios), against the error rate p′ of the "
            "vertical links between the layers, in units of the physical error rate p. At each "
            "p′ every run uses the smallest odd code distance that meets the program-error "
            f"target (d = {ds[0]}-{ds[-1]}); vertical merges use the lower thresholds measured "
            "for them in Stim. Lines: geometric mean over the circuits; bands: range. Above "
            "the dashed line (1), HBM has the lower STV; log scale.")


def crossover(sets, path):
    """sets: [(name, cells)]; the first is drawn in colour, the rest in grey."""
    fig, ax = plt.subplots(figsize=(COL, 1.6))
    _, legend, base, hbm, fam = SAME[0]
    for k, (set_name, cells) in enumerate(sets):
        pts = [(num(next(iter(cs.values()))["t_density"]), same_ratio(cs, base, hbm), b)
               for b, cs in cells.items()]
        pts = [p for p in pts if p[1]]
        if k == 0:
            for fam_name, mk in (("Ising", "o"), ("Heisenberg", "s")):
                sel = [p for p in pts if circuit(p[2])[0] == fam_name]
                ax.scatter([p[0] for p in sel], [p[1] for p in sel], s=18, marker=mk,
                           color=LINE["HBM"], edgecolor=INK, lw=0.4, zorder=3, label=fam_name)
        else:
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=12, marker="^",
                       color="#9a9a9a", edgecolor=INK, lw=0.3, zorder=2, label=set_name)
    ax.axhline(1, color=INK, lw=0.7, ls="--")
    ax.set_yscale("log")
    plain_log(ax, minor="2345")
    ax.set_xlabel("T density (T gates per qubit per ideal step)")
    ax.set_ylabel("STV ratio")
    ax.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    legend_above(ax, 3)
    fig.savefig(path)
    plt.close(fig)
    return ("STV of Planar-2D divided by that of HBM-Ded (both with factories) against the "
            "circuit's T density, the T count over logical qubits times ideal depth. Each "
            "marker is one circuit"
            + ("; grey: " + ", ".join(n for n, _ in sets[1:]) if len(sets) > 1 else "")
            + ". Above the dashed line (1), HBM has the lower STV; log scale. All runs at "
            f"{d_note(sets[0][1])}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--set", choices=["v1", "v2"], default="v1",
                    help="v1: all runs at the simulated d, best layouts; v2: each run at its "
                         "own d, like-for-like fixed layouts, p' sensitivity, T-density crossover")
    ap.add_argument("--out", help="directory for the figures (default figs, or figs_v2)")
    ap.add_argument("--extra", nargs="+", default=[], metavar="NAME=CSV",
                    help="v2 crossover: more campaigns drawn in grey, e.g. synthetic=rev.csv")
    ap.add_argument("--circuit", nargs="+",
                    help="circuits for spacetime and tradeoff (default: the largest at each R)")
    ap.add_argument("--fmt", default="pdf,png", help="comma-separated file types")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463",
                    help="as in analyze.py (for the patch qubits)")
    args = ap.parse_args()

    v2 = args.set == "v2"
    out_dir = args.out or ("figs_v2" if v2 else "figs")
    rows = read_rows(args.csv)
    cells, benches = to_cells(refit(rows, 1, args.cult_grades) if v2 else rows)
    if not benches:
        raise SystemExit("no finished, feasible runs in " + args.csv)
    os.makedirs(out_dir, exist_ok=True)
    chosen = args.circuit or [
        max((b for b in benches if grade(cells[b]) == g), key=lambda b: circuit(b)[1])
        for g in sorted({grade(cells[b]) for b in benches}, key=str)]
    if v2:
        sets = [("this campaign", cells)]
        for item in args.extra:
            set_name, path = item.split("=", 1) if "=" in item else (os.path.basename(item), item)
            sets.append((set_name, load(path, 1, args.cult_grades)[0]))
        figs = [("ratios_same", lambda p: ratios_same(cells, benches, p)),
                ("heatmap", lambda p: heatmap(cells, benches, p)),
                ("sharing", lambda p: sharing(cells, benches, p)),
                ("pprime", lambda p: pprime(rows, args.cult_grades, p)),
                ("crossover", lambda p: crossover(sets, p))]
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
