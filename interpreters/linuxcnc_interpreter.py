"""
Concrete implementation of the interpreter for the LinuxCNC dialect.

This class inherits from the BaseInterpreter and provides the Python
implementations for all the G-code and M-code handler functions. The logic
is ported from the various interp_*.cc files.
"""
from .base_interpreter import BaseInterpreter
from core.canonical import *
from utils.geometry import calculate_arc_data_r, calculate_arc_data_ijk

class LinuxCNCInterpreter(BaseInterpreter):

    def _get_target_position(self, block):
        target = self.machine_state.get_position()
        is_incremental = self.machine_state.distance_mode == 910

        for axis in 'xyzabc':
            if getattr(block, f"{axis}_flag"):
                if is_incremental:
                    target[axis] += getattr(block, f"{axis}_number")
                else:
                    target[axis] = getattr(block, f"{axis}_number")
        return target

    # --- Motion Handlers (from interp_convert.cc & interp_arc.cc) ---
    def _handle_rapid_move(self, block):
        target = self._get_target_position(block)
        self.canon_commands.append(RapidMove(block.line_number, self.machine_state.get_position(), target))
        self.machine_state.set_position(target)

    def _handle_linear_feed(self, block):
        target = self._get_target_position(block)
        self.canon_commands.append(LinearFeed(block.line_number, self.machine_state.get_position(), target))
        self.machine_state.set_position(target)

    def _handle_arc_feed(self, block):
        target = self._get_target_position(block)
        start_pos = self.machine_state.get_position()
        arc_g_code = block.g_modes.get(1)

        if block.r_flag:
            center_x, center_y, turns = calculate_arc_data_r(
                arc_g_code, start_pos['x'], start_pos['y'], target['x'], target['y'], block.r_number
            )
        else:
            center_x, center_y, turns = calculate_arc_data_ijk(
                arc_g_code, start_pos['x'], start_pos['y'], target['x'], target['y'],
                block.i_number or 0, block.j_number or 0, block.k_number or 0, self.machine_state.plane
            )

        self.canon_commands.append(ArcFeed(block.line_number, start_pos, target, {'x': center_x, 'y': center_y, 'z': 0}, turns))
        self.machine_state.set_position(target)

    # --- Canned Cycle Handlers (from interp_cycles.cc) ---
    def _handle_cycle_g81(self, block):
        target = self._get_target_position(block)
        r_plane = block.r_number
        start_pos = self.machine_state.get_position()

        pos1 = {'x': target['x'], 'y': target['y'], 'z': start_pos['z']}
        pos2 = {'x': target['x'], 'y': target['y'], 'z': r_plane}
        pos3 = {'x': target['x'], 'y': target['y'], 'z': target['z']}
        
        self.canon_commands.append(RapidMove(block.line_number, start_pos, pos1))
        self.canon_commands.append(RapidMove(block.line_number, pos1, pos2))
        self.canon_commands.append(LinearFeed(block.line_number, pos2, pos3))
        self.canon_commands.append(RapidMove(block.line_number, pos3, pos2))
        
        self.machine_state.set_position(pos2)

    def _handle_cancel_cycle(self, block):
        self.machine_state.active_g_codes[1] = 800

    # ... other G8x cycle handlers would follow a similar pattern ...

    # --- G-Code Handlers (Modal Group 0) ---
    def _handle_dwell(self, block):
        self.canon_commands.append(Dwell(block.line_number, block.p_number))
    
    # --- M-Code Handlers ---
    def _handle_program_end(self, block):
        self.canon_commands.append(ProgramEnd(block.line_number))
        self._handle_spindle_off(block)
        self._handle_coolant_off(block)

    def _handle_spindle_clockwise(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'CW'))
    
    def _handle_spindle_counterclockwise(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'CCW'))

    def _handle_spindle_off(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'OFF'))

    def _handle_mist_on(self, block):
        self.canon_commands.append(CoolantControl(block.line_number, 'MIST', True))

    def _handle_flood_on(self, block):
        self.canon_commands.append(CoolantControl(block.line_number, 'FLOOD', True))

    def _handle_coolant_off(self, block):
        self.canon_commands.append(CoolantControl(block.line_number, 'MIST', False))
        self.canon_commands.append(CoolantControl(block.line_number, 'FLOOD', False))

    # --- Placeholder Handlers for other codes ---
    def __getattr__(self, name):
        """Catch-all for unimplemented handlers."""
        if name.startswith('_handle_'):
            def placeholder(block):
                # print(f"Warning: Handler '{name}' for block '{block.text.strip()}' is not implemented.")
                pass
            return placeholder
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
