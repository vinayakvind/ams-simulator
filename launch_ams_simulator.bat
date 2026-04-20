@echo off
REM AMS Simulator Launcher
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python -m simulator.main
pause
