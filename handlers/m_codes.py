"""
M-code command handlers for the interpreter.
"""
from typing import Optional, Dict, Any, Callable
from core.parser import Block
from core.machine_state import MachineState
from core.geometry import GeometryManager
from utils.errors import ErrorCollector, ErrorType, ErrorSeverity


class MCodeHandlers:
    """Handles execution of M-codes."""
    
    def __init__(self, machine_state: MachineState, 
                 geometry_manager: GeometryManager,
                 error_collector: ErrorCollector):
        self.machine_state = machine_state
        self.geometry_manager = geometry_manager
        self.error_collector = error_collector
        
        # M-code handler mapping
        self.handlers = {
            # Program control
            0: self.handle_m0_program_pause,
            1: self.handle_m1_optional_pause,
            2: self.handle_m2_program_end,
            30: self.handle_m30_program_end_and_rewind,
            60: self.handle_m60_pallet_change_pause,
            
            # Spindle control
            3: self.handle_m3_spindle_clockwise,
            4: self.handle_m4_spindle_counterclockwise,
            5: self.handle_m5_spindle_stop,
            
            # Tool control
            6: self.handle_m6_tool_change,
            61: self.handle_m61_set_current_tool,
            
            # Coolant control
            7: self.handle_m7_mist_coolant_on,
            8: self.handle_m8_flood_coolant_on,
            9: self.handle_m9_coolant_off,
            
            # Override control
            48: self.handle_m48_override_enable,
            49: self.handle_m49_override_disable,
            50: self.handle_m50_feed_override_enable,
            51: self.handle_m51_spindle_override_enable,
            52: self.handle_m52_adaptive_feed_enable,
            53: self.handle_m53_feed_stop_enable,
        }
        
        # Modal group tracking for M-codes
        self.modal_groups = {
            'stopping': [0, 1, 2, 30, 60],
            'spindle': [3, 4, 5],
            'coolant': [7, 8, 9],
            'override': [48, 49, 50, 51, 52, 53],
        }
        
        # Current modal states
        self.current_modals = {
            'spindle': 5,     # M5 - spindle stop
            'coolant': 9,     # M9 - coolant off
            'override': 48,   # M48 - override enable
        }
        
        # Custom M-code handlers (M100-M199)
        self.custom_handlers: Dict[int, Callable] = {}
    
    def execute_m_code(self, m_number: int, block: Block) -> bool:
        """Execute an M-code command."""
        handler = self.handlers.get(m_number)
        if handler:
            try:
                success = handler(block)
                self._update_modal_groups(m_number)
                return success
            except Exception as e:
                self.error_collector.add_error(
                    block.line_number, 0, 0,
                    f"Error executing M{m_number}: {str(e)}",
                    ErrorType.RUNTIME
                )
                return False
        elif 100 <= m_number <= 199:
            # User-defined M-codes
            return self._execute_custom_m_code(m_number, block)
        else:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                f"Unsupported M-code: M{m_number}",
                ErrorType.SEMANTIC
            )
            return False
    
    def _update_modal_groups(self, m_number: int):
        """Update modal group states for non-stopping M-codes."""
        for group, codes in self.modal_groups.items():
            if m_number in codes and group != 'stopping':
                self.current_modals[group] = m_number
    
    def register_custom_m_code(self, m_number: int, handler: Callable):
        """Register a custom M-code handler (M100-M199)."""
        if 100 <= m_number <= 199:
            self.custom_handlers[m_number] = handler
        else:
            raise ValueError("Custom M-codes must be in range M100-M199")
    
    def _execute_custom_m_code(self, m_number: int, block: Block) -> bool:
        """Execute a custom M-code."""
        if m_number in self.custom_handlers:
            try:
                return self.custom_handlers[m_number](block, self.machine_state)
            except Exception as e:
                self.error_collector.add_error(
                    block.line_number, 0, 0,
                    f"Error in custom M{m_number}: {str(e)}",
                    ErrorType.RUNTIME
                )
                return False
        else:
            # Default behavior for undefined custom M-codes
            self.error_collector.add_error(
                block.line_number, 0, 0,
                f"Custom M-code M{m_number} not implemented",
                ErrorType.SEMANTIC,
                ErrorSeverity.WARNING
            )
            return True  # Continue execution with warning
    
    # Program control M-codes
    
    def handle_m0_program_pause(self, block: Block) -> bool:
        """
        M0 - Program pause
        Pauses program execution until operator intervention.
        """
        # In a real implementation, this would pause the machine
        # For simulation, we just log the pause
        print(f"Program paused at line {block.line_number} (M0)")
        return True
    
    def handle_m1_optional_pause(self, block: Block) -> bool:
        """
        M1 - Optional pause
        Pauses program execution if optional stop is enabled.
        """
        # In a real implementation, this would check if optional stop is enabled
        print(f"Optional pause at line {block.line_number} (M1)")
        return True
    
    def handle_m2_program_end(self, block: Block) -> bool:
        """
        M2 - Program end
        Ends the program and resets to initial state.
        """
        # Reset spindle and coolant
        self.current_modals['spindle'] = 5   # Spindle stop
        self.current_modals['coolant'] = 9   # Coolant off
        print(f"Program ended at line {block.line_number} (M2)")
        return True
    
    def handle_m30_program_end_and_rewind(self, block: Block) -> bool:
        """
        M30 - Program end and rewind
        Ends the program, resets state, and rewinds to beginning.
        """
        # Similar to M2 but also rewinds
        self.current_modals['spindle'] = 5   # Spindle stop
        self.current_modals['coolant'] = 9   # Coolant off
        print(f"Program ended and rewound at line {block.line_number} (M30)")
        return True
    
    def handle_m60_pallet_change_pause(self, block: Block) -> bool:
        """
        M60 - Pallet change pause
        Pauses for pallet change operation.
        """
        print(f"Pallet change pause at line {block.line_number} (M60)")
        return True
    
    # Spindle control M-codes
    
    def handle_m3_spindle_clockwise(self, block: Block) -> bool:
        """
        M3 - Spindle clockwise
        Starts spindle rotation in clockwise direction.
        """
        if block.s is not None:
            self.machine_state.spindle_speed = block.s
        
        if self.machine_state.spindle_speed <= 0:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                "Spindle speed must be set before M3",
                ErrorType.SEMANTIC
            )
            return False
        
        print(f"Spindle CW at {self.machine_state.spindle_speed} RPM (M3)")
        return True
    
    def handle_m4_spindle_counterclockwise(self, block: Block) -> bool:
        """
        M4 - Spindle counterclockwise
        Starts spindle rotation in counterclockwise direction.
        """
        if block.s is not None:
            self.machine_state.spindle_speed = block.s
        
        if self.machine_state.spindle_speed <= 0:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                "Spindle speed must be set before M4",
                ErrorType.SEMANTIC
            )
            return False
        
        print(f"Spindle CCW at {self.machine_state.spindle_speed} RPM (M4)")
        return True
    
    def handle_m5_spindle_stop(self, block: Block) -> bool:
        """
        M5 - Spindle stop
        Stops spindle rotation.
        """
        print("Spindle stopped (M5)")
        return True
    
    # Tool control M-codes
    
    def handle_m6_tool_change(self, block: Block) -> bool:
        """
        M6 - Tool change
        Changes to the tool specified by the most recent T word.
        """
        if block.t is not None:
            self.machine_state.current_tool = block.t
        
        print(f"Tool change to T{self.machine_state.current_tool} (M6)")
        return True
    
    def handle_m61_set_current_tool(self, block: Block) -> bool:
        """
        M61 - Set current tool number
        Sets the current tool number without performing a tool change.
        """
        if block.q is not None:
            self.machine_state.current_tool = int(block.q)
            print(f"Current tool set to T{self.machine_state.current_tool} (M61)")
            return True
        else:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                "M61 requires Q parameter for tool number",
                ErrorType.SEMANTIC
            )
            return False
    
    # Coolant control M-codes
    
    def handle_m7_mist_coolant_on(self, block: Block) -> bool:
        """
        M7 - Mist coolant on
        Turns on mist coolant.
        """
        print("Mist coolant on (M7)")
        return True
    
    def handle_m8_flood_coolant_on(self, block: Block) -> bool:
        """
        M8 - Flood coolant on
        Turns on flood coolant.
        """
        print("Flood coolant on (M8)")
        return True
    
    def handle_m9_coolant_off(self, block: Block) -> bool:
        """
        M9 - Coolant off
        Turns off all coolant.
        """
        print("Coolant off (M9)")
        return True
    
    # Override control M-codes
    
    def handle_m48_override_enable(self, block: Block) -> bool:
        """M48 - Enable speed and feed override"""
        print("Override controls enabled (M48)")
        return True
    
    def handle_m49_override_disable(self, block: Block) -> bool:
        """M49 - Disable speed and feed override"""
        print("Override controls disabled (M49)")
        return True
    
    def handle_m50_feed_override_enable(self, block: Block) -> bool:
        """M50 - Feed override enable"""
        if block.p is not None:
            enabled = block.p != 0
            status = "enabled" if enabled else "disabled"
            print(f"Feed override {status} (M50)")
        return True
    
    def handle_m51_spindle_override_enable(self, block: Block) -> bool:
        """M51 - Spindle override enable"""
        if block.p is not None:
            enabled = block.p != 0
            status = "enabled" if enabled else "disabled"
            print(f"Spindle override {status} (M51)")
        return True
    
    def handle_m52_adaptive_feed_enable(self, block: Block) -> bool:
        """M52 - Adaptive feed enable"""
        if block.p is not None:
            enabled = block.p != 0
            status = "enabled" if enabled else "disabled"
            print(f"Adaptive feed {status} (M52)")
        return True
    
    def handle_m53_feed_stop_enable(self, block: Block) -> bool:
        """M53 - Feed stop enable"""
        if block.p is not None:
            enabled = block.p != 0
            status = "enabled" if enabled else "disabled"
            print(f"Feed stop {status} (M53)")
        return True
    
    def get_current_modal_states(self) -> Dict[str, int]:
        """Get current modal states for all M-code groups."""
        return self.current_modals.copy()