"""
Defines the specific G-codes and M-codes for the LinuxCNC dialect.

This class acts as a "database" of codes, translating the static arrays
from LinuxCNC's interp_array.cc into a Python dictionary.
"""
from .base_dialect import BaseDialect

class LinuxCNCDialect(BaseDialect):
    def __init__(self):
        super().__init__()
        # Format: {g_code_as_int: ('handler_function_name', modal_group_id)}
        self.g_code_map = {
            # Group 0 (Non-Modal)
            40:  ('_handle_dwell', 0),
            100: ('_handle_g10_set_offsets', 0),
            280: ('_handle_g28_g30_return_home', 0),
            300: ('_handle_g28_g30_return_home', 0),
            530: ('_handle_g53_motion_in_machine_coords', 0),
            920: ('_handle_g92_offset_coords', 0),
            921: ('_handle_g92_offset_coords_clear', 0),
            922: ('_handle_g92_offset_coords_clear', 0),

            # Group 1 (Motion)
            0:   ('_handle_rapid_move', 1),
            10:  ('_handle_linear_feed', 1),
            20:  ('_handle_arc_feed', 1),
            30:  ('_handle_arc_feed', 1),
            382: ('_handle_probe', 1),
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

            # Group 2 (Plane Selection)
            170: ('_handle_set_plane_xy', 2),
            180: ('_handle_set_plane_xz', 2),
            190: ('_handle_set_plane_yz', 2),

            # Group 3 (Distance Mode)
            900: ('_handle_distance_mode', 3),
            910: ('_handle_distance_mode', 3),

            # Group 5 (Feed Rate Mode)
            930: ('_handle_feed_mode', 5),
            940: ('_handle_feed_mode', 5),
            950: ('_handle_feed_mode', 5),

            # Group 6 (Units)
            200: ('_handle_units', 6),
            210: ('_handle_units', 6),

            # Group 7 (Cutter Compensation)
            400: ('_handle_cutter_comp', 7),
            410: ('_handle_cutter_comp', 7),
            420: ('_handle_cutter_comp', 7),

            # Group 8 (Tool Length Offset)
            430: ('_handle_tool_length_offset', 8),
            490: ('_handle_tool_length_offset', 8),

            # Group 10 (Canned Cycle Return Mode)
            980: ('_handle_retract_mode', 10),
            990: ('_handle_retract_mode', 10),
        }

        self.m_code_map = {
            # Group 4 (Stopping)
            0: ('_handle_program_stop', 4),
            1: ('_handle_optional_stop', 4),
            2: ('_handle_program_end', 4),
            30: ('_handle_program_end', 4),

            # Group 6 (Tool Change)
            6: ('_handle_tool_change', 6),

            # Group 7 (Spindle)
            3: ('_handle_spindle_clockwise', 7),
            4: ('_handle_spindle_counterclockwise', 7),
            5: ('_handle_spindle_off', 7),

            # Group 8 (Coolant)
            7: ('_handle_mist_on', 8),
            8: ('_handle_flood_on', 8),
            9: ('_handle_coolant_off', 8),
        }