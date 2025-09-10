"""
Mathematical expression evaluator for G-code interpreter.
Simple, robust evaluation of LinuxCNC-style expressions.
"""
import math
import re
from typing import Dict, Optional
from utils.errors import ErrorCollector, ErrorType


class ExpressionEvaluator:
    """Evaluates mathematical expressions in G-code safely."""
    
    def __init__(self, error_collector: ErrorCollector):
        self.error_collector = error_collector
        
        # Math functions available in expressions
        self.functions = {
            'abs': abs,
            'acos': math.acos,
            'asin': math.asin, 
            'atan': math.atan,
            'cos': math.cos,
            'exp': math.exp,
            'fix': math.floor,
            'fup': math.ceil,
            'ln': math.log,
            'round': round,
            'sin': math.sin,
            'sqrt': math.sqrt,
            'tan': math.tan,
        }
    
    def evaluate(self, expression: str, variables: Dict[str, float], 
                line_number: int = 0) -> Optional[float]:
        """
        Evaluate a mathematical expression with variables.
        
        Args:
            expression: Expression to evaluate like "5 + #100 * sin[30]"
            variables: Available variables like {"#100": 10.5}
            line_number: Line number for error reporting
            
        Returns:
            Evaluated result or None if error
        """
        expr = expression.strip()
        if not expr:
            return 0.0
        
        # Substitute variables first
        expr = self._substitute_variables(expr, variables, line_number)
        if expr is None:
            return None
        
        # Replace function calls
        expr = self._replace_functions(expr)
        
        # Replace operators
        expr = self._replace_operators(expr)
        
        # Evaluate safely
        return self._safe_eval(expr, line_number)
    
    def _substitute_variables(self, expr: str, variables: Dict[str, float], 
                            line_number: int) -> Optional[str]:
        """Replace #var and #<var> with values."""
        # Find all variable references
        var_pattern = r'#(?:(\d+)|<([^>]+)>)'
        
        def replace_var(match):
            if match.group(1):  # Numbered: #123
                var_key = f"#{match.group(1)}"
            else:  # Named: #<n>
                var_key = f"#{match.group(2)}"
            
            if var_key in variables:
                return str(variables[var_key])
            else:
                self.error_collector.add_error(
                    line_number, 0, 0,
                    f"Undefined variable: {match.group(0)}",
                    ErrorType.RUNTIME
                )
                return "0"
        
        return re.sub(var_pattern, replace_var, expr)
    
    def _replace_functions(self, expr: str) -> str:
        """Replace function calls like sin[30] with results."""
        # Pattern: function_name[argument]
        func_pattern = r'([a-z]+)\[([^\]]+)\]'
        
        def replace_func(match):
            func_name = match.group(1).lower()
            arg_expr = match.group(2)
            
            if func_name in self.functions:
                # Evaluate argument and apply function
                arg_value = self._safe_eval(arg_expr, 0)
                if arg_value is not None:
                    result = self.functions[func_name](float(arg_value))
                    return str(result)
            
            return match.group(0)  # Leave unchanged if unknown function
        
        # Keep replacing until no more functions
        while '[' in expr and any(f in expr for f in self.functions):
            expr = re.sub(func_pattern, replace_func, expr)
        
        return expr
    
    def _replace_operators(self, expr: str) -> str:
        """Replace LinuxCNC operators with Python equivalents."""
        replacements = {
            r'\bEQ\b': '==',
            r'\bNE\b': '!=',
            r'\bGT\b': '>',
            r'\bGE\b': '>=', 
            r'\bLT\b': '<',
            r'\bLE\b': '<=',
            r'\bAND\b': ' and ',
            r'\bOR\b': ' or ',
            r'\bXOR\b': '^',
            r'\bMOD\b': '%',
        }
        
        for pattern, replacement in replacements.items():
            expr = re.sub(pattern, replacement, expr, flags=re.IGNORECASE)
        
        return expr
    
    def _safe_eval(self, expr: str, line_number: int) -> Optional[float]:
        """Safely evaluate expression using restricted eval."""
        # Only allow safe operations
        allowed = {
            '__builtins__': {},
            'abs': abs,
            'round': round,
            'pow': pow,
            'min': min,
            'max': max,
        }
        
        result = eval(expr, allowed, {})
        return float(result)
    
    def is_assignment(self, text: str) -> bool:
        """Check if text contains a variable assignment."""
        return '=' in text and ('#' in text[:text.find('=')])
    
    def parse_assignment(self, text: str) -> Optional[tuple]:
        """
        Parse variable assignment like '#100=42' or '#<len>=5.5'.
        
        Returns:
            (variable_name, expression) or None if not assignment
        """
        # Pattern for assignments
        pattern = r'(#(?:\d+|<[^>]+>))\s*=\s*(.+)'
        
        match = re.match(pattern, text.strip())
        if match:
            return match.group(1), match.group(2)
        
        return None