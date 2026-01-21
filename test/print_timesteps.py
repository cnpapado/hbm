import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="Count number of gates per timestep.")
    parser.add_argument("filename", help="Path to the JSON file")
    args = parser.parse_args()

    with open(args.filename, "r") as f:
        data = json.load(f)

    steps = data["steps"]

    gate_counts = {t: len(step) for t, step in enumerate(steps)}

    for t, count in gate_counts.items():
        print(f"Timestep {t}: {count} gate(s)")

    total_gates = sum(gate_counts.values())
    print("Total gates:", total_gates)
    print("Total timesteps:", len(steps))

if __name__ == "__main__":
    main()
