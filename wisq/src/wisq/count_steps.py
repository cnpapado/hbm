import os
import json
import sys
from collections import defaultdict


def count_steps(filepath):
    """Return total number of routing steps from a WISQ JSON result file."""
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        print(f"❌ File not found: {abs_path}")
        return None

    try:
        with open(abs_path, "r") as f:
            data = json.load(f)

        steps = data.get("steps", None)
        if steps is None:
            print(f"⚠️ No 'steps' field in {abs_path}")
            return None

        if steps == "timeout":
            print(f"⚠️ Timeout encountered in {abs_path}")
            return None

        if isinstance(steps, list):
            return len(steps)

        print(f"⚠️ Unexpected 'steps' type in {abs_path}: {type(steps)}")
        return None

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error in {abs_path}: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Could not parse {abs_path}: {e}")
        return None


def parse_benchmark_and_mode(filename):
    """Extract benchmark name and mode robustly, regardless of underscores."""
    base = filename[:-5]  # remove .json
    for mode in ["ARCH_A", "ARCH_B", "ARCH_C", "NO_HBM"]:
        if base.endswith("_" + mode):
            return base[: -len("_" + mode)], mode
    return base, "UNKNOWN"


def count_steps_in_directory(directory):
    """Traverse a directory, count steps for all benchmarks, and save summary."""
    abs_dir = os.path.abspath(directory)
    if not os.path.isdir(abs_dir):
        print(f"❌ Not a valid directory: {abs_dir}")
        return

    json_files = sorted([f for f in os.listdir(abs_dir) if f.endswith(".json")])
    if not json_files:
        print(f"⚠️ No JSON files found in {abs_dir}")
        return

    results = defaultdict(dict)
    total_timeouts = 0
    total_successes = 0

    print(f"\n📂 Directory: {abs_dir}")
    print("=" * 75)
    print(f"{'Benchmark':<30} {'NO_HBM':>10} {'ARCH_A':>10} {'ARCH_B':>10} {'ARCH_C':>10}")
    print("-" * 75)

    # Collect results
    for filename in json_files:
        filepath = os.path.join(abs_dir, filename)
        steps = count_steps(filepath)
        bench, mode = parse_benchmark_and_mode(filename)
        results[bench][mode] = steps

        if steps is None:
            total_timeouts += 1
        else:
            total_successes += 1

    # Print table of results
    valid_rows = 0
    for bench in sorted(results.keys()):
        no_hbm = results[bench].get("NO_HBM")
        arch_a = results[bench].get("ARCH_A")
        arch_b = results[bench].get("ARCH_B")
        arch_c = results[bench].get("ARCH_C")

        if all(v is None for v in [no_hbm, arch_a, arch_b, arch_c]):
            continue

        print(f"{bench:<30} "
              f"{str(no_hbm if no_hbm is not None else '—'):>10} "
              f"{str(arch_a if arch_a is not None else '—'):>10} "
              f"{str(arch_b if arch_b is not None else '—'):>10} "
              f"{str(arch_c if arch_c is not None else '—'):>10}")
        valid_rows += 1

    # Save summary file
    summary_path = os.path.join(abs_dir, "steps_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"Benchmark Steps Summary for {abs_dir}\n")
        f.write("=" * 75 + "\n")
        f.write(f"{'Benchmark':<30} {'NO_HBM':>10} {'ARCH_A':>10} {'ARCH_B':>10} {'ARCH_C':>10}\n")
        f.write("-" * 75 + "\n")

        for bench in sorted(results.keys()):
            no_hbm = results[bench].get("NO_HBM")
            arch_a = results[bench].get("ARCH_A")
            arch_b = results[bench].get("ARCH_B")
            arch_c = results[bench].get("ARCH_C")

            if all(v is None for v in [no_hbm, arch_a, arch_b, arch_c]):
                continue

            f.write(f"{bench:<30} "
                    f"{str(no_hbm if no_hbm is not None else '—'):>10} "
                    f"{str(arch_a if arch_a is not None else '—'):>10} "
                    f"{str(arch_b if arch_b is not None else '—'):>10} "
                    f"{str(arch_c if arch_c is not None else '—'):>10}\n")

        f.write("\n" + "=" * 75 + "\n")
        f.write(f"✅ Successful benchmarks: {total_successes}\n")
        f.write(f"⚠️ Timed out or missing:   {total_timeouts}\n")
        f.write(f"📊 Benchmarks reported:   {valid_rows}\n")

    print("\n" + "=" * 75)
    print(f"✅ Successful benchmarks: {total_successes}")
    print(f"⚠️ Timed out or missing:   {total_timeouts}")
    print(f"📊 Benchmarks reported:   {valid_rows}")
    print(f"📝 Summary saved to: {summary_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python count_steps.py <path_to_json_or_directory>")
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isdir(path):
        count_steps_in_directory(path)
    else:
        steps = count_steps(path)
        if steps is not None:
            print(f"✅ {path}: {steps} steps")
        else:
            print(f"⚠️ Could not read steps from {path}")
