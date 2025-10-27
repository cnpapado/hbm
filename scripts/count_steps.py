import os, subprocess, json, argparse, statistics

# === Command-line arguments ===
parser = argparse.ArgumentParser(description="Run WISQ benchmarks for hbm and magic states.")
parser.add_argument("--tmr", type=str, default="30", help="TMR value to use (default: 30)")
parser.add_argument("--fixed-mapping", action="store_true", help="For hbm use the same mapping from the magic run")
parser.add_argument("--runs", type=int, default=1, help="Number of times to run each benchmark before averaging results")
args = parser.parse_args()

wisq_path = "wisq"
# use apt_path only in kostas laptop
apt_path = "/home/c/synthetiq/bin/main" if os.path.expanduser("~").split('/')[-1] == 'c' else None
benchmarks = "../quantum-compiler-benchmark-circuits/jku_suite"


def all_qasm_files_in_dir(dir):
    paths = []
    names = []

    for dirpath, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            if filename.endswith(".qasm"):
                full_path = os.path.join(dirpath, filename)
                name = os.path.splitext(filename)[0]
                paths.append(full_path)
                names.append(name)

    return paths, names


# ✅ Ensure output directory exists
output_dir = os.path.join(os.getcwd(), "output")
# extract the last subdirectory name from the benchmarks path (e.g. "autobraid")
benchmark_folder_name = os.path.basename(os.path.normpath(benchmarks))

# create a dedicated output subfolder (e.g. output/autobraid)
bench_output_dir = os.path.join(output_dir, benchmark_folder_name)
os.makedirs(bench_output_dir, exist_ok=True)

def run_command(cmd, env):
    print(f"\n🧠 Running: {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    print(f"\n✅ Command finished with exit code {process.returncode}\n")
    return process.returncode

def count_steps(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath) as f:
            data = json.load(f)
            steps = data.get("steps", [])
            if steps == "timeout":
                return None
        return len(steps)
    except Exception as e:
        print(f"⚠️ Could not parse {filepath}: {e}")
        return None

env = os.environ.copy()
results = []

for bench_path, bench_name in zip(*all_qasm_files_in_dir(benchmarks)):
    #print(bench_path, bench_name)

    magic_values, hbm_values = [], []

    for run_idx in range(args.runs):
        print(f"\n=== 🧩 Running benchmark: {bench_name} (Run {run_idx + 1}/{args.runs}) ===\n")

        # output file paths (inside ./output/)
        magic_out = os.path.join(bench_output_dir, f"{bench_name}_magic_run{run_idx+1}.out")
        hbm_out   = os.path.join(bench_output_dir, f"{bench_name}_hbm_run{run_idx+1}.out")

        magic_cmd = [
            wisq_path, bench_path, "--mode", "scmr", "-arch", "compact_layout",
            "-op", magic_out, "-ap", "1e-10", "-ot", "10", "-tmr", args.tmr
        ] + (["-apt", apt_path] if apt_path else [])

        hbm_cmd = [
            wisq_path, bench_path, "--mode", "scmr", "-arch", "compact_layout",
            "-op", hbm_out, "-ap", "1e-10", "-ot", "10", "-tmr", args.tmr
        ] + (["--fixed-mapping", magic_out] if args.fixed_mapping else []) \
          + (["-apt", apt_path] if apt_path else [])

        env["HBM_ARCH"] = "NO_HBM"
        run_command(magic_cmd, env=env)

        env["HBM_ARCH"] = "ARCH_A"
        run_command(hbm_cmd, env=env)

        # count steps
        magic_steps = count_steps(magic_out)
        hbm_steps = count_steps(hbm_out)
        if magic_steps is not None:
            magic_values.append(magic_steps)
        if hbm_steps is not None:
            hbm_values.append(hbm_steps)

    # average results
    avg_magic = statistics.mean(magic_values) if magic_values else None
    avg_hbm = statistics.mean(hbm_values) if hbm_values else None
    results.append((bench_name, avg_magic, avg_hbm))

# === Save results ===
results_txt = os.path.join(bench_output_dir, "results_summary.txt")

with open(results_txt, "w") as f:
    f.write("=== Results Summary ===\n\n")
    for bench, magic_steps, hbm_steps in results:
        line = f"{bench:20s}  magic={magic_steps}  hbm={hbm_steps}\n"
        print(line, end="")   # still prints to terminal
        f.write(line)

print(f"\n✅ Results saved to {results_txt}\n")
