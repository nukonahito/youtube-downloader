@echo off
setlocal
set "DIR=%~dp0"
cd /d "%DIR%"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  echo Please install Python 3.10 or later from https://www.python.org/downloads/
  echo During setup, check the box "Add python.exe to PATH", then try again.
  exit /b 2
)

if not exist "%DIR%.venv" (
  echo First-time setup has not been run yet.
  echo Please run the setup .bat file in this folder first.
  exit /b 2
)

chcp 65001 >nul
call "%DIR%.venv\Scripts\activate.bat"
python -X utf8 -m src.cli %*
endlocal
