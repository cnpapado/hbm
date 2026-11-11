Heisenberg-model Hamiltonian-simulation circuits from the QED-C application-oriented benchmarks
([SRI-International/QC-App-Oriented-Benchmarks](https://github.com/SRI-International/QC-App-Oriented-Benchmarks),
Apache-2.0, license in [LICENSE.QED-C](LICENSE.QED-C)).

QED-C publishes a Qiskit generator, not QASM files. [gen_qedc_heisenberg.py](gen_qedc_heisenberg.py) transcribes its
method-1 circuit (`qedcbench/hamiltonian_simulation/qiskit/hamiltonian_simulation_kernel.py`) to OpenQASM 2.0 with the
benchmark's own parameters from `_common/precalculated_data.json`:

- open chain, checkerboard initial state (X on even qubits)
- K = 5 Trotter steps, t = 0.2, w = 1, per-qubit fields hx, hz from the data file
- each step: rx and rz field rotations on every qubit, then the 3-CX `xxyyzz_opt_gate` on even bonds, then odd bonds
- final measurements omitted (DASCOT ignores them)

`heisenberg_qedc_n{16,20}.qasm` are exactly what the benchmark builds. QED-C only publishes 20 field values, so for
`n25, n49, n64, n100` the fields are cycled (`hx[i % 20]`); this is the only deviation.

Regenerate with `python gen_qedc_heisenberg.py --batch`. Rotations are not yet synthesized to Clifford+T.
