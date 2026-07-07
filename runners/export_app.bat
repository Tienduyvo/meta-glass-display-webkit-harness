@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

echo Export an app + this build session into published\ (committable to GitHub).
set /p SLUG=App slug to export (blank = all registered apps):
set /p PW=Your app password to REDACT from the session (blank = none):
echo.
if "%PW%"=="" (
  %PY% tools\export_app.py %SLUG%
) else (
  %PY% tools\export_app.py %SLUG% --redact "%PW%"
)
echo.
pause
