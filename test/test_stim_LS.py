import stim

def generate_correct_d5():
    # This generates a Rotated Surface Code (the most efficient layout)
    # distance=5 means a 5x5 grid of data qubits (25 total)
    # and 24 measure qubits (ancillas). Total = 49 qubits.
    # rounds=5 ensures we have enough temporal distance to catch measurement errors.
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=5,
        rounds=5,
        after_clifford_depolarization=0.001, # 0.1% gate noise
        after_reset_flip_probability=0.001,   # 0.1% reset noise
        before_measure_flip_probability=0.001 # 0.1% measurement noise
    )

    # 1. Verify the distance analytically
    # This proves the code is actually d=5
    shortest_error = circuit.shortest_graphlike_error()
    print(f"Verified Logical Distance: {len(shortest_error)}")

    # 2. Save the raw Stim code to a file
    with open("surface_d5_correct.stim", "w") as f:
        f.write(str(circuit))
    
    print("Full Stim code saved to 'surface_d5_correct.stim'")
    return circuit

if __name__ == "__main__":
    d5_circuit = generate_correct_d5()