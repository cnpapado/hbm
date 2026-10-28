# QASMBench Ising, Clifford+T at ε = 10⁻² per rotation

Copies of `quantum-compiler-benchmark-circuits/qasmbench_ising/clifford_t_eps1e-2/ising_n{26,34,66}.qasm`
from the `mati` branch (commit 73b3202f), unchanged. They are QASMBench's transverse-field Ising circuits
(one Trotter step), synthesized there with `scripts/synth_ising.py --eps 1e-2 --merge` (Qualtran rotation
synthesis, wisq's own path). See that branch's `qasmbench_ising/README.md` for details.

`ising_n10` (QASMBench `original/ising_n10.qasm`, register renamed `reg` to `q`) and `ising_n13`,
`ising_n16` (JKU `jku_suite/ising_model_{13,16}.qasm`) are cut to their first Trotter step by
`scripts/ising_one_step.py`, so every circuit here is one step, as QASMBench ships n26/n34/n66.
They were synthesized the same way by `../../runs/real/setup/synth_1step.sh`; `*.stats.json` holds
their synthesis statistics. The 5-step versions are in `../ising5_eps1e-2/`.

| Circuit | N | T | CNOT |
|---|---|---|---|
| ising_n10 | 10 | 982 | 18 |
| ising_n13 | 13 | 1,303 | 24 |
| ising_n16 | 16 | 1,618 | 30 |
| ising_n26 | 26 | 1,550 | 50 |
| ising_n34 | 34 | 2,018 | 66 |
| ising_n66 | 66 | 3,920 | 130 |

ε = 10⁻² per rotation is a routing precision, not a result precision: summed over the rotations, the
synthesis error bound is far above a 1% target.

DASCOT's square layout uses a ⌈√N⌉² data grid (36, 36 and 81 slots), and every revision design is sized
for that full grid, so each configuration also pays for the empty slots.

QASMBench is © 2020 Battelle Memorial Institute, BSD-style license: [`LICENSE.QASMBench`](LICENSE.QASMBench).
Run them with `REV_DIR=runs/<name> bash test/revision/submit_revision.sh ising` (see `REVISION.md`).
