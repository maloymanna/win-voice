#!/usr/bin/env python3
"""
read-aloud.py - Application-aware read aloud for Windows 11.
Toggle with the same hotkey: press once to start, press again to stop.

Supports web pages and PDFs in Microsoft Edge (and other Chromium browsers).
No admin rights required.
"""

import os
import sys
import re
import json
import time
import shutil
import tempfile
import subprocess
import atexit
import ctypes
from ctypes import wintypes

# ------------------- Configuration -------------------
PIPER_BIN = os.environ.get(
    "PIPER_BIN",
    os.path.join(os.path.expanduser("~"), r"AppData\Roaming\Python\Python314\Scripts\piper.exe"),
)
PIPER_VOICE = os.environ.get(
    "PIPER_VOICE",
    os.path.join(os.path.expanduser("~"), r"pipervoices\en_US-lessac-medium.onnx"),
)

TEMP_DIR = tempfile.gettempdir()
PIDFILE = os.path.join(TEMP_DIR, "read-aloud.pid")
CHILDREN_FILE = os.path.join(TEMP_DIR, "read-aloud.children")
LOGFILE = os.path.join(TEMP_DIR, "read-aloud.log")

# ------------------- Logging -------------------
def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    line = f"{timestamp} {msg}"
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def init_log():
    try:
        with open(LOGFILE, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass


# ------------------- Toggle / Stop -------------------
def read_pidfile():
    try:
        with open(PIDFILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def write_pidfile(pid):
    with open(PIDFILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def read_children():
    try:
        with open(CHILDREN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_children(children):
    try:
        with open(CHILDREN_FILE, "w", encoding="utf-8") as f:
            json.dump(children, f)
    except Exception:
        pass


def cleanup():
    for f in [PIDFILE, CHILDREN_FILE]:
        try:
            os.remove(f)
        except Exception:
            pass


def is_process_alive(pid):
    if not pid:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def kill_tree(pid):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def stop_running_instance():
    pid = read_pidfile()
    if pid:
        children = read_children()
        for cpid in children:
            kill_tree(cpid)
        kill_tree(pid)
    cleanup()
    notify("Read Aloud", "Stopped.")


# ------------------- Notifications -------------------
def notify(title, message, icon="Information"):
    ps_code = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$notify = New-Object System.Windows.Forms.NotifyIcon; "
        f'$notify.Icon = [System.Drawing.SystemIcons]::{icon}; '
        f"$notify.BalloonTipTitle = '{title}'; "
        f"$notify.BalloonTipText = '{message}'; "
        "$notify.Visible = $true; "
        "$notify.ShowBalloonTip(2000); "
        "Start-Sleep -Milliseconds 2500; "
        "$notify.Dispose()"
    )
    try:
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-Command",
                ps_code,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log(f"Notification error: {e}")


# ------------------- Window Detection -------------------
def get_active_window_handle():
    user32 = ctypes.windll.user32
    return user32.GetForegroundWindow()


def get_active_process_name():
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = get_active_window_handle()
        if not hwnd:
            return ""

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        h_process = kernel32.OpenProcess(0x0410, False, pid)  # QUERY_INFORMATION | VM_READ
        if not h_process:
            return _get_active_process_name_ps()

        filename = (ctypes.c_wchar * 512)()
        size = wintypes.DWORD(512)
        kernel32.QueryFullProcessImageNameW(h_process, 0, filename, ctypes.byref(size))
        kernel32.CloseHandle(h_process)

        return os.path.basename(filename.value).replace(".exe", "").lower()
    except Exception as e:
        log(f"ctypes process name error: {e}")
        return _get_active_process_name_ps()


def _get_active_process_name_ps():
    ps_code = """
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@
$hwnd = [WinAPI]::GetForegroundWindow()
$pid = 0
[void][WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$pid)
try {
    $proc = Get-Process -Id $pid -ErrorAction Stop
    $proc.ProcessName
} catch {
    ""
}
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip().lower()
    except Exception as e:
        log(f"PowerShell process name error: {e}")
        return ""


def get_active_window_title():
    try:
        user32 = ctypes.windll.user32
        hwnd = get_active_window_handle()
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception as e:
        log(f"ctypes window title error: {e}")
        return ""


def is_pdf_in_browser(title):
    title_lower = title.lower()
    return ".pdf" in title_lower or title_lower.endswith(" - pdf") or "pdf viewer" in title_lower


# ------------------- Clipboard & Keys -------------------
def clear_clipboard():
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", 'Set-Clipboard -Value ""'],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        log(f"Clear clipboard error: {e}")


def get_clipboard():
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        log(f"Get clipboard error: {e}")
    return ""


def send_keys(keys):
    ps_code = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        f'[System.Windows.Forms.SendKeys]::SendWait("{keys}")'
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_code],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        log(f"SendKeys error: {e}")


# ------------------- Text Extraction -------------------
def extract_pdf_text(pdf_path, page=None):
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        cmd = [pdftotext]
        if page and str(page).isdigit():
            cmd.extend(["-f", str(page), "-l", str(page)])
        cmd.extend(["-layout", "-nopgbrk", pdf_path, "-"])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            return result.stdout[:50000]
        except Exception as e:
            log(f"pdftotext error: {e}")

    # Fallback to pure Python if pypdf/PyPDF2 is installed
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        if page and isinstance(page, int) and 1 <= page <= len(reader.pages):
            text = reader.pages[page - 1].extract_text() or ""
        else:
            for i, p in enumerate(reader.pages):
                text += (p.extract_text() or "") + "\n"
                if len(text) >= 50000:
                    break
        return text[:50000]
    except Exception as e:
        log(f"pypdf fallback error: {e}")

    return ""


# ------------------- Audio -------------------
def speak_text(text, label="Reading aloud"):
    # Kill any existing audio children first
    children = read_children()
    for cpid in children:
        kill_tree(cpid)
    write_children([])

    preview = text[:60]
    if len(text) > 60:
        preview += "..."
    notify(label, preview)

    # Write text to temp file for piper
    text_path = os.path.join(TEMP_DIR, "read-aloud-text.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)

    wav_path = os.path.join(TEMP_DIR, "read-aloud-audio.wav")
    for p in [wav_path]:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass

    # Run piper to generate WAV
    piper_cmd = [
        PIPER_BIN,
        "--model",
        PIPER_VOICE,
        "--file",
        text_path,
        "--output_file",
        wav_path,
    ]

    log(f"Running piper: {' '.join(piper_cmd)}")

    try:
        piper_proc = subprocess.Popen(
            piper_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as e:
        notify("Read Aloud Error", f"Failed to start piper: {e}", "Error")
        return False

    write_children([piper_proc.pid])

    try:
        stdout, stderr = piper_proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        piper_proc.kill()
        notify("Read Aloud Error", "Piper TTS timed out.", "Error")
        return False

    if piper_proc.returncode != 0:
        err = stderr.decode("utf-8", errors="ignore")[:200]
        notify("Read Aloud Error", f"Piper failed: {err}", "Error")
        return False

    if not os.path.isfile(wav_path):
        notify("Read Aloud Error", "Piper did not create audio file.", "Error")
        return False

    # Play WAV using winsound in a helper subprocess
    play_script = "import winsound\nimport sys\nwinsound.PlaySound(sys.argv[1], winsound.SND_FILENAME | winsound.SND_SYNC)\n"
    play_path = os.path.join(TEMP_DIR, "read-aloud-play.py")
    with open(play_path, "w", encoding="utf-8") as f:
        f.write(play_script)

    try:
        player_proc = subprocess.Popen([sys.executable, play_path, wav_path])
    except Exception as e:
        notify("Read Aloud Error", f"Failed to start audio player: {e}", "Error")
        return False

    write_children([player_proc.pid])

    # Wait for playback to finish so the script stays alive.
    # A new hotkey press will spawn a new instance that kills us.
    try:
        player_proc.wait(timeout=3600)
    except subprocess.TimeoutExpired:
        player_proc.kill()

    return True


# ------------------- Main -------------------
def main():
    init_log()
    my_pid = os.getpid()
    old_pid = read_pidfile()

    if old_pid and old_pid != my_pid:
        if is_process_alive(old_pid):
            stop_running_instance()
            sys.exit(0)
        else:
            cleanup()

    write_pidfile(my_pid)
    atexit.register(cleanup)

    log(f"Starting read-aloud.py PID={my_pid}")
    log(f"PIPER_BIN={PIPER_BIN}")
    log(f"PIPER_VOICE={PIPER_VOICE}")

    if not os.path.isfile(PIPER_BIN):
        notify("Read Aloud Error", f"piper.exe not found at:\n{PIPER_BIN}\nSet PIPER_BIN env var.", "Error")
        log(f"piper.exe not found: {PIPER_BIN}")
        sys.exit(1)

    if not os.path.isfile(PIPER_VOICE):
        notify("Read Aloud Error", f"Voice model not found at:\n{PIPER_VOICE}\nSet PIPER_VOICE env var.", "Error")
        log(f"Voice not found: {PIPER_VOICE}")
        sys.exit(1)

    process_name = get_active_process_name()
    window_title = get_active_window_title()
    log(f"Active process: {process_name}")
    log(f"Active window title: {window_title}")

    text = ""
    source_name = "none"
    is_tty = sys.stdout.isatty()

    browsers = {
        "msedge", "chrome", "chromium", "brave", "vivaldi", "opera", "firefox",
    }
    editors = {
        "notepad", "notepad++", "code", "sublime_text", "kate",
        "xed", "mousepad", "gedit", "pluma", "leafpad", "geany",
    }

    # ------------------------------------------------------------------
    # BROWSERS (Edge / Chromium / Firefox)
    # ------------------------------------------------------------------
    if process_name in browsers:
        is_pdf = is_pdf_in_browser(window_title)
        if is_pdf:
            notify("Read Aloud", "PDF in browser detected...")
        else:
            notify("Read Aloud", "Browser detected...")

        clear_clipboard()
        time.sleep(0.1)
        send_keys("^c")
        time.sleep(0.5)
        text = get_clipboard()
        if text:
            if is_pdf:
                source_name = "browser-pdf-selection"
                notify("Read Aloud", "Reading selected PDF text from browser.")
            else:
                source_name = "browser-selection"
                notify("Read Aloud", "Reading selected web text.")
            log(f"Using browser selection via Ctrl+C, length={len(text)}")

        if not text and not is_tty:
            if is_pdf:
                notify(
                    "Read Aloud",
                    "No text selected in PDF.\nPlease select text in the PDF viewer,\nthen press the hotkey again.",
                )
                log("No PDF selection in browser. Exiting gracefully.")
                sys.exit(0)
            else:
                notify("Read Aloud", "Selecting all page text...")
                time.sleep(0.2)
                send_keys("^a")
                time.sleep(0.2)
                send_keys("^c")
                time.sleep(0.5)
                text = get_clipboard()
                if text:
                    if len(text) > 50000:
                        text = text[:50000]
                        notify("Read Aloud", "Reading first 50 KB of page.\nYour clipboard was overwritten.")
                    else:
                        notify("Read Aloud", "Reading full page.\nYour clipboard was overwritten.")
                    source_name = "browser-all"

    # ------------------------------------------------------------------
    # TEXT EDITORS
    # ------------------------------------------------------------------
    elif process_name in editors:
        clear_clipboard()
        time.sleep(0.1)
        send_keys("^c")
        time.sleep(0.5)
        text = get_clipboard()
        if text:
            source_name = "editor-selection"
            log(f"Using editor clipboard via Ctrl+C, length={len(text)}")

    # ------------------------------------------------------------------
    # EVERYTHING ELSE
    # ------------------------------------------------------------------
    else:
        clear_clipboard()
        time.sleep(0.1)
        send_keys("^c")
        time.sleep(0.5)
        text = get_clipboard()
        if text:
            if len(text) > 50000:
                text = text[:50000]
            source_name = "clipboard-auto"

    # ------------------- Normalize & Speak -------------------
    if text:
        text = re.sub(r"\s+", " ", text).strip()

    if not text:
        notify(
            "Read Aloud",
            "No text found.\nSelect text, or open a document and press the hotkey.",
        )
        log("No text found. Exiting.")
        sys.exit(0)

    log(f"Final source: {source_name}, length={len(text)}")

    if source_name == "browser-all":
        pass  # already notified
    elif source_name == "clipboard-auto":
        notify("Read Aloud", "Used Ctrl+C fallback (capped at 50 KB).\nYour clipboard was overwritten.")

    speak_text(text, "Reading aloud")


if __name__ == "__main__":
    main()