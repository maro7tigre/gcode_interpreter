"""
Defines the G-code and M-code "database" for the NUM 1060 M controller.
This is based on the NUM 1020/1040/1060M Programming Manual, Volume 1.
"""
from .base_dialect import BaseDialect

class NUMDialect(BaseDialect):
    def __init__(self):
        super().__init__()
        self._populate_g_code_map()
        self._populate_m_code_map()

    def _populate_g_code_map(self):
        """Populates the G-code map based on NUM 1060 specification."""
        self.g_code_map = {
            # Motion (Modal Group 1)
            0:   ('_handle_rapid_move', 1),
            10:  ('_handle_linear_feed', 1),
            20:  ('_handle_arc_feed_cw', 1),
            30:  ('_handle_arc_feed_ccw', 1),
            230: ('_handle_arc_three_points', 1),
            60:  ('_handle_spline_execution', 1),

            # Non-Modal (Group 0)
            40:  ('_handle_dwell', 0),
            90:  ('_handle_accurate_stop', 0),
            100: ('_handle_interruptible_block', 0),
            120: ('_handle_overspeed_handwheel', 0),
            770: ('_handle_subroutine_call', 0),
            790: ('_handle_jump', 0),
            
            # Plane Selection (Modal Group 2)
            170: ('_handle_set_plane_xy', 2),
            180: ('_handle_set_plane_zx', 2),
            190: ('_handle_set_plane_yz', 2),

            # Distance Mode (Modal Group 3)
            900: ('_handle_absolute_mode', 3),
            910: ('_handle_incremental_mode', 3),
            
            # Feed Rate Mode (Modal Group 5)
            930: ('_handle_inverse_time_feed', 5),
            940: ('_handle_units_per_minute_feed', 5),
            950: ('_handle_units_per_rev_feed', 5),

            # Units (Modal Group 6)
            700: ('_handle_inch_units', 6),
            710: ('_handle_metric_units', 6),

            # Cutter Compensation (Modal Group 7)
            400: ('_handle_comp_off', 7),
            410: ('_handle_comp_left', 7),
            420: ('_handle_comp_right', 7),
            290: ('_handle_3d_comp', 7),
            430: ('_handle_3d_comp_cylindrical', 7),
            
            # Origin Selection (Modal Group 12)
            520: ('_handle_g52_absolute_coords', 12),
            530: ('_handle_dat_offset_cancel', 12),
            540: ('_handle_dat_offset_enable', 12),
            590: ('_handle_g59_origin_offset', 12),
            920: ('_handle_g92_origin_preset', 12),
            
            # Canned Cycles (Treated as Motion Group 1)
            800: ('_handle_cancel_cycle', 1),
            810: ('_handle_cycle_g81', 1),
            820: ('_handle_cycle_g82', 1),
            830: ('_handle_cycle_g83', 1),
            840: ('_handle_cycle_g84', 1),
            850: ('_handle_cycle_g85', 1),
            860: ('_handle_cycle_g86', 1),
            870: ('_handle_cycle_g87', 1),
            880: ('_handle_cycle_g88', 1),
            890: ('_handle_cycle_g89', 1),
            450: ('_handle_cycle_g45_pocket', 1),
        }

    def _populate_m_code_map(self):
        """Populates the M-code map based on NUM 1060 specification."""
        self.m_code_map = {
            # Program Control (Modal Group 4)
            0: ('_handle_program_stop', 4),
            1: ('_handle_optional_stop', 4),
            2: ('_handle_program_end', 4),
            
            # Spindle Control (Modal Group 7)
            3: ('_handle_spindle_clockwise', 7),
            4: ('_handle_spindle_counterclockwise', 7),
            5: ('_handle_spindle_off', 7),
            19: ('_handle_spindle_index', 7),

            # Tool Change (Modal Group 6)
            6: ('_handle_tool_change', 6),

            # Coolant (Modal Group 8)
            7: ('_handle_coolant_2_on', 8),
            8: ('_handle_coolant_1_on', 8),
            9: ('_handle_coolant_off', 8),
            
            # Overrides (Modal Group 9)
            48: ('_handle_overrides_enable', 9),
            49: ('_handle_overrides_disable', 9),
        }

