import stim

class LatticeSurgeryGenerator:
    def __init__(self, d: int, p: float = 0.001):
        self.d = d
        self.p = p
        self.circuit = stim.Circuit()

        self.q2coord = {}
        self.coord2q = {}
        self.data_qubits = []
        self.x_ancillas = []
        self.z_ancillas = []
        self.bridge_ancillas = []

        self._build_layout()

        self.meas_count = 0
        self.history = {}  # Maps qubit index -> absolute measurement index

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        """
        Coordinate system: integers, (x+y)%2==0 → data, (x+y)%2!=0 → ancilla.

        Patch A : x in [0, 2d-2]
        Bridge  : x == 2d-1   (Z-type ancillas only, for a ZZ merge)
        Patch B : x in [2d, 4d-2]
        Both patches span y in [0, 2d-2].

        Boundary filtering: an ancilla is kept only if it has at least one
        valid data-qubit neighbour inside the patch region (cardinal ±1).
        """
        q_idx = 0
        patch_width = 2 * self.d - 1   # = 2d-1  (last x-index of patch A)
        max_x = 4 * self.d - 2
        max_y = 2 * self.d - 2

        def has_data_neighbour(x, y):
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx <= max_x and 0 <= ny <= max_y:
                    if (nx + ny) % 2 == 0:          # data-qubit parity
                        # exclude bridge data qubits from patch A/B neighbour check
                        return True
            return False

        for y in range(max_y + 1):
            for x in range(max_x + 1):
                if (x + y) % 2 == 0:
                    # Data qubit — always include
                    self._add_q(q_idx, x, y, "DATA")
                    q_idx += 1
                else:
                    # Ancilla — classify and boundary-filter
                    if x == patch_width:
                        # Bridge column: Z-type only, keep if y is odd
                        if y % 2 == 1 and has_data_neighbour(x, y):
                            self._add_q(q_idx, x, y, "BRIDGE")
                            q_idx += 1
                    else:
                        if not has_data_neighbour(x, y):
                            continue  # boundary position with no neighbours → skip
                        # X ancilla: (x+y)%2!=0 AND x is even (so y is odd)
                        # Z ancilla: (x+y)%2!=0 AND x is odd  (so y is even)
                        if x % 2 == 0:
                            self._add_q(q_idx, x, y, "X_ANC")
                        else:
                            self._add_q(q_idx, x, y, "Z_ANC")
                        q_idx += 1

        for q, (x, y) in self.q2coord.items():
            self.circuit.append("QUBIT_COORDS", [q], [x, y])

    def _add_q(self, q, x, y, role):
        self.q2coord[q] = (x, y)
        self.coord2q[(x, y)] = q
        if   role == "DATA":   self.data_qubits.append(q)
        elif role == "X_ANC":  self.x_ancillas.append(q)
        elif role == "Z_ANC":  self.z_ancillas.append(q)
        elif role == "BRIDGE": self.bridge_ancillas.append(q)

    # ── Syndrome round ────────────────────────────────────────────────────────

    def _do_syndrome_round(self, active_ancillas, is_first_merge_round=False):
        """
        One full syndrome extraction round:
          reset → H(X) → 4×CX → H(X) → measure → detectors
        Circuit-level depolarising noise on every gate.
        """
        active_x = [q for q in active_ancillas if q in self.x_ancillas]
        active_z = [q for q in active_ancillas
                    if q in self.z_ancillas or q in self.bridge_ancillas]

        # ── Reset ─────────────────────────────────────────────────────────────
        if active_z:
            self.circuit.append("R",  active_z)
            self.circuit.append("X_ERROR", active_z, self.p)   # reset noise
        if active_x:
            self.circuit.append("RX", active_x)
            self.circuit.append("Z_ERROR", active_x, self.p)   # reset noise
        self.circuit.append("TICK")

        # ── H on X-ancillas ───────────────────────────────────────────────────
        if active_x:
            self.circuit.append("H", active_x)
        self.circuit.append("TICK")

        # ── 4 CNOT layers (cardinal directions: W, E, N, S) ──────────────────
        # Bug fix: use cardinal (±1,0),(0,±1) so we reach data-qubit neighbours.
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for dx, dy in directions:
            cx_pairs = []
            for a in active_ancillas:
                ax, ay = self.q2coord[a]
                nb = (ax + dx, ay + dy)
                if nb not in self.coord2q:
                    continue
                data_q = self.coord2q[nb]
                if data_q not in self.data_qubits:
                    continue          # skip ancilla-ancilla pairs
                if a in self.z_ancillas or a in self.bridge_ancillas:
                    cx_pairs.extend([data_q, a])   # data controls Z-ancilla
                else:
                    cx_pairs.extend([a, data_q])   # X-ancilla controls data
            if cx_pairs:
                self.circuit.append("DEPOLARIZE2", cx_pairs, self.p)
                self.circuit.append("CX", cx_pairs)
            self.circuit.append("TICK")

        # ── H on X-ancillas ───────────────────────────────────────────────────
        if active_x:
            self.circuit.append("H", active_x)
        self.circuit.append("TICK")

        # ── Measurement with noise ────────────────────────────────────────────
        if active_z:
            self.circuit.append("X_ERROR", active_z, self.p)
            self.circuit.append("M",  active_z)
        if active_x:
            self.circuit.append("Z_ERROR", active_x, self.p)
            self.circuit.append("MX", active_x)
        self.circuit.append("TICK")

        # ── Track measurement indices ─────────────────────────────────────────
        current_meas = {}
        # Measurements are appended in the order: active_z then active_x
        for a in active_z + active_x:
            current_meas[a] = self.meas_count
            self.meas_count += 1

        # ── Detectors ─────────────────────────────────────────────────────────
        for a in active_z + active_x:
            skip = is_first_merge_round and (a in self.bridge_ancillas)
            if a in self.history and not skip:
                offset_now  = current_meas[a]    - self.meas_count
                offset_past = self.history[a]     - self.meas_count
                x, y = self.q2coord[a]
                self.circuit.append(
                    "DETECTOR",
                    [stim.target_rec(offset_now), stim.target_rec(offset_past)],
                    [x, y, 0]
                )

        # ── Update history ────────────────────────────────────────────────────
        for a in active_z + active_x:
            self.history[a] = current_meas[a]

    # ── Circuit assembly ──────────────────────────────────────────────────────

    def generate(self) -> stim.Circuit:
        isolated_ancillas = self.x_ancillas + self.z_ancillas
        merged_ancillas   = isolated_ancillas + self.bridge_ancillas

        # Phase 0: initialise everything to |0⟩
        self.circuit.append("R", self.data_qubits + merged_ancillas)
        self.circuit.append("TICK")

        # Phase 1: d rounds of isolated (two separate patches)
        for _ in range(self.d):
            self._do_syndrome_round(isolated_ancillas)

        # Phase 2: d rounds of merged (bridge ancillas active)
        for i in range(self.d):
            self._do_syndrome_round(merged_ancillas, is_first_merge_round=(i == 0))

        # Phase 3: d rounds of isolated again (split)
        for _ in range(self.d):
            self._do_syndrome_round(isolated_ancillas)

        # Phase 4: final data-qubit readout
        self.circuit.append("M", self.data_qubits)

        # Update meas_count so rec offsets stay correct
        data_meas_start = self.meas_count
        for q in self.data_qubits:
            self.history[q] = self.meas_count
            self.meas_count += 1

        # ── Final data detectors (Z stabilizers only) ─────────────────────────
        # For each Z-type ancilla active in the last round, the parity of its
        # data-qubit neighbours (measured in Z basis) must match its last
        # syndrome outcome. X ancillas are skipped — data is read in Z basis.
        last_active_z = [a for a in (self.z_ancillas + self.bridge_ancillas)
                         if a in self.history]

        for a in last_active_z:
            ax, ay = self.q2coord[a]
            nb_data = []
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nb = (ax + dx, ay + dy)
                if nb in self.coord2q:
                    q = self.coord2q[nb]
                    if q in self.data_qubits:
                        nb_data.append(q)

            if not nb_data:
                continue

            anc_offset  = self.history[a] - self.meas_count
            data_offsets = [self.history[q] - self.meas_count for q in nb_data]
            targets = [stim.target_rec(anc_offset)] + \
                      [stim.target_rec(o) for o in data_offsets]
            x, y = self.q2coord[a]
            self.circuit.append("DETECTOR", targets, [x, y, 1])

        # ── Observable: Z logical of patch A ──────────────────────────────────
        # Z-logical string = Z on leftmost column of data qubits (x == 0)
        obs_qubits = sorted(
            [q for q in self.data_qubits if self.q2coord[q][0] == 0]
        )
        if obs_qubits:
            obs_targets = [stim.target_rec(self.history[q] - self.meas_count)
                           for q in obs_qubits]
            self.circuit.append("OBSERVABLE_INCLUDE", obs_targets, 0)

        return self.circuit


# ── Execute ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    for d in [3, 5, 7, 9, 11]:
        gen = LatticeSurgeryGenerator(d=d, p=0.001)
        circ = gen.generate()

        fname = f"lattice_surgery_d{d}.stim"
        with open(fname, "w") as f:
            f.write(str(circ))

        print(f"d={d:2d} | qubits={circ.num_qubits:4d} | measurements={circ.num_measurements:6d} | saved → {fname}")
