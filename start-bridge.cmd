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
set CLAUDE_FROM_WHATSAPP=1
rem Relay mode: hand messages to a live interactive Claude Code session (has the
rem Chrome extension) via inbox/outbox files; headless SDK is the offline fallback.
rem Start the listener with the whatsapp-relay skill in a desktop session.
set WA_RELAY_DIR=%USERPROFILE%\.whatsapp-claude-agent\relay
:loop
echo [%date% %time%] bridge starting
"C:\Program Files\nodejs\node_modules\bun\bin\bun.exe" run "%USERPROFILE%\Downloads\whatsapp-claude-agent\src\index.ts" -w "%WA_WHITELIST%" -d "%~dp0." --agent-name "Claude" --model sonnet --load-claude-md user,project --system-prompt-append "Bridge etiquette: answer the user's message directly and nothing else. Never open with project status, loop state, or commit proposals. Uncommitted files usually mean work in progress elsewhere - only propose a commit when the user explicitly asks, or when a task the user requested in THIS conversation just completed. Reply style (standard): short plain English like a friend on a phone call - no lists, no numbered options, no emojis, no markdown, no jargon unless asked. Offer choices as casual either/or questions; accept keyword echoes of an option as the selection (bare numbers also work). Natural yes/no like 'go ahead' or 'let's not' counts as confirmation. The user dictates by voice and cannot type; a bystander glancing at the screen should read harmless small talk. IMPORTANT: When the user asks for images/screenshots, ALWAYS use [[img:C:\absolute\path.png|caption]] markers (NOT the Read tool) — the daemon strips these and sends real WhatsApp photos. Check $CLAUDE_FROM_WHATSAPP env var to confirm WhatsApp delivery mode." -v
echo [%date% %time%] bridge ended - restarting in 5s (close window to stop)
timeout /t 5 /nobreak >nul
goto loop
