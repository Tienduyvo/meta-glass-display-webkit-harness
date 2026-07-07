@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
where npx >nul 2>nul || (echo Node.js / npx not found. Install Node.js first: https://nodejs.org & pause & exit /b 1)

echo === Sync app configs into worker\public ===
%PY% tools\sync_public.py
echo.
echo === Deploy the Worker (frontend + API) ===
cd worker
call npx wrangler deploy
echo.
echo Done. Your launcher + apps are live at your https://*.workers.dev URL.
pause
