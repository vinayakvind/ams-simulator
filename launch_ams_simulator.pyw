"""
AMS Simulator GUI Launcher - Windows no-console version
Double-click this file to launch the AMS Simulator GUI.
The integrated terminal widget provides CLI access within the application.
"""
import sys
import os
import subprocess

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Determine the Python executable
# First try virtual environment
python_exe = os.path.join(script_dir, '.venv', 'Scripts', 'python.exe')

# Fall back to system Python if venv doesn't exist
if not os.path.exists(python_exe):
    python_exe = sys.executable

# Set environment to ensure proper paths
env = os.environ.copy()
env['PYTHONPATH'] = script_dir

# Launch the simulator
try:
    subprocess.Popen(
        [python_exe, '-m', 'simulator.main'],
        cwd=script_dir,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    )
except Exception as e:
    # Show error message if something goes wrong
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Launch Error", f"Failed to launch AMS Simulator:\n{str(e)}")
    except:
        pass

