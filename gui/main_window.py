"""
The main window for the G-Code IDE application.
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QFileDialog, QMessageBox, QTextEdit,
                               QSplitter, QLabel)
from PySide6.QtCore import Qt
from .editor import Editor
from .viewport import Viewport
from core.simulation_controller import SimulationController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Code IDE and Simulator")
        self.setGeometry(100, 100, 1200, 800)

        self.controller = SimulationController()

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        top_layout = QVBoxLayout(main_widget)

        # Top controls
        controls_layout = QHBoxLayout()
        self.load_button = QPushButton("Load G-Code File")
        self.simulate_button = QPushButton("Simulate Current Code")
        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.simulate_button)
        controls_layout.addStretch()
        top_layout.addLayout(controls_layout)

        # Main vertical splitter for workspace and console
        main_splitter = QSplitter(Qt.Vertical)
        top_layout.addWidget(main_splitter)

        # Top pane widget for the horizontal splitter
        top_pane = QWidget()
        top_pane_layout = QVBoxLayout(top_pane)
        top_pane_layout.setContentsMargins(0,0,0,0)
        
        # Horizontal splitter for Editor and Viewport
        workspace_splitter = QSplitter(Qt.Horizontal)
        top_pane_layout.addWidget(workspace_splitter)

        # Editor
        self.editor = Editor()
        workspace_splitter.addWidget(self.editor)

        # Viewport
        self.viewport = Viewport()
        workspace_splitter.addWidget(self.viewport)
        
        # Bottom pane for the console
        bottom_pane = QWidget()
        bottom_pane_layout = QVBoxLayout(bottom_pane)
        bottom_pane_layout.setContentsMargins(0,0,0,0)
        bottom_pane_layout.addWidget(QLabel("Errors and Messages:"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        bottom_pane_layout.addWidget(self.console)

        # Add panes to the main vertical splitter
        main_splitter.addWidget(top_pane)
        main_splitter.addWidget(bottom_pane)

        # Set initial splitter sizes
        workspace_splitter.setSizes([600, 600])
        main_splitter.setSizes([650, 150])

        # Connect signals
        self.load_button.clicked.connect(self.load_gcode)
        self.simulate_button.clicked.connect(self.simulate_gcode)
        self.editor.selectionChangedSignal.connect(self.on_editor_selection_changed)

    def load_gcode(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open G-Code File", "", "G-Code Files (*.ngc *.gcode *.nc);;All Files (*)")
        if file_path:
            lines, error = self.controller.load_gcode_file(file_path)
            if lines is not None:
                self.editor.setPlainText("".join(lines))
                self.console.clear()
                self.simulate_gcode() # Automatically simulate after loading
            else:
                QMessageBox.critical(self, "Error", f"Failed to load file: {error}")

    def simulate_gcode(self):
        """Simulates the text currently in the editor."""
        current_code = self.editor.toPlainText().splitlines(True) # Keep line endings
        ok, error = self.controller.run_simulation(current_code)
        if ok:
            self.viewport.set_path(self.controller.canonical_commands)
            if self.controller.errors:
                self.console.setText("\n".join(self.controller.errors))
            else:
                self.console.setText("Simulation successful.")
        else:
            QMessageBox.critical(self, "Error", f"Simulation failed: {error}")

    def on_editor_selection_changed(self, selected_lines):
        self.viewport.highlight_path_segments(selected_lines)
