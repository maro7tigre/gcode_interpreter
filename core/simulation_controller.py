"""
This class acts as the main controller for the simulation, bridging the GUI
and the interpreter backend.
"""

class SimulationController:
    def __init__(self):
        self.interpreter = None
        self.gcode_lines = []
        self.canonical_commands = []
        self.errors = []

    def load_gcode_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return f.readlines(), None
        except Exception as e:
            return None, str(e)

    def run_simulation(self, gcode_lines):
        if not self.interpreter:
            return False, "No interpreter selected."
        
        self.gcode_lines = gcode_lines
        self.canonical_commands, self.errors = self.interpreter.run_simulation(gcode_lines)
        
        if self.errors:
            return False, self.errors[0] # Return the first error for simplicity
        
        return True, None

