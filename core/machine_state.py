"""
Represents the state of the virtual machine tool.

This class is a direct Python analog to the 'setup' struct found in
LinuxCNC's interp_internal.hh. It holds all modal information, current
positions, feed/speed rates, and other state variables required by the
interpreter.
"""
from typing import Dict

class MachineState:
    def __init__(self):
        self.reset()

    def reset(self):
        """Resets the machine state to default values."""
        self.position: Dict[str, float] = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'a': 0.0, 'b': 0.0, 'c': 0.0}
        self.feed_rate: float = 100.0
        self.spindle_speed: float = 0.0
        self.spindle_on: bool = False
        self.spindle_dir: int = 1 # 1 for CW (M3), -1 for CCW (M4)

        # Modal G-Codes, mapped by group ID
        self.active_g_codes: Dict[int, int] = {
            1: 800, # Motion (G80 - Cancel Motion Mode)
            2: 170, # Plane (G17 - XY Plane)
            3: 900, # Distance Mode (G90 - Absolute)
            5: 940, # Feed Mode (G94 - Units per Minute)
            # ... and other defaults
        }

        # Modal M-Codes
        self.active_m_codes: Dict[int, int] = {}

        self.plane: int = 170  # G17
        self.distance_mode: int = 900  # G90

    def get_position(self) -> Dict[str, float]:
        """Returns a copy of the current position."""
        return self.position.copy()

    def set_position(self, new_pos: Dict[str, float]):
        """Updates the current position."""
        self.position.update(new_pos)