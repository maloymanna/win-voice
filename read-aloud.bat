@echo off
REM read-aloud.bat - Windows wrapper for read-aloud.py
REM Place this file in the same folder as read-aloud.py or in your PATH.
REM Usage: read-aloud.bat

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=py.exe"

where py.exe >nul 2>nul
if errorlevel 1 (
    set "PYTHON_EXE=python.exe"
)

"%PYTHON_EXE%" "%SCRIPT_DIR%read-aloud.py" %*
