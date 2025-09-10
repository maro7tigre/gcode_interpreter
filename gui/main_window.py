"""
The main window for the G-Code IDE application.
Updated to use the new G-code interpreter system.
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QFileDialog, QMessageBox, QTextEdit,
                               QSplitter, QLabel, QComboBox, QProgressBar)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCharFormat, QColor, QFont
from .editor import Editor
from .viewport import Viewport
from gcode_processor import GCodeProcessor
from config.machine_config import ConfigManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Code IDE and Simulator")
        self.setGeometry(100, 100, 1600, 1000)

        # Initialize G-code processor
        self.processor = GCodeProcessor()
        self.current_config = ConfigManager.get_config("mill_3axis")
        
        # Auto-update timer for real-time syntax checking
        self.syntax_timer = QTimer()
        self.syntax_timer.setSingleShot(True)
        self.syntax_timer.timeout.connect(self.check_syntax)

        self.setup_ui()
        self.connect_signals()
        
        # Load sample G-code for demonstration
        self.load_sample_gcode()

    def setup_ui(self):
        """Set up the user interface."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Load G-Code File")
        self.save_button = QPushButton("Save G-Code")
        self.process_button = QPushButton("Process G-Code")
        
        # Machine configuration selector
        self.machine_selector = QComboBox()
        self.machine_selector.addItems(["mill_3axis", "mill_5axis", "lathe", "plasma"])
        
        # Processing status
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addWidget(self.process_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(QLabel("Machine Type:"))
        toolbar_layout.addWidget(self.machine_selector)
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(toolbar_layout)

        # Main content area
        main_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(main_splitter)

        # Top pane with editor and viewport
        top_pane = QWidget()
        top_layout = QVBoxLayout(top_pane)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        workspace_splitter = QSplitter(Qt.Horizontal)
        top_layout.addWidget(workspace_splitter)

        # Editor with enhanced features
        self.editor = Editor()
        workspace_splitter.addWidget(self.editor)

        # 3D viewport
        self.viewport = Viewport()
        workspace_splitter.addWidget(self.viewport)
        
        # Information panel
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        # Statistics display
        self.stats_label = QLabel("Statistics:\nNo G-code processed")
        self.stats_label.setFont(QFont("Courier", 9))
        self.stats_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        info_layout.addWidget(self.stats_label)
        
        workspace_splitter.addWidget(info_panel)

        # Bottom pane with console and errors
        bottom_pane = QWidget()
        bottom_layout = QVBoxLayout(bottom_pane)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        console_splitter = QSplitter(Qt.Horizontal)
        bottom_layout.addWidget(console_splitter)
        
        # Error console
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setContentsMargins(0, 0, 0, 0)
        error_layout.addWidget(QLabel("Errors and Warnings:"))
        
        self.error_console = QTextEdit()
        self.error_console.setReadOnly(True)
        self.error_console.setMaximumHeight(150)
        error_layout.addWidget(self.error_console)
        console_splitter.addWidget(error_widget)
        
        # General console
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.addWidget(QLabel("Console Output:"))
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        console_layout.addWidget(self.console)
        console_splitter.addWidget(console_widget)

        main_splitter.addWidget(top_pane)
        main_splitter.addWidget(bottom_pane)

        # Set initial sizes
        workspace_splitter.setSizes([600, 600, 200])
        console_splitter.setSizes([400, 400])
        main_splitter.setSizes([800, 200])

    def connect_signals(self):
        """Connect all signal handlers."""
        self.load_button.clicked.connect(self.load_gcode_file)
        self.save_button.clicked.connect(self.save_gcode_file)
        self.process_button.clicked.connect(self.process_gcode)
        self.machine_selector.currentTextChanged.connect(self.change_machine_config)
        self.editor.selectionChangedSignal.connect(self.on_editor_selection_changed)
        self.editor.textChanged.connect(self.on_text_changed)

    def load_sample_gcode(self):
        """Load a sample G-code program for demonstration."""
        sample_gcode = """G21 G90 G94 ; Metric, absolute, feed rate mode
G0 X0 Y0 Z5 ; Rapid to start position
G1 Z0 F1000 ; Plunge to work surface
G1 X10 Y0 F2000 ; Linear move
G2 X20 Y10 I10 J0 ; Clockwise arc
G1 X30 Y10 ; Another linear move
G3 X40 Y0 I5 J-5 ; Counterclockwise arc
G0 Z5 ; Rapid retract
G0 X0 Y0 ; Return to origin
M30 ; Program end"""
        
        self.editor.setPlainText(sample_gcode)
        self.process_gcode()

    def load_gcode_file(self):
        """Load G-code from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open G-Code File", "", 
            "G-Code Files (*.ngc *.gcode *.nc *.txt);;All Files (*)"
        )
        
        if file_path:
            with open(file_path, 'r') as f:
                content = f.read()
            self.editor.setPlainText(content)
            self.console.append(f"Loaded: {file_path}")
            self.process_gcode()

    def save_gcode_file(self):
        """Save current G-code to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save G-Code File", "", 
            "G-Code Files (*.ngc);;All Files (*)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.editor.toPlainText())
            self.console.append(f"Saved: {file_path}")

    def change_machine_config(self, machine_type):
        """Change the machine configuration."""
        self.current_config = ConfigManager.get_config(machine_type)
        self.console.append(f"Switched to {self.current_config.name}")
        # Reprocess with new configuration
        if self.editor.toPlainText().strip():
            self.process_gcode()

    def process_gcode(self):
        """Process the current G-code and update displays."""
        gcode_text = self.editor.toPlainText()
        if not gcode_text.strip():
            return

        self.status_label.setText("Processing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Reset processor
        self.processor.reset()
        
        # Process the G-code
        success = self.processor.process_gcode(gcode_text)
        
        # Update error display
        self.update_error_display()
        
        # Update statistics
        self.update_statistics()
        
        # Update viewport with geometry
        if success or not self.processor.has_fatal_errors():
            self.update_viewport()
        
        # Update status
        if success:
            self.status_label.setText("Processing complete")
            self.console.append("G-code processed successfully")
        else:
            self.status_label.setText("Processing completed with errors")
            self.console.append("G-code processed with errors")
                
        self.progress_bar.setVisible(False)

    def update_error_display(self):
        """Update the error console with current errors."""
        errors = self.processor.get_all_errors()
        
        if not errors:
            self.error_console.setText("No errors found.")
            # Clear error highlighting
            self.editor.clear_error_highlights()
            return
        
        # Group errors by line
        error_text = []
        error_lines = set()
        
        for error in errors:
            severity = error.severity.value.upper()
            error_text.append(f"Line {error.line_number}: [{severity}] {error.message}")
            error_lines.add(error.line_number)
        
        self.error_console.setText("\n".join(error_text))
        
        # Highlight error lines in editor
        self.editor.highlight_error_lines(list(error_lines))

    def update_statistics(self):
        """Update the statistics display."""
        stats = self.processor.get_statistics()
        
        stats_text = f"""Statistics:
Total Lines: {stats['processing']['total_lines']}
Blocks: {stats['processing']['total_blocks']}
Errors: {stats['processing']['errors']}
Warnings: {stats['processing']['warnings']}

Toolpath:
Total Length: {stats['geometry']['total_length']:.2f}
Feed Length: {stats['geometry']['feed_length']:.2f}
Rapid Length: {stats['geometry']['rapid_length']:.2f}
Total Segments: {stats['geometry']['total_segments']}

Machine State:
Current Tool: T{stats['machine_state']['current_tool']}
Feed Rate: {stats['machine_state']['feed_rate']}
Spindle Speed: {stats['machine_state']['spindle_speed']}"""
        
        self.stats_label.setText(stats_text)

    def update_viewport(self):
        """Update the 3D viewport with current geometry."""
        geometry_segments = self.processor.get_all_geometry()
        self.viewport.set_geometry(geometry_segments)

    def on_editor_selection_changed(self, selected_lines):
        """Handle editor selection changes."""
        # Highlight corresponding geometry in viewport
        self.viewport.highlight_lines(selected_lines)

    def on_text_changed(self):
        """Handle text changes in editor for real-time syntax checking."""
        # Restart the syntax check timer
        self.syntax_timer.stop()
        self.syntax_timer.start(500)  # Check syntax 500ms after typing stops

    def check_syntax(self):
        """Perform real-time syntax checking."""
        gcode_text = self.editor.toPlainText()
        if not gcode_text.strip():
            return
        
        # Quick syntax validation without full processing
        is_valid = self.processor.validate_syntax(gcode_text)
        
        if not is_valid:
            errors = self.processor.get_all_errors()
            error_lines = [error.line_number for error in errors 
                          if error.severity.value in ['error', 'fatal']]
            self.editor.highlight_error_lines(error_lines)
        else:
            self.editor.clear_error_highlights()

    def on_viewport_selection_changed(self, segment_ids):
        """Handle geometry selection in viewport (if implemented)."""
        # Find lines that generated these segments
        lines_to_highlight = []
        for segment_id in segment_ids:
            line_num = self.processor.get_line_for_geometry(segment_id)
            if line_num:
                lines_to_highlight.append(line_num)
        
        if lines_to_highlight:
            self.editor.highlight_lines(lines_to_highlight)