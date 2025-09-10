"""
G-code lexer for tokenizing raw G-code text.
"""
import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Iterator, Tuple
from utils.errors import ErrorCollector, ErrorType, ErrorSeverity


class TokenType(Enum):
    # Command tokens
    G_COMMAND = "G"
    M_COMMAND = "M"
    O_COMMAND = "O"
    
    # Axis words
    X_WORD = "X"
    Y_WORD = "Y"
    Z_WORD = "Z"
    A_WORD = "A"
    B_WORD = "B"
    C_WORD = "C"
    U_WORD = "U"
    V_WORD = "V"
    W_WORD = "W"
    
    # Parameter words
    I_WORD = "I"
    J_WORD = "J"
    K_WORD = "K"
    L_WORD = "L"
    P_WORD = "P"
    Q_WORD = "Q"
    R_WORD = "R"
    H_WORD = "H"
    
    # Settings words
    F_WORD = "F"
    S_WORD = "S"
    T_WORD = "T"
    N_WORD = "N"
    
    # Values and expressions
    NUMBER = "NUMBER"
    VARIABLE = "VARIABLE"
    EXPRESSION = "EXPRESSION"
    
    # Comments
    COMMENT = "COMMENT"
    MSG_COMMENT = "MSG_COMMENT"
    DEBUG_COMMENT = "DEBUG_COMMENT"
    PYTHON_COMMENT = "PYTHON_COMMENT"
    
    # Special
    NEWLINE = "NEWLINE"
    EOF = "EOF"


@dataclass
class Token:
    """Represents a single token in G-code."""
    type: TokenType
    value: str
    line_number: int
    char_start: int
    char_end: int
    
    def __str__(self):
        return f"{self.type.value}:{self.value}"


class GCodeLexer:
    """Tokenizes G-code text into a stream of tokens."""
    
    # Pattern for matching G-code words
    WORD_PATTERN = re.compile(r'([A-Z])([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|#\w+(?:[+\-*/]\w+)*)', re.IGNORECASE)
    
    # Pattern for variables and expressions
    VARIABLE_PATTERN = re.compile(r'#\w+')
    EXPRESSION_PATTERN = re.compile(r'\[([^\]]+)\]')
    NUMBER_PATTERN = re.compile(r'[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?')
    
    # Comment patterns
    PAREN_COMMENT_PATTERN = re.compile(r'\(([^)]*)\)')
    SEMICOLON_COMMENT_PATTERN = re.compile(r';(.*)$')
    
    def __init__(self, error_collector: ErrorCollector):
        self.error_collector = error_collector
        
    def tokenize(self, gcode_text: str) -> List[Token]:
        """Tokenize the entire G-code text."""
        tokens = []
        lines = gcode_text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_tokens = self._tokenize_line(line, line_num)
            tokens.extend(line_tokens)
            tokens.append(Token(TokenType.NEWLINE, '\n', line_num, len(line), len(line)))
        
        tokens.append(Token(TokenType.EOF, '', len(lines), 0, 0))
        return tokens
    
    def _tokenize_line(self, line: str, line_number: int) -> List[Token]:
        """Tokenize a single line of G-code."""
        tokens = []
        
        # Remove whitespace
        original_line = line
        line = line.strip()
        if not line:
            return tokens
        
        pos = 0
        while pos < len(line):
            # Skip whitespace
            if line[pos].isspace():
                pos += 1
                continue
            
            # Check for comments first
            comment_token = self._try_parse_comment(line, pos, line_number, original_line)
            if comment_token:
                tokens.append(comment_token)
                break  # Comments consume rest of line
            
            # Check for expressions in brackets
            expr_match = self.EXPRESSION_PATTERN.match(line, pos)
            if expr_match:
                start_pos = self._get_original_position(original_line, line, pos)
                end_pos = start_pos + len(expr_match.group(0))
                token = Token(TokenType.EXPRESSION, expr_match.group(1), 
                            line_number, start_pos, end_pos)
                tokens.append(token)
                pos = expr_match.end()
                continue
            
            # Check for G-code words
            word_match = self.WORD_PATTERN.match(line, pos)
            if word_match:
                letter = word_match.group(1).upper()
                value = word_match.group(2)
                
                start_pos = self._get_original_position(original_line, line, pos)
                end_pos = start_pos + len(word_match.group(0))
                
                # Determine token type based on letter
                token_type = self._get_token_type_for_letter(letter)
                if token_type:
                    token = Token(token_type, value, line_number, start_pos, end_pos)
                    tokens.append(token)
                else:
                    self.error_collector.add_error(
                        line_number, start_pos, end_pos,
                        f"Unknown G-code letter: {letter}",
                        ErrorType.SYNTAX
                    )
                
                pos = word_match.end()
                continue
            
            # If we get here, we have an unrecognized character
            start_pos = self._get_original_position(original_line, line, pos)
            self.error_collector.add_error(
                line_number, start_pos, start_pos + 1,
                f"Unrecognized character: '{line[pos]}'",
                ErrorType.SYNTAX
            )
            pos += 1
        
        return tokens
    
    def _try_parse_comment(self, line: str, pos: int, line_number: int, original_line: str) -> Optional[Token]:
        """Try to parse a comment starting at the given position."""
        # Check for parentheses comment
        if line[pos] == '(':
            paren_match = self.PAREN_COMMENT_PATTERN.match(line, pos)
            if paren_match:
                comment_text = paren_match.group(1)
                start_pos = self._get_original_position(original_line, line, pos)
                end_pos = start_pos + len(paren_match.group(0))
                
                # Check for special comment types
                comment_upper = comment_text.upper().strip()
                if comment_upper.startswith('MSG,'):
                    return Token(TokenType.MSG_COMMENT, comment_text[4:].strip(), 
                               line_number, start_pos, end_pos)
                elif comment_upper.startswith('DEBUG,'):
                    return Token(TokenType.DEBUG_COMMENT, comment_text[6:].strip(), 
                               line_number, start_pos, end_pos)
                elif comment_upper.startswith('PY,'):
                    return Token(TokenType.PYTHON_COMMENT, comment_text[3:].strip(), 
                               line_number, start_pos, end_pos)
                else:
                    return Token(TokenType.COMMENT, comment_text, 
                               line_number, start_pos, end_pos)
            else:
                # Unclosed parenthesis
                start_pos = self._get_original_position(original_line, line, pos)
                self.error_collector.add_error(
                    line_number, start_pos, len(original_line),
                    "Unclosed parenthesis in comment",
                    ErrorType.SYNTAX
                )
                return Token(TokenType.COMMENT, line[pos+1:], 
                           line_number, start_pos, len(original_line))
        
        # Check for semicolon comment
        elif line[pos] == ';':
            semicolon_match = self.SEMICOLON_COMMENT_PATTERN.match(line, pos)
            if semicolon_match:
                comment_text = semicolon_match.group(1)
                start_pos = self._get_original_position(original_line, line, pos)
                end_pos = len(original_line)
                return Token(TokenType.COMMENT, comment_text, 
                           line_number, start_pos, end_pos)
        
        return None
    
    def _get_token_type_for_letter(self, letter: str) -> Optional[TokenType]:
        """Get the appropriate token type for a G-code letter."""
        token_map = {
            'G': TokenType.G_COMMAND,
            'M': TokenType.M_COMMAND,
            'O': TokenType.O_COMMAND,
            'X': TokenType.X_WORD,
            'Y': TokenType.Y_WORD,
            'Z': TokenType.Z_WORD,
            'A': TokenType.A_WORD,
            'B': TokenType.B_WORD,
            'C': TokenType.C_WORD,
            'U': TokenType.U_WORD,
            'V': TokenType.V_WORD,
            'W': TokenType.W_WORD,
            'I': TokenType.I_WORD,
            'J': TokenType.J_WORD,
            'K': TokenType.K_WORD,
            'L': TokenType.L_WORD,
            'P': TokenType.P_WORD,
            'Q': TokenType.Q_WORD,
            'R': TokenType.R_WORD,
            'H': TokenType.H_WORD,
            'F': TokenType.F_WORD,
            'S': TokenType.S_WORD,
            'T': TokenType.T_WORD,
            'N': TokenType.N_WORD,
        }
        return token_map.get(letter)
    
    def _get_original_position(self, original_line: str, processed_line: str, processed_pos: int) -> int:
        """Map position in processed line back to original line position."""
        # This is a simplified mapping - in practice, you might need more sophisticated tracking
        # if you do complex preprocessing
        stripped_count = len(original_line) - len(original_line.lstrip())
        return stripped_count + processed_pos