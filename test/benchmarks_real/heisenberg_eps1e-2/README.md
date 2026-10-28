# QED-C Heisenberg, one Trotter step, Clifford+T at ε = 10⁻² per rotation

The first of QED-C's K = 5 Trotter steps (τ = t / K = 0.04, as in the full benchmark), so every real
circuit is one step, like the Ising set in `../ising_eps1e-2/`. Generated with
`quantum-compiler-benchmark-circuits/qedc_heisenberg/gen_qedc_heisenberg.py N --steps 1` (a prefix of
the 5-step `heisenberg_qedc_nN.qasm`; see `REAL_BENCHMARKS.md`) and synthesized with
`scripts/synth_ising.py in.qasm out.qasm --eps 1e-2 --merge` (small angles kept as stand-ins) by
`../../runs/real/setup/synth_heis_1step.sh`. `*.stats.json` holds each file's synthesis statistics.
The 5-step versions are in `../heisenberg5_eps1e-2/`.

| Circuit | N | T | CNOT | small-angle stand-ins |
|---|---|---|---|---|
| heisenberg_qedc_n16 | 16 | 1,638 | 45 | 2 |
| heisenberg_qedc_n20 | 20 | 2,068 | 57 | 3 |
| heisenberg_qedc_n25 | 25 | 2,598 | 72 | 4 |
| heisenberg_qedc_n49 | 49 | 5,163 | 144 | 8 |
| heisenberg_qedc_n64 | 64 | 6,759 | 189 | 10 |

QED-C is Apache-2.0: [`LICENSE.QED-C`](LICENSE.QED-C).
