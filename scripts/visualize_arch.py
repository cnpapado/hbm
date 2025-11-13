import json
import sys
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.lines as mlines

# Use an interactive backend
matplotlib.use("Qt5Agg")

def draw_arch(ax, arch, highlight_paths=None):
    """Draw the architecture grid and optional highlighted paths."""
    H = arch["height"]
    W = arch["width"]
    alg = set(arch["alg_qubits"])
    magic = set(arch["magic_states"])

    ax.clear()

    qubit_id = 0
    for row in range(H):
        for col in range(W):
            if qubit_id in magic:
                color = "orange"
            elif qubit_id in alg:
                color = "cornflowerblue"
            else:
                color = "lightgray"

            y = H - 1 - row
            rect = patches.Rectangle(
                (col, y), 1, 1,
                linewidth=1,
                edgecolor="black",
                facecolor=color
            )
            ax.add_patch(rect)

            ax.text(
                col + 0.5, y + 0.5, str(qubit_id),
                ha="center", va="center", fontsize=9
            )

            qubit_id += 1

    # draw highlighted paths if provided
    if highlight_paths:
        for path_info in highlight_paths:
            full_path, color = path_info

            for i in range(len(full_path) - 1):
                x1, y1 = full_path[i] % W, H - 1 - (full_path[i] // W)
                x2, y2 = full_path[i + 1] % W, H - 1 - (full_path[i + 1] // W)
                ax.add_line(mlines.Line2D(
                    [x1 + 0.5, x2 + 0.5],
                    [y1 + 0.5, y2 + 0.5],
                    color=color,
                    linewidth=3,
                    alpha=0.8
                ))

    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")


def visualize_steps(data):
    """Visualize each step interactively."""
    arch = data["arch"]
    steps = data["steps"]
    mapping = {int(k): v for k, v in data["map"].items()}  # logical → physical

    fig, ax = plt.subplots(figsize=(arch["width"], arch["height"]))
    current_step = [0]

    def draw_step(step_idx):
        step_data = steps[step_idx]
        highlight_paths = []
        color_map = {
            "cx": "red",
            "t": "green",
            "tdg": "green"
        }

        title_parts = []
        for gate in step_data:
            op = gate["op"]
            color = color_map.get(op, "black")
            qubits = [mapping[q] for q in gate["qubits"]]  # physical locations
            path = gate["path"]

            # Build a full physical path: start -> route -> end
            full_path = [qubits[0]] + path
            if len(qubits) > 1:
                full_path.append(qubits[1])

            highlight_paths.append((full_path, color))

            # Format title as cx(map[q0], map[q1])
            qubit_str = ", ".join(str(mapping[q]) for q in gate["qubits"])
            title_parts.append(f"{op}({qubit_str})")

        draw_arch(ax, arch, highlight_paths)
        ax.set_title(
            f"Step {step_idx + 1}/{len(steps)} — " +
            ", ".join(title_parts),
            fontsize=10
        )
        plt.draw()

    def on_key(event):
        if event.key == "right":
            if current_step[0] < len(steps) - 1:
                current_step[0] += 1
                draw_step(current_step[0])
        elif event.key == "left":
            if current_step[0] > 0:
                current_step[0] -= 1
                draw_step(current_step[0])
        elif event.key == "q":
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)
    draw_step(0)
    plt.show()


def main():
    if len(sys.argv) != 2:
        print("Usage: python visualize_arch.py architecture.json")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r") as f:
        data = json.load(f)

    visualize_steps(data)


if __name__ == "__main__":
    main()
