"""
Create a desktop shortcut for AMS Simulator
"""
import os
import sys
import subprocess
from pathlib import Path
from win32com.client import Dispatch

# Get paths
simulator_dir = Path(__file__).parent.absolute()
python_exe = simulator_dir / '.venv' / 'Scripts' / 'pythonw.exe'
launcher_script = simulator_dir / 'launch_ams_simulator.pyw'

# Desktop path - use shell:desktop to get the REAL desktop (handles OneDrive redirection)
try:
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', "[Environment]::GetFolderPath('Desktop')"],
        capture_output=True, text=True
    )
    desktop = Path(result.stdout.strip())
except Exception:
    desktop = Path.home() / 'Desktop'

# Fallback: also try OneDrive desktop
if not desktop.exists():
    onedrive_desktop = Path.home() / 'OneDrive' / 'Desktop'
    if onedrive_desktop.exists():
        desktop = onedrive_desktop

shortcut_path = desktop / 'AMS Simulator.lnk'

# Create shortcut using win32com
shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(str(shortcut_path))
shortcut.Targetpath = str(python_exe)
shortcut.Arguments = f'"{launcher_script}"'
shortcut.WorkingDirectory = str(simulator_dir)
shortcut.Description = 'AMS Simulator - Analog Mixed Signal Circuit Simulator'
shortcut.IconLocation = str(python_exe)
shortcut.save()

print(f"✓ Desktop shortcut created: {shortcut_path}")
print("You can now launch AMS Simulator from your desktop!")
