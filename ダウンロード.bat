@echo off
setlocal
set "DIR=%~dp0"
cd /d "%DIR%"

if not exist "%DIR%.venv" (
  echo First-time setup has not been run yet.
  echo Please run the setup .bat file in this folder first.
  pause
  exit /b 2
)

chcp 65001 >nul
call "%DIR%.venv\Scripts\activate.bat"
python -X utf8 -m src.cli --interactive
endlocal
