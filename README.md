# win-voice

Read aloud text from Microsoft Edge, Google Chrome, Notepad, and Notepad++ using Piper TTS and sounddevice.

## Requirements

- Windows 11
- Python 3.14 installed at `C:\Program Files\Python314\python.exe`
- AutoHotkey v2
- Piper TTS with a voice model (e.g. `en_US-lessac-medium.onnx`)
- Python packages: `sounddevice`, `numpy`

Install dependencies:

```powershell
python -m pip install sounddevice numpy
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
| `Alt + 1` with text selected (any app) | Reads the selected text |
| `Alt + 1` in Edge/Chrome with no selection | Reads the current webpage (up to 50 KB of text) |
| `Alt + 1` in Notepad/Notepad++ with no selection | Tray notification: "No text selected. Please select text and press Alt+1." |
| `Alt + 1` while audio is playing | Stops playback immediately |
| `Alt + 1` in an unsupported app | Tray notification: "Alt-1 pressed but no supported app is active" |

**Supported applications:** Microsoft Edge, Google Chrome, Notepad, Notepad++

## Files

- `win-voice.ahk` — Minimal AutoHotkey v2 launcher. Detects supported apps, captures selection, invokes Python.
- `win_voice.py` — Python worker. Extracts text (selection or page), sanitizes, runs Piper, streams audio via sounddevice.
- `win_voice.log` — Debug log created on every run in the same folder.

## Notes

- **Browsers:** If text is selected, the selection is read. If nothing is selected, the script falls back to reading the full page text via UI Automation (up to 50,000 characters).
- **Notepad++:** The script uses the Scintilla API to verify a true text selection is present. This avoids reading the current line when no text is actually selected (if Notepad++'s "Copy current line" feature is enabled).
- **Character limit:** Text longer than 50,000 characters is truncated before speaking.

## Troubleshooting

- **No sound:** Check `win_voice.log` for Piper or sounddevice errors.
- **"Could not read text":** The page or control may not expose text via UI Automation. Try selecting text manually and press `Alt + 1` again.
- **"No text selected":** Notepad/Notepad++ require an explicit selection. Highlight some text first.
- **Piper errors:** Verify the voice model path in `win_voice.py` matches your actual `.onnx` and `.json` files.
