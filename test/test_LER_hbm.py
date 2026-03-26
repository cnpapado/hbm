import stim
import pymatching
import numpy as np
import matplotlib.pyplot as plt

# ── Helpers ─────────────────────────────────────────────────────────────────

def measure_ler(circuit: stim.Circuit, shots: int) -> float:
    dem = circuit.detector_error_model(decompose_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler()
    detection_events, observable_flips = sampler.sample(
        shots=shots, separate_observables=True
    )
    predictions = matcher.decode_batch(detection_events)
    return np.sum(predictions != observable_flips) / shots


def make_baseline_circuit(d: int, p: float) -> stim.Circuit:
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=d,
        rounds=d,
        after_clifford_depolarization=p,
        after_reset_flip_probability=p,
        before_measure_flip_probability=p,
    )


def make_hbm_circuit(d: int, p: float, p_prime: float, sharing_ratio: int) -> stim.Circuit:
    base = make_baseline_circuit(d, p)
    num_data_qubits = d * d
    n_affected = max(1, num_data_qubits // sharing_ratio)
    affected_qubits = list(range(n_affected))
    p_prime = min(p_prime, 0.499)   # ← ADD THIS LINE
    new_circuit = stim.Circuit()
    for instruction in base.flattened():
        new_circuit.append(instruction)
        # Apply the correlated vertical noise penalty on every TICK
        if instruction.name == "TICK":
            new_circuit.append("DEPOLARIZE1", affected_qubits, p_prime)
    return new_circuit


# ── Parameters ───────────────────────────────────────────────────────────────

distances      = [3, 5, 7, 9, 11]
error_rates    = np.logspace(-3, -1, 15)
sharing_ratios = [2, 4, 8, 16]
scenarios      = {"p'=p": 1, "p'=5p": 5, "p'=10p": 10}

# NOTE: Set to 10,000 for testing so it finishes quickly. 
# Change to 100,000 or 1,000,000 for the final MICRO paper run.
shots          = 100_000 


# ── Baseline ─────────────────────────────────────────────────────────────────

print("=" * 60)
print("Running baseline (no HBM)...")
print("=" * 60)

baseline = {d: [] for d in distances}

for d in distances:
    for p in error_rates:
        circuit = make_baseline_circuit(d, p)
        ler = measure_ler(circuit, shots)
        baseline[d].append(ler)
        print(f"  baseline  d={d:2d}  p={p:.5f}  LER={ler:.6f}")

print()


# ── HBM inter-layer sweep ─────────────────────────────────────────────────────

print("=" * 60)
print("Running HBM inter-layer noise sweep...")
print("=" * 60)

# results[scenario_name][sharing_ratio][d] = list of LER values (one per error_rate)
results = {}

for scenario_name, mult in scenarios.items():
    results[scenario_name] = {}
    for sr in sharing_ratios:
        results[scenario_name][sr] = {d: [] for d in distances}
        for d in distances:
            for p in error_rates:
                p_prime = p * mult
                circuit = make_hbm_circuit(d, p, p_prime, sr)
                ler = measure_ler(circuit, shots)
                results[scenario_name][sr][d].append(ler)
                print(f"  {scenario_name:7s}  shared_{sr:<2d}  d={d:2d}  p={p:.5f}  p'={p_prime:.5f}  LER={ler:.6f}")
    print()


# ── Save raw data ─────────────────────────────────────────────────────────────

np.save("e1_baseline.npy", baseline)
np.save("e1_results.npy", results)
np.save("e1_error_rates.npy", error_rates)
print("Raw data saved to e1_baseline.npy, e1_results.npy, e1_error_rates.npy")
print()


# ── Plots ─────────────────────────────────────────────────────────────────────

colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(distances)))

for scenario_name in scenarios:
    fig, axes = plt.subplots(1, 4, figsize=(18, 5), sharey=True)
    fig.suptitle(f"HBM LER Threshold — {scenario_name}", fontsize=13)

    for ax, sr in zip(axes, sharing_ratios):
        # Baseline (dashed black)
        for i, d in enumerate(distances):
            ax.loglog(error_rates, baseline[d],
                    color=colors[i], linestyle='--', linewidth=1, alpha=0.4)
        # HBM (solid)
        for i, d in enumerate(distances):
            ax.loglog(error_rates, results[scenario_name][sr][d],
                    color=colors[i], linestyle='-', marker='o',
                    markersize=3, linewidth=1.5, label=f'd={d}')

        ax.axvline(x=0.01, color='gray', linestyle=':', alpha=0.6, label='p_th≈0.01')
        ax.set_title(f"shared_{sr}", fontsize=11)
        ax.set_xlabel("Physical Error Rate p", fontsize=9)
        ax.grid(True, which='both', alpha=0.2)

    axes[0].set_ylabel("Logical Error Rate (per code cycle)", fontsize=9)
    axes[0].legend(fontsize=7, loc='lower right')

    # Add note: dashed = baseline, solid = HBM
    fig.text(0.5, 0.01,
            "Dashed = baseline (no HBM),  Solid = HBM with inter-layer noise",
            ha='center', fontsize=8, style='italic')

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    # fname = f"e1_{scenario_name.replace(\"'=\", '').replace(' ', '_')}.png"
    # Clean the name outside of the f-string to avoid quote escaping issues
    clean_name = scenario_name.replace("'=", "").replace(" ", "_")
    fname = f"e1_{clean_name}.png"
    plt.savefig(fname, dpi=150)
    print(f"Saved {fname}")


# ── Summary plot: LER ratio at operating point p=0.001, d=7 ──────────────────

fig, ax = plt.subplots(figsize=(8, 5))

p_op_idx = np.argmin(np.abs(error_rates - 0.005))
d_op = 7
x = np.arange(len(sharing_ratios))
width = 0.25
scenario_list = list(scenarios.keys())

for i, scenario_name in enumerate(scenario_list):
    ratios = []
    for sr in sharing_ratios:
        hbm_ler  = results[scenario_name][sr][d_op][p_op_idx]
        base_ler = baseline[d_op][p_op_idx]
        ratio = hbm_ler / base_ler if base_ler > 0 else 1.0
        ratios.append(ratio)
    ax.bar(x + i * width, ratios, width, label=scenario_name)

ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1.2, label='baseline')

# [FIX] Mathematically center the x-ticks under the grouped bars
center_offset = width * (len(scenario_list) - 1) / 2
ax.set_xticks(x + center_offset)
ax.set_xticklabels([f"shared_{sr}" for sr in sharing_ratios])

ax.set_ylabel("LER(HBM) / LER(baseline)")
ax.set_title(f"LER overhead from inter-layer ops  (d={d_op}, p=0.001)")
ax.legend()
ax.grid(True, axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig("e1_summary_ratio.png", dpi=150)
print("Saved e1_summary_ratio.png")

print()
print("All done.")