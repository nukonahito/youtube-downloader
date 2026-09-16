@echo off
setlocal
set "DIR=%~dp0"
cd /d "%DIR%"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  echo Please install Python 3.10 or later from https://www.python.org/downloads/
  echo During setup, check the box "Add python.exe to PATH", then run this again.
  pause
  exit /b 1
)

chcp 65001 >nul
python -X utf8 -m src.setup_wizard
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
