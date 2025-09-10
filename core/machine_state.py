"""
Machine state management for G-code interpreter.
Tracks modal codes, position, coordinate systems, and other machine state.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class PlaneSelection(Enum):
    XY = "G17"
    XZ = "G18" 
    YZ = "G19"
    UV = "G17.1"
    UW = "G18.1"
    VW = "G19.1"


class DistanceMode(Enum):
    ABSOLUTE = "G90"
    INCREMENTAL = "G91"


class ArcDistanceMode(Enum):
    ABSOLUTE = "G90.1"
    INCREMENTAL = "G91.1"


class FeedRateMode(Enum):
    UNITS_PER_MINUTE = "G94"
    INVERSE_TIME = "G93"
    UNITS_PER_REVOLUTION = "G95"


class Units(Enum):
    INCHES = "G20"
    MILLIMETERS = "G21"


@dataclass
class CoordinateSystem:
    """Represents a coordinate system offset (G54-G59.3)."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0
    u: float = 0.0
    v: float = 0.0
    w: float = 0.0
    
    def get_offset(self, axis: str) -> float:
        """Get offset for a specific axis."""
        return getattr(self, axis.lower(), 0.0)
    
    def set_offset(self, axis: str, value: float):
        """Set offset for a specific axis."""
        if hasattr(self, axis.lower()):
            setattr(self, axis.lower(), value)


@dataclass
class Position:
    """Represents a position in 9-axis space."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0
    u: float = 0.0
    v: float = 0.0
    w: float = 0.0
    
    def get_axis(self, axis: str) -> float:
        """Get value for a specific axis."""
        return getattr(self, axis.lower(), 0.0)
    
    def set_axis(self, axis: str, value: float):
        """Set value for a specific axis."""
        if hasattr(self, axis.lower()):
            setattr(self, axis.lower(), value)
    
    def copy(self) -> 'Position':
        """Create a copy of this position."""
        return Position(
            x=self.x, y=self.y, z=self.z,
            a=self.a, b=self.b, c=self.c,
            u=self.u, v=self.v, w=self.w
        )
    
    def to_list(self) -> list:
        """Convert to list [x, y, z] for compatibility."""
        return [self.x, self.y, self.z]


class MachineState:
    """Manages the complete state of the CNC machine."""
    
    def __init__(self):
        # Current position (in machine coordinates)
        self.current_position = Position()
        self.previous_position = Position()
        
        # Modal states with defaults matching LinuxCNC
        self.modal_groups = {
            'motion': 1,           # G1 (linear motion)
            'plane': 17,           # G17 (XY plane)
            'distance': 90,        # G90 (absolute distance)
            'arc_distance': 91.1,  # G91.1 (incremental arc distance)
            'feed_rate_mode': 94,  # G94 (units per minute)
            'units': 21,           # G21 (millimeters)
            'cutter_comp': 40,     # G40 (cutter compensation off)
            'tool_length': 49,     # G49 (tool length compensation off)
            'coordinate_system': 54, # G54 (first coordinate system)
            'path_control': 64,    # G64 (path blending)
            'return_mode': 98,     # G98 (initial level return)
        }
        
        # Coordinate systems (G54-G59.3)
        self.coordinate_systems = {
            54: CoordinateSystem(),    # G54
            55: CoordinateSystem(),    # G55
            56: CoordinateSystem(),    # G56
            57: CoordinateSystem(),    # G57
            58: CoordinateSystem(),    # G58
            59: CoordinateSystem(),    # G59
            59.1: CoordinateSystem(),  # G59.1
            59.2: CoordinateSystem(),  # G59.2
            59.3: CoordinateSystem(),  # G59.3
        }
        
        # G92 offset (applied to all coordinate systems)
        self.g92_offset = CoordinateSystem()
        
        # Machine settings
        self.feed_rate: float = 0.0
        self.spindle_speed: float = 0.0
        self.current_tool: int = 0
        
        # Variables for parameter programming
        self.variables: Dict[str, float] = {}
        self.numbered_parameters: Dict[int, float] = {}
        
    def update_modal_group(self, group: str, code: int):
        """Update a modal group with a new code."""
        if group in self.modal_groups:
            self.modal_groups[group] = code
    
    def get_active_coordinate_system(self) -> CoordinateSystem:
        """Get the currently active coordinate system."""
        cs_code = self.modal_groups.get('coordinate_system', 54)
        return self.coordinate_systems.get(cs_code, self.coordinate_systems[54])
    
    def get_current_plane(self) -> tuple:
        """Get the current working plane as a tuple of axis names."""
        plane_code = self.modal_groups.get('plane', 17)
        plane_map = {
            17: ('X', 'Y'),    # G17 - XY plane
            18: ('X', 'Z'),    # G18 - XZ plane  
            19: ('Y', 'Z'),    # G19 - YZ plane
            17.1: ('U', 'V'),  # G17.1 - UV plane
            18.1: ('U', 'W'),  # G18.1 - UW plane
            19.1: ('V', 'W'),  # G19.1 - VW plane
        }
        return plane_map.get(plane_code, ('X', 'Y'))
    
    def calculate_absolute_position(self, relative_position: Position) -> Position:
        """Calculate absolute machine position from relative coordinates."""
        active_cs = self.get_active_coordinate_system()
        absolute_pos = Position()
        
        for axis in 'xyzabcuvw':
            # Apply coordinate system offset and G92 offset
            cs_offset = active_cs.get_offset(axis)
            g92_offset = self.g92_offset.get_offset(axis)
            relative_value = relative_position.get_axis(axis)
            
            absolute_value = relative_value + cs_offset + g92_offset
            absolute_pos.set_axis(axis, absolute_value)
        
        return absolute_pos
    
    def is_distance_mode_absolute(self) -> bool:
        """Check if distance mode is absolute (G90)."""
        return self.modal_groups.get('distance', 90) == 90
    
    def is_arc_distance_mode_absolute(self) -> bool:
        """Check if arc distance mode is absolute (G90.1)."""
        return self.modal_groups.get('arc_distance', 91.1) == 90.1
    
    def is_feed_rate_mode_units_per_minute(self) -> bool:
        """Check if feed rate mode is units per minute (G94)."""
        return self.modal_groups.get('feed_rate_mode', 94) == 94
    
    def update_position(self, new_position: Position):
        """Update the current position and save previous position."""
        self.previous_position = self.current_position.copy()
        self.current_position = new_position
    
    def set_coordinate_system_offset(self, cs_number: float, axis: str, value: float):
        """Set an offset for a specific coordinate system and axis."""
        if cs_number in self.coordinate_systems:
            self.coordinate_systems[cs_number].set_offset(axis, value)
    
    def set_g92_offset(self, axis: str, value: float):
        """Set G92 offset for a specific axis."""
        self.g92_offset.set_offset(axis, value)
    
    def clear_g92_offset(self):
        """Clear all G92 offsets."""
        self.g92_offset = CoordinateSystem()
    
    def set_variable(self, name: str, value: float):
        """Set a named variable."""
        self.variables[name] = value
    
    def get_variable(self, name: str) -> Optional[float]:
        """Get a named variable value."""
        return self.variables.get(name)
    
    def set_numbered_parameter(self, number: int, value: float):
        """Set a numbered parameter."""
        self.numbered_parameters[number] = value
    
    def get_numbered_parameter(self, number: int) -> Optional[float]:
        """Get a numbered parameter value."""
        return self.numbered_parameters.get(number)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current machine state for debugging."""
        return {
            'position': {
                'current': [self.current_position.x, self.current_position.y, self.current_position.z],
                'previous': [self.previous_position.x, self.previous_position.y, self.previous_position.z]
            },
            'modal_groups': self.modal_groups.copy(),
            'feed_rate': self.feed_rate,
            'spindle_speed': self.spindle_speed,
            'current_tool': self.current_tool,
            'active_coordinate_system': self.modal_groups.get('coordinate_system', 54),
            'plane': self.get_current_plane()
        }