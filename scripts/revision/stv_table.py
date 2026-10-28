"""Print the revision runs as one table: a row per circuit, a column per configuration.

Reads analyze.py's CSV (works on partial results). Each cell is the run's STV (qubits x
rounds, at the simulated d) or, with --metric, its Q or steps:
  T/O     timed out (retried by the next submission)
  infeas  the T states alone break the error target
  .       not finished yet
2D-Cult cells use the cultivation R with the lowest STV. The last columns compare STV:
P1 = best 2D-Cult / best HBM, P2 = Planar-2D / best HBM (> 1: HBM wins), and name the best
HBM layout. Bottom-routed Shared-S columns (D3-s<S>-fact-bottom) appear when the CSV has them,
and count as HBM layouts.

Usage:
  python stv_table.py rev.csv [--metric STV|Q|steps] [--csv stv_table.csv]
"""

import argparse
import csv
import math
import re

COLS = [  # (column, spec)
    ("2D-Cult-k1", "D2-wide"), ("2D-Cult-k1/2", "D2-tight"), ("Planar-2D", "D0-alt"),
    ("HBM-Ded", "D3-k1-fact"), ("HBM-S2", "D3-s2-fact"), ("HBM-S4", "D3-s4-fact"),
    ("HBM-S8", "D3-s8-fact"), ("HBM-S16", "D3-s16-fact"),
]
BOTTOM_COLS = [(f"HBM-S{k}-bot", f"D3-s{k}-fact-bottom") for k in (2, 4, 8, 16)]  # if run
CULT = ("D2-wide", "D2-tight")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def cell(rows):
    """The run a cell shows: the lowest-STV feasible run, else infeasible, else timeout."""
    ok = [r for r in rows if r["status"] == "ok" and r.get("feasible") == "True"]
    if ok:
        return min(ok, key=lambda r: num(r["STV"]))
    if any(r["status"] == "ok" for r in rows):
        return "infeas"
    return "T/O" if rows else "."


def fmt(c, metric):
    if isinstance(c, str):
        return c
    v = num(c[metric])
    return f"{v:.2e}" if metric == "STV" else f"{v:,.0f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--metric", choices=["STV", "Q", "steps"], default="STV")
    ap.add_argument("--csv-out", "--csv", dest="out", help="also write the table here")
    args = ap.parse_args()

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))
    by = {}
    for r in rows:
        by.setdefault((r["bench"], r["spec"]), []).append(r)
    cols = COLS + [c for c in BOTTOM_COLS if any(r["spec"] == c[1] for r in rows)]
    hbm_specs = [spec for _, spec in cols if spec.startswith("D3")]
    benches = sorted({r["bench"] for r in rows},
                     key=lambda b: tuple(int(x) for x in re.findall(r"\d+", b)[::-1]))

    head = ["circuit"] + [c for c, _ in cols] + ["P1", "P2", "best HBM"]
    table = []
    for b in benches:
        cells = {spec: cell(by.get((b, spec), [])) for _, spec in cols}
        stv = {s: num(c["STV"]) for s, c in cells.items() if not isinstance(c, str)}
        hbm = min((s for s in hbm_specs if s in stv), key=stv.get, default=None)
        cult = min((stv[s] for s in CULT if s in stv), default=None)
        p1 = f"{cult / stv[hbm]:.2f}" if hbm and cult else ""
        p2 = f"{stv['D0-alt'] / stv[hbm]:.2f}" if hbm and "D0-alt" in stv else ""
        best = dict((s, c) for c, s in cols).get(hbm, "")
        table.append([b] + [fmt(cells[s], args.metric) for _, s in cols] + [p1, p2, best])

    w = [max(len(str(x)) for x in col) for col in zip(head, *table)]
    line = lambda xs: "  ".join(str(x).rjust(n) for x, n in zip(xs, w))  # noqa: E731
    print(f"{args.metric} per circuit and configuration "
          f"(P1, P2: baseline STV / best HBM STV, > 1: HBM wins)\n")
    print(line(head))
    for t in table:
        print(line(t))
    done = {s: sum(not isinstance(cell(by.get((b, s), [])), str) for b in benches)
            for _, s in cols}
    print("\nfinished and feasible: " + ", ".join(f"{c} {done[s]}" for c, s in cols)
          + f"  (of {len(benches)} circuits with any result)")
    if args.out:
        with open(args.out, "w", newline="") as f:
            csv.writer(f).writerows([head] + table)
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
