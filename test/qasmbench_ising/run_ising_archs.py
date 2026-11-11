"""
run_ising_archs.py
------------------
Run the paper's 2D baseline + HBM configurations on a directory of circuits.
The wisq invocations and HBM_CONFIG values are the ones in test/run_no_hbm.sh,
run_arch_A.sh and run_arch_C_shared_{2,4,8,16}.sh on temp-transfer-branch;
this runs them locally in parallel instead of as SLURM arrays.

Usage:
  python run_ising_archs.py <bench_dir> <out_dir> [--tmr 172800] [--jobs 6]
"""

import argparse
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ARCH_NAME -> (HBM_CONFIG, extra wisq args)
CONFIGS = {
    "no_hbm": ("no_hbm", ["-arch", "compact_layout"]),
    "ARCH_A": ("shared_none", []),
    "ARCH_C_shared_2": ("shared_2-route_upper", []),
    "ARCH_C_shared_4": ("shared_4-route_upper", []),
    "ARCH_C_shared_8": ("shared_8-route_upper", []),
    "ARCH_C_shared_16": ("shared_16-route_upper", []),
}


def run_one(bench, arch, out_dir, tmr):
    hbm, extra = CONFIGS[arch]
    out = out_dir / f"{bench.stem}_{arch}.out"
    if out.exists() and out.stat().st_size > 0:
        return
    env = dict(os.environ, HBM_CONFIG=hbm)
    start = time.time()
    with open(out_dir / f"{bench.stem}_{arch}.log", "w") as log:
        subprocess.run(
            ["wisq", str(bench), "-op", str(out), "--mode", "scmr", *extra, "-tmr", str(tmr)],
            env=env, stdout=log, stderr=subprocess.STDOUT,
        )
    with open(out_dir / "wallclock.txt", "a") as f:
        f.write(f"{bench.stem} {arch} {time.time() - start:.0f}s\n")
    print(f"done {bench.stem} {arch} {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("bench_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--tmr", type=int, default=172800)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--archs", nargs="*", default=list(CONFIGS))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    benches = sorted(args.bench_dir.glob("*.qasm"), key=lambda p: int(p.stem.split("_n")[-1]))
    with ThreadPoolExecutor(args.jobs) as ex:
        for b in benches:
            for a in args.archs:
                ex.submit(run_one, b, a, args.out_dir, args.tmr)
