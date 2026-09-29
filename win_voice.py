#!/usr/bin/env python3
"""
win_voice.py
Direct document text extraction from Edge via UI Automation TextPattern.
No URL fetching, no address bar detection, no clipboard manipulation.
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
    import html

    import numpy as np
    import sounddevice as sd
    import uiautomation as uia
    logger.info("All imports successful.")
except Exception as import_exc:
    logger.exception("IMPORT FAILURE: %s", import_exc)
    ctypes.windll.user32.MessageBoxW(
        0,
        f"Import error — check win_voice.log\n\n{import_exc}",
        "win_voice import error",
        0x10
    )
    sys.exit(1)

# ============================================================
# Config
# ============================================================
PIPER_EXE = Path(r"C:\Users\myuser\AppData\Roaming\Python\Python314\Scripts\piper")
VOICE_PATH = Path(r"C:\Users\myuser\pipervoices\en_US-lessac-medium.onnx")
VOICE_JSON = Path(str(VOICE_PATH) + ".json")

MAX_CHARS = 50000  # Hard safety limit on spoken text (~50KB equivalent)

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


def speak_text(text: str) -> None:
    try:
        sample_rate = get_sample_rate()
    except Exception as exc:
        logger.exception("Failed to read voice config: %s", exc)
        return

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
        return

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[:500]
        logger.error("Piper failed (rc=%d): %s", proc.returncode, err)
        PID_FILE.unlink(missing_ok=True)
        return

    audio = np.frombuffer(stdout, dtype=np.int16)
    logger.info("Received %d samples from Piper.", len(audio))

    if len(audio) == 0:
        logger.warning("No audio generated (empty output).")
        PID_FILE.unlink(missing_ok=True)
        return

    try:
        sd.play(audio, samplerate=sample_rate)
    except Exception as exc:
        logger.exception("sounddevice play failed: %s", exc)
        PID_FILE.unlink(missing_ok=True)
        return

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


# ============================================================
# Text extraction via UI Automation TextPattern
# ============================================================
def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_document_text_from_edge(hwnd: int) -> tuple[str, bool]:
    """
    Returns (text, has_selection).
    If extraction fails completely, raises Exception.
    """
    logger.info("Connecting to Edge window HWND=%d", hwnd)
    window = uia.ControlFromHandle(hwnd)
    if not window:
        raise RuntimeError("uiautomation could not get control from HWND.")

    logger.info("Window name=%s class=%s", window.Name, window.ClassName)

    # Strategy 1: Find DocumentControl directly
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

    # Strategy 2: Find any control that supports TextPattern
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
        # Debug: log top-level children
        logger.error("No DocumentControl or TextPattern control found.")
        for child in window.GetChildren():
            logger.debug("  child: type=%s name=%s id=%s",
                         child.ControlTypeName, child.Name, child.AutomationId)
        raise RuntimeError("No document or text control found in Edge window.")

    text_pattern = target.GetTextPattern()
    if not text_pattern:
        raise RuntimeError("Target control does not expose TextPattern.")

    # Check for selection first
    selections = text_pattern.GetSelection()
    if selections:
        selected_texts = []
        for sel in selections:
            txt = sel.GetText(-1)
            if txt:
                selected_texts.append(txt)
        if selected_texts:
            full_selection = "\n".join(selected_texts)
            logger.info("Selection detected: %d chars", len(full_selection))
            return clean_text(full_selection), True

    # No selection: get full document text
    doc_range = text_pattern.DocumentRange()
    full_text = doc_range.GetText(MAX_CHARS)
    logger.info("Full document text: %d chars", len(full_text))
    return clean_text(full_text), False


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-file", type=Path, default=None)
    parser.add_argument("--hwnd", type=int, default=0)
    args = parser.parse_args()

    logger.info("Args: selection-file=%s hwnd=%s", args.selection_file, args.hwnd)

    if stop_if_running():
        return

    text = ""
    has_selection = False

    if args.selection_file and args.selection_file.exists():
        # Legacy path from AHK clipboard mode (still supported)
        raw = args.selection_file.read_text("utf-8", errors="replace")
        text = clean_text(raw)
        logger.info("Selection-file mode: %d chars.", len(text))
        has_selection = True
    elif args.hwnd:
        try:
            text, has_selection = get_document_text_from_edge(args.hwnd)
            logger.info("UIA mode: %d chars, has_selection=%s", len(text), has_selection)
        except Exception as exc:
            logger.exception("Document text extraction failed: %s", exc)
            ctypes.windll.user32.MessageBoxW(
                0,
                "Could not read page text from Edge.\n\n"
                "Please select the text you want to read and press Alt+1.",
                "win-voice",
                0x40  # MB_ICONINFORMATION
            )
            return
    else:
        logger.error("No selection file and no HWND provided.")
        return

    if not text:
        if has_selection:
            logger.info("Selection was empty; exiting.")
        else:
            logger.info("No text found on page; may be an image-based PDF. Prompting user.")
            ctypes.windll.user32.MessageBoxW(
                0,
                "No readable text found on this page.\n\n"
                "Please select the text you want to read and press Alt+1.",
                "win-voice",
                0x40
            )
        return

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        logger.info("Text truncated to %d chars.", MAX_CHARS)

    speak_text(text)


if __name__ == "__main__":
    main()
