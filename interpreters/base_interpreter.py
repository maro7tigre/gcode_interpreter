"""
The base class for all G-code interpreters. This class provides the core
parsing and execution loop, but the specific handlers for G- and M-codes
are implemented in the dialect-specific subclasses.
"""
from core.machine_state import MachineState
from .parser import GCodeParser

class Block:
    def __init__(self, line_num):
        self.line_number = line_num
        self.words = {}
        # Initialize all possible word flags to False
        for char_code in range(ord('a'), ord('z') + 1):
            letter = chr(char_code)
            setattr(self, f"{letter}_flag", False)
            setattr(self, f"{letter}_number", 0.0)

        # Special case for NUM arguments
        self.er_flag = False; self.er_number = 0.0
        self.eh_flag = False; self.eh_number = 0.0
        self.ef_flag = False; self.ef_number = 0.0

class BaseInterpreter:
    def __init__(self, dialect):
        self.dialect = dialect
        self.machine_state = MachineState()
        self.parser = GCodeParser(self.machine_state)
        self.canon_commands = []
        self.errors = []

    def run_simulation(self, gcode_lines):
        self.machine_state.reset()
        self.canon_commands = []
        self.errors = []
        
        line_num = 0
        for line in gcode_lines:
            line_num += 1
            line = line.strip()
            if not line or line.startswith('%'):
                continue
            
            block = Block(line_num)
            ok, error = self.parser.parse_line(line, block)

            if not ok:
                self.errors.append(error)
                return self.canon_commands, self.errors

            # --- Enhance Block with implicit motion ---
            has_axis_word = any(flag for name, flag in vars(block).items() if name.endswith('_flag') and name[0] in 'xyzabcuvw')
            has_motion_code = False
            for word in block.words:
                if word.startswith('g') and self.dialect.g_code_map.get(int(float(word[1:]) * 10), (None, -1))[1] == 1:
                    has_motion_code = True
                    break
            
            if has_axis_word and not has_motion_code:
                block.words[self.machine_state.motion_mode.lower()] = 0 # Dummy value to trigger motion handler

            self.execute_block(block)
            if self.errors:
                return self.canon_commands, self.errors

        return self.canon_commands, self.errors

    def execute_block(self, block):
        # Strict order of execution based on industrial controller logic
        
        # Stage 1: Set state (non-motion G-codes)
        self._execute_g_codes_by_group(block, [2, 3, 5, 6, 7, 8, 12, 14]) # Plane, Distance, Feed, Units, Comp, Tool Length, CS
        
        # Stage 2: M-Codes and other settings
        self._execute_m_codes_by_group(block, [7, 8, 9]) # Spindle, Coolant, Overrides
        if block.f_flag: self.machine_state.feed_rate = block.f_number
        if block.s_flag: self.machine_state.spindle_speed = block.s_number
        if block.t_flag: self.machine_state.selected_tool = block.t_number

        # Stage 3: Tool Change
        self._execute_m_codes_by_group(block, [6])

        # Stage 4: Motion
        self._execute_g_codes_by_group(block, [1, 0]) # Motion, Non-modal
        
        # Stage 5: Program Stop/End
        self._execute_m_codes_by_group(block, [4])

    def _execute_g_codes_by_group(self, block, groups):
        for g_word, g_val in block.words.items():
            if g_word.startswith('g'):
                if not g_word[1:]: continue # Handle bare 'g'
                try:
                    g_code_int = int(float(g_word[1:]) * 10)
                except ValueError:
                    self.errors.append(f"Invalid G-code format on line {block.line_number}: {g_word}")
                    return

                handler_name, group = self.dialect.g_code_map.get(g_code_int, (None, -1))
                if group in groups and hasattr(self, handler_name):
                    getattr(self, handler_name)(block)

    def _execute_m_codes_by_group(self, block, groups):
        for m_word, m_val in block.words.items():
            if m_word.startswith('m'):
                if not m_word[1:]: continue
                try:
                    m_code_int = int(float(m_word[1:]))
                except ValueError:
                    self.errors.append(f"Invalid M-code format on line {block.line_number}: {m_word}")
                    return

                handler_name, group = self.dialect.m_code_map.get(m_code_int, (None, -1))
                if group in groups and hasattr(self, handler_name):
                    getattr(self, handler_name)(block)
