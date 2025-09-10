"""
G-code command handlers for the interpreter.
"""
from typing import Optional, Dict, Any
from core.parser import Block
from core.machine_state import MachineState, Position
from core.geometry import GeometryManager, MoveType
from utils.errors import ErrorCollector, ErrorType, ErrorSeverity
import math


class GCodeHandlers:
    """Handles execution of G-codes."""
    
    def __init__(self, machine_state: MachineState, 
                 geometry_manager: GeometryManager,
                 error_collector: ErrorCollector):
        self.machine_state = machine_state
        self.geometry_manager = geometry_manager
        self.error_collector = error_collector
        
        # G-code handler mapping
        self.handlers = {
            0: self.handle_g0_rapid_positioning,
            1: self.handle_g1_linear_interpolation,
            2: self.handle_g2_clockwise_arc,
            3: self.handle_g3_counterclockwise_arc,
            4: self.handle_g4_dwell,
            # TODO: Add more handlers as needed
            10: self.handle_g10_coordinate_system_data,
            17: self.handle_g17_xy_plane,
            18: self.handle_g18_xz_plane,
            19: self.handle_g19_yz_plane,
            20: self.handle_g20_inches,
            21: self.handle_g21_millimeters,
            28: self.handle_g28_return_home,
            90: self.handle_g90_absolute_distance,
            91: self.handle_g91_incremental_distance,
            92: self.handle_g92_coordinate_system_offset,
        }
    
    def execute_g_code(self, g_number: int, block: Block) -> bool:
        """Execute a G-code command."""
        handler = self.handlers.get(g_number)
        if handler:
            try:
                return handler(block)
            except Exception as e:
                self.error_collector.add_error(
                    block.line_number, 0, 0,
                    f"Error executing G{g_number}: {str(e)}",
                    ErrorType.RUNTIME
                )
                return False
        else:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                f"Unsupported G-code: G{g_number}",
                ErrorType.SEMANTIC
            )
            return False
    
    def handle_g0_rapid_positioning(self, block: Block) -> bool:
        """
        G0 - Rapid positioning
        Move to specified coordinates at rapid rate (non-cutting move).
        """
        # Update modal group
        self.machine_state.update_modal_group('motion', 0)
        
        if not block.has_axis_words():
            # No axis words, just update modal state
            return True
        
        # Calculate target position
        target_position = self._calculate_target_position(block)
        if target_position is None:
            return False
        
        # Convert to absolute machine coordinates
        abs_position = self.machine_state.calculate_absolute_position(target_position)
        
        # Add geometry
        start_pos = self.machine_state.current_position.to_list()
        end_pos = abs_position.to_list()
        
        self.geometry_manager.add_linear_move(
            start=start_pos,
            end=end_pos,
            line_number=block.line_number,
            move_type=MoveType.RAPID
        )
        
        # Update machine state
        self.machine_state.update_position(abs_position)
        
        return True
    
    def handle_g1_linear_interpolation(self, block: Block) -> bool:
        """
        G1 - Linear interpolation
        Move to specified coordinates at programmed feed rate (cutting move).
        """
        # Update modal group
        self.machine_state.update_modal_group('motion', 1)
        
        # Check for feed rate if this is first G1 or F word is present
        if block.f is not None:
            if block.f <= 0:
                self.error_collector.add_error(
                    block.line_number, 0, 0,
                    "Feed rate must be positive for G1",
                    ErrorType.SEMANTIC
                )
                return False
            self.machine_state.feed_rate = block.f
        elif self.machine_state.feed_rate <= 0:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                "No feed rate specified for G1 move",
                ErrorType.SEMANTIC
            )
            return False
        
        if not block.has_axis_words():
            # No axis words, just update modal state and feed rate
            return True
        
        # Calculate target position
        target_position = self._calculate_target_position(block)
        if target_position is None:
            return False
        
        # Convert to absolute machine coordinates
        abs_position = self.machine_state.calculate_absolute_position(target_position)
        
        # Add geometry
        start_pos = self.machine_state.current_position.to_list()
        end_pos = abs_position.to_list()
        
        self.geometry_manager.add_linear_move(
            start=start_pos,
            end=end_pos,
            line_number=block.line_number,
            move_type=MoveType.FEED,
            feed_rate=self.machine_state.feed_rate
        )
        
        # Update machine state
        self.machine_state.update_position(abs_position)
        
        return True
    
    def handle_g2_clockwise_arc(self, block: Block) -> bool:
        """
        G2 - Clockwise circular interpolation
        """
        return self._handle_arc_motion(block, 'CW')
    
    def handle_g3_counterclockwise_arc(self, block: Block) -> bool:
        """
        G3 - Counterclockwise circular interpolation  
        """
        return self._handle_arc_motion(block, 'CCW')
    
    def _handle_arc_motion(self, block: Block, direction: str) -> bool:
        """Handle G2/G3 arc motion."""
        g_code = 2 if direction == 'CW' else 3
        self.machine_state.update_modal_group('motion', g_code)
        
        # Check for feed rate
        if block.f is not None:
            if block.f <= 0:
                self.error_collector.add_error(
                    block.line_number, 0, 0,
                    f"Feed rate must be positive for G{g_code}",
                    ErrorType.SEMANTIC
                )
                return False
            self.machine_state.feed_rate = block.f
        elif self.machine_state.feed_rate <= 0:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                f"No feed rate specified for G{g_code} move",
                ErrorType.SEMANTIC
            )
            return False
        
        if not block.has_axis_words():
            return True
        
        # Get current plane
        plane_axes = self.machine_state.get_current_plane()
        plane_name = ''.join(plane_axes)
        
        # Calculate target position
        target_position = self._calculate_target_position(block)
        if target_position is None:
            return False
        
        abs_position = self.machine_state.calculate_absolute_position(target_position)
        
        # Calculate arc center
        center_position = self._calculate_arc_center(block, plane_axes)
        if center_position is None:
            return False
        
        # Add geometry
        start_pos = self.machine_state.current_position.to_list()
        end_pos = abs_position.to_list()
        center_pos = center_position.to_list()
        
        self.geometry_manager.add_arc_move(
            start=start_pos,
            end=end_pos,
            center=center_pos,
            line_number=block.line_number,
            direction=direction,
            plane=plane_name,
            feed_rate=self.machine_state.feed_rate
        )
        
        # Update machine state
        self.machine_state.update_position(abs_position)
        
        return True
    
    def handle_g4_dwell(self, block: Block) -> bool:
        """
        G4 - Dwell (pause)
        P - seconds to pause
        """
        if block.p is None or block.p < 0:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                "G4 requires positive P value (seconds)",
                ErrorType.SEMANTIC
            )
            return False
        
        # Dwell doesn't generate geometry, just a pause
        # In a real implementation, this would pause the machine
        return True
    
    def handle_g10_coordinate_system_data(self, block: Block) -> bool:
        """
        G10 - Coordinate system data tool and work offset tables
        """
        # TODO: Implement G10 variants (L2, L20, etc.)
        self.error_collector.add_error(
            block.line_number, 0, 0,
            "G10 not yet implemented",
            ErrorType.SEMANTIC
        )
        return False
    
    def handle_g17_xy_plane(self, block: Block) -> bool:
        """G17 - XY plane selection"""
        self.machine_state.update_modal_group('plane', 17)
        return True
    
    def handle_g18_xz_plane(self, block: Block) -> bool:
        """G18 - XZ plane selection"""
        self.machine_state.update_modal_group('plane', 18)
        return True
    
    def handle_g19_yz_plane(self, block: Block) -> bool:
        """G19 - YZ plane selection"""
        self.machine_state.update_modal_group('plane', 19)
        return True
    
    def handle_g20_inches(self, block: Block) -> bool:
        """G20 - Programming in inches"""
        self.machine_state.update_modal_group('units', 20)
        return True
    
    def handle_g21_millimeters(self, block: Block) -> bool:
        """G21 - Programming in millimeters"""
        self.machine_state.update_modal_group('units', 21)
        return True
    
    def handle_g28_return_home(self, block: Block) -> bool:
        """G28 - Return to home position"""
        # TODO: Implement proper G28 with intermediate point
        home_position = Position()  # All zeros
        abs_position = self.machine_state.calculate_absolute_position(home_position)
        
        start_pos = self.machine_state.current_position.to_list()
        end_pos = abs_position.to_list()
        
        self.geometry_manager.add_linear_move(
            start=start_pos,
            end=end_pos,
            line_number=block.line_number,
            move_type=MoveType.RAPID
        )
        
        self.machine_state.update_position(abs_position)
        return True
    
    def handle_g90_absolute_distance(self, block: Block) -> bool:
        """G90 - Absolute distance mode"""
        self.machine_state.update_modal_group('distance', 90)
        return True
    
    def handle_g91_incremental_distance(self, block: Block) -> bool:
        """G91 - Incremental distance mode"""
        self.machine_state.update_modal_group('distance', 91)
        return True
    
    def handle_g92_coordinate_system_offset(self, block: Block) -> bool:
        """
        G92 - Coordinate system offset
        Sets the current position to the specified coordinates without moving.
        """
        if not block.has_axis_words():
            self.error_collector.add_error(
                block.line_number, 0, 0,
                "G92 requires at least one axis word",
                ErrorType.SEMANTIC
            )
            return False
        
        # Set G92 offsets to make current position equal the specified values
        for axis in 'xyzabcuvw':
            specified_value = getattr(block, axis)
            if specified_value is not None:
                current_value = self.machine_state.current_position.get_axis(axis)
                offset = current_value - specified_value
                self.machine_state.set_g92_offset(axis, offset)
        
        return True
    
    def _calculate_target_position(self, block: Block) -> Optional[Position]:
        """Calculate target position from block, considering distance mode."""
        target = Position()
        
        if self.machine_state.is_distance_mode_absolute():
            # Absolute mode - use specified coordinates or current position
            for axis in 'xyzabcuvw':
                specified_value = getattr(block, axis)
                if specified_value is not None:
                    target.set_axis(axis, specified_value)
                else:
                    # Keep current coordinate for unspecified axes
                    current_abs = self.machine_state.current_position.get_axis(axis)
                    # Convert back to relative coordinate
                    active_cs = self.machine_state.get_active_coordinate_system()
                    cs_offset = active_cs.get_offset(axis)
                    g92_offset = self.machine_state.g92_offset.get_offset(axis)
                    relative_value = current_abs - cs_offset - g92_offset
                    target.set_axis(axis, relative_value)
        else:
            # Incremental mode - add to current position
            for axis in 'xyzabcuvw':
                specified_value = getattr(block, axis)
                if specified_value is not None:
                    # Get current relative position
                    current_abs = self.machine_state.current_position.get_axis(axis)
                    active_cs = self.machine_state.get_active_coordinate_system()
                    cs_offset = active_cs.get_offset(axis)
                    g92_offset = self.machine_state.g92_offset.get_offset(axis)
                    current_relative = current_abs - cs_offset - g92_offset
                    
                    target.set_axis(axis, current_relative + specified_value)
                else:
                    # Keep current relative coordinate
                    current_abs = self.machine_state.current_position.get_axis(axis)
                    active_cs = self.machine_state.get_active_coordinate_system()
                    cs_offset = active_cs.get_offset(axis)
                    g92_offset = self.machine_state.g92_offset.get_offset(axis)
                    relative_value = current_abs - cs_offset - g92_offset
                    target.set_axis(axis, relative_value)
        
        return target
    
    def _calculate_arc_center(self, block: Block, plane_axes: tuple) -> Optional[Position]:
        """Calculate arc center position from I, J, K values."""
        center = self.machine_state.current_position.copy()
        
        # Map I, J, K to the current plane
        axis1, axis2 = plane_axes
        
        # Determine which offset parameters to use based on plane
        if plane_axes == ('X', 'Y'):
            i_offset = block.i or 0.0
            j_offset = block.j or 0.0
        elif plane_axes == ('X', 'Z'):
            i_offset = block.i or 0.0
            j_offset = block.k or 0.0  # K for Z in XZ plane
        elif plane_axes == ('Y', 'Z'):
            i_offset = block.j or 0.0
            j_offset = block.k or 0.0
        else:
            # Handle other planes (UV, UW, VW) if needed
            i_offset = block.i or 0.0
            j_offset = block.j or 0.0
        
        # Apply offsets in arc distance mode
        if self.machine_state.is_arc_distance_mode_absolute():
            # Absolute arc center
            center.set_axis(axis1.lower(), i_offset)
            center.set_axis(axis2.lower(), j_offset)
        else:
            # Incremental arc center (relative to start point)
            current_axis1 = self.machine_state.current_position.get_axis(axis1.lower())
            current_axis2 = self.machine_state.current_position.get_axis(axis2.lower())
            center.set_axis(axis1.lower(), current_axis1 + i_offset)
            center.set_axis(axis2.lower(), current_axis2 + j_offset)
        
        return center