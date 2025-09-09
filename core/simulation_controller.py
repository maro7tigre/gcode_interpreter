"""
The central coordinator that links the GUI to the core interpreter logic.
"""
from interpreters.linuxcnc_interpreter import LinuxCNCInterpreter
from dialects.linuxcnc_dialect import LinuxCNCDialect

class SimulationController:
    def __init__(self):
        self.interpreter = LinuxCNCInterpreter(LinuxCNCDialect())
        self.canonical_commands = []
        self.errors = []

    def load_gcode_file(self, file_path: str):
        """Loads G-code from a file and returns the lines."""
        try:
            with open(file_path, 'r') as f:
                gcode_lines = f.readlines()
            return gcode_lines, None
        except Exception as e:
            return None, str(e)

    def run_simulation(self, gcode_lines):
        """Runs the interpreter on the provided G-code lines."""
        if not gcode_lines:
            return False, "No G-code to simulate."

        self.canonical_commands, self.errors = self.interpreter.run_simulation(gcode_lines)
        return True, None

