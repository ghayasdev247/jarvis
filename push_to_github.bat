@echo off
title JARVIS GitHub Auto-Sync
cd /d "%~dp0"
echo ========================================================
echo               JARVIS GITHUB AUTO-SYNC
echo ========================================================
echo.
echo [1/3] Checking git status and staging changes...
git status --short
git add .
echo.
echo [2/3] Creating commit with timestamp...
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set dt=%%I
if defined dt (
    set TIMESTAMP=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%:%dt:~12,2%
) else (
    set TIMESTAMP=%date% %time%
)
git commit -m "JARVIS update: %TIMESTAMP%"
echo.
echo [3/3] Pushing to GitHub (origin main)...
git push -u origin main
echo.
echo ========================================================
echo GitHub Sync Complete!
echo ========================================================
timeout /t 5
