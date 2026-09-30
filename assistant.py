"""
Local Voice Assistant
- whisper.cpp (whisper-cli.exe) for STT
- Piper for TTS
- Modes: echo | stt
- Stop: hotkey toggle, sleepword ("stop"), or 30s cap
"""
from __future__ import annotations

import os
import re
import sys
import time
import wave
import queue
import shutil
import signal
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------
# CONFIG  -- edit here, no separate ini file
# ---------------------------------------------------------------
CONFIG = {
    # --- whisper.cpp ---
    "whisper_bin":    r"C:\Users\myuser\dev\whisper-bin\whisper-cli.exe",
    "whisper_model":  r"C:\Users\Apps\voiceassistant\models\ggml-tiny.en.bin",
    "whisper_threads": 4,
    "whisper_lang":   "en",

    # --- Piper ---
    "piper_exe":      r"C:\Users\myuser\AppData\Roaming\Python\Python314\Scripts\piper.exe",
    "piper_voice":    r"C:\Users\myuser\pipervoices\en_US-lessac-medium.onnx",

    # --- Audio ---
    "samplerate":     16000,
    "channels":       1,
    "max_seconds":    30,           # safety cap

    # --- Sleepword ---
    "sleepwords":     ["stop", "cancel", "halt", "nevermind"],
    "sleep_check_interval": 1.0,    # seconds between rolling checks
    "sleep_window":   2.0,          # seconds of audio per check

    # --- Runtime ---
    "root":           r"C:\Users\Apps\voiceassistant",
    "toast_app_id":   "Voice Assistant",
}

TEMP_DIR = Path(CONFIG["root"]) / "temp"
LOG_DIR  = Path(CONFIG["root"]) / "logs"
REC_WAV       = TEMP_DIR / "recording.wav"
REC_FLAG      = TEMP_DIR / "recording.flag"
STOP_FLAG     = TEMP_DIR / "stop.flag"
SLEEP_WAV     = TEMP_DIR / "sleepchunk.wav"
REPLY_WAV     = TEMP_DIR / "reply.wav"

# ---------------------------------------------------------------
# Logging
# ---------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "assistant.log"),
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("va")

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def toast(title: str, msg: str):
    try:
        from winotify import Notification
        Notification(app_id=CONFIG["toast_app_id"], title=title, msg=msg).show()
    except Exception as e:
        log.warning(f"toast failed: {e}")

def cleanup_flags():
    for f in (REC_FLAG, STOP_FLAG):
        try:
            f.unlink()
        except FileNotFoundError:
            pass

# ---------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------
class Recorder:
    def __init__(self):
        import sounddevice as sd
        self.sd = sd
        self.q: queue.Queue = queue.Queue()
        self.frames: list = []
        self.stop_event = threading.Event()
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.warning(f"audio status: {status}")
        self.q.put(bytes(indata))

    def start(self):
        self.frames.clear()
        self.stop_event.clear()
        self.stream = self.sd.RawInputStream(
            samplerate=CONFIG["samplerate"],
            channels=CONFIG["channels"],
            dtype="int16",
            callback=self._callback,
        )
        self.stream.start()
        REC_FLAG.write_text("1")

    def stop(self):
        self.stop_event.set()

    def _drain_queue(self):
        while True:
            try:
                self.frames.append(self.q.get_nowait())
            except queue.Empty:
                break

    def run_until_stopped(self):
        """Blocking record loop. Returns (duration_sec, hit_stop_word)."""
        start = time.time()
        last_sleep_check = 0.0
        hit_sleep = False

        try:
            while not self.stop_event.is_set():
                elapsed = time.time() - start

                # safety cap
                if elapsed >= CONFIG["max_seconds"]:
                    log.info(f"safety cap hit at {elapsed:.1f}s")
                    break

                # hotkey stop flag (temp-file toggle)
                if STOP_FLAG.exists():
                    log.info("stop flag detected")
                    break

                # sleepword rolling check
                if elapsed - last_sleep_check >= CONFIG["sleep_check_interval"]:
                    last_sleep_check = elapsed
                    if self._check_sleepword():
                        log.info("sleepword detected")
                        hit_sleep = True
                        break

                time.sleep(0.05)
        finally:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self._drain_queue()
            REC_FLAG.unlink(missing_ok=True)
            STOP_FLAG.unlink(missing_ok=True)

        duration = time.time() - start
        self._write_wav(REC_WAV)
        return duration, hit_sleep

    def _write_wav(self, path: Path):
        import numpy as np
        if not self.frames:
            log.warning("no audio frames captured")
            # write an empty wav so downstream doesn't crash
            with wave.open(str(path), "wb") as w:
                w.setnchannels(CONFIG["channels"])
                w.setsampwidth(2)
                w.setframerate(CONFIG["samplerate"])
                w.writeframes(b"")
            return
        raw = b"".join(self.frames)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(CONFIG["channels"])
            w.setsampwidth(2)
            w.setframerate(CONFIG["samplerate"])
            w.writeframes(raw)

    def _check_sleepword(self) -> bool:
        """Take last N seconds of buffered audio, transcribe, check for stop words."""
        window_bytes = int(CONFIG["sleep_window"] * CONFIG["samplerate"] * 2)
        raw = b"".join(self.frames)
        if len(raw) < window_bytes:
            return False
        chunk = raw[-window_bytes:]
        try:
            with wave.open(str(SLEEP_WAV), "wb") as w:
                w.setnchannels(CONFIG["channels"])
                w.setsampwidth(2)
                w.setframerate(CONFIG["samplerate"])
                w.writeframes(chunk)
            text = run_whisper(SLEEP_WAV, quiet=True)
            if not text:
                return False
            words = re.findall(r"[a-z']+", text.lower())
            stopset = {w.lower() for w in CONFIG["sleepwords"]}
            if stopset & set(words):
                log.info(f"sleepword in: {text!r}")
                return True
        except Exception as e:
            log.warning(f"sleepword check failed: {e}")
        return False

# ---------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------
def run_whisper(wav_path: Path, quiet: bool = False) -> str:
    cmd = [
        CONFIG["whisper_bin"],
        "-m", CONFIG["whisper_model"],
        "-f", str(wav_path),
        "-l", CONFIG["whisper_lang"],
        "-t", str(CONFIG["whisper_threads"]),
        "-nt",           # no timestamps
        "-otxt",         # output .txt
        "-of", str(wav_path.with_suffix("")),  # output prefix
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error(f"whisper failed rc={proc.returncode}: {proc.stderr.strip()[:300]}")
        return ""
    txt_file = wav_path.with_suffix(".txt")
    if not txt_file.exists():
        return ""
    text = txt_file.read_text(encoding="utf-8", errors="replace").strip()
    try:
        txt_file.unlink()
    except Exception:
        pass
    if not quiet:
        log.info(f"whisper raw: {text!r}")
    return text

def clean_transcript(text: str) -> str:
    # strip [bracketed] cues, collapse whitespace
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\([^\)]*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ---------------------------------------------------------------
# Piper
# ---------------------------------------------------------------
def speak(text: str) -> float:
    if not text.strip():
        return 0.0
    t0 = time.time()
    cmd = [
        CONFIG["piper_exe"],
        "-m", CONFIG["piper_voice"],
        "-f", str(REPLY_WAV),
    ]
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error(f"piper failed rc={proc.returncode}: {proc.stderr.strip()[:300]}")
        return 0.0
    # play via winsound (stdlib, no deps)
    import winsound
    winsound.PlaySound(str(REPLY_WAV), winsound.SND_FILENAME)
    return time.time() - t0

# ---------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------
def to_clipboard(text: str) -> float:
    t0 = time.time()
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception as e:
        log.warning(f"pyperclip failed: {e}")
    return time.time() - t0

# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("echo", "stt"):
        print("usage: assistant.py [echo|stt]")
        sys.exit(2)
    mode = sys.argv[1]

    cleanup_flags()

    # toggle check: if a recording is already in progress, just drop STOP flag
    if REC_FLAG.exists():
        STOP_FLAG.write_text("1")
        log.info("second press: stop flag dropped")
        return

    t_start = time.time()
    toast("Voice Assistant", f"{mode.upper()} — recording…")

    rec = Recorder()
    try:
        rec.start()
        duration, hit_sleep = rec.run_until_stopped()
    except Exception as e:
        log.exception(f"recorder error: {e}")
        toast("Voice Assistant", f"error: {e}")
        cleanup_flags()
        return

    if hit_sleep:
        toast("Voice Assistant", "stopped by sleepword")
        log.info(f"mode={mode}  rec={duration:.2f}s  abort=sleepword")
        return

    if duration < 0.3:
        toast("Voice Assistant", "too short — ignored")
        log.info(f"mode={mode}  rec={duration:.2f}s  abort=too-short")
        return

    # transcribe
    t_tr = time.time()
    text = clean_transcript(run_whisper(REC_WAV))
    tr_time = time.time() - t_tr

    if not text:
        toast("Voice Assistant", "no speech detected")
        log.info(f"mode={mode}  rec={duration:.2f}s  transcribe={tr_time:.2f}s  empty")
        return

    # clipboard
    cp_time = to_clipboard(text)

    # echo mode: speak
    speak_time = 0.0
    if mode == "echo":
        speak_time = speak(text)

    total = time.time() - t_start
    log.info(
        f"mode={mode}  rec={duration:.2f}s  transcribe={tr_time:.2f}s  "
        f"copy={cp_time:.2f}s  piper={speak_time:.2f}s  total={total:.2f}s"
    )
    toast("Voice Assistant", f"done — {text[:80]}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup_flags()
        sys.exit(130)