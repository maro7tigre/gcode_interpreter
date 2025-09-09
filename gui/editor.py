"""
A custom G-code editor widget with line number highlighting.
"""
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtGui import QColor, QTextFormat, QPainter, QFont
from PySide6.QtCore import Qt, QRect, Signal

class Editor(QPlainTextEdit):
    selectionChangedSignal = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighted_lines = set()
        self.selectionChanged.connect(self.on_selection_changed)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        # Simple monospaced font for code
        font = self.font()
        font.setFamily("Courier")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.setFont(font)
        
    def highlight_lines(self, lines):
        self.highlighted_lines = set(lines)
        self.update_extra_selections()

    def update_extra_selections(self):
        selections = []
        for line_num in self.highlighted_lines:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(Qt.yellow).lighter(160))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            block = self.document().findBlockByNumber(line_num - 1)
            selection.cursor = self.textCursor()
            selection.cursor.setPosition(block.position())
            selection.cursor.clearSelection()
            selections.append(selection)
        self.setExtraSelections(selections)

    def on_selection_changed(self):
        selected_lines = set()
        cursor = self.textCursor()
        if not cursor.hasSelection():
            self.selectionChangedSignal.emit([])
            return

        start_block = self.document().findBlock(cursor.selectionStart())
        end_block = self.document().findBlock(cursor.selectionEnd())
        
        # Ensure the selection on the last line is counted if it contains content
        if cursor.atBlockEnd() and cursor.position() == cursor.selectionEnd():
             if end_block.previous().isValid():
                 end_block = end_block.previous()
       
        current_block = start_block
        while current_block.isValid() and current_block.blockNumber() <= end_block.blockNumber():
            if current_block.text().strip(): # Only add non-empty lines
                 selected_lines.add(current_block.blockNumber() + 1)
            if current_block == end_block:
                break
            current_block = current_block.next()
        
        self.selectionChangedSignal.emit(list(selected_lines))