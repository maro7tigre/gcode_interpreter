"""
G-code interpreter for the NUM 1060 M controller standard.
This implements the specific handlers for G- and M-codes defined in the NUM dialect.
The logic is derived from the NUM 1020/1040/1060M Programming Manual.
"""
from .base_interpreter import BaseInterpreter
from core.canonical import *
from utils.geometry import calculate_arc_data_r, calculate_arc_data_ijk
import math

class NUMInterpreter(BaseInterpreter):

    def _get_target_position(self, block):
        """
        Calculates the target position based on the current distance mode.
        NUM controllers handle axes independently based on whether they are flagged.
        """
        pos = self.machine_state.get_position()
        
        # Start with the current position
        target_pos = pos.copy()

        if self.machine_state.distance_mode == 'absolute':
            if block.x_flag: target_pos['x'] = block.x_number
            if block.y_flag: target_pos['y'] = block.y_number
            if block.z_flag: target_pos['z'] = block.z_number
        else: # Incremental
            if block.x_flag: target_pos['x'] += block.x_number
            if block.y_flag: target_pos['y'] += block.y_number
            if block.z_flag: target_pos['z'] += block.z_number
        
        return target_pos

    # --- Motion Handlers (Chapter 4 of Manual) ---
    def _handle_rapid_move(self, block):
        target = self._get_target_position(block)
        command = RapidMove(
            source_line_number=block.line_number,
            start_pos=self.machine_state.get_position(),
            end_pos=target
        )
        self.canon_commands.append(command)
        self.machine_state.set_position(target)

    def _handle_linear_feed(self, block):
        target = self._get_target_position(block)
        command = LinearFeed(
            source_line_number=block.line_number,
            start_pos=self.machine_state.get_position(),
            end_pos=target
        )
        self.canon_commands.append(command)
        self.machine_state.set_position(target)

    def _handle_arc_feed(self, block, direction):
        target = self._get_target_position(block)
        start_pos = self.machine_state.get_position()
        
        if not block.x_flag and not block.y_flag:
            self.errors.append(f"Error on line {block.line_number}: G02/G03 requires an end point (X, Y).")
            return

        if block.r_flag:
            if block.r_number <= math.hypot(target['x'] - start_pos['x'], target['y'] - start_pos['y']) / 2:
                self.errors.append(f"Error on line {block.line_number}: Arc Radius (R) too small.")
                return
            center_x, center_y, turns = calculate_arc_data_r(
                direction, start_pos['x'], start_pos['y'],
                target['x'], target['y'], block.r_number
            )
        elif block.i_flag or block.j_flag:
            i = block.i_number if block.i_flag else 0.0
            j = block.j_number if block.j_flag else 0.0
            
            # NUM manual implies I,J are always incremental from the start point
            center_x, center_y, turns = calculate_arc_data_ijk(
                direction, start_pos['x'], start_pos['y'],
                target['x'], target['y'], i, j
            )
        else:
            self.errors.append(f"Error on line {block.line_number}: G02/G03 requires either R or I/J words.")
            return

        command = ArcFeed(
            source_line_number=block.line_number,
            start_pos=start_pos, end_pos=target,
            center={'x': center_x, 'y': center_y}, direction=direction
        )
        self.canon_commands.append(command)
        self.machine_state.set_position(target)

    def _handle_arc_feed_cw(self, block):
        self._handle_arc_feed(block, -1)

    def _handle_arc_feed_ccw(self, block):
        self._handle_arc_feed(block, 1)

    # --- Canned Cycles (Section 4.9) ---
    def _handle_cycle_g81(self, block):
        """Centre drilling cycle."""
        target = self._get_target_position(block)
        start_pos = self.machine_state.get_position()
        
        retract_z = block.er_number if block.er_flag else start_pos['z']
        
        rapid_to_xy = RapidMove(block.line_number, start_pos, {'x': target['x'], 'y': target['y'], 'z': start_pos['z']})
        self.canon_commands.append(rapid_to_xy)
        
        rapid_to_r = RapidMove(block.line_number, rapid_to_xy.end_pos, {'x': target['x'], 'y': target['y'], 'z': retract_z})
        self.canon_commands.append(rapid_to_r)

        feed_to_z = LinearFeed(block.line_number, rapid_to_r.end_pos, target)
        self.canon_commands.append(feed_to_z)

        rapid_up = RapidMove(block.line_number, target, rapid_to_r.end_pos)
        self.canon_commands.append(rapid_up)
        
        self.machine_state.set_position(rapid_up.end_pos)
        
    def _handle_cycle_g82(self, block):
        """Counterboring cycle with dwell."""
        if not block.ef_flag:
            self.errors.append(f"Error on line {block.line_number}: G82 requires an EF word for dwell time.")
            return
            
        self._handle_cycle_g81(block) # Base movement is the same
        self.canon_commands.insert(-1, Dwell(block.line_number, block.ef_number))

    def _handle_cancel_cycle(self, block):
        self.machine_state.active_cycle = None
        
    # --- Dummy handlers for unimplemented codes ---
    def __getattr__(self, name):
        if name.startswith('_handle_'):
            def dummy_handler(block):
                gcode_name = name.replace('_handle_', '').replace('_', ' ').upper()
                print(f"Warning: Handler for {gcode_name} on line {block.line_number} is not implemented.")
            return dummy_handler
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # --- Cutter Compensation Handlers ---
    def _handle_comp_off(self, block):
        self.machine_state.cutter_comp = None

    def _handle_comp_left(self, block):
        self.machine_state.cutter_comp = 'left'

    def _handle_comp_right(self, block):
        self.machine_state.cutter_comp = 'right'

    # --- System State Handlers ---
    def _handle_absolute_mode(self, block):
        self.machine_state.distance_mode = 'absolute'
    
    def _handle_incremental_mode(self, block):
        self.machine_state.distance_mode = 'incremental'

    def _handle_set_plane_xy(self, block):
        self.machine_state.plane = 'xy'

    def _handle_set_plane_zx(self, block):
        self.machine_state.plane = 'zx'
        
    def _handle_set_plane_yz(self, block):
        self.machine_state.plane = 'yz'
        
    def _handle_units_per_minute_feed(self, block):
        self.machine_state.feed_mode = 'units_per_minute'
    
    def _handle_inverse_time_feed(self, block):
        self.machine_state.feed_mode = 'inverse_time'

    def _handle_units_per_rev_feed(self, block):
        self.machine_state.feed_mode = 'units_per_rev'

    def _handle_spindle_clockwise(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'cw', self.machine_state.spindle_speed))

    def _handle_spindle_counterclockwise(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'ccw', self.machine_state.spindle_speed))

    def _handle_spindle_off(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'off'))
        
    def _handle_coolant_1_on(self, block):
        self.canon_commands.append(CoolantControl(block.line_number, 'coolant1_on'))

    def _handle_coolant_2_on(self, block):
        self.canon_commands.append(CoolantControl(block.line_number, 'coolant2_on'))

    def _handle_coolant_off(self, block):
        self.canon_commands.append(CoolantControl(block.line_number, 'off'))

    def _handle_tool_change(self, block):
        if self.machine_state.tool_number is None:
             self.errors.append(f"Error on line {block.line_number}: M06 requires a tool to be selected with T word first.")
             return
        self.canon_commands.append(ToolChange(block.line_number, self.machine_state.tool_number))

    def _handle_program_end(self, block):
        self.canon_commands.append(ProgramEnd(block.line_number))
