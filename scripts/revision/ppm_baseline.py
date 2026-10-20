"""Pauli-product-measurement (PPM) baseline, from Litinski's published cost model.

Litinski, "A Game of Surface Codes" (GoSC; Quantum 3, 128, 2019; arXiv:1808.02892):
  - After the Litinski transformation every T gate is a pi/8 rotation about a Pauli product,
    executed by one Pauli-product measurement that consumes one magic state; Clifford gates
    are commuted to the end and absorbed into the final measurements (Sec. 1). "A data block
    combined with a distillation block constitutes a quantum computer in which T gates are
    performed one after the other" (p. 4), so the runtime is T count x (steps per rotation):
    Sec. 4 "finish[es] computations in a time proportional to the T count" (p. 18).
  - Data blocks (Sec. 2 summary, p. 9), n = logical qubits, one step = d code cycles (the
    same unit as a DASCOT/HBMS step):
        compact        1.5n + 3 tiles               up to 9 steps per rotation
        intermediate   2n + 4 tiles                 up to 5 steps
        fast           2n + ceil(sqrt(8n)) + 1      1 step
    (Fig. 13's caption gives 2.5n + 4 for the intermediate block; we use the text's 2n + 4.)
    The fast block with one rotation per step is also what the Microsoft Azure Quantum
    Resource Estimator assumes (logical qubits 2n + ceil(sqrt(8n)) + 1, logical depth = T
    count); ppm_qre.py cross-checks it.
  - Sec. 5 ("trade-offs limited by T depth") runs T layers in parallel on "units", each a
    fast block holding 2n qubits plus modified distillation blocks; "going from the fast
    setup to parallelized units is, initially, not a favorable space-time trade-off" (p. 24).
    We model units only as a lower bound for the fast block: u x (block tiles), u x the
    source rate, steps = max(T depth, ceil(T count / u)). The doubled data, Bell pairs,
    correction qubits and teleportation are ignored. At a fixed d this gives about the same
    STV as the sequential fast block (u x the tiles for 1/u of the steps).

Magic-state supply uses the same model as the HBMS designs: each source delivers one state
per (1 + ceil(R/d)) steps. Full supply is ceil(u * (1 + ceil(R/d)) / steps_per_rotation)
sources, so the block never waits; --source-fracs also tries fewer sources (the block then
waits for states, like the D3 k sweep). Cultivation grades come from Tour de gross (arXiv:
2506.03094) App. A.6, Table 5. The factory option (--source factory) matches the D0 runs:
always ready, 22 d^2 qubits and 35 p^3 error (GoSC 15-to-1 block, Secs. 3.3 and 4.1).

Code distance: every row is at a given d (--d, default 13, the d the HBMS runs use), as in
analyze.py. A row is infeasible when its T states alone exceed the error target. Its program
error at that d (data idling + T states; the ancilla region's merges are not charged) is
reported as logical_error. No tiles are charged for connecting the sources to the block.

Output: rows in analyze.py's CSV schema (family "PPM"), so compare.py can read them
alongside the HBMS runs. compare.py keeps the best PPM row per benchmark and setting.

Usage:
  python ppm_baseline.py test/benchmarks_bursty_cx --csv ppm.csv
  python compare.py rev.csv ppm.csv --prefix rev     # adds pair P3 (PPM vs HBM)
"""

import argparse
import csv
import glob
import math
import os
import re
from collections import defaultdict

BLOCKS = {  # name: (tiles for n qubits, steps per rotation)
    "compact": (lambda n: math.ceil(1.5 * n) + 3, 9),
    "intermediate": (lambda n: 2 * n + 4, 5),
    "fast": (lambda n: 2 * n + math.ceil(math.sqrt(8 * n)) + 1, 1),
}


def read_circuit(path):
    """Register size, and CNOT / T gates parsed with wisq.dascot.extract_gates_from_file's regex."""
    n_reg, gates = 0, []
    with open(path) as f:
        for line in f:
            m = re.match(r"qreg\s+\w+\[(\d+)\];", line)
            if m:
                n_reg += int(m.group(1))
            m = re.match(r"(cx)\s+q\[(\d+)\],\s*q\[(\d+)\];", line)
            if m:
                gates.append((int(m.group(2)), int(m.group(3))))
            m = re.match(r"(t|tdg)\s+q\[(\d+)\];", line)
            if m:
                gates.append((int(m.group(2)),))
    return n_reg, gates


def circuit_stats(n_reg, gates):
    """Same counts as analyze.circuit_stats, plus T depth (T gates on the longest path)."""
    level, t_level = defaultdict(int), defaultdict(int)
    n_t = n_cx = 0
    qubits = set()
    for g in gates:
        qubits.update(g)
        if len(g) == 1:
            n_t += 1
            level[g[0]] += 1
            t_level[g[0]] += 1
        else:
            n_cx += 1
            a, b = g
            level[a] = level[b] = max(level[a], level[b]) + 1
            t_level[a] = t_level[b] = max(t_level[a], t_level[b])
    return dict(N=max(n_reg, len(qubits)), n_used=len(qubits), n_t=n_t, n_cx=n_cx,
                ideal_depth=max(level.values(), default=0),
                t_depth=max(t_level.values(), default=0))


def eps(d, p, A, p_th):
    return A * (p / p_th) ** ((d + 1) / 2)


def parse_grades(text):
    out = {}
    for item in text.split(","):
        rounds, err, qubits = item.split(":")
        out[int(rounds)] = (float(err), int(qubits))
    return out


def variants(args):
    """(spec, block, units, source fraction) for every PPM setting evaluated."""
    out = []
    for block in BLOCKS:
        for units in (args.units if block == "fast" else [1]):
            for frac in args.source_fracs:
                spec = f"PPM-{block}" + (f"-u{units}" if units > 1 else "") + (
                    f"-s{frac:g}" if frac < 1 else "")
                out.append((spec, block, units, frac))
    return out


def plan(d, cs, block, units, frac, rounds):
    """Sources and steps at code distance d."""
    t_rot = BLOCKS[block][1]
    period = 1 + math.ceil(rounds / d)  # steps between two states from one source
    full = math.ceil(units * period / t_rot)
    n_src = max(1, math.ceil(frac * full))
    per_rot = max(t_rot / units, period / n_src)  # steady-state steps per rotation
    steps = max(cs["t_depth"], math.ceil(cs["n_t"] * per_rot))
    return n_src, steps


def rows_for(path, args):
    cs = circuit_stats(*read_circuit(path))
    n, n_t = cs["N"], cs["n_t"]
    bench = os.path.basename(path)[:-len(".qasm")]
    if args.source == "cultivation":
        supplies = [(r, *args.cult_grades[r]) for r in args.rounds]  # (rounds, error, qubits)
    else:  # factory qubits None: 22 d^2, set per d below
        err = args.factory_error if args.factory_error is not None else 35 * args.p ** 3
        supplies = [(args.factory_rounds, err, args.factory_qubits)]
    out = []
    for spec, block, units, frac in variants(args):
        tiles = units * BLOCKS[block][0](n)
        for rounds, src_err, src_qubits in supplies:
            e_src = n_t * src_err
            for d in args.d:
                n_src, steps = plan(d, cs, block, units, frac, rounds)
                err = n * steps * d * eps(d, args.p, args.A, args.p_th) + e_src
                row = dict(
                    bench=bench, file=path, family="PPM", spec=spec, knob=spec[len("PPM-"):],
                    source=args.source, placement="plane", recharge_rounds=rounds, d_sim=d,
                    recharge_steps=math.ceil(rounds / d), **cs,
                    t_parallelism=n_t / cs["t_depth"] if cs["t_depth"] else math.nan,
                    t_fraction=n_t / max(1, n_t + cs["n_cx"]),
                    t_density=n_t / (n * cs["ideal_depth"]) if cs["ideal_depth"] else 0,
                    units=units, source_frac=frac, lower_tiles=tiles, top_tiles=0,
                    status="ok", e_source=e_src, logical_error=err,
                    meets_target=err <= args.target, n_sources=n_src,
                    n_patches=n_src if args.source == "cultivation" else 0,
                    n_factories=n_src if args.source == "factory" else 0, steps=steps,
                    cost_ratio=steps / cs["ideal_depth"] if cs["ideal_depth"] else math.nan)
                if e_src > args.target:  # the T states alone break the target
                    out.append(dict(row, feasible=False, Q=None, rounds=None, STV=None))
                    continue
                q = tiles * 2 * d * d + n_src * (src_qubits or 22 * d * d)
                out.append(dict(row, feasible=True, Q=q, rounds=steps * d, STV=q * steps * d))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", help=".qasm files or directories of them")
    ap.add_argument("--csv", default="ppm_results.csv")
    ap.add_argument("--source", choices=["cultivation", "factory"], default="cultivation")
    ap.add_argument("--rounds", type=int, nargs="+", default=[60, 360],
                    help="cultivation grades to evaluate (keys of --cult-grades)")
    ap.add_argument("--cult-grades", type=parse_grades, default="60:3e-6:454,360:2e-9:463",
                    help="'rounds:T-error:qubits,...' (Tour de gross App. A.6, Table 5)")
    ap.add_argument("--factory-rounds", type=int, default=0,
                    help="rounds between factory outputs (default 0: always ready)")
    ap.add_argument("--factory-qubits", type=int, default=None,
                    help="qubits per factory (default 22 d^2: GoSC Sec. 3.3, 11 tiles)")
    ap.add_argument("--factory-error", type=float, default=None,
                    help="T-state error per factory output (default 35 p^3, GoSC Sec. 4.1)")
    ap.add_argument("--source-fracs", type=float, nargs="+", default=[1, 0.5, 0.25],
                    help="fractions of the full-supply source count to try")
    ap.add_argument("--units", type=int, nargs="+", default=[1, 2, 4],
                    help="GoSC Sec. 5 units for the fast block (1 = sequential)")
    ap.add_argument("--d", type=int, nargs="+", default=[13],
                    help="code distances to evaluate (the HBMS runs' HBM_D)")
    ap.add_argument("--p", type=float, default=1e-3)
    ap.add_argument("--target", type=float, default=0.01)
    ap.add_argument("--A", type=float, default=0.1)
    ap.add_argument("--p-th", dest="p_th", type=float, default=0.01)
    args = ap.parse_args()

    files = []
    for x in args.inputs:
        files += sorted(glob.glob(os.path.join(x, "*.qasm"))) if os.path.isdir(x) else [x]
    rows = [r for f in files for r in rows_for(f, args)]
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(files)} circuits -> {len(rows)} rows -> {args.csv}")
    # lambda = T per ideal step: PPM's cost ratio with the fast block (1 step per T gate).
    print(f"{'circuit':22s} {'N':>4s} {'T':>7s} {'depth':>7s} {'lambda':>7s} {'T-par':>7s}")
    for r in rows:
        if r["spec"] == "PPM-fast" and r["d_sim"] == args.d[0] \
                and r["recharge_rounds"] == rows[0]["recharge_rounds"]:
            lam = r["n_t"] / r["ideal_depth"] if r["ideal_depth"] else float("nan")
            print(f"{r['bench']:22s} {r['N']:4d} {r['n_t']:7d} {r['ideal_depth']:7d} "
                  f"{lam:7.2f} {r['t_parallelism']:7.2f}")


if __name__ == "__main__":
    main()
