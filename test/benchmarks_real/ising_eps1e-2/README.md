# Transverse-field Ising, one Trotter step, Clifford+T at ε = 10⁻² per rotation

| Circuit | Source | N | T | CNOT |
|---|---|---|---|---|
| ising_n10 | QASMBench `ising_n10`, first of its 5 steps | 10 | 982 | 18 |
| ising_n13 | JKU `ising_model_13`, first step | 13 | 1,303 | 24 |
| ising_n16 | JKU `ising_model_16`, first step | 16 | 1,618 | 30 |
| ising_n26 | QASMBench `ising_n26` (one step) | 26 | 1,550 | 50 |
| ising_n34 | QASMBench `ising_n34` (one step) | 34 | 2,018 | 66 |
| ising_n66 | QASMBench `ising_n66` (one step) | 66 | 3,920 | 130 |

Sources are `quantum-compiler-benchmark-circuits/qasmbench_ising/original/` and
`quantum-compiler-benchmark-circuits/jku_suite/`. n10, n13 and n16 are cut to their first Trotter
step with `scripts/ising_one_step.py`, so every circuit here is one step, as QASMBench ships
n26/n34/n66. Each circuit is then synthesized with Qualtran rotation synthesis (wisq's own path):

```bash
python scripts/ising_one_step.py quantum-compiler-benchmark-circuits/jku_suite/ising_model_13.qasm onestep.qasm
python scripts/synth_ising.py onestep.qasm out.qasm --eps 1e-2 --merge --stats ising_n13.stats.json
sed -E 's/\breg\[/q[/g' out.qasm > ising_n13.qasm   # DASCOT reads only q[...]
```

`*.stats.json` holds the synthesis statistics of n10, n13 and n16.

ε = 10⁻² per rotation is a routing precision, not a result precision: summed over the rotations, the
synthesis error bound is far above a 1% target.

DASCOT's square layout uses a ⌈√N⌉² data grid (16, 16, 16, 36, 36 and 81 slots), and every revision
design is sized for that full grid, so each configuration also pays for the empty slots.

QASMBench is © 2020 Battelle Memorial Institute, BSD-style license: [`LICENSE.QASMBench`](LICENSE.QASMBench).
