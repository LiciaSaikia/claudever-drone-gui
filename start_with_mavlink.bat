@echo off
echo Starting Drone Controller with MAVLink Parser...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Start MAVLink parser in background
echo Starting MAVLink parser on port 14550...
start /B python src\python\mavlink_parser.py 14550 14551

REM Wait a moment for parser to start
timeout /t 3 /nobreak > nul

REM Start Electron app
echo Starting Electron application...
npm start

echo.
echo Application started. Check for windows to open.
pause