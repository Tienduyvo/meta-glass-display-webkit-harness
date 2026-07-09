@echo off
REM Code-driven build loop: recomputes the loop state each pass and hands the agent ONE
REM transition per pass. Stops at DONE or the COMMIT user gate. See tools/loop_runner.py.
cd /d "%~dp0.."
python tools\loop_runner.py %*
pause
