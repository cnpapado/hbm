"""Stim simulation of the HBMS cross-layer merge (paper Sec. 4.5) with seam-only noise.

The Z_D Z_M lattice-surgery merge between the data patch D (lower layer) and the T-state patch
M (upper layer, directly above D), through the gap column G (upper layer, along M's boundary).
The checks and their CNOT order are those of scripts/revision/draw_schematics.py (merge_code,
schedule), copied below with the same checks. Folded across the layers, only the d checks
between D's last column and G involve both layers. They are measured by ancillas on the lower
layer, and 2d - 1 of their CNOTs per round reach upper-layer (G) qubits: the vertical coupling.

Layout (unfolded, as in draw_schematics.merge_code): data qubits at integer (x, y), y = 0..d-1;
D on columns 0..d-1, G on column d, M on columns d+1..2d. One ancilla per check, at the check's
centre. A round is 6 layers: reset ancillas, 4 CNOT layers (Z checks NW NE SW SE, X checks
NW SW NE SE), measure ancillas.

Noise, uniform circuit-level depolarizing of strength p:
  CNOT            DEPOLARIZE2(p) after it
  reset           X_ERROR(p) after R, Z_ERROR(p) after RX
  measurement     X_ERROR(p) before M, Z_ERROR(p) before MX
  idle            DEPOLARIZE1(p) on every qubit that does nothing in a layer
and, with p' = m p:
  --mode seam     (default) only the 2d - 1 cross-layer CNOTs per round get DEPOLARIZE2(p')
  --mode whole    the old model of ls.ipynb: every operation on a qubit of M or G, or on the
                  ancilla of a check that touches M or G (the coupler patch and the bridge), runs
                  at p'. With --old-offset, p' = (1 + m) p, as ls.ipynb's right_factor did
                  (its "p' = p" curve had the coupler patch at 2p).

Two experiments per (mode, d, p, m), each `rounds` merged rounds (default d) between a
transversal initialisation and a transversal readout:
  zz  D, M in |0>, G in |+>. Observable: the merge outcome Z_D Z_M, the product of the new Z
      checks (those that touch G) in the first merged round. It ends with the split, G measured
      in X and D, M in Z, so the new Z checks have no final detectors: a chain of `rounds`
      measurement errors on one of them flips the outcome (timelike failure).
  xx  D, G, M in |+>. Observable: X_D X_M, the X parity of the bottom row across D, G and M,
      read out at the end. A Z chain from the bottom edge to the top edge, e.g. along the seam,
      flips it (spacelike failure of the merged patch).
The union is reported as 1 - (1 - P_zz)(1 - P_xx), treating the two failures as independent.

Setup (Quest venv):
  pip install stim sinter pymatching

Run (see seam_merge.sh for the Slurm array, one d per task):
  python seam_merge.py --check --d 3 5 7                 # builds every circuit and its decomposed
                                                         # error model (no sampling)
  python seam_merge.py --d 3 5 7 9 11 --m 1 5 10 --mode seam whole --workers 8 \\
      --csv results_seam/seam.csv
  python seam_merge.py --fit results_seam/seam_d*.csv    # thresholds and --seam-pth for analyze.py

Reading the CSV: one row per (mode, basis, d, p, m) with shots, errors, ler (per merge, i.e.
per `rounds` rounds) and ler_round = 1 - (1 - ler)^(1 / rounds). --fit adds the union and
prints, per mode and m:
  - the threshold: the median crossing of adjacent-d curves of the union (as ls.ipynb did);
  - a fit of the union below --fit-pmax to P = A (p / p_th)^((d + 1) / 2): log P - k log p =
    log A - k log p_th with k = (d + 1) / 2 is linear in k, so A and p_th come out of one
    least-squares line over every (d, p) point with at least --min-errors errors;
  - the --seam-pth string for scripts/revision/analyze.py: 1:0.01,5:<x>,10:<y> with
    x = 0.01 * p_th(m = 5) / p_th(m = 1), so the seam keeps analyze.py's in-plane calibration
    (A = 0.1, p_th = 0.01) at m = 1 and moves its threshold by what the simulation shows.
    analyze.py uses the same A for the seam, so also check the printed A(m) / A(1): if it is far
    from 1, the seam penalty is a prefactor more than a threshold shift.
Then, on the run outputs:
  python scripts/revision/analyze.py <outs> --pprime 1 5 10 --seam-pth <string> --csv rev.csv
  python scripts/revision/fit_d.py rev.csv --pprime 5 --csv rev_fitd_5p.csv   # and 10
(the current default, 1:0.01,5:0.004,10:0.002, is ls.ipynb's whole-patch result).
"""

import argparse
import csv
import glob
import math
import os
import sys
import time
from collections import defaultdict


# ---- the merge construction, copied from scripts/revision/draw_schematics.py (keep in sync)

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


# ---- the Stim circuit

class Layout:
    """Qubit indices, check groups and the cross-layer CNOTs of the distance-d merge."""

    def __init__(self, d):
        self.d = d
        merged, D, G, M = merge_code(d)
        self.times = schedule(merged)
        self.checks = [c for c, _ in self.times]
        self.D, self.G, self.M = set(D), set(G), set(M)
        self.data = D + G + M
        self.q = {p: i for i, p in enumerate(self.data)}  # data qubit -> index
        self.a = {c: len(self.data) + i for i, c in enumerate(self.checks)}  # check -> ancilla
        self.n = len(self.data) + len(self.checks)
        # cross-layer checks: support on D (lower) and G (upper), ancilla on the lower layer
        self.cross = [c for c in self.checks if c[2] & self.D and c[2] & self.G]
        self.cross_pairs = {(c, p) for c in self.cross for p in c[2] if p in self.G}
        assert len(self.cross) == d, (len(self.cross), d)
        assert len(self.cross_pairs) == 2 * d - 1, (len(self.cross_pairs), d)
        for c in self.cross:  # the drawn wires: D west, G east of each cross-layer check
            assert all((p in self.D) == (p[0] < c[1][0]) for p in c[2])
        self.new_z = [c for c in self.checks if c[0] == "Z" and c[2] & self.G]
        self.coupler = ({self.q[p] for p in self.G | self.M}
                        | {self.a[c] for c in self.checks if c[2] & (self.G | self.M)})


def build_circuit(lay, p, m, basis, mode="seam", rounds=None, old_offset=False):
    """The merge experiment as a stim.Circuit (basis 'zz' or 'xx', see the module docstring)."""
    import stim

    rounds = rounds or lay.d
    pp = (1 + m) * p if old_offset else m * p
    hot = lay.coupler if mode == "whole" else set()

    def r1(i):
        return pp if i in hot else p

    def r2(i, j, crossing):
        if mode == "seam":
            return pp if crossing else p
        return pp if (i in hot or j in hot) else p

    circ = stim.Circuit()
    nmeas = [0]

    def noise1(name, targets):
        by = defaultdict(list)
        for i in targets:
            by[r1(i)].append(i)
        for rate, ts in sorted(by.items()):
            if rate > 0:
                circ.append(name, ts, rate)

    def noise2(pairs):
        by = defaultdict(list)
        for i, j, crossing in pairs:
            by[r2(i, j, crossing)] += [i, j]
        for rate, ts in sorted(by.items()):
            if rate > 0:
                circ.append("DEPOLARIZE2", ts, rate)

    def measure(name, targets):
        """Measure targets (noise before), return their absolute measurement indices."""
        if not targets:
            return {}
        noise1("X_ERROR" if name == "M" else "Z_ERROR", targets)
        circ.append(name, targets)
        start = nmeas[0]
        nmeas[0] += len(targets)
        return {i: start + k for k, i in enumerate(targets)}

    def rec(*abs_idx):
        return [stim.target_rec(k - nmeas[0]) for k in abs_idx]

    for p_, i in lay.q.items():
        circ.append("QUBIT_COORDS", [i], [2 * p_[0], 2 * p_[1]])
    for c, i in lay.a.items():
        circ.append("QUBIT_COORDS", [i], [2 * c[1][0], 2 * c[1][1]])

    data_ids = [lay.q[p_] for p_ in lay.data]
    if basis == "zz":
        data_z = [lay.q[p_] for p_ in lay.data if p_ not in lay.G]
        data_x = [lay.q[p_] for p_ in lay.data if p_ in lay.G]
    elif basis == "xx":
        data_z, data_x = [], data_ids
    else:
        raise ValueError(basis)
    anc_z = [lay.a[c] for c in lay.checks if c[0] == "Z"]
    anc_x = [lay.a[c] for c in lay.checks if c[0] == "X"]
    cross = {(lay.a[c], lay.q[p_]) for c, p_ in lay.cross_pairs}

    def first_round_detector(c):
        if basis == "zz":  # D, M in |0>: Z checks that do not touch G are +1
            return c[0] == "Z" and not c[2] & lay.G
        return c[0] == "X"  # all data in |+>: every X check is +1

    prev = {}
    for r in range(rounds):
        # layer 1: reset the ancillas (and, in the first round, the data)
        rz = anc_z + (data_z if r == 0 else [])
        rx = anc_x + (data_x if r == 0 else [])
        for name, ts in (("R", rz), ("RX", rx)):
            if ts:
                circ.append(name, ts)
        noise1("X_ERROR", rz)
        noise1("Z_ERROR", rx)
        if r > 0:
            noise1("DEPOLARIZE1", data_ids)
        circ.append("TICK")
        # layers 2-5: the CNOTs
        for t in range(4):
            pairs = []
            for c, tm in lay.times:
                for p_, s in tm.items():
                    if s != t:
                        continue
                    a, q = lay.a[c], lay.q[p_]
                    pairs.append((q, a) if c[0] == "Z" else (a, q))
            circ.append("CX", [i for pr in pairs for i in pr])
            noise2([(i, j, (i, j) in cross or (j, i) in cross) for i, j in pairs])
            busy = {i for pr in pairs for i in pr}
            noise1("DEPOLARIZE1", [i for i in range(lay.n) if i not in busy])
            circ.append("TICK")
        # layer 6: measure the ancillas
        mz = measure("M", anc_z)
        mx = measure("MX", anc_x)
        noise1("DEPOLARIZE1", data_ids)
        now = {**mz, **mx}
        for c in lay.checks:
            k = now[lay.a[c]]
            coords = [2 * c[1][0], 2 * c[1][1], r]
            if r == 0:
                if first_round_detector(c):
                    circ.append("DETECTOR", rec(k), coords)
            else:
                circ.append("DETECTOR", rec(k, prev[c]), coords)
        if r == 0 and basis == "zz":  # the merge outcome: product of the new Z checks
            circ.append("OBSERVABLE_INCLUDE", rec(*(now[lay.a[c]] for c in lay.new_z)), 0)
        prev = {c: now[lay.a[c]] for c in lay.checks}
        circ.append("TICK")

    # transversal readout (for zz this is the split: G in X, D and M in Z)
    fz = measure("M", data_z)
    fx = measure("MX", data_x)
    final = {**fz, **fx}
    for c in lay.checks:
        if basis == "zz" and (c[0] != "Z" or c[2] & lay.G):
            continue  # only Z checks off G can be rebuilt from the Z readout
        if basis == "xx" and c[0] != "X":
            continue
        ks = [final[lay.q[p_]] for p_ in sorted(c[2])]
        circ.append("DETECTOR", rec(prev[c], *ks), [2 * c[1][0], 2 * c[1][1], rounds])
    if basis == "xx":  # X_D X_M: the bottom row across D, G and M
        row = [final[lay.q[(x, 0)]] for x in range(2 * lay.d + 1)]
        circ.append("OBSERVABLE_INCLUDE", rec(*row), 0)
    return circ


# ---- sampling

def tasks_for(args):
    import sinter

    out = []
    for d in args.d:
        lay = Layout(d)
        rounds = args.rounds or d
        for mode in args.mode:
            for m in args.m:
                for p in args.p:
                    pp = (1 + m) * p if (mode == "whole" and args.old_offset) else m * p
                    if pp >= 0.5:
                        continue
                    for basis in ("zz", "xx"):
                        circ = build_circuit(lay, p, m, basis, mode, rounds,
                                             old_offset=args.old_offset and mode == "whole")
                        meta = dict(mode=mode, old_offset=bool(args.old_offset and mode == "whole"),
                                    basis=basis, d=d, rounds=rounds, p=p, m=m, p_prime=pp,
                                    n_qubits=circ.num_qubits, cross_cnots_per_round=2 * d - 1)
                        out.append(sinter.Task(circuit=circ, json_metadata=meta))
    return out


FIELDS = ["mode", "old_offset", "basis", "d", "rounds", "p", "m", "p_prime", "n_qubits",
          "cross_cnots_per_round", "shots", "errors", "discards", "seconds", "ler", "ler_round"]


def run(args):
    import sinter

    tasks = tasks_for(args)
    print(f"{len(tasks)} circuits", file=sys.stderr)
    os.makedirs(os.path.dirname(os.path.abspath(args.csv)), exist_ok=True)
    stats = sinter.collect(num_workers=args.workers, tasks=tasks, decoders=["pymatching"],
                           max_shots=args.max_shots, max_errors=args.max_errors,
                           save_resume_filepath=args.csv + ".sinter", print_progress=True)
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for s in sorted(stats, key=lambda s: tuple(str(s.json_metadata[k]) for k in
                                                   ("mode", "basis", "m", "d", "p"))):
            md = s.json_metadata
            ler = s.errors / (s.shots - s.discards) if s.shots > s.discards else float("nan")
            w.writerow(dict(md, shots=s.shots, errors=s.errors, discards=s.discards,
                            seconds=round(s.seconds, 1), ler=ler,
                            ler_round=1 - (1 - ler) ** (1 / md["rounds"]) if ler == ler else ""))
    print("wrote", args.csv, file=sys.stderr)


def check(args):
    for d in args.d:
        lay = Layout(d)
        for mode in args.mode:
            for basis in ("zz", "xx"):
                circ = build_circuit(lay, 1e-3, args.m[-1], basis, mode, args.rounds or d,
                                     old_offset=args.old_offset and mode == "whole")
                dem = circ.detector_error_model(decompose_errors=True)  # fails if non-deterministic
                print(f"d={d} {mode:5s} {basis}: {circ.num_qubits} qubits, "
                      f"{circ.num_detectors} detectors, {circ.num_observables} observable, "
                      f"{dem.num_errors} error mechanisms, {len(lay.cross_pairs)} cross-layer "
                      f"CNOTs per round")


# ---- fitting

def load_sinter(path):
    """Rows like the CSV's from a sinter resume file (<csv>.sinter), so a fit can run on the
    partial results of tasks that have not finished. Its lines are incremental: lines of the
    same task (strong_id) are summed."""
    import json
    tot = {}
    with open(path) as f:
        for r in csv.DictReader(f, skipinitialspace=True):
            r = {k.strip(): v for k, v in r.items()}
            t = tot.setdefault(r["strong_id"], dict(json.loads(r["json_metadata"]), shots=0,
                                                    errors=0, discards=0, seconds=0.0))
            t["old_offset"] = str(t.get("old_offset", False))  # as in the CSV
            for k in ("shots", "errors", "discards"):
                t[k] += int(r[k])
            t["seconds"] += float(r["seconds"])
    return list(tot.values())


def load(paths):
    rows = []
    for pat in paths:
        for path in sorted(glob.glob(pat)) or [pat]:
            if path.endswith(".sinter"):
                rows += load_sinter(path)
                continue
            with open(path) as f:
                rows += list(csv.DictReader(f))
    for r in rows:
        for k in ("d", "rounds", "shots", "errors", "discards"):
            r[k] = int(float(r[k]))
        for k in ("p", "m", "p_prime"):
            r[k] = float(r[k])
    return rows


def crossings(curves):
    """Median crossing p of adjacent-d curves {d: {p: ler}} in log-log space."""
    out = []
    ds = sorted(curves)
    for d1, d2 in zip(ds, ds[1:]):
        ps = sorted(p for p in curves[d1] if p in curves[d2]
                    and curves[d1][p] > 0 and curves[d2][p] > 0)
        diff = [math.log10(curves[d1][p]) - math.log10(curves[d2][p]) for p in ps]
        for k in range(len(ps) - 1):
            y0, y1 = diff[k], diff[k + 1]
            if y0 * y1 < 0:
                x0, x1 = math.log10(ps[k]), math.log10(ps[k + 1])
                out.append(10 ** (x0 - y0 * (x1 - x0) / (y1 - y0)))
    out.sort()
    return out[len(out) // 2] if out else None


def fit_line(points):
    """Least squares y = b0 + b1 x over (x, y) points; None with fewer than two x values."""
    if len({x for x, _ in points}) < 2:
        return None
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    sxx = sum((x - mx) ** 2 for x, _ in points)
    b1 = sum((x - mx) * (y - my) for x, y in points) / sxx
    return my - b1 * mx, b1


def fit(args):
    rows = load(args.fit)
    by = defaultdict(dict)  # (mode, old_offset, m, d, p) -> {basis: row}
    for r in rows:
        by[(r["mode"], r["old_offset"], r["m"], r["d"], r["p"])][r["basis"]] = r
    union = defaultdict(lambda: defaultdict(dict))  # (mode, off, m) -> d -> p -> (ler, errors)
    for (mode, off, m, d, p), b in by.items():
        if "zz" in b and "xx" in b:
            pz, px = (b[k]["errors"] / max(b[k]["shots"] - b[k]["discards"], 1) for k in ("zz", "xx"))
            union[(mode, off, m)][d][p] = (1 - (1 - pz) * (1 - px),
                                           min(b["zz"]["errors"], b["xx"]["errors"])
                                           if args.both else b["zz"]["errors"] + b["xx"]["errors"])
    fits = {}
    for key in sorted(union):
        mode, off, m = key
        curves = {d: {p: v[0] for p, v in ps.items()} for d, ps in union[key].items()}
        pth_cross = crossings(curves)
        pts = [((d + 1) / 2, math.log(v[0]) - (d + 1) / 2 * math.log(p))
               for d, ps in union[key].items() for p, v in ps.items()
               if p <= args.fit_pmax and v[1] >= args.min_errors and v[0] > 0]
        line = fit_line(pts)
        if line:
            fits[key] = (math.exp(line[0]), math.exp(-line[1]))
        A, pth = fits.get(key, (float("nan"), float("nan")))
        print(f"{mode:5s}{' (1+m)p' if off == 'True' else ''} m={m:g}: crossing threshold "
              f"{pth_cross if pth_cross else float('nan'):.2e}, fit A={A:.3g} p_th={pth:.2e} "
              f"({len(pts)} points)")
    for mode, off in sorted({(k[0], k[1]) for k in fits}):
        ref = fits.get((mode, off, 1.0)) or fits.get(("seam", "False", 1.0))
        if not ref:
            print(f"{mode}: no m = 1 fit to scale against")
            continue
        items = ["1:0.01"]
        for (md, of, m), (A, pth) in sorted(fits.items()):
            if (md, of) == (mode, off) and m != 1:
                items.append(f"{m:g}:{0.01 * pth / ref[1]:.4g}")
                print(f"{mode} m={m:g}: A(m)/A(1) = {A / ref[0]:.2f}, "
                      f"p_th(m)/p_th(1) = {pth / ref[1]:.3f}")
        print(f"{mode}{' (1+m)p' if off == 'True' else ''}: --seam-pth {','.join(items)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d", type=int, nargs="+", default=[3, 5, 7, 9, 11])
    ap.add_argument("--p", type=float, nargs="+",
                    default=[1e-3, 1.5e-3, 2e-3, 3e-3, 4e-3, 5e-3, 6e-3, 7e-3, 8e-3, 1e-2,
                             1.2e-2, 1.5e-2])
    ap.add_argument("--m", type=float, nargs="+", default=[1, 5, 10], help="p' = m p")
    ap.add_argument("--mode", nargs="+", default=["seam"], choices=["seam", "whole"])
    ap.add_argument("--old-offset", action="store_true",
                    help="whole mode: p' = (1 + m) p, as ls.ipynb's right_factor")
    ap.add_argument("--rounds", type=int, default=None, help="merged rounds (default d)")
    ap.add_argument("--max-shots", type=int, default=10_000_000)
    ap.add_argument("--max-errors", type=int, default=500)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--csv", default="results_seam/seam.csv")
    ap.add_argument("--check", action="store_true",
                    help="build every circuit and its decomposed error model, no sampling")
    ap.add_argument("--fit", nargs="+", metavar="CSV", help="fit thresholds from these CSVs")
    ap.add_argument("--fit-pmax", type=float, default=5e-3,
                    help="largest p used in the A (p/p_th)^((d+1)/2) fit")
    ap.add_argument("--min-errors", type=int, default=20,
                    help="fewest errors (zz + xx) for a point to enter the fit")
    ap.add_argument("--both", action="store_true",
                    help="--min-errors applies to each basis instead of their sum")
    args = ap.parse_args()
    if args.fit:
        fit(args)
    elif args.check:
        check(args)
    else:
        t0 = time.time()
        run(args)
        print(f"done in {time.time() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
