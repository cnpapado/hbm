"""Draw a revision design (lower plane and top layer) to check the layout by eye.

Usage: python draw_design.py SPEC N OUT.png      e.g. python draw_design.py D3-k1 16 d3k1.png
Physical parameters come from the HBM_* env vars (see wisq/src/wisq/designs.py).
"""

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Patch, Rectangle  # noqa: E402

from wisq.designs import build_arch, parse_design  # noqa: E402

DATA, ROUTE, SOURCE, FACTORY, EDGE = "#1f5fae", "#d9d9d9", "#ee8a3c", "#f8c9a0", "#3a3a3a"


def draw_plane(ax, arch, x0, kinds, dots):
    w, h = arch["width"], arch["height"]
    gap = 0.14
    for p in range(w * h):
        r, c = divmod(p, w)
        kind = kinds.get(p, "route")
        x, y = x0 + c + gap / 2, h - 1 - r + gap / 2
        if kind == "empty":
            ax.add_patch(Rectangle((x, y), 1 - gap, 1 - gap, facecolor="white",
                                   edgecolor="#bdbdbd", linestyle=":", linewidth=0.6))
        else:
            color = {"data": DATA, "route": ROUTE, "source": SOURCE, "factory": FACTORY}[kind]
            ax.add_patch(Rectangle((x, y), 1 - gap, 1 - gap, facecolor=color, edgecolor=EDGE,
                                   linewidth=0.6))
        if p in dots:
            ax.add_patch(Circle((x + (1 - gap) / 2, y + (1 - gap) / 2), 0.16, color=DATA))


def main():
    spec, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    design = parse_design(spec)
    arch = build_arch(design, n)
    acct = arch["design"]
    data = set(arch["alg_qubits"])
    sources = set(arch["magic_states"])

    lower = {p: "data" for p in data}
    lower.update({p: "factory" for p in arch["blocked"]})
    if design.placement == "plane":
        lower.update({p: "source" for p in sources})

    w, h = arch["width"], arch["height"]
    layers = 1
    if design.placement == "top":
        layers = 2
        default = "route" if design.top_routing_layer else "empty"
        top = {p: default for p in range(w * h)}
        top.update({p: "factory" for p in arch["blocked_top"]})
        top.update({p: "source" for p in sources})

    fig, ax = plt.subplots(figsize=(max(5, 0.42 * (w * layers + 2)), max(3.5, 0.42 * h + 1.6)))
    draw_plane(ax, arch, 0, lower, set())
    ax.text(w / 2, -0.6, "lower (data) plane", ha="center", va="top", fontsize=8)
    if layers == 2:
        draw_plane(ax, arch, w + 2, top, data)
        ax.text(w + 2 + w / 2, -0.6, "top layer (dots: above a data qubit)", ha="center",
                va="top", fontsize=8)
    ax.set_xlim(-0.3, w * layers + 2 * (layers - 1) + 0.3)
    ax.set_ylim(-1.6, h + 1.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        f"{spec}, N={n}, d={acct['d']}: {acct['lower_tiles']} lower + {acct['top_tiles']} top "
        f"tiles, {acct['n_sources']} sources, {acct['n_factories']} factories "
        f"({acct['factory_tiles']} tiles each), recharge {acct['recharge_steps']} steps",
        fontsize=8, loc="left")
    ax.legend(handles=[Patch(facecolor=DATA, label="data"), Patch(facecolor=ROUTE, label="routing"),
                       Patch(facecolor=SOURCE, label="source (port / patch)"),
                       Patch(facecolor=FACTORY, label="factory")],
              loc="upper right", bbox_to_anchor=(1, 0), ncol=4, frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(out)


if __name__ == "__main__":
    main()
