"""
Main G-code interpreter that coordinates all components.
"""
from typing import List, Dict, Any, Optional
from core.lexer import GCodeLexer, Token
from core.parser import GCodeParser, Block
from core.machine_state import MachineState
from core.geometry import GeometryManager
from handlers.g_codes import GCodeHandlers
from handlers.m_codes import MCodeHandlers
from handlers.o_words import OWordProcessor
from utils.errors import ErrorCollector, ErrorType
from utils.expressions import ExpressionEvaluator
from utils.variables import VariableManager


class GCodeInterpreter:
    """Main G-code interpreter that processes G-code text into geometry."""
    
    def __init__(self):
        # Core components
        self.error_collector = ErrorCollector()
        self.machine_state = MachineState()
        self.geometry_manager = GeometryManager()
        
        # Expression and variable system
        self.variable_manager = VariableManager()
        self.expression_evaluator = ExpressionEvaluator(self.error_collector)
        
        # Processing components
        self.lexer = GCodeLexer(self.error_collector)
        self.parser = GCodeParser(self.error_collector)
        self.g_code_handlers = GCodeHandlers(
            self.machine_state, 
            self.geometry_manager, 
            self.error_collector
        )
        self.m_code_handlers = MCodeHandlers(
            self.machine_state,
            self.geometry_manager,
            self.error_collector
        )
        self.o_word_processor = OWordProcessor(
            self.expression_evaluator,
            self.variable_manager,
            self.error_collector
        )
        
        # State tracking
        self.current_gcode_text = ""
        self.tokens: List[Token] = []
        self.blocks: List[Block] = []
        self.execution_line = 0
    
    def process_gcode(self, gcode_text: str) -> bool:
        """
        Process G-code text and generate geometry.
        Returns True if processing succeeded without fatal errors.
        """
        self.current_gcode_text = gcode_text
        self.error_collector.clear()
        self.geometry_manager.clear()
        
        # Reset machine state to defaults
        self.machine_state = MachineState()
        self.variable_manager.clear_user_variables()
        
        # Step 1: Tokenize the input
        self.tokens = self.lexer.tokenize(gcode_text)
        if self.error_collector.has_fatal_errors():
            return False
        
        # Step 2: Parse tokens into blocks
        self.blocks = self.parser.parse(self.tokens)
        if self.error_collector.has_fatal_errors():
            return False
        
        # Step 3: Preprocess O-words and subroutines
        if not self.o_word_processor.preprocess_program(self.blocks):
            return False
        
        # Step 4: Execute blocks
        success = self._execute_blocks()
        
        return success and not self.error_collector.has_fatal_errors()
    
    def _execute_blocks(self) -> bool:
        """Execute all parsed blocks in order with O-word control flow."""
        self.execution_line = 0
        
        while self.execution_line < len(self.blocks):
            block = self.blocks[self.execution_line]
            
            # Check for O-word first (control flow)
            if block.o_word:
                next_line = self.o_word_processor.execute_o_word(self.execution_line)
                if next_line is not None:
                    self.execution_line = next_line
                    continue
            
            # Process variable assignments
            if not self._process_variable_assignments(block):
                if self.error_collector.has_fatal_errors():
                    return False
            
            # Execute normal block
            if not self._execute_block(block):
                if self.error_collector.has_fatal_errors():
                    return False
            
            self.execution_line += 1
        
        return True
    
    def _process_variable_assignments(self, block: Block) -> bool:
        """Process any variable assignments in the block."""
        # TODO: Parse variable assignments from tokens
        # For now, this is a placeholder for future implementation
        return True
    
    def _execute_block(self, block: Block) -> bool:
        """
        Execute a single block following LinuxCNC execution order:
        1. Comments
        2. Feed rate mode (G93, G94, G95)
        3. Feed rate (F)
        4. Spindle speed (S)
        5. Tool selection (T)
        6. M-codes
        7. G-codes
        8. Stopping commands
        """
        # Step 1: Process comments (just logging for now)
        self._process_comments(block)
        
        # Step 2: Feed rate mode
        if 93 in block.g_codes:
            self.machine_state.update_modal_group('feed_rate_mode', 93)
        elif 94 in block.g_codes:
            self.machine_state.update_modal_group('feed_rate_mode', 94)
        elif 95 in block.g_codes:
            self.machine_state.update_modal_group('feed_rate_mode', 95)
        
        # Step 3: Feed rate
        if block.f is not None:
            self.machine_state.feed_rate = block.f
        
        # Step 4: Spindle speed
        if block.s is not None:
            self.machine_state.spindle_speed = block.s
        
        # Step 5: Tool selection
        if block.t is not None:
            self.machine_state.current_tool = block.t
        
        # Step 6: M-codes 
        for m_code in sorted(block.m_codes.keys()):
            if not self.m_code_handlers.execute_m_code(m_code, block):
                return False
        
        # Step 7: G-codes (execute in numerical order for consistency)
        for g_code in sorted(block.g_codes.keys()):
            if not self.g_code_handlers.execute_g_code(g_code, block):
                return False
        
        # Step 8: Stopping commands (TODO: implement when M-codes are added)
        
        return True
    
    def _process_comments(self, block: Block):
        """Process comments in the block."""
        if block.msg_comment:
            # In a real implementation, this would display to operator
            print(f"MSG: {block.msg_comment}")
        
        if block.debug_comment:
            # In a real implementation, this could be logged conditionally
            print(f"DEBUG: {block.debug_comment}")
        
        if block.python_comment:
            # TODO: Implement Python code execution
            print(f"PYTHON: {block.python_comment}")
    
    def _execute_m_code(self, m_code: int, block: Block) -> bool:
        """Execute an M-code (now using proper M-code handlers)."""
        return self.m_code_handlers.execute_m_code(m_code, block)
    
    # Public interface methods for editor integration
    
    def get_errors_for_line(self, line_number: int):
        """Get all errors for a specific line number."""
        return self.error_collector.get_errors_for_line(line_number)
    
    def get_all_errors(self):
        """Get all errors from the last processing."""
        return self.error_collector.get_all_errors()
    
    def get_geometry_for_line(self, line_number: int):
        """Get all geometry segments for a specific line number."""
        return self.geometry_manager.get_segments_for_line(line_number)
    
    def get_all_geometry(self):
        """Get all geometry segments."""
        return self.geometry_manager.get_all_segments()
    
    def get_geometry_by_type(self, move_type):
        """Get geometry segments filtered by type."""
        return self.geometry_manager.get_segments_by_type(move_type)
    
    def get_bounding_box(self):
        """Get the bounding box of all geometry."""
        return self.geometry_manager.get_bounding_box()
    
    def get_statistics(self):
        """Get processing and toolpath statistics."""
        geometry_stats = self.geometry_manager.get_statistics()
        machine_stats = self.machine_state.get_state_summary()
        
        return {
            'processing': {
                'total_lines': len(self.current_gcode_text.split('\n')),
                'total_blocks': len(self.blocks),
                'total_tokens': len(self.tokens),
                'errors': len(self.error_collector.errors),
                'warnings': len([e for e in self.error_collector.errors 
                               if e.severity.value == 'warning'])
            },
            'geometry': geometry_stats,
            'machine_state': machine_stats
        }
    
    def validate_syntax_only(self, gcode_text: str) -> bool:
        """
        Perform only syntax validation without execution.
        Useful for real-time editor feedback.
        """
        temp_error_collector = ErrorCollector()
        temp_lexer = GCodeLexer(temp_error_collector)
        temp_parser = GCodeParser(temp_error_collector)
        
        tokens = temp_lexer.tokenize(gcode_text)
        blocks = temp_parser.parse(tokens)
        
        # Copy errors to main collector for retrieval
        self.error_collector.errors = temp_error_collector.errors.copy()
        
        return not temp_error_collector.has_errors()
    
    def reset(self):
        """Reset interpreter to initial state."""
        self.error_collector.clear()
        self.geometry_manager.clear()
        self.machine_state = MachineState()
        self.variable_manager.clear_user_variables()
        self.current_gcode_text = ""
        self.tokens.clear()
        self.blocks.clear()
        self.execution_line = 0
        
        # Reset O-word processor
        self.o_word_processor.call_stack.clear()
        self.o_word_processor.loop_stack.clear()
        self.o_word_processor.subroutines.clear()