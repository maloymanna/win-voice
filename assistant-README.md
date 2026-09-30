# Voice Assistant (local, whisper.cpp + Piper)

Hotkey-driven local STT/TTS. No cloud. Clipboard + speaker output.

## Requirements
- Windows 11
- Python 3.14 at `C:\Program Files\Python314\python.exe`
- AutoHotkey v2
- whisper.cpp binaries in `C:\Users\myuser\dev\whisper-bin` (specifically `whisper-cli.exe`)
- Piper at `...\Scripts\piper.exe`
- Piper voice `en_US-lessac-medium.onnx` (+ `.onnx.json`) in `C:\Users\myuser\pipervoices`

## One-time setup
1. Copy all files to `C:\Users\Apps\voiceassistant`.
2. Double-click `setup.bat`. It will:
   - `pip install sounddevice numpy winotify pyperclip`
   - Download `ggml-tiny.en.bin` into `models\`
3. Open your existing AutoHotkey v2 file, append the snippet below, save, reload.

## PATH / ENV — IMPORTANT
**Do NOT add `whisper-bin` to your global PATH.**
Your existing `whisper` command on PATH resolves to the **openai-whisper Python package**, which is *not* what this assistant uses. `assistant.py` calls `whisper-cli.exe` by **absolute path** from `CONFIG`, so the global PATH is irrelevant to it — but if you add `whisper-bin` to PATH, it may shadow or be shadowed depending on order and cause confusion in other tools.

If you ever want to use `whisper-cli` from Git Bash interactively, do it per-shell:
```bash
export PATH="/c/Users/myuser/dev/whisper-bin:$PATH"
whisper-cli -m /c/Users/Apps/voiceassistant/models/ggml-tiny.en.bin -f audio.wav
```
…and simply close that terminal to revert. Do not persist it.

## Usage
- **Win+W** → echo mode: record, transcribe, copy to clipboard, speak back.
- **Win+C** → stt mode: record, transcribe, copy to clipboard only.
- Press the *same* hotkey a second time to stop recording early.
- Say **"stop"** (or cancel / halt / nevermind) while recording to abort.
- Recording auto-stops at **30 seconds**.

A toast notification appears when recording starts and when it finishes.

## Tuning (edit CONFIG at top of assistant.py)
| Key | Meaning |
|---|---|
| `whisper_bin` | full path to `whisper-cli.exe` |
| `whisper_model` | full path to `ggml-tiny.en.bin` (swap for base/small here) |
| `whisper_threads` | CPU threads for whisper (4 is a safe default) |
| `piper_exe` / `piper_voice` | Piper binary + voice |
| `max_seconds` | safety cap (default 30) |
| `sleepwords` | list of abort words |
| `sleep_check_interval` | how often to scan for a sleepword (default 1.0s) |
| `sleep_window` | audio length per sleepword scan (default 2.0s) |

## Performance notes
Each run appends a timing line to `logs\assistant.log`:
```
mode=echo  rec=3.20s  transcribe=0.87s  copy=0.01s  piper=0.42s  total=6.30s
```
If `transcribe` is your bottleneck, try:
1. `whisper_threads` = physical core count
2. A smaller quantization (whisper.cpp `-q 5` builds) if not already using one
3. Upgrade to `ggml-base.en.bin` only if accuracy is the problem — it will be slower

## Troubleshooting
- **"no speech detected"** → check default mic is the one you speak into (`sounddevice` uses system default).
- **Piper errors** → verify `.onnx` **and** `.onnx.json` sit next to each other.
- **Whisper "model file not found"** → run `setup.bat`, check `models\ggml-tiny.en.bin` exists.
- **Hotkey does nothing** → right-click your AHK tray icon → Reload; make sure no other AHK has Win+W/Win+C bound.
- **Double-recording** → don't press both Win+W and Win+C simultaneously; the flag system treats the 2nd press as "stop".

## Uninstall
Delete `C:\Users\Apps\voiceassistant` and remove the snippet from your .ahk.
No registry changes, no PATH edits, no services.