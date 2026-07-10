@echo off
rem Claude WhatsApp Remote — the ONE launcher. Starts the bridge daemon in its own
rem minimized window if it is not already running, then opens the interactive relay
rem session with /whatsapp-relay pre-typed (Chrome extension, Gmail, windows-mcp).
rem Closing this window stops only the relay — the bridge keeps answering headless.
rem Close the minimized "Claude WhatsApp Bridge" window to stop the daemon too.
title Claude WhatsApp Relay Listener
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "exit [int]!(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'bun.exe' -and $_.CommandLine -like '*whatsapp-claude-agent*' })"
if errorlevel 1 (
  echo Starting WhatsApp bridge daemon in a minimized window...
  start "Claude WhatsApp Bridge" /min "%~dp0start-bridge.cmd"
) else (
  echo Bridge daemon already running.
)
claude "/whatsapp-relay"
