@echo off
chcp 65001 >nul
setlocal

set "ABC_CANVAS_DIR=%~dp0"
cd /d "%ABC_CANVAS_DIR%"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHON_EXE=%ABC_CANVAS_DIR%..\..\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

title ABC Canvas
echo ABC Canvas starting...
echo URL: http://127.0.0.1:8790/
echo Log: %ABC_CANVAS_DIR%logs\abc_canvas.log
echo Access log: off
echo.

"%PYTHON_EXE%" -m uvicorn app:app --host 127.0.0.1 --port 8790 --no-access-log

echo.
echo ABC Canvas stopped.
pause
