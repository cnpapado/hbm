"""More evaluation figures for the Lower-First paper, from analyze.py's CSV and the seam
simulation (no new runs).

  python plot_eval2.py rev_all.csv RESULTS_SEAM --qasm ../../test/benchmarks_real \
      [--out ../../figures/revision] [--fmt pdf,png]

  tradeoff  (one column) qubits (x) and rounds (y) of the planar baseline over HBMS, geometric
            means over the circuits, a marker per configuration joined in resource order, with
            lines of equal STV ratio.
  roofline  (one column, two panels) per run: the magic-state supply bound over the ideal depth
            (x) against the timesteps over the ideal depth (y), with the lines y = x (supply)
            and y = 1 (dependencies).
  budget    (one column, two panels) the terms of Eq. 3 at each run's code distance, as
            fractions of the 1% target, mean over the circuits, per configuration, at p' = p and
            p' = 10p.
  tornado   (one column) geometric-mean STV ratio of three configurations when one constant of
            the error model changes at a time.

The supply bound counts how many timesteps the magic-state resources need to hand out the
circuit's T states, ignoring routing and dependencies: a factory hands out one T state per
timestep, a cultivation patch one per 1 + ceil(R / d) timesteps, and every resource starts the run
holding a T state, so k T states from one resource need (k - 1) periods plus one step. A resource
that serves a single
data qubit (Dedicated, and 2D-Cult's patch beside each qubit) must serve that qubit's T gates in
turn, so the bound uses the largest per-qubit T count; shared resources use the circuit's T count
over their number. Timesteps and the bound are taken at the simulated d.
"""

import argparse
import csv
import glob
import math
import os
import re
from collections import Counter

import matplotlib.ticker as mticker
import numpy as np
from matplotlib.lines import Line2D

import plot_seam as ps
import seam_merge
from fit_d import refit
from plot_eval import CULT, FACT, HATCHES, ratios
from plot_results import (COL, FILL, GRID, INK, MUTED, gmean, label, load, num, plt, ramp,
                          to_cells)

KINDS = [("HBM", FACT, "(a) Factories: Planar-2D / HBMS"),
         ("HBM-Cult", CULT, "(b) Cultivation: 2D-Cult / HBMS")]
MARKS = ("o", "s", "^", "D")
BASE_COLOUR = {"D0-alt": "#808080", "D2-wide": "#F0A33A"}  # Planar-2D, 2D-Cult
DEDICATED = {"D3-k1-fact", "D3-k1", "D2-wide"}  # one resource per data qubit
TARGET = 0.01


def save(fig, path):
    for p in ([path] if isinstance(path, str) else path):
        fig.savefig(p)
    plt.close(fig)


# ---------------------------------------------------------------- trade-off

def tradeoff(cells, benches, path):
    fig, ax = plt.subplots(figsize=(COL, 2.7))
    lo, hi = 0.15, 8
    xx = np.logspace(math.log10(lo), math.log10(hi), 50)
    for c in (0.25, 0.5, 1, 2, 4, 8):  # equal STV ratio: x * y = c
        ax.plot(xx, c / xx, color=GRID if c != 1 else INK, lw=0.7 if c != 1 else 0.8,
                ls="-" if c != 1 else "--", zorder=0)
        y = c / hi * 1.6
        if lo < hi / 1.6 and lo <= c / (hi / 1.6) <= hi:
            ax.text(hi / 1.6, c / (hi / 1.6), f"{c:g}$\\times$", fontsize=8, color=MUTED,
                    ha="left", va="bottom")
    ax.plot(1, 1, marker="*", ms=8, color="#9A9A9A", mec=INK, mew=0.4, zorder=4)
    ax.annotate("planar\nbaseline", (1, 1), xytext=(-5, -4), textcoords="offset points",
                fontsize=8, ha="right", va="top", color=MUTED)
    for fam, (base, specs), _ in KINDS:
        q = [gmean(ratios(cells, benches, base, s, "Q")) for s, _ in specs]
        r = [gmean(ratios(cells, benches, base, s, "rounds")) for s, _ in specs]
        ax.plot(q, r, color=FILL[fam], lw=1.0, zorder=2)
        for k, (s, lab) in enumerate(specs):
            ax.plot(q[k], r[k], marker=MARKS[k], ms=5, color=ramp(fam, k, len(specs)),
                    mec=INK, mew=0.4, ls="", zorder=3)
            ax.annotate(lab, (q[k], r[k]), xytext=(5, 0), textcoords="offset points",
                        fontsize=8, va="center", ha="left", color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.3, 4)
    ax.set_ylim(lo, hi)
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        axis.set_minor_formatter(mticker.NullFormatter())
    ax.xaxis.set_major_locator(mticker.FixedLocator([0.5, 1, 2]))
    ax.yaxis.set_major_locator(mticker.FixedLocator([0.25, 0.5, 1, 2, 4]))
    ax.set_xlabel("Qubits, baseline / HBMS")
    ax.set_ylabel("Rounds, baseline / HBMS")
    handles = [Line2D([], [], color=FILL["HBM"], lw=1.0, label="Factories"),
               Line2D([], [], color=FILL["HBM-Cult"], lw=1.0, label="Cultivation"),
               Line2D([], [], color=GRID, lw=0.7, label="equal STV ratio")]
    ax.legend(handles=handles, loc="lower left", fontsize=8, handlelength=1.4)
    save(fig, path)
    return ("Qubits and rounds of the planar baseline over HBMS, geometric means over the "
            "circuits, per HBMS configuration. Gray lines: equal STV ratio. Up and to the right "
            "favours HBMS.")


# ---------------------------------------------------------------- roofline

def t_per_qubit(qasm_dir):
    """{bench: (total T, largest per-qubit T)} from the circuit files."""
    out = {}
    for f in (glob.glob(os.path.join(qasm_dir, "ising_eps1e-2", "*.qasm"))  # the real1 set only
              + glob.glob(os.path.join(qasm_dir, "heisenberg_eps1e-2", "*.qasm"))):
        cnt = Counter()
        for line in open(f):
            m = re.match(r"\s*(t|tdg)\s+\w+\[(\d+)\]", line)
            if m:
                cnt[int(m.group(2))] += 1
        out[os.path.basename(f)[:-5]] = (sum(cnt.values()), max(cnt.values()) if cnt else 0)
    return out


def supply_bound(c, tq):
    """Timesteps the magic-state resources need to hand out the circuit's T states."""
    n_t, t_max = tq
    period = 1 if c["source"] == "factory" else 1 + math.ceil(int(c["recharge_rounds"]) /
                                                              int(c["d_sim"]))
    k = t_max if c["spec"] in DEDICATED else math.ceil(n_t / int(c["n_sources"]))
    return (k - 1) * period + 1  # every resource starts the run holding a T state


def _line_angle(ax, x0, x1):
    """Screen angle (degrees) of the line y = x between x0 and x1 on log-log axes."""
    p0, p1 = ax.transData.transform([(x0, x0), (x1, x1)])
    return math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))


def roofline(cells13, benches, tq, path):
    fig, axes = plt.subplots(2, 1, figsize=(COL, 4.3), gridspec_kw=dict(hspace=0.42))
    lo, hi, ylo = 0.3, 40, 0.85
    tags = ("(a) Factories: Planar-2D and HBMS", "(b) Cultivation: 2D-Cult and HBMS")
    for ax, (fam, (base, specs), _), tag in zip(axes, KINDS, tags):
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lo, hi)
        ax.set_ylim(ylo, hi)
        # what no run can reach: below both the ideal depth and the supply bound
        xx = np.logspace(math.log10(lo), math.log10(hi), 200)
        ax.fill_between(xx, ylo, np.maximum(1, xx), color="#EFEFEF", lw=0, zorder=0)
        ax.plot([lo, hi], [lo, hi], color=INK, lw=0.8, ls="--", zorder=1)
        ax.axhline(1, color=INK, lw=0.8, ls=":", zorder=1)
        series = [(base, "Planar-2D" if base == "D0-alt" else "2D-Cult", BASE_COLOUR[base], "X")]
        series += [(s_, lab, ramp(fam, k, len(specs)), MARKS[k]) for k, (s_, lab) in
                   enumerate(specs)]
        for spec, lab, colour, mk in series:
            pts = []
            for bn in benches:
                c = cells13[bn].get(spec)
                if not c:
                    continue
                ideal = num(c["ideal_depth"])
                pts.append((supply_bound(c, tq[bn]) / ideal, num(c["steps"]) / ideal))
            hollow = spec in BASE_COLOUR  # the baseline on top, hollow: 2D-Cult hides Dedicated
            ax.scatter([q[0] for q in pts], [q[1] for q in pts], s=26 if hollow else 16,
                       marker="o" if hollow else mk, facecolor="none" if hollow else colour,
                       edgecolor=colour if hollow else INK, linewidth=1.0 if hollow else 0.3,
                       zorder=4 if hollow else 3, label=lab)
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
            axis.set_minor_formatter(mticker.NullFormatter())
        ax.xaxis.set_major_locator(mticker.FixedLocator([0.5, 1, 2, 5, 10, 20]))
        ax.yaxis.set_major_locator(mticker.FixedLocator([1, 2, 5, 10, 20]))
        ax.grid(True, which="major", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_ylabel("Timesteps / ideal depth")
        ax.text(0.0, 1.03, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
        # the two bounds, named on the plot
        ax.text(7, 1.07, "ideal depth", fontsize=8, ha="left", va="bottom", color=INK)
        ang = _line_angle(ax, 12, 30)
        ax.text(14, 14 / 1.25, "supply bound", fontsize=8, ha="center", va="top",
                rotation=ang, rotation_mode="anchor", color=INK)  # below the line: no markers
        ax.text(38, 2.4, "below both bounds:\nunreachable", fontsize=8, ha="right",
                va="bottom", color=MUTED)
        ax.legend(loc="upper left", fontsize=8, ncol=2, handletextpad=0.2, columnspacing=0.6,
                  labelspacing=0.2, borderaxespad=0.3, frameon=False)
    axes[0].annotate("above both bounds:\ntime on paths\nto the ring", xy=(1.3, 1.85),
                     xytext=(0.33, 3.3), fontsize=8, ha="left", va="center", color=INK,
                     arrowprops=dict(arrowstyle="->", color=INK, lw=0.7))
    axes[1].annotate("", xy=(1.0, 3.3), xytext=(9, 30),  # parallel to the bound, above it
                     arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
    axes[1].text(0.33, 5.5, "more patches\nper data slot", fontsize=8, ha="left", va="center",
                 color=INK)
    axes[-1].set_xlabel("Magic-state supply bound / ideal depth")
    save(fig, path)
    return ("Timesteps against the magic-state supply bound, both over the ideal depth, one "
            "marker per circuit and configuration: (a) with factories, (b) with cultivation "
            "patches. No run can fall below both lines.")


# ---------------------------------------------------------------- error budget

TERMS = [("idle", "Idle data", "#5E5E5E", None), ("route", "Routing paths", "#B4B4B4", None),
         ("vert", "Vertical merges", "#C51B7D", None), ("magic", "Magic states", "#FFFFFF",
                                                         "//////")]


def eq3_terms(r, rm, d, A=ps.A0, p=ps.P, pth=ps.PTH0):
    e = A * (p / pth) ** ((d + 1) / 2)
    return dict(idle=float(r["N"]) * float(r["steps"]) * d * e,
                route=(float(r["t_path_tiles"]) + float(r["cx_path_tiles"])) * d * e,
                vert=float(r["vertical_merges"]) * rm(d) * d * e,
                magic=float(r["e_source"]))


def budget(rev, rms, path, ms=(1, 10)):
    specs = []
    for fam, (base, sp), _ in KINDS:
        specs += [(base, "Planar-2D" if base == "D0-alt" else "2D-Cult")] + list(sp)
    fig, axes = plt.subplots(2, 1, figsize=(COL, 3.6), sharex=True,
                             gridspec_kw=dict(hspace=0.35))
    x = np.arange(len(specs)) + np.array([0] * 5 + [0.6] * 5)  # a gap between the kinds
    for ax, m in zip(axes, ms):
        frac = {k: [] for k, *_ in TERMS}
        for spec, _ in specs:
            rows = [r for r in rev if r["spec"] == spec and r.get("status") == "ok"]
            acc = {k: [] for k, *_ in TERMS}
            for r in rows:
                d = ps.d_need(r, rms[m])
                if not d:
                    continue
                t = eq3_terms(r, rms[m], int(d))
                for k in acc:
                    acc[k].append(t[k] / TARGET)
            for k in acc:
                frac[k].append(np.mean(acc[k]))
        bottom = np.zeros(len(specs))
        for k, lab, colour, hatch in TERMS:
            v = np.array(frac[k])
            ax.bar(x, v, 0.7, bottom=bottom, color=colour, edgecolor=INK, linewidth=0.3,
                   hatch=hatch, label=lab)
            bottom += v
        ax.axhline(1, color=INK, lw=0.7, ls="--")
        ax.set_ylim(0, 1.25)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(0.25))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_ylabel("Share of target")
        tag = "(a) $p' = p$" if m == 1 else f"(b) $p' = {m}p$"
        ax.text(0.0, 1.03, tag, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    axes[0].legend(loc="upper left", ncol=4, fontsize=8, handlelength=1.0, handletextpad=0.3,
                   columnspacing=0.6, borderaxespad=0.2)
    axes[-1].set_xticks(x, [lab for _, lab in specs], rotation=45, ha="right",
                        rotation_mode="anchor")
    axes[-1].tick_params(axis="x", length=0)
    save(fig, path)
    return ("Terms of Eq. 3 at each run's code distance, as shares of the 1% target, mean over "
            "the circuits, per configuration (factories left, cultivation right): (a) "
            "$p' = p$, (b) $p' = 10p$.")


# ---------------------------------------------------------------- tornado

def stv_ratio_under(rev, rm, base, spec, A, pth, target):
    """Geometric-mean STV ratio with every run at its own d under changed constants."""
    def dneed(r):
        e_src = float(r["e_source"])
        if e_src > target:
            return ""
        for d in range(3, 201, 2):
            t = eq3_terms(r, rm, d, A=A, pth=pth)
            if t["idle"] + t["route"] + t["vert"] + e_src <= target:
                return str(d)
        return ""
    rows = [dict(r, d_need_1p=dneed(r)) for r in rev]
    cells, benches = to_cells(refit(rows, 1))
    v = ratios(cells, benches, base, spec)
    return gmean(v[~np.isnan(v)]) if np.any(~np.isnan(v)) else float("nan")


VARIANTS = [("$A$ = 0.03 / 0.3", dict(A=0.03), dict(A=0.3)),
            ("$p_{\\mathrm{th}}$ = 0.7 / 1.4%", dict(pth=0.007), dict(pth=0.014)),
            ("target = 0.5 / 2%", dict(target=0.005), dict(target=0.02))]
TORNADO = [("D0-alt", "D3-k1-fact", "Factories, Dedicated", "HBM", 0),
           ("D0-alt", "D3-s2-fact-bottom", "Factories, Shared-2", "HBM", 1),
           ("D2-wide", "D3-full-bottom", "Cultivation, Full", "HBM-Cult", 0)]


def tornado(rev, rm1, path):
    base_kw = dict(A=ps.A0, pth=ps.PTH0, target=TARGET)
    rows = []
    for base, spec, lab, fam, k in TORNADO:
        ref = stv_ratio_under(rev, rm1, base, spec, **base_kw)
        for vlab, lo_kw, hi_kw in VARIANTS:
            a = stv_ratio_under(rev, rm1, base, spec, **dict(base_kw, **lo_kw))
            b = stv_ratio_under(rev, rm1, base, spec, **dict(base_kw, **hi_kw))
            rows.append((lab, fam, k, vlab, ref, a, b))
    print("tornado:")
    for lab, _, _, vlab, ref, a, b in rows:
        print(f"  {lab:22s} {vlab:28s} ref {ref:.2f}  low {a:.2f}  high {b:.2f}")
    fig, ax = plt.subplots(figsize=(COL, 2.5))
    y, yt, ylab = 0.0, [], []
    for i, (base, spec, lab, fam, k) in enumerate(TORNADO):
        group = [r for r in rows if r[0] == lab]
        ax.text(1.02, y - 0.35, lab, fontsize=8, ha="left", va="bottom", color=INK,
                transform=ax.get_yaxis_transform())
        for _, _, _, vlab, ref, a, b in group:
            lo_, hi_ = min(a, b, ref), max(a, b, ref)
            ax.barh(y, hi_ - lo_, left=lo_, height=0.55, color=ramp(fam, 1 + k, 4),
                    edgecolor=INK, linewidth=0.3)
            ax.plot([ref, ref], [y - 0.38, y + 0.38], color=INK, lw=1.1)
            yt.append(y)
            ylab.append(vlab)
            y += 0.8
        y += 0.6
    ax.set_yticks(yt, ylab)
    ax.tick_params(axis="y", length=0)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(1, 6)
    ax.xaxis.set_major_locator(mticker.FixedLocator([1, 1.5, 2, 3, 4, 5]))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.grid(True, axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("STV ratio, baseline / HBMS")
    save(fig, path)
    return rows


# ---------------------------------------------------------------- RQ4 map

MAP_P = (1e-3, 1.5e-3, 2e-3)  # in-plane error rates with seam data for every p'/p
MAP_PAIRS = [("D0-alt", "D3-k1-fact", "Factories, Dedicated", "HBM"),
             ("D0-alt", "D3-s2-fact-bottom", "Factories, Shared-2", "HBM"),
             ("D2-wide", "D3-full-bottom", "Cultivation, Full (grade fixed)", "HBM-Cult")]


def ratio_fit_at(u, ms, p, ds=(5, 7, 9, 11)):
    """r_m(d) at in-plane error p: the seam fit of log P against (d + 1) / 2 relative to m = 1."""
    ab = {}
    for m in ms:
        pts = [((d + 1) / 2, math.log(u[("seam", float(m), d, p)][0])) for d in ds]
        ab[m] = seam_merge.fit_line(pts)
    return {m: (lambda d, m=m: math.exp(ab[m][0] - ab[1][0] + (ab[m][1] - ab[1][1]) * (d + 1) / 2))
            for m in ms}


def map_ratio(rev, rm, p, base, spec):
    """Geometric-mean STV ratio with every run at its own d at in-plane error p. Factory output
    error scales as 35 p^3, cultivation grades stay at their p = 1e-3 values."""
    def dneed(r):
        e_src = float(r["e_source"])
        if r["source"] == "factory":
            e_src *= (p / ps.P) ** 3
        if e_src > TARGET:
            return ""
        for d in range(3, 301, 2):
            t = eq3_terms(r, rm, d, p=p)
            if t["idle"] + t["route"] + t["vert"] + e_src <= TARGET:
                return str(d)
        return ""
    rows = [dict(r, d_need_1p=dneed(r)) for r in rev if r["spec"] in (base, spec)]
    cells, benches = to_cells(refit(rows, 1))
    v = ratios(cells, benches, base, spec)
    return gmean(v[~np.isnan(v)]) if np.any(~np.isnan(v)) else float("nan")


def rq4_map(rev, u, path):
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    grid = {}
    for p in MAP_P:
        rms = ratio_fit_at(u, ps.MS_STV, p)
        for base, spec, lab, fam in MAP_PAIRS:
            grid[(lab, p)] = [map_ratio(rev, rms[m], p, base, spec) for m in ps.MS_STV]
    print("RQ4 map (rows p, columns p'/p):")
    for base, spec, lab, fam in MAP_PAIRS:
        for p in MAP_P:
            print(f"  {lab:32s} p={p:.1e} " + " ".join(f"{v:5.2f}" for v in grid[(lab, p)]))
    fig, axes = plt.subplots(len(MAP_PAIRS), 1, figsize=(COL, 3.4), sharex=True,
                             gridspec_kw=dict(hspace=0.55))
    for ax, (base, spec, lab, fam) in zip(axes, MAP_PAIRS):
        vals = np.array([grid[(lab, p)] for p in MAP_P])
        cmap = LinearSegmentedColormap.from_list(
            "c", [(0.55, 0.55, 0.55), (1, 1, 1), FILL[fam]])  # gray below 1, kind colour above
        span = math.log(8)
        ax.pcolormesh(np.arange(len(ps.MS_STV) + 1), np.arange(len(MAP_P) + 1),
                      np.log(vals), cmap=cmap, norm=Normalize(-span, span), edgecolors="white",
                      linewidth=0.8)
        for i in range(len(MAP_P)):
            for j in range(len(ps.MS_STV)):
                v = vals[i, j]
                ax.text(j + 0.5, i + 0.5, f"{v:.2f}", ha="center", va="center", fontsize=8,
                        color=INK, fontweight="bold" if v >= 1 else "normal")
        ax.set_yticks(np.arange(len(MAP_P)) + 0.5, [f"{p * 1e3:g}" for p in MAP_P])
        ax.set_ylabel("$p$ ($10^{-3}$)")
        ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.text(0.0, 1.04, lab, transform=ax.transAxes, fontsize=8, va="bottom", ha="left")
    axes[-1].set_xticks(np.arange(len(ps.MS_STV)) + 0.5, [f"{m:g}" for m in ps.MS_STV])
    axes[-1].set_xlabel("Coupling error $p'/p$")
    save(fig, path)
    return grid


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rev", help="analyze.py's CSV (real1 rev_all.csv)")
    ap.add_argument("seam", help="seam_merge.py results directory")
    ap.add_argument("--qasm", required=True, help="benchmarks_real directory")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..",
                                                  "figures", "revision"))
    ap.add_argument("--fmt", default="pdf,png")
    ap.add_argument("--only", nargs="+",
                    default=["tradeoff", "roofline", "budget", "tornado", "rq4map"])
    args = ap.parse_args()
    out = lambda n: [os.path.join(args.out, f"{n}.{f}") for f in args.fmt.split(",")]  # noqa
    os.makedirs(args.out, exist_ok=True)
    rev = list(csv.DictReader(open(args.rev)))
    cells, benches = load(args.rev, fit=1)
    files = [os.path.join(args.seam, f"seam_d{d}.csv") for d in ps.FIT_DS + (ps.CHECK_D,)]
    u = ps.union(seam_merge.load([f for f in files if os.path.exists(f)]))
    rms = ps.ratio_fit(u, ps.MS_STV)
    if "tradeoff" in args.only:
        tradeoff(cells, benches, out("tradeoff"))
    if "roofline" in args.only:
        cells13, b13 = load(args.rev)
        roofline(cells13, b13, t_per_qubit(args.qasm), out("roofline"))
    if "budget" in args.only:
        budget(rev, rms, out("budget"))
    if "tornado" in args.only:
        tornado(rev, rms[1], out("tornado"))
    if "rq4map" in args.only:
        rq4_map(rev, u, out("rq4map"))
    print("wrote", os.path.normpath(args.out))


if __name__ == "__main__":
    main()
