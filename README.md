# win-voice

Read aloud text from Microsoft Edge (webpages and selected text) using Piper TTS and sounddevice.

## Requirements

- Windows 11
- Python 3.14 installed at `C:\Program Files\Python314\python.exe`
- AutoHotkey v2
- Piper TTS with a voice model (e.g. `en_US-lessac-medium.onnx`)
- Python packages: `sounddevice`, `numpy`, `uiautomation`

Install dependencies:

```powershell
python -m pip install sounddevice numpy uiautomation
```

## Installation

1. Place both files in `C:\Users\myuser\Apps\win-voice\`:
   - `win-voice.ahk`
   - `win_voice.py`

2. Update paths inside both files if your Python or Piper locations differ.

3. Double-click `win-voice.ahk` to run it. It will sit in the system tray.

## Usage

| Action | Result |
|--------|--------|
| `Alt + 1` in Edge with text selected | Reads the selected text |
| `Alt + 1` in Edge with no selection | Reads the current webpage (up to 50 KB of text) |
| `Alt + 1` while audio is playing | Stops playback immediately |
| `Alt + 1` in any other window | Tray notification: "Alt-1 pressed but Edge not active" |

## Files

- `win-voice.ahk` — Minimal AutoHotkey v2 launcher. Detects Edge, captures selection, invokes Python.
- `win_voice.py` — Python worker. Extracts text via UI Automation, runs Piper, streams audio via sounddevice.
- `win_voice.log` — Debug log created on every run in the same folder.

## Troubleshooting

- **No sound**: Check `win_voice.log` for Piper or sounddevice errors.
- **"Could not read page text"**: The page may be an image-based PDF. Select text manually and press `Alt + 1` again.
- **Piper errors**: Verify the voice model path in `win_voice.py` matches your actual `.onnx` and `.json` files.
