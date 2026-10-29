# QED-C Heisenberg, one Trotter step, Clifford+T at ε = 10⁻² per rotation

The first of QED-C's K = 5 Trotter steps (τ = t / K = 0.04, as in the full benchmark), so every
circuit is one step, like the Ising set in `../ising_eps1e-2/`. Generated and synthesized with

```bash
python quantum-compiler-benchmark-circuits/qedc_heisenberg/gen_qedc_heisenberg.py 16 --steps 1 -o onestep.qasm
python scripts/synth_ising.py onestep.qasm out.qasm --eps 1e-2 --merge --stats heisenberg_qedc_n16.stats.json
sed -E 's/\breg\[/q[/g' out.qasm > heisenberg_qedc_n16.qasm
```

Small angles are kept as stand-ins (see `scripts/synth_ising.py`). `*.stats.json` holds each file's
synthesis statistics.

| Circuit | N | T | CNOT | small-angle stand-ins |
|---|---|---|---|---|
| heisenberg_qedc_n16 | 16 | 1,638 | 45 | 2 |
| heisenberg_qedc_n20 | 20 | 2,068 | 57 | 3 |
| heisenberg_qedc_n25 | 25 | 2,598 | 72 | 4 |
| heisenberg_qedc_n49 | 49 | 5,163 | 144 | 8 |
| heisenberg_qedc_n64 | 64 | 6,759 | 189 | 10 |

QED-C is Apache-2.0: [`LICENSE.QED-C`](LICENSE.QED-C).
