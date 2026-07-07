@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% tools\new_app.py
echo.
pause
