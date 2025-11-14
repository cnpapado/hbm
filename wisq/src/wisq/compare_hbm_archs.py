import os
import subprocess
from count_steps import count_steps

# --- CONFIG ---
JCU_SUITE_DIR = "/home/george/hbm/quantum-compiler-benchmark-circuits/jku_suite"
OUTPUT_DIR = "/home/george/hbm/quantum-compiler-benchmark-circuits/results_v3"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_wisq(benchmark_path, arch_mode, output_json):
    """Run WISQ for a single benchmark and return the output JSON path."""
    env = os.environ.copy()
    env["HBM_ARCH"] = arch_mode

    cmd = [
        "wisq",
        benchmark_path,
        "--mode", "scmr",
        "--arch", "compact_layout",
        "-tmr", "4",
        "-op", output_json,  # ✅ correct output flag
    ]

    print(f"\n🚀 Running {os.path.basename(benchmark_path)} with HBM_ARCH={arch_mode}")
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ WISQ failed for {arch_mode} on {benchmark_path}: {e}")
        return None

    return output_json if os.path.exists(output_json) else None


def main():
    benchmarks = [f[:-5] for f in os.listdir(JCU_SUITE_DIR) if f.endswith(".qasm")]
    results = []

    print("\n==============================")
    print(f"🧠 Running WISQ Benchmarks from: {JCU_SUITE_DIR}")
    print("==============================\n")

    for bench in benchmarks:
        bench_path = os.path.join(JCU_SUITE_DIR, f"{bench}.qasm")
        print(f"\n────────────────────────────────────────────")
        print(f"Benchmark: {bench}")
        print("────────────────────────────────────────────")

        bench_results = {}

        for mode in ["NO_HBM", "ARCH_A", "ARCH_B", "ARCH_C"]:
            output_json = os.path.join(OUTPUT_DIR, f"{bench}_{mode}.json")
            json_path = run_wisq(bench_path, mode, output_json)

            steps = count_steps(json_path) if json_path else None
            bench_results[mode] = steps

            # ✅ Print live result for this mode
            if steps is not None:
                print(f"   → {mode:<8}: {steps} steps")
            else:
                print(f"   → {mode:<8}: timeout/error")

            results.append((bench, mode, steps))

        # ✅ Print quick comparison for the benchmark
        no_hbm = bench_results.get("NO_HBM")
        arch_a = bench_results.get("ARCH_A")
        arch_b = bench_results.get("ARCH_B")
        arch_c = bench_results.get("ARCH_C")
        print(f"✅ {bench:<25} NO_HBM: {no_hbm if no_hbm is not None else '—'} | ARCH_A: {arch_a if arch_a is not None else '—'} | ARCH_B: {arch_b if arch_b is not None else '—'} | ARCH_C: {arch_c if arch_c is not None else '—'}")

    # ✅ Final summary
    print("\n\n📊 Summary of All Benchmarks")
    print("───────────────────────────────")
    print(f"{'Benchmark':<25} {'NO_HBM':>10} {'ARCH_A':>10} {'ARCH_B':>10} {'ARCH_C':>10}")
    print("───────────────────────────────")

    summary_path = os.path.join(OUTPUT_DIR, "steps_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"Benchmark Steps Summary for {OUTPUT_DIR}\n")
        f.write("=" * 65 + "\n")
        f.write(f"{'Benchmark':<25} {'NO_HBM':>10} {'ARCH_A':>10} {'ARCH_B':>10} {'ARCH_C':>10}\n")
        f.write("-" * 65 + "\n")

        for bench, mode_group in sorted({b for b, _, _ in results}):
            pass  # filler for clarity

        bench_modes = {}
        for bench, mode, steps in results:
            if bench not in bench_modes:
                bench_modes[bench] = {}
            bench_modes[bench][mode] = steps

        for bench in sorted(bench_modes.keys()):
            no_hbm = bench_modes[bench].get("NO_HBM")
            arch_a = bench_modes[bench].get("ARCH_A")
            arch_b = bench_modes[bench].get("ARCH_B")
            arch_c = bench_modes[bench].get("ARCH_C")
            line = f"{bench:<25} {str(no_hbm if no_hbm is not None else '—'):>10} {str(arch_a if arch_a is not None else '—'):>10} {str(arch_b if arch_b is not None else '—'):>10} {str(arch_c if arch_c is not None else '—'):>10}"
            print(line)
            f.write(line + "\n")

        f.write("=" * 65 + "\n")

    print(f"\n✅ Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
