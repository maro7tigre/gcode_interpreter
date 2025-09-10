"""
A more advanced G-code parser and expression evaluator.
This module is responsible for tokenizing a line of G-code and
evaluating any mathematical expressions or parameters it contains.
"""
import re
import math

class GCodeParser:
    def __init__(self, machine_state):
        self.machine_state = machine_state

    def parse_line(self, text, block):
        """Tokenizes a line of G-code and populates a Block object."""
        # Strip comments first
        text = re.sub(r'\(.*\)', '', text).strip()
        text = text.split(';')[0].strip()
        
        # Regex to find words, expressions, and named parameters
        pattern = re.compile(r'([a-zA-Z]{1,2})([+-]?#<[a-zA-Z0-9_]+>|[+-]?#\d+|[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?|\[[^\]]+\])')
        
        for match in pattern.finditer(text.lower()):
            letter = match.group(1)
            value_str = match.group(2)
            
            try:
                value = self.evaluate_expression(value_str)
                setattr(block, f"{letter}_flag", True)
                setattr(block, f"{letter}_number", value)
                block.words[letter] = value
            except Exception as e:
                return False, f"Error evaluating '{value_str}' on line {block.line_number}: {e}"

        return True, None

    def evaluate_expression(self, expr_str):
        """Evaluates a G-code value, which could be a number, parameter, or expression."""
        expr_str = expr_str.strip()

        # Case 1: It's a parameter lookup
        if expr_str.startswith('#'):
            if expr_str.startswith('#<') and expr_str.endswith('>'):
                param_name = expr_str[2:-1]
                return self.machine_state.get_parameter(param_name)
            else:
                param_index = int(expr_str[1:])
                return self.machine_state.get_parameter(param_index)
        
        # Case 2: It's a mathematical expression in brackets
        if expr_str.startswith('[') and expr_str.endswith(']'):
            return self._eval_math(expr_str[1:-1])

        # Case 3: It's a simple number
        try:
            return float(expr_str)
        except ValueError:
            pass 
            
        raise ValueError(f"Unknown expression format: {expr_str}")

    def _eval_math(self, expression):
        """
        A safe math evaluator for expressions within G-code.
        This is a simplified implementation. A production-ready version
        would use a more robust shunting-yard algorithm.
        """
        # Replace parameter lookups with their values
        expression = re.sub(r'#<([a-zA-Z0-9_]+)>', lambda m: str(self.machine_state.get_parameter(m.group(1))), expression)
        expression = re.sub(r'#(\d+)', lambda m: str(self.machine_state.get_parameter(int(m.group(1)))), expression)

        # Define safe functions
        safe_dict = {
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan, 'atan2': math.atan2,
            'sqrt': math.sqrt, 'abs': abs, 'round': round,
            'pi': math.pi, 'e': math.e, 'pow': math.pow
        }
        
        # Replace G-code function names with Python's and handle ATAN[/]
        expression = expression.replace('atan[', 'atan2(').replace(']/[', ',')
        expression = expression.replace(']', ')')
        expression = expression.replace('[', '(')


        return eval(expression, {"__builtins__": None}, safe_dict)

