import random
import math
from qiskit import QuantumCircuit
from typing import List, Tuple


class RandomCliffordTBenchmark:
    """
    Generates random Clifford + T circuits with configurable structural parameters.
    The generated circuits can be exported to QASM and used as synthetic benchmarks
    to test routing and architecture optimizations (e.g., HBM-aware 3D layouts).

    Control knobs:
        n_qubits:         number of logical qubits
        n_layers:         total logical layers (rough circuit depth)
        t_density:        fraction of gates that are T (0.0–1.0)
        cnot_density:     probability that a layer includes entangling CNOTs
        t_dependency:     [0.0–1.0] degree of T-gate dependency:
                             0.0 → T gates spread across qubits (high concurrency)
                             1.0 → T gates stacked on same qubits (serial dependencies)
        clifford_mix:     mix of Clifford gates (H, S, X, Y, Z)
        seed:             random seed for reproducibility
    """

    CLIFFORD_GATES = ["h", "s", "x", "y", "z"]

    def __init__(
        self,
        n_qubits: int = 5,
        n_layers: int = 50,
        t_density: float = 0.2,
        cnot_density: float = 0.5,
        t_dependency: float = 0.5,
        clifford_mix: float = 0.3,
        seed: int = None,
    ):
        if seed is not None:
            random.seed(seed)
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.t_density = t_density
        self.cnot_density = cnot_density
        self.t_dependency = t_dependency
        self.clifford_mix = clifford_mix

    def generate(self) -> QuantumCircuit:
        qc = QuantumCircuit(self.n_qubits, name="rand_CliffordT")

        # Track which qubits recently had T gates → controls dependency
        t_qubit_bias = [0] * self.n_qubits

        for layer in range(self.n_layers):
            layer_type = random.random()

            # Add T gates based on density
            if layer_type < self.t_density:
                n_t = max(1, int(self.t_density * self.n_qubits))
                for _ in range(n_t):
                    q = self._select_t_qubit(t_qubit_bias)
                    qc.t(q)
                    # Increase bias so same qubit is more likely re-used (dependency)
                    t_qubit_bias[q] += self.t_dependency * 10
                    # Decay bias of others
                    t_qubit_bias = [b * 0.9 for b in t_qubit_bias]

            # Add CNOT gates randomly
            if random.random() < self.cnot_density:
                q1, q2 = random.sample(range(self.n_qubits), 2)
                qc.cx(q1, q2)

            # Add random single-qubit Clifford gates
            if random.random() < self.clifford_mix:
                q = random.randrange(self.n_qubits)
                gate = random.choice(self.CLIFFORD_GATES)
                getattr(qc, gate)(q)

        return qc

    def _select_t_qubit(self, bias_list: List[float]) -> int:
        """
        Select a qubit for placing a T gate, controlled by the dependency parameter.
        Higher bias → more dependent stacking on same qubit.
        """
        # Normalize probabilities
        total_bias = sum(bias_list) + 1e-6
        if random.random() < self.t_dependency and total_bias > 0:
            # Choose weighted by bias
            weights = [b / total_bias for b in bias_list]
            r = random.random()
            cumulative = 0
            for i, w in enumerate(weights):
                cumulative += w
                if r < cumulative:
                    return i
        # Otherwise pick new qubit uniformly
        return random.randrange(self.n_qubits)

    # from qiskit.qasm3 import dump

    def save_qasm(self, path: str):
        """Save circuit in OpenQASM 2.0 format (compatible with WISQ)."""
        qc = self.generate()
        from qiskit.qasm2 import dumps  # ✅ Qiskit 1.x API
        qasm_str = dumps(qc)
        with open(path, "w") as f:
            f.write(qasm_str)
        print(f"[✓] Saved random Clifford+T benchmark to {path}")




if __name__ == "__main__":
    # Example usage:
    gen = RandomCliffordTBenchmark(
        n_qubits=10,
        n_layers=80,
        t_density=0.3,
        cnot_density=0.4,
        t_dependency=0.8,
        clifford_mix=0.6,
        seed=42,
    )
    circuit = gen.generate()
    print(circuit)
    gen.save_qasm("rand_benchmark.qasm")
