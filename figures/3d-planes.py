from manim import *
from manim import WHITE

config.background_color = WHITE

# --- Colors ---
MAGIC = "#f4a425"
DATA = "#488fe0"
ROUTE = "#d6006f"
ANCHILLA = "#e9e7e7"
BOTTOM = "#aeadad"
TOP = "#aeadad"
LINES = BLACK  # color for vertical connectors
ROUTE_LINE_COLOR = BLACK  # color of horizontal lines and dots
SHOW_VERTICAL_DOTS = True  # if True, adds dots at the center of tiles connected with vertical lines
HORIZONTAL_DOTS_AT_ENDPOINTS_ONLY = True  # if True, dots are only at the first and last tile of each horizontal route


# # HBM_A
# GRID_SIZE = 7
#BOTTOM
# BOTTOM_MAGIC = []
# BOTTOM_DATA  = [8,10,12,22,24,26,36,38,40]
# BOTTOM_ROUTE = []
#
# TOP_MAGIC = BOTTOM_DATA
# TOP_DATA  = []
# TOP_ROUTE = []
#
# CONNECTOR_CELLS = BOTTOM_DATA
#
# LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
# LAST_TOP_TILE = None      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)



# # HBM_B shared_2
# GRID_SIZE = 7
#
# BOTTOM_MAGIC = []
# BOTTOM_DATA  = [8,10,12,22,24,26,36,38,40]
#
# TOP_MAGIC = [9,11,23,25,37,39]
# BOTTOM_ROUTE = TOP_MAGIC
# TOP_DATA  = []
# TOP_ROUTE = []
#
# CONNECTOR_CELLS = BOTTOM_ROUTE
#
# LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
# LAST_TOP_TILE = None      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)



# # HBM_C
# GRID_SIZE = 7

# BOTTOM_MAGIC = []
# BOTTOM_DATA  = [8,10,12,22,24,26,36,38,40]

# TOP_MAGIC = [9,11,23,25,37,39]
# BOTTOM_ROUTE = [37,30,31,32,25,18,11]
# TOP_DATA  = []
# TOP_ROUTE = []

# CONNECTOR_CELLS = [11]
#
# LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
# LAST_TOP_TILE = None      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)


# HBM_B
GRID_SIZE = 7

BOTTOM_MAGIC = []
BOTTOM_DATA  = [8,10,12,22,24,26,36,38,40]

TOP_MAGIC = [9,11,23,25,37,39]
BOTTOM_ROUTE = []
TOP_DATA  = []
TOP_ROUTE = [36,29,30,31,32]

CONNECTOR_CELLS = [36]

LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
LAST_TOP_TILE = 25      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)



# # shared_2 mini
# GRID_SIZE = 3
#
# BOTTOM_MAGIC = []
# BOTTOM_DATA  = [0,2,6,8]
#
# TOP_MAGIC = BOTTOM_DATA
# BOTTOM_ROUTE = []
# TOP_DATA  = []
# TOP_ROUTE = []
#
# CONNECTOR_CELLS = []
#
# LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
# LAST_TOP_TILE = None      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)




# # shared_2 mini
# GRID_SIZE = 3
#
# BOTTOM_MAGIC = []
# BOTTOM_DATA  = [0,2,6,8]
#
# TOP_MAGIC = [1,7]
# BOTTOM_ROUTE = []
# TOP_DATA  = []
# TOP_ROUTE = []
#
# CONNECTOR_CELLS = []
#
# LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
# LAST_TOP_TILE = None      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)


# shared_4 mini
# GRID_SIZE = 3
#
# BOTTOM_MAGIC = []
# BOTTOM_DATA  = [0,2,6,8]
#
# TOP_MAGIC = [4]
# BOTTOM_ROUTE = []
# TOP_DATA  = []
# TOP_ROUTE = []
#
# CONNECTOR_CELLS = []
#
# LAST_BOTTOM_TILE = None   # index of tile to connect (with horizontal lines) the last BOTTOM_ROUTE tile to (if any)
# LAST_TOP_TILE = None      # index of tile to connect (with horizontal lines) the last TOP_ROUTE tile to (if any)


class HorizontalPlanes3D(ThreeDScene):

    def construct(self):
        # --- Camera ---
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES, distance=8)

        # --- Planes ---
        plane_size = 6
        plane_bottom = Square(plane_size).shift(OUT * 0)
        plane_top    = Square(plane_size).shift(OUT * 1.5)

        for plane, col in [(plane_bottom, BOTTOM), (plane_top, TOP)]:
            plane.set_fill(col, opacity=0.5)
            plane.set_stroke(col, opacity=0.7, width=1.2)

        # --- Function to create grid ---
        def create_grid(plane, n=GRID_SIZE, margin_ratio=0.1, gap_ratio=0.05):
            grid = VGroup()
            total_margin = 2 * margin_ratio * plane_size
            total_gap = (n - 1) * gap_ratio * plane_size
            usable_size = plane_size - total_margin - total_gap
            small_size = usable_size / n
            start = -plane_size / 2 + margin_ratio * plane_size + small_size / 2

            rects = []
            for i in range(n):
                for j in range(n):
                    x = start + i * (small_size + gap_ratio * plane_size)
                    y = start + j * (small_size + gap_ratio * plane_size)
                    sq = Square(small_size)
                    sq.move_to(plane.get_center() + RIGHT * x + UP * y)
                    sq.set_fill(ANCHILLA, opacity=1)  # default fill
                    sq.set_stroke(BLACK, width=1)
                    rects.append(sq)
                    grid.add(sq)
            return grid, rects

        # --- Create grids ---
        grid_bottom, rects_bottom = create_grid(plane_bottom)
        grid_top, rects_top       = create_grid(plane_top)

        # --- Color Bottom Plane ---
        for idx in range(len(rects_bottom)):
            if idx in BOTTOM_DATA:
                rects_bottom[idx].set_fill(DATA, opacity=1)
            elif idx in BOTTOM_ROUTE:
                rects_bottom[idx].set_fill(ROUTE, opacity=1)
            elif idx in BOTTOM_MAGIC:
                rects_bottom[idx].set_fill(MAGIC, opacity=1)

        # --- Color Top Plane ---
        for idx in range(len(rects_top)):
            if idx in TOP_DATA:
                rects_top[idx].set_fill(DATA, opacity=1)
            elif idx in TOP_ROUTE:
                rects_top[idx].set_fill(ROUTE, opacity=1)
            elif idx in TOP_MAGIC:
                rects_top[idx].set_fill(MAGIC, opacity=1)

        # --- Vertical connectors with MAGIC halo ---
        connectors = VGroup()
        vertical_dots = VGroup()
        for idx in CONNECTOR_CELLS:
            if idx < len(rects_bottom) and idx < len(rects_top):
                # --- MAGIC halo line ---
                halo = Line(
                    rects_bottom[idx].get_center(),
                    rects_top[idx].get_center(),
                    color=MAGIC,
                    stroke_width=10,      # wider for halo effect
                    stroke_opacity=0.5   # semi-transparent
                )
                connectors.add(halo)

                # --- main vertical line ---
                line = Line(
                    rects_bottom[idx].get_center(),
                    rects_top[idx].get_center(),
                    color=LINES,
                    stroke_width=3,
                )
                connectors.add(line)

                # --- Add dots if enabled ---
                if SHOW_VERTICAL_DOTS:
                    dot_bottom = Dot(rects_bottom[idx].get_center(), radius=0.08, color=LINES)
                    dot_top = Dot(rects_top[idx].get_center(), radius=0.08, color=LINES)
                    vertical_dots.add(dot_bottom, dot_top)

        # --- Horizontal connectors for BOTTOM_ROUTE ---
        bottom_horiz_lines = VGroup()
        if len(BOTTOM_ROUTE) > 1:
            for i in range(len(BOTTOM_ROUTE) - 1):
                idx1, idx2 = BOTTOM_ROUTE[i], BOTTOM_ROUTE[i + 1]
                line = Line(
                    rects_bottom[idx1].get_center(),
                    rects_bottom[idx2].get_center(),
                    color=ROUTE_LINE_COLOR,
                    stroke_width=2
                )
                bottom_horiz_lines.add(line)

        # Connect first tile to specified tile if set
        if FIRST_BOTTOM_TILE is not None and len(BOTTOM_ROUTE) > 0:
            first_idx = BOTTOM_ROUTE[0]
            line = Line(
                rects_bottom[first_idx].get_center(),
                rects_bottom[FIRST_BOTTOM_TILE].get_center(),
                color=ROUTE_LINE_COLOR,
                stroke_width=2
            )
            bottom_horiz_lines.add(line)

        # --- Horizontal connectors for TOP_ROUTE ---
        top_horiz_lines = VGroup()
        if len(TOP_ROUTE) > 1:
            for i in range(len(TOP_ROUTE) - 1):
                idx1, idx2 = TOP_ROUTE[i], TOP_ROUTE[i + 1]
                line = Line(
                    rects_top[idx1].get_center(),
                    rects_top[idx2].get_center(),
                    color=ROUTE_LINE_COLOR,
                    stroke_width=2
                )
                top_horiz_lines.add(line)

                # --- Dots at center of route tiles ---
        route_dots = VGroup()

        def add_endpoint_dot(rects, route, endpoint_tile, draw_first=True):
            """Add dot at either the route start, end, or specific endpoint tile."""
            if len(route) == 0:
                return
            if draw_first and endpoint_tile is None:
                # Only add the route’s first tile if there’s no custom endpoint
                dot = Dot(rects[route[0]].get_center(), radius=0.08, color=ROUTE_LINE_COLOR)
                route_dots.add(dot)
            if endpoint_tile is not None:
                # Add only the endpoint tile (skip route[0])
                dot = Dot(rects[endpoint_tile].get_center(), radius=0.08, color=ROUTE_LINE_COLOR)
                route_dots.add(dot)

        if HORIZONTAL_DOTS_AT_ENDPOINTS_ONLY:
            # For bottom: only FIRST_BOTTOM_TILE should get a dot
            add_endpoint_dot(rects_bottom, BOTTOM_ROUTE, FIRST_BOTTOM_TILE, draw_first=False)
            # For top: only LAST_TOP_TILE should get a dot
            add_endpoint_dot(rects_top, TOP_ROUTE, LAST_TOP_TILE, draw_first=False)
        else:
            # If showing all dots
            for idx in BOTTOM_ROUTE:
                dot = Dot(rects_bottom[idx].get_center(), radius=0.08, color=ROUTE_LINE_COLOR)
                route_dots.add(dot)
            if FIRST_BOTTOM_TILE is not None:
                dot = Dot(rects_bottom[FIRST_BOTTOM_TILE].get_center(), radius=0.08, color=ROUTE_LINE_COLOR)
                route_dots.add(dot)

            for idx in TOP_ROUTE:
                dot = Dot(rects_top[idx].get_center(), radius=0.08, color=ROUTE_LINE_COLOR)
                route_dots.add(dot)
            if LAST_TOP_TILE is not None:
                dot = Dot(rects_top[LAST_TOP_TILE].get_center(), radius=0.08, color=ROUTE_LINE_COLOR)
                route_dots.add(dot)


        # --- Add to scene ---
        self.add(plane_bottom, plane_top, grid_bottom, grid_top, connectors)
        self.add(bottom_horiz_lines, top_horiz_lines, route_dots, vertical_dots)

        # Optional camera motion
        self.wait(1.5)
        self.wait(10.5)
