from .base_interpreter import BaseInterpreter
from core.canonical import *
from utils.geometry import calculate_arc_data_r, calculate_arc_data_ijk

class LinuxCNCInterpreter(BaseInterpreter):
    # This class inherits all the advanced parsing and execution logic
    # from the new BaseInterpreter. We only need to add LinuxCNC-specific
    # handlers here.

    def _get_target_position(self, block):
        # Apply offsets to get absolute position in machine coordinates
        offset = self.machine_state.get_offset()
        current_abs = {axis: self.machine_state.current_pos[axis] + offset[axis] for axis in 'xyz'}
        
        target = self.machine_state.get_position()
        
        if self.machine_state.distance_mode == 'absolute':
            if block.x_flag: target['x'] = block.x_number - offset['x']
            if block.y_flag: target['y'] = block.y_number - offset['y']
            if block.z_flag: target['z'] = block.z_number - offset['z']
        else: # Incremental
            if block.x_flag: target['x'] += block.x_number
            if block.y_flag: target['y'] += block.y_number
            if block.z_flag: target['z'] += block.z_number
        return target
        
    def _handle_rapid_move(self, block):
        target = self._get_target_position(block)
        command = RapidMove(block.line_number, self.machine_state.get_position(), target)
        self.canon_commands.append(command)
        self.machine_state.set_position(target)

    def _handle_linear_feed(self, block):
        target = self._get_target_position(block)
        command = LinearFeed(block.line_number, self.machine_state.get_position(), target)
        self.canon_commands.append(command)
        self.machine_state.set_position(target)
        
    def _handle_arc_feed(self, block, direction):
        target = self._get_target_position(block)
        start_pos = self.machine_state.get_position()
        
        if block.r_flag:
             center_x, center_y, _ = calculate_arc_data_r(direction, start_pos['x'], start_pos['y'], target['x'], target['y'], block.r_number)
        else:
             center_x, center_y, _ = calculate_arc_data_ijk(direction, start_pos['x'], start_pos['y'], target['x'], target['y'], block.i_number, block.j_number)

        command = ArcFeed(block.line_number, start_pos, target, {'x': center_x, 'y': center_y}, direction)
        self.canon_commands.append(command)
        self.machine_state.set_position(target)

    def _handle_arc_feed_cw(self, block): self._handle_arc_feed(block, -1)
    def _handle_arc_feed_ccw(self, block): self._handle_arc_feed(block, 1)

    def _handle_absolute_mode(self, block): self.machine_state.distance_mode = 'absolute'
    def _handle_incremental_mode(self, block): self.machine_state.distance_mode = 'incremental'

    def _handle_spindle_clockwise(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'cw', self.machine_state.spindle_speed))

    def _handle_spindle_off(self, block):
        self.canon_commands.append(SpindleControl(block.line_number, 'off'))
        
    def _handle_tool_change(self, block):
        self.canon_commands.append(ToolChange(block.line_number, self.machine_state.selected_tool))

    def _handle_program_end(self, block):
        self.canon_commands.append(ProgramEnd(block.line_number))
        
    def __getattr__(self, name):
        if name.startswith('_handle_'):
            def dummy_handler(block):
                print(f"Warning: Handler for {name} on line {block.line_number} is not implemented.")
            return dummy_handler
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

