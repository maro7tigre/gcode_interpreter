"""
Main entry point for the G-Code IDE application.
Initializes the Qt application, sets up the main window, and starts the event loop.
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """Initializes and runs the PySide6 application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
