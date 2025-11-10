import math

def hbm_shared_2_positions(arch):
    """Magic states between data-qubits in x dimension (same row)."""
    width = arch["width"]
    ms = set()
    for q in arch["alg_qubits"]:
        row = q // width
        col = q % width
        right = col + 1
        if right < width:
            between = row * width + right
            ms.add(between)
    return sorted(ms)

def hbm_shared_4_positions(arch):
    """
    Magic states that are the center of a 2x2 "square" formed by four data qubits
    located at the four diagonal neighbors of the center:
        up-left, up-right, down-left, down-right.

    For each cell p in the grid, if all four diagonal neighbors exist and are
    algorithm qubits, p is included as a magic-state candidate.
    """
    width = arch["width"]
    height = arch["height"]
    alg = set(arch["alg_qubits"])
    ms = set()

    for p in range(width * height):
        row = p // width
        col = p % width

        # need at least one row above and one row below and one column left and one column right
        if row == 0 or row == height - 1 or col == 0 or col == width - 1:
            continue

        ul = (row - 1) * width + (col - 1)  # up-left
        ur = (row - 1) * width + (col + 1)  # up-right
        dl = (row + 1) * width + (col - 1)  # down-left
        dr = (row + 1) * width + (col + 1)  # down-right

        if ul in alg and ur in alg and dl in alg and dr in alg:
            ms.add(p)

    return sorted(ms)

def insert_row_above(arch):
    new = arch.copy()
    new['height'] = arch['height']+1
    new['alg_qubits'] = [q+new['width'] for q in arch['alg_qubits']]
    new['magic_states'] = [q+new['width'] for q in arch['magic_states']]
    return new

def insert_row_below(arch):
    new = arch.copy()
    new['height'] = arch['height']+1
    return new

def insert_column_left(arch):
    new = arch.copy()
    new['width'] = arch['width']+1
    new['alg_qubits'] = []
    new['magic_states'] = []
    for q in arch['alg_qubits']:
        # need to count first row
        row = q // arch['width']+1
        new['alg_qubits'].append(q+row)
    for m in arch['magic_states']:
        # need to count first row
        row = m // arch['width']+1
        new['magic_states'].append(m+row)
    return new

def insert_column_right(arch):
    new = arch.copy()
    new['width'] = arch['width']+1
    new['alg_qubits'] = []
    new['magic_states'] = []
    for q in arch['alg_qubits']:
        # now don't coount the one in my row
        row = q // arch['width']
        new['alg_qubits'].append(q+row)
    for m in arch['magic_states']:
        # don't coujnt my row
        row = m // arch['width']
        new['magic_states'].append(m+row)
    return new

def center_column(width, height):
    return [(width*i)+(width//2) for i in range(height)]

def right_column(width, height):
    return [(width*i)+(width-1) for i in range(height)]

def all_sides(width, height):

    left_column = [(width*i) for i in range(height)]
    right_column =  [(width*i)+(width-1) for i in range(height)]
    top_row = [i for i in range(width)]
    bottom_row = [(width)*(height-1) + i for i in range(width)]
    all_slots =  list(dict.fromkeys(top_row + right_column + list(reversed(bottom_row))+left_column))
    msf = []
    for i in range(1,len(all_slots),2):
        msf.append(all_slots[i])
    return msf

def square_sparse_layout(alg_qubit_count, magic_states):
    grid_len = 2*math.ceil(math.sqrt(alg_qubit_count))+1
    grid_height = grid_len
    for_circ = []
    for i in range(grid_height*grid_len):
       x,y = reversed(divmod(i, grid_len))
       if x % 2 == y % 2 == 1:
            for_circ.append(i)
    arch = {"height" : grid_height, "width" : grid_len, "alg_qubits" : for_circ, "magic_states" : [] }
    if magic_states == 'all_sides':
        arch = insert_row_below(insert_row_above(insert_column_right(insert_column_left(arch))))
        msf_faces = all_sides(arch['width'], arch['height'])
    elif magic_states == "center_column":
        msf_faces = center_column(grid_len, grid_height)
    elif magic_states == 'right_column':
        arch = insert_column_right(arch)
        msf_faces = right_column(arch['width'], arch['height'])
    elif magic_states == "shared_2":
        msf_faces = hbm_shared_2_positions(arch)
    elif magic_states == "shared_4":
        msf_faces = hbm_shared_4_positions(arch)
    else: msf_faces = magic_states
    arch['magic_states'] = msf_faces
    return arch

def compact_layout(alg_qubit_count, magic_states):
    grid_height = 3
    grid_len = (2*(math.ceil(alg_qubit_count/2))-1)
    for_circ = []
    for i in range(0,grid_len,2):
        for_circ.append(i)
        for_circ.append((grid_len)*2 + i )
    arch = {"height" : grid_height, "width" : grid_len, "alg_qubits" : for_circ, "magic_states" : [] }
    if magic_states == 'all_sides':
        arch = insert_row_below(insert_row_above(insert_column_right(insert_column_left(arch))))
        msf_faces = all_sides(arch['width'], arch['height'])
    elif magic_states == "center_column":
        msf_faces = center_column(grid_len, grid_height)
    elif magic_states == 'right_column':
        arch = insert_column_right(arch)
        msf_faces = right_column(arch['width'], arch['height'])
    elif magic_states == "shared_2":
        msf_faces = hbm_shared_2_positions(arch)
    elif magic_states == "shared_4":
        msf_faces = hbm_shared_4_positions(arch)
    else: msf_faces = magic_states
    arch['magic_states'] = msf_faces
    return arch

def vertical_neighbors(n, grid_len, grid_height, omitted_edges):
    neighbors = []
    down = n + grid_len
    up = n - grid_len
    if n // grid_len != 0 and (n,up) not in omitted_edges and (up, n) not in omitted_edges:
        neighbors.append(up)
    if n // grid_len != grid_height-1 and (n,down) not in omitted_edges and (down,n) not in omitted_edges:
        neighbors.append(down)
    return neighbors

def horizontal_neighbors(n, grid_len, grid_height, omitted_edges):
    neighbors = []
    left = n - 1
    right = n + 1
    if n % grid_len != 0 and (n,left) not in omitted_edges and (left,n) not in omitted_edges:
        neighbors.append(left)
    if n % grid_len != grid_len-1 and (n,right) not in omitted_edges and (right,n) not in omitted_edges:
        neighbors.append(right)
    return neighbors