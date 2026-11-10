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
"""

import argparse
import os

import matplotlib.ticker as mticker
import numpy as np

from plot_results import (COL, FILL, GRID, INK, MUTED, STAR, gmean, label, load, num, plt,
                          shade)

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
        for name, fn in [("eval_stv", eval_stv), ("eval_split", eval_split)]:
            f.write(f"**{name}.pdf.** {fn(cells, benches, paths(name))}\n\n")
    print("wrote", os.path.normpath(args.out))


if __name__ == "__main__":
    main()
