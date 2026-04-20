"""
Main entry point for the AMS Simulator GUI application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from simulator.gui.main_window import MainWindow


def main():
    """Launch the AMS Simulator GUI application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("AMS Simulator")
    app.setOrganizationName("AMS Simulator")
    app.setApplicationVersion("1.0.0")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start API server for VS Code integration
    try:
        from simulator.api.server import start_api_server
        api_server = start_api_server(window, port=5100)
        print("API server started on http://127.0.0.1:5100")
    except Exception as e:
        print(f"Warning: Could not start API server: {e}")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
