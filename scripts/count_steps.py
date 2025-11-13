import os
import subprocess
import json
import argparse
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

# === CLI ===
parser = argparse.ArgumentParser(description="Run WISQ benchmarks in parallel")
parser.add_argument("--runs", type=int, default=1)
parser.add_argument("--parallel", type=int, default=8, help="Number of parallel processes")
args = parser.parse_args()

wisq_path = "wisq"
benchmarks_dir = "../quantum-compiler-benchmark-circuits/jku_suite"

# === Setup output ===
output_root = os.path.join(os.getcwd(), "output_parallel")
bench_folder_name = os.path.basename(os.path.normpath(benchmarks_dir))
bench_output_dir = os.path.join(output_root, bench_folder_name)
os.makedirs(bench_output_dir, exist_ok=True)

# === HBM configurations ===
HBM_CASES = [
    ("NO_HBM", "nohbm"),
    ("ARCH_A", "hbmA"),
    ("ARCH_B", "hbmB"),
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

def run_wisq_case(bench_path, bench_name, case_name, hbm_arch, run_idx):
    """Single benchmark/architecture run."""
    out_path = os.path.join(bench_output_dir, f"{bench_name}_{case_name}_run{run_idx}.out")
    log_path = os.path.join(bench_output_dir, f"{bench_name}_{case_name}_run{run_idx}.log")

    env = os.environ.copy()
    env["HBM_ARCH"] = hbm_arch

    cmd = [wisq_path, bench_path, "-op", out_path, "--mode", "scmr"]

    ok = run_and_stream(cmd, env, log_path)
    steps = load_steps(out_path) if ok else None

    return bench_name, case_name, run_idx, steps

# === MAIN ===
def main():
    qasm_paths, qasm_names = get_qasm_files(benchmarks_dir)
    all_jobs = []

    print(f"🧠 Preparing jobs for {len(qasm_names)} benchmarks × {len(HBM_CASES)} architectures × {args.runs} runs")

    for bench_path, bench_name in zip(qasm_paths, qasm_names):
        for run_idx in range(1, args.runs + 1):
            for hbm_arch, case_name in HBM_CASES:
                all_jobs.append((bench_path, bench_name, case_name, hbm_arch, run_idx))

    print(f"🚀 Launching {len(all_jobs)} total runs with {args.parallel} parallel workers")

    results = []
    with ProcessPoolExecutor(max_workers=args.parallel) as executor:
        future_to_job = {executor.submit(run_wisq_case, *job): job for job in all_jobs}

        for i, future in enumerate(as_completed(future_to_job), start=1):
            bench_name, case_name, run_idx, steps = future.result()
            print(f"[{i}/{len(all_jobs)}] ✅ {bench_name} | {case_name:<8} | run {run_idx} → {steps if steps is not None else 'timeout/error'} steps")
            results.append((bench_name, case_name, run_idx, steps))

    # === Summarize results ===
    summary_path = os.path.join(bench_output_dir, "results_summary.txt")
    bench_modes = {}

    for bench, case, _, steps in results:
        bench_modes.setdefault(bench, {}).setdefault(case, []).append(steps)

    with open(summary_path, "w") as f:
        header = f"{'Benchmark':<20} | " + "  ".join([f"{name:<8}" for _, name in HBM_CASES])
        f.write(header + "\n" + "-" * len(header) + "\n")

        for bench, cases in sorted(bench_modes.items()):
            line = f"{bench:<20} | "
            for _, name in HBM_CASES:
                vals = [v for v in cases.get(name, []) if v is not None]
                avg = round(statistics.mean(vals), 1) if vals else "—"
                line += f"{str(avg):<8}  "
            f.write(line + "\n")
            print(line)

    print(f"\n✅ Summary saved at: {summary_path}")

if __name__ == "__main__":
    main()
