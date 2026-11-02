"""Put every run at its own code distance: the smallest odd d that meets the error target.

analyze.py reports STV at the d the runs were simulated at (HBM_D, 13 in the sweep) and, for
the sensitivity note, d_need_<m>p: the smallest odd d at which the run's program error,
with vertical links at p' = m * p, stays under the target. This rescales each run to that d:

  tiles      (Q - patches * patch_q - factories * 22 d_sim^2) / (2 d_sim^2), from the run
  Q(d)       tiles * 2 d^2 + patches * max(patch_q, 2 d^2) + factories * 22 d_sim^2
  rounds(d)  steps * d
  STV(d)     Q(d) * rounds(d)

A factory keeps the size it was simulated with (HBM_FACTORY_QUBITS, 22 d_sim^2): its output
error (35 p^3) is fixed, so its size is too, whatever the data's d. A cultivation patch keeps
its grade's qubit count (454 or 463) but is never smaller than the distance-d tile it hands the
T state to. The step count is kept: that is exact for factory
designs (always ready); for cultivation, recharge takes ceil(R / d) steps, so at d > d_sim a
run would take slightly fewer steps than kept here and at d < d_sim slightly more. Re-simulate
with HBM_D = d for exact numbers. A run with no such d up to analyze.py's --dmax is infeasible.

Every column keeps its name, so stv_table.py, compare.py and plot_results.py read the output
as usual; d_sim becomes the fitted d and the simulated values move to d_sim_run, Q_sim_run,
rounds_sim_run and STV_sim_run.

Usage:
  python fit_d.py rev.csv --csv rev_fitd.csv [--pprime 1]
"""

import argparse
import csv

from analyze import parse_grades

FACTORY_TILES = 11  # HBM_FACTORY_QUBITS default: 22 d^2, i.e. 11 tiles of 2 d^2


def patch_qubits(grade_qubits, d):
    return max(grade_qubits, 2 * d * d)


def refit(rows, pprime=1, grades=None):
    """The rows with each feasible run moved to its smallest odd d meeting the target."""
    grades = grades or parse_grades("60:3e-6:454,360:2e-9:463")
    col = f"d_need_{pprime:g}p"
    out = []
    for r in rows:
        if r.get("status") != "ok" or r.get("feasible") != "True":
            out.append(dict(r))
            continue
        if not r.get(col):  # no d up to --dmax meets the target
            out.append(dict(r, feasible="False", Q="", rounds="", STV=""))
            continue
        d0, d = int(r["d_sim"]), int(r[col])
        n_p, n_f = int(r["n_patches"]), int(r["n_factories"])
        q_p = grades[int(r["recharge_rounds"])][1] if n_p else 0
        tiles = (float(r["Q"]) - n_p * q_p - n_f * FACTORY_TILES * 2 * d0 * d0) / (2 * d0 * d0)
        q = (round(tiles) * 2 * d * d + n_p * patch_qubits(q_p, d)
             + n_f * FACTORY_TILES * 2 * d0 * d0)
        rounds = int(r["steps"]) * d
        out.append(dict(r, d_sim=d, Q=q, rounds=rounds, STV=q * rounds, meets_target="True",
                        d_sim_run=d0, Q_sim_run=r["Q"], rounds_sim_run=r["rounds"],
                        STV_sim_run=r["STV"]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="output of analyze.py")
    ap.add_argument("--csv-out", "--csv", dest="out", required=True)
    ap.add_argument("--pprime", type=float, default=1,
                    help="vertical-link error in units of p (a d_need_<m>p column)")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.csv)))
    out = refit(rows, args.pprime, args.cult_grades)
    fields = list(rows[0]) + ["d_sim_run", "Q_sim_run", "rounds_sim_run", "STV_sim_run"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    moved = sum(1 for a, b in zip(rows, out) if a.get("d_sim") != str(b.get("d_sim")))
    print(f"{len(out)} rows, {moved} moved off d_sim -> {args.out}")


if __name__ == "__main__":
    main()
