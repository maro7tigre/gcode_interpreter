"""
O-word (control structure) handlers for the interpreter.
Implements subroutines, conditionals, and loops.
"""
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from core.parser import Block
from utils.errors import ErrorCollector, ErrorType
from utils.expressions import ExpressionEvaluator
from utils.variables import VariableManager


class OWordType(Enum):
    SUBROUTINE = "sub"
    CONDITIONAL = "if"
    LOOP_WHILE = "while"
    LOOP_REPEAT = "repeat"
    CALL = "call"
    RETURN = "return"
    BREAK = "break"
    CONTINUE = "continue"


@dataclass
class OWordCommand:
    """Represents an O-word command."""
    type: OWordType
    label: Union[str, int]
    expression: Optional[str] = None
    arguments: List[float] = None
    line_number: int = 0
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []


@dataclass
class SubroutineDefinition:
    """Represents a subroutine definition."""
    name: Union[str, int]
    start_line: int
    end_line: int
    parameter_count: int = 0
    local_variables: Dict[str, float] = None
    
    def __post_init__(self):
        if self.local_variables is None:
            self.local_variables = {}


@dataclass
class CallStackFrame:
    """Represents a frame in the call stack."""
    subroutine_name: Union[str, int]
    return_line: int
    local_variables: Dict[str, float]
    arguments: List[float]


@dataclass
class LoopContext:
    """Represents a loop context for break/continue."""
    type: OWordType  # LOOP_WHILE or LOOP_REPEAT
    label: Union[str, int]
    start_line: int
    end_line: int
    condition: Optional[str] = None
    repeat_count: Optional[int] = None
    current_iteration: int = 0


class OWordProcessor:
    """Processes O-word control structures."""
    
    def __init__(self, expression_evaluator: ExpressionEvaluator,
                 variable_manager: VariableManager,
                 error_collector: ErrorCollector):
        self.expression_evaluator = expression_evaluator
        self.variable_manager = variable_manager
        self.error_collector = error_collector
        
        # Subroutine definitions
        self.subroutines: Dict[Union[str, int], SubroutineDefinition] = {}
        
        # Execution control
        self.call_stack: List[CallStackFrame] = []
        self.loop_stack: List[LoopContext] = []
        
        # Control flow state
        self.current_line = 0
        self.next_line = 0
        self.should_skip_to_line = None
        self.return_value = None
        
        # Program structure (built during preprocessing)
        self.blocks: List[Block] = []
        self.o_word_map: Dict[int, OWordCommand] = {}  # line -> O-word command
    
    def preprocess_program(self, blocks: List[Block]) -> bool:
        """
        Preprocess the program to find subroutines and validate structure.
        Must be called before execution.
        """
        self.blocks = blocks
        self.o_word_map.clear()
        self.subroutines.clear()
        
        # Parse O-words and build structure
        for i, block in enumerate(blocks):
            if block.o_word:
                o_cmd = self._parse_o_word(block)
                if o_cmd:
                    self.o_word_map[i] = o_cmd
        
        # Find and validate subroutine definitions
        return self._validate_program_structure()
    
    def _parse_o_word(self, block: Block) -> Optional[OWordCommand]:
        """Parse an O-word from a block."""
        if not block.o_word:
            return None
        
        parts = block.o_word.strip().split()
        if len(parts) < 2:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                f"Invalid O-word format: {block.o_word}",
                ErrorType.SYNTAX
            )
            return None
        
        # Extract label and command
        label_part = parts[0]
        command_part = parts[1].lower()
        
        # Parse label (can be number or name)
        if label_part.startswith('O') or label_part.startswith('o'):
            label_str = label_part[1:]
        else:
            label_str = label_part
        
        # Try to parse as number, otherwise use as string
        try:
            label = int(label_str)
        except ValueError:
            label = label_str
        
        # Parse command type
        command_map = {
            'sub': OWordType.SUBROUTINE,
            'endsub': OWordType.SUBROUTINE,
            'if': OWordType.CONDITIONAL,
            'else': OWordType.CONDITIONAL,
            'elseif': OWordType.CONDITIONAL,
            'endif': OWordType.CONDITIONAL,
            'while': OWordType.LOOP_WHILE,
            'endwhile': OWordType.LOOP_WHILE,
            'repeat': OWordType.LOOP_REPEAT,
            'endrepeat': OWordType.LOOP_REPEAT,
            'call': OWordType.CALL,
            'return': OWordType.RETURN,
            'break': OWordType.BREAK,
            'continue': OWordType.CONTINUE,
        }
        
        if command_part not in command_map:
            self.error_collector.add_error(
                block.line_number, 0, 0,
                f"Unknown O-word command: {command_part}",
                ErrorType.SYNTAX
            )
            return None
        
        # Extract expression and arguments
        expression = None
        arguments = []
        
        if len(parts) > 2:
            if command_part in ['if', 'elseif', 'while']:
                # Expression in brackets
                expr_part = ' '.join(parts[2:])
                if expr_part.startswith('[') and expr_part.endswith(']'):
                    expression = expr_part[1:-1]
                else:
                    self.error_collector.add_error(
                        block.line_number, 0, 0,
                        f"Expression must be in brackets for {command_part}",
                        ErrorType.SYNTAX
                    )
                    return None
            elif command_part == 'call':
                # Arguments for subroutine call
                for arg_str in parts[2:]:
                    if arg_str.startswith('[') and arg_str.endswith(']'):
                        arg_expr = arg_str[1:-1]
                        # Evaluate argument expression
                        variables = self.variable_manager.get_all_variables()
                        arg_value = self.expression_evaluator.evaluate(
                            arg_expr, variables, block.line_number
                        )
                        if arg_value is not None:
                            arguments.append(arg_value)
                    else:
                        # Try to parse as direct number
                        try:
                            arguments.append(float(arg_str))
                        except ValueError:
                            self.error_collector.add_error(
                                block.line_number, 0, 0,
                                f"Invalid argument: {arg_str}",
                                ErrorType.SYNTAX
                            )
                            return None
            elif command_part == 'return':
                # Return value expression
                if len(parts) > 2:
                    expr_part = ' '.join(parts[2:])
                    if expr_part.startswith('[') and expr_part.endswith(']'):
                        expression = expr_part[1:-1]
        
        return OWordCommand(
            type=command_map[command_part],
            label=label,
            expression=expression,
            arguments=arguments,
            line_number=block.line_number
        )
    
    def _validate_program_structure(self) -> bool:
        """Validate the overall program structure."""
        stack = []
        subroutine_starts = {}
        
        for line_num, o_cmd in self.o_word_map.items():
            if o_cmd.type == OWordType.SUBROUTINE:
                if self._get_command_text(o_cmd).endswith('sub'):
                    # Start of subroutine
                    stack.append(('sub', o_cmd.label, line_num))
                    subroutine_starts[o_cmd.label] = line_num
                elif self._get_command_text(o_cmd).endswith('endsub'):
                    # End of subroutine
                    if not stack or stack[-1][0] != 'sub' or stack[-1][1] != o_cmd.label:
                        self.error_collector.add_error(
                            o_cmd.line_number, 0, 0,
                            f"Mismatched endsub for O{o_cmd.label}",
                            ErrorType.SYNTAX
                        )
                        return False
                    
                    start_info = stack.pop()
                    start_line = start_info[2]
                    
                    # Create subroutine definition
                    self.subroutines[o_cmd.label] = SubroutineDefinition(
                        name=o_cmd.label,
                        start_line=start_line,
                        end_line=line_num
                    )
            
            elif o_cmd.type == OWordType.CONDITIONAL:
                cmd_text = self._get_command_text(o_cmd)
                if cmd_text == 'if':
                    stack.append(('if', o_cmd.label, line_num))
                elif cmd_text == 'endif':
                    if not stack or stack[-1][0] != 'if' or stack[-1][1] != o_cmd.label:
                        self.error_collector.add_error(
                            o_cmd.line_number, 0, 0,
                            f"Mismatched endif for O{o_cmd.label}",
                            ErrorType.SYNTAX
                        )
                        return False
                    stack.pop()
            
            elif o_cmd.type == OWordType.LOOP_WHILE:
                cmd_text = self._get_command_text(o_cmd)
                if cmd_text == 'while':
                    stack.append(('while', o_cmd.label, line_num))
                elif cmd_text == 'endwhile':
                    if not stack or stack[-1][0] != 'while' or stack[-1][1] != o_cmd.label:
                        self.error_collector.add_error(
                            o_cmd.line_number, 0, 0,
                            f"Mismatched endwhile for O{o_cmd.label}",
                            ErrorType.SYNTAX
                        )
                        return False
                    stack.pop()
            
            elif o_cmd.type == OWordType.LOOP_REPEAT:
                cmd_text = self._get_command_text(o_cmd)
                if cmd_text == 'repeat':
                    stack.append(('repeat', o_cmd.label, line_num))
                elif cmd_text == 'endrepeat':
                    if not stack or stack[-1][0] != 'repeat' or stack[-1][1] != o_cmd.label:
                        self.error_collector.add_error(
                            o_cmd.line_number, 0, 0,
                            f"Mismatched endrepeat for O{o_cmd.label}",
                            ErrorType.SYNTAX
                        )
                        return False
                    stack.pop()
        
        # Check for unclosed structures
        if stack:
            structure_type, label, line_num = stack[-1]
            self.error_collector.add_error(
                line_num, 0, 0,
                f"Unclosed {structure_type} structure O{label}",
                ErrorType.SYNTAX
            )
            return False
        
        return True
    
    def _get_command_text(self, o_cmd: OWordCommand) -> str:
        """Get the command text from the original block."""
        if o_cmd.line_number < len(self.blocks):
            parts = self.blocks[o_cmd.line_number].o_word.strip().split()
            if len(parts) >= 2:
                return parts[1].lower()
        return ""
    
    def execute_o_word(self, line_number: int) -> Optional[int]:
        """
        Execute an O-word command.
        
        Returns:
            Next line number to execute, or None to continue normally
        """
        if line_number not in self.o_word_map:
            return None
        
        o_cmd = self.o_word_map[line_number]
        self.current_line = line_number
        
        try:
            if o_cmd.type == OWordType.CALL:
                return self._execute_call(o_cmd)
            elif o_cmd.type == OWordType.RETURN:
                return self._execute_return(o_cmd)
            elif o_cmd.type == OWordType.CONDITIONAL:
                return self._execute_conditional(o_cmd)
            elif o_cmd.type == OWordType.LOOP_WHILE:
                return self._execute_while_loop(o_cmd)
            elif o_cmd.type == OWordType.LOOP_REPEAT:
                return self._execute_repeat_loop(o_cmd)
            elif o_cmd.type == OWordType.BREAK:
                return self._execute_break(o_cmd)
            elif o_cmd.type == OWordType.CONTINUE:
                return self._execute_continue(o_cmd)
            
        except Exception as e:
            self.error_collector.add_error(
                o_cmd.line_number, 0, 0,
                f"Error executing O-word: {str(e)}",
                ErrorType.RUNTIME
            )
        
        return None
    
    def _execute_call(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute a subroutine call."""
        if o_cmd.label not in self.subroutines:
            self.error_collector.add_error(
                o_cmd.line_number, 0, 0,
                f"Undefined subroutine: O{o_cmd.label}",
                ErrorType.RUNTIME
            )
            return None
        
        subroutine = self.subroutines[o_cmd.label]
        
        # Create call stack frame
        frame = CallStackFrame(
            subroutine_name=o_cmd.label,
            return_line=self.current_line + 1,
            local_variables={},
            arguments=o_cmd.arguments.copy()
        )
        
        # Set up local parameters (#1, #2, etc.)
        for i, arg in enumerate(o_cmd.arguments, 1):
            self.variable_manager.set_numbered_parameter(i, arg)
        
        self.call_stack.append(frame)
        
        # Jump to subroutine start
        return subroutine.start_line + 1
    
    def _execute_return(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute a return from subroutine."""
        if not self.call_stack:
            self.error_collector.add_error(
                o_cmd.line_number, 0, 0,
                "Return outside of subroutine",
                ErrorType.RUNTIME
            )
            return None
        
        # Evaluate return value if provided
        if o_cmd.expression:
            variables = self.variable_manager.get_all_variables()
            self.return_value = self.expression_evaluator.evaluate(
                o_cmd.expression, variables, o_cmd.line_number
            )
        else:
            self.return_value = None
        
        # Pop call stack and return
        frame = self.call_stack.pop()
        return frame.return_line
    
    def _execute_conditional(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute conditional statements."""
        cmd_text = self._get_command_text(o_cmd)
        
        if cmd_text in ['if', 'elseif']:
            if o_cmd.expression:
                variables = self.variable_manager.get_all_variables()
                condition_value = self.expression_evaluator.evaluate(
                    o_cmd.expression, variables, o_cmd.line_number
                )
                
                if condition_value is None:
                    return None
                
                # If condition is false, skip to else/elseif/endif
                if not condition_value:
                    return self._find_matching_else_or_endif(o_cmd.label, self.current_line)
        
        # For else, endif, and true conditions, continue normally
        return None
    
    def _execute_while_loop(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute while loop."""
        cmd_text = self._get_command_text(o_cmd)
        
        if cmd_text == 'while':
            if o_cmd.expression:
                variables = self.variable_manager.get_all_variables()
                condition_value = self.expression_evaluator.evaluate(
                    o_cmd.expression, variables, o_cmd.line_number
                )
                
                if condition_value is None:
                    return None
                
                # If condition is false, skip to endwhile
                if not condition_value:
                    return self._find_matching_endwhile(o_cmd.label, self.current_line)
                
                # Push loop context for break/continue
                loop_context = LoopContext(
                    type=OWordType.LOOP_WHILE,
                    label=o_cmd.label,
                    start_line=self.current_line,
                    end_line=self._find_matching_endwhile(o_cmd.label, self.current_line) - 1,
                    condition=o_cmd.expression
                )
                self.loop_stack.append(loop_context)
        
        elif cmd_text == 'endwhile':
            # Jump back to while condition
            if self.loop_stack and self.loop_stack[-1].label == o_cmd.label:
                while_line = self.loop_stack[-1].start_line
                self.loop_stack.pop()
                return while_line
        
        return None
    
    def _execute_repeat_loop(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute repeat loop."""
        cmd_text = self._get_command_text(o_cmd)
        
        if cmd_text == 'repeat':
            if o_cmd.expression:
                variables = self.variable_manager.get_all_variables()
                repeat_count = self.expression_evaluator.evaluate(
                    o_cmd.expression, variables, o_cmd.line_number
                )
                
                if repeat_count is None or repeat_count <= 0:
                    # Skip to endrepeat
                    return self._find_matching_endrepeat(o_cmd.label, self.current_line)
                
                # Push loop context
                loop_context = LoopContext(
                    type=OWordType.LOOP_REPEAT,
                    label=o_cmd.label,
                    start_line=self.current_line,
                    end_line=self._find_matching_endrepeat(o_cmd.label, self.current_line) - 1,
                    repeat_count=int(repeat_count),
                    current_iteration=0
                )
                self.loop_stack.append(loop_context)
        
        elif cmd_text == 'endrepeat':
            # Check if we should repeat
            if self.loop_stack and self.loop_stack[-1].label == o_cmd.label:
                loop_ctx = self.loop_stack[-1]
                loop_ctx.current_iteration += 1
                
                if loop_ctx.current_iteration < loop_ctx.repeat_count:
                    # Continue loop
                    return loop_ctx.start_line + 1
                else:
                    # End loop
                    self.loop_stack.pop()
        
        return None
    
    def _execute_break(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute break statement."""
        # Find matching loop
        for i in range(len(self.loop_stack) - 1, -1, -1):
            if self.loop_stack[i].label == o_cmd.label:
                # Jump to end of loop
                end_line = self.loop_stack[i].end_line
                # Remove loop contexts up to this one
                self.loop_stack = self.loop_stack[:i]
                return end_line + 1
        
        self.error_collector.add_error(
            o_cmd.line_number, 0, 0,
            f"Break outside of loop O{o_cmd.label}",
            ErrorType.RUNTIME
        )
        return None
    
    def _execute_continue(self, o_cmd: OWordCommand) -> Optional[int]:
        """Execute continue statement."""
        # Find matching loop
        for i in range(len(self.loop_stack) - 1, -1, -1):
            if self.loop_stack[i].label == o_cmd.label:
                loop_ctx = self.loop_stack[i]
                if loop_ctx.type == OWordType.LOOP_WHILE:
                    # Jump back to while condition
                    return loop_ctx.start_line
                elif loop_ctx.type == OWordType.LOOP_REPEAT:
                    # Jump to endrepeat for iteration check
                    return loop_ctx.end_line
        
        self.error_collector.add_error(
            o_cmd.line_number, 0, 0,
            f"Continue outside of loop O{o_cmd.label}",
            ErrorType.RUNTIME
        )
        return None
    
    def _find_matching_else_or_endif(self, label: Union[str, int], start_line: int) -> int:
        """Find the matching else, elseif, or endif for an if statement."""
        # TODO: Implement proper structure parsing
        # For now, return next line (simplified)
        return start_line + 1
    
    def _find_matching_endwhile(self, label: Union[str, int], start_line: int) -> int:
        """Find the matching endwhile for a while statement."""
        # TODO: Implement proper structure parsing
        return start_line + 1
    
    def _find_matching_endrepeat(self, label: Union[str, int], start_line: int) -> int:
        """Find the matching endrepeat for a repeat statement."""
        # TODO: Implement proper structure parsing
        return start_line + 1
    
    def is_inside_subroutine(self) -> bool:
        """Check if currently executing inside a subroutine."""
        return len(self.call_stack) > 0
    
    def get_current_subroutine(self) -> Optional[str]:
        """Get the name of the currently executing subroutine."""
        if self.call_stack:
            return str(self.call_stack[-1].subroutine_name)
        return None