@echo off
setlocal
cd /d "%~dp0.."
set "NAME=meta-glass-display-webkit-harness"
set "OUT=%~dp0setup_repo_out.txt"
where gh >nul 2>nul || (echo GitHub CLI ^(gh^) not found. Install it and run 'gh auth login' first. & pause & exit /b 1)

echo === PUBLISH %NAME% === > "%OUT%"
if exist ".git" rmdir /s /q ".git"
git init >> "%OUT%" 2>&1
git branch -M main >> "%OUT%" 2>&1
git add -A >> "%OUT%" 2>&1

echo --- secret / PII scan on STAGED files only (aborts on any hit) --- >> "%OUT%"
powershell -NoProfile -Command ^
  "$files=git ls-files; if(-not $files){Write-Output 'no staged files'; exit 1};" ^
  "$pat=@('[A-Za-z0-9._%%+-]+@(?!example\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}','(app_?password|passwd|secret|token|api_?key)\s*[:=]\s*[''\"][^''\"]{6,}','BEGIN (RSA|OPENSSH|EC) PRIVATE KEY','ghp_[A-Za-z0-9]{20,}','xox[baprs]-');" ^
  "$h=Select-String -Path $files -Pattern $pat -AllMatches -ErrorAction SilentlyContinue | Where-Object {$_.Line -notmatch 'REPLACE_WITH|example\.com'};" ^
  "if($h){$h | ForEach-Object { Write-Output ($_.Path+': '+$_.Line.Trim()) }; exit 1} else { Write-Output 'clean'; exit 0 }" >> "%OUT%" 2>&1
if errorlevel 1 ( echo SECRET/PII FOUND -- ABORT, nothing pushed. >> "%OUT%" & type "%OUT%" & pause & exit /b 1 )

echo --- gh repo create (public) + push --- >> "%OUT%"
git commit -m "meta-glass-display-webkit-harness: public template" >> "%OUT%" 2>&1
gh repo create %NAME% --public --source=. --remote=origin --push >> "%OUT%" 2>&1
echo --- mark as GitHub template (so others can "Use this template") --- >> "%OUT%"
gh repo edit --template >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- repo url --- >> "%OUT%"
gh repo view --json url -q .url >> "%OUT%" 2>&1
echo DONE >> "%OUT%"
type "%OUT%"
