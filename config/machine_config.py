"""
Machine configuration for G-code interpreter.
Simple, clean configuration system for different machine types.
"""
from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import json


@dataclass
class MachineConfig:
    """Configuration for a CNC machine."""
    name: str
    machine_type: str  # "mill", "lathe", "plasma"
    
    # Axes configuration
    axes: List[str]  # Available axes like ["X", "Y", "Z", "A", "B"]
    
    # Supported codes
    g_codes: Set[int]
    m_codes: Set[int]
    
    # Machine limits
    max_feed: float = 10000.0
    max_spindle: float = 24000.0
    max_rapid: float = 15000.0
    
    # Features
    has_tool_changer: bool = True
    has_coolant: bool = True
    has_spindle: bool = True


class ConfigManager:
    """Manages machine configurations with simple presets."""
    
    @staticmethod
    def mill_3axis() -> MachineConfig:
        """Standard 3-axis milling machine."""
        return MachineConfig(
            name="3-Axis Mill",
            machine_type="mill",
            axes=["X", "Y", "Z"],
            g_codes={
                # Motion
                0, 1, 2, 3,
                # Plane selection
                17, 18, 19,
                # Units and modes
                20, 21, 90, 91, 94,
                # Coordinate systems
                54, 55, 56, 57, 58, 59,
                # Tool functions
                43, 49,
                # Canned cycles
                80, 81, 82, 83, 84, 85
            },
            m_codes={
                # Program control
                0, 1, 2, 30,
                # Spindle
                3, 4, 5,
                # Tool change
                6,
                # Coolant
                7, 8, 9,
                # Custom range
                *range(100, 200)
            }
        )
    
    @staticmethod
    def mill_5axis() -> MachineConfig:
        """5-axis milling machine with rotary axes."""
        config = ConfigManager.mill_3axis()
        config.name = "5-Axis Mill"
        config.axes = ["X", "Y", "Z", "A", "B"]
        config.max_feed = 8000.0  # Slower for 5-axis
        return config
    
    @staticmethod
    def lathe() -> MachineConfig:
        """2-axis lathe configuration."""
        return MachineConfig(
            name="Lathe",
            machine_type="lathe",
            axes=["X", "Z"],
            g_codes={
                # Motion
                0, 1, 2, 3,
                # Modes
                20, 21, 90, 91, 95,  # G95 = feed per rev
                # Coordinate systems
                54, 55, 56, 57, 58, 59,
                # Spindle modes
                96, 97
            },
            m_codes={
                # Program control
                0, 1, 2, 30,
                # Spindle
                3, 4, 5,
                # Tool change
                6,
                # Coolant
                8, 9,  # No mist on lathe
                # Custom range
                *range(100, 200)
            },
            max_feed=3000.0,
            max_spindle=4000.0,
            max_rapid=6000.0
        )
    
    @staticmethod
    def plasma() -> MachineConfig:
        """Plasma cutting table."""
        return MachineConfig(
            name="Plasma Table",
            machine_type="plasma",
            axes=["X", "Y", "Z"],
            g_codes={
                # Motion only
                0, 1, 2, 3,
                # Modes
                20, 21, 90, 91, 94,
                # Coordinate systems
                54, 55, 56
            },
            m_codes={
                # Program control
                0, 1, 2, 30,
                # Torch control (using M3/M5 for torch on/off)
                3, 5,
                # Custom range
                *range(100, 200)
            },
            max_feed=6000.0,
            max_spindle=0.0,  # No spindle
            max_rapid=12000.0,
            has_tool_changer=False,
            has_coolant=False,
            has_spindle=False
        )
    
    @staticmethod
    def get_config(machine_type: str) -> MachineConfig:
        """Get configuration by type name."""
        configs = {
            "mill": ConfigManager.mill_3axis(),
            "mill_3axis": ConfigManager.mill_3axis(),
            "mill_5axis": ConfigManager.mill_5axis(),
            "lathe": ConfigManager.lathe(),
            "plasma": ConfigManager.plasma()
        }
        return configs.get(machine_type.lower(), ConfigManager.mill_3axis())
    
    @staticmethod
    def save_config(config: MachineConfig, filepath: str):
        """Save configuration to JSON file."""
        data = {
            "name": config.name,
            "machine_type": config.machine_type,
            "axes": config.axes,
            "g_codes": list(config.g_codes),
            "m_codes": list(config.m_codes),
            "max_feed": config.max_feed,
            "max_spindle": config.max_spindle,
            "max_rapid": config.max_rapid,
            "has_tool_changer": config.has_tool_changer,
            "has_coolant": config.has_coolant,
            "has_spindle": config.has_spindle
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def load_config(filepath: str) -> MachineConfig:
        """Load configuration from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Convert lists back to sets
            data["g_codes"] = set(data["g_codes"])
            data["m_codes"] = set(data["m_codes"])
            
            return MachineConfig(**data)
            
        except Exception:
            # Return default on error
            return ConfigManager.mill_3axis()
    
    @staticmethod
    def validate_gcode(config: MachineConfig, g_code: int) -> bool:
        """Check if G-code is supported by machine."""
        return g_code in config.g_codes
    
    @staticmethod
    def validate_mcode(config: MachineConfig, m_code: int) -> bool:
        """Check if M-code is supported by machine."""
        return m_code in config.m_codes
    
    @staticmethod
    def validate_axis(config: MachineConfig, axis: str) -> bool:
        """Check if axis is available on machine."""
        return axis.upper() in config.axes