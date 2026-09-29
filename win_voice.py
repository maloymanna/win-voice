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
# Logging FIRST — before any imports that might fail
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
    import tempfile
    import time
    import urllib.parse
    import urllib.request
    import html
    from html.parser import HTMLParser

    import numpy as np
    import requests
    import sounddevice as sd
    import uiautomation as uia
    from pypdf import PdfReader
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
VOICE_JSON = Path(str(VOICE_PATH) + ".json")  # FIXED: was .onnx.json which duplicated the extension

HARD_LIMIT_BYTES = 50 * 1024  # 50 KB raw limit
MAX_CHARS = 20000

# ============================================================
# Stop toggle
# ============================================================
def stop_if_running() -> bool:
    """If another instance is playing, signal it to stop and return True."""
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
    """Stream Piper raw PCM through sounddevice."""
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
        for ctrl, _ in uia.WalkTree(window):
            if ctrl.AutomationId in ("view_1002", "AddressBar", "addressEdit"):
                address_bar = ctrl
                break
            if ctrl.Name in (
                "Address and search bar",
                "アドレスと検索バー",
                "地址和搜索栏",
            ) and ctrl.ControlTypeName in ("EditControl", "DocumentControl"):
                address_bar = ctrl
                break

        if not address_bar:
            logger.error("Could not find Edge address bar in UIA tree.")
            return None

        val_pat = address_bar.GetValuePattern()
        url = val_pat.Value if val_pat else address_bar.Name
        logger.info("Resolved URL: %s", url)
        return url
    except Exception as exc:
        logger.exception("UI Automation failed: %s", exc)
        return None


def fetch_bytes(url: str, limit: int = HARD_LIMIT_BYTES) -> bytes:
    logger.info("Fetching up to %d bytes from %s", limit, url)
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
            if len(data) >= limit:
                break
        return data[:limit]

    if parsed.scheme == "file":
        path = urllib.request.url2pathname(parsed.path)
        with open(path, "rb") as f:
            return f.read(limit)

    if os.path.exists(url):
        with open(url, "rb") as f:
            return f.read(limit)

    raise ValueError(f"Unsupported URL scheme or missing file: {url}")


def extract_pdf_first_page_text(data: bytes) -> str | None:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        reader = PdfReader(tmp_path)
        if len(reader.pages) == 0:
            return None
        text = reader.pages[0].extract_text()
        if text and text.strip():
            return text.strip()
        return None
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return None
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def extract_text_from_url(url: str) -> str:
    data = fetch_bytes(url)
    if not data:
        return ""

    is_pdf = data.startswith(b"%PDF") or url.lower().endswith(".pdf")

    if is_pdf:
        text = extract_pdf_first_page_text(data)
        if text is None:
            logger.info("PDF first page has no extractable text; skipping.")
            return ""
        return clean_text(text)

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
        text = extract_text_from_url(url)
        logger.info("Page/PDF mode: %d chars from %s", len(text), url)
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
