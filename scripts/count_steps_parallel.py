import os, subprocess, json, argparse, statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

# === Command-line arguments ===
parser = argparse.ArgumentParser(description="Run WISQ benchmarks for hbm and magic states.")
parser.add_argument("--tmr", type=str, default="180", help="TMR value to use (default: 30)")
parser.add_argument("--fixed-mapping", action="store_true", help="For hbm use the same mapping from the magic run")
parser.add_argument("--runs", type=int, default=1, help="Number of times to run each benchmark before averaging results")
args = parser.parse_args()

wisq_path = "wisq"
# use apt_path only in Kostas laptop
apt_path = "/home/c/synthetiq/bin/main" if os.path.expanduser("~").split('/')[-1] == 'c' else None
benchmarks = "../quantum-compiler-benchmark-circuits/jku_suite"

# === Helpers ===
def all_qasm_files_in_dir(dir):
    paths, names = [], []
    for dirpath, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            if filename.endswith(".qasm"):
                full_path = os.path.join(dirpath, filename)
                name = os.path.splitext(filename)[0]
                paths.append(full_path)
                names.append(name)
    return paths, names


def run_command(cmd, env):
    """Run a command and wait for it to complete."""
    print(f"\n🧠 Running: {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    print(f"✅ Command finished with exit code {process.returncode}\n")
    return process.returncode


def count_steps(filepath):
    """Count number of steps in JSON result."""
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


# === Prepare directories ===
output_dir = os.path.join(os.getcwd(), "output_180")
benchmark_folder_name = os.path.basename(os.path.normpath(benchmarks))
bench_output_dir = os.path.join(output_dir, benchmark_folder_name)
os.makedirs(bench_output_dir, exist_ok=True)

env = os.environ.copy()
results = []


# === Run all benchmarks ===
for bench_path, bench_name in zip(*all_qasm_files_in_dir(benchmarks)):
    print(f"\n=== 🧩 Starting benchmark: {bench_name} ({args.runs} runs) ===\n")

    magic_values, hbm_values = [], []

    # define one function to run a single run_id
    def run_single(run_idx):
        """Run both magic and hbm for a single iteration index."""
        run_env = env.copy()

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

        # run "magic" version
        run_env["HBM_ARCH"] = "NO_HBM"
        run_command(magic_cmd, env=run_env)
        magic_steps = count_steps(magic_out)

        # run "hbm" version
        run_env["HBM_ARCH"] = "ARCH_A"
        run_command(hbm_cmd, env=run_env)
        hbm_steps = count_steps(hbm_out)

        return (magic_steps, hbm_steps)

    # === Parallel execution per benchmark ===
    if args.runs > 1:
        with ProcessPoolExecutor(max_workers=args.runs) as executor:
            futures = {executor.submit(run_single, i): i for i in range(args.runs)}
            for future in as_completed(futures):
                try:
                    magic_steps, hbm_steps = future.result()
                    if magic_steps is not None:
                        magic_values.append(magic_steps)
                    if hbm_steps is not None:
                        hbm_values.append(hbm_steps)
                except Exception as e:
                    print(f"⚠️ Run {futures[future]} failed: {e}")
    else:
        # single run (no parallelism)
        m, h = run_single(0)
        if m is not None:
            magic_values.append(m)
        if h is not None:
            hbm_values.append(h)

    # === Average results for this benchmark ===
    avg_magic = statistics.mean(magic_values) if magic_values else None
    avg_hbm   = statistics.mean(hbm_values) if hbm_values else None
    results.append((bench_name, avg_magic, avg_hbm))

    print(f"✅ Completed benchmark {bench_name}: magic={avg_magic}, hbm={avg_hbm}\n")


# === Save all results ===
results_txt = os.path.join(bench_output_dir, "results_summary.txt")
with open(results_txt, "w") as f:
    f.write("=== Results Summary ===\n\n")
    for bench, magic_steps, hbm_steps in results:
        line = f"{bench:20s}  magic={magic_steps}  hbm={hbm_steps}\n"
        print(line, end="")
        f.write(line)

print(f"\n✅ Results saved to {results_txt}\n")
