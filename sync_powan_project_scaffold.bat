@echo off
chcp 65001 >nul
setlocal

set "ABC_CANVAS_DIR=%~dp0"
cd /d "%ABC_CANVAS_DIR%"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHON_EXE=%ABC_CANVAS_DIR%..\..\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" "%ABC_CANVAS_DIR%sync_powan_project_scaffold.py" %*
exit /b %ERRORLEVEL%
