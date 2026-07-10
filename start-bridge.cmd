@echo off
rem Claude WhatsApp Bridge — patched fork of whatsapp-claude-agent (adds [[img:...]] markers
rem so Claude can send images). Fork lives in ..\whatsapp-claude-agent, runs from source.
rem Private config (owner numbers) comes from %USERPROFILE%\.bridge-env.cmd — never commit
rem numbers into this file. Close this window to stop the bridge.
title Claude WhatsApp Bridge
cd /d "%~dp0"
if not exist "%USERPROFILE%\.bridge-env.cmd" (
  echo Missing %USERPROFILE%\.bridge-env.cmd - create it with: set WA_WHITELIST=+49...,LID
  pause
  exit /b 1
)
call "%USERPROFILE%\.bridge-env.cmd"
:loop
echo [%date% %time%] bridge starting
"C:\Program Files\nodejs\node_modules\bun\bin\bun.exe" run "%USERPROFILE%\Downloads\whatsapp-claude-agent\src\index.ts" -w "%WA_WHITELIST%" -d "%~dp0." --agent-name "Claude" --model sonnet --load-claude-md user,project --system-prompt-append "Bridge etiquette: answer the user's message directly and nothing else. Never open with project status, loop state, or commit proposals. Uncommitted files usually mean work in progress elsewhere - only propose a commit when the user explicitly asks, or when a task the user requested in THIS conversation just completed. Keep replies short and dictation-friendly: selections as bare numbers, confirmations as ja/nein." -v
echo [%date% %time%] bridge ended - restarting in 5s (close window to stop)
timeout /t 5 /nobreak >nul
goto loop
