"""RQ4 figure: the cross-layer merge with noisy vertical couplings, and what it does to STV.

  python plot_seam.py RESULTS_DIR REV_CSV [--out figures/revision] [--fmt pdf,png]

RESULTS_DIR holds lattice_surgery/seam_merge.py's seam_d<d>.csv (d = 3..11 are fitted, d = 13
is drawn as a check of the fit). REV_CSV is analyze.py's CSV of the compiler runs.

  seam_merge  (two columns) (a), (b) logical error per merge (zz or xx failure) against the
              physical error rate p, for coupling error p' = 5p and 10p on the 2d - 1
              cross-layer CNOTs only, with p' = p in gray: points with binomial error bars, the
              fit A (p / p_th)^((d + 1) / 2) over d = 3..11 (solid over the simulated p, dashed
              down to 1e-4), d = 13 as a check of the fit; the fitted threshold (dotted). (c) The
              geometric-mean STV ratio (planar baseline over HBMS) against p' / p, every run at
              the smallest odd d that meets the 1% target with the seam fit.
"""

import argparse
import csv
import math
import os
import sys

import matplotlib.ticker as mticker
import numpy as np

from fit_d import refit
from plot_results import COL, FILL, FULL, GRID, INK, MUTED, plt, shade

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "lattice_surgery"))
import seam_merge  # noqa: E402

# Per code distance, the colours and markers of the earlier LER figure (Okabe-Ito); the d = 13
# check in black, the in-plane reference (p' = p) in gray, as that figure's "planar 2D".
D_STYLE = {3: ("#0072B2", "o"), 5: ("#E69F00", "s"), 7: ("#009E73", "^"), 9: ("#CC79A7", "D"),
           11: ("#D55E00", "v"), 13: ("#000000", "o")}
REF = "#999999"
FIT_DS, CHECK_D = (3, 5, 7, 9, 11), 13
MS = (1, 5, 10)
PAIRS = [("D0-alt", "D3-k1-fact", "Factories, Dedicated", FILL["HBM"], "o"),
         ("D0-alt", "D3-s2-fact-bottom", "Factories, Shared-2", shade(FILL["HBM"], 1, 2), "s"),
         ("D2-wide", "D3-full-bottom", "Cultivation, Full", FILL["HBM-Cult"], "D")]
P, A0, PTH0, TARGET = 1e-3, 0.1, 0.01, 0.01  # analyze.py's in-plane model and error target


def union(rows):
    """{(mode, m, d, p): (P, sigma, errors)}: either the zz or the xx experiment fails."""
    by = {}
    for r in rows:
        by.setdefault((r["mode"], r["m"], r["d"], r["p"]), {})[r["basis"]] = r
    out = {}
    for key, b in by.items():
        if "zz" not in b or "xx" not in b:
            continue
        ps, vs = [], []
        for r in b.values():
            n = max(r["shots"] - r["discards"], 1)
            q = r["errors"] / n
            ps.append(q)
            vs.append(q * (1 - q) / n)
        out[key] = (1 - (1 - ps[0]) * (1 - ps[1]), math.sqrt(sum(vs)),
                    b["zz"]["errors"] + b["xx"]["errors"])
    return out


def fit(u, mode, m, pmax=5e-3, min_errors=20):
    """(A, p_th) of P = A (p / p_th)^((d + 1) / 2) over d = 3..11, as seam_merge.py --fit."""
    pts = [((d + 1) / 2, math.log(v[0]) - (d + 1) / 2 * math.log(p))
           for (md, mm, d, p), v in u.items()
           if md == mode and mm == m and d in FIT_DS and p <= pmax and v[2] >= min_errors
           and v[0] > 0]
    b0, b1 = seam_merge.fit_line(pts)
    return math.exp(b0), math.exp(-b1)


def d_need(r, pth_v, a_v):
    """analyze.py's smallest odd d under the 1% target, with the seam at (a_v, pth_v)."""
    e_src = float(r["e_source"])
    if e_src > TARGET:
        return ""
    eps = lambda d, x, a=A0: a * (P / x) ** ((d + 1) / 2)  # noqa: E731
    n, steps = float(r["N"]), float(r["steps"])
    tiles = float(r["t_path_tiles"]) + float(r["cx_path_tiles"])
    v = float(r["vertical_merges"])
    for d in range(3, 101, 2):
        if (n * steps + tiles) * d * eps(d, PTH0) + v * d * eps(d, pth_v, a_v) + e_src <= TARGET:
            return str(d)
    return ""


def stv_ratios(rev, fits, mode):
    """{label: [geomean STV ratio at each m]}, the seam scaled as seam_merge.py --fit does:
    analyze.py's in-plane (A, p_th) at m = 1, moved by the fitted ratios at m > 1."""
    a1, t1 = fits[(mode, 1.0)]
    out = {lab: [] for _, _, lab, _, _ in PAIRS}
    for m in MS:
        a, t = fits[(mode, float(m))]
        col = f"d_need_{m}p"
        rows = [dict(r, **{col: d_need(r, PTH0 * t / t1, A0 * a / a1)}) for r in rev]
        cells = {(r["bench"], r["spec"]): r for r in refit(rows, m)}
        benches = sorted({b for b, _ in cells})
        for base, spec, lab, _, _ in PAIRS:
            v = [float(cells[(b, base)]["STV"]) / float(cells[(b, spec)]["STV"]) for b in benches]
            out[lab].append(math.exp(sum(map(math.log, v)) / len(v)))
    return out


def seam_figure(u, fits, ratios, path):
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.15),
                             gridspec_kw=dict(width_ratios=[1, 1, 1.1], wspace=0.38))
    ds = sorted({k[2] for k in u})
    for ax, m, tag in zip(axes, MS[1:], "ab"):
        a, pth = fits[("seam", float(m))]
        lo = np.logspace(-4, -3, 20)  # the fit below the simulated p: a prediction
        hi = np.logspace(-3, math.log10(pth), 30)  # the fit over the simulated p
        for d in FIT_DS:  # the in-plane merge (p' = p) for reference
            pts = sorted((p, v[0]) for (md, mm, dd, p), v in u.items()
                         if md == "seam" and mm == 1 and dd == d and v[0] > 0)
            ax.plot([p for p, _ in pts], [y for _, y in pts], ls="--", lw=0.7, color=REF,
                    marker=D_STYLE[d][1], ms=2.6, mfc="white", mec=REF, mew=0.5, zorder=1,
                    label="$p' = p$ (in-plane)" if d == FIT_DS[0] else None)
        for d in ds:
            pts = sorted((p, v) for (md, mm, dd, p), v in u.items()
                         if md == "seam" and mm == m and dd == d and v[0] > 0)
            if not pts:
                continue
            color, mk = D_STYLE[d]
            check = d == CHECK_D
            x = [p for p, _ in pts]
            y = np.array([v[0] for _, v in pts])
            e = np.array([v[1] for _, v in pts])
            ax.errorbar(x, y, yerr=[np.minimum(e, y * 0.9), e], fmt=mk, ms=3.4, mfc="white",
                        mec=color, mew=0.9, ecolor=color, elinewidth=0.6, capsize=0, zorder=3,
                        label=f"$d = {d}$" + (" (check)" if check else ""))
            law = lambda q: a * (q / pth) ** ((d + 1) / 2)  # noqa: E731
            ax.plot(hi, law(hi), color=color, lw=1.0, ls="--" if check else "-", zorder=2)
            ax.plot(lo, law(lo), color=color, lw=0.8, ls="--", zorder=2)
        ax.axvline(pth, color=MUTED, lw=0.7, ls=":", zorder=1)
        ax.text(pth * 1.08, 2e-12, f"$p_{{th}} = {pth * 1e3:.1f}\\times10^{{-3}}$",
                ha="left", va="bottom", fontsize=7, color=MUTED, rotation=90)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(1e-4, 1.6e-2)
        ax.set_ylim(1e-12, 1)
        ax.yaxis.set_major_locator(mticker.LogLocator(numticks=7))
        ax.set_xlabel("Physical error rate $p$")
        ax.grid(True, which="major", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.text(0.0, 1.03, f"({tag}) coupling error $p' = {m}p$", transform=ax.transAxes,
                fontsize=8, va="bottom", ha="left")
    axes[0].set_ylabel("Logical error per merge")
    h, lab = axes[0].get_legend_handles_labels()
    ref = lab.index("$p' = p$ (in-plane)")  # d first, then the fit, then the reference
    h, lab = h[:ref] + h[ref + 1:], lab[:ref] + lab[ref + 1:]
    h += [plt.Line2D([], [], color=INK, lw=1.0), plt.Line2D([], [], color=INK, lw=0.8, ls="--"),
          axes[0].get_legend_handles_labels()[0][ref]]
    lab += ["fit", "fit, beyond the data", "$p' = p$ (in-plane)"]
    fig.legend(h, lab, loc="lower center", bbox_to_anchor=(0.35, 0.99), ncol=5, fontsize=7,
               handletextpad=0.3, columnspacing=0.9, labelspacing=0.25)
    ax = axes[2]
    for (_, _, lab, color, mk) in PAIRS:
        ax.plot(MS, ratios["seam"][lab], color=color, marker=mk, ms=4, lw=1.1, label=lab)
    ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(mticker.FixedLocator(MS))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlim(0.8, 12.5)
    ax.set_ylim(0, 5)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Coupling error $p'/p$")
    ax.set_ylabel("STV ratio, planar / HBMS")
    ax.text(0.0, 1.03, "(c) STV ratio (geometric mean)", transform=ax.transAxes, fontsize=8,
            va="bottom", ha="left")
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", bbox_to_anchor=(0.84, 0.99), ncol=1, fontsize=6.5,
               handlelength=1.6, handletextpad=0.3, labelspacing=0.2)
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("(a), (b) Logical error per lattice-surgery merge across a vertical coupling "
            "(a wrong merge outcome or a logical flip of the merged patch) against the "
            "physical error rate p, with error p' = 5p or 10p on the 2d - 1 cross-layer CNOTs "
            "per round and p everywhere else. Markers: simulation, with binomial error bars. "
            "Solid lines: the fit A (p/p_th)^((d+1)/2) over d = 3 to 11. Dashed: the fit below "
            "the simulated p, and its prediction for d = 13 (black markers, not fitted). "
            "Dotted: the fitted threshold. Gray: the same merge with p' = p. (c) Geometric-mean "
            "STV of the planar baseline over that of HBMS against p'/p, every run at the "
            "smallest odd code distance that meets the program-error target.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="directory with seam_merge.py's seam_d<d>.csv")
    ap.add_argument("rev", help="analyze.py's CSV of the compiler runs")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..",
                                                  "figures", "revision"))
    ap.add_argument("--fmt", default="pdf,png")
    args = ap.parse_args()
    files = [os.path.join(args.results, f"seam_d{d}.csv") for d in FIT_DS + (CHECK_D,)]
    u = union(seam_merge.load([f for f in files if os.path.exists(f)]))
    fits = {(mode, float(m)): fit(u, mode, float(m)) for mode in ("seam",) for m in MS}
    for (mode, m), (a, t) in sorted(fits.items()):
        print(f"{mode:5s} m={m:<4g} A={a:.3g} p_th={t:.3g}  "
              f"A/A(1)={a / fits[(mode, 1.0)][0]:.2f}  p_th/p_th(1)={t / fits[(mode, 1.0)][1]:.3f}")
    rev = list(csv.DictReader(open(args.rev)))
    ratios = {mode: stv_ratios(rev, fits, mode) for mode in ("seam",)}
    for mode in ratios:
        for lab, v in ratios[mode].items():
            print(f"{mode:5s} {lab:22s} " + "  ".join(f"{m}p: {x:.2f}" for m, x in zip(MS, v)))
    os.makedirs(args.out, exist_ok=True)
    paths = [os.path.join(args.out, f"seam_merge.{f}") for f in args.fmt.split(",")]
    caption = seam_figure(u, fits, ratios, paths)
    with open(os.path.join(args.out, "seam_caption.md"), "w") as f:
        f.write(f"**seam_merge.pdf.** {caption}\n")
    print("wrote", paths[0])


if __name__ == "__main__":
    main()
