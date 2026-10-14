@echo off
rem Windows: double-click to start. A shortcut to this file in the Startup folder runs it at login.
cd /d "%~dp0"
".venv\Scripts\python.exe" main.py
pause
