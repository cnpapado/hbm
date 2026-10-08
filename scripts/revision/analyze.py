"""Turn HBM_DESIGN run outputs into physical cost numbers (one CSV row per run x p').

For each wisq output JSON (written with HBM_DESIGN set) this computes:
  - circuit stats from the JSON itself: logical qubits N, T count, CNOT count, ideal depth
    (DAG depth over cx/t/tdg), T density = T / (N * ideal depth);
  - routing stats: timesteps, cost ratio, stalls (waiting for magic vs blocked path),
    direct vs routed T gates, path tiles, vertical merges;
  - the smallest odd code distance d_req that keeps the whole program's logical error
    below --target, using the model below;
  - physical qubits Q(d_req), runtime in rounds, space-time volume STV = Q * rounds.

Error model (per program; eps(d, p, p_th) = A * (p / p_th) ** ((d + 1) / 2) per tile-round):
  data idling      N * steps * d * eps(d, p, p_th)
  routing merges   (T + CNOT path tiles) * d * eps(d, p, p_th)
  vertical seams   vertical_merges * d * eps(d, p, p_th_v(mult))   (top designs only)
  T states         T count * eps_source                  (cultivation or factory output)
A vertical merge with coupling error p' = mult * p uses the lower threshold p_th_v(mult)
measured for that merge in Stim (HBMS paper, Fig. 11: ~1e-2 at 1p, ~4e-3 at 5p, ~2e-3 at
10p; override with --seam-pth). Only the coupler qubits along the seam see p'.
A run whose T-state error alone exceeds the target is infeasible for that circuit (the
cultivation fidelity floor).

Physical qubits: tiles * 2 d^2 + n_factories * factory_qubits, where tiles counts every
lower- and top-layer tile except factory tiles (cultivation patches count as tiles).

The simulation used a fixed d (HBM_D) to turn recharge rounds into timesteps and to size
factories in tiles. If d_req changes either of those, the row is flagged rerun_needed:
rerun that design with HBM_D=d_req for exact numbers.

Usage:
  python analyze.py OUT_DIR [OUT_DIR ...] --csv results.csv
  python analyze.py outs_rev --pprime 1 5 10 --p 1e-3 --target 0.01 --csv rev.csv
"""

import argparse
import csv
import glob
import json
import math
import os
import sys
from collections import defaultdict


def eps(d, p, A, p_th):
    return A * (p / p_th) ** ((d + 1) / 2)


def parse_seam_pth(text):
    """'1:0.01,5:0.004' -> {1.0: 0.01, 5.0: 0.004}"""
    out = {}
    for item in text.split(","):
        mult, pth = item.split(":")
        out[float(mult)] = float(pth)
    return out


def circuit_stats(gates):
    level = defaultdict(int)
    n_t = n_cx = 0
    qubits = set()
    for g in gates:
        qubits.update(g)
        if len(g) == 1:
            n_t += 1
            level[g[0]] += 1
        else:
            n_cx += 1
            nxt = max(level[g[0]], level[g[1]]) + 1
            level[g[0]] = level[g[1]] = nxt
    depth = max(level.values()) if level else 0
    return dict(n_used=len(qubits), n_t=n_t, n_cx=n_cx, ideal_depth=depth)


def program_error(d, args, des, st, steps, mult):
    e = eps(d, args.p, args.A, args.p_th)
    total = des["n_logical"] * steps * d * e
    total += (st.get("t_path_tiles", 0) + st.get("cx_path_tiles", 0)) * d * e
    total += st.get("vertical_merges", 0) * d * eps(d, args.p, args.A, args.seam_pth[mult])
    return total


def source_error(des, args):
    return args.cult_error if des["source"] == "cultivation" else args.factory_error


def qubits(d, des):
    tiles = (des["lower_tiles"] - des["lower_factory_tiles"]
             + des["top_tiles"] - des["top_factory_tiles"])
    return tiles * 2 * d * d + des["n_factories"] * des["factory_qubits"]


def analyze_file(path, args):
    with open(path) as f:
        data = json.load(f)
    arch = data.get("arch") or {}
    des = arch.get("design")
    if des is None:
        return []  # legacy (HBM_CONFIG) output
    bench = os.path.basename(path).split("__")[0]
    base = dict(bench=bench, file=os.path.basename(path), family=des["family"],
                spec=des["spec"], knob=des["knob"], source=des["source"],
                placement=des["placement"], d_sim=des["d"],
                recharge_rounds=des["recharge_rounds"], recharge_steps=des["recharge_steps"],
                N=des["n_logical"], lower_tiles=des["lower_tiles"], top_tiles=des["top_tiles"],
                n_factories=des["n_factories"], n_sources=des["n_sources"])
    steps = data.get("steps")
    if not isinstance(steps, list):
        return [dict(base, status="timeout")]

    st = data.get("stats") or {}
    cs = circuit_stats([tuple(g) for g in data.get("gates", [])])
    n_steps = len(steps)
    t_density = cs["n_t"] / (des["n_logical"] * cs["ideal_depth"]) if cs["ideal_depth"] else 0
    common = dict(
        base, status="ok", **cs, t_fraction=cs["n_t"] / max(1, cs["n_t"] + cs["n_cx"]),
        t_density=t_density, steps=n_steps,
        cost_ratio=n_steps / cs["ideal_depth"] if cs["ideal_depth"] else math.nan,
        t_direct=st.get("t_direct", 0), t_routed=st.get("t_routed", 0),
        t_path_tiles=st.get("t_path_tiles", 0), cx_path_tiles=st.get("cx_path_tiles", 0),
        vertical_merges=st.get("vertical_merges", 0),
        stall_magic_wait=st.get("stall_magic_wait", 0),
        stall_t_blocked=st.get("stall_t_blocked", 0),
        stall_cx_blocked=st.get("stall_cx_blocked", 0),
        empty_steps=st.get("empty_steps", 0), sources_used=st.get("sources_used", 0),
    )

    rows = []
    e_src = cs["n_t"] * source_error(des, args)
    for mult in args.pprime:
        row = dict(common, pprime_mult=mult, e_source=e_src)
        if e_src > args.target:
            rows.append(dict(row, feasible=False, d_req=None, Q=None, rounds=None, STV=None,
                             error=None, rerun_needed=False))
            continue
        d_req = None
        for d in range(3, args.dmax + 1, 2):
            if program_error(d, args, des, st, n_steps, mult) + e_src <= args.target:
                d_req = d
                break
        if d_req is None:
            rows.append(dict(row, feasible=False, d_req=None, Q=None, rounds=None, STV=None,
                             error=None, rerun_needed=False))
            continue
        q = qubits(d_req, des)
        rounds = n_steps * d_req
        rerun = (math.ceil(des["recharge_rounds"] / d_req) != des["recharge_steps"]
                 or (des["n_factories"] > 0 and des["family"] in ("D1", "D5")
                     and math.ceil(des["factory_qubits"] / (2 * d_req * d_req))
                     != des["factory_tiles"]))
        rows.append(dict(row, feasible=True, d_req=d_req, Q=q, rounds=rounds, STV=q * rounds,
                         error=program_error(d_req, args, des, st, n_steps, mult) + e_src,
                         rerun_needed=rerun))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dirs", nargs="+", help="directories (searched recursively) or .out files")
    ap.add_argument("--csv", default="revision_results.csv")
    ap.add_argument("--p", type=float, default=1e-3, help="physical error rate")
    ap.add_argument("--pprime", type=float, nargs="+", default=[1, 5, 10],
                    help="vertical-coupling error as multiples of p")
    ap.add_argument("--target", type=float, default=0.01, help="allowed program error")
    ap.add_argument("--A", type=float, default=0.1)
    ap.add_argument("--p-th", dest="p_th", type=float, default=0.01)
    ap.add_argument("--cult-error", type=float, default=1e-7,
                    help="T-state error from cultivation (Gidney 2025: 1e-7 at p=1e-3)")
    ap.add_argument("--factory-error", type=float, default=4.5e-8,
                    help="T-state error from the factory (Litinski 2019 (15-to-1)_{17,7,7})")
    ap.add_argument("--seam-pth", type=parse_seam_pth, default="1:0.01,5:0.004,10:0.002",
                    help="threshold of a vertical merge per p' multiple, 'mult:p_th,...' "
                         "(default from the HBMS paper's Stim results, Fig. 11)")
    ap.add_argument("--dmax", type=int, default=61)
    args = ap.parse_args()
    missing = [m for m in args.pprime if m not in args.seam_pth]
    if missing:
        ap.error(f"--seam-pth has no threshold for p' multiples {missing}")

    files = []
    for d in args.dirs:
        if os.path.isdir(d):
            files += glob.glob(os.path.join(d, "**", "*.out"), recursive=True)
            files += glob.glob(os.path.join(d, "**", "*.json"), recursive=True)
        else:
            files.append(d)
    rows = []
    for f in sorted(files):
        try:
            rows += analyze_file(f, args)
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"skip {f}: {e}", file=sys.stderr)
    if not rows:
        print("no HBM_DESIGN outputs found", file=sys.stderr)
        sys.exit(1)

    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    ok = [r for r in rows if r["status"] == "ok"]
    print(f"{len(files)} files -> {len(rows)} rows ({len(ok)} finished, "
          f"{sum(r['status'] == 'timeout' for r in rows)} timeouts) -> {args.csv}")
    rerun = sorted({(r["spec"], r["d_req"]) for r in ok if r.get("rerun_needed")})
    if rerun:
        print("rows needing a rerun at d_req (spec, d_req):", rerun)


if __name__ == "__main__":
    main()
