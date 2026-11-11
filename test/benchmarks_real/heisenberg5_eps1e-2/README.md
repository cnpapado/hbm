# QED-C Heisenberg, 5 Trotter steps, Clifford+T at ε = 10⁻² per rotation

`quantum-compiler-benchmark-circuits/qedc_heisenberg/heisenberg_qedc_n{16,20,25,49,64}.qasm` (5 Trotter
steps; see `REAL_BENCHMARKS.md`), synthesized with
`scripts/synth_ising.py in.qasm out.qasm --eps 1e-2 --merge` (small angles kept as stand-ins), the same
settings as `../ising_eps1e-2/`. Run as a Slurm array: `../../runs/real/setup/synth_real.sh`.
`*.stats.json` holds each file's synthesis statistics. These are the circuits of the first
real-benchmark campaign (`runs/real`); `../heisenberg_eps1e-2/` now holds one-step cuts.

| Circuit | N | T | CNOT | small-angle stand-ins |
|---|---|---|---|---|
| heisenberg_qedc_n16 | 16 | 8,190 | 225 | 10 |
| heisenberg_qedc_n20 | 20 | 10,340 | 285 | 15 |
| heisenberg_qedc_n25 | 25 | 12,990 | 360 | 20 |
| heisenberg_qedc_n49 | 49 | 25,815 | 720 | 40 |
| heisenberg_qedc_n64 | 64 | 33,795 | 945 | 50 |

QED-C is Apache-2.0: [`LICENSE.QED-C`](LICENSE.QED-C).
