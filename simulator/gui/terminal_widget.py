"""
Terminal widget for running CLI commands within the GUI.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette
import os


class TerminalWidget(QWidget):
    """
    Integrated terminal widget for running CLI commands.
    """
    
    command_finished = pyqtSignal(int)  # Exit code
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._process = None
        self._command_history = []
        self._history_index = -1
        
        self._setup_ui()
        self._setup_process()
    
    def _setup_ui(self):
        """Setup the terminal UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.quick_commands = QComboBox()
        self.quick_commands.addItems([
            "Select command...",
            "DC Analysis",
            "AC Analysis", 
            "Transient Analysis",
            "Digital Simulation",
            "Batch Simulation",
            "Help",
        ])
        self.quick_commands.currentTextChanged.connect(self._on_quick_command)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_output)
        
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._stop_process)
        
        toolbar.addWidget(QLabel("Quick Commands:"))
        toolbar.addWidget(self.quick_commands)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(stop_btn)
        
        layout.addLayout(toolbar)
        
        # Output display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Consolas", 9))
        
        # Dark terminal theme
        palette = self.output_display.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        self.output_display.setPalette(palette)
        
        layout.addWidget(self.output_display)
        
        # Command input
        input_layout = QHBoxLayout()
        
        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        self.command_input = QLineEdit()
        self.command_input.setFont(QFont("Consolas", 9))
        self.command_input.returnPressed.connect(self._execute_command)
        self.command_input.setPlaceholderText("Enter command (e.g., ams-sim --netlist circuit.spice --analysis dc)")
        
        # Install event filter for history navigation
        self.command_input.installEventFilter(self)
        
        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.command_input)
        
        layout.addLayout(input_layout)
        
        # Welcome message
        self._append_output("=== AMS Simulator Terminal ===", color="#4CAF50")
        self._append_output("Type commands or use Quick Commands dropdown above.")
        self._append_output("Examples:")
        self._append_output("  ams-sim --netlist circuit.spice --analysis dc")
        self._append_output("  ams-batch --dir ./netlists --analysis transient")
        self._append_output("  python -m simulator.cli.runner --help")
        self._append_output("")
    
    def _setup_process(self):
        """Setup the QProcess for command execution."""
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_process_finished)
        
        # Set environment - use setProcessEnvironment in PyQt6
        env = QProcess.systemEnvironment()
        # Add virtual environment to PATH
        venv_path = os.path.join(os.getcwd(), '.venv', 'Scripts')
        if os.path.exists(venv_path):
            for i, item in enumerate(env):
                if item.upper().startswith('PATH='):
                    env[i] = f"PATH={venv_path};{item[5:]}"
                    break
            else:
                env.append(f"PATH={venv_path};{os.environ.get('PATH', '')}")
        
        from PyQt6.QtCore import QProcessEnvironment
        process_env = QProcessEnvironment()
        for item in env:
            if '=' in item:
                key, value = item.split('=', 1)
                process_env.insert(key, value)
        self._process.setProcessEnvironment(process_env)
    
    def _execute_command(self):
        """Execute the command entered in the input field."""
        command = self.command_input.text().strip()
        if not command:
            return
        
        # Add to history
        self._command_history.append(command)
        self._history_index = len(self._command_history)
        
        # Display command
        self._append_output(f"$ {command}", color="#4CAF50", bold=True)
        
        # Clear input
        self.command_input.clear()
        
        # Handle built-in commands
        if command.lower() in ['clear', 'cls']:
            self._clear_output()
            return
        elif command.lower() == 'exit':
            self._append_output("Use the GUI to close the application.", color="#FFC107")
            return
        
        # Execute command
        if self._process.state() == QProcess.ProcessState.Running:
            self._append_output("Error: A command is already running. Use Stop button first.", color="#F44336")
            return
        
        # Handle Python module commands
        python_exe = os.path.join(os.getcwd(), '.venv', 'Scripts', 'python.exe')
        
        # Build proper command list for QProcess
        if command.startswith('ams-sim '):
            # Replace ams-sim with python -m simulator.cli.runner
            args = command[8:].strip().split()
            self._process.start(python_exe, ['-m', 'simulator.cli.runner'] + args)
        elif command.startswith('ams-batch '):
            # Replace ams-batch with python -m simulator.cli.batch
            args = command[10:].strip().split()
            self._process.start(python_exe, ['-m', 'simulator.cli.batch'] + args)
        elif command.startswith('python -m '):
            # Handle python -m commands
            args = command[10:].strip().split()
            self._process.start(python_exe, ['-m'] + args)
        else:
            # Use shell for other commands
            self._process.start('powershell', ['-NoProfile', '-Command', command])
        
        if not self._process.waitForStarted():
            self._append_output(f"Error: Failed to start command", color="#F44336")
    
    def _on_stdout(self):
        """Handle stdout from the process."""
        data = self._process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        self._append_output(data, newline=False)
    
    def _on_stderr(self):
        """Handle stderr from the process."""
        data = self._process.readAllStandardError().data().decode('utf-8', errors='ignore')
        self._append_output(data, color="#F44336", newline=False)
    
    def _on_process_finished(self, exit_code, exit_status):
        """Handle process completion."""
        if exit_code == 0:
            self._append_output(f"\nCommand completed successfully (exit code: {exit_code})", color="#4CAF50")
        else:
            self._append_output(f"\nCommand failed with exit code: {exit_code}", color="#F44336")
        
        self.command_finished.emit(exit_code)
    
    def _stop_process(self):
        """Stop the running process."""
        if self._process.state() == QProcess.ProcessState.Running:
            self._process.kill()
            self._append_output("\nProcess terminated by user", color="#FFC107")
    
    def _clear_output(self):
        """Clear the output display."""
        self.output_display.clear()
        self._append_output("=== Terminal Cleared ===", color="#4CAF50")
    
    def _append_output(self, text, color=None, bold=False, newline=True):
        """Append text to the output display."""
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if color:
            html = f'<span style="color: {color}'
            if bold:
                html += '; font-weight: bold'
            html += f'">{text}</span>'
            if newline:
                html += '<br>'
            cursor.insertHtml(html)
        else:
            cursor.insertText(text)
            if newline:
                cursor.insertText('\n')
        
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
    
    def _on_quick_command(self, command_text):
        """Handle quick command selection."""
        if command_text == "Select command...":
            return
        
        # Reset combo box
        self.quick_commands.setCurrentIndex(0)
        
        # Map to actual commands
        command_map = {
            "DC Analysis": "ams-sim --netlist circuit.spice --analysis dc --verbose",
            "AC Analysis": "ams-sim --netlist circuit.spice --analysis ac --fstart 1 --fstop 1e6",
            "Transient Analysis": "ams-sim --netlist circuit.spice --analysis transient --tstop 1e-6 --tstep 1e-9",
            "Digital Simulation": "ams-sim --netlist circuit.v --analysis digital --max-time 1000",
            "Batch Simulation": "ams-batch --dir ./netlists --analysis dc --workers 4",
            "Help": "python -m simulator.cli.runner --help",
        }
        
        if command_text in command_map:
            self.command_input.setText(command_map[command_text])
            self.command_input.setFocus()
    
    def eventFilter(self, obj, event):
        """Event filter for command history navigation."""
        if obj == self.command_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                # Previous command
                if self._history_index > 0:
                    self._history_index -= 1
                    self.command_input.setText(self._command_history[self._history_index])
                return True
            elif event.key() == Qt.Key.Key_Down:
                # Next command
                if self._history_index < len(self._command_history) - 1:
                    self._history_index += 1
                    self.command_input.setText(self._command_history[self._history_index])
                elif self._history_index == len(self._command_history) - 1:
                    self._history_index = len(self._command_history)
                    self.command_input.clear()
                return True
        
        return super().eventFilter(obj, event)
    
    def execute_command_directly(self, command: str):
        """Execute a command programmatically."""
        self.command_input.setText(command)
        self._execute_command()
