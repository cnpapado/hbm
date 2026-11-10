"""Schematic paper figures, drawn at their printed size (same style as plot_results.py).

  python draw_schematics.py [--out figures/revision] [--fmt pdf,png]

  design_space       (one column) the four evaluated designs for N = 16, from the simulator's
                     own layouts (designs.build_arch): T-state source (factory or cultivation)
                     against placement (data plane or upper layer). Replaces the old Figs. 1, 3.
  cross_layer_merge  (two columns) the Z_D Z_M merge that injects a T state from the upper
                     layer: (a) the merged patch, (b) the same patch folded across the layers,
                     (c) the CNOT order of a cross-layer check. Replaces the old Fig. 2.
  lower_first        (one column) Lower-First routing in Shared-2, N = 4: a T path on the data
                     layer to the ancilla tile below a resource, then one vertical coupling.
  upper_layers       (one column) the upper-layer configurations for N = 16: Dedicated,
                     Shared-2, -4, -8; replaces the old layered-organization and top-layer figures.
  captions.md        a caption per figure: what it shows, no findings.

The merge figure is built from a rotated-surface-code construction that this script checks
before drawing (merge_code, schedule): the checks commute and are independent, the Z checks
that touch the gap column G multiply to Z_D Z_M, and the CNOT order (Z checks NW NE SW SE,
X checks NW SW NE SE) touches each qubit once per layer, measures commuting checks correctly
and keeps hook errors perpendicular to the logical of the same type.
"""

import argparse
import math
import os
import sys
import types

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, Patch, Polygon, Rectangle  # noqa: E402

from plot_results import COL, FULL, INK, MUTED  # noqa: E402  (also sets the rcParams)

HERE = os.path.dirname(os.path.abspath(__file__))
# designs.py needs only architecture.py; a bare package skips wisq/__init__ (qiskit).
_pkg = types.ModuleType("wisq")
_pkg.__path__ = [os.path.join(HERE, "..", "..", "wisq", "src", "wisq")]
sys.modules.setdefault("wisq", _pkg)
from wisq.designs import build_arch, parse_design  # noqa: E402

DATA, ROUTE, SOURCE, EDGE = "#1F5FAE", "#DCDCDC", "#EE8A3C", "#3A3A3A"
LINK = "#C51B7D"  # vertical couplings and cross-layer checks
XCHK, ZCHK = "#E4E4E4", "#93A9C9"  # X and Z checks: light and dark, grayscale-safe
CULT_HATCH = "////"  # cultivation, as HBM-Cult in plot_results.py
SLANT, DEPTH = 0.5, 0.42  # oblique view: x shift and height per unit of depth


def oblique(x, y, z=0.0):
    """(x, y, z) -> page coordinates: y runs into the page, z up."""
    return x + SLANT * y, DEPTH * y + z


# ---------------------------------------------------------------- design space

def tile(ax, x, y, z, color, hatch=None, lw=0.35):
    pts = [oblique(x + a, y + b, z) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=EDGE, linewidth=lw,
                         hatch=hatch, zorder=2 + z))


def draw_layout(ax, arch, source, top, lift):
    """One design, its lower plane at the origin; an upper-layer design gets its top layer
    `lift` above. Returns the drawing's page extent (x0, x1, y0, y1)."""
    w, h = arch["width"], arch["height"]
    data, sources = set(arch["alg_qubits"]), set(arch["magic_states"])
    src = (SOURCE, CULT_HATCH if source == "cultivation" else None)

    def xy(p):
        r, c = divmod(p, w)
        return c, h - 1 - r  # row 0 at the back

    for p in range(w * h):
        x, y = xy(p)
        tile(ax, x, y, 0, DATA if p in data else src[0] if not top and p in sources else ROUTE,
             hatch=src[1] if not top and p in sources and p not in data else None)
    if top:
        for p in data:  # vertical coupling from each data tile to the tile above it
            x, y = xy(p)
            (a, b), (_, c) = oblique(x + .5, y + .5, 0), oblique(x + .5, y + .5, lift)
            ax.plot([a, a], [b, c], color=LINK, lw=0.9, zorder=2.5, solid_capstyle="butt")
        for p in range(w * h):  # the upper layer holds only the sources (Lower-First)
            if p in sources:
                x, y = xy(p)
                tile(ax, x, y, lift, *src)
    return 0, w + SLANT * h, 0, DEPTH * h + (lift if top else 0)


def design_space(path, n=16):
    """2 x 2: rows factory / cultivation, columns in the data plane / on an upper layer, every
    cell at the same scale."""
    cells = {(0, 0): ("D0-alt", "Planar-2D"), (0, 1): ("D3-k1-fact", "HBM"),
             (1, 0): ("D2-wide", "2D-Cult"), (1, 1): ("D3-k1", "HBM-Cult")}
    lift, unit = 4.6, 0.095  # inches per tile
    fig = plt.figure(figsize=(COL, 2.55))
    left, gap, cell_w = 0.17, 0.08, None
    cell_w = (COL - left - gap) / 2
    row_h, title_h, top_h = 0.86, 0.17, 0.52  # inches
    for (ri, ci), (spec, label) in cells.items():
        design = parse_design(spec, d=13)
        arch = build_arch(design, n)
        x_in = left + ci * (cell_w + gap)
        y_in = 2.55 - top_h - (ri + 1) * (row_h + title_h) + 0.02
        ax = fig.add_axes((x_in / COL, y_in / 2.55, cell_w / COL, row_h / 2.55))
        x0, x1, y0, y1 = draw_layout(ax, arch, design.source, design.placement == "top", lift)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ax.set_xlim(cx - cell_w / unit / 2, cx + cell_w / unit / 2)
        ax.set_ylim(cy - row_h / unit / 2, cy + row_h / unit / 2)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.text((x_in + cell_w / 2) / COL, (y_in + row_h + 0.015) / 2.55, label,
                 ha="center", va="bottom", fontsize=8, fontweight="bold")
    for ri, text in enumerate(["Factories", "Cultivation"]):
        y_in = 2.55 - top_h - (ri + 1) * (row_h + title_h) + 0.02 + (row_h + title_h) / 2
        fig.text(0.06 / COL, y_in / 2.55, text, rotation=90, ha="center", va="center",
                 fontsize=8, color=MUTED)
    for ci, text in enumerate(["In the data plane", "On an upper layer"]):
        fig.text((left + ci * (cell_w + gap) + cell_w / 2) / COL, (2.55 - top_h + 0.04) / 2.55,
                 text, ha="center", va="bottom", fontsize=8, color=MUTED)
    handles = [Patch(facecolor=DATA, edgecolor=EDGE, lw=0.4, label="Data qubit"),
               Patch(facecolor=ROUTE, edgecolor=EDGE, lw=0.4, label="Routing tile"),
               Patch(facecolor=SOURCE, edgecolor=EDGE, lw=0.4, label="Factory port"),
               Patch(facecolor=SOURCE, edgecolor=EDGE, lw=0.4, hatch=CULT_HATCH,
                     label="Cultivation patch"),
               Line2D([], [], color=LINK, lw=1.0, label="Vertical coupling")]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0),
               handlelength=1.1, columnspacing=0.8)
    save(fig, path)


# ---------------------------------------------------------------- cross-layer merge

def kind(i, j):
    return "X" if (i + j) % 2 == 0 else "Z"


def patch_checks(x0, x1, d):
    """Rotated-surface-code checks on columns x0..x1, rows 0..d-1, on one global checkerboard.
    Left and right edges keep weight-2 X checks, top and bottom weight-2 Z checks, so Z_L is
    a column, parallel to the left and right edges (the edges a Z Z merge joins)."""
    out = []
    for i in range(x0 - 1, x1 + 1):
        for j in range(-1, d):
            qs = frozenset((x, y) for x in (i, i + 1) for y in (j, j + 1)
                           if x0 <= x <= x1 and 0 <= y < d)
            k, lr = kind(i, j), i in (x0 - 1, x1)
            if len(qs) == 4 or (len(qs) == 2 and (k == "X") == lr):
                out.append((k, (i + .5, j + .5), qs))
    return out


def _rank(vecs):
    basis = []
    for v in vecs:
        for b in basis:
            v = min(v, v ^ b)
        if v:
            basis.append(v)
    return len(basis)


def _check_code(checks, qubits):
    for a in checks:
        for b in checks:
            assert a[0] == b[0] or len(a[2] & b[2]) % 2 == 0, (a, b)
    idx = {q: k for k, q in enumerate(qubits)}
    vecs = [sum(1 << idx[q] for q in qs) << (len(qubits) if k == "Z" else 0)
            for k, _, qs in checks]
    assert _rank(vecs) == len(checks) == len(qubits) - 1


def merge_code(d):
    """The Z_D Z_M merge: data patch D (columns 0..d-1), gap column G (d, prepared in |+>),
    T-state patch M (d+1..2d). Returns the merged checks and the qubit groups, after checking
    the construction."""
    D = [(x, y) for x in range(d) for y in range(d)]
    G = [(d, y) for y in range(d)]
    M = [(x, y) for x in range(d + 1, 2 * d + 1) for y in range(d)]
    cd, cm, merged = patch_checks(0, d - 1, d), patch_checks(d + 1, 2 * d, d), \
        patch_checks(0, 2 * d, d)
    _check_code(cd, D)
    _check_code(cm, M)
    _check_code(merged, D + G + M)
    old, g = {qs for _, _, qs in cd + cm}, set(G)
    prod = set()
    for k, _, qs in merged:
        if qs & g and k == "X":
            assert qs - g in old  # an old boundary check times X on |+>: deterministic
        if qs & g and k == "Z":
            prod ^= qs  # new checks, random one by one
    assert prod == {(d - 1, y) for y in range(d)} | {(d + 1, y) for y in range(d)}
    return merged, D, G, M


OFF = {"NW": (-.5, .5), "NE": (.5, .5), "SW": (-.5, -.5), "SE": (.5, -.5)}
ORDER = {"Z": ("NW", "NE", "SW", "SE"), "X": ("NW", "SW", "NE", "SE")}


def cnot_times(check):
    k, (cx, cy), qs = check
    out = {}
    for t, o in enumerate(ORDER[k]):
        q = (round(cx + OFF[o][0]), round(cy + OFF[o][1]))
        if q in qs:
            out[q] = t
    return out


def schedule(checks):
    """Check ORDER on these checks and return each check's CNOT times."""
    times = [(c, cnot_times(c)) for c in checks]
    used = set()
    for _, t in times:
        for q, s in t.items():
            assert (q, s) not in used
            used.add((q, s))
    for cz, tz in times:
        for cx, tx in times:
            if cz[0] == "Z" and cx[0] == "X":
                shared = cz[2] & cx[2]
                assert sum(tx[q] < tz[q] for q in shared) % 2 == 0
    return times


def draw_check(ax, check, page, color, edge=None, lw=0.4, z=1):
    """A weight-4 check as its square, a weight-2 check as a half disc bulging towards the
    check's centre (outside the patch). page maps flat (x, y) to the page."""
    k, (cx, cy), qs = check
    if len(qs) == 4:
        x0, y0 = cx - .5, cy - .5
        pts = [page(x0, y0), page(x0 + 1, y0), page(x0 + 1, y0 + 1), page(x0, y0 + 1)]
    else:
        (ax_, ay), (bx, by) = sorted(qs)
        mx, my = (ax_ + bx) / 2, (ay + by) / 2
        ux, uy = bx - ax_, by - ay  # along the edge, length 1
        nx, ny = 2 * (cx - mx), 2 * (cy - my)  # towards the centre, length 1
        arc = [math.pi * t / 16 for t in range(17)]
        pts = [page(mx + .5 * (math.cos(a) * ux + math.sin(a) * nx),
                    my + .5 * (math.cos(a) * uy + math.sin(a) * ny)) for a in arc]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=edge or EDGE,
                         linewidth=lw, zorder=z))


def merge_panel(ax, d, merged, D, G, M):
    """(a) The merged patch, flat."""
    cross = [c for c in merged if c[2] & set(D) and c[2] & set(G)]
    page = lambda x, y: (x, y)  # noqa: E731
    for c in merged:
        draw_check(ax, c, page, XCHK if c[0] == "X" else ZCHK)
    for c in cross:
        draw_check(ax, c, page, XCHK if c[0] == "X" else ZCHK, edge=LINK, lw=1.3, z=1.5)
    for group, face in ((D, DATA), (G, "white"), (M, SOURCE)):
        for q in group:
            ax.add_patch(Circle(q, 0.13, facecolor=face, edgecolor=INK,
                                lw=0.6 if face == "white" else 0.4, zorder=3))
    for x, text in ((d / 2 - .5, "D"), (d, "G"), (1.5 * d + .5, "M")):
        ax.text(x, -0.75, text, ha="center", va="top", fontsize=8)
    ax.set_xlim(-0.8, 2 * d + 0.8)
    ax.set_ylim(-1.5, d - 0.1)
    ax.set_aspect("equal")
    ax.axis("off")


def fold_panel(ax, d, merged, D, G, M, lift=2.6):
    """(b) The merged patch folded at the seam: D on the lower layer, G and M on the upper
    layer, M directly above D (Dedicated). The upper layer is mirrored, x -> 2d - x, and a
    cross-layer check spans from D's last column (lower) to G (upper)."""
    gs, ds = set(G), set(D)

    def page(x, y):
        if x <= d - 1:
            return oblique(x, y, 0)
        if x >= d:
            return oblique(2 * d - x, y, lift)
        t = x - (d - 1)
        (ax_, ay), (bx, by) = oblique(d - 1, y, 0), oblique(d, y, lift)
        return ax_ + t * (bx - ax_), ay + t * (by - ay)

    for z, xs in ((0, (-0.7, d - 0.3)), (lift, (-0.7, d + 0.7))):  # layer outlines
        pts = [oblique(xs[0], -0.7, z), oblique(xs[1], -0.7, z), oblique(xs[1], d - 0.3, z),
               oblique(xs[0], d - 0.3, z)]
        ax.add_patch(Polygon(pts, closed=True, facecolor="none", edgecolor=MUTED, lw=0.5,
                             linestyle=(0, (2, 1.5)), zorder=0))
    lower = [c for c in merged if c[2] <= ds]
    upper = [c for c in merged if not c[2] & ds]
    cross = [c for c in merged if c[2] & ds and c[2] & gs]
    for c in lower:
        draw_check(ax, c, page, XCHK if c[0] == "X" else ZCHK, z=1)
    for c in cross:
        draw_check(ax, c, page, XCHK if c[0] == "X" else ZCHK, edge=LINK, lw=1.3, z=2)
    for c in upper:
        draw_check(ax, c, page, XCHK if c[0] == "X" else ZCHK, z=3)
    for group, face, z in ((D, DATA, 2.2), (G, "white", 4), (M, SOURCE, 4)):
        for q in group:
            ax.add_patch(Circle(page(*q), 0.13, facecolor=face, edgecolor=INK,
                                lw=0.6 if face == "white" else 0.4, zorder=z))
    for z, text in ((0, "Lower layer"), (lift, "Upper layer")):
        tx, ty = oblique(-0.7, -0.7, z)
        ax.text(tx, ty - 0.12, text, ha="left", va="top", fontsize=8, color=MUTED)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.autoscale_view()


def circuit(ax, y0, check_kind, title):
    """One cross-layer check of the given type, its ancilla on the lower layer. Wires: the
    ancilla (labelled with its initial state), two D qubits (lower layer) and two G qubits
    (upper layer)."""
    wire = {"NW": "d2", "SW": "d1", "NE": "g2", "SE": "g1"}  # D west of the seam, G east
    names = ["a", "d1", "d2", "g1", "g2"]
    label = {"a": r"$|0\rangle$" if check_kind == "Z" else r"$|+\rangle$", "d1": "D",
             "d2": "D", "g1": "G", "g2": "G"}
    ys = {nm: y0 - k * 0.42 for k, nm in enumerate(names)}
    x_start, x_end = 0.75, 4.75
    for nm in names:
        ax.plot([x_start, x_end if nm != "a" else x_end - 0.02], [ys[nm]] * 2, color=INK,
                lw=0.5, zorder=1)
        ax.text(x_start - 0.1, ys[nm], label[nm], ha="right", va="center", fontsize=8)
    for t, o in enumerate(ORDER[check_kind]):
        x = 1.35 + 0.85 * t
        tgt = wire[o]
        cross = tgt.startswith("g")
        color = LINK if cross else INK
        ctrl, targ = (tgt, "a") if check_kind == "Z" else ("a", tgt)
        ax.plot([x, x], [ys[ctrl], ys[targ]], color=color, lw=1.3 if cross else 0.8, zorder=2)
        ax.add_patch(Circle((x, ys[ctrl]), 0.06, color=color, zorder=3))
        ax.add_patch(Circle((x, ys[targ]), 0.12, facecolor="white", edgecolor=color,
                            lw=1.0 if cross else 0.7, zorder=3))
        ax.plot([x - 0.12, x + 0.12], [ys[targ]] * 2, color=color, lw=0.7, zorder=4)
        ax.plot([x, x], [ys[targ] - 0.12, ys[targ] + 0.12], color=color, lw=0.7, zorder=4)
    ax.add_patch(Polygon([(x_end, ys["a"] - 0.19), (x_end + 0.5, ys["a"] - 0.19),
                          (x_end + 0.5, ys["a"] + 0.19), (x_end, ys["a"] + 0.19)],
                         closed=True, facecolor="white", edgecolor=INK, lw=0.6, zorder=3))
    ax.text(x_end + 0.25, ys["a"], check_kind, ha="center", va="center", fontsize=8,
            zorder=4)
    ax.text(x_start - 0.75, y0 + 0.3, title, ha="left", va="bottom", fontsize=8)


def schedule_panel(ax, merged, D, G):
    cross = [c for c in merged if c[2] & set(D) and c[2] & set(G)]
    times = dict((c, t) for c, t in schedule(merged))
    for c in cross:  # the drawn wires assume D west and G east of each cross-layer check
        assert all((q in set(D)) == (q[0] < c[1][0]) for q in times[c])
    circuit(ax, 0.0, "Z", "Z check")
    circuit(ax, -2.6, "X", "X check")
    ax.set_xlim(-0.1, 5.4)
    ax.set_ylim(-4.45, 0.7)
    ax.axis("off")


def cross_layer_merge(path, d=3):
    merged, D, G, M = merge_code(d)
    schedule(merged)
    fig = plt.figure(figsize=(FULL, 1.9))
    axes = [fig.add_axes(r) for r in ((0.0, 0.15, 0.36, 0.7), (0.37, 0.13, 0.31, 0.74),
                                      (0.71, 0.13, 0.27, 0.74))]
    merge_panel(axes[0], d, merged, D, G, M)
    fold_panel(axes[1], d, merged, D, G, M)
    schedule_panel(axes[2], merged, D, G)
    for ax, x, text in ((axes[0], 0.18, "(a) Merged patch"),
                        (axes[1], 0.525, "(b) Folded across the layers"),
                        (axes[2], 0.855, "(c) CNOT order of a cross-layer check")):
        fig.text(x, 0.02, text, ha="center", va="bottom", fontsize=8)
    handles = [Patch(facecolor=XCHK, edgecolor=EDGE, lw=0.4, label="X check"),
               Patch(facecolor=ZCHK, edgecolor=EDGE, lw=0.4, label="Z check"),
               Patch(facecolor="white", edgecolor=LINK, lw=1.3, label="Cross-layer check"),
               Line2D([], [], marker="o", ls="", markerfacecolor=DATA, markeredgecolor=INK,
                      markeredgewidth=0.4, markersize=5, label="Data patch D (lower)"),
               Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=INK,
                      markeredgewidth=0.6, markersize=5, label="Gap G (upper)"),
               Line2D([], [], marker="o", ls="", markerfacecolor=SOURCE, markeredgecolor=INK,
                      markeredgewidth=0.4, markersize=5, label="T-state patch M (upper)")]
    fig.legend(handles=handles, loc="upper center", ncol=6, bbox_to_anchor=(0.5, 1.0),
               handlelength=1.1, columnspacing=1.0)
    save(fig, path)


# ---------------------------------------------------------------- output

# ---------------------------------------------------------------- Lower-First routing

PATH = "#8FD3C1"  # ancilla tiles on a T path


def t_path(arch, q, target):
    """Shortest path of free ancilla tiles from a tile on q's vertical (Z) side to `target`,
    as the router searches it (design_routing._best_path, BOTTOM)."""
    w, h = arch["width"], arch["height"]
    data = set(arch["alg_qubits"])
    starts = [p for p in (q - w, q + w) if 0 <= p < w * h and p not in data]
    prev, frontier = {s: None for s in starts}, list(starts)
    while frontier and target not in prev:
        nxt = []
        for p in frontier:
            r, c = divmod(p, w)
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                n = rr * w + cc
                if 0 <= rr < h and 0 <= cc < w and n not in data and n not in prev:
                    prev[n] = p
                    nxt.append(n)
        frontier = nxt
    out, p = [], target
    while p is not None:
        out.append(p)
        p = prev[p]
    return out[::-1]


def lower_first(path, n=4):
    """Shared-2 for N = 4 (the simulator's layout), Lower-First: (a) both layers, the upper
    one holding only the two resources; (b) the data layer from above, with the T path from
    q2 to the ancilla tile below M1 and the vertical coupling there."""
    arch = build_arch(parse_design("D3-s2", d=13), n)
    arch = arch[0] if isinstance(arch, tuple) else arch
    w, h = arch["width"], arch["height"]
    data, sources = sorted(arch["alg_qubits"]), sorted(arch["magic_states"])
    q, src = data[1], sources[0]  # the T gate's data qubit (q2) and its resource (M1)
    route = t_path(arch, q, src)
    names = {p: f"q{i + 1}" for i, p in enumerate(data)}
    names.update({p: f"M{i + 1}" for i, p in enumerate(sources)})
    lift, arrow = 3.0, "#16695A"
    head = dict(arrowstyle="-|>", color=arrow, lw=1.3, mutation_scale=7, shrinkA=0, shrinkB=0)

    def xy(p):
        r, c = divmod(p, w)
        return c, h - 1 - r

    H = 2.1
    fig = plt.figure(figsize=(COL, H))
    # (a) both layers
    ax = fig.add_axes((0.0, 0.0, 0.57, 0.76))
    for p in range(w * h):
        x, y = xy(p)
        tile(ax, x, y, 0, DATA if p in data else PATH if p in route else ROUTE)
    corners = [oblique(a_, b_, lift) for a_, b_ in ((0, 0), (w, 0), (w, h), (0, h))]
    ax.add_patch(Polygon(corners, closed=True, facecolor="#F4F4F4", edgecolor=MUTED, lw=0.5,
                         ls=(0, (3, 2)), zorder=2.2))
    for s in sources:
        x, y = xy(s)
        (a_, b_), (_, c_) = oblique(x + .5, y + .5, 0), oblique(x + .5, y + .5, lift)
        ax.plot([a_, a_], [b_, c_], color=LINK, lw=1.4 if s == src else 0.9, zorder=2.6,
                solid_capstyle="butt")
        tile(ax, x, y, lift, SOURCE)
        lx, ly = oblique(x - 0.1, y + .5, lift)
        ax.text(lx, ly, names[s], ha="right", va="center", fontsize=8, zorder=9)
    pts = [oblique(*(v + .5 for v in xy(p))) for p in [q] + route]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=arrow, lw=1.3, zorder=8,
            solid_capstyle="round", solid_joinstyle="round")
    x, y = xy(src)
    ax.annotate("", xy=oblique(x + .5, y + .5, lift - 0.45), xytext=pts[-1], zorder=8,
                arrowprops=head)
    ax.text(*oblique(w - 0.25, h - 0.55, lift), "upper layer", fontsize=8, color=MUTED,
            ha="right", va="center", zorder=9)
    ax.text(*oblique(w, -0.25), "data layer", fontsize=8, color=MUTED, ha="right", va="top")
    ax.set_xlim(-0.6, w + SLANT * h + 0.1)
    ax.set_ylim(-0.75, DEPTH * h + lift + 0.15)
    ax.set_aspect("equal")
    ax.axis("off")
    # (b) the data layer from above
    bx = fig.add_axes((0.61, 0.0, 0.39, 0.74))
    for p in range(w * h):
        x, y = xy(p)
        bx.add_patch(Rectangle((x, y), 1, 1, facecolor=DATA if p in data else
                               PATH if p in route else ROUTE, edgecolor=EDGE, lw=0.4))
        if p in data:
            bx.text(x + .5, y + .5, names[p], ha="center", va="center", fontsize=8,
                    color="white")
    for s in sources:  # the resource above, drawn as an inset outline, with its coupling
        x, y = xy(s)
        bx.add_patch(Rectangle((x + .1, y + .1), .8, .8, facecolor="none", edgecolor=SOURCE,
                               lw=1.3, ls=(0, (2.2, 1.2)), zorder=4))
        bx.add_patch(Circle((x + .5, y + .7), .1, facecolor=LINK, edgecolor="none", zorder=6))
        bx.text(x + .5, y + .33, names[s], ha="center", va="center", fontsize=8, zorder=6)
    cs = [tuple(v + .5 for v in xy(p)) for p in [q] + route]
    end = (cs[-1][0], cs[-1][1] + 0.2 + 0.1)
    bx.plot([c[0] for c in cs[:-1]], [c[1] for c in cs[:-1]], color=arrow, lw=1.3, zorder=5,
            solid_capstyle="round", solid_joinstyle="round")
    bx.annotate("", xy=end, xytext=cs[-2], zorder=5, arrowprops=head)
    bx.set_xlim(-0.05, w + 0.05)
    bx.set_ylim(-0.05, h + 0.05)
    bx.set_aspect("equal")
    bx.axis("off")
    for x_, text in ((0.0, "(a) Both layers"), (0.61, "(b) Data layer, top view")):
        fig.text(x_, 0.765, text, fontsize=8, ha="left", va="bottom")
    handles = [Patch(facecolor=DATA, edgecolor=EDGE, lw=0.4, label="Data qubit"),
               Patch(facecolor=ROUTE, edgecolor=EDGE, lw=0.4, label="Ancilla tile"),
               Patch(facecolor=PATH, edgecolor=EDGE, lw=0.4, label="T path"),
               Patch(facecolor=SOURCE, edgecolor=EDGE, lw=0.4, label="Resource (upper layer)"),
               Line2D([], [], color=LINK, lw=1.2, marker="o", markersize=3.5,
                      label="Vertical coupling")]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.01),
               handlelength=1.2, columnspacing=0.9)
    save(fig, path)


def upper_layers(path, n=16):
    """HBMS's upper-layer configurations for N = 16 (the simulator's layouts), 2 x 2, in the
    style of lower_first: Dedicated, Shared-2, Shared-4 and Full (a cultivation patch on every
    upper tile). The upper layer holds
    only the resources; each has one vertical coupling to the tile below it (Lower-First)."""
    panels = [("D3-k1", "Dedicated"), ("D3-s2", "Shared-2"), ("D3-s4", "Shared-4"),
              ("full", "Full (cultivation)")]
    lift = 4.0
    fig = plt.figure(figsize=(COL, 2.6))
    pw, ph, top = 0.5, 0.425, 0.85  # panel width and height (figure fractions), top edge
    for k, (spec, title) in enumerate(panels):
        arch = build_arch(parse_design("D3-k1" if spec == "full" else spec, d=13), n)
        arch = arch[0] if isinstance(arch, tuple) else arch
        w, h = arch["width"], arch["height"]
        data, sources = set(arch["alg_qubits"]), sorted(arch["magic_states"])
        if spec == "full":  # mati's D3-full: a patch on every upper tile
            sources = list(range(w * h))
        hatch = CULT_HATCH if spec == "full" else None
        col, row = k % 2, k // 2
        ax = fig.add_axes((col * pw, top - (row + 1) * ph, pw, ph - 0.045))

        def xy(p):
            r, c = divmod(p, w)
            return c, h - 1 - r

        for p in range(w * h):
            x, y = xy(p)
            tile(ax, x, y, 0, DATA if p in data else ROUTE, lw=0.3)
        corners = [oblique(a_, b_, lift) for a_, b_ in ((0, 0), (w, 0), (w, h), (0, h))]
        ax.add_patch(Polygon(corners, closed=True, facecolor="#F4F4F4", edgecolor=MUTED,
                             lw=0.5, ls=(0, (3, 2)), zorder=2.2))
        for s_ in sources:
            x, y = xy(s_)
            (a_, b_), (_, c_) = oblique(x + .5, y + .5, 0), oblique(x + .5, y + .5, lift)
            ax.plot([a_, a_], [b_, c_], color=LINK, lw=0.45 if hatch else 0.9, zorder=2.6,
                    solid_capstyle="butt")
            tile(ax, x, y, lift, SOURCE, lw=0.3)
        ax.set_xlim(-0.3, w + SLANT * h + 0.3)
        ax.set_ylim(-0.3, DEPTH * h + lift + 0.15)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.text(col * pw, top - row * ph,
                 f"({'abcd'[k]}) {title}, {len(sources)} " + ("patches" if hatch else "resources"),
                 ha="left", va="top", fontsize=8)
    handles = [Patch(facecolor=DATA, edgecolor=EDGE, lw=0.4, label="Data qubit"),
               Patch(facecolor=ROUTE, edgecolor=EDGE, lw=0.4, label="Ancilla tile"),
               Patch(facecolor=SOURCE, edgecolor=EDGE, lw=0.4, label="Resource (upper layer)"),
               Line2D([], [], color=LINK, lw=1.2, label="Vertical coupling")]
    fig.legend(handles=handles, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.01),
               handlelength=1.2, columnspacing=0.9)
    save(fig, path)


def save(fig, path):
    for p in path:
        fig.savefig(p)
    plt.close(fig)


CAPTIONS = {
    "design_space": (
        "The four evaluated designs for N = 16 logical data qubits, drawn from the "
        "simulator's layouts. Rows: T-state source (15-to-1 distillation factories or "
        "magic-state cultivation). Columns: placement of the sources, in the data plane or "
        "on an upper layer connected by vertical couplings. Planar-2D places a factory port "
        "on every other tile of a ring around the data; 2D-Cult places a cultivation patch "
        "beside each data qubit; HBM and HBM-Cult place one source above each data qubit "
        "(Dedicated) on an upper layer that holds only sources. Factory bodies (11 tiles "
        "each) are not drawn; a cultivation patch is drawn as one tile. Shared-S layouts keep "
        "one upper-layer source per S data qubits, and T gates reach them by routing on the "
        "data layer to the tile below a source (Lower-First)."),
    "lower_first": (
        "Lower-First routing in a Shared-2 configuration of a Square Sparse layout with four "
        "logical data qubits (the simulator's layout): (a) both layers, (b) the data layer "
        "from above. The upper layer holds only the two magic-state resources: M1 above the "
        "ancilla tile between q1 and q2, and M2 between q3 and q4, each with one vertical "
        "coupling to the tile below it. A T gate on q2 routes over free ancilla tiles of the "
        "data layer (the T path), starting next to q2's Z boundary, to the tile below M1, and "
        "merges up through that tile's vertical coupling."),
    "upper_layers": (
        "The HBMS upper-layer configurations for N = 16 logical data qubits, drawn from the "
        "simulator's layouts: (a) Dedicated, one magic-state resource above each data qubit; "
        "(b), (c) Shared-2 and -4, one resource per 2 or 4 data qubits, each above an ancilla "
        "tile of the data layer; (d) Full, a cultivation patch above every tile of the data "
        "layer. The upper layer holds only the resources, and each resource has one vertical "
        "coupling to the tile below it. For factories, the resource drawn is the factory's "
        "output tile; its distillation block sits on further layers above (not drawn). "
        "Shared-8 and Shared-16 follow the pattern of (b) and (c) with 2 and 1 resources."),
    "cross_layer_merge": (
        "Lattice-surgery merge that injects a T state from the upper layer (d = 3). (a) The "
        "merged patch: data patch D, gap column G prepared in |+>, and T-state patch M; the "
        "Z checks that touch G are new during the merge and their product is Z_D Z_M. (b) "
        "The same checks folded at the seam: D on the lower layer, G and M on the upper "
        "layer with M directly above D. Only the checks outlined in magenta involve both "
        "layers. (c) The CNOT order of a cross-layer Z check and X check, measured by an "
        "ancilla on the lower layer; magenta CNOTs use a vertical coupling."),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "figures", "revision"))
    ap.add_argument("--fmt", default="pdf,png")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    fmts = args.fmt.split(",")
    paths = lambda name: [os.path.join(args.out, f"{name}.{f}") for f in fmts]  # noqa: E731
    design_space(paths("design_space"))
    cross_layer_merge(paths("cross_layer_merge"))
    lower_first(paths("lower_first"))
    upper_layers(paths("upper_layers"))
    with open(os.path.join(args.out, "captions.md"), "w") as f:
        for name, text in CAPTIONS.items():
            f.write(f"**{name}.pdf.** {text}\n\n")
    print("wrote", os.path.normpath(args.out))


if __name__ == "__main__":
    main()
