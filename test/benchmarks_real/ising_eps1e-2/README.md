# QASMBench Ising, Clifford+T at ε = 10⁻² per rotation

Copies of `quantum-compiler-benchmark-circuits/qasmbench_ising/clifford_t_eps1e-2/ising_n{26,34,66}.qasm`
from the `mati` branch (commit 73b3202f), unchanged. They are QASMBench's transverse-field Ising circuits
(one Trotter step), synthesized there with `scripts/synth_ising.py --eps 1e-2 --merge` (Qualtran rotation
synthesis, wisq's own path). See that branch's `qasmbench_ising/README.md` for details.

| Circuit | N | T | CNOT |
|---|---|---|---|
| ising_n26 | 26 | 1,550 | 50 |
| ising_n34 | 34 | 2,018 | 66 |
| ising_n66 | 66 | 3,920 | 130 |

ε = 10⁻² per rotation is a routing precision, not a result precision: summed over the rotations, the
synthesis error bound is far above a 1% target.

DASCOT's square layout uses a ⌈√N⌉² data grid (36, 36 and 81 slots), and every revision design is sized
for that full grid, so each configuration also pays for the empty slots.

QASMBench is © 2020 Battelle Memorial Institute, BSD-style license: [`LICENSE.QASMBench`](LICENSE.QASMBench).
Run them with `REV_DIR=runs/<name> bash test/revision/submit_revision.sh ising` (see `REVISION.md`).
