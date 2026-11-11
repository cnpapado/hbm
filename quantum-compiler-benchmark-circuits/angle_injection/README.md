Routing models of the real-world benchmarks for a surface-code machine with **arbitrary-angle injection**:
rotations are not synthesized to Clifford+T, each one consumes injected resource states instead.

Produced from the Clifford+rotation sources by [`scripts/injection_model.py`](../../scripts/injection_model.py).
DASCOT routes only `cx` and `t`, sending every `t` to a magic-state patch, so here a `t` means
"consume one injected resource state on this qubit":

| Folder | Model | Resource states per non-Clifford rotation |
|---|---|---|
| `deterministic/` | ideal injection | 1 |
| `rus_expected/` | repeat-until-success at its expected cost (success probability 1/2 per attempt) | 2, in sequence |
| `rus_sampled/` | repeat-until-success, sampled (`--rus-sample --seed 0`) | Geometric(1/2), mean 2 |

In every model: rotations by odd multiples of π/4 are an ordinary T (1 state); multiples of π/2 and all
other single-qubit Cliffords are dropped (free in DASCOT); small angles are charged in full; cz/cy are
written as cx. The files are resource models for routing, not executable circuits, and always use register `q`.

Sources (all at most 100 qubits, unmodified, with their original step counts): QED-C Heisenberg
n16–n100, QUEST Heisenberg (`heisenberg_step_10_4`, `_50_4`, `_50_8`), QASMBench Ising n10–n98, JKU Ising
13 and 16, QUEST TFIM `step_100` at 4–32 qubits, wisq QAOA, and the parallel Fermi-Hubbard circuits.

Regenerate one file with, for example:

```bash
python scripts/injection_model.py quantum-compiler-benchmark-circuits/qasmbench_ising/original/ising_n66.qasm quantum-compiler-benchmark-circuits/angle_injection/rus_expected/ising_n66.qasm --attempts 2
```

The sampled model is closest to real RUS but still static: real RUS is adaptive (the correction angle depends on
the measurement outcome), which a precompiled DASCOT schedule cannot express. See `REAL_BENCHMARKS.md` for results.
