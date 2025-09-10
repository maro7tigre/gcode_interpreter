"""
G-code parser for creating structured blocks from token streams.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from core.lexer import Token, TokenType
from utils.errors import ErrorCollector, ErrorType, ErrorSeverity


@dataclass
class Block:
    """Represents a parsed block of G-code with all its components."""
    line_number: int
    
    # Command codes
    g_codes: Dict[int, float] = field(default_factory=dict)
    m_codes: Dict[int, float] = field(default_factory=dict)
    o_word: Optional[str] = None
    
    # Axis words
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    a: Optional[float] = None
    b: Optional[float] = None
    c: Optional[float] = None
    u: Optional[float] = None
    v: Optional[float] = None
    w: Optional[float] = None
    
    # Parameter words
    i: Optional[float] = None
    j: Optional[float] = None
    k: Optional[float] = None
    l: Optional[float] = None
    p: Optional[float] = None
    q: Optional[float] = None
    r: Optional[float] = None
    h: Optional[float] = None
    
    # Settings
    f: Optional[float] = None  # Feed rate
    s: Optional[float] = None  # Spindle speed
    t: Optional[int] = None    # Tool number
    n: Optional[int] = None    # Line number
    
    # Comments and special
    comment: Optional[str] = None
    msg_comment: Optional[str] = None
    debug_comment: Optional[str] = None
    python_comment: Optional[str] = None
    
    # Position tracking for error reporting
    tokens: List[Token] = field(default_factory=list)
    
    def has_motion(self) -> bool:
        """Check if this block contains motion commands."""
        motion_gcodes = {0, 1, 2, 3, 5, 33, 38, 73, 76, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89}
        return any(g in motion_gcodes for g in self.g_codes.keys())
    
    def has_axis_words(self) -> bool:
        """Check if this block contains any axis words."""
        return any(getattr(self, axis) is not None for axis in 'xyzabcuvw')
    
    def get_axis_words(self) -> Dict[str, float]:
        """Get all axis words present in this block."""
        axes = {}
        for axis in 'xyzabcuvw':
            value = getattr(self, axis)
            if value is not None:
                axes[axis.upper()] = value
        return axes


class GCodeParser:
    """Parses tokens into structured G-code blocks."""
    
    # Modal group definitions
    MODAL_GROUPS = {
        'motion': {0, 1, 2, 3, 33, 38, 73, 76, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89},
        'plane': {17, 18, 19},
        'distance': {90, 91},
        'arc_distance': {90.1, 91.1},
        'feed_rate_mode': {93, 94, 95},
        'units': {20, 21},
        'cutter_comp': {40, 41, 42},
        'tool_length': {43, 49},
        'coordinate_system': {54, 55, 56, 57, 58, 59, 59.1, 59.2, 59.3},
        'path_control': {61, 61.1, 64},
        'return_mode': {98, 99},
        'non_modal': {4, 10, 28, 30, 53, 92, 92.1, 92.2, 92.3}
    }
    
    def __init__(self, error_collector: ErrorCollector):
        self.error_collector = error_collector
    
    def parse(self, tokens: List[Token]) -> List[Block]:
        """Parse tokens into blocks."""
        blocks = []
        current_block = None
        current_line = 1
        
        for token in tokens:
            if token.type == TokenType.NEWLINE:
                if current_block and self._is_block_valid(current_block):
                    blocks.append(current_block)
                current_block = None
                current_line = token.line_number + 1
                continue
            
            if token.type == TokenType.EOF:
                if current_block and self._is_block_valid(current_block):
                    blocks.append(current_block)
                break
            
            # Start new block if needed
            if current_block is None:
                current_block = Block(line_number=token.line_number)
            
            # Add token to block
            current_block.tokens.append(token)
            
            # Process token based on type
            try:
                self._process_token(current_block, token)
            except ValueError as e:
                self.error_collector.add_error(
                    token.line_number, token.char_start, token.char_end,
                    str(e), ErrorType.SYNTAX
                )
        
        return blocks
    
    def _process_token(self, block: Block, token: Token):
        """Process a single token and add it to the block."""
        if token.type == TokenType.G_COMMAND:
            g_num = self._parse_number(token.value)
            if g_num is not None:
                block.g_codes[g_num] = g_num
            
        elif token.type == TokenType.M_COMMAND:
            m_num = self._parse_number(token.value)
            if m_num is not None:
                block.m_codes[m_num] = m_num
                
        elif token.type == TokenType.O_COMMAND:
            block.o_word = token.value
            
        elif token.type == TokenType.X_WORD:
            block.x = self._parse_number(token.value)
        elif token.type == TokenType.Y_WORD:
            block.y = self._parse_number(token.value)
        elif token.type == TokenType.Z_WORD:
            block.z = self._parse_number(token.value)
        elif token.type == TokenType.A_WORD:
            block.a = self._parse_number(token.value)
        elif token.type == TokenType.B_WORD:
            block.b = self._parse_number(token.value)
        elif token.type == TokenType.C_WORD:
            block.c = self._parse_number(token.value)
        elif token.type == TokenType.U_WORD:
            block.u = self._parse_number(token.value)
        elif token.type == TokenType.V_WORD:
            block.v = self._parse_number(token.value)
        elif token.type == TokenType.W_WORD:
            block.w = self._parse_number(token.value)
            
        elif token.type == TokenType.I_WORD:
            block.i = self._parse_number(token.value)
        elif token.type == TokenType.J_WORD:
            block.j = self._parse_number(token.value)
        elif token.type == TokenType.K_WORD:
            block.k = self._parse_number(token.value)
        elif token.type == TokenType.L_WORD:
            block.l = self._parse_number(token.value)
        elif token.type == TokenType.P_WORD:
            block.p = self._parse_number(token.value)
        elif token.type == TokenType.Q_WORD:
            block.q = self._parse_number(token.value)
        elif token.type == TokenType.R_WORD:
            block.r = self._parse_number(token.value)
        elif token.type == TokenType.H_WORD:
            block.h = self._parse_number(token.value)
            
        elif token.type == TokenType.F_WORD:
            block.f = self._parse_number(token.value)
        elif token.type == TokenType.S_WORD:
            block.s = self._parse_number(token.value)
        elif token.type == TokenType.T_WORD:
            block.t = int(self._parse_number(token.value) or 0)
        elif token.type == TokenType.N_WORD:
            block.n = int(self._parse_number(token.value) or 0)
            
        elif token.type == TokenType.COMMENT:
            block.comment = token.value
        elif token.type == TokenType.MSG_COMMENT:
            block.msg_comment = token.value
        elif token.type == TokenType.DEBUG_COMMENT:
            block.debug_comment = token.value
        elif token.type == TokenType.PYTHON_COMMENT:
            block.python_comment = token.value
    
    def _parse_number(self, value: str) -> Optional[float]:
        """Parse a numeric value, handling variables and expressions."""
        try:
            # Handle simple numbers
            if value.replace('.', '').replace('-', '').replace('+', '').replace('e', '').replace('E', '').isdigit():
                return float(value)
            
            # TODO: Handle variables (#var) and expressions in future iterations
            # For now, just try to parse as float
            return float(value)
            
        except ValueError:
            return None
    
    def _is_block_valid(self, block: Block) -> bool:
        """Validate a block and report any errors."""
        valid = True
        
        # Check for modal group conflicts
        for group_name, group_codes in self.MODAL_GROUPS.items():
            active_codes = [g for g in block.g_codes.keys() if g in group_codes]
            if len(active_codes) > 1:
                # Find tokens for error reporting
                error_tokens = [t for t in block.tokens 
                              if t.type == TokenType.G_COMMAND and 
                              self._parse_number(t.value) in active_codes]
                if error_tokens:
                    self.error_collector.add_error(
                        block.line_number, 
                        error_tokens[0].char_start,
                        error_tokens[-1].char_end,
                        f"Multiple codes from {group_name} modal group: {active_codes}",
                        ErrorType.SEMANTIC
                    )
                valid = False
        
        # Check for Group 0 and Group 1 conflict with axis words
        group0_codes = [g for g in block.g_codes.keys() if g in self.MODAL_GROUPS['non_modal']]
        group1_codes = [g for g in block.g_codes.keys() if g in self.MODAL_GROUPS['motion']]
        
        if group0_codes and group1_codes and block.has_axis_words():
            # Special exception for G53 which can work with motion
            if not (len(group0_codes) == 1 and 53 in group0_codes):
                self.error_collector.add_error(
                    block.line_number, 0, 0,
                    f"Group 0 code {group0_codes} conflicts with motion code {group1_codes} when axis words present",
                    ErrorType.SEMANTIC
                )
                valid = False
        
        return valid