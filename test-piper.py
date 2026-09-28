#!/usr/bin/env python3
"""
test-piper.py - Quick diagnostic to verify Piper TTS is working on Windows 11.
Run this from Git Bash, CMD, or PowerShell to check:
  1. Piper binary exists and is accessible
  2. Voice model files exist
  3. Piper can generate audio
  4. Windows can play the audio
"""

import os
import sys
import time
import tempfile
import subprocess

if sys.platform == "win32":
    _CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    _CREATE_NO_WINDOW = 0


def run_hidden(cmd, **kwargs):
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 30)
    if sys.platform == "win32":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
    return subprocess.run(cmd, **kwargs)


PIPER_BIN = os.environ.get(
    "PIPER_BIN",
    os.path.join(os.path.expanduser("~"), r"AppData\Roaming\Python\Python314\Scripts\piper.exe"),
)
PIPER_VOICE = os.environ.get(
    "PIPER_VOICE",
    os.path.join(os.path.expanduser("~"), r"pipervoices\en_US-lessac-medium.onnx"),
)

VOICE_JSON = PIPER_VOICE + ".json"
TEMP_DIR = tempfile.gettempdir()
TEST_TEXT_PATH = os.path.join(TEMP_DIR, "piper-test-text.txt")
TEST_WAV_PATH = os.path.join(TEMP_DIR, "piper-test-audio.wav")

errors = []
warnings = []

def section(title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")

def ok(msg):
    print(f"  [OK]   {msg}")

def fail(msg):
    print(f"  [FAIL] {msg}")
    errors.append(msg)

def warn(msg):
    print(f"  [WARN] {msg}")
    warnings.append(msg)

def info(msg):
    print(f"  [INFO] {msg}")


section("1. Piper binary")
info(f"PIPER_BIN = {PIPER_BIN}")
if os.path.isfile(PIPER_BIN):
    ok(f"piper.exe found at: {PIPER_BIN}")
    # Try to get version
    try:
        result = run_hidden([PIPER_BIN, "--help"], timeout=5)
        if "piper" in result.stderr.lower() or "usage" in result.stderr.lower():
            ok("piper.exe responds to --help")
        elif "piper" in result.stdout.lower() or "usage" in result.stdout.lower():
            ok("piper.exe responds to --help")
        else:
            warn("piper.exe ran but output was unexpected")
            info(f"stdout: {result.stdout[:200]}")
            info(f"stderr: {result.stderr[:200]}")
    except Exception as e:
        fail(f"Could not run piper.exe --help: {e}")
else:
    fail(f"piper.exe NOT found at: {PIPER_BIN}")
    info("Set PIPER_BIN environment variable to the correct path.")


section("2. Voice model files")
info(f"PIPER_VOICE = {PIPER_VOICE}")
if os.path.isfile(PIPER_VOICE):
    ok(f"Voice model .onnx found: {PIPER_VOICE}")
    size_mb = os.path.getsize(PIPER_VOICE) / (1024 * 1024)
    info(f"  Size: {size_mb:.1f} MB")
else:
    fail(f"Voice model .onnx NOT found: {PIPER_VOICE}")

if os.path.isfile(VOICE_JSON):
    ok(f"Voice config .onnx.json found: {VOICE_JSON}")
else:
    warn(f"Voice config .onnx.json NOT found: {VOICE_JSON}")
    info("  Piper may still work if the config is embedded in the .onnx file.")


section("3. Generate test audio")
if errors:
    print("  Skipping audio generation because previous checks failed.")
else:
    test_text = "Hello, this is a test of the Piper text to speech system on Windows 11."
    with open(TEST_TEXT_PATH, "w", encoding="utf-8") as f:
        f.write(test_text)
    info(f"Test text written to: {TEST_TEXT_PATH}")

    piper_cmd = [
        PIPER_BIN,
        "--model", PIPER_VOICE,
        "--file", TEST_TEXT_PATH,
        "--output_file", TEST_WAV_PATH,
    ]
    info(f"Running: {' '.join(piper_cmd)}")

    try:
        result = run_hidden(piper_cmd, timeout=60)
        if result.returncode == 0:
            ok("Piper completed successfully")
        else:
            fail(f"Piper exited with code {result.returncode}")
            info(f"stderr: {result.stderr[:500]}")
    except Exception as e:
        fail(f"Failed to run piper: {e}")

    if os.path.isfile(TEST_WAV_PATH):
        size_kb = os.path.getsize(TEST_WAV_PATH) / 1024
        ok(f"WAV file created: {TEST_WAV_PATH} ({size_kb:.1f} KB)")
    else:
        fail("WAV file was NOT created")


section("4. Play test audio")
if not os.path.isfile(TEST_WAV_PATH):
    print("  Skipping playback because WAV file was not generated.")
else:
    info("Playing WAV with winsound...")
    try:
        import winsound
        winsound.PlaySound(TEST_WAV_PATH, winsound.SND_FILENAME | winsound.SND_SYNC)
        ok("Audio playback completed")
    except Exception as e:
        fail(f"Could not play audio: {e}")


section("5. Environment summary")
info(f"Python: {sys.executable}")
info(f"Python version: {sys.version}")
info(f"Platform: {sys.platform}")
info(f"TEMP_DIR: {TEMP_DIR}")
info(f"PIPER_BIN: {PIPER_BIN}")
info(f"PIPER_VOICE: {PIPER_VOICE}")

section("RESULT")
if errors:
    print(f"  Found {len(errors)} error(s). Fix them before using read-aloud.py.")
    sys.exit(1)
else:
    if warnings:
        print(f"  Found {len(warnings)} warning(s), but piper should work.")
    else:
        print("  All checks passed! Piper TTS is ready to use.")
    sys.exit(0)
