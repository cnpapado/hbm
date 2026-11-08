"""
molecule_paulis.py
------------------
Write the qubit Hamiltonian (Jordan-Wigner, STO-3G, full orbital space) of H2, LiH or H2O as
a JSON list of [coefficient, "IXYZ..."] (qubit 0 first), for gen_trotter.py paulis.
Qubit counts match simulation_hamiltonians/molecule_hams: H2 4, LiH 12, H2O 14.
Needs PennyLane (in the wisq venv); uses its built-in Hartree-Fock, no PySCF.

Geometries (equilibrium, Bohr): H2 0.74 A bond; LiH 1.595 A; H2O 0.9572 A, 104.5 deg.

Usage:
  python molecule_paulis.py lih -o lih.json
"""

import argparse
import json

import numpy as np
import pennylane as qml

MOLECULES = {
    "h2":  (["H", "H"], [[0, 0, 0], [0, 0, 1.3984]]),
    "lih": (["Li", "H"], [[0, 0, 0], [0, 0, 3.0141]]),
    "h2o": (["O", "H", "H"], [[0, 0, 0], [1.4305, 0, 1.1072], [-1.4305, 0, 1.1072]]),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("molecule", choices=sorted(MOLECULES))
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--cutoff", type=float, default=1e-8, help="drop terms with |c| below this")
    a = ap.parse_args()
    symbols, coords = MOLECULES[a.molecule]
    mol = qml.qchem.Molecule(symbols, np.array(coords, dtype=float), basis_name="sto-3g")
    H, n = qml.qchem.molecular_hamiltonian(mol, mapping="jordan_wigner")
    wires = list(range(n))
    out = []
    for c, op in zip(*H.terms()):
        c = float(np.real(c))
        if abs(c) < a.cutoff:
            continue
        word = qml.pauli.pauli_word_to_string(op, wire_map={w: w for w in wires})
        out.append([c, word])
    with open(a.output, "w") as f:
        json.dump(out, f)
    print(f"{a.output}: {n} qubits, {len(out)} Pauli terms")


if __name__ == "__main__":
    main()
