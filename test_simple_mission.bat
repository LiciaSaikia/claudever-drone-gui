@echo off
echo Testing Simple UDP Mission Controller...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Run the simple mission script directly
echo Starting simple mission script...
python src\python\simple_udp_mission.py

echo.
echo Test completed.
pause