First-order Trotter circuits for the Fermi-Hubbard model, in Clifford+Rz (rotations still need Clifford+T synthesis).

    H = -t * sum_<ij>,s (a+_is a_js + h.c.)  +  U * sum_i n_i,up n_i,down,    t = 1, U = 4, dt = 0.1

Jordan-Wigner encoding, spin-blocked (qubit = site + spin * n_sites), snake ordering on 2D lattices, open boundaries.
Qubit counts match even grid sizes of the synthetic suite, kept below 100 qubits: N = 16, 64
(1D chains of N/2 sites; 2D lattices 2x4 and 4x8). Larger sizes can be generated with `--lattice/--sites/--lx/--ly`.

Files are named `fermi_hubbard_{1d,2d}_{N}q_{steps}step_{order}.qasm`:
- `parallel`: hopping bonds are grouped into layers with disjoint JW supports, and each hopping term
  `exp(-i b (XZ..ZX + YZ..ZY))` is one gadget with its two Rz rotations on both endpoints at once.
  The on-site layer applies Rz on every qubit, then all ZZ gadgets.
- `sequential`: same Hamiltonian, but each Pauli string gets its own CX-ladder gadget, emitted bond by bond.
  This is the style of the FTCircuitBench Hamiltonian circuits, and is included for comparison.

[gen_fermi_hubbard.py](gen_fermi_hubbard.py) generates them (`--batch` regenerates this directory, `--help` for single circuits).
`--verify` checks every gadget against exact Pauli exponentials by statevector simulation on 6-12 qubits.

T density as DASCOT sees it (cx and T only, ~82 T per rotation at eps = 1e-8, before synthesis):

| Lattice | Order | N=16 | N=64 |
|---|---|---|---|
| 1D | parallel | 0.80 | 0.84 |
| 1D | sequential | 0.20 | 0.05 |
| 2D | parallel | 0.64 | 0.49 |
| 2D | sequential | 0.18 | 0.06 |

The 2D parallel density falls with N because vertical hops carry JW Z strings whose intervals are nested,
so they cannot share a layer. A fermionic-swap network or a local fermion encoding would remove this.
