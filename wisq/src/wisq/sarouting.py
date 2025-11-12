import itertools
import math
import random
import numpy as np
from .architecture import vertical_neighbors, horizontal_neighbors, are_adjacent
import rustworkx as rx
import os

HBM_ARCH = os.getenv("HBM_ARCH", "NO_HBM") # ARCH_A: 1-1 connectivity, ARCH_B: route below then connect to top, ARCH_C: connect to top then route on top
if HBM_ARCH not in ["NO_HBM", "ARCH_A", "ARCH_B", "ARCH_C"]:
    raise ValueError("HBM_ARCH can be only ARCH_A: 1-1 connectivity, ARCH_B: route below then connect to top, ARCH_C: connect to top then route on top. Thanks.")
HBM_BENDS = os.getenv("BENDS", "False") == "True"
print("HBM mode:", HBM_ARCH, "bends:", HBM_BENDS)

def route_gate(
    indexed_gate, grid_len, grid_height, msf_faces, mapping, to_remove, to_remove_hbm, take_first_ms
):
    device_graph = rx.generators.grid_graph(rows=grid_height, cols=grid_len)
    hbm_graph = rx.generators.grid_graph(rows=grid_height, cols=grid_len)
    device_graph.remove_nodes_from(list(to_remove))
    hbm_graph.remove_nodes_from(list(to_remove_hbm))
    shortest_path_len = 2**31 - 1
    shortest_pair = None

    id, gate = indexed_gate
    # print(f"    trying gate {id}({mapping[gate[0]], mapping[gate[1]]})")
    if len(gate) == 2:
        pairs = [
            (vn, hn)
            for vn in vertical_neighbors(
                mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
            )
            for hn in horizontal_neighbors(
                mapping[gate[1]], grid_len, grid_height, omitted_edges=[]
            )
        ]
        print(f"    cnot pairs {pairs}")
        print(msf_faces)
        print(list(mapping[q] for q in mapping.keys()))
        print(grid_len, grid_height)
    elif len(gate) == 1 and HBM_ARCH == "ARCH_A":
        # don't even route T gates
        return ([(id, gate, [])], to_remove, to_remove_hbm)
    else:
        sorted_msf = sorted(
            msf_faces,
            key=lambda m: abs(
                list(reversed(divmod(m, grid_len)))[0]
                - list(reversed(divmod(mapping[gate[0]], grid_len)))[0]
            )
            + abs(
                list(reversed(divmod(m, grid_len)))[1]
                - list(reversed(divmod(mapping[gate[0]], grid_len)))[1]
            ),
        )

        if (HBM_BENDS == False) and (HBM_ARCH == "ARCH_B" or HBM_ARCH == "ARCH_C"):
            # normally we would only need a single pair connecting the magic state to the data qubit,
            # but since both the data qubit and magic state have been removed from the graph
            # to prevent being occupied by other paths, we generate all pairs between their
            # neighbors instead
        
            pairs = []
            data_node = mapping[gate[0]]
            print(f"data qubit {data_node}, magic states: {sorted_msf}")
            data_neighbors = vertical_neighbors(data_node, grid_len, grid_height, omitted_edges=[]) + \
                            horizontal_neighbors(data_node, grid_len, grid_height, omitted_edges=[])

            for magic_state in sorted_msf:
                magic_neighbors = vertical_neighbors(magic_state, grid_len, grid_height, omitted_edges=[]) + \
                                horizontal_neighbors(magic_state, grid_len, grid_height, omitted_edges=[])
                for dn in data_neighbors:
                    for mn in magic_neighbors:
                        print(f"data neighbor {dn}, magic neighbor {mn}")
                        pairs.append((dn, mn))

            print(f"all pairs:{pairs}")

        else: # route to the horizontal neighbors of the anchila below the magic qubit in ARCH_B/the anchila above the data qubit in ARCH_C
            pairs = [
                (vn, hn) # all possible combinations of vertical neighboors of data qubits and horizontal of magic qubits 
                for magic_state in sorted_msf
                for vn in vertical_neighbors(
                    mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
                )
                for hn in horizontal_neighbors(  
                    magic_state, grid_len, grid_height, omitted_edges=[]
                )
            ]
    if HBM_ARCH == "NO_HBM" or HBM_ARCH == "ARCH_A":
        pairs = filter(
            lambda p: device_graph.has_node(p[0]) and device_graph.has_node(p[1]), pairs # removes the above pairs which contain endpoints occupied by already routed gates
        )
    elif HBM_ARCH == "ARCH_B":
        if gate in msf_faces:
            return ([(id, gate, [])], to_remove, to_remove_hbm) # if this data qubit has a magic state directly on top of it just connect to that one without routing the T gate
        pairs = filter(
            lambda p: device_graph.has_node(p[0]) and device_graph.has_node(p[1]), pairs 
        )
    elif HBM_ARCH == "ARCH_C":
        if gate in msf_faces:
            return ([(id, gate, [])], to_remove, to_remove_hbm)
        if (len(gate)==1): # t gate
            pairs = filter(
                lambda p: hbm_graph.has_node(p[0]) and hbm_graph.has_node(p[1]), pairs 
            )
        else:
            pairs = filter(
                lambda p: device_graph.has_node(p[0]) and device_graph.has_node(p[1]), pairs 
            )
    # 
    pairs=list(pairs)
    print(f"filtered pairs:{pairs}")
    # if (len(gate) == 1): 
    #     a=1/0
    #     print(f"filtered pairs:{list(pairs)}")
    
    shortest_pair = None
    shortest_path_len = 2**31 - 1

    graph_to_use = hbm_graph if (HBM_ARCH == "ARCH_C" and len(gate)==1) else device_graph

    for s, t in pairs:
        print(s,t)
        if not HBM_BENDS \
        and ((HBM_ARCH == "ARCH_B" or HBM_ARCH == "ARCH_C") and len(gate)==1) \
        and are_adjacent(s, t, grid_len):
            return [(id, gate, [s,t])], to_remove, to_remove_hbm


        const_1 = lambda _: 1
        dist_dict = rx.dijkstra_shortest_path_lengths(graph_to_use, node=s, edge_cost_fn=const_1)
        if t not in dist_dict:
            # t is not reachable from s, skip this pair
            continue

        dist = dist_dict[t]
        print(dist)
        if dist < shortest_path_len:
            shortest_path_len = dist
            shortest_pair = s, t
            if take_first_ms and len(gate) == 1:
                break

    # Build the path if a reachable pair was found
    if shortest_pair is not None:
        s, t = shortest_pair
        # print("target node:", t)
        # print(f"to_remove: {to_remove}")
        # print(f"to_remove_hbm: {to_remove_hbm}")

        path = list(rx.dijkstra_shortest_paths(graph_to_use, source=s, target=t)[t])

        if s not in path:
            path = [s] + path
        if t not in path:
            path.append(t)
        route = [(id, gate, path)]
        for v in path:
            if HBM_ARCH == "ARCH_C":
                to_remove_hbm.add(v)
            else:
                to_remove.add(v)
    else:
        print("else")
        route = []
    print(route)
    return route, to_remove, to_remove_hbm


def try_order(
    order, executable, grid_len, grid_height, msf_faces, mapping, take_first_ms
):
    # print(f"trying order {order}")
    step = []
    to_remove, to_remove_hbm = initialize_to_remove(msf_faces, mapping)
    for i in range(len(executable)):
        gate = list(executable.items())[order[i]]
        route, to_remove, to_remove_hbm = route_gate(
            gate, grid_len, grid_height, msf_faces, mapping, to_remove, to_remove_hbm, take_first_ms
        )
        step.extend(route)
    return step


def initialize_to_remove(msf_faces, mapping):
    # print()
    # print(mapping)
    # print(msf_faces)
    # a=1/0
    to_remove = set()
    to_remove_hbm = set()
    if HBM_ARCH == "NO_HBM": # remove both magic and qubits from lower, do not care about higher
        for q in mapping.keys():
            to_remove.add(mapping[q])
        for f in msf_faces:
            to_remove.add(f)

    elif HBM_ARCH == "ARCH_A": # do not remove magic from lower, do not care about higher
        for q in mapping.keys():
            to_remove.add(mapping[q])

    elif HBM_ARCH == "ARCH_B": # do not remove magic from lower, remove magic from higher
        for q in mapping.keys():
            to_remove.add(mapping[q])

        # for f in msf_faces:
        #     # remove magic-state positions from the device layer to prevent routing paths
        #     # from occupying these nodes. This ensures that data qubits can always be connected
        #     # to the anchilla below a magic state qubit and are not blocked by other routed T gate path.
        #     to_remove.add(f) 

    elif HBM_ARCH == "ARCH_C":
        for q in mapping.keys():
            to_remove.add(mapping[q])

            # # remove data qubit positions from the HBM graph to prevent routing paths
            # # from occupying the nodes directly above them. This ensures that each
            # # data qubit can always connect to the HBM layer above without being blocked
            # # by some other routed T gate path.
            # to_remove_hbm.add(mapping[q])

        for f in msf_faces:
            to_remove_hbm.add(f)

    return to_remove,to_remove_hbm

        


def shortest_path(gate, mapping, grid_len, grid_height, msf_faces):
    shortest_path_len = 2**31 - 1
    if len(gate) == 1:
        if HBM:
            return 0
        else:
            return shortest_path_len
    if len(gate) == 2:
        pairs = [
            (vn, hn)
            for vn in vertical_neighbors(
                mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
            )
            for hn in horizontal_neighbors(
                mapping[gate[1]], grid_len, grid_height, omitted_edges=[]
            )
        ]
    else:
        pairs = [
            (vn, hn)
            for magic_state in msf_faces
            for vn in vertical_neighbors(
                mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
            )
            for hn in horizontal_neighbors(
                magic_state, grid_len, grid_height, omitted_edges=[]
            )
        ]
    for s, t in pairs:
        dist = rx.dijkstra_shortest_path_lengths(
            rx.generators.grid_graph(rows=grid_height, cols=grid_len), node=s, goal=t
        )[t]
        if dist < shortest_path_len:
            shortest_path_len = dist
    return shortest_path_len


def gates_routed(step, remaining_gates, crit_dict):
    return len(step)


def criticality(step, remaining_gates, crit_dict):
    paths = 0
    for id, qubits, path in step:
        dependent = get_dependent_gates((id, qubits), remaining_gates)
        depths = get_depth_by_qubit(dependent)
        crit_path = max(depths.get(q, 0) for q in depths.keys())
        paths += 1 + crit_path
    return paths


def criticality_fast(step, remaining_gates, crit_dict):
    paths = 0
    for id, qubits, path in step:
        paths += crit_dict[id]
    return paths


def build_crit_dict(gates):
    crit_dict = {}
    for id, qubits in gates.items():
        dependent = get_dependent_gates((id, qubits), gates)
        depths = get_depth_by_qubit(dependent)
        crit_path = max(depths.get(q, 0) for q in qubits)
        crit_dict[id] = crit_path
    return crit_dict


def build_crit_dict_fast(gates: list[int]) -> dict[int, int]:
    crit_dict: dict[int, int] = {}
    last_id_per_qubit: dict[int, int] = {}
    for id in range(len(gates) - 1, -1, -1):
        gate = gates[id]
        if len(gate) == 1 and HBM_ARCH == "ARCH_A": # maybe set 0 for all T gates which have a magic qubit above them
            crit_dict[id] = 0
        else:
            max_crit = 1
            for qubit in gate:
                if qubit not in last_id_per_qubit:
                    continue
                max_crit = max(max_crit, crit_dict[last_id_per_qubit[qubit]] + 1)
            crit_dict[id] = max_crit
        for qubit in gate:
            last_id_per_qubit[qubit] = id
    return crit_dict


def dependent(step, remaining_gates):
    deps = 0
    for id, qubits, path in step:
        dependent = get_dependent_gates((id, qubits), remaining_gates)
        deps += len(dependent)
    return deps


def best_realizable_set_found(
    gates,
    executable,
    arch,
    mapping,
    initial_order,
    reward_name,
    crit_dict,
    order_fraction,
    temperature=10,
    cooling_rate=0.1,
    termination_temp=0.1,
    take_first_ms=False,
):
    grid_len = arch["width"]
    grid_height = arch["height"]
    if HBM_ARCH == "NO_HBM":
        msf_faces = arch["magic_states"]
    elif HBM_ARCH == "ARCH_A":
        msf_faces = arch["alg_qubits"] # not being used anyway
    elif HBM_ARCH == "ARCH_B":
        msf_faces = arch["magic_states"] # check if it error if you also define a magic state in the same pos a data qubit is
    elif HBM_ARCH == "ARCH_C":
        msf_faces = arch["magic_states"]
    
    t_indices = [
        i for (i, (id, gate)) in enumerate(executable.items()) if len(gate) == 1
    ]
    cnot_indices = [
        i for (i, (id, gate)) in enumerate(executable.items()) if len(gate) == 2
    ]

    # Skip T gates entirely from annealing if ARCH_A (they are “free”)
    # if HBM_ARCH == "ARCH_A":
        # t_indices = []

    if initial_order == "naive":
        best_order = cnot_indices + t_indices
        best_step = try_order(
            best_order,
            executable,
            grid_len,
            grid_height,
            msf_faces,
            mapping,
            take_first_ms,
        )
        current_order = best_order
        current_step = best_step
    elif initial_order == "random":
        best_order = cnot_indices + t_indices
        random.shuffle(best_order)
        best_step = try_order(
            best_order,
            executable,
            grid_len,
            grid_height,
            msf_faces,
            mapping,
            take_first_ms,
        )
        current_order = best_order
        current_step = best_step
    elif initial_order == "shortest_first":
        shortest_cnot = sorted(
            tuple(range(len(cnot_indices))),
            key=lambda x: shortest_path(
                list(executable.items())[x][1],
                mapping,
                grid_len,
                grid_height,
                msf_faces,
            ),
        )
        shortest_t = sorted(
            tuple(range(len(t_indices))),
            key=lambda x: shortest_path(
                list(executable.items())[x][1],
                mapping,
                grid_len,
                grid_height,
                msf_faces,
            ),
        )
        shortest_first = shortest_cnot + shortest_t
        best_order = shortest_first
        best_step = try_order(
            best_order,
            executable,
            grid_len,
            grid_height,
            msf_faces,
            mapping,
            take_first_ms,
        )
        current_order = best_order
        current_step = best_step
    routed_ids = [x[0] for x in best_step]
    best_remaining_gates = {k: v for k, v in gates.items() if k not in routed_ids}
    name_to_func = {
        "gates_routed": gates_routed,
        "criticality": criticality_fast,
        "dependent": dependent,
    }

    reward_func = name_to_func[reward_name]
    orders_tried_count = 1
    if len(executable) < 2:
        return best_step, 1

    elif (len(cnot_indices) < 5 and len(t_indices) < 5) and cooling_rate != 1:
        # print("exhaustive step")
        all_cnot_orders = itertools.permutations(cnot_indices)
        all_t_orders = itertools.permutations(t_indices)
        orders = list(itertools.product(all_cnot_orders, all_t_orders))
        random.shuffle(orders)
        sample_size = int(len(orders) * order_fraction)
        # print(sample_size, len(orders))

        orders_to_explore = orders[:sample_size]
        for cnot_order, t_order in orders_to_explore:
            order = list(cnot_order) + list(t_order)
            new_step = try_order(
                order,
                executable,
                grid_len,
                grid_height,
                msf_faces,
                mapping,
                take_first_ms,
            )
            orders_tried_count += 1
            routed_ids = [x[0] for x in new_step]
            new_remaining_gates = {
                k: v for k, v in gates.items() if k not in routed_ids
            }
            # print(f"considering step {new_step}", f"reward: {reward_func(new_step, new_remaining_gates)}")
            if reward_func(new_step, new_remaining_gates, crit_dict) > reward_func(
                best_step, best_remaining_gates, crit_dict
            ):
                best_step = new_step
        return best_step, orders_tried_count

    else:
        while temperature > termination_temp:
            new_order = current_order.copy()
            cnots, ts = new_order[: len(cnot_indices)], new_order[len(cnot_indices) :]
            if len(cnots) > 1:
                ind1, ind2 = np.random.choice(
                    range(len(cnot_indices)), size=2, replace=False
                )
                cnots[ind1], cnots[ind2] = cnots[ind2], cnots[ind1]
            if len(ts) > 1:
                ind1, ind2 = np.random.choice(
                    range(len(t_indices)), size=2, replace=False
                )
                ts[ind1], ts[ind2] = ts[ind2], ts[ind1]
            new_order = cnots + ts
            new_step = try_order(
                new_order,
                executable,
                grid_len,
                grid_height,
                msf_faces,
                mapping,
                take_first_ms,
            )
            orders_tried_count += 1
            routed_ids = [x[0] for x in new_step]
            new_remaining_gates = {
                k: v for k, v in gates.items() if k not in routed_ids
            }
            delta_curr = reward_func(
                current_step, best_remaining_gates, crit_dict
            ) - reward_func(new_step, new_remaining_gates, crit_dict)
            delta_best = reward_func(
                best_step, best_remaining_gates, crit_dict
            ) - reward_func(new_step, new_remaining_gates, crit_dict)
            if delta_curr < 0 or np.random.rand() < np.exp(-delta_curr / temperature):
                current_order = new_order
                current_step = new_step
            if delta_best < 0:
                # print(len(best_step))
                best_order = new_order
                best_step = new_step
            temperature *= 1 - cooling_rate
        return best_step, orders_tried_count


def sim_anneal_route(
    gates,
    arch,
    mapping,
    temperature,
    cooling_rate,
    termination_temp,
    order_fraction,
    initial_order="random",
    reward_name="criticality",
    take_first_ms=True,
):
    timesteps = []
    grid_len = arch["width"]
    grid_height = arch["height"]
    msf_faces = arch["magic_states"]
    mapping = {q: p for (q, p) in mapping}
    gates_id_table = {i: gate for i, gate in enumerate(gates)}
    crit_dict = {}
    if temperature > termination_temp:
        crit_dict = build_crit_dict_fast(gates)
    tried_steps = 0
    while len(gates_id_table) != 0:
        executable, remaining = executable_subset(gates_id_table)
        step, tried = best_realizable_set_found(
            gates_id_table,
            executable,
            arch,
            mapping,
            order_fraction=order_fraction,
            crit_dict=crit_dict,
            temperature=temperature,
            cooling_rate=cooling_rate,
            termination_temp=termination_temp,
            initial_order=initial_order,
            reward_name=reward_name,
            take_first_ms=take_first_ms,
        )
        tried_steps += tried
        timesteps.append(step)
        routed_ids = [x[0] for x in step]
        not_executed = {
            id: gates_id_table[id] for id in executable if id not in routed_ids
        }
        gates_id_table = {**not_executed, **remaining}
    # print(f'routing orders tried {tried_steps}')
    return timesteps, tried_steps


def get_depth_by_qubit(gates):
    depth_by_qubit = {}
    for i in gates:
        qubits = gates[i]
        depths = (depth_by_qubit.get(q, 0) for q in qubits)
        max_depth = max(depths)
        for qubit in qubits:
            depth_by_qubit[qubit] = 1 + max_depth
    return depth_by_qubit


def get_depth_by_qubit_p(start_id, gates):
    depth_by_qubit = {}
    touched_qubits = {q for q in gates[start_id]}
    for i in range(start_id, len(gates)):
        qubits = gates[i]
        if len(touched_qubits.intersection(qubits)) > 0:
            touched_qubits.update(qubits)
            depths = (depth_by_qubit.get(q, 0) for q in qubits)
            max_depth = max(depths)
            for qubit in qubits:
                depth_by_qubit[qubit] = 1 + max_depth
    return depth_by_qubit


def get_dependent_gates(gate_tuple, remaining):
    id, initial_gate = gate_tuple
    dependent = {}
    dependent[id] = initial_gate
    for id, gate in remaining.items():
        if any(depends_on((id, gate), added) for added in dependent.items()):
            dependent[id] = gate

    return dependent


def executable_subset(gates: dict):
    executable = {}
    remainining = {}
    blocked_qubits = set()
    for i, gate in gates.items():
        not_blocked = all([q not in blocked_qubits for q in gate])
        if not_blocked:
            executable[i] = gates[i]
            blocked_qubits.update(set(q for q in gate))
        else:
            remainining[i] = gates[i]
            blocked_qubits.update(set(q for q in gate))
    return executable, remainining


def depends_on(g1, g2):
    # For ARCH_A, treat T gates as independent (they execute instantly)
    if HBM_ARCH == "ARCH_A" and (len(g1[1]) == 1 or len(g2[1]) == 1):
        return False
    return g1[0] > g2[0] and len(set(g1[1]).intersection(g2[1])) > 0
