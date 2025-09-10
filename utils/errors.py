"""
Error definitions and handling for G-code interpreter.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


class ErrorType(Enum):
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    RUNTIME = "runtime"
    WARNING = "warning"


class ErrorSeverity(Enum):
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class GCodeError:
    """Represents an error in G-code processing with position information."""
    line_number: int
    char_start: int
    char_end: int
    message: str
    error_type: ErrorType
    severity: ErrorSeverity = ErrorSeverity.ERROR
    
    def __str__(self):
        return f"Line {self.line_number}: {self.message}"


class ErrorCollector:
    """Collects and manages errors during G-code processing."""
    
    def __init__(self):
        self.errors: List[GCodeError] = []
    
    def add_error(self, line_number: int, char_start: int, char_end: int, 
                  message: str, error_type: ErrorType, 
                  severity: ErrorSeverity = ErrorSeverity.ERROR):
        """Add an error to the collection."""
        error = GCodeError(line_number, char_start, char_end, message, 
                          error_type, severity)
        self.errors.append(error)
    
    def get_errors_for_line(self, line_number: int) -> List[GCodeError]:
        """Get all errors for a specific line."""
        return [error for error in self.errors if error.line_number == line_number]
    
    def has_fatal_errors(self) -> bool:
        """Check if there are any fatal errors."""
        return any(error.severity == ErrorSeverity.FATAL for error in self.errors)
    
    def has_errors(self) -> bool:
        """Check if there are any errors (excluding warnings)."""
        return any(error.severity in [ErrorSeverity.ERROR, ErrorSeverity.FATAL] 
                  for error in self.errors)
    
    def clear(self):
        """Clear all errors."""
        self.errors.clear()
    
    def get_all_errors(self) -> List[GCodeError]:
        """Get all errors sorted by line number."""
        return sorted(self.errors, key=lambda e: (e.line_number, e.char_start))