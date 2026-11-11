"""Evaluation figures for the Lower-First paper (ISCA 2027), from analyze.py's CSV.

  python plot_eval.py rev_all.csv [--out figures/revision] [--fmt pdf,png] [--pprime 1]

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
               number of factories in HBMS over that in Planar-2D, Shared-16 to Dedicated.
  sources_cult (full width) the same with cultivation patches: 2D-Cult / HBMS Dedicated, Rows,
               Ancilla, Full.
These four replace the Upper-First real13 figures split, split_s2 and sources.
"""

import argparse
import os

import matplotlib.ticker as mticker
import numpy as np
from matplotlib.lines import Line2D

from plot_results import (COL, FILL, FULL, GRID, INK, MUTED, STAR, circuit, gmean, label,
                          load, num, plain_log, plt, shade)

FACT = ("D0-alt", [("D3-k1-fact", "Dedicated"), ("D3-s2-fact-bottom", "Shared-2"),
                   ("D3-s4-fact-bottom", "Shared-4"), ("D3-s8-fact-bottom", "Shared-8"),
                   ("D3-s16-fact-bottom", "Shared-16")])
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


def eval_stv(cells, benches, path):
    names = [label(b, cells[b]) for b in benches] + ["GMean"]
    panels = [(FACT, ["D3-k1-fact", "D3-s2-fact-bottom"], FILL["HBM"], None, (2.5, 0.5),
               "(a) Factories: Planar-2D / HBMS", 2),
              (CULT, [s for s, _ in CULT[1]], FILL["HBM-Cult"], None, (10, 2),
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
            ax.bar(x - 0.4 + w * (k + 0.5), vals, width=w, color=shade(color, k, n),
                   edgecolor=INK, linewidth=0.3, hatch=hatch, label=lab[spec])
        ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=3)
        ax.axvline(len(benches) - 0.5, color=MUTED, lw=0.5)
        ax.set_ylim(0, top)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(step))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_ylabel("STV ratio")
        ax.text(0.0, 1.04, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
        ax.legend(loc="upper right", ncol=ncol, handlelength=1.0, columnspacing=0.7,
                  handletextpad=0.3, borderaxespad=0.1)
    axes[-1].set_xticks(x, names, rotation=45, ha="right", rotation_mode="anchor")
    axes[-1].set_xlim(-0.6, len(names) - 0.4)
    axes[-1].tick_params(axis="x", length=0)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("STV of the planar baseline divided by that of HBMS with the same kind of "
            "magic-state resource, per circuit and as the geometric mean (GMean): (a) "
            "Planar-2D over HBMS Dedicated and Shared-2, all with factories, and (b) 2D-Cult "
            "over HBMS Dedicated, Rows, Ancilla and Full, all with cultivation patches. Above "
            "the dashed line (1), HBMS has the lower STV. Every run at the smallest odd code "
            "distance that meets the program-error target." + STAR)


def eval_split(cells, benches, path):
    fig, axes = plt.subplots(2, 1, figsize=(COL, 2.9), gridspec_kw=dict(hspace=0.75))
    bars = [("Q", "Qubits", "#D4D4D4"), ("rounds", "Rounds", "#8C8C8C")]
    for ax, ((base, specs), color, marker, (top, step), tag) in zip(
            axes, [(FACT, FILL["HBM"], "D", (3, 0.5), "(a) Factories: Planar-2D / HBMS"),
                   (CULT, FILL["HBM-Cult"], "s", (8, 2), "(b) Cultivation: 2D-Cult / HBMS")]):
        order = specs[::-1] if base == "D0-alt" else specs  # fewest resources first
        x = np.arange(len(order))
        w = 0.3
        for k, (key, mlab, fill) in enumerate(bars):
            vals = [gmean(ratios(cells, benches, base, spec, key)) for spec, _ in order]
            ax.bar(x + (k - 0.5) * w, vals, width=w, color=fill, edgecolor=INK,
                   linewidth=0.3, label=mlab)
        r = [ratios(cells, benches, base, spec) for spec, _ in order]
        g = np.array([gmean(v) for v in r])
        lo, hi = g - np.array([np.nanmin(v) for v in r]), np.array([np.nanmax(v) for v in r]) - g
        ax.errorbar(x, g, yerr=[lo, hi], fmt=marker, color=color, mec=INK, mew=0.4, ms=4.5,
                    ecolor=INK, elinewidth=0.6, capsize=1.5, zorder=4,
                    label="STV, " + ("factories" if base == "D0-alt" else "cultivation"))
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
        ax.set_ylabel("Baseline / HBMS")
        ax.text(0.0, 1.04, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    h0, l0 = axes[0].get_legend_handles_labels()
    h1, l1 = axes[1].get_legend_handles_labels()
    fig.legend(h0 + h1[2:], l0 + l1[2:], loc="lower center", bbox_to_anchor=(0.5, 0.97),
               ncol=4, handlelength=1.0, columnspacing=0.7, handletextpad=0.3)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("Physical qubits and rounds (bars) and STV (markers) of the planar baseline "
            "divided by those of HBMS, as geometric means over the circuits, per HBMS "
            "configuration ordered by its number of magic-state resources per data slot "
            "(below each name): (a) Planar-2D over HBMS Shared-16 to Dedicated, with "
            "factories, and (b) 2D-Cult over HBMS Dedicated to Full, with cultivation patches. "
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
                fam, rest = label(p[2], cells[p[2]]).split("-", 1)
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
        ax.set_xlabel("Qubit ratio (baseline / HBMS)")
    ax.set_ylabel("Rounds ratio")


def split(cells, benches, path):
    fig, ax = plt.subplots(figsize=(COL, 2.1))
    pf = split_points(ax, cells, benches, "D0-alt", "D3-k1-fact", FILL["HBM"], "o",
                      (0.03, 0.05), {"Ising-26": (-4, 0, "right")},
                      "Planar-2D / HBMS Dedicated (factories)")
    pc = split_points(ax, cells, benches, "D2-wide", "D3-k1", FILL["HBM-Cult"], "s",
                      (0.03, 0.05), {"all 11 circuits": (-6, -9, "left")},
                      "2D-Cult / HBMS Dedicated (cultivation)")
    xs, ys = [p[0] for p in pf + pc], [p[1] for p in pf + pc]
    split_frame(ax, xs, ys, pad=(0.08, 0.3, 0.1, 0.1))
    ax.text(0.745, 1.2, "equal STV", fontsize=8, ha="center", va="center", color=INK,
            rotation=-38)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=1, handletextpad=0.3)
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
               {"Ising-26": (4, 2, "left"), "Heis-16, Ising-16": (4, 5, "left")}),
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
            "Markers give the HBMS configuration, from Shared-16 to Dedicated. Above the "
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


LOSS = "#C8553D"  # cells below 1 (HBMS has the higher STV)


def sources_table(cells, benches, path):
    """One column: the STV ratio per circuit (rows, plus GMean) and HBMS configuration
    (columns), factories and cultivation as separate blocks, each shaded in its own hue."""
    blocks = [(FACT[0], FACT[1][::-1], FILL["HBM"], "(a) Factories"),
              (CULT[0], CULT[1], FILL["HBM-Cult"], "(b) Cultivation")]
    rows = [label(b, cells[b]) for b in benches] + ["GMean"]
    ncols = sum(len(s) for _, s, _, _ in blocks)
    gap = 0.45
    fig, ax = plt.subplots(figsize=(COL, 2.8))
    x0 = 0.0
    for base, specs, hue, tag in blocks:
        vals = np.array([ratios(cells, benches, base, s) for s, _ in specs]).T  # circuit x spec
        vals = np.vstack([vals, [gmean(v) for v in vals.T]])
        top = max(np.nanmax(np.log(vals)), np.log(2))
        for i, row in enumerate(vals):
            best = np.nanargmax(row)
            for j, v in enumerate(row):
                lv = np.log(v)
                t = 0.1 + 0.5 * min(1, lv / top) if v >= 1 else 0.1 + 0.45 * min(1, -lv / 1.5)
                face = _mix(hue if v >= 1 else LOSS, t)
                y = i + (0.35 if i == len(rows) - 1 else 0)  # GMean row set apart
                ax.add_patch(plt.Rectangle((x0 + j, y), 1, 1, facecolor=face, edgecolor="white",
                                           lw=0.8))
                ax.text(x0 + j + 0.5, y + 0.52, f"{v:.2f}", ha="center", va="center",
                        fontsize=8, color=INK,
                        fontweight="bold" if j == best else "normal")
        for j, (_, lab) in enumerate(specs):
            ax.text(x0 + j + 0.5, -0.15, lab, rotation=55, ha="left", va="bottom", fontsize=8,
                    rotation_mode="anchor")
        ax.text(x0 + len(specs) / 2, len(rows) + 0.75, tag, ha="center", va="top", fontsize=8)
        x0 += len(specs) + gap
    for i, name in enumerate(rows):
        y = i + (0.35 if i == len(rows) - 1 else 0)
        ax.text(-0.15, y + 0.52, name, ha="right", va="center", fontsize=8)
    ax.set_xlim(-2.2, ncols + gap + 0.05)
    ax.set_ylim(len(rows) + 0.8, -2.3)
    ax.axis("off")
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("STV of the planar baseline divided by that of HBMS with the same kind of "
            "magic-state resource, per circuit (rows), as the geometric mean (GMean), and per "
            "HBMS configuration (columns, ordered by magic-state resources per data slot): (a) "
            "Planar-2D over HBMS Shared-16 to Dedicated, all with factories, and (b) 2D-Cult "
            "over HBMS Dedicated to Full, all with cultivation patches. Shaded in the block's "
            "colour: above 1, HBMS has the lower STV. Shaded red: below 1. Bold: the HBMS "
            "configuration with the lowest STV on that row, within each block. " + D_NOTE + STAR)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..",
                                                  "figures", "revision"))
    ap.add_argument("--fmt", default="pdf,png")
    ap.add_argument("--pprime", type=float, default=1, help="vertical links at p' = m p")
    args = ap.parse_args()
    cells, benches = load(args.csv, fit=args.pprime)
    os.makedirs(args.out, exist_ok=True)
    paths = lambda n: [os.path.join(args.out, f"{n}.{f}") for f in args.fmt.split(",")]  # noqa
    with open(os.path.join(args.out, "eval_captions.md"), "w") as f:
        for name, fn in [("eval_stv", eval_stv), ("eval_split", eval_split), ("split", split),
                         ("split_s2", split_s2), ("sources_fact", sources_fact),
                         ("sources_cult", sources_cult), ("sources_table", sources_table)]:
            f.write(f"**{name}.pdf.** {fn(cells, benches, paths(name))}\n\n")
    print("wrote", os.path.normpath(args.out))


if __name__ == "__main__":
    main()
