@echo off
setlocal

set ROOT=C:\Users\Apps\voiceassistant
set PY=C:\Program Files\Python314\python.exe
set MODEL_DIR=%ROOT%\models
set MODEL_FILE=%MODEL_DIR%\ggml-tiny.en.bin
set MODEL_URL=https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin

echo === Voice Assistant Setup ===

if not exist "%ROOT%"        mkdir "%ROOT%"
if not exist "%ROOT%\temp"   mkdir "%ROOT%\temp"
if not exist "%ROOT%\logs"   mkdir "%ROOT%\logs"
if not exist "%MODEL_DIR%"   mkdir "%MODEL_DIR%"

echo.
echo [1/2] Installing Python dependencies...
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r "%ROOT%\requirements.txt"

echo.
echo [2/2] Downloading whisper tiny.en model (about 75 MB)...
if exist "%MODEL_FILE%" (
    echo     already present, skipping.
) else (
    curl -L "%MODEL_URL%" -o "%MODEL_FILE%"
)

echo.
echo Done. Edit CONFIG at the top of assistant.py if any paths differ.
pause