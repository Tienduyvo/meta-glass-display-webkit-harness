@echo off
setlocal
cd /d "%~dp0..\worker"
where npx >nul 2>nul || (echo Node.js / npx not found. Install Node.js first: https://nodejs.org & pause & exit /b 1)

echo ==================================================
echo   Deploy the CRUD Worker to Cloudflare (D1)
echo ==================================================
echo This guides you through: login, create D1, apply schema, set API_SECRET, deploy.
echo You need a (free) Cloudflare account.
echo.
pause
call npx wrangler login
echo.
echo --- creating D1 database "glass_crud" ---
call npx wrangler d1 create glass_crud
echo.
echo ^>^>^> Copy the printed database_id into  worker\wrangler.toml  (d1_databases.database_id),
echo      SAVE the file, then press any key to continue.
pause
echo --- applying schema.sql ---
call npx wrangler d1 execute glass_crud --remote --file=schema.sql
echo.
echo --- set your APP PASSWORD (this secures the app; you'll type it once in the launcher) ---
echo     Choose a strong password you can remember. Keep it private.
call npx wrangler secret put API_SECRET
echo.
echo --- syncing app configs into public\ ---
where py >nul 2>nul && (py -3 ..\tools\sync_public.py) || (python ..\tools\sync_public.py)
echo --- deploying ---
call npx wrangler deploy
echo.
echo Done. Open the printed  https://glass-crud-api.*.workers.dev  URL — the Worker serves the
echo   launcher itself. Enter your password once; for glasses register  ...workers.dev/#glass&t=PASSWORD
pause
