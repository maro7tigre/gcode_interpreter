"""
The main window for the G-Code IDE application.
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QFileDialog, QMessageBox, QTextEdit,
                               QSplitter, QLabel, QComboBox)
from PySide6.QtCore import Qt
from .editor import Editor
from .viewport import Viewport
from core.simulation_controller import SimulationController
from dialects.linuxcnc_dialect import LinuxCNCDialect
from dialects.num_dialect import NUMDialect
from interpreters.linuxcnc_interpreter import LinuxCNCInterpreter
from interpreters.num_interpreter import NUMInterpreter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Code IDE and Simulator")
        self.setGeometry(100, 100, 1400, 900)

        # --- Dialect and Interpreter Management ---
        self.dialects = {
            "LinuxCNC": LinuxCNCDialect(),
            "NUM 1060 M": NUMDialect()
        }
        self.interpreters = {
            "LinuxCNC": LinuxCNCInterpreter(self.dialects["LinuxCNC"]),
            "NUM 1060 M": NUMInterpreter(self.dialects["NUM 1060 M"])
        }
        self.controller = SimulationController()
        self.controller.interpreter = self.interpreters["LinuxCNC"] # Default

        # --- GUI Setup ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        top_layout = QVBoxLayout(main_widget)

        # Top controls
        controls_layout = QHBoxLayout()
        self.load_button = QPushButton("Load G-Code File")
        self.simulate_button = QPushButton("Simulate Current Code")
        
        self.dialect_selector = QComboBox()
        self.dialect_selector.addItems(self.dialects.keys())
        
        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.simulate_button)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Controller Dialect:"))
        controls_layout.addWidget(self.dialect_selector)
        top_layout.addLayout(controls_layout)

        # Main vertical splitter
        main_splitter = QSplitter(Qt.Vertical)
        top_layout.addWidget(main_splitter)

        top_pane = QWidget()
        top_pane_layout = QVBoxLayout(top_pane)
        top_pane_layout.setContentsMargins(0,0,0,0)
        
        workspace_splitter = QSplitter(Qt.Horizontal)
        top_pane_layout.addWidget(workspace_splitter)

        self.editor = Editor()
        workspace_splitter.addWidget(self.editor)

        self.viewport = Viewport()
        workspace_splitter.addWidget(self.viewport)
        
        bottom_pane = QWidget()
        bottom_pane_layout = QVBoxLayout(bottom_pane)
        bottom_pane_layout.setContentsMargins(0,0,0,0)
        bottom_pane_layout.addWidget(QLabel("Errors and Messages:"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        bottom_pane_layout.addWidget(self.console)

        main_splitter.addWidget(top_pane)
        main_splitter.addWidget(bottom_pane)

        workspace_splitter.setSizes([700, 700])
        main_splitter.setSizes([750, 150])

        # --- Connect signals ---
        self.load_button.clicked.connect(self.load_gcode)
        self.simulate_button.clicked.connect(self.simulate_gcode)
        self.editor.selectionChangedSignal.connect(self.on_editor_selection_changed)
        self.dialect_selector.currentTextChanged.connect(self.on_dialect_changed)

    def on_dialect_changed(self, dialect_name):
        if dialect_name in self.interpreters:
            self.controller.interpreter = self.interpreters[dialect_name]
            print(f"Switched to {dialect_name} interpreter.")
            self.simulate_gcode()

    def load_gcode(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open G-Code File", "", "G-Code Files (*.ngc *.gcode *.nc);;All Files (*)")
        if file_path:
            lines, error = self.controller.load_gcode_file(file_path)
            if lines is not None:
                self.editor.setPlainText("".join(lines))
                self.console.clear()
                self.simulate_gcode()
            else:
                QMessageBox.critical(self, "Error", f"Failed to load file: {error}")

    def simulate_gcode(self):
        current_code = self.editor.toPlainText().splitlines()
        self.controller.run_simulation(current_code)
        
        self.console.clear()
        if self.controller.errors:
            self.console.setText("\n".join(self.controller.errors))
        else:
            self.console.setText("Simulation successful.")
        
        self.viewport.set_path(self.controller.canonical_commands)

    def on_editor_selection_changed(self, selected_lines):
        self.viewport.highlight_path_segments(selected_lines)
