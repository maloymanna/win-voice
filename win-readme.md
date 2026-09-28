# Read Aloud for Windows 11

A Windows port of the Linux Lite 8 / XFCE `read-aloud.sh` script. Press a hotkey to have your computer read selected text aloud. Press the same hotkey again while reading to stop immediately.

## Features

- **Toggle with the same hotkey**: press once to start, press again to stop. Works everywhere (web pages, PDFs, text editors).
- **Application-aware**: detects the active window and adapts its behavior.
- **Web pages** (Microsoft Edge, Chrome, Brave, Vivaldi, Opera, Firefox): reads the current selection, or falls back to the full page via `Ctrl+A / Ctrl+C` with a 50 KB cap.
- **PDF in browser** (Microsoft Edge PDF viewer, etc.): reads the current text selection via clipboard.
- **Text editors** (Notepad, Notepad++, VS Code, Sublime Text, etc.): reads the selected text via clipboard.
- **No stale selections across windows**: the script clears the clipboard and sends `Ctrl+C` to the active window before reading.
- **Safe by design**: all text extractions are capped at 50 KB to prevent freezing on large documents.
- **Works for non-admin users**: no administrator privileges required.

## Requirements

- Windows 11
- Python 3.x (installed for your user, e.g. from Microsoft Store or python.org)
- `piper.exe` and voice model (`.onnx` + `.onnx.json`)
- Optional: `pdftotext.exe` (from [Xpdf](https://www.xpdfreader.com/download.html) or [poppler](https://github.com/oschwartz10612/poppler-windows)) for better PDF text extraction
- Optional: `pypdf` or `PyPDF2` Python package as a pure-Python PDF fallback

## File Layout

Place the files in a folder of your choice, for example:

```
C:\Users\a123bc\read-aloud\
    read-aloud.py
    read-aloud.bat
```

Make sure your Piper tools are available at:

```
C:\Users\a123bc\AppData\Roaming\Python\Python314\Scripts\piper.exe
```

And your voice model at:

```
C:\Users\a123bc\pipervoices\en_US-lessac-medium.onnx
C:\Users\a123bc\pipervoices\en_US-lessac-medium.onnx.json
```

## Installation

1. Copy `read-aloud.py` and `read-aloud.bat` into your chosen folder.
2. Ensure `piper.exe` and the voice model files are in the paths shown above (or set the environment variables below).
3. Add the folder containing `read-aloud.bat` to your user `PATH`, **or** note the full path to `read-aloud.bat` for the hotkey step.

### Optional: Install PDF fallback support

If you do not have `pdftotext.exe` on your PATH, install the Python fallback:

```cmd
py -m pip install pypdf
```

## Configuration

If your paths differ from the defaults, set these **user** environment variables (no admin rights needed):

| Variable      | Example value                                                              |
|---------------|----------------------------------------------------------------------------|
| `PIPER_BIN`   | `C:\Users\a123bc\AppData\Roaming\Python\Python314\Scripts\piper.exe`        |
| `PIPER_VOICE` | `C:\Users\a123bc\pipervoices\en_US-lessac-medium.onnx`                     |

To set them in Windows 11:

1. Press `Win` and search for **"Environment Variables"**.
2. Choose **"Edit environment variables for your account"**.
3. Click **New...** under **User variables**.
4. Add `PIPER_BIN` and `PIPER_VOICE` with the full paths above.
5. Log out and log back in (or restart any open terminal/Git Bash windows).

## Hotkey Setup

You can bind a hotkey using any of these methods:

### Option A: AutoHotkey v2 (recommended)

1. Install [AutoHotkey v2](https://www.autohotkey.com/).
2. Create a file named `ReadAloud.ahk` with the following content (adjust the path):

```autohotkey
#Requires AutoHotkey v2.0
#r::Run("C:\Users\a123bc\read-aloud\read-aloud.bat")
```

3. Double-click `ReadAloud.ahk` to run it. Press `Win + R` to read aloud / stop.
4. To start automatically on login, place a shortcut to `ReadAloud.ahk` in:
   `C:\Users\a123bc\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

### Option B: Built-in Keyboard Shortcuts (simple but limited)

1. Right-click `read-aloud.bat` and choose **Create shortcut**.
2. Right-click the shortcut → **Properties** → **Shortcut key**.
3. Press a key combination (e.g. `Ctrl + Alt + R`).
4. Click **OK**.
5. Place the shortcut on your Desktop. The hotkey only works when you are on the Desktop, so this method is less convenient than AutoHotkey.

### Option C: Git Bash alias

If you use Git Bash often, add to your `~/.bashrc`:

```bash
alias read-aloud='python /c/Users/a123bc/read-aloud/read-aloud.py'
```

Then run:

```bash
read-aloud
```

## Usage

1. Open a web page or PDF in Microsoft Edge (or another supported browser).
2. Select text (optional for web pages, required for PDFs).
3. Press your hotkey (e.g. `Win + R`) to start reading.
4. Press the same hotkey again at any time to stop.

When switching between applications, the script always reads from the **currently focused window**.

## Behavior by application

| Application         | Selection present              | No selection                                    |
|---------------------|--------------------------------|-------------------------------------------------|
| Browser (web page)  | Reads selection via clipboard  | Selects all page text (capped at 50 KB)        |
| Browser (PDF)       | Reads selection via clipboard  | Prompts you to select text in the PDF viewer   |
| Text editor         | Reads clipboard via Ctrl+C     | Prompts you to select text                      |
| Other apps          | Reads clipboard via Ctrl+C     | Prompts you to select text                      |

## Safety limits

| Source            | Limit                                      |
|-------------------|--------------------------------------------|
| Web page full text| 50 KB cap                                  |
| Editor / generic  | 50 KB cap                                  |
| Audio pipeline    | Piper generates WAV, then Windows plays it |

## Logging

Debug output is written to:

```
%TEMP%\read-aloud.log
```

Open it in a terminal:

```cmd
type %TEMP%\read-aloud.log
```

Or in File Explorer, paste into the address bar:

```
%TEMP%\read-aloud.log
```

## Troubleshooting

### "piper.exe not found"

- Check that `PIPER_BIN` points to the correct `piper.exe`.
- Or ensure `piper.exe` is at the default path shown in **File Layout**.

### "Voice model not found"

- Check that `PIPER_VOICE` points to the `.onnx` file.
- The matching `.onnx.json` file must be in the same folder.

### No sound

- Make sure your default playback device is working.
- Check `%TEMP%\read-aloud.log` for errors.
- Try running `read-aloud.bat` from a Command Prompt to see any console output.

### Clipboard is overwritten

When reading a full web page, the script uses `Ctrl+A / Ctrl+C`. This will replace your clipboard. This is by design so the script always reads from the currently focused window.

### PDF in browser shows "No text selected"

- In Microsoft Edge, click the PDF viewer toolbar and use the text selection tool, then select some text before pressing the hotkey.
- Some scanned/image-based PDFs do not contain selectable text.

## Differences from the Linux version

| Feature              | Linux (read-aloud.sh)                        | Windows (read-aloud.py)                              |
|----------------------|-----------------------------------------------|------------------------------------------------------|
| Audio output         | `pacat` (PulseAudio) streaming raw PCM        | `winsound` playing a generated WAV file              |
| Window detection     | `xdotool`, `xprop`, `lsof`                  | `ctypes` + `user32.dll` / PowerShell fallback        |
| Notifications        | `notify-send`                                 | PowerShell `System.Windows.Forms.NotifyIcon`         |
| Clipboard            | `xclip`                                       | PowerShell `Get-Clipboard` / `Set-Clipboard`           |
| Key simulation       | `xdotool key`                                 | `System.Windows.Forms.SendKeys` via PowerShell       |
| EPUB support         | Yes (FBReader)                                | No (removed; focus is on web/PDF in browser)         |

## License

MIT / Public Domain — use and modify freely.
