@echo off
setlocal
cd /d "%~dp0.."
where npx >nul 2>nul || (echo Node.js / npx not found. Install Node.js first: https://nodejs.org & pause & exit /b 1)

rem Stateful, idempotent deploy — checks what's already set up (login, D1, password)
rem and only does the missing steps, then syncs + deploys. Logic lives in tools/deploy.py.
where py >nul 2>nul && (py -3 tools\deploy.py) || (python tools\deploy.py)

echo.
pause
