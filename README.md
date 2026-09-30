# win-voice

A lightweight text-to-speech tool for Windows that reads selected text aloud using Piper TTS and direct PCM streaming.

## Features

- **Global hotkey**: Press `Alt+1` to read selected text aloud
- **Stop toggle**: Press `Alt+1` again during playback to stop immediately
- **Selected text only**: Reads whatever text is currently selected in the active window
- **No temporary files**: Streams audio directly from Piper to your speakers via `sounddevice`
- **Tray notifications**: Clean Windows tray tips for status and errors (no popup dialogs)
- **Character sanitization**: Automatically cleans smart quotes, zero-width characters, and other symbols that confuse TTS engines

## Supported Applications

| Application | Status | Notes |
|-------------|--------|-------|
| Microsoft Edge | Supported | Selected text on any web page |
| Google Chrome | Supported | Selected text on any web page |
| Notepad++ | Supported | Reads current line if no text is explicitly selected (Scintilla behavior) |
| Windows Notepad | **Not supported** | UIA EditControl detection is unreliable on Windows 11 |

## Requirements

- Windows 10 or later
- AutoHotkey v2
- Python 3.14 (or compatible version)
- Piper TTS engine
- `sounddevice` and `numpy` Python packages
- `uiautomation` Python package (for browser text extraction)

## File Structure

Place these files in `C:\Users\myuser\Apps\win-voice\`:

```
win-voice/
  win-voice.ahk      # AutoHotkey launcher (global hotkey handler)
  win_voice.py       # Python engine (text extraction, TTS, audio playback)
  win_voice.log      # Runtime log (auto-created)
  playback.pid        # Playback lock file (auto-created during speech)
```

## Installation

1. Install AutoHotkey v2 from https://www.autohotkey.com/
2. Install Python 3.14 to `C:\Program Files\Python314\`
3. Install Piper TTS:
   ```
   pip install piper-tts
   ```
4. Download a Piper voice model (e.g., `en_US-lessac-medium.onnx`) to:
   ```
   C:\Users\myuser\pipervoices\
   ```
5. Install Python dependencies:
   ```
   pip install sounddevice numpy uiautomation
   ```
6. Place `win-voice.ahk` and `win_voice.py` in `C:\Users\myuser\Apps\win-voice\`
7. Double-click `win-voice.ahk` to start the script (it runs in the background)

## Usage

1. Open a supported application (Edge, Chrome, or Notepad++)
2. Select some text (or place cursor on a line in Notepad++)
3. Press `Alt+1`
4. The selected text will be read aloud
5. Press `Alt+1` again at any time to stop playback

### Behavior by Application

**Edge / Chrome:**
- Copies selected text to clipboard and reads it
- If no text is selected, shows "No text selected" notification

**Notepad++:**
- Uses Scintilla API to read the current editor selection
- Due to Scintilla behavior, if no text is explicitly selected, the current line under the cursor will be read
- This is expected behavior and does not need to be "fixed"

## How It Works

### Architecture
- **AHK** (`win-voice.ahk`): Minimal launcher that handles the `Alt+1` hotkey, captures clipboard selection, and delegates to Python
- **Python** (`win_voice.py`): Handles text extraction (UIA for browsers, Scintilla for Notepad++), sanitization, Piper TTS invocation, and audio streaming via `sounddevice`

### Stop Toggle Mechanism
- When playback starts, Python creates a `playback.pid` file
- Pressing `Alt+1` during playback deletes this file
- Python's playback loop detects the missing file and stops audio immediately
- AHK sends `{Alt Up}{Esc}` after stop to prevent browser menu focus glitches

### Text Sanitization
The following characters are automatically cleaned before sending to Piper:
- Non-breaking spaces, zero-width spaces
- Smart quotes (curly quotes converted to straight quotes)
- Em-dashes, en-dashes (converted to hyphens)
- Combining diacritical marks that cause "umlaut" speech artifacts
- Control characters (except tab and newline)

## Troubleshooting

### "No text selected" notification
- Make sure text is actually selected in the active window
- For Notepad++, the current line will be read even without explicit selection

### "Could not read text" notification
- Check `win_voice.log` for detailed error messages
- Ensure the target application window is active when pressing `Alt+1`

### Audio not playing
- Verify Piper is installed and the voice model path is correct
- Check `win_voice.log` for Piper errors
- Ensure your default audio output device is working

### Stop toggle not working
- Make sure `playback.pid` is being created in the script directory
- Check that no other process is locking the PID file

## Log Files

- `win_voice.log` — Detailed Python-side logging (text extraction, TTS, audio)
- Check this file first when debugging issues

## License

MIT License — use at your own risk.
