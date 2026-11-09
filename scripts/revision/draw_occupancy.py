"""Draw which lower-plane tiles hold a data qubit, one panel per circuit, from finished runs.

DASCOT pads the data grid to ceil(sqrt(N))^2 slots, so circuits whose qubit count is not a
perfect square leave slots empty. Each panel shows the run's actual placement; the table
printed (and written as CSV) gives the slot and tile usage.

Usage: python draw_occupancy.py OUTS_DIR OUT.png [--spec D3-k1-fact] [--csv usage.csv]
  e.g. python draw_occupancy.py test/runs/real1/outs/real occupancy.png
"""

import argparse
import csv
import glob
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

DATA, ROUTE, EDGE = "#1f5fae", "#d9d9d9", "#3a3a3a"  # as in draw_design.py


def load(outs, spec):
    runs = []
    for f in glob.glob(os.path.join(outs, f"*__{spec}__*.out")):
        d = json.load(open(f))
        a = d["arch"]
        runs.append(dict(
            circuit=os.path.basename(f).split("__")[0], w=a["width"], h=a["height"],
            slots=a["alg_qubits"], placed={int(q): p for q, p in d["map"].items()},
        ))
    return sorted(runs, key=lambda r: (len(r["placed"]), r["circuit"]))


def draw(ax, r):
    w, h, gap = r["w"], r["h"], 0.14
    where = {p: q for q, p in r["placed"].items()}
    slots = set(r["slots"])
    for p in range(w * h):
        row, col = divmod(p, w)
        x, y = col + gap / 2, h - 1 - row + gap / 2
        if p in where:
            ax.add_patch(Rectangle((x, y), 1 - gap, 1 - gap, facecolor=DATA, edgecolor=EDGE,
                                   linewidth=0.5))
            if w <= 13:
                ax.text(x + (1 - gap) / 2, y + (1 - gap) / 2, where[p], color="white",
                        ha="center", va="center", fontsize=5 if w > 9 else 6)
        elif p in slots:
            ax.add_patch(Rectangle((x, y), 1 - gap, 1 - gap, facecolor="white",
                                   edgecolor="#c0392b", linestyle="--", linewidth=0.8))
        else:
            ax.add_patch(Rectangle((x, y), 1 - gap, 1 - gap, facecolor=ROUTE, edgecolor="none"))
    n, s = len(r["placed"]), len(slots)
    ax.set_title(f"{r['circuit'].replace('_qedc', '')}\n{n}/{s} slots ({n / s:.0%}), "
                 f"{n}/{w * h} tiles ({n / (w * h):.0%})", fontsize=8)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outs")
    ap.add_argument("png")
    ap.add_argument("--spec", default="D3-k1-fact")
    ap.add_argument("--csv")
    args = ap.parse_args()

    runs = load(args.outs, args.spec)
    cols = 4
    rows = math.ceil(len(runs) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 3.3 * rows))
    for ax, r in zip(axes.flat, runs):
        draw(ax, r)
    for ax in list(axes.flat)[len(runs):]:
        ax.axis("off")
    fig.legend(handles=[Patch(facecolor=DATA, edgecolor=EDGE, label="data qubit"),
                        Patch(facecolor="white", edgecolor="#c0392b", linestyle="--",
                              label="empty data slot (padding)"),
                        Patch(facecolor=ROUTE, label="routing tile")],
               loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle(f"Lower-plane occupancy ({args.spec} placement)", fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(args.png, dpi=200)

    table = [dict(circuit=r["circuit"], qubits=len(r["placed"]), slots=len(r["slots"]),
                  grid=f"{r['w']}x{r['h']}", tiles=r["w"] * r["h"],
                  slot_usage=f"{len(r['placed']) / len(r['slots']):.3f}",
                  tile_usage=f"{len(r['placed']) / (r['w'] * r['h']):.3f}") for r in runs]
    print(f"{'circuit':20s} {'N':>3s} {'slots':>5s} {'grid':>6s} {'tiles':>5s} "
          f"{'slots used':>10s} {'tiles used':>10s}")
    for t in table:
        print(f"{t['circuit']:20s} {t['qubits']:3d} {t['slots']:5d} {t['grid']:>6s} "
              f"{t['tiles']:5d} {float(t['slot_usage']):10.0%} {float(t['tile_usage']):10.0%}")
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(table[0]))
            wr.writeheader()
            wr.writerows(table)


if __name__ == "__main__":
    main()
