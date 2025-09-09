"""
Defines the canonical machining commands.

These are simple, standardized data classes that represent the fundamental
machine movements and actions. The interpreter's sole purpose is to convert
dialect-specific G-code into a list of these commands. This creates a clean
separation between the interpreter logic and the 3D renderer.
"""

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class CanonicalCommand:
    """Base class for all canonical commands."""
    source_line_number: int

@dataclass
class RapidMove(CanonicalCommand):
    """Represents a G0 rapid move."""
    start_pos: Dict[str, float]
    end_pos: Dict[str, float]

@dataclass
class LinearFeed(CanonicalCommand):
    """Represents a G1 linear feed move."""
    start_pos: Dict[str, float]
    end_pos: Dict[str, float]

@dataclass
class ArcFeed(CanonicalCommand):
    """Represents a G2/G3 arc feed move."""
    start_pos: Dict[str, float]
    end_pos: Dict[str, float]
    center: Dict[str, float]
    direction: int  # 1 for CCW (G3), -1 for CW (G2)

@dataclass
class Dwell(CanonicalCommand):
    """Represents a G4 dwell."""
    duration: float

@dataclass
class SetSpindleSpeed(CanonicalCommand):
    """Represents an S-word command."""
    speed: float

@dataclass
class SpindleControl(CanonicalCommand):
    """Represents M3, M4, M5."""
    state: str  # 'CW', 'CCW', 'OFF'

@dataclass
class ToolChange(CanonicalCommand):
    """Represents an M6 tool change."""
    tool_number: int

@dataclass
class CoolantControl(CanonicalCommand):
    """Represents M7, M8, M9."""
    coolant_type: str # 'MIST', 'FLOOD'
    state: bool       # True for ON, False for OFF

@dataclass
class ProgramEnd(CanonicalCommand):
    """Represents M2, M30."""
    pass
