"""
The core G-code interpreter engine.

This class is designed to be dialect-agnostic. It parses a line into a
structured 'Block' and then uses the dialect's maps to dispatch to the
correct handler function for each word.
"""
import re
from core.machine_state import MachineState

class Block:
    """A Python representation of the 'block' struct."""
    def __init__(self, line_num, text):
        self.line_number = line_num
        self.text = text
        self.g_modes = {}
        self.m_modes = {}
        self.params = {}
        self.comment = ""

    def __getattr__(self, name):
        # Dynamically create flag and number attributes
        if name.endswith('_flag'):
            key = name[:-5]
            return key in self.params
        if name.endswith('_number'):
            key = name[:-7]
            return self.params.get(key)
        raise AttributeError(f"'Block' object has no attribute '{name}'")


class BaseInterpreter:
    def __init__(self, dialect):
        self.dialect = dialect
        self.machine_state = MachineState()
        self.canon_commands = []
        self.errors = []

    def parse_line(self, text, line_num):
        """Replicates the logic of interp_read.cc."""
        block = Block(line_num, text)

        # Strip comments first
        text = re.sub(r'\(.*?\)', '', text)
        text = text.split(';')[0]
        text = text.strip().lower()

        pattern = re.compile(r'([a-zA-Z])([-+]?\d*\.?\d+)')

        for match in pattern.finditer(text):
            letter = match.group(1)
            value = float(match.group(2))
            block.params[letter] = value

            if letter == 'g':
                g_code_int = int(round(value * 10))
                _, group = self.dialect.g_code_map.get(g_code_int, (None, -1))
                if group != -1:
                    block.g_modes[group] = g_code_int
            elif letter == 'm':
                m_code_int = int(round(value))
                _, group = self.dialect.m_code_map.get(m_code_int, (None, -1))
                if group != -1:
                    block.m_modes[group] = m_code_int
        return block

    def enhance_block(self, block):
        """Replicates logic from enhance_block in interp_internal.cc."""
        has_axis_word = any(c in block.params for c in 'xyzabc')
        if has_axis_word and 1 not in block.g_modes:
             # If axes are present but no motion G-code, apply the last motion mode.
            block.g_modes[1] = self.machine_state.active_g_codes.get(1, 0)
        return True, None # Simplified error checking for now

    def run_simulation(self, gcode_lines):
        """Main simulation loop."""
        self.machine_state.reset()
        self.canon_commands = []
        self.errors = []

        for i, line in enumerate(gcode_lines):
            block = self.parse_line(line, i + 1)
            ok, err = self.enhance_block(block)
            if not ok:
                self.errors.append(f"Line {i+1}: {err}")
                continue
            
            ok, err = self.execute_block(block)
            if not ok:
                self.errors.append(f"Line {i+1}: {err}")

        return self.canon_commands, self.errors

    def execute_block(self, block):
        """
        Executes a parsed block in the correct order of operations,
        replicating the logic from interp_execute.cc.
        """
        # This order is critical
        execution_order = [
            (5, self.dialect.g_code_map),  # Feed Mode
            ('s', None),                  # Spindle Speed
            ('t', None),                  # Tool Select
            (8, self.dialect.m_code_map),  # Coolant
            (7, self.dialect.m_code_map),  # Spindle Control
            (6, self.dialect.m_code_map),  # Tool Change
            (2, self.dialect.g_code_map),  # Plane
            (6, self.dialect.g_code_map),  # Units
            (7, self.dialect.g_code_map),  # Cutter Comp
            (8, self.dialect.g_code_map),  # Tool Length Offset
            (12, self.dialect.g_code_map), # Coordinate System
            (3, self.dialect.g_code_map),  # Distance Mode
            (10, self.dialect.g_code_map), # Retract Mode
            (0, self.dialect.g_code_map),  # Non-Modal G-Codes
            (1, self.dialect.g_code_map),  # Motion
            (4, self.dialect.m_code_map),  # Stopping
        ]

        for key, code_map in execution_order:
            if isinstance(key, int): # Modal group
                if key in block.g_modes and code_map is self.dialect.g_code_map:
                    code = block.g_modes[key]
                    handler_name, _ = code_map[code]
                    getattr(self, handler_name)(block)
                elif key in block.m_modes and code_map is self.dialect.m_code_map:
                    code = block.m_modes[key]
                    handler_name, _ = code_map[code]
                    getattr(self, handler_name)(block)
            else: # Single word like 's' or 't'
                if f"{key}_flag" in block.params:
                     # Simplified handler dispatch for single words
                    if key == 's': self._handle_spindle_speed(block)
                    if key == 't': self._handle_tool_select(block)
        
        return True, None
