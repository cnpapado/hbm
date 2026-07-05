"""
E1 HBM Inter-Layer Noise Threshold Analysis
============================================
Steps 3-6: load circuit -> identify bridge ancillas -> inject p' noise ->
           decode with PyMatching -> plot LER threshold curves.

Usage:
    python steps3-6.py

Auto-discovers h5 files named  ls_circuit_{d}_{p}_z.h5  in H5_DIR.
Generate them with:
    python decoder_bench/generator.py --code=ls --basis=z --noise=circuit \
        -d 5 -p <p> --records=100000
"""

import h5py
import re
import stim
import pymatching
import numpy as np
import matplotlib.pyplot as plt
import math
import json
from pathlib import Path

# ── Publication style (matches other HBM plots) ───────────────────────────────
plt.rcParams.update({
    "font.family":       "serif",
    "font.size":         50,
    "axes.titlesize":    50,
    "axes.labelsize":    50,
    "axes.labelweight":  "bold",
    "axes.titleweight":  "bold",
    "axes.linewidth":    2.0,
    "xtick.labelsize":   50,
    "ytick.labelsize":   50,
    "xtick.major.size":  10,
    "xtick.major.width": 2,
    "ytick.major.size":  10,
    "ytick.major.width": 2,
    "savefig.dpi":       300,
    "pdf.fonttype":      42,
    "ps.fonttype":       42,
    "text.usetex":       False,
})

# ── Sweep parameters ──────────────────────────────────────────────────────────
DISTANCES      = [3, 5, 7, 9]
P_PRIME_MULTS  = [1, 5, 10]      # p' = mult * p
SHARING_RATIOS = [2, 4, 8, 16]
NUM_SHOTS      = 100_000
H5_DIR         = Path(".")        # directory containing the .h5 files
OUT_DIR        = Path("e1_plots")
RESULTS_FILE   = OUT_DIR / "e1_results.json"

OUT_DIR.mkdir(exist_ok=True)


# ── Auto-discover available (d, p) pairs from h5 filenames ───────────────────
_H5_PATTERN = re.compile(r"ls_circuit_(\d+)_([0-9.eE+\-]+)_z\.h5$")

def discover_h5_files(h5_dir: Path) -> dict:
    """
    Scan h5_dir for files matching ls_circuit_{d}_{p}_z.h5.
    Returns {d: [p_float, ...]} with p values sorted ascending.
    Only includes distances listed in DISTANCES.
    """
    found: dict = {d: [] for d in DISTANCES}
    for path in sorted(h5_dir.glob("ls_circuit_*_z.h5")):
        m = _H5_PATTERN.match(path.name)
        if not m:
            continue
        d, p = int(m.group(1)), float(m.group(2))
        if d in found:
            found[d].append(p)
    for d in found:
        found[d] = sorted(found[d])
    return found


# ── Step 3a: Load Stim circuit from h5 ───────────────────────────────────────
def load_circuit(h5_path: Path) -> stim.Circuit:
    with h5py.File(h5_path, "r") as f:
        raw = f["circuit"][()]
        text = raw.decode("utf-8") if isinstance(raw, (bytes, np.bytes_)) else str(raw)
    return stim.Circuit(text)


# ── Step 3b: Identify bridge ancilla qubits ───────────────────────────────────
def find_bridge_ancillas(circuit: stim.Circuit) -> list:
    """
    Bridge ancillas sit at the seam (middle x-column) between the two patches.
    Strategy:
      1. Read QUBIT_COORDS to get the x-coordinate of every qubit.
      2. Collect ancilla qubits (those that appear in R / RX instructions).
      3. Bridge ancillas = ancillas whose x is within one column width of x_mid.
    """
    flat = circuit.flattened()
    q2x  = {}

    for inst in flat:
        if inst.name == "QUBIT_COORDS":
            args = inst.gate_args_copy()
            if args:
                for t in inst.targets_copy():
                    q2x[t.value] = args[0]   # x-coordinate

    if not q2x:
        print("[warn] No QUBIT_COORDS found — cannot detect bridge ancillas.")
        return []

    ancilla_set = set()
    for inst in flat:
        if inst.name in ("R", "RX"):
            for t in inst.targets_copy():
                ancilla_set.add(t.value)

    anc_xs = [x for q, x in q2x.items() if q in ancilla_set]
    if not anc_xs:
        return []

    x_min, x_max = min(anc_xs), max(anc_xs)
    x_mid = (x_min + x_max) / 2
    col_w = (x_max - x_min) / 8      # approx. one ancilla-column width

    bridge = sorted(
        q for q, x in q2x.items()
        if q in ancilla_set and abs(x - x_mid) <= col_w
    )
    return bridge


# ── Step 3c: Inject inter-layer noise on bridge ancillas ─────────────────────
def inject_interlayer_noise(circuit: stim.Circuit,
                             bridge_ancillas: list,
                             p_prime: float,
                             sharing_ratio: int,
                             d: int) -> stim.Circuit:
    """
    Add DEPOLARIZE1(p') immediately before measurements of inter-layer ancillas.

    With sharing_ratio = k, only ceil(d/k) of the d bridge ancillas have a
    direct vertical channel (inter-layer); the rest route in-plane at normal p.
    """
    n_il   = max(1, math.ceil(d / sharing_ratio))
    il_set = set(bridge_ancillas[:n_il])

    new = stim.Circuit()
    for inst in circuit.flattened():
        if inst.name in ("M", "MX", "MR", "MRX", "MRZ") and p_prime > 0:
            noisy = [
                t.value for t in inst.targets_copy()
                if t.is_qubit_target and t.value in il_set
            ]
            if noisy:
                new.append("DEPOLARIZE1", noisy, p_prime)
        new.append(inst)
    return new


# ── Step 4: Sample syndromes and decode with PyMatching ──────────────────────
def compute_ler(circuit: stim.Circuit, num_shots: int) -> float:
    """Return logical error rate using PyMatching on the given noisy circuit."""
    sampler = circuit.compile_detector_sampler()
    det_events, obs_flips = sampler.sample(num_shots, separate_observables=True)

    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
    )
    matcher     = pymatching.Matching.from_detector_error_model(dem)
    predictions = matcher.decode_batch(det_events)

    return float(np.mean(predictions != obs_flips))


# ── Step 5: Main parameter sweep ─────────────────────────────────────────────
print("=" * 65)
print("Discovering h5 files...")
dp_map = discover_h5_files(H5_DIR)   # {d: [p, ...]}
for d, ps in dp_map.items():
    print(f"  d={d}: {len(ps)} p-values found → {ps}")

all_distances = [d for d in DISTANCES if dp_map[d]]

# results[mult][sr][d][p_str] = ler   (p as string for JSON compatibility)
results = {
    mult: {sr: {d: {} for d in all_distances} for sr in SHARING_RATIOS}
    for mult in P_PRIME_MULTS
}

print("=" * 65)
print("Loading circuits and detecting bridge ancillas...")

base_circuits = {}   # (d, p) -> stim.Circuit
bridge_map    = {}   # d      -> list[int]

for d in all_distances:
    for p in dp_map[d]:
        # Match file by parsing p from filename to avoid float-formatting mismatches
        h5 = next(
            (f for f in H5_DIR.glob(f"ls_circuit_{d}_*_z.h5")
             if abs(float(_H5_PATTERN.match(f.name).group(2)) - p) < 1e-15),
            None
        )
        if h5 is None:
            continue
        circ = load_circuit(h5)
        base_circuits[(d, p)] = circ
        if d not in bridge_map:
            bridge_map[d] = find_bridge_ancillas(circ)
            print(f"  d={d}: {len(bridge_map[d])} bridge ancillas → {bridge_map[d]}")

print("=" * 65)
print("Running threshold sweep...\n")

for d in all_distances:
    if d not in bridge_map:
        print(f"  [skip] d={d} — no .h5 files found")
        continue
    for p in dp_map[d]:
        if (d, p) not in base_circuits:
            continue
        base = base_circuits[(d, p)]
        for mult in P_PRIME_MULTS:
            for sr in SHARING_RATIOS:
                p_prime = mult * p
                if p_prime >= 0.75:
                    print(f"  [skip] d={d:2d}  p={p:.6g}  p'={mult:2d}p={p_prime:.4f} "
                          f"— exceeds DEPOLARIZE1 limit (0.75)")
                    continue
                noisy   = inject_interlayer_noise(base, bridge_map[d], p_prime, sr, d)
                ler     = compute_ler(noisy, NUM_SHOTS)
                results[mult][sr][d][str(p)] = ler
                print(f"  d={d:2d}  p={p:.6g}  p'={mult:2d}p  shared_{sr:2d}  "
                      f"->  LER={ler:.4e}")

# Persist results so plotting can be rerun without re-simulating
with open(RESULTS_FILE, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n[✓] Results saved -> {RESULTS_FILE}")


# ── Step 6: Plot — 3×4 grid (rows=p' scenario, cols=sharing ratio) ───────────
d_colors  = {3: "#1f77b4", 5: "#2ca02c", 7: "#ff7f0e", 9: "#9467bd", 11: "#d62728"}
d_markers = {3: "o",       5: "s",       7: "^",       9: "v",       11: "D"}

p_prime_labels = {
    1:  r"$p'=p$",
    5:  r"$p'=5p$",
    10: r"$p'=10p$",
}
sr_labels = {2: "3D-Shared-2", 4: "3D-Shared-4", 8: "3D-Shared-8", 16: "3D-Shared-16"}

# Layout: 3 rows (p' multiplier) × 4 columns (sharing ratio)
nrows, ncols = len(P_PRIME_MULTS), len(SHARING_RATIOS)
fig, axes = plt.subplots(nrows, ncols, figsize=(45 * ncols // 3, 15 * nrows),
                          sharey=False, sharex=False)

for row, mult in enumerate(P_PRIME_MULTS):
    for col, sr in enumerate(SHARING_RATIOS):
        ax = axes[row][col]

        for d in all_distances:
            data = results[mult][sr][d]
            if not data:
                continue
            ps   = sorted(float(k) for k in data.keys())
            lers = [data[str(p)] for p in ps]

            ax.semilogy(
                ps, lers,
                color=d_colors[d], marker=d_markers[d],
                linewidth=6, markersize=20,
                label=f"d={d}",
            )

        # Column title (top row only)
        if row == 0:
            ax.set_title(sr_labels[sr], pad=30)

        # Row label (leftmost column only)
        if col == 0:
            ax.set_ylabel(f"{p_prime_labels[mult]}\nLogical Error Rate")

        # X label (bottom row only)
        if row == nrows - 1:
            ax.set_xlabel("Physical error rate $p$")

        legend_loc = "upper left" if mult == P_PRIME_MULTS[-1] else "upper right"
        ax.legend(fontsize=38, loc=legend_loc)
        ax.grid(True, which="major", linestyle="--", alpha=0.4)

fig.suptitle(
    "HBM Inter-Layer Threshold — LER vs Physical Error Rate",
    fontweight="bold", y=1.01,
)
plt.tight_layout()

fname = OUT_DIR / "e1_threshold_3x4.pdf"
plt.savefig(fname, bbox_inches="tight")
plt.close()
print(f"[✓] Saved {fname}")

print("\nDone.")
