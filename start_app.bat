@echo off
echo Starting Drone Controller Application...
call venv\Scripts\activate
start "" npm start
echo Application started. Check for the Electron window.
pause
