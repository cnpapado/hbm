import os
import subprocess
import json
import argparse
import statistics

# === CLI ===
parser = argparse.ArgumentParser(description="Run WISQ benchmarks")
parser.add_argument("--tmr", type=str, default="30")
parser.add_argument("--fixed-mapping", action="store_true")
parser.add_argument("--runs", type=int, default=1)
args = parser.parse_args()

wisq_path = "wisq"
apt_path = "/home/c/synthetiq/bin/main" if os.path.expanduser("~").split("/")[-1] == "c" else None
benchmarks_dir = "../quantum-compiler-benchmark-circuits/jku_suite"

# === Setup output ===
output_root = os.path.join(os.getcwd(), "output")
bench_folder_name = os.path.basename(os.path.normpath(benchmarks_dir))
bench_output_dir = os.path.join(output_root, bench_folder_name)
os.makedirs(bench_output_dir, exist_ok=True)

# === Helpers ===
def get_qasm_files(directory):
    qasms = []
    names = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".qasm"):
                qasms.append(os.path.join(root, f))
                names.append(os.path.splitext(f)[0])
    return qasms, names


def run_and_stream(cmd, env):
    print(f"\n🧠 Running: {' '.join(cmd)}\n")
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        print(line, end="")
    p.wait()
    print(f"✅ Finished with exit code {p.returncode}")
    return p.returncode == 0


def load_steps(path):
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


def run_wisq_case(bench_path, out_path, env_overrides, extra_args):
    env = os.environ.copy()
    env.update(env_overrides)

    cmd = [
        wisq_path, bench_path, "--mode", "scmr",
        "-arch", "compact_layout",
        "-op", out_path, "-tmr", args.tmr
    ]

    if args.fixed_mapping and "magic_out" in extra_args:
        cmd += ["--fixed-mapping", extra_args["magic_out"]]

    if apt_path:
        cmd += ["-apt", apt_path]

    if "magic-sharing" in extra_args:
        cmd += ["--magic-state-sharing", extra_args["magic-sharing"]]

    run_and_stream(cmd, env)
    return load_steps(out_path)


# === HBM configurations to run ===
HBM_CASES = [
    ("magic", {"HBM_ARCH": "NO_HBM", "BENDS": "True"}, {}),
    ("hbmA",  {"HBM_ARCH": "ARCH_A", "BENDS": "True"}, {}),
    ("hbmB_shared2",  {"HBM_ARCH": "ARCH_B", "BENDS": "False"}, {"magic-sharing": "shared_2"}),
    ("hbmC_shared2",  {"HBM_ARCH": "ARCH_C", "BENDS": "False"}, {"magic-sharing": "shared_2"}),
    ("hbmB_shared4",  {"HBM_ARCH": "ARCH_B", "BENDS": "False"}, {"magic-sharing": "shared_4"}),
    ("hbmC_shared4",  {"HBM_ARCH": "ARCH_C", "BENDS": "False"}, {"magic-sharing": "shared_4"}),
]


# === MAIN LOOP ===
summary_path = os.path.join(bench_output_dir, "results_summary.txt")
with open(summary_path, "w") as summary:

    qasm_paths, qasm_names = get_qasm_files(benchmarks_dir)

    for bench_path, bench_name in zip(qasm_paths, qasm_names):

        print(f"\n==============================")
        print(f"  🧪 Benchmark: {bench_name}")
        print(f"==============================\n")

        # store per-run measurements
        acc = {key: [] for key, _, _ in HBM_CASES}
        magic_outputs = []

        for run_idx in range(1, args.runs + 1):
            print(f"\n=== Run {run_idx}/{args.runs} ===")

            # --- Execute all cases ---
            for case_name, env_vars, extras in HBM_CASES:
                outfile = os.path.join(bench_output_dir, f"{bench_name}_{case_name}_run{run_idx}.out")

                # magic output used for --fixed-mapping
                if case_name == "magic":
                    magic_outputs.append(outfile)
                    extras = {"magic_out": outfile}

                steps = run_wisq_case(bench_path, outfile, env_vars, extras)
                acc[case_name].append(steps)

                print(f"➡️  {bench_name}/{case_name}/run{run_idx}: {steps}\n")

            print("--------------------------------------")

        # ⬇ compute averages
        averages = {case: (statistics.mean(v) if any(v) else None) for case, v in acc.items()}

        # ⬇ log immediately
        line = (
            f"{bench_name:20s} | "
            f"magic={averages['magic']}  "
            f"hbmA={averages['hbmA']}  "
            f"hbmB_shared2={averages['hbmB_shared2']}  "
            f"hbmC_shared2={averages['hbmC_shared2']}  "
            f"hbmB_shared4={averages['hbmB_shared4']}  "
            f"hbmC_shared4={averages['hbmC_shared4']}\n"
        )

        print(line)
        summary.write(line)

print(f"\n✅ Summary saved at: {summary_path}\n")
