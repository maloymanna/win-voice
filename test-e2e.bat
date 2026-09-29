@echo off
REM test-e2e.bat - Test read-aloud.py on the currently focused window.
REM
REM 1. Click the window where you want text read
REM    (e.g. Notepad with some text SELECTED).
REM 2. Do NOT click this console again.
REM 3. Wait for the countdown...

echo ===========================================
echo  Read Aloud - End-to-End Test
echo ===========================================
echo.
echo  1. Click the window where you want text read
echo     (e.g. Notepad with some text SELECTED).
echo  2. Do NOT click this console again.
echo  3. Wait for the countdown...
echo.
timeout /t 5 /nobreak >nul

echo Running read-aloud.py now...
echo.

"C:\Program Files\Python314\python.exe" "C:\Users\a123bc\read-aloud\read-aloud.py"

echo.
echo Script exited. Check above for any Python errors.
echo Press any key to close.
pause >nul
