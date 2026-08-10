import itertools
import math
import random
import numpy as np
from .architecture import vertical_neighbors, horizontal_neighbors
import rustworkx as rx
import os

HBM_CONFIG = os.getenv("HBM_CONFIG", "NO_CONFIG")


# shared_2-route_bottom
# shared_2-route_upper
# shared_2-route_3d
# shared_4-route_bottom
# shared_4-route_upper
# shared_4-route_3d
# shared_none-anchilla_perimeter
# shared_2-route_bottom-anchilla_perimeter
# shared_2-route_upper-anchilla_perimeter
# shared_4-route_bottom-anchilla_perimeter
# shared_4-route_upper-anchilla_perimeter

print(HBM_CONFIG)
if "shared_none" in HBM_CONFIG:
    HBM_ARCH = "ARCH_A" # ARCH_A: 1-1 connectivity
elif "route_bottom" in HBM_CONFIG:
    HBM_ARCH = "ARCH_B" # ARCH_B: route below then connect to top
elif "route_3d" in HBM_CONFIG:
    HBM_ARCH = "ARCH_D" # ARCH_D: generic 3D routing, elevator up/down anywhere
elif "route_upper" in HBM_CONFIG:
    HBM_ARCH = "ARCH_C" # ARCH_C: connect to top then route on top
elif "no_hbm" in HBM_CONFIG or HBM_CONFIG == "NO_CONFIG":
    HBM_ARCH = "NO_HBM"
else:
    raise ValueError("invalid HBM_CONFIG option")
print(HBM_ARCH)


def _build_3d_graph(grid_len, grid_height, to_remove_lower, to_remove_upper):
    """Two stacked planes with an elevator edge at every cell.

    Lower plane payloads: [0, N). Upper plane payloads: [N, 2N).
    Nodes in `to_remove_lower` are excised from the lower plane; likewise
    `to_remove_upper` from the upper plane. Elevator edges connect payload i
    to payload i + N whenever both endpoints remain in the graph.
    """
    N = grid_len * grid_height
    g = rx.PyGraph()
    payload_to_idx = {}

    def add(payload):
        idx = g.add_node(payload)
        payload_to_idx[payload] = idx
        return idx

    for p in range(N):
        if p not in to_remove_lower:
            add(p)
    for p in range(N):
        upper_payload = p + N
        if p not in to_remove_upper:
            add(upper_payload)

    for p in range(N):
        r, c = divmod(p, grid_len)
        for np_ in (p + 1 if c + 1 < grid_len else None,
                    p + grid_len if r + 1 < grid_height else None):
            if np_ is None:
                continue
            if p in payload_to_idx and np_ in payload_to_idx:
                g.add_edge(payload_to_idx[p], payload_to_idx[np_], 1)
            up_a, up_b = p + N, np_ + N
            if up_a in payload_to_idx and up_b in payload_to_idx:
                g.add_edge(payload_to_idx[up_a], payload_to_idx[up_b], 1)
        elev_a, elev_b = p, p + N
        if elev_a in payload_to_idx and elev_b in payload_to_idx:
            g.add_edge(payload_to_idx[elev_a], payload_to_idx[elev_b], 1)

    return g, payload_to_idx, N

def route_gate(
    indexed_gate, grid_len, grid_height, msf_faces, mapping, to_remove, to_remove_hbm, take_first_ms
):
    print("trying gate...", indexed_gate, f"({mapping[indexed_gate[1][0]]})")
    device_graph = rx.generators.grid_graph(rows=grid_height, cols=grid_len)
    for idx in device_graph.node_indices():
        device_graph[idx] = idx  # payload = original index
    # print("init nodes:",device_graph.node_indices())

    # remove nodes by converting payload -> internal index
    device_graph.remove_nodes_from([
        device_graph.find_node_by_weight(v) for v in to_remove if device_graph.find_node_by_weight(v) is not None
    ])
    # print("first to remove:", to_remove)
    # print("nodes after 1st removal:",device_graph.node_indices())
    hbm_graph = rx.generators.grid_graph(rows=grid_height, cols=grid_len)
    for idx in hbm_graph.node_indices():
        hbm_graph[idx] = idx
    hbm_graph.remove_nodes_from([
        hbm_graph.find_node_by_weight(v) for v in to_remove_hbm if hbm_graph.find_node_by_weight(v) is not None
    ])

    shortest_path_len = 2**31 - 1
    shortest_pair = None

    id, gate = indexed_gate
    if len(gate) == 2 and HBM_ARCH == "ARCH_D":
        # Generic 3D CNOT routing: endpoints stay on the lower plane
        # (data qubits are lower-plane), but the path may detour through
        # the upper plane's free ancilla cells via elevator edges.
        g3d, payload_to_idx, N = _build_3d_graph(
            grid_len, grid_height, to_remove, to_remove_hbm
        )
        src_payloads = vertical_neighbors(
            mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
        )
        tgt_payloads = horizontal_neighbors(
            mapping[gate[1]], grid_len, grid_height, omitted_edges=[]
        )

        shortest_path_len = 2**31 - 1
        shortest_route = None
        for s_pl in src_payloads:
            if s_pl not in payload_to_idx:
                continue
            s_idx = payload_to_idx[s_pl]
            dist_map = rx.dijkstra_shortest_path_lengths(
                g3d, edge_cost_fn=lambda w: w, node=s_idx, goal=None,
            )
            for t_pl in tgt_payloads:
                if t_pl not in payload_to_idx:
                    continue
                t_idx = payload_to_idx[t_pl]
                d = dist_map[t_idx] if t_idx in dist_map else math.inf
                if d < shortest_path_len:
                    shortest_path_len = d
                    shortest_route = (s_idx, t_idx)

        if shortest_route is None:
            return [], to_remove, to_remove_hbm

        s_idx, t_idx = shortest_route
        if s_idx == t_idx:
            path_payloads = [g3d.get_node_data(s_idx)]
        else:
            path_internal = list(rx.dijkstra_shortest_paths(
                g3d, source=s_idx, target=t_idx
            )[t_idx])
            path_payloads = [g3d.get_node_data(i) for i in path_internal]

        for pl in path_payloads:
            if pl < N:
                to_remove.add(pl)
            else:
                to_remove_hbm.add(pl - N)
        return [(id, gate, path_payloads)], to_remove, to_remove_hbm
    elif len(gate) == 2:
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
        if HBM_ARCH == "ARCH_A":
            # don't even route T gates
            return ([(id, gate, [])], to_remove, to_remove_hbm)
        elif HBM_ARCH == "ARCH_D":
            # Generic 3D routing: build a two-plane graph with an elevator
            # edge at every cell and let Dijkstra pick where to hop up/down.
            # Source candidates are lower-plane neighbors of the data qubit;
            # target candidates are upper-plane neighbors of any magic-state
            # face (encoded as payload + N).
            g3d, payload_to_idx, N = _build_3d_graph(
                grid_len, grid_height, to_remove, to_remove_hbm
            )
            src_payloads = vertical_neighbors(
                mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
            ) + horizontal_neighbors(
                mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
            )
            tgt_payloads = []
            for m in msf_faces:
                for hn in horizontal_neighbors(m, grid_len, grid_height, omitted_edges=[]):
                    tgt_payloads.append(hn + N)
                for vn in vertical_neighbors(m, grid_len, grid_height, omitted_edges=[]):
                    tgt_payloads.append(vn + N)

            shortest_path_len = 2**31 - 1
            shortest_route = None
            for s_pl in src_payloads:
                if s_pl not in payload_to_idx:
                    continue
                s_idx = payload_to_idx[s_pl]
                dist_map = rx.dijkstra_shortest_path_lengths(
                    g3d, edge_cost_fn=lambda w: w, node=s_idx,
                    goal=None,
                )
                for t_pl in tgt_payloads:
                    if t_pl not in payload_to_idx:
                        continue
                    t_idx = payload_to_idx[t_pl]
                    d = dist_map[t_idx] if t_idx in dist_map else math.inf
                    if d < shortest_path_len:
                        shortest_path_len = d
                        shortest_route = (s_idx, t_idx)
                        if take_first_ms:
                            break
                if take_first_ms and shortest_route is not None:
                    break

            if shortest_route is None:
                return [], to_remove, to_remove_hbm

            s_idx, t_idx = shortest_route
            if s_idx == t_idx:
                path_payloads = [g3d.get_node_data(s_idx)]
            else:
                path_internal = list(rx.dijkstra_shortest_paths(
                    g3d, source=s_idx, target=t_idx
                )[t_idx])
                path_payloads = [g3d.get_node_data(i) for i in path_internal]

            for pl in path_payloads:
                if pl < N:
                    to_remove.add(pl)
                else:
                    to_remove_hbm.add(pl - N)
            return [(id, gate, path_payloads)], to_remove, to_remove_hbm
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
            pairs = [
                (mapping[gate[0]], hn) if vn in sorted_msf else (vn, hn)
                for magic_state in sorted_msf
                for vn in vertical_neighbors(
                    mapping[gate[0]], grid_len, grid_height, omitted_edges=[]
                )
                for hn in horizontal_neighbors(
                    magic_state, grid_len, grid_height, omitted_edges=[]
                )
            ]
    pairs_before_filter = pairs
    # filter pairs by checking payload existence
    if HBM_ARCH == "ARCH_C" and len(gate) == 1: # for T gates in ARCH_C:
        pairs = [
            (s, t) for s, t in pairs
            if hbm_graph.find_node_by_weight(s) is not None
            and hbm_graph.find_node_by_weight(t) is not None
        ]
    else:
        pairs = [
            (s, t) for s, t in pairs
            if device_graph.find_node_by_weight(s) is not None
            and device_graph.find_node_by_weight(t) is not None
        ]

    
    graph_to_use = hbm_graph if (HBM_ARCH == "ARCH_C" and len(gate) == 1) else device_graph
    
    print("nodes:",graph_to_use.node_indices())
    pairs = list(pairs)
    print("Pairs before filter:", pairs_before_filter)
    print("Pairs after filter:", pairs)
    
    for s_payload, t_payload in pairs:
        # convert payload -> internal index
        s = graph_to_use.find_node_by_weight(s_payload)
        t = graph_to_use.find_node_by_weight(t_payload)
        if s is None or t is None:
            print(f"pair {s_payload, t_payload} is None ({s,t})")
            continue

        const_1 = lambda _: 1
        dist_dict = rx.dijkstra_shortest_path_lengths(
            graph_to_use, edge_cost_fn=const_1, node=s, goal=t
        )
        dist = dist_dict[t] if t in dist_dict else math.inf

        if dist < shortest_path_len:
            shortest_path_len = dist
            shortest_pair = s, t
            if take_first_ms and len(gate) == 1:
                break

    if shortest_pair is not None:
        s, t = shortest_pair
        # print(s,t)
        # print(graph_to_use.nodes())
        # print(graph_to_use.node_indices())
        
        # convert internal indices -> payloads
        if s==t:
            path = []
        else:
            path_internal = list(rx.dijkstra_shortest_paths(graph_to_use, source=s, target=t)[t])
            path = [graph_to_use.get_node_data(i) for i in path_internal]
        if s not in path:
            path = [graph_to_use.get_node_data(s)] + path
        if t not in path:
            path.append(graph_to_use.get_node_data(t))
        # route = [(id, gate, path)]
        # for v in path:
        #     to_remove.add(v)
        #to_remove.add(v) is not updated 
        #after routing
        route = [(id, gate, path)]                                                                                
        for v in path:
            if HBM_ARCH == "ARCH_C" and len(gate) == 1:
                to_remove_hbm.add(v)
            else:
                to_remove.add(v)
    else:
        route = []
    return route, to_remove, to_remove_hbm


def try_order(
    order, executable, grid_len, grid_height, msf_faces, mapping, take_first_ms
):
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
    to_remove = set()
    to_remove_hbm = set()

    if HBM_ARCH=="ARCH_A":
        for q in mapping.keys():
            to_remove.add(mapping[q])
        # do not remove magic states
    elif HBM_ARCH=="ARCH_B":
        for q in mapping.keys():
            to_remove.add(mapping[q])
        # do not remove magic states
    elif HBM_ARCH=="ARCH_C":
        # remove magic states from upper plane
        for f in msf_faces:
            to_remove_hbm.add(f)
        # remove data from lower plane
        for q in mapping.keys():
            to_remove.add(mapping[q])
    elif HBM_ARCH=="ARCH_D":
        # 3D routing: magic-state faces occupy upper plane terminals;
        # data qubits occupy lower plane cells.
        for f in msf_faces:
            to_remove_hbm.add(f)
        for q in mapping.keys():
            to_remove.add(mapping[q])
    else:
        for q in mapping.keys():
            to_remove.add(mapping[q])
        for f in msf_faces:
            to_remove.add(f)
    # print("to remove:", to_remove)
    return to_remove,to_remove_hbm


def shortest_path(gate, mapping, grid_len, grid_height, msf_faces):
    shortest_path_len = 2**31 - 1
    if len(gate) == 1:
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
    msf_faces = arch["magic_states"]
    t_indices = [
        i for (i, (id, gate)) in enumerate(executable.items()) if len(gate) == 1
    ]
    cnot_indices = [
        i for (i, (id, gate)) in enumerate(executable.items()) if len(gate) == 2
    ]
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
    return g1[0] > g2[0] and len(set(g1[1]).intersection(g2[1])) > 0
