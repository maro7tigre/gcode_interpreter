"""
Holds the complete state of the virtual machine, including modal states,
offsets, parameters, and the tool table. This is a comprehensive model
designed to support advanced G-code features.
"""
import copy

class MachineState:
    def __init__(self):
        self.reset()

    def reset(self):
        """Resets the machine to a default state."""
        # --- Positional Data ---
        self.current_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.program_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0} # For cutter comp

        # --- Modal States ---
        self.distance_mode = 'absolute'  # G90
        self.plane = 'xy'                # G17
        self.feed_mode = 'units_per_minute' # G94
        self.active_cycle = None         # G80
        self.cutter_comp = None          # G40 ('left', 'right', or None)
        self.motion_mode = 'G0'

        # --- Tooling and Spindle ---
        self.tool_table = {i: {'length': 0.0, 'diameter': 0.0} for i in range(256)}
        self.current_tool = 0
        self.selected_tool = 0
        self.tool_length_offset = 0.0
        self.spindle_speed = 0.0
        self.spindle_on = False
        self.spindle_dir = 'cw'

        # --- Offsets and Parameters ---
        self.coordinate_systems = {i: {'x': 0, 'y': 0, 'z': 0} for i in range(1, 10)} # G54-G59.3
        self.active_cs = 1
        self.g92_offset = {'x': 0, 'y': 0, 'z': 0}
        self.parameters = {i: 0.0 for i in range(5400)}
        self.named_parameters = {}

        # --- Subroutine Call Stack ---
        self.call_stack = []

    def get_position(self):
        return copy.copy(self.current_pos)

    def set_position(self, new_pos):
        self.current_pos = copy.copy(new_pos)

    def get_offset(self):
        """Calculates the total active offset."""
        cs_offset = self.coordinate_systems[self.active_cs]
        return {
            'x': cs_offset['x'] + self.g92_offset['x'],
            'y': cs_offset['y'] + self.g92_offset['y'],
            'z': cs_offset['z'] + self.g92_offset['z'] + self.tool_length_offset
        }

    def get_parameter(self, index):
        if isinstance(index, str):
            return self.named_parameters.get(index.lower(), 0.0)
        else:
            return self.parameters.get(index, 0.0)

    def set_parameter(self, index, value):
        if isinstance(index, str):
            self.named_parameters[index.lower()] = value
        else:
            self.parameters[index] = value

