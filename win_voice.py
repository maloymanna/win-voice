#!/usr/bin/env python3
"""
win_voice.py
Reads selected text or current page content from Edge and speaks it via Piper + sounddevice.
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
    import urllib.parse
    import urllib.request
    import html
    from html.parser import HTMLParser

    import numpy as np
    import requests
    import sounddevice as sd
    import uiautomation as uia
    logger.info("All imports successful.")
except Exception as import_exc:
    logger.exception("IMPORT FAILURE: %s", import_exc)
    ctypes.windll.user32.MessageBoxW(0, f"Import error — check win_voice.log\n\n{import_exc}", "win_voice import error", 0x10)
    sys.exit(1)

# ============================================================
# Config
# ============================================================
PIPER_EXE = Path(r"C:\Users\myuser\AppData\Roaming\Python\Python314\Scripts\piper")
VOICE_PATH = Path(r"C:\Users\myuser\pipervoices\en_US-lessac-medium.onnx")
VOICE_JSON = Path(str(VOICE_PATH) + ".json")

HARD_LIMIT_BYTES = 50 * 1024  # 50 KB raw limit for webpages
MAX_CHARS = 20000

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
# Text extraction helpers
# ============================================================
class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_tags = {"script", "style", "nav", "footer", "header", "aside"}
        self.in_skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.in_skip += 1
        if tag == "br":
            self.parts.append("\n")
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip -= 1
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_skip <= 0:
            self.parts.append(data)

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ============================================================
# URL / Content fetching
# ============================================================
def get_edge_url(hwnd: int) -> str | None:
    logger.info("Resolving URL from Edge HWND=%d", hwnd)
    try:
        window = uia.ControlFromHandle(hwnd)
        if not window:
            logger.error("uiautomation could not get control from HWND.")
            return None

        address_bar = None

        def find_by_id(control, ids, max_depth=6, depth=0):
            if depth > max_depth:
                return None
            for child in control.GetChildren():
                if child.AutomationId in ids:
                    return child
                result = find_by_id(child, ids, max_depth, depth + 1)
                if result:
                    return result
            return None

        address_bar = find_by_id(window, ("view_1002", "AddressBar", "addressEdit"))
        if address_bar:
            logger.info("Found address bar by AutomationId=%s", address_bar.AutomationId)

        if not address_bar:
            def find_by_name(control, max_depth=6, depth=0):
                if depth > max_depth:
                    return None
                for child in control.GetChildren():
                    if child.ControlTypeName in ("EditControl", "DocumentControl"):
                        name = child.Name or ""
                        if any(k in name for k in ("Address", "アドレス", "地址", "search", "検索", "搜索")):
                            return child
                    result = find_by_name(child, max_depth, depth + 1)
                    if result:
                        return result
                return None

            address_bar = find_by_name(window)
            if address_bar:
                logger.info("Found address bar by Name=%s", address_bar.Name)

        if not address_bar:
            def find_by_url_value(control, max_depth=6, depth=0):
                if depth > max_depth:
                    return None
                for child in control.GetChildren():
                    if child.ControlTypeName == "EditControl":
                        val_pat = child.GetValuePattern()
                        if val_pat:
                            val = val_pat.Value or ""
                            if val.startswith("http") or val.startswith("file:") or "://" in val:
                                return child
                    result = find_by_url_value(child, max_depth, depth + 1)
                    if result:
                        return result
                return None

            address_bar = find_by_url_value(window)
            if address_bar:
                logger.info("Found address bar by URL-like value")

        if not address_bar:
            logger.error("Could not find Edge address bar in UIA tree.")
            for child in window.GetChildren():
                logger.debug("  child: type=%s name=%s id=%s", child.ControlTypeName, child.Name, child.AutomationId)
            return None

        val_pat = address_bar.GetValuePattern()
        url = val_pat.Value if val_pat else address_bar.Name
        logger.info("Resolved URL: %s", url)
        return url
    except Exception as exc:
        logger.exception("UI Automation failed: %s", exc)
        return None


def is_pdf_url(url: str) -> bool:
    """Detect PDF from URL suffix or HEAD request without downloading body."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    if path.endswith(".pdf"):
        logger.info("PDF detected by URL suffix: %s", url)
        return True

    # For HTTP(S), try a HEAD request to check Content-Type
    if parsed.scheme in ("http", "https"):
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            ct = resp.headers.get("Content-Type", "").lower()
            if "pdf" in ct:
                logger.info("PDF detected by Content-Type: %s", ct)
                return True
        except Exception as exc:
            logger.debug("HEAD request failed (%s); assuming not PDF.", exc)
    return False


def fetch_webpage_text(url: str) -> str:
    """Fetch up to 50KB of raw HTML and convert to plain text."""
    logger.info("Fetching webpage up to %d bytes from %s", HARD_LIMIT_BYTES, url)
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme in ("http", "https"):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.0 Edg/128.0.0.0"
            )
        }
        resp = requests.get(url, headers=headers, stream=True, timeout=20)
        resp.raise_for_status()
        data = b""
        for chunk in resp.iter_content(chunk_size=8192):
            data += chunk
            if len(data) >= HARD_LIMIT_BYTES:
                break
        data = data[:HARD_LIMIT_BYTES]
    elif parsed.scheme == "file":
        path = urllib.request.url2pathname(parsed.path)
        with open(path, "rb") as f:
            data = f.read(HARD_LIMIT_BYTES)
    elif os.path.exists(url):
        with open(url, "rb") as f:
            data = f.read(HARD_LIMIT_BYTES)
    else:
        raise ValueError(f"Unsupported URL scheme or missing file: {url}")

    if not data:
        return ""

    try:
        html_str = data.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        html_str = data.decode("latin-1", errors="replace")

    extractor = HTMLTextExtractor()
    extractor.feed(html_str)
    text = extractor.get_text()
    return clean_text(text)


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
    if args.selection_file and args.selection_file.exists():
        raw = args.selection_file.read_text("utf-8", errors="replace")
        text = clean_text(raw)
        logger.info("Selection mode: %d chars.", len(text))
    elif args.hwnd:
        url = get_edge_url(args.hwnd)
        if not url:
            logger.error("Could not determine Edge URL; aborting.")
            return

        if is_pdf_url(url):
            logger.info("PDF detected in page mode. Prompting user to select text.")
            ctypes.windll.user32.MessageBoxW(
                0,
                "PDF detected.\n\nPlease select the text you want to read and press Alt+1.",
                "win-voice",
                0x40  # MB_ICONINFORMATION
            )
            return

        text = fetch_webpage_text(url)
        logger.info("Page mode: %d chars from %s", len(text), url)
    else:
        logger.error("No selection file and no HWND provided.")
        return

    if not text:
        logger.info("No text to speak; exiting.")
        return

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        logger.info("Text truncated to %d chars.", MAX_CHARS)

    speak_text(text)


if __name__ == "__main__":
    main()
