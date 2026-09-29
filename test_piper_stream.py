import subprocess
import numpy as np
import sounddevice as sd
import sys

PIPER = r"C:\users\myuser\appdata\roaming\python\python314\scripts\piper"
VOICE = r"C:\users\myuser\pipervoices\en_US-lessac-medium.onnx"

# Check sample rate in the voice json
import json
with open(VOICE + ".json") as f:
    config = json.load(f)
SAMPLE_RATE = config.get("audio", {}).get("sample_rate", 22050)
print(f"Voice sample rate: {SAMPLE_RATE}")

proc = subprocess.Popen(
    [PIPER, "-m", VOICE, "--output-raw"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

stdout, stderr = proc.communicate(input=b"Hello, this is a test of direct streaming.\n")

if proc.returncode != 0:
    print("Piper failed:", stderr.decode())
    sys.exit(1)

audio = np.frombuffer(stdout, dtype=np.int16)
print(f"Got {len(audio)} samples")

sd.play(audio, samplerate=SAMPLE_RATE)
sd.wait()
print("Done!")