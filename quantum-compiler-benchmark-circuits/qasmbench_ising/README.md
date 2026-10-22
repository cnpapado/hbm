# QASMBench Ising circuits

Transverse-field Ising Trotter circuits from QASMBench, used as real-world
Hamiltonian-simulation benchmarks for the HBM evaluation alongside the
synthetic `bench_n*_p*` circuits.

## Source

[pnnl/QASMBench](https://github.com/pnnl/QASMBench), `master` branch, fetched 2026-10-20:

| File | QASMBench path |
|---|---|
| `original/ising_n10.qasm`  | `small/ising_n10/ising_n10.qasm` |
| `original/ising_n26.qasm`  | `medium/ising_n26/ising_n26.qasm` |
| `original/ising_n34.qasm`  | `large/ising_n34/ising_n34.qasm` |
| `original/ising_n66.qasm`  | `large/ising_n66/ising_n66.qasm` |
| `original/ising_n98.qasm`  | `large/ising_n98/ising_n98.qasm` |

The files in `original/` are unmodified. `ising_n10` is 5 Trotter steps and names its
register `reg`, so DASCOT (which only reads `q[...]`) needs the register renamed before
routing; the others are 1 step on register `q`. `ising_n10` and `ising_n98` have not been
synthesized yet: DASCOT runs on the synthesized `ising_n98` did not finish in reasonable
time locally. QASMBench also has `ising_n420`, which is above the 100-qubit limit.

## License

QASMBench is © 2020 Battelle Memorial Institute and is distributed under
a BSD-style license that allows redistribution with or without modification,
provided the copyright notice and disclaimers are retained. The full license
text is in [`LICENSE.QASMBench`](LICENSE.QASMBench).

Reference: A. Li, S. Stein, S. Krishnamoorthy, J. Ang, "QASMBench: A Low-level
Quantum Benchmark Suite for NISQ Evaluation and Simulation", ACM TQC 2023.

## Structure

Each circuit is one Trotter step over a line of N qubits: H on every qubit,
then ZZ terms as `rz / cx / rz / cx` on brickwork pairs, then single-qubit
rotations. In total there are 2N−2 cx gates and 6N−4 rz gates, of which 2N are
`rz(0)`. The cx/rz-only depth before synthesis is 10 for every N.

## Clifford+T synthesis

`clifford_t_eps1e-2/` holds the synthesized circuits, produced with
[`scripts/synth_ising.py`](../../scripts/synth_ising.py):

```bash
PYTHONPATH=wisq/src python scripts/synth_ising.py original/ising_n26.qasm clifford_t_eps1e-2/ising_n26.qasm --eps 1e-2 --merge
```

The script follows wisq's own synthesis path (`guoq.transpile_if_needed`):
it translates to the NAM basis {rz, h, x, cx} and then runs Qualtran's
`diagonal_unitary_approx` (the `QualtranRS` pass, dps=200, max T=400). There are
four differences:

* ε is the precision for each rotation. wisq instead takes a total budget and
  uses ε_total / (2·num_rz) for each rotation.
* `--merge` drops `rz(0)` and fuses back-to-back rz on the same qubit before
  synthesis. This is lossless and removes about half of the rotations.
* Measurements and barriers are dropped. DASCOT ignores them anyway.
* At the pinned Qualtran commit (fa5a8ec), `SU2CliffordT.to_sequence()` is a
  module-level function, so the script supplies the method that
  `wisq/qualtran_rotation_synthesis.py` expects.

The T count per rotation at a given ε is the same for every circuit (≈ 3·log2(1/ε)):

| ε per rotation | mean T / rotation |
|---|---|
| 1e-2 | ~20 |
| 1e-3 | ~31 |
| 1e-6 | ~62 |
| 1e-8 | ~82 |
| wisq default (1e-10 total) | ~101–123 |

ε=1e-2 was chosen to keep DASCOT runtime manageable, not as a realistic
simulation precision. Lower ε lengthens each rotation's T chain but doesn't
change how many qubits need a magic state in each layer. On n26, the T density
is 0.628 at 1e-2 and 0.649 at 1e-3.

### Synthesized circuits (ε = 1e-2, `--merge`)

Statistics are as DASCOT sees the circuit: only cx and t/tdg are scheduled, and
other gates are free (`scripts/t_density.py`). L is the cx/T depth, density is
T / (N·L), and max_T is the largest number of T gates in one layer.

| Circuit | N | rz (raw → synthesized) | T / rotation | T | cx | L | density | max_T / 4√N |
|---|---|---|---|---|---|---|---|---|
| ising_n26 | 26 | 152 → 75  | 20.7 | 1550 | 50  | 95 | 0.628 | 1.27 |
| ising_n34 | 34 | 200 → 99  | 20.4 | 2018 | 66  | 94 | 0.631 | 1.46 |
| ising_n66 | 66 | 392 → 195 | 20.1 | 3920 | 130 | 96 | 0.619 | 2.00 |

For comparison, the paper's synthetic `bench_n*_p90` circuits have a density
of 0.41–0.49 at N ≥ 100, and the `p50` circuits 0.11–0.13.

To run the paper's 2D baseline and HBM configurations on these circuits:

```bash
python test/qasmbench_ising/run_ising_archs.py quantum-compiler-benchmark-circuits/qasmbench_ising/clifford_t_eps1e-2 <out_dir>
python test/qasmbench_ising/collect_results.py quantum-compiler-benchmark-circuits/qasmbench_ising/clifford_t_eps1e-2 <out_dir>
```
