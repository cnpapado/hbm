import json
import sys, os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Use default interactive backend if possible
matplotlib.use("Qt5Agg")  # headless backend for servers without X11

def main():
    if len(sys.argv) != 2:
        print("Usage: python visualize_arch.py architecture.json")
        sys.exit(1)

    path = sys.argv[1]

    with open(path, "r") as f:
        data = json.load(f)

    arch = data["arch"]
    H = arch["height"]
    W = arch["width"]
    alg = set(arch["alg_qubits"])
    magic = set(arch["magic_states"])

    fig, ax = plt.subplots(figsize=(W, H))

    # Create grid: physical qubit ID increases left-to-right, top-to-bottom
    qubit_id = 0
    for row in range(H):
        for col in range(W):
            # Assign color based on qubit type
            if qubit_id in magic:
                color = "orange"
            elif qubit_id in alg:
                color = "cornflowerblue"
            else:
                color = "lightgray"

            # Flip y-axis: row 0 at top
            y = H - 1 - row

            rect = patches.Rectangle(
                (col, y), 1, 1,
                linewidth=1,
                edgecolor="black",
                facecolor=color
            )
            ax.add_patch(rect)

            # Label box with qubit ID
            ax.text(
                col + 0.5,
                y + 0.5,
                str(qubit_id),
                ha="center",
                va="center",
                fontsize=9
            )

            qubit_id += 1

    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    plt.show()


if __name__ == "__main__":
    main()
