@echo off
title JARVIS (Mark LV) - Unrestricted System Controller - Developed by V I students
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo ========================================================
echo Starting JARVIS (Mark LV) - Developed by V I students
echo Mode: Full Unrestricted System Control Enabled
echo ========================================================

set "PY_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) else if exist "C:\Python312\python.exe" (
    set "PY_EXE=C:\Python312\python.exe"
) else if exist "C:\Users\hamad\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY_EXE=C:\Users\hamad\AppData\Local\Programs\Python\Python312\python.exe"
) else (
    set "PY_EXE=python.exe"
)

"%PY_EXE%" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo JARVIS exited with error code %ERRORLEVEL%.
    pause
)
