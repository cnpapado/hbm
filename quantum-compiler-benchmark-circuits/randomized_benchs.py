import random
import math
from qiskit import QuantumCircuit
from typing import List


class RandomCliffordTBenchmark:
    """
    Generates random Clifford + T circuits with configurable structural parameters.
    """

    CLIFFORD_GATES = ["h", "s", "x", "y", "z"]

    def __init__(
        self,
        n_qubits: int = 150,
        n_layers: int = 40,
        t_density: float = 0.3,
        cnot_density: float = 0.5,
        t_dependency: float = 0.5,
        clifford_mix: float = 0.3,
        seed: int = None,
        total_gates: int = 2000,
    ):
        if seed is not None:
            random.seed(seed)
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.t_density = t_density
        self.cnot_density = cnot_density
        self.t_dependency = t_dependency
        self.clifford_mix = clifford_mix
        self.total_gates = total_gates

    def generate(self) -> QuantumCircuit:
        qc = QuantumCircuit(self.n_qubits, name="rand_CliffordT")
        t_qubit_bias = [0] * self.n_qubits
        gates_inserted = 0

        while gates_inserted < self.total_gates:
            for _ in range(self.n_layers):
                if gates_inserted >= self.total_gates:
                    break

                layer_type = random.random()

                # Add T gates
                if layer_type < self.t_density and gates_inserted < self.total_gates:
                    n_t = max(1, int(self.t_density * self.n_qubits))
                    for _ in range(n_t):
                        if gates_inserted >= self.total_gates:
                            break
                        q = self._select_t_qubit(t_qubit_bias)
                        qc.t(q)
                        gates_inserted += 1
                        t_qubit_bias[q] += self.t_dependency * 10
                        t_qubit_bias = [b * 0.9 for b in t_qubit_bias]

                # Add CNOTs
                if random.random() < self.cnot_density and gates_inserted < self.total_gates:
                    q1, q2 = random.sample(range(self.n_qubits), 2)
                    qc.cx(q1, q2)
                    gates_inserted += 1

                # Add Clifford
                if random.random() < self.clifford_mix and gates_inserted < self.total_gates:
                    q = random.randrange(self.n_qubits)
                    gate = random.choice(self.CLIFFORD_GATES)
                    getattr(qc, gate)(q)
                    gates_inserted += 1

        return qc

    def _select_t_qubit(self, bias_list: List[float]) -> int:
        total_bias = sum(bias_list) + 1e-6
        if random.random() < self.t_dependency and total_bias > 0:
            weights = [b / total_bias for b in bias_list]
            r = random.random()
            cumulative = 0
            for i, w in enumerate(weights):
                cumulative += w
                if r < cumulative:
                    return i
        return random.randrange(self.n_qubits)

    def save_qasm(self, path: str):
        qc = self.generate()
        from qiskit.qasm2 import dumps
        qasm_str = dumps(qc)
        with open(path, "w") as f:
            f.write(qasm_str)
        print(f"[✓] Saved random Clifford+T benchmark to {path}")
