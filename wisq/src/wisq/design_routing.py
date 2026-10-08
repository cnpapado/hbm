"""Routing for HBM_DESIGN runs: magic-state sources with finite recharge.

sarouting calls into this module only when HBM_DESIGN is set; legacy HBM_CONFIG runs never
reach it. Rules per timestep (one lattice-surgery step = d rounds):

  - every source tile holds at most one T state, and a T gate consumes one ready source;
  - a source used at step t is ready again at step t + 1 + recharge_steps;
  - a T gate first tries a direct source (on its vertical side or directly above it, no
    routing tiles); if the design allows routing it then routes to any ready source,
    reaching any free side of that source;
  - CNOTs route as in DASCOT: from a vertical neighbour of the control to a horizontal
    neighbour of the target, in-plane (on the two-layer graph for TOP_3D designs).

Paths in the output use lower-plane positions as-is and top-layer positions offset by
width * height (the ARCH_D convention). Direct T gates have an empty path.
"""

import rustworkx as rx

from .designs import direct_sources

CTX = None


class Step(list):
    """A routed timestep; `state` keeps the bookkeeping of the order that produced it."""

    __slots__ = ("state",)


class StepState:
    __slots__ = ("lower", "upper", "consumed", "face_of", "mode", "fail")

    def __init__(self, lower, upper):
        self.lower = lower  # occupied lower-plane tiles (data, sources, factories, paths)
        self.upper = upper  # occupied top-layer tiles
        self.consumed = set()  # sources used in this step
        self.face_of = {}  # gate id -> source used
        self.mode = {}  # gate id -> "direct" | "routed"
        self.fail = {}  # gate id -> "magic_wait" | "blocked"


class Context:
    def __init__(self, design, arch, mapping):
        self.design = design
        self.width = arch["width"]
        self.height = arch["height"]
        self.n_tiles = self.width * self.height
        self.mapping = mapping
        self.faces = list(arch["magic_states"])
        self.ready_at = {f: 0 for f in self.faces}
        self.recharge = design.recharge_steps
        self.direct = direct_sources(arch, design)
        self.face_nbrs = {f: self._neighbors(f) for f in self.faces}
        faces = set(self.faces)
        on_top = design.placement == "top"
        self.base_lower = (set(mapping.values()) | set(arch.get("blocked", []))
                           | (set() if on_top else faces))
        self.base_upper = set(arch.get("blocked_top", [])) | (faces if on_top else set())
        self.t = 0
        self.used_faces = set()
        self.stats = dict(
            design=design.spec, steps=0, t_gates=0, t_direct=0, t_routed=0, cx_gates=0,
            t_path_tiles=0, cx_path_tiles=0, vertical_merges=0, stall_magic_wait=0,
            stall_t_blocked=0, stall_cx_blocked=0, empty_steps=0, sources_used=0,
        )

    def vertical(self, p):
        r, c = divmod(p, self.width)
        return [x * self.width + c for x in (r - 1, r + 1) if 0 <= x < self.height]

    def horizontal(self, p):
        r, c = divmod(p, self.width)
        return [r * self.width + x for x in (c - 1, c + 1) if 0 <= x < self.width]

    def _neighbors(self, p):
        return self.vertical(p) + self.horizontal(p)


def begin(design, arch, mapping):
    """Reset the routing context at the start of a run."""
    global CTX
    CTX = Context(design, arch, mapping)
    return CTX


def stats():
    return None if CTX is None else dict(CTX.stats)


# --------------------------------------------------------------------------------------
# Graphs and paths
# --------------------------------------------------------------------------------------

def _plane_graph(removed):
    w, h = CTX.width, CTX.height
    g = rx.PyGraph()
    idx = {p: g.add_node(p) for p in range(w * h) if p not in removed}
    for p, i in idx.items():
        r, c = divmod(p, w)
        if c + 1 < w and p + 1 in idx:
            g.add_edge(i, idx[p + 1], 1)
        if r + 1 < h and p + w in idx:
            g.add_edge(i, idx[p + w], 1)
    return g, idx


def _graph_3d(removed_lower, removed_upper):
    """Two stacked planes; upper payloads are offset by N; an elevator edge at every cell."""
    w, h, n = CTX.width, CTX.height, CTX.n_tiles
    g = rx.PyGraph()
    idx = {}
    for p in range(n):
        if p not in removed_lower:
            idx[p] = g.add_node(p)
    for p in range(n):
        if p not in removed_upper:
            idx[p + n] = g.add_node(p + n)
    for p in range(n):
        r, c = divmod(p, w)
        for q in ((p + 1) if c + 1 < w else None, (p + w) if r + 1 < h else None):
            if q is None:
                continue
            for off in (0, n):
                if p + off in idx and q + off in idx:
                    g.add_edge(idx[p + off], idx[q + off], 1)
        if p in idx and p + n in idx:
            g.add_edge(idx[p], idx[p + n], 1)
    return g, idx


def _best_path(g, idx, sources, targets):
    """Shortest path (as payloads) from any source to any target, or None."""
    targets = {t for t in targets if t in idx}
    if not targets:
        return None
    best = None
    for s in sources:
        if s not in idx:
            continue
        if s in targets:
            return [s]
        paths = rx.dijkstra_shortest_paths(g, idx[s])
        for t in targets:
            ti = idx[t]
            if ti in paths:
                path = [g[i] for i in paths[ti]]
                if best is None or len(path) < len(best):
                    best = path
    return best


def _targets(avail, occupied, offset=0):
    """Free neighbours of available sources -> source, for path endpoints."""
    out = {}
    for f in avail:
        for nb in CTX.face_nbrs[f]:
            if nb not in occupied:
                out.setdefault(nb + offset, f)
    return out


def _claim_3d(st, path):
    """Mark the tiles of a two-layer path as occupied on their own layer."""
    n = CTX.n_tiles
    for p in path:
        if p >= n:
            st.upper.add(p - n)
        else:
            st.lower.add(p)


# --------------------------------------------------------------------------------------
# Gate routing
# --------------------------------------------------------------------------------------

def _route_cnot(gid, gate, st):
    c, t = CTX.mapping[gate[0]], CTX.mapping[gate[1]]
    if CTX.design.routing == "TOP_3D":
        g, idx = _graph_3d(st.lower, st.upper)
        path = _best_path(g, idx, CTX.vertical(c), CTX.horizontal(t))
        if path is None:
            st.fail[gid] = "blocked"
            return []
        _claim_3d(st, path)
        return [(gid, gate, path)]
    g, idx = _plane_graph(st.lower)
    path = _best_path(g, idx, CTX.vertical(c), CTX.horizontal(t))
    if path is None:
        st.fail[gid] = "blocked"
        return []
    st.lower.update(path)
    return [(gid, gate, path)]


def _route_t(gid, gate, st):
    q = CTX.mapping[gate[0]]
    design = CTX.design
    ready = lambda f: CTX.ready_at[f] <= CTX.t and f not in st.consumed  # noqa: E731
    avail = [f for f in CTX.faces if ready(f)]
    if not avail:
        st.fail[gid] = "magic_wait"
        return []

    if design.allow_direct:
        for f in CTX.direct.get(q, ()):
            if ready(f):
                st.consumed.add(f)
                st.face_of[gid] = f
                st.mode[gid] = "direct"
                return [(gid, gate, [])]
    if not design.allow_route:
        st.fail[gid] = "magic_wait"  # this qubit's own sources are recharging
        return []

    n = CTX.n_tiles
    if design.routing == "PLANE":
        g, idx = _plane_graph(st.lower)
        targets = _targets(avail, st.lower)
        path = _best_path(g, idx, CTX.vertical(q), targets)
        if path is not None:
            st.lower.update(path)
            face = targets[path[-1]]
    elif design.routing == "TOP":
        g, idx = _plane_graph(st.upper)
        targets = _targets(avail, st.upper)
        path = _best_path(g, idx, [q] + CTX.vertical(q), targets)
        if path is not None:
            st.upper.update(path)
            face = targets[path[-1]]
            path = [p + n for p in path]
    else:  # TOP_3D
        g, idx = _graph_3d(st.lower, st.upper)
        targets = _targets(avail, st.upper, offset=n)
        path = _best_path(g, idx, CTX.vertical(q) + [q + n], targets)
        if path is not None:
            _claim_3d(st, path)
            face = targets[path[-1]]

    if path is None:
        st.fail[gid] = "blocked"
        return []
    st.consumed.add(face)
    st.face_of[gid] = face
    st.mode[gid] = "routed"
    return [(gid, gate, path)]


def try_order(order, executable):
    """Route the executable gates in the given order; returns a Step with its state."""
    st = StepState(set(CTX.base_lower), set(CTX.base_upper))
    items = list(executable.items())
    step = Step()
    for i in order:
        gid, gate = items[i]
        if len(gate) == 2:
            step.extend(_route_cnot(gid, gate, st))
        else:
            step.extend(_route_t(gid, gate, st))
    step.state = st
    return step


def _vertical_merges(path, is_t, mode):
    if is_t and mode == "direct":
        return 1 if CTX.design.placement == "top" else 0
    n = CTX.n_tiles
    merges = sum(1 for a, b in zip(path, path[1:]) if (a >= n) != (b >= n))
    if is_t and path and path[0] >= n:
        merges += 1  # the seam from the data qubit up to the top layer
    return merges


def commit(step, executable):
    """Apply the chosen step: recharge used sources and record statistics."""
    st = getattr(step, "state", None)
    s = CTX.stats
    s["steps"] += 1
    if not step:
        s["empty_steps"] += 1
    routed = set()
    for gid, gate, path in step:
        routed.add(gid)
        is_t = len(gate) == 1
        mode = st.mode.get(gid) if st is not None else None
        if is_t:
            s["t_gates"] += 1
            s["t_direct" if mode == "direct" else "t_routed"] += 1
            s["t_path_tiles"] += len(path)
            face = st.face_of.get(gid) if st is not None else None
            if face is not None:
                CTX.ready_at[face] = CTX.t + 1 + CTX.recharge
                CTX.used_faces.add(face)
        else:
            s["cx_gates"] += 1
            s["cx_path_tiles"] += len(path)
        s["vertical_merges"] += _vertical_merges(path, is_t, mode)
    for gid, gate in executable.items():
        if gid in routed:
            continue
        reason = st.fail.get(gid, "blocked") if st is not None else "blocked"
        if len(gate) == 1:
            s["stall_magic_wait" if reason == "magic_wait" else "stall_t_blocked"] += 1
        else:
            s["stall_cx_blocked"] += 1
    s["sources_used"] = len(CTX.used_faces)
