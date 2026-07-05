import stim
import pymatching
import numpy as np
import matplotlib.pyplot as plt

def measure_ler(circuit: stim.Circuit, shots: int =
100_000) -> float:
    """Measure logical error rate for a given circuit."""
    dem = circuit.detector_error_model(decompose_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler()
    detection_events, observable_flips = sampler.sample(
        shots=shots, separate_observables=True
    )
    predictions = matcher.decode_batch(detection_events)
    num_errors = np.sum(predictions != observable_flips)
    return num_errors / shots

def baseline_circuit(d: int, p: float) -> stim.Circuit:
    """Standard rotated surface code memory experiment."""
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=d,
        rounds=d,          # d rounds = one code cycle
        after_clifford_depolarization=p,
        after_reset_flip_probability=p,
        before_measure_flip_probability=p,
    )

# Sweep parameters
distances = [3, 5, 7, 9, 11]
error_rates = np.logspace(-3, -1, 20)  # 0.001 to 0.1
shots = 100_000

results = {}
for d in distances:
    results[d] = []
    for p in error_rates:
        circuit = baseline_circuit(d, p)
        ler = measure_ler(circuit, shots)
        results[d].append(ler)
        print(f"d={d}, p={p:.4f}, LER={ler:.6f}")

# Plot threshold curves
fig, ax = plt.subplots(figsize=(7, 5))
for d in distances:
    ax.loglog(error_rates, results[d], marker='o',
label=f'd={d}')
ax.axvline(x=0.01, color='gray', linestyle='--',
label='p_th ≈ 0.01')
ax.set_xlabel("Physical Error Rate p")
ax.set_ylabel("Logical Error Rate (per code cycle)")
ax.set_title("Baseline: 2D Surface Code")
ax.legend()
plt.tight_layout()
plt.savefig("baseline_threshold.png", dpi=150)