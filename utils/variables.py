"""
Variable and parameter management for G-code interpreter.
Handles numbered parameters, named parameters, and system variables.
"""
import re
from typing import Dict, Optional, Any, Set
from utils.errors import ErrorCollector, ErrorType


class VariableManager:
    """Manages variables and parameters for the G-code interpreter."""
    
    def __init__(self):
        # User-defined numbered parameters (#1-#5399)
        self.numbered_parameters: Dict[int, float] = {}
        
        # Named parameters (#<name> and #<_global>)
        self.local_parameters: Dict[str, float] = {}
        self.global_parameters: Dict[str, float] = {}
        
        # System parameters (#5400+) - read-only, updated by machine state
        self.system_parameters: Dict[int, float] = {}
        
        # Predefined named parameters (read-only)
        self.predefined_named: Dict[str, float] = {}
        
        # Initialize system and predefined parameters
        self._initialize_system_parameters()
        self._initialize_predefined_named()
    
    def _initialize_system_parameters(self):
        """Initialize system parameters with default values."""
        # Current position parameters
        self.system_parameters.update({
            5420: 0.0,  # Current X coordinate
            5421: 0.0,  # Current Y coordinate
            5422: 0.0,  # Current Z coordinate
            5423: 0.0,  # Current A coordinate
            5424: 0.0,  # Current B coordinate
            5425: 0.0,  # Current C coordinate
            5426: 0.0,  # Current U coordinate
            5427: 0.0,  # Current V coordinate
            5428: 0.0,  # Current W coordinate
        })
        
        # Tool and modal information
        self.system_parameters.update({
            5400: 0,    # Current tool number
            5401: 0,    # Tool X offset
            5402: 0,    # Tool Y offset
            5403: 0,    # Tool Z offset
            5404: 0,    # Tool A offset
            5405: 0,    # Tool B offset
            5406: 0,    # Tool C offset
            5407: 0,    # Tool U offset
            5408: 0,    # Tool V offset
            5409: 0,    # Tool W offset
            5410: 0,    # Current feed rate
            5411: 0,    # Current spindle speed
        })
        
        # Modal group values
        self.system_parameters.update({
            5070: 1,    # Motion modal group (G0, G1, etc.)
            5080: 17,   # Plane selection (G17, G18, G19)
            5090: 90,   # Distance mode (G90, G91)
            5100: 94,   # Feed rate mode (G93, G94, G95)
            5110: 21,   # Units (G20, G21)
            5120: 40,   # Cutter compensation (G40, G41, G42)
            5130: 49,   # Tool length compensation (G43, G49)
            5140: 54,   # Coordinate system (G54-G59.3)
            5150: 64,   # Path control mode (G61, G64)
            5160: 98,   # Return mode (G98, G99)
        })
        
        # Coordinate system offsets (G54-G59.3)
        for i in range(1, 10):  # G54=1, G55=2, ..., G59.3=9
            base = 5200 + (i-1)*20
            for axis_offset in range(9):  # X,Y,Z,A,B,C,U,V,W
                self.system_parameters[base + axis_offset] = 0.0
    
    def _initialize_predefined_named(self):
        """Initialize predefined named parameters."""
        # Current position (read-only)
        self.predefined_named.update({
            '_x': 0.0, '_y': 0.0, '_z': 0.0,
            '_a': 0.0, '_b': 0.0, '_c': 0.0,
            '_u': 0.0, '_v': 0.0, '_w': 0.0,
        })
        
        # Current modal states (read-only)
        self.predefined_named.update({
            '_motion': 1,      # Current motion modal
            '_plane': 17,      # Current plane
            '_distance': 90,   # Current distance mode
            '_feed': 0,        # Current feed rate
            '_speed': 0,       # Current spindle speed
            '_tool': 0,        # Current tool number
        })
    
    def set_numbered_parameter(self, number: int, value: float) -> bool:
        """Set a numbered parameter."""
        if 1 <= number <= 5399:
            # User parameters
            self.numbered_parameters[number] = value
            return True
        else:
            # System parameters are read-only
            return False
    
    def get_numbered_parameter(self, number: int) -> float:
        """Get a numbered parameter value."""
        if number in self.system_parameters:
            return self.system_parameters[number]
        return self.numbered_parameters.get(number, 0.0)
    
    def set_named_parameter(self, name: str, value: float) -> bool:
        """Set a named parameter."""
        if name.startswith('_') and not name.startswith('__'):
            # Global parameter
            if name in self.predefined_named:
                # Predefined parameters are read-only
                return False
            self.global_parameters[name] = value
            return True
        else:
            # Local parameter
            self.local_parameters[name] = value
            return True
    
    def get_named_parameter(self, name: str) -> float:
        """Get a named parameter value."""
        if name in self.predefined_named:
            return self.predefined_named[name]
        elif name.startswith('_'):
            return self.global_parameters.get(name, 0.0)
        else:
            return self.local_parameters.get(name, 0.0)
    
    def update_system_parameter(self, number: int, value: float):
        """Update a system parameter (internal use only)."""
        if number in self.system_parameters:
            self.system_parameters[number] = value
            
            # Update corresponding predefined named parameters
            self._sync_predefined_named()
    
    def update_predefined_named(self, name: str, value: float):
        """Update a predefined named parameter (internal use only)."""
        if name in self.predefined_named:
            self.predefined_named[name] = value
    
    def _sync_predefined_named(self):
        """Sync predefined named parameters with system parameters."""
        # Position parameters
        if 5420 in self.system_parameters:
            self.predefined_named['_x'] = self.system_parameters[5420]
        if 5421 in self.system_parameters:
            self.predefined_named['_y'] = self.system_parameters[5421]
        if 5422 in self.system_parameters:
            self.predefined_named['_z'] = self.system_parameters[5422]
        
        # Modal and settings
        if 5400 in self.system_parameters:
            self.predefined_named['_tool'] = self.system_parameters[5400]
        if 5410 in self.system_parameters:
            self.predefined_named['_feed'] = self.system_parameters[5410]
        if 5411 in self.system_parameters:
            self.predefined_named['_speed'] = self.system_parameters[5411]
        if 5070 in self.system_parameters:
            self.predefined_named['_motion'] = self.system_parameters[5070]
        if 5080 in self.system_parameters:
            self.predefined_named['_plane'] = self.system_parameters[5080]
        if 5090 in self.system_parameters:
            self.predefined_named['_distance'] = self.system_parameters[5090]
    
    def get_all_variables(self) -> Dict[str, float]:
        """Get all variables in a format suitable for expression evaluation."""
        variables = {}
        
        # Add numbered parameters
        for num, value in self.numbered_parameters.items():
            variables[f"#{num}"] = value
        
        # Add system parameters
        for num, value in self.system_parameters.items():
            variables[f"#{num}"] = value
        
        # Add named parameters
        for name, value in self.local_parameters.items():
            variables[f"#{name}"] = value
        
        for name, value in self.global_parameters.items():
            variables[f"#{name}"] = value
        
        for name, value in self.predefined_named.items():
            variables[f"#{name}"] = value
        
        return variables
    
    def clear_local_variables(self):
        """Clear local variables (called when entering/exiting subroutines)."""
        self.local_parameters.clear()
    
    def clear_user_variables(self):
        """Clear all user-defined variables."""
        self.numbered_parameters.clear()
        self.local_parameters.clear()
        self.global_parameters.clear()
    
    def get_variable_info(self, variable_ref: str) -> Dict[str, Any]:
        """Get information about a variable reference."""
        info = {
            'valid': False,
            'type': None,
            'value': 0.0,
            'read_only': False,
            'scope': None
        }
        
        if variable_ref.startswith('#<') and variable_ref.endswith('>'):
            # Named parameter
            name = variable_ref[2:-1]
            info['type'] = 'named'
            info['value'] = self.get_named_parameter(name)
            info['valid'] = True
            
            if name in self.predefined_named:
                info['read_only'] = True
                info['scope'] = 'predefined'
            elif name.startswith('_'):
                info['scope'] = 'global'
            else:
                info['scope'] = 'local'
                
        elif variable_ref.startswith('#'):
            # Numbered parameter
            try:
                number = int(variable_ref[1:])
                info['type'] = 'numbered'
                info['value'] = self.get_numbered_parameter(number)
                info['valid'] = True
                
                if number >= 5400:
                    info['read_only'] = True
                    info['scope'] = 'system'
                else:
                    info['scope'] = 'user'
                    
            except ValueError:
                pass
        
        return info
    
    def process_assignment(self, variable_ref: str, value: float, 
                          error_collector: ErrorCollector, line_number: int) -> bool:
        """
        Process a variable assignment.
        
        Args:
            variable_ref: Variable reference (e.g., "#100" or "#<length>")
            value: Value to assign
            error_collector: Error collector for reporting issues
            line_number: Line number for error reporting
            
        Returns:
            True if assignment succeeded
        """
        var_info = self.get_variable_info(variable_ref)
        
        if not var_info['valid']:
            error_collector.add_error(
                line_number, 0, 0,
                f"Invalid variable reference: {variable_ref}",
                ErrorType.SYNTAX
            )
            return False
        
        if var_info['read_only']:
            error_collector.add_error(
                line_number, 0, 0,
                f"Cannot assign to read-only variable: {variable_ref}",
                ErrorType.SEMANTIC
            )
            return False
        
        try:
            if var_info['type'] == 'named':
                name = variable_ref[2:-1]
                return self.set_named_parameter(name, value)
            elif var_info['type'] == 'numbered':
                number = int(variable_ref[1:])
                return self.set_numbered_parameter(number, value)
            
        except Exception as e:
            error_collector.add_error(
                line_number, 0, 0,
                f"Error in variable assignment: {str(e)}",
                ErrorType.RUNTIME
            )
            return False
        
        return False
    
    def get_variable_list(self) -> Dict[str, Dict[str, Any]]:
        """Get a list of all variables organized by type."""
        return {
            'numbered_user': {
                f"#{num}": {'value': val, 'read_only': False}
                for num, val in self.numbered_parameters.items()
            },
            'numbered_system': {
                f"#{num}": {'value': val, 'read_only': True}
                for num, val in self.system_parameters.items()
            },
            'named_local': {
                f"#<{name}>": {'value': val, 'read_only': False}
                for name, val in self.local_parameters.items()
            },
            'named_global': {
                f"#<{name}>": {'value': val, 'read_only': False}
                for name, val in self.global_parameters.items()
            },
            'named_predefined': {
                f"#<{name}>": {'value': val, 'read_only': True}
                for name, val in self.predefined_named.items()
            }
        }