#!/usr/bin/env python3
"""
test-pipeline.py - Standalone test of the Piper + winsound audio path.
Run this from Git Bash or CMD to verify paths and audio output without AHK.
"""
import os
import sys
import tempfile
import subprocess

# Same resolution logic as read-aloud.py
PIPER_BIN = os.environ.get(
    "PIPER_BIN",
    os.path.join(os.path.expanduser("~"), r"AppData\Roaming\Python\Python314\Scripts\piper.exe"),
)
PIPER_VOICE = os.environ.get(
    "PIPER_VOICE",
    os.path.join(os.path.expanduser("~"), r"pipervoices\en_US-lessac-medium.onnx"),
)

TEMP_DIR = tempfile.gettempdir()
TEST_TEXT = "Hello. This is a test of the read aloud audio pipeline."

print("=" * 50)
print("Read Aloud - Audio Pipeline Test")
print("=" * 50)
print(f"PIPER_BIN   = {PIPER_BIN}")
print(f"PIPER_VOICE = {PIPER_VOICE}")
print(f"piper.exe exists   : {os.path.isfile(PIPER_BIN)}")
print(f"voice model exists : {os.path.isfile(PIPER_VOICE)}")

if not os.path.isfile(PIPER_BIN):
    print("\nERROR: piper.exe not found.")
    print("Set the PIPER_BIN user environment variable to the full path.")
    sys.exit(1)

if not os.path.isfile(PIPER_VOICE):
    print("\nERROR: Voice model .onnx not found.")
    print("Set the PIPER_VOICE user environment variable to the full path.")
    sys.exit(1)

text_path = os.path.join(TEMP_DIR, "test-piper-text.txt")
wav_path = os.path.join(TEMP_DIR, "test-piper-audio.wav")

with open(text_path, "w", encoding="utf-8") as f:
    f.write(TEST_TEXT)

for p in [wav_path]:
    try:
        os.remove(p)
    except FileNotFoundError:
        pass

cmd = [
    PIPER_BIN,
    "--model", PIPER_VOICE,
    "--file", text_path,
    "--output_file", wav_path,
]

print(f"\nRunning: {' '.join(cmd)}")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = proc.communicate(timeout=60)

print(f"Piper return code: {proc.returncode}")
if stdout:
    print("Piper stdout:", stdout.decode("utf-8", errors="ignore"))
if stderr:
    print("Piper stderr:", stderr.decode("utf-8", errors="ignore"))

if proc.returncode != 0:
    print("\nERROR: Piper returned non-zero. Check stderr above.")
    sys.exit(1)

if not os.path.isfile(wav_path):
    print("\nERROR: Piper did not create the WAV file.")
    sys.exit(1)

print(f"\nWAV created: {wav_path}")
print("Playing audio now...")

import winsound
winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_SYNC)
print("\nDone. If you heard the test phrase, the audio pipeline is working.")
