import os
import subprocess
import json
import argparse
import statistics
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv

# === CLI ===
parser = argparse.ArgumentParser(description="Run WISQ benchmarks in parallel")
parser.add_argument("--runs", type=int, default=1)
parser.add_argument("--parallel", type=int, default=8, help="Number of parallel processes")
parser.add_argument("--tmr", type=str, default="3604", help="TMR value to use (default: 180)")
args = parser.parse_args()

wisq_path = "wisq"
benchmarks_dir = "../quantum-compiler-benchmark-circuits/synthetic_2"

# === Setup output ===
output_root = os.path.join(os.getcwd(), "output_parallel_3604")
bench_folder_name = os.path.basename(os.path.normpath(benchmarks_dir))
bench_output_dir = os.path.join(output_root, bench_folder_name)
os.makedirs(bench_output_dir, exist_ok=True)

# === configurations ===
HBM_CASES = [
    # name                                                     config                                       extra args
    ("no_hbm-compact_layout",                                  "no_hbm",                                   ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("no_hbm_single_magic_state-compact_layout",               "no_hbm_single_magic_state",                ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("shared_none-compact_layout",                             "shared_none",                              ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("shared_2-route_bottom-compact_layout",                   "shared_2-route_bottom",                    ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("shared_2-route_upper-compact_layout",                    "shared_2-route_upper",                     ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_4-route_bottom-compact_layout",                   "shared_4-route_bottom",                    ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_4-route_upper-compact_layout",                    "shared_4-route_upper",                     ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("shared_none-anchilla_perimeter-compact_layout",          "shared_none-anchilla_perimeter",           ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("shared_2-route_bottom-anchilla_perimeter-compact_layout","shared_2-route_bottom-anchilla_perimeter", ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    ("shared_2-route_upper-anchilla_perimeter-compact_layout", "shared_2-route_upper-anchilla_perimeter",  ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_4-route_bottom-anchilla_perimeter-compact_layout","shared_4-route_bottom-anchilla_perimeter", ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_4-route_upper-anchilla_perimeter-compact_layout", "shared_4-route_upper-anchilla_perimeter",  ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),

    # ("no_hbm-squared_sparse",                                  "no_hbm",                                   ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # ("no_hbm_single_magic_state-squared_sparse",               "no_hbm_single_magic_state",                ["-arch", "compact_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_none-squared_sparse",                             "shared_none",                              ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_2-route_bottom-squared_sparse",                   "shared_2-route_bottom",                    ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_2-route_upper-squared_sparse",                    "shared_2-route_upper",                     ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # # ("shared_4-route_bottom-squared_sparse",                   "shared_4-route_bottom",                    ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # # ("shared_4-route_upper-squared_sparse",                    "shared_4-route_upper",                     ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_none-anchilla_perimeter-squared_sparse",          "shared_none-anchilla_perimeter",           ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_2-route_bottom-anchilla_perimeter-squared_sparse","shared_2-route_bottom-anchilla_perimeter", ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # ("shared_2-route_upper-anchilla_perimeter-squared_sparse", "shared_2-route_upper-anchilla_perimeter",  ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # # ("shared_4-route_bottom-anchilla_perimeter-squared_sparse","shared_4-route_bottom-anchilla_perimeter", ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
    # # ("shared_4-route_upper-anchilla_perimeter-squared_sparse", "shared_4-route_upper-anchilla_perimeter",  ["-arch", "square_sparse_layout", "-tmr", f"{args.tmr}"]),
]

# === Helper functions ===
def get_qasm_files(directory):
    qasms, names = [], []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".qasm"):
                qasms.append(os.path.join(root, f))
                names.append(os.path.splitext(f)[0])
    return qasms, names

def run_and_stream(cmd, env, log_path):
    """Run subprocess and stream output to log file."""
    with open(log_path, "w") as log:
        p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
        p.wait()
    return p.returncode == 0

def load_steps(path):
    """Load number of steps from JSON output (if exists)."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        steps = data.get("steps")
        if steps == "timeout":
            return None
        return len(steps)
    except:
        return None

def load_footprint(path):
    """Load max number of occupied ancilla of any timestep."""
    with open(path, 'r') as f:
        data = json.load(f)
    steps = data.get("steps")
    if steps == "timeout":
        return None
    max_occupied = 0
    for timestep in data["steps"]:
        # Sum lengths of "path" lists for all operations in this timestep
        occupied = sum(len(op["path"]) for op in timestep)
        print(occupied)
        max_occupied = max(max_occupied, occupied)

    return max_occupied

def run_wisq_case(bench_path, bench_name, case_name, hbm_config, extra_wisq_args, run_idx):
    """Single benchmark/architecture run."""
    out_path = os.path.join(bench_output_dir, f"{bench_name}{case_name.replace(' ', '')}_run{run_idx}.out")
    log_path = os.path.join(bench_output_dir, f"{bench_name}{case_name.replace(' ', '')}_run{run_idx}.log")

    env = os.environ.copy()
    env["HBM_CONFIG"] = hbm_config

    cmd = [wisq_path, bench_path, "-op", out_path, "--mode", "scmr"] + extra_wisq_args
    # print(cmd)
    ok = run_and_stream(cmd, env, log_path)
    steps = load_steps(out_path) if ok else None
    routing_footprint = load_footprint(out_path) if ok else None

    return bench_name, case_name, run_idx, steps, routing_footprint

# === MAIN ===
def main():
    qasm_paths, qasm_names = get_qasm_files(benchmarks_dir)
    all_jobs = []

    print(f"🧠 Preparing jobs for {len(qasm_names)} benchmarks × {len(HBM_CASES)} architectures × {args.runs} runs")

    for bench_path, bench_name in zip(qasm_paths, qasm_names):
        for run_idx in range(1, args.runs + 1):
            for case_name, hbm_config, extra_wisq_args in HBM_CASES:
                all_jobs.append((bench_path, bench_name, case_name, hbm_config, extra_wisq_args, run_idx))

    print(f"🚀 Launching {len(all_jobs)} total runs with {args.parallel} parallel workers")

    results = []
    with ProcessPoolExecutor(max_workers=args.parallel) as executor:
        future_to_job = {executor.submit(run_wisq_case, *job): job for job in all_jobs}

        for i, future in enumerate(as_completed(future_to_job), start=1):
            bench_name, case_name, run_idx, steps, routing_footprint = future.result()
            print(f"[{i}/{len(all_jobs)}] ✅ {bench_name} | {case_name:<8} | run {run_idx} → {steps if steps is not None else 'timeout/error'} steps")
            results.append((bench_name, case_name, run_idx, steps, routing_footprint))

    # results: (bench_name, case_name, run_idx, steps, routing_footprint)

    steps = {}
    routing = {}
    benches = set()
    cases = set()

    for b, c, run, s, r in results:
        benches.add(b)
        cases.add(c)

        if s is not None:
            if (b, c) not in steps:
                steps[(b, c)] = []
            steps[(b, c)].append(s)

        if r is not None:
            if (b, c) not in routing:
                routing[(b, c)] = []
            routing[(b, c)].append(r)

    benches = sorted(benches)
    cases = sorted(cases)

    def write_csv(filename, data):
        with open(filename, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["bench_name"] + cases)
            for b in benches:
                row = [b]
                for c in cases:
                    vals = data.get((b, c), [])
                    row.append(statistics.mean(vals) if vals else "")
                w.writerow(row)

    write_csv("num_steps.csv", steps)
    write_csv("routing_footprint.csv", routing)

if __name__ == "__main__":
    main()
