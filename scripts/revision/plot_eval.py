"""Evaluation figures for the Lower-First paper (ISCA 2027), from analyze.py's CSV.

  python plot_eval.py rev_all.csv [--out figures/revision] [--fmt pdf,png] [--pprime 1]
                     [--exclude BENCH ...]

Every run is moved to its own code distance first (fit_d.refit, vertical links at p' = m p).
Configurations (mati's Lower-First specs):
  factories    Planar-2D D0-alt  vs  HBMS Dedicated D3-k1-fact, Shared-S D3-s<S>-fact-bottom
  cultivation  2D-Cult D2-wide   vs  HBMS Dedicated D3-k1, Rows D3-rows-bottom,
                                     Ancilla D3-ancilla-bottom, Full D3-full-bottom

  eval_stv     (one column) per circuit and as the geometric mean: STV of the planar baseline
               over that of HBMS, (a) factories, (b) cultivation.
  eval_split   (one column) per configuration, ordered by the number of magic-state
               resources: geometric means of the qubit, rounds and STV ratios (baseline over
               HBMS), with the STV range over the circuits.
  split        (one column) per circuit, qubit ratio (x) against rounds ratio (y), HBMS
               Dedicated: Planar-2D / Dedicated (factories), 2D-Cult / Dedicated (cultivation).
  split_s2     (one column) the same for the routed layouts, one panel per kind: (a) Planar-2D
               / Shared-2 (factories), (b) 2D-Cult / Rows (cultivation).
  sources_fact (full width) one panel per circuit: STV ratio (Planar-2D / HBMS) against the
               number of factories in HBMS over that in Planar-2D, Shared-8 to Dedicated.
  sources_cult (full width) the same with cultivation patches: 2D-Cult / HBMS Dedicated, Rows,
               Ancilla, Full.
These four replace the Upper-First real13 figures split, split_s2 and sources.
  tint_table   (one column) the synthetic circuits (test/runs/tint1): STV ratio per T fraction
               and configuration, geometric mean over the sizes. Draw it alone with
               --only tint_table on that campaign's rev.csv.
"""

import argparse
import math
import os

import matplotlib.ticker as mticker
import numpy as np
from matplotlib.lines import Line2D

from plot_results import (COL, FILL, FULL, GRID, INK, MUTED, STAR, _lstar, circuit, gmean,
                          label, load, num, plain_log, plt, ramp, shade)

FACT = ("D0-alt", [("D3-k1-fact", "Dedicated"), ("D3-s2-fact-bottom", "Shared-2"),
                   ("D3-s4-fact-bottom", "Shared-4"), ("D3-s8-fact-bottom", "Shared-8")])
CULT = ("D2-wide", [("D3-k1", "Dedicated"), ("D3-rows-bottom", "Rows"),
                    ("D3-ancilla-bottom", "Ancilla"), ("D3-full-bottom", "Full")])


def ratios(cells, benches, base, spec, key="STV"):
    """Baseline over HBMS, per circuit (nan where a run is missing)."""
    out = []
    for b in benches:
        a, h = cells[b].get(base), cells[b].get(spec)
        out.append(num(a[key]) / num(h[key]) if a and h else np.nan)
    return np.array(out)


def per_slot(cells, benches, spec, base):
    """Magic-state resources per data slot: nominal for factories, mean over the circuits
    (relative to Dedicated, one per slot) for cultivation."""
    if base == "D0-alt":
        k = spec.split("-")[1]
        return "1" if k == "k1" else f"1/{k[1:]}"
    v = [num(cells[b][spec]["n_sources"]) / num(cells[b]["D3-k1"]["n_sources"])
         for b in benches if spec in cells[b] and "D3-k1" in cells[b]]
    return f"{np.mean(v):.1f}".rstrip("0").rstrip(".")


HATCHES = (None, "//////", "\\\\\\\\\\\\", "xxxx")  # the same order in both panels, for grayscale prints


def eval_stv(cells, benches, path):
    names = [label(b, cells[b]) for b in benches] + ["GMean"]
    panels = [(FACT, [s for s, _ in FACT[1]], "HBM", None, (3, 0.5),
               "(a) Factories: Planar-2D / HBMS", 4),
              (CULT, [s for s, _ in CULT[1]], "HBM-Cult", None, (10, 2),
               "(b) Cultivation: 2D-Cult / HBMS", 4)]
    fig, axes = plt.subplots(2, 1, figsize=(COL, 2.9), sharex=True,
                             gridspec_kw=dict(hspace=0.55))
    x = np.arange(len(names))
    for ax, ((base, specs), show, color, hatch, (top, step), tag, ncol) in zip(axes, panels):
        lab = dict(specs)
        n = len(show)
        w = 0.8 / n
        for k, spec in enumerate(show):
            r = ratios(cells, benches, base, spec)
            vals = np.append(r, gmean(r))
            fill = ramp(color, k, n)
            ax.bar(x - 0.4 + w * (k + 0.5), vals, width=w, color=fill, edgecolor=INK,
                   linewidth=0.3, hatch=HATCHES[k], label=lab[spec],
                   hatchcolor="white" if _lstar(fill) < 55 else INK)  # visible on the fill
        ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=3)
        ax.axvline(len(benches) - 0.5, ymax=0.78, color=MUTED, lw=0.5)  # stops below the legend
        ax.set_ylim(0, top)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(step))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_ylabel("STV ratio")
        ax.text(0.0, 1.04, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
        ax.legend(loc="upper right", ncol=ncol, handlelength=0.9, columnspacing=0.5,
                  handletextpad=0.25, borderaxespad=0.1, borderpad=0.2)
    axes[-1].set_xticks(x, names, rotation=45, ha="right", rotation_mode="anchor")
    axes[-1].set_xlim(-0.6, len(names) - 0.4)
    axes[-1].tick_params(axis="x", length=0)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("STV of the planar baseline divided by that of HBMS with the same kind of "
            "magic-state resource, per circuit and as the geometric mean (GMean): (a) "
            "Planar-2D over HBMS Dedicated, Shared-2, Shared-4 and Shared-8, all with "
            "factories, and (b) 2D-Cult "
            "over HBMS Dedicated, Rows, Ancilla and Full, all with cultivation patches. Above "
            "the dashed line (1), HBMS has the lower STV. Every run at the smallest odd code "
            "distance that meets the program-error target." + STAR)


def eval_split(cells, benches, path):
    fig, axes = plt.subplots(2, 1, figsize=(COL, 2.9), gridspec_kw=dict(hspace=0.75))
    for ax, ((base, specs), color, marker, (top, step), tag) in zip(
            axes, [(FACT, FILL["HBM"], "D", (3.2, 0.5), "(a) Factories: Planar-2D / HBMS"),
                   (CULT, FILL["HBM-Cult"], "s", (9, 2), "(b) Cultivation: 2D-Cult / HBMS")]):
        fam = "HBM" if base == "D0-alt" else "HBM-Cult"
        bars = [("Q", "Qubits", ramp(fam, 3, 4), None), ("rounds", "Rounds", ramp(fam, 2, 4), "//////")]
        order = specs  # Dedicated first in both panels, as in eval_stv
        x = np.arange(len(order))
        w = 0.3
        for k, (key, mlab, fill, hatch) in enumerate(bars):
            vals = [gmean(ratios(cells, benches, base, spec, key)) for spec, _ in order]
            ax.bar(x + (k - 0.5) * w, vals, width=w, color=fill, edgecolor=INK,
                   linewidth=0.3, label=mlab, hatch=hatch, hatchcolor=INK)
        r = [ratios(cells, benches, base, spec) for spec, _ in order]
        g = np.array([gmean(v) for v in r])
        lo, hi = g - np.array([np.nanmin(v) for v in r]), np.array([np.nanmax(v) for v in r]) - g
        ax.errorbar(x, g, yerr=[lo, hi], fmt=marker, color=ramp(fam, 0, 4), mec=INK, mew=0.4, ms=4.5,
                    ecolor=INK, elinewidth=0.6, capsize=1.5, zorder=4,
                    label="STV")
        ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=3)
        ticks = [f"{lab}\n{per_slot(cells, benches, spec, base)}" for spec, lab in order]
        ax.set_xticks(x, ticks)
        ax.tick_params(axis="x", length=0)
        ax.set_xlim(-0.6, len(order) - 0.4)
        ax.set_ylim(0, top)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(step))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_ylabel("Ratio")
        ax.text(0.0, 1.04, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    for ax, loc in zip(axes, ("upper left", "upper left")):  # inside, above the Dedicated bars
        ax.legend(loc=loc, ncol=3, handlelength=1.0, columnspacing=0.8, handletextpad=0.3)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("Physical qubits (plain bars) and rounds (hatched bars) and STV (markers) of the planar baseline "
            "divided by those of HBMS, as geometric means over the circuits, per HBMS "
            "configuration, with its number of magic-state resources per data slot below its "
            "name: (a) Planar-2D over HBMS Dedicated to Shared-8, with factories, and (b) "
            "2D-Cult over HBMS Dedicated to Full, with cultivation patches. "
            "Whiskers: the STV ratio's range over the circuits. Above the dashed line (1), "
            "HBMS uses fewer qubits or rounds, or has the lower STV. Every run at the smallest "
            "odd code distance that meets the program-error target.")


MARK = {"D3-k1-fact": "o", "D3-s2-fact-bottom": "s", "D3-s4-fact-bottom": "^",
        "D3-s8-fact-bottom": "D", "D3-s16-fact-bottom": "v",
        "D3-k1": "o", "D3-rows-bottom": "s", "D3-ancilla-bottom": "^", "D3-full-bottom": "D"}
D_NOTE = "Every run at the smallest odd code distance that meets the program-error target."


def split_points(ax, cells, benches, base, spec, color, marker, tol, place, legend=None):
    """Scatter qubit ratio (x) against rounds ratio (y), one marker per circuit, and label
    them. Points closer than tol = (dx, dy) share a label. place: label text -> (dx, dy, ha)
    offset in points, for labels that would collide (default: right of the marker)."""
    pts = [(num(cells[b][base]["Q"]) / num(cells[b][spec]["Q"]),
            num(cells[b][base]["rounds"]) / num(cells[b][spec]["rounds"]), b)
           for b in benches if base in cells[b] and spec in cells[b]]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=20, marker=marker, facecolor=color,
               edgecolor=INK, linewidth=0.4, zorder=3, label=legend)
    groups = []
    for p in sorted(pts, key=lambda p: (p[1], p[0])):
        for g in groups:
            if abs(g[0][0] - p[0]) < tol[0] and abs(g[0][1] - p[1]) < tol[1]:
                g.append(p)
                break
        else:
            groups.append([p])
    for g in groups:
        ns = [circuit(p[2])[1] for p in g]
        if len(g) == len(benches):
            text = f"all {len(g)} circuits"
        elif len(g) > 2 and max(ns) <= 16:
            text = f"{len(g)} circuits, n ≤ 16"
        else:  # compact: "Heis-25, -49*, -64*"
            out, last = [], None
            for p in sorted(g, key=lambda p: circuit(p[2])):
                lab = label(p[2], cells[p[2]])
                if "-" not in lab:  # a molecule (H2, LiH*): its name alone
                    out.append(lab)
                    last = None
                    continue
                fam, rest = lab.split("-", 1)
                out.append(f"-{rest}" if fam == last else f"{fam}-{rest}")
                last = fam
            text = ", ".join(out)
        x, y = max(p[0] for p in g), float(np.mean([p[1] for p in g]))
        dx, dy, ha = place.get(text, (4, 0, "left"))
        if ha == "right":
            x = min(p[0] for p in g)
        ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8,
                    ha=ha, va="center", color=MUTED)
    return pts


def split_frame(ax, xs, ys, xlabel=True, pad=(0.08, 0.25, 0.08, 0.1)):
    lo, hi = min(xs + [1]) - pad[0], max(xs) + pad[1]
    xx = np.linspace(lo, hi, 200)
    ax.plot(xx, 1 / xx, color=INK, lw=0.7, ls="--", zorder=1)
    ax.axvline(1, color=GRID, lw=0.6, zorder=0)
    ax.axhline(1, color=GRID, lw=0.6, zorder=0)
    ax.set_xlim(lo, hi)
    ax.set_ylim(min(ys + [1]) - pad[2], max(ys) + pad[3])
    if xlabel:
        ax.set_xlabel("Qubit ratio")
    ax.set_ylabel("Rounds ratio")
    for axis in (ax.xaxis, ax.yaxis):  # 1, 1.5 as in eval_split, not 1.00, 1.50
        axis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))


def split(cells, benches, path):
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    pf = split_points(ax, cells, benches, "D0-alt", "D3-k1-fact", FILL["HBM"], "o",
                      (0.03, 0.05), {"Ising-26": (-4, 0, "right")},
                      "Planar-2D / HBMS Dedicated (factories)")
    pc = split_points(ax, cells, benches, "D2-wide", "D3-k1", FILL["HBM-Cult"], "s",
                      (0.03, 0.05), {"all 11 circuits": (-6, -9, "left")},
                      "2D-Cult / HBMS Dedicated (cultivation)")
    xs, ys = [p[0] for p in pf + pc], [p[1] for p in pf + pc]
    split_frame(ax, xs, ys, pad=(0.08, 0.3, 0.17, 0.5))
    ax.text(0.745, 1.2, "equal STV", fontsize=8, ha="center", va="center", color=INK,
            rotation=-38)
    ax.legend(loc="upper right", ncol=1, handletextpad=0.3)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("Physical qubits ($x$) and rounds ($y$) of the planar baseline divided by those "
            "of HBMS Dedicated, one marker per circuit: Planar-2D over HBMS Dedicated, both "
            "with factories (circles), and 2D-Cult over HBMS Dedicated, both with cultivation "
            "patches (squares). Beyond 1 on an axis, HBMS uses fewer qubits or rounds. Above "
            "the dashed curve ($xy = 1$), HBMS has the lower STV. Circuits whose markers "
            "coincide share one label. " + D_NOTE + STAR)


def split_s2(cells, benches, path):
    fig, axes = plt.subplots(2, 1, figsize=(COL, 3.4), gridspec_kw=dict(hspace=0.55))
    panels = [(axes[0], "D0-alt", "D3-s2-fact-bottom", FILL["HBM"], "o",
               "(a) Factories: Planar-2D / HBMS Shared-2", (0.06, 0.05),
               {"Ising-26": (0, 7, "center"), "Heis-16, Ising-16": (4, 5, "left")}),
              (axes[1], "D2-wide", "D3-rows-bottom", FILL["HBM-Cult"], "s",
               "(b) Cultivation: 2D-Cult / HBMS Rows", (0.03, 0.8), {})]
    for ax, base, spec, color, marker, tag, tol, place in panels:
        pts = split_points(ax, cells, benches, base, spec, color, marker, tol, place)
        split_frame(ax, [p[0] for p in pts], [p[1] for p in pts], pad=(0.1, 0.45, 0.1, 0.3))
        ax.text(0.0, 1.03, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("As Fig. split, for the HBMS configurations whose T gates route with Lower-First: "
            "(a) Planar-2D over HBMS Shared-2, both with factories, and (b) 2D-Cult over HBMS "
            "Rows, both with cultivation patches. One marker per circuit. Beyond 1 on an axis, "
            "HBMS uses fewer qubits or rounds. Above the dashed curve ($xy = 1$), HBMS has the "
            "lower STV. " + D_NOTE + STAR)


KINDS = {  # kind: (baseline and HBMS configurations, colour, x label, resource name)
    "fact": (FACT, FILL["HBM"], "Factories in HBMS / in Planar-2D", "factories"),
    "cult": (CULT, FILL["HBM-Cult"], "Cultivation patches in HBMS / in 2D-Cult", "patches"),
}


def source_grid(cells, benches, path, kind):
    """One panel per circuit: STV ratio (baseline / HBMS) against the resource-count ratio
    (HBMS / baseline), a marker per HBMS configuration, for one kind of magic-state resource."""
    (base, specs), color, xlabel, _ = KINDS[kind]
    ncol = 6
    nrow = int(np.ceil(len(benches) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(FULL, 1.2 * nrow + 0.25), sharex=True,
                             sharey=True, squeeze=False,
                             gridspec_kw=dict(wspace=0.1, hspace=0.38))
    xs, ys = [], []
    for ax, b in zip(axes.flat, benches):
        cs = cells[b]
        pts = sorted((num(cs[s]["n_sources"]) / num(cs[base]["n_sources"]),
                      num(cs[base]["STV"]) / num(cs[s]["STV"]), s)
                     for s, _ in specs if s in cs and base in cs)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=0.9, zorder=2)
        for x, y, s in pts:
            ax.scatter(x, y, s=18, marker=MARK[s], color=color, edgecolor=INK, lw=0.3,
                       zorder=3)
            xs.append(x)
            ys.append(y)
        ax.axhline(1, color=INK, lw=0.6, ls="--")
        ax.axvline(1, color=INK, lw=0.6, ls=":")
        title = label(b, cs)  # the * marks the slower cultivation grade
        ax.set_title(title if kind == "cult" else title.rstrip("*"), fontsize=8, pad=2)
        ax.grid(True, color=GRID, lw=0.4)
        ax.set_axisbelow(True)
    ax0 = axes.flat[0]
    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlim(min(xs + [1]) / 1.5, max(xs + [1]) * 1.5)
    ax0.set_ylim(min(ys + [1]) / 1.6, max(ys + [1]) * 1.6)
    plain_log(ax0, "x", minor="")
    plain_log(ax0, "y", minor="")
    if kind == "cult":  # less than a decade on x: label 1, 2, 5 (and 2, 5 on y)
        fmt = mticker.FuncFormatter(lambda v, _: f"{v:g}")
        ax0.xaxis.set_major_locator(mticker.FixedLocator([1, 2, 5]))
        ax0.yaxis.set_major_locator(mticker.FixedLocator([1, 2, 5, 10]))
        ax0.xaxis.set_major_formatter(fmt)
        ax0.yaxis.set_major_formatter(fmt)
        ax0.xaxis.set_minor_formatter(mticker.NullFormatter())
        ax0.yaxis.set_minor_formatter(mticker.NullFormatter())
    for ax in axes.flat[len(benches):]:
        ax.axis("off")
    order = specs if kind == "cult" else specs[::-1]  # fewest resources first
    handles = [Line2D([], [], ls="", marker=MARK[s], ms=4.5, color=color, mec=INK, mew=0.3,
                      label=lab) for s, lab in order]
    head = Line2D([], [], ls="", label="HBMS:")  # a text-only first entry
    fig.legend(handles=[head] + handles, loc="lower center", ncol=len(handles) + 1,
               fontsize=8, bbox_to_anchor=(0.5, 0.95), handletextpad=0.2, columnspacing=1.2,
               borderaxespad=0, handlelength=0.8)
    fig.supxlabel(xlabel, fontsize=9, y=-0.05)
    fig.supylabel("STV ratio (" + ("Planar-2D" if kind == "fact" else "2D-Cult") + " / HBMS)",
                  fontsize=9, x=0.06)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)


def sources_fact(cells, benches, path):
    source_grid(cells, benches, path, "fact")
    return ("STV of Planar-2D divided by that of HBMS, both with factories, against the "
            "number of factories in HBMS over that in Planar-2D, one panel per circuit. "
            "Markers give the HBMS configuration, from Shared-8 to Dedicated. Above the "
            "dashed line (1), HBMS has the lower STV. On the dotted line, both use the same "
            "number of factories. Both axes are logarithmic. " + D_NOTE)


def sources_cult(cells, benches, path):
    source_grid(cells, benches, path, "cult")
    return ("STV of 2D-Cult divided by that of HBMS, both with cultivation patches, against "
            "the number of patches in HBMS over that in 2D-Cult, one panel per circuit. "
            "Markers give the HBMS configuration: Dedicated, Rows, Ancilla and Full. Above "
            "the dashed line (1), HBMS has the lower STV. On the dotted line, both use the "
            "same number of patches. Both axes are logarithmic. " + D_NOTE + STAR)


def _mix(hex_color, t):
    """hex_color blended towards white: t = 0 white, t = 1 the full colour."""
    rgb = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    return tuple(1 - t * (1 - rgb))


BASE_FILL = {"D0-alt": "#808080", "D2-wide": "#F0A33A"}  # Planar-2D, 2D-Cult (plot_results)
SPAN = {"D0-alt": math.log(4), "D2-wide": math.log(8)}  # colour scale per panel, log, centred on 1


def sources_table(cells, benches, path):
    """One column: the STV ratio (baseline / HBMS) per circuit (rows, then GMean) and HBMS
    configuration (columns), one panel per kind of magic-state resource. Each panel shades
    towards its HBMS colour above 1 and towards its baseline's colour below 1."""
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    blocks = [(FACT[0], FACT[1], FILL["HBM"], "(a) Factories:\nPlanar-2D / HBMS"),
              (CULT[0], CULT[1], FILL["HBM-Cult"], "(b) Cultivation:\n2D-Cult / HBMS")]
    names = [label(b, cells[b]) for b in benches] + ["GMean"]
    n = len(benches)
    edges = np.r_[np.arange(n + 1), n + 0.3, n + 1.3]  # GMean row set apart
    height = 3.0 * (n + 2.3) / 13.3  # 3.0 in for the 11 real circuits, the same row pitch beyond
    fig, axes = plt.subplots(1, 2, figsize=(COL, height), sharey=True,
                             gridspec_kw=dict(width_ratios=[len(b[1]) for b in blocks],
                                              wspace=0.08))
    for ax, (base, specs, hue, tag) in zip(axes, blocks):
        vals = np.array([ratios(cells, benches, base, s) for s, _ in specs]).T
        vals = np.vstack([vals, [gmean(v) for v in vals.T]])
        grid = np.vstack([vals[:n], np.full(len(specs), np.nan), vals[n:]])
        cmap = LinearSegmentedColormap.from_list(
            "c", [_mix(BASE_FILL[base], 0.65), (1, 1, 1), _mix(hue, 0.65)])
        cmap.set_bad(alpha=0)
        ax.pcolormesh(np.arange(len(specs) + 1), edges, np.ma.masked_invalid(np.log(grid)),
                      cmap=cmap, norm=Normalize(-SPAN[base], SPAN[base]), edgecolors="white",
                      linewidth=0.8)
        for i, row in enumerate(vals):
            y = (edges[i] + edges[i + 1]) / 2 if i < n else (edges[n + 1] + edges[n + 2]) / 2
            best = np.nanargmax(row) if np.isfinite(row).any() else -1
            for j, v in enumerate(row):  # a missing run (no source on a small grid) as a dash
                ax.text(j + 0.5, y, f"{v:.2f}" if np.isfinite(v) else "\u2013", ha="center",
                        va="center", fontsize=8, color=MUTED if not np.isfinite(v) else INK,
                        fontweight="bold" if j == best else "normal")
        ax.axhline(n + 0.15, color=INK, lw=0.6)
        ax.set_xticks(np.arange(len(specs)) + 0.5, [lab for _, lab in specs], rotation=45,
                      ha="right", rotation_mode="anchor")
        ax.set_ylim(edges[-1], 0)
        ax.set_xlim(0, len(specs))
        ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.text(0.0, 1.02, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    centers = list((edges[:n] + edges[1:n + 1]) / 2) + [(edges[n + 1] + edges[n + 2]) / 2]
    axes[0].set_yticks(centers, names)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("STV of the planar baseline divided by that of HBMS with the same kind of "
            "magic-state resource, per circuit and as the geometric mean (GMean), for every "
            "HBMS configuration, starting from Dedicated: (a) Planar-2D over HBMS Dedicated to "
            "Shared-8, all with factories, and (b) 2D-Cult over HBMS "
            "Dedicated to Full, all with cultivation patches. Cells shade towards the HBMS "
            "colour above 1, where HBMS has the lower STV, and towards the baseline's colour "
            "below 1, each panel on its own logarithmic scale. Bold: the HBMS configuration with the lowest STV on the circuit, within "
            "each panel. " + D_NOTE + (MISSING if np.isnan(
                [ratios(cells, benches, b, s) for b, sp in (FACT, CULT) for s, _ in sp]).any()
                else "") + STAR)


MISSING = (" Dash: no run, the grid too small for one magic-state source at that sharing "
           "ratio; GMean is over the circuits that have one.")


TINT = ("10", "50", "90")  # T fraction of the synthetic circuits, % of all gates


def tint_table(cells, benches, path):
    """One column: the STV ratio (baseline / HBMS) on the synthetic circuits, geometric mean over
    their sizes, per T fraction (rows) and HBMS configuration (columns), one panel per kind of
    magic-state resource. Shading and bold as in sources_table."""
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    blocks = [(FACT[0], FACT[1], FILL["HBM"], "(a) Factories:\nPlanar-2D / HBMS"),
              (CULT[0], CULT[1], FILL["HBM-Cult"], "(b) Cultivation:\n2D-Cult / HBMS")]
    frac = lambda b: b.rsplit("_p", 1)[1]  # noqa: E731
    rows = [t for t in TINT if any(frac(b) == t for b in benches)]
    fig, axes = plt.subplots(1, 2, figsize=(COL, 1.5), sharey=True,
                             gridspec_kw=dict(width_ratios=[len(b[1]) for b in blocks],
                                              wspace=0.08))
    for ax, (base, specs, hue, tag) in zip(axes, blocks):
        vals = np.array([[gmean(ratios(cells, [b for b in benches if frac(b) == t], base, s))
                          for s, _ in specs] for t in rows])
        cmap = LinearSegmentedColormap.from_list(
            "c", [_mix(BASE_FILL[base], 0.65), (1, 1, 1), _mix(hue, 0.65)])
        ax.pcolormesh(np.arange(len(specs) + 1), np.arange(len(rows) + 1), np.log(vals),
                      cmap=cmap, norm=Normalize(-SPAN[base], SPAN[base]), edgecolors="white",
                      linewidth=0.8)
        for i, row in enumerate(vals):
            best = np.nanargmax(row)
            for j, v in enumerate(row):
                ax.text(j + 0.5, i + 0.5, f"{v:.2f}", ha="center", va="center", fontsize=8,
                        color=INK, fontweight="bold" if j == best else "normal")
        ax.set_xticks(np.arange(len(specs)) + 0.5, [lab for _, lab in specs], rotation=45,
                      ha="right", rotation_mode="anchor")
        ax.set_ylim(len(rows), 0)
        ax.set_xlim(0, len(specs))
        ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.text(0.0, 1.04, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    axes[0].set_yticks(np.arange(len(rows)) + 0.5, [f"{t}% T" for t in rows])
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("STV of the planar baseline over that of HBMS on the synthetic circuits, geometric "
            "mean over the seven sizes, per T fraction: (a) with factories, (b) with cultivation "
            "patches. Bold: best configuration per row and panel.")


def split_size(cells, benches, path):
    """One column, two panels (Dedicated, Shared-2, both with factories): qubit, rounds and STV
    ratios (Planar-2D / HBMS) against the grid's data slots N, one marker per circuit and a
    line through the geometric mean at each N."""
    side = {b: math.ceil(math.sqrt(int(cells[b]["D0-alt"]["N"]))) for b in benches}
    sizes = sorted(set(side.values()))
    color = FILL["HBM"]
    series = [("Q", "Qubits", _mix(color, 0.35), "o"), ("rounds", "Rounds", _mix(color, 0.7), "s"),
              ("STV", "STV", color, "D")]
    fig, axes = plt.subplots(1, 2, figsize=(COL, 2.05), sharey=True,
                             gridspec_kw=dict(wspace=0.12))
    for ax, spec, tag in zip(axes, ("D3-k1-fact", "D3-s2-fact-bottom"),
                             ("(a) Dedicated:\nPlanar-2D / HBMS", "(b) Shared-2:\nPlanar-2D / HBMS")):
        for key, lab, c, mk in series:
            r = dict(zip(benches, ratios(cells, benches, "D0-alt", spec, key)))
            ax.scatter([side[b] for b in benches], [r[b] for b in benches], s=14, marker=mk,
                       facecolor=c, edgecolor=INK, linewidth=0.3, zorder=3 if key == "STV" else 2)
            g = [gmean([r[b] for b in benches if side[b] == k]) for k in sizes]
            ax.plot(sizes, g, color=c, lw=1.2 if key == "STV" else 1.0, zorder=1,
                    marker=mk, ms=0, label=lab)
        ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=0)
        ax.set_xticks(sizes, [str(k * k) for k in sizes])
        ax.set_xlim(sizes[0] - 0.5, sizes[-1] + 0.5)
        ax.set_ylim(0.4, 2.3)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_xlabel("Data slots $N$")
        ax.text(0.0, 1.02, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    axes[0].set_ylabel("Ratio")
    handles = [Line2D([], [], color=c, marker=mk, ms=4, mfc=c, mec=INK, mew=0.3,
                      lw=1.2 if key == "STV" else 1.0, label=lab) for key, lab, c, mk in series]
    axes[1].legend(handles=handles, loc="upper right", handlelength=1.4, handletextpad=0.3,
                   labelspacing=0.25)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("Physical qubits, rounds and STV of Planar-2D divided by those of HBMS, all with "
            "factories, against the number of data slots $N$ of the circuit's grid: (a) HBMS "
            "Dedicated, (b) HBMS Shared-2. Markers: one per circuit. Lines: the geometric mean "
            "over the circuits of each $N$. Above the dashed line (1), HBMS uses fewer qubits or "
            "rounds, or has the lower STV. " + D_NOTE)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..",
                                                  "figures", "revision"))
    ap.add_argument("--fmt", default="pdf,png")
    ap.add_argument("--pprime", type=float, default=1, help="vertical links at p' = m p")
    ap.add_argument("--only", nargs="+", metavar="FIG",
                    help="figures to draw (default: all but tint_table, which needs the "
                         "synthetic circuits)")
    ap.add_argument("--exclude", nargs="+", default=[], metavar="BENCH",
                    help="circuits to leave out (e.g. h2o, whose 2D-Cult run timed out)")
    args = ap.parse_args()
    cells, benches = load(args.csv, fit=args.pprime)
    benches = [b for b in benches if b not in args.exclude]
    os.makedirs(args.out, exist_ok=True)
    paths = lambda n: [os.path.join(args.out, f"{n}.{f}") for f in args.fmt.split(",")]  # noqa
    with open(os.path.join(args.out, "eval_captions.md"), "w") as f:
        figs = [("eval_stv", eval_stv), ("eval_split", eval_split), ("split", split),
                ("split_s2", split_s2), ("sources_fact", sources_fact),
                ("sources_cult", sources_cult), ("sources_table", sources_table),
                ("split_size", split_size), ("tint_table", tint_table)]
        for name, fn in figs:
            if (args.only and name not in args.only) or (not args.only and name == "tint_table"):
                continue
            f.write(f"**{name}.pdf.** {fn(cells, benches, paths(name))}\n\n")
    print("wrote", os.path.normpath(args.out))


if __name__ == "__main__":
    main()
