'''
returns the min number of timesteps when taking into account only the gate dependencies (and ignoring all routing/mapping contraints)
'''

import re
from pathlib import Path
from wisq import extract_gates_from_file
import json

def extract_gates_from_wisq_out(filename):
    with open(filename, "r") as f:
        data = json.load(f)

    ops = []
    qubits = []
    paths = []

    # "steps" is a list of lists of gate dictionaries
    for step in data.get("steps", []):
        for gate in step:
            ops.append(gate.get("op"))
            qubits.append(gate.get("qubits", []))
            paths.append(gate.get("path", []))

    return ops, qubits, paths



def min_timesteps(wisq_out_filename, take_cnot_routing_into_account=False):
    _, ops, paths = extract_gates_from_wisq_out(wisq_out_filename)

    # dependencies[i] = list of indices j s.t. j<i and gates i and j share at least one qubit
    dependencies = []

    for i, g_i in enumerate(ops):
        deps = []
        for j in range(i):
            g_j = ops[j]
            # check if they share a qubit
            if set(g_i) & set(g_j):
                deps.append(j)
            # check if their paths cross:
            elif take_cnot_routing_into_account and bool(set(paths[i]) & set(paths[j])):
                deps.append(j)
        dependencies.append(deps)

    def schedule_from_dependencies(dependencies):
        levels = [0] * len(dependencies)

        for i, deps in enumerate(dependencies):
            if deps:
                levels[i] = 1 + max(levels[j] for j in deps)
            else:
                levels[i] = 0

        # group gates by level
        schedule = []
        for i, lvl in enumerate(levels):
            while len(schedule) <= lvl:
                schedule.append([])
            schedule[lvl].append(i)
        return schedule

    return len(schedule_from_dependencies(dependencies))




"""
Read the results file and append the ideal min timesteps on each line
"""

def append_ideal_to_file(results_file_path):
    lines = Path(results_file_path).read_text().splitlines()
    updated_lines = []
    
    for line in lines:
        # Skip section headers or empty lines
        if not line.strip() or line.startswith("==="):
            updated_lines.append(line)
            continue
        
        # Skip lines where magic=None or hbm=None
        if "magic=None" in line or "hbm=None" in line:
            updated_lines.append(line)
            continue
        
        # Extract the first word (circuit name)
        match = re.match(r"(\S+)", line)
        if not match:
            updated_lines.append(line)
            continue
        
        circuit_name = match.group(1)
        wisq_out = f"/home/c/hbm/scripts/teo_output/output_180/output_180/jku_suite/{circuit_name}_hbm_run1.out"    
        
        try:
            ideal_val = min_timesteps(wisq_out)
            ideal_cnot = min_timesteps(wisq_out, take_cnot_routing_into_account=True)
            new_line = f"{line}  ideal={ideal_val}   ideal_w_cnot_routing_constraints={ideal_cnot}"
            print(new_line)
        except Exception as e:
            new_line = f"{line}  ideal=None  # Error: {e}"
        
        updated_lines.append(new_line)
    
    # Write back to the same file
    Path(results_file_path).write_text("\n".join(updated_lines) + "\n")

results_file_path = "/home/c/hbm/scripts/output_180/jku_suite/results_summary.txt"
append_ideal_to_file(results_file_path) 