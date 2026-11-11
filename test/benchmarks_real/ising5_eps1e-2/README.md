# Ising, 5 Trotter steps, Clifford+T at ε = 10⁻² per rotation

`ising_n10` (QASMBench `original/ising_n10.qasm`, register renamed `reg` to `q`) and `ising_n13`,
`ising_n16` (JKU `jku_suite/ising_model_{13,16}.qasm`), all 5 steps as published, synthesized with
`scripts/synth_ising.py --eps 1e-2 --merge` by `../../runs/real/setup/synth_real.sh`. These are the
circuits of the first real-benchmark campaign (`runs/real`). They were replaced in
`../ising_eps1e-2/` by one-step cuts, to match QASMBench's one-step n26/n34/n66.

| Circuit | N | T | CNOT |
|---|---|---|---|
| ising_n10 | 10 | 3,882 | 90 |
| ising_n13 | 13 | 5,162 | 120 |
| ising_n16 | 16 | 6,430 | 150 |

QASMBench is © 2020 Battelle Memorial Institute, BSD-style license: [`../ising_eps1e-2/LICENSE.QASMBench`](../ising_eps1e-2/LICENSE.QASMBench).
