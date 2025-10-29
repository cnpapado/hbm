import os, subprocess, json, argparse, statistics

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

# extract the last subdirectory name from the benchmarks path (e.g. "autobraid")
benchmark_folder_name = os.path.basename(os.path.normpath(benchmarks))

def run_command(cmd):
    print(f"\n🧠 Running: {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    print(f"\n✅ Command finished with exit code {process.returncode}\n")
    return process.returncode

for input_path, bench_name in zip(*all_qasm_files_in_dir(benchmarks)):
    #print(bench_path, bench_name)

    print(f"\n=== 🧩 Transpiling benchmark: {bench_name} ===\n")

    # output file paths (same dirs as benchmarks)
    base, ext = os.path.splitext(input_path)
    out_path = f"{base}_opt{ext}"
        
    wisq_cmd = [
        wisq_path, input_path, "--mode", "opt", "--target_gateset", "CLIFFORDT", "-arch", "compact_layout",
        "-op", out_path, "-ap", "1e-10", "-ot", "10"
    ] + (["-apt", apt_path] if apt_path else [])

    
    run_command(wisq_cmd)

        