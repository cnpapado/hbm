import json
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Count number of gates per timestep.")
    parser.add_argument("filename", help="Path to the JSON file")
    parser.add_argument("--summary", action="store_true", help="Print only the total timestep count")
    args = parser.parse_args()

    try:
        with open(args.filename, "r") as f:
            data = json.load(f)
        
        steps = data.get("steps", [])

        # On a mapping/routing timeout wisq writes {"steps": "timeout"}.
        # len() of that string is 7, which would otherwise be reported as a
        # (very good) timestep count.
        if isinstance(steps, str):
            print("TIMEOUT")
            return

        if args.summary:
            print(len(steps))
        else:
            gate_counts = {t: len(step) for t, step in enumerate(steps)}
            for t, count in gate_counts.items():
                print(f"Timestep {t}: {count} gate(s)")
            print("Total gates:", sum(gate_counts.values()))
            print("Total timesteps:", len(steps))
            
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        # If the file doesn't exist or is invalid (common in timeouts)
        print("TIMEOUT")

if __name__ == "__main__":
    main()