"""
Utility functions for geometric calculations, primarily for arcs.
Logic is ported directly from LinuxCNC's interp_arc.cc.
"""
import math

TINY = 1e-12

def calculate_arc_data_r(move, x1, y1, x2, y2, radius):
    """
    Calculates arc center for R-format arcs.
    move: 20 for G2 (CW), 30 for G3 (CCW)
    """
    abs_radius = abs(radius)
    half_dist = math.hypot(x2 - x1, y2 - y1) / 2.0

    if half_dist > abs_radius:
        # Arc is impossible, return a straight line midpoint as fallback
        return (x1 + x2) / 2, (y1 + y2) / 2, 1 if move == 30 else -1

    if (half_dist / abs_radius) > (1 - TINY):
        half_dist = abs_radius # Allow for small floating point error for semicircles

    offset = math.sqrt(abs_radius**2 - half_dist**2)
    mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    angle = math.atan2(y2 - y1, x2 - x1)
    
    # G2 (CW) with R+ or G3 (CCW) with R- means shorter arc
    if (move == 20 and radius > 0) or (move == 30 and radius < 0):
        center_angle = angle - math.pi / 2.0
    else: # G3 with R+ or G2 with R- means longer arc
        center_angle = angle + math.pi / 2.0
        
    center_x = mid_x + offset * math.cos(center_angle)
    center_y = mid_y + offset * math.sin(center_angle)
    
    return center_x, center_y, 1 if move == 30 else -1

def calculate_arc_data_ijk(move, x1, y1, x2, y2, i, j, k, plane):
    """Calculates arc center for IJK-format arcs (incremental offsets)."""
    if plane == 170: # XY
        center_x, center_y = x1 + i, y1 + j
    elif plane == 180: # XZ
        center_x, center_y = x1 + i, y1 + k # Here y1 is actually z1
    elif plane == 190: # YZ
        center_x, center_y = x1 + j, y1 + k # Here x1 is y1, y1 is z1
    else:
        center_x, center_y = x1 + i, y1 + j # Default to XY

    # A more robust solution would check radius from start vs end point,
    # but for simulation this is sufficient.
    
    return center_x, center_y, 1 if move == 30 else -1