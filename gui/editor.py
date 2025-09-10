"""
Enhanced G-code editor widget with LinuxCNC syntax highlighting and dark mode.
"""
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtGui import (QColor, QTextFormat, QPainter, QFont, QSyntaxHighlighter, 
                          QTextCharFormat, QPalette, QTextCursor)
from PySide6.QtCore import Qt, QRect, Signal, QSize, QTimer
import re


class LinuxCNCHighlighter(QSyntaxHighlighter):
    """LinuxCNC G-code syntax highlighter with dark mode colors."""
    
    def __init__(self, document):
        super().__init__(document)
        
        # Set up font
        font = QFont('Consolas', 11)
        font.setFixedPitch(True)
        
        # Define color formats for different G-code elements
        
        # G-code specific highlighting
        self.g0_format = QTextCharFormat()
        self.g0_format.setForeground(QColor('#ff6b6b'))  # Red for rapid (G0)
        self.g0_format.setFont(font)
        self.g0_format.setFontWeight(QFont.Weight.Bold)
        
        self.g1_format = QTextCharFormat()
        self.g1_format.setForeground(QColor('#51cf66'))  # Green for linear feed (G1)
        self.g1_format.setFont(font)
        self.g1_format.setFontWeight(QFont.Weight.Bold)
        
        self.g2g3_format = QTextCharFormat()
        self.g2g3_format.setForeground(QColor('#ffd43b'))  # Yellow for arcs (G2/G3)
        self.g2g3_format.setFont(font)
        self.g2g3_format.setFontWeight(QFont.Weight.Bold)
        
        self.gcode_format = QTextCharFormat()
        self.gcode_format.setForeground(QColor('#74c0fc'))  # Light blue for other G-codes
        self.gcode_format.setFont(font)
        
        self.mcode_format = QTextCharFormat()
        self.mcode_format.setForeground(QColor('#ff8cc8'))  # Pink for M-codes
        self.mcode_format.setFont(font)
        
        # Axis words
        self.x_format = QTextCharFormat()
        self.x_format.setForeground(QColor('#ff9999'))  # Light red for X
        self.x_format.setFont(font)
        
        self.y_format = QTextCharFormat()
        self.y_format.setForeground(QColor('#99ff99'))  # Light green for Y
        self.y_format.setFont(font)
        
        self.z_format = QTextCharFormat()
        self.z_format.setForeground(QColor('#9999ff'))  # Light blue for Z
        self.z_format.setFont(font)
        
        self.abc_format = QTextCharFormat()
        self.abc_format.setForeground(QColor('#ffcc99'))  # Light orange for A/B/C
        self.abc_format.setFont(font)
        
        # Parameters
        self.ijk_format = QTextCharFormat()
        self.ijk_format.setForeground(QColor('#cc99ff'))  # Light purple for I/J/K
        self.ijk_format.setFont(font)
        
        self.r_format = QTextCharFormat()
        self.r_format.setForeground(QColor('#ff99cc'))  # Light pink for R
        self.r_format.setFont(font)
        
        self.fs_format = QTextCharFormat()
        self.fs_format.setForeground(QColor('#ffff99'))  # Light yellow for F/S
        self.fs_format.setFont(font)
        
        self.other_param_format = QTextCharFormat()
        self.other_param_format.setForeground(QColor('#99ffcc'))  # Light cyan for other params
        self.other_param_format.setFont(font)
        
        # Variables and expressions
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor('#ffa500'))  # Orange for variables (#var)
        self.variable_format.setFont(font)
        
        self.expression_format = QTextCharFormat()
        self.expression_format.setForeground(QColor('#dda0dd'))  # Plum for expressions [expr]
        self.expression_format.setFont(font)
        
        # Comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor('#6c757d'))  # Gray for comments
        self.comment_format.setFont(font)
        self.comment_format.setFontItalic(True)
        
        # Line numbers
        self.line_number_format = QTextCharFormat()
        self.line_number_format.setForeground(QColor('#adb5bd'))  # Light gray for N words
        self.line_number_format.setFont(font)
        
        # O-words (subroutines, control structures)
        self.oword_format = QTextCharFormat()
        self.oword_format.setForeground(QColor('#20c997'))  # Teal for O-words
        self.oword_format.setFont(font)
        self.oword_format.setFontWeight(QFont.Weight.Bold)

    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        i = 0
        length = len(text)
        
        while i < length:
            # Skip whitespace
            if text[i].isspace():
                i += 1
                continue
            
            # Handle comments (semicolon or parentheses)
            if text[i] == ';':
                self.setFormat(i, length - i, self.comment_format)
                break
            elif text[i] == '(':
                # Find closing parenthesis
                start = i
                i += 1
                while i < length and text[i] != ')':
                    i += 1
                if i < length:
                    i += 1
                self.setFormat(start, i - start, self.comment_format)
                continue
            
            # Handle expressions in brackets [expr]
            elif text[i] == '[':
                start = i
                i += 1
                bracket_count = 1
                while i < length and bracket_count > 0:
                    if text[i] == '[':
                        bracket_count += 1
                    elif text[i] == ']':
                        bracket_count -= 1
                    i += 1
                self.setFormat(start, i - start, self.expression_format)
                continue
            
            # Handle variables #var or #<var>
            elif text[i] == '#':
                start = i
                i += 1
                if i < length and text[i] == '<':
                    # Named variable #<name>
                    while i < length and text[i] != '>':
                        i += 1
                    if i < length:
                        i += 1
                else:
                    # Numbered variable #123
                    while i < length and text[i].isdigit():
                        i += 1
                self.setFormat(start, i - start, self.variable_format)
                continue
            
            # Handle letters (G-codes, M-codes, axis words, etc.)
            elif text[i].isalpha():
                letter_start = i
                letter = text[i].upper()
                i += 1
                
                # Skip whitespace after letter
                while i < length and text[i].isspace():
                    i += 1
                
                # Parse the value after the letter
                value_start = i
                if letter == 'O':
                    # O-words can have names or numbers
                    while i < length and (text[i].isalnum() or text[i] in '._'):
                        i += 1
                else:
                    # Regular numeric values (including decimals, +/-, expressions)
                    while i < length and (text[i].isdigit() or text[i] in '+-.#[]<>'):
                        if text[i] == '[':
                            # Skip expressions
                            bracket_count = 1
                            i += 1
                            while i < length and bracket_count > 0:
                                if text[i] == '[':
                                    bracket_count += 1
                                elif text[i] == ']':
                                    bracket_count -= 1
                                i += 1
                        elif text[i] == '#':
                            # Skip variables
                            i += 1
                            if i < length and text[i] == '<':
                                while i < length and text[i] != '>':
                                    i += 1
                                if i < length:
                                    i += 1
                            else:
                                while i < length and text[i].isdigit():
                                    i += 1
                        else:
                            i += 1
                
                # Apply formatting based on letter and value
                total_length = i - letter_start
                if total_length > 1 or letter in ['G', 'M', 'O']:  # Allow single letters for G/M/O
                    value_text = text[value_start:i].strip()
                    
                    if letter == 'G':
                        # Specific G-code highlighting
                        if value_text in ['0', '00']:
                            self.setFormat(letter_start, total_length, self.g0_format)
                        elif value_text in ['1', '01']:
                            self.setFormat(letter_start, total_length, self.g1_format)
                        elif value_text in ['2', '02', '3', '03']:
                            self.setFormat(letter_start, total_length, self.g2g3_format)
                        else:
                            self.setFormat(letter_start, total_length, self.gcode_format)
                    elif letter == 'M':
                        self.setFormat(letter_start, total_length, self.mcode_format)
                    elif letter == 'O':
                        self.setFormat(letter_start, total_length, self.oword_format)
                    elif letter == 'X':
                        self.setFormat(letter_start, total_length, self.x_format)
                    elif letter == 'Y':
                        self.setFormat(letter_start, total_length, self.y_format)
                    elif letter == 'Z':
                        self.setFormat(letter_start, total_length, self.z_format)
                    elif letter in ['A', 'B', 'C', 'U', 'V', 'W']:
                        self.setFormat(letter_start, total_length, self.abc_format)
                    elif letter in ['I', 'J', 'K']:
                        self.setFormat(letter_start, total_length, self.ijk_format)
                    elif letter == 'R':
                        self.setFormat(letter_start, total_length, self.r_format)
                    elif letter in ['F', 'S']:
                        self.setFormat(letter_start, total_length, self.fs_format)
                    elif letter == 'N':
                        self.setFormat(letter_start, total_length, self.line_number_format)
                    elif letter in ['T', 'H', 'D', 'L', 'P', 'Q', 'E']:
                        self.setFormat(letter_start, total_length, self.other_param_format)
                continue
            
            # Skip any other character
            i += 1


class LineNumberArea(QWidget):
    """Line number area widget for the editor."""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class Editor(QPlainTextEdit):
    """Enhanced G-code editor with LinuxCNC syntax highlighting and dark mode."""
    
    selectionChangedSignal = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup dark mode appearance
        self.setup_dark_mode()
        
        # Line number area
        self.lineNumberArea = LineNumberArea(self)
        
        # Tracking sets
        self.highlighted_lines = set()
        self.error_lines = set()
        
        # Selection tracking
        self.selected_text = ""
        self.selection_timer = QTimer()
        self.selection_timer.setSingleShot(True)
        self.selection_timer.timeout.connect(self.highlight_selections)
        
        # Setup editor
        self.setup_editor()
        
        # Setup syntax highlighter
        self.highlighter = LinuxCNCHighlighter(self.document())
        
        # Connect signals
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.selectionChanged.connect(self.on_selection_changed)

    def setup_dark_mode(self):
        """Configure dark mode appearance."""
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor('#2b2b2b'))  # Background
        palette.setColor(QPalette.Text, QColor('#f8f8f2'))  # Text
        palette.setColor(QPalette.Highlight, QColor('#44475a'))  # Selection
        palette.setColor(QPalette.HighlightedText, QColor('#f8f8f2'))  # Selected text
        self.setPalette(palette)

    def setup_editor(self):
        """Configure the editor appearance and behavior."""
        # Disable line wrapping for code
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        # Set monospaced font
        font = QFont("Consolas", 11)
        if not font.exactMatch():
            font = QFont("Courier New", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        
        # Set tab width to 4 spaces
        tab_width = self.fontMetrics().horizontalAdvance(' ') * 4
        self.setTabStopDistance(tab_width)
        
        # Initialize line number area
        self.updateLineNumberAreaWidth(0)

    def highlight_lines(self, lines):
        """Highlight specific lines (for geometry selection)."""
        self.highlighted_lines = set(lines) if lines else set()
        self.update_extra_selections()

    def highlight_error_lines(self, lines):
        """Highlight lines with errors."""
        self.error_lines = set(lines) if lines else set()
        self.update_extra_selections()

    def clear_error_highlights(self):
        """Clear all error highlighting."""
        self.error_lines.clear()
        self.update_extra_selections()

    def update_extra_selections(self):
        """Update all line highlighting (current line, selection, errors, geometry)."""
        selections = []
        
        # Add current line highlighting
        if not self.isReadOnly():
            cursor = self.textCursor()
            if not cursor.hasSelection():
                selection = QTextEdit.ExtraSelection()
                line_color = QColor('#44475a')  # Dark gray for current line
                selection.format.setBackground(line_color)
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                selection.cursor = cursor
                selection.cursor.clearSelection()
                selections.append(selection)
        
        # Add error line highlighting (red background)
        for line_num in self.error_lines:
            if line_num > 0:
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor('#660000'))  # Dark red
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                
                block = self.document().findBlockByNumber(line_num - 1)
                if block.isValid():
                    selection.cursor = self.textCursor()
                    selection.cursor.setPosition(block.position())
                    selection.cursor.clearSelection()
                    selections.append(selection)
        
        # Add geometry highlight (blue background)
        for line_num in self.highlighted_lines:
            if line_num > 0 and line_num not in self.error_lines:
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor('#1e3a8a'))  # Dark blue
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                
                block = self.document().findBlockByNumber(line_num - 1)
                if block.isValid():
                    selection.cursor = self.textCursor()
                    selection.cursor.setPosition(block.position())
                    selection.cursor.clearSelection()
                    selections.append(selection)
        
        # Add selected text highlighting
        if self.selected_text and len(self.selected_text) > 1:
            document = self.document()
            cursor = QTextCursor(document)
            
            while True:
                cursor = document.find(self.selected_text, cursor)
                if cursor.isNull():
                    break
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor('#6f42c1'))  # Purple for selected text occurrences
                selection.cursor = cursor
                selections.append(selection)
        
        self.setExtraSelections(selections)

    def highlight_current_line(self):
        """Highlight the current line."""
        self.update_extra_selections()

    def on_selection_changed(self):
        """Handle text selection changes and emit line numbers."""
        cursor = self.textCursor()
        
        # Handle selected text highlighting
        if cursor.hasSelection():
            selected = cursor.selectedText().strip()
            if len(selected) > 1 and selected != self.selected_text:
                self.selected_text = selected
                self.selection_timer.start(300)
            
            # Emit selected line numbers
            start_pos = cursor.selectionStart()
            end_pos = cursor.selectionEnd()
            
            start_block = self.document().findBlock(start_pos)
            end_block = self.document().findBlock(end_pos)
            
            # Handle selection that ends at the start of a line
            if end_pos == end_block.position() and end_block.previous().isValid():
                end_block = end_block.previous()
            
            # Collect all selected lines with content
            selected_lines = []
            current_block = start_block
            while current_block.isValid() and current_block.blockNumber() <= end_block.blockNumber():
                line_text = current_block.text().strip()
                if line_text and not line_text.startswith(';'):  # Skip empty lines and comments
                    selected_lines.append(current_block.blockNumber() + 1)
                
                if current_block == end_block:
                    break
                current_block = current_block.next()
            
            self.selectionChangedSignal.emit(selected_lines)
        else:
            self.selected_text = ""
            self.selectionChangedSignal.emit([])
        
        self.update_extra_selections()

    def highlight_selections(self):
        """Highlight all occurrences of selected text."""
        self.update_extra_selections()

    # Line number area methods
    def lineNumberAreaWidth(self):
        """Calculate the width needed for line numbers."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        """Update the viewport margins to accommodate line numbers."""
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        """Update the line number area when scrolling."""
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        """Paint the line number area."""
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor('#383838'))  # Dark background for line numbers
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                
                # Highlight line numbers for error lines
                if (blockNumber + 1) in self.error_lines:
                    painter.setPen(QColor('#ff6b6b'))  # Red for error lines
                else:
                    painter.setPen(QColor('#6c757d'))  # Gray for normal lines
                
                painter.drawText(0, int(top), self.lineNumberArea.width() - 3, 
                               self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    # Utility methods
    def goto_line(self, line_number):
        """Jump to a specific line number."""
        if line_number > 0:
            block = self.document().findBlockByNumber(line_number - 1)
            if block.isValid():
                cursor = self.textCursor()
                cursor.setPosition(block.position())
                self.setTextCursor(cursor)
                self.centerCursor()

    def get_current_line_number(self):
        """Get the current cursor line number."""
        cursor = self.textCursor()
        return cursor.blockNumber() + 1