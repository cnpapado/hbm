"""RQ4 figure: the cross-layer merge with noisy vertical couplings, and what it does to STV.

  python plot_seam.py RESULTS_DIR REV_CSV [--out figures/revision] [--fmt pdf,png]

RESULTS_DIR holds lattice_surgery/seam_merge.py's seam_d<d>.csv (d = 3..11 are fitted, d = 13
is drawn as a check of the fit). REV_CSV is analyze.py's CSV of the compiler runs.

  seam_merge  (two columns) (a), (b) logical error per merge (zz or xx failure) against the
              physical error rate p, for coupling error p' = 5p and 10p on the 2d - 1
              cross-layer CNOTs only: points with binomial error bars, the
              fit A (p / p_th)^((d + 1) / 2) over d = 3..11 (solid over the simulated p, dashed
              down to 1e-4), d = 13 as a check of the fit; the fitted threshold (dotted). (c) The
              geometric-mean STV ratio (planar baseline over HBMS) against p' / p = 1..100,
              every run at the smallest odd d that meets the 1% target, each vertical merge at
              r_m(d) times its in-plane error, r_m from the simulations at p = 1e-3 (fitted over
              d = 5..11); triangles where the ratio crosses 1.
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
# check in black.
D_STYLE = {3: ("#0072B2", "o"), 5: ("#E69F00", "s"), 7: ("#009E73", "^"), 9: ("#CC79A7", "D"),
           11: ("#D55E00", "v"), 13: ("#000000", "o")}
FIT_DS, CHECK_D = (3, 5, 7, 9, 11), 13
MS = (1, 5, 10)  # p' / p in the threshold fits
MS_STV = (1, 5, 10, 20, 50, 100)  # p' / p in the STV panel
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


def ratio_fit(u, ms, ds=(5, 7, 9, 11)):
    """{m: r_m}, r_m(d) = merge error at p' = m p over that at p' = p, both at the operating
    point p = 1e-3: log P = a_m + b_m (d + 1) / 2 fitted over d = 5..11 for each m."""
    ab = {}
    for m in ms:
        pts = [((d + 1) / 2, math.log(u[("seam", float(m), d, P)][0])) for d in ds]
        ab[m] = seam_merge.fit_line(pts)
    return {m: (lambda d, m=m: math.exp(ab[m][0] - ab[1][0]
                                        + (ab[m][1] - ab[1][1]) * (d + 1) / 2)) for m in ms}


def d_need(r, rm):
    """analyze.py's smallest odd d under the 1% target, the vertical merges at r_m(d) times
    their in-plane error (Eq. 3)."""
    e_src = float(r["e_source"])
    if e_src > TARGET:
        return ""
    eps = lambda d: A0 * (P / PTH0) ** ((d + 1) / 2)  # noqa: E731
    n, steps = float(r["N"]), float(r["steps"])
    tiles = float(r["t_path_tiles"]) + float(r["cx_path_tiles"])
    v = float(r["vertical_merges"])
    for d in range(3, 201, 2):
        if (n * steps + tiles + v * rm(d)) * d * eps(d) + e_src <= TARGET:
            return str(d)
    return ""


def stv_ratios(rev, rms):
    """{label: [geomean STV ratio at each m]} with every run at its own d."""
    out = {lab: [] for _, _, lab, _, _ in PAIRS}
    for m in MS_STV:
        rows = [dict(r, d_need_1p=d_need(r, rms[m])) for r in rev]
        cells = {(r["bench"], r["spec"]): r for r in refit(rows, 1)}
        benches = sorted({b for b, _ in cells})
        for base, spec, lab, _, _ in PAIRS:
            v = [float(cells[(b, base)]["STV"]) / float(cells[(b, spec)]["STV"]) for b in benches]
            out[lab].append(math.exp(sum(map(math.log, v)) / len(v)))
    return out


def break_even(ratios):
    """{label: p'/p where the ratio crosses 1}, log-log interpolation between sampled m."""
    out = {}
    for lab, v in ratios.items():
        for (m0, r0), (m1, r1) in zip(zip(MS_STV, v), zip(MS_STV[1:], v[1:])):
            if r0 >= 1 > r1:
                f = math.log(r0) / (math.log(r0) - math.log(r1))
                out[lab] = math.exp(math.log(m0) + f * (math.log(m1) - math.log(m0)))
                break
    return out


def seam_figure(u, fits, ratios, be, path):
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.15),
                             gridspec_kw=dict(width_ratios=[1, 1, 1.1], wspace=0.38))
    ds = sorted({k[2] for k in u})
    for ax, m, tag in zip(axes, MS[1:], "ab"):
        a, pth = fits[("seam", float(m))]
        lo = np.logspace(-4, -3, 20)  # the fit below the simulated p: a prediction
        hi = np.logspace(-3, math.log10(pth), 30)  # the fit over the simulated p
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
                ha="left", va="bottom", fontsize=8, color=MUTED, rotation=90)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(1e-4, 1.6e-2)
        ax.set_ylim(1e-12, 1)
        ax.yaxis.set_major_locator(mticker.LogLocator(numticks=7))
        ax.set_xlabel("Physical error rate $p$")
        ax.grid(True, which="major", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.text(0.0, 1.03, f"({tag}) Coupling error $p' = {m}p$", transform=ax.transAxes,
                fontsize=8, va="bottom", ha="left")
    axes[0].set_ylabel("Logical error per merge")
    h, lab = axes[0].get_legend_handles_labels()
    h += [plt.Line2D([], [], color=INK, lw=1.0), plt.Line2D([], [], color=INK, lw=0.8, ls="--")]
    lab += ["fit", "fit, beyond the data"]
    fig.legend(h, lab, loc="lower center", bbox_to_anchor=(0.35, 0.99), ncol=4, fontsize=8,
               handletextpad=0.3, columnspacing=0.9, labelspacing=0.25)
    ax = axes[2]
    for (_, _, lab, color, mk) in PAIRS:
        ax.plot(MS_STV, ratios[lab], color=color, marker=mk, ms=4, lw=1.1, label=lab)
        if lab in be:  # where HBMS stops winning
            ax.plot(be[lab], 1, marker="v", ms=5, color=color, mec=INK, mew=0.4, zorder=5)
    ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(mticker.FixedLocator(MS_STV))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlim(0.8, 125)
    ax.set_ylim(0, 6)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Coupling error $p'/p$")
    ax.set_ylabel("STV ratio")
    ax.text(0.0, 1.03, "(c) Baseline / HBMS, GMean", transform=ax.transAxes, fontsize=8,
            va="bottom", ha="left")
    ax.legend(loc="upper right", fontsize=8, handlelength=1.6, handletextpad=0.3,
              labelspacing=0.2)  # inside, as in the other evaluation figures
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)
    return ("(a), (b) Logical error per lattice-surgery merge across a vertical coupling "
            "(a wrong merge outcome or a logical flip of the merged patch) against the "
            "physical error rate p, with error p' = 5p or 10p on the 2d - 1 cross-layer CNOTs "
            "per round and p everywhere else. Markers: simulation, with binomial error bars. "
            "Solid lines: the fit A (p/p_th)^((d+1)/2) over d = 3 to 11. Dashed: the fit below "
            "the simulated p, and its prediction for d = 13 (black markers, not fitted). "
            "Dotted: the fitted threshold. (c) Geometric-mean "
            "STV of the planar baseline over that of HBMS against p'/p, every run at the "
            "smallest odd code distance that meets the program-error target, with each merge "
            "across a vertical coupling at the error simulated at p = 10^-3 relative to "
            "p' = p. Triangles: where the ratio crosses 1.")


M_STYLE = {1: ("#B0B0B0", "o"), 5: ("#8C8C8C", "s"), 10: ("#6A6A6A", "^"),  # p'/p, light to dark
           20: ("#484848", "D"), 50: ("#262626", "v"), 100: ("#000000", "P")}


def seam_column(u, fits, ratios, be, path, m=10):
    """One column, two panels. (a) Merge error against p at p' = m p: simulation, the fit
    A (p / p_th)^((d + 1) / 2) over d = 3..11, dashed below the simulated p, the d = 13 check,
    and the fitted thresholds at p' = m p (black) and p' = p (gray). (b) The geometric-mean STV
    ratio against p'/p, with its crossings of 1."""
    fig, axes = plt.subplots(2, 1, figsize=(COL, 3.7), gridspec_kw=dict(hspace=0.5))
    ax = axes[0]
    a, pth = fits[("seam", float(m))]
    pth1 = fits[("seam", 1.0)][1]
    lo = np.logspace(-4, -3, 20)  # the fit below the simulated p: a prediction
    hi = np.logspace(-3, math.log10(pth), 30)
    for d in sorted({k[2] for k in u}):
        pts = sorted((q, v) for (md, mm, dd, q), v in u.items()
                     if md == "seam" and mm == m and dd == d and v[0] > 0)
        if not pts:
            continue
        color, mk = D_STYLE[d]
        check = d == CHECK_D
        y = np.array([v[0] for _, v in pts])
        e = np.array([v[1] for _, v in pts])
        ax.errorbar([q for q, _ in pts], y, yerr=[np.minimum(e, y * 0.9), e], fmt=mk, ms=3.2,
                    mfc="white", mec=color, mew=0.9, ecolor=color, elinewidth=0.6, capsize=0,
                    zorder=3, label=f"$d = {d}$" + (" (check)" if check else ""))
        law = lambda q: a * (q / pth) ** ((d + 1) / 2)  # noqa: E731
        ax.plot(hi, law(hi), color=color, lw=1.0, ls="--" if check else "-", zorder=2)
        ax.plot(lo, law(lo), color=color, lw=0.8, ls="--", zorder=2)
    for t, c, lab in ((pth, INK, f"$p_{{th}}$, ${m}p$"), (pth1, "#9A9A9A", "$p_{th}$, $p$")):
        ax.axvline(t, ymin=0.58, color=c, lw=0.8, ls=":", zorder=1, label=lab)  # above the legend
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-4, 1.6e-2)
    ax.set_ylim(1e-12, 1)
    ax.yaxis.set_major_locator(mticker.FixedLocator([1e-12, 1e-9, 1e-6, 1e-3, 1]))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.grid(True, which="major", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Physical error rate $p$")
    ax.set_ylabel("Error per merge")
    ax.text(0.0, 1.03, f"(a) Coupling error $p' = {m}p$", transform=ax.transAxes, fontsize=8,
            va="bottom", ha="left")
    h, lab = ax.get_legend_handles_labels()
    order = [lab.index(x) for x in lab if x.startswith("$d")] + \
        [lab.index(x) for x in lab if x.startswith("$p_")]
    ax.legend([h[i] for i in order], [lab[i] for i in order], loc="lower right", ncol=2,
              fontsize=8, handletextpad=0.2, columnspacing=0.6, labelspacing=0.15,
              borderaxespad=0.2, handlelength=1.1)
    ax = axes[1]
    for (_, _, lab, color, mk) in PAIRS:
        ax.plot(MS_STV, ratios[lab], color=color, marker=mk, ms=4, lw=1.1, label=lab)
        if lab in be:  # where HBMS stops winning
            ax.plot(be[lab], 1, marker="v", ms=5, color=color, mec=INK, mew=0.4, zorder=5)
    ax.axhline(1, color=INK, lw=0.7, ls="--", zorder=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(mticker.FixedLocator(MS_STV))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlim(0.8, 125)
    ax.set_ylim(0, 6)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Coupling error $p'/p$")
    ax.set_ylabel("STV ratio")
    ax.text(0.0, 1.03, "(b) Baseline / HBMS, GMean", transform=ax.transAxes, fontsize=8,
            va="bottom", ha="left")
    ax.legend(loc="upper right", fontsize=8, handlelength=1.6, handletextpad=0.3,
              labelspacing=0.2)
    for p_ in ([path] if isinstance(path, str) else path):
        fig.savefig(p_)
    plt.close(fig)
    return ("(a) Logical error per lattice-surgery merge across a vertical coupling against "
            "the physical error rate $p$, with error $p' = 10p$ on the $2d - 1$ cross-layer "
            "CNOTs per round and $p$ everywhere else. Markers: simulation, with binomial error "
            "bars. Solid lines: the fit $A\\,(p/p_{\\mathrm{th}})^{(d+1)/2}$ over $d = 3$ to 11. "
            "Dashed: the fit below the simulated $p$, and its prediction for $d = 13$ (black "
            "markers, not fitted). Dotted: the fitted threshold at $p' = 10p$ (black) and at "
            "$p' = p$ (gray). "
            "(b) STV of the planar baseline divided by that of HBMS, geometric mean over the "
            "circuits, against $p'/p$, every run at the smallest odd code distance that meets "
            "the program-error target with the merge error of (a). Triangles: where the ratio "
            "crosses 1.")


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
    ratios = stv_ratios(rev, ratio_fit(u, MS_STV))
    be = break_even(ratios)
    for lab, v in ratios.items():
        print(f"{lab:22s} " + "  ".join(f"{m}p: {x:.2f}" for m, x in zip(MS_STV, v))
              + (f"  break-even {be[lab]:.0f}p" if lab in be else ""))
    os.makedirs(args.out, exist_ok=True)
    paths = [os.path.join(args.out, f"seam_merge.{f}") for f in args.fmt.split(",")]
    caption = seam_figure(u, fits, ratios, be, paths)
    col = [os.path.join(args.out, f"seam_stv.{f}") for f in args.fmt.split(",")]
    col_caption = seam_column(u, fits, ratios, be, col)
    with open(os.path.join(args.out, "seam_caption.md"), "w") as f:
        f.write(f"**seam_merge.pdf.** {caption}\n\n**seam_stv.pdf.** {col_caption}\n")
    print("wrote", paths[0])


if __name__ == "__main__":
    main()
