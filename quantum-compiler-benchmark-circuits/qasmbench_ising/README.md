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

The files in `original/` are unmodified. `ising_n10` is 5 Trotter steps and names its
register `reg`; the others are 1 step on register `q`. The one-step, Clifford+T versions used
for the HBM evaluation are in `test/benchmarks_real/ising_eps1e-2/`, which says how they are made.

## License

QASMBench is © 2020 Battelle Memorial Institute and is distributed under
a BSD-style license that allows redistribution with or without modification,
provided the copyright notice and disclaimers are retained. The full license
text is in [`LICENSE.QASMBench`](LICENSE.QASMBench).

Reference: A. Li, S. Stein, S. Krishnamoorthy, J. Ang, "QASMBench: A Low-level
Quantum Benchmark Suite for NISQ Evaluation and Simulation", ACM TQC 2023.

## Structure

Each Trotter step acts on a line of N qubits: H on every qubit,
then ZZ terms as `rz / cx / rz / cx` on brickwork pairs, then single-qubit
rotations. Per step there are 2N−2 cx gates and 6N−4 rz gates, of which 2N are
`rz(0)`. The cx/rz-only depth before synthesis is 10 for every N.
