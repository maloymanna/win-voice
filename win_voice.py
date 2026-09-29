#!/usr/bin/env python3
"""
win_voice.py v10
Read aloud selected text from Edge, Chrome, Notepad, and Notepad++.
Uses Piper TTS + sounddevice for direct PCM streaming.
"""

import sys
import logging
import os
from pathlib import Path

# ============================================================
# Logging FIRST
# ============================================================
APP_DIR = Path(r"C:\Users\myuser\Apps\win-voice")
LOG_FILE = APP_DIR / "win_voice.log"
PID_FILE = APP_DIR / "playback.pid"

APP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("win_voice")
logger.info("=" * 50)
logger.info("Script started. PID=%d", os.getpid())

# ============================================================
# Imports with error trapping
# ============================================================
try:
    import argparse
    import ctypes
    import json
    import re
    import subprocess
    import time

    import numpy as np
    import sounddevice as sd
    logger.info("All imports successful.")
except Exception as import_exc:
    logger.exception("IMPORT FAILURE: %s", import_exc)
    sys.exit(1)

# ============================================================
# Config
# ============================================================
PIPER_EXE = Path(r"C:\Users\myuser\AppData\Roaming\Python\Python314\Scripts\piper")
VOICE_PATH = Path(r"C:\Users\myuser\pipervoices\en_US-lessac-medium.onnx")
VOICE_JSON = Path(str(VOICE_PATH) + ".json")

MAX_CHARS = 50000  # Hard safety limit on spoken text

# ============================================================
# Stop toggle
# ============================================================
def stop_if_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(1, False, pid)
        if handle:
            kernel.CloseHandle(handle)
            PID_FILE.unlink()
            logger.info("Stop signal sent to running playback (PID %d).", pid)
            return True
    except (ValueError, OSError) as exc:
        logger.warning("Stale PID file (%s); removing.", exc)
        try:
            PID_FILE.unlink()
        except OSError:
            pass
    return False

# ============================================================
# Piper / Audio
# ============================================================
def get_sample_rate() -> int:
    logger.info("Reading voice config from: %s", VOICE_JSON)
    with open(VOICE_JSON, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("audio", {}).get("sample_rate", 22050)


def sanitize_for_piper(text: str) -> str:
    replacements = {
        '\u00A0': ' ',
        '\u200B': '',
        '\u200C': '',
        '\u200D': '',
        '\uFEFF': '',
        '\u2018': "'",
        '\u2019': "'",
        '\u201C': '"',
        '\u201D': '"',
        '\u201A': ',',
        '\u201E': ',',
        '\u2026': '...',
        '\u2013': '-',
        '\u2014': '-',
        '\u02C6': '',
        '\u0302': '',
        '\u0308': '',
        '\u00A8': '',
        '\u02D8': '',
        '\u02DA': '',
        '\u02DD': '',
        '\u02DB': '',
        '\u02DC': '',
        '\u00B4': "'",
        '\u0060': "'",
        '\u02CA': "'",
        '\u02CB': "'",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = "".join(ch for ch in text if ch == '\t' or ch == '\n' or ch == '\r' or (ord(ch) >= 32 and ord(ch) < 0xD800) or ord(ch) > 0xDFFF)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def speak_text(text: str) -> int:
    try:
        sample_rate = get_sample_rate()
    except Exception as exc:
        logger.exception("Failed to read voice config: %s", exc)
        return 1

    text = sanitize_for_piper(text)
    if not text:
        logger.warning("Text is empty after sanitization.")
        return 1

    logger.info("Speaking %d chars at %d Hz.", len(text), sample_rate)
    PID_FILE.write_text(str(os.getpid()))

    try:
        proc = subprocess.Popen(
            [str(PIPER_EXE), "-m", str(VOICE_PATH), "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=text.encode("utf-8"))
    except Exception as exc:
        logger.exception("Failed to run Piper: %s", exc)
        PID_FILE.unlink(missing_ok=True)
        return 1

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[:1000]
        logger.error("Piper failed (rc=%d): %s", proc.returncode, err)
        PID_FILE.unlink(missing_ok=True)
        return 1

    audio = np.frombuffer(stdout, dtype=np.int16)
    logger.info("Received %d samples from Piper.", len(audio))

    if len(audio) == 0:
        logger.warning("No audio generated (empty output).")
        PID_FILE.unlink(missing_ok=True)
        return 1

    try:
        sd.play(audio, samplerate=sample_rate)
    except Exception as exc:
        logger.exception("sounddevice play failed: %s", exc)
        PID_FILE.unlink(missing_ok=True)
        return 1

    try:
        while sd.get_stream().active:
            if not PID_FILE.exists():
                logger.info("Stop requested during playback.")
                sd.stop()
                break
            time.sleep(0.2)
    except Exception as exc:
        logger.error("Playback polling error: %s", exc)
    finally:
        PID_FILE.unlink(missing_ok=True)
        logger.info("Playback finished.")

    return 0


# ============================================================
# Text extraction helpers
# ============================================================
def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ============================================================
# Edge / Chrome: DocumentControl + TextPattern
# ============================================================
def get_browser_selection(hwnd: int) -> str:
    import uiautomation as uia

    logger.info("Connecting to browser window HWND=%d", hwnd)
    window = uia.ControlFromHandle(hwnd)
    if not window:
        raise RuntimeError("uiautomation could not get control from HWND.")

    logger.info("Window name=%s class=%s", window.Name, window.ClassName)

    doc_control = None
    def find_doc(control, max_depth=8, depth=0):
        nonlocal doc_control
        if depth > max_depth or doc_control:
            return
        for child in control.GetChildren():
            if child.ControlTypeName == "DocumentControl":
                doc_control = child
                return
            find_doc(child, max_depth, depth + 1)

    find_doc(window)
    if doc_control:
        logger.info("Found DocumentControl: name=%s", doc_control.Name)

    text_control = None
    if not doc_control:
        def find_text_pattern(control, max_depth=8, depth=0):
            nonlocal text_control
            if depth > max_depth or text_control:
                return
            for child in control.GetChildren():
                if child.GetTextPattern():
                    text_control = child
                    return
                find_text_pattern(child, max_depth, depth + 1)

        find_text_pattern(window)
        if text_control:
            logger.info("Found control with TextPattern: type=%s name=%s",
                        text_control.ControlTypeName, text_control.Name)

    target = doc_control or text_control
    if not target:
        raise RuntimeError("No document or text control found in browser window.")

    text_pattern = target.GetTextPattern()
    if not text_pattern:
        raise RuntimeError("Target control does not expose TextPattern.")

    selections = text_pattern.GetSelection()
    if selections:
        selected_texts = []
        for sel in selections:
            txt = sel.GetText(-1)
            if txt:
                selected_texts.append(txt)
        if selected_texts:
            return clean_text("\n".join(selected_texts))

    return ""


# ============================================================
# Notepad: EditControl
# ============================================================
def get_notepad_selection(hwnd: int) -> str:
    import uiautomation as uia

    logger.info("Connecting to Notepad window HWND=%d", hwnd)
    window = uia.ControlFromHandle(hwnd)
    if not window:
        raise RuntimeError("uiautomation could not get control from HWND.")

    edit = None
    def find_edit(control, max_depth=5, depth=0):
        nonlocal edit
        if depth > max_depth or edit:
            return
        for child in control.GetChildren():
            if child.ControlTypeName == "EditControl":
                edit = child
                return
            find_edit(child, max_depth, depth + 1)

    find_edit(window)
    if not edit:
        raise RuntimeError("No EditControl found in Notepad window.")

    logger.info("Found EditControl: name=%s", edit.Name)

    text_pattern = edit.GetTextPattern()
    if text_pattern:
        selections = text_pattern.GetSelection()
        if selections:
            selected_texts = [sel.GetText(-1) for sel in selections if sel.GetText(-1)]
            if selected_texts:
                return clean_text("\n".join(selected_texts))

    return ""


# ============================================================
# Notepad++: Scintilla API via SendMessage
# ============================================================
# Scintilla constants
SCI_GETSELTEXT = 2161
SCI_GETCURRENTPOS = 2008
SCI_GETANCHOR = 2009


def send_message(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    user32 = ctypes.windll.user32
    return user32.SendMessageW(hwnd, msg, wparam, lparam)


def get_notepad_plus_plus_selection(hwnd: int) -> str:
    """
    Uses Scintilla API via SendMessage.
    hwnd is the main Notepad++ window handle.
    We find ALL Scintilla editor child windows and pick the one with a selection.
    """
    logger.info("Connecting to Notepad++ window HWND=%d", hwnd)

    EnumChildWindows = ctypes.windll.user32.EnumChildWindows
    scintilla_hwnds = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_long, ctypes.c_long)
    def enum_child_callback(child_hwnd, extra):
        class_name = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(child_hwnd, class_name, 256)
        cn = class_name.value
        if cn == "Scintilla":
            scintilla_hwnds.append(child_hwnd)
        return True

    EnumChildWindows(hwnd, enum_child_callback, 0)
    logger.info("Found %d Scintilla window(s).", len(scintilla_hwnds))

    if not scintilla_hwnds:
        raise RuntimeError("No Scintilla editor window found in Notepad++.")

    # Try each Scintilla window; pick the one with a real selection.
    for sci_hwnd in scintilla_hwnds:
        anchor = send_message(sci_hwnd, SCI_GETANCHOR, 0, 0)
        current_pos = send_message(sci_hwnd, SCI_GETCURRENTPOS, 0, 0)
        logger.info("Scintilla HWND=%d anchor=%d current_pos=%d", sci_hwnd, anchor, current_pos)

        if anchor == current_pos:
            logger.info("  -> no selection on this view.")
            continue

        sel_len = send_message(sci_hwnd, SCI_GETSELTEXT, 0, 0)
        if sel_len <= 1:
            logger.info("  -> selection too small: %d", sel_len)
            continue

        buf = ctypes.create_string_buffer(sel_len)
        send_message(sci_hwnd, SCI_GETSELTEXT, 0, ctypes.addressof(buf))
        text = buf.raw[:sel_len - 1].decode("utf-8", errors="replace")
        logger.info("Notepad++ selection: %d chars", len(text))
        return clean_text(text)

    logger.info("No selection found in any Scintilla view.")
    return ""


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True, choices=["edge", "chrome", "notepad", "notepad++"])
    parser.add_argument("--hwnd", type=int, required=True)
    parser.add_argument("--selection-file", type=Path, default=None)
    args = parser.parse_args()

    logger.info("Args: app=%s hwnd=%d selection-file=%s", args.app, args.hwnd, args.selection_file)

    if stop_if_running():
        return 0

    text = ""

    # Priority 1: use clipboard selection file if AHK detected one
    if args.selection_file and args.selection_file.exists():
        raw = args.selection_file.read_text("utf-8", errors="replace")
        text = clean_text(raw)
        logger.info("Clipboard selection mode: %d chars.", len(text))
    else:
        # Priority 2: app-specific extraction
        try:
            if args.app in ("edge", "chrome"):
                text = get_browser_selection(args.hwnd)
            elif args.app == "notepad":
                text = get_notepad_selection(args.hwnd)
            elif args.app == "notepad++":
                text = get_notepad_plus_plus_selection(args.hwnd)
        except Exception as exc:
            logger.exception("Text extraction failed for %s: %s", args.app, exc)
            return 2

    if not text:
        logger.info("No text selected.")
        return 3

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        logger.info("Text truncated to %d chars.", MAX_CHARS)

    return speak_text(text)


if __name__ == "__main__":
    sys.exit(main())
