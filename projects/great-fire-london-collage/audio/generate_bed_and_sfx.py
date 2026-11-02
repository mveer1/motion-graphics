#!/usr/bin/env python3
"""Synthesise this project's music bed and foley track. Original, deterministic (seeded), no samples, no licences.

  bed.wav        warm low pad + soft marimba-style plucks; thins to almost nothing in s4, warms in s5
  sfx-track.wav  paper slides, stamp thuds, pin tap, crackle, counter ticks, typewriter ticks, brick thocks
Cue times come from audio/cues.json (shared with src/index.html). Run: .venv/bin/python generate_bed_and_sfx.py
"""
import json, wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
SR = 44100
C = json.loads((HERE / "cues.json").read_text())
END = C["end"]
rng = np.random.default_rng(1666)


def t(n): return np.arange(int(n * SR)) / SR
def write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
def env(n, a=0.005, d=0.2):
    k = t(n); return np.minimum(k / a, 1) * np.exp(-k / d)
def place(buf, snd, at, gain=1.0):
    i = int(at * SR); j = min(len(buf), i + len(snd))
    if i < len(buf): buf[i:j] += gain * snd[: j - i]
def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y

# ---- bed: A minor pad (A2 C3 E3 G3), slow LFO, plucks on a pentatonic walk
bed = np.zeros(int(END * SR))
tt = t(END)
for f, g in ((110.0, 0.55), (130.81, 0.4), (164.81, 0.4), (196.0, 0.25)):
    bed += g * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * tt + f))
level = np.ones_like(tt) * 0.55
level = np.interp(tt, [0, 0.8, 24.5, 25.5, 32.4, 34.0, 41.0, 43.0, END], [0, 0.55, 0.55, 0.16, 0.16, 0.62, 0.62, 0.5, 0.0])
bed *= level * 0.09
scale = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0]
step = 60 / 72 * 2
n = 0
for at in np.arange(1.2, END - 1.5, step):
    q = 0.16 if 25.0 < at < 32.5 else (0.30 if at > 33 else 0.24)
    f = scale[int(rng.integers(0, len(scale)))] * (0.5 if n % 4 == 0 else 1.0)
    d = 1.1; k = t(d)
    snd = (np.sin(2 * np.pi * f * k) + 0.4 * np.sin(2 * np.pi * 3 * f * k) * np.exp(-k * 8)) * env(d, 0.004, 0.35)
    place(bed, snd, at, q * 0.08 * (1.0 if n % 2 else 0.7)); n += 1
write(HERE / "bed.wav", bed)

# ---- foley
sfx = np.zeros(int(END * SR))
def slide(at, dur=0.45, g=0.5):
    k = t(dur); x = rng.standard_normal(len(k)); x = lp(x, 2800) - lp(x, 400)
    place(sfx, x * np.sin(np.pi * k / dur) ** 2, at, g * 0.5)
def thud(at, f=88, g=0.9, dur=0.28):
    k = t(dur); body = np.sin(2 * np.pi * f * (1 - 0.35 * k / dur) * k) * env(dur, 0.002, 0.07)
    nz = lp(rng.standard_normal(len(k)), 1800) * env(dur, 0.001, 0.02)
    place(sfx, body + 0.5 * nz, at, g * 0.8)
def tap(at, g=0.5):
    k = t(0.08); place(sfx, np.sin(2 * np.pi * 1700 * k) * env(0.08, 0.001, 0.015), at, g * 0.4)
def tick(at, g=0.3, f=3200):
    k = t(0.03); place(sfx, (rng.standard_normal(len(k)) * 0.5 + np.sin(2 * np.pi * f * k)) * env(0.03, 0.0005, 0.006), at, g * 0.25)
def scratch(at, dur=0.5, g=0.4):
    k = t(dur); x = rng.standard_normal(len(k)); x = lp(x, 6000) - lp(x, 1500)
    place(sfx, x * np.minimum(k / 0.04, 1) * np.exp(-k / 0.25), at, g * 0.5)
def crackle(a, b, g=0.3):
    for at in np.sort(rng.uniform(a, b, int((b - a) * 40))):
        k = t(0.012); fade = 1 - (at - a) / (b - a)
        place(sfx, rng.standard_normal(len(k)) * env(0.012, 0.0004, 0.003), at, g * 0.3 * (0.4 + fade))
def rise(a, b, g=0.25):
    k = t(b - a); f = np.linspace(180, 260, len(k)); ph = 2 * np.pi * np.cumsum(f) / SR
    place(sfx, np.sin(ph) * np.minimum(k / 0.8, 1) * np.minimum((b - a - k) / 0.8, 1), a, g * 0.4)

s1, s2, s3, s4, s5 = (C[k] for k in ("s1", "s2", "s3", "s4", "s5"))
slide(s1["map"], 0.5); slide(s1["tape"], 0.35, 0.4); thud(s1["stamp"], 95); tap(s1["flame"]); thud(s1["bakery"], 140, 0.5, 0.18); thud(s1["banner"], 82, 1.0)
for k in ("d1", "d2", "d3", "d4"): thud(s2[k], 90, 0.8)
slide(s2["push"], 0.7, 0.5); slide(s2["wind"], 0.5, 0.35); crackle(s2["d1"], s2["wind"] + 1.4)
slide(s3["wipe"], 0.7, 0.45)
for at in np.arange(s3["counter"], s3["counter"] + 2.5, 0.09): tick(at, 0.35, 2800 + 8 * (at - s3["counter"]) * 100)
rise(s3["counter"], s3["counter"] + 2.6)
for i in range(12): tick(s3["houseChar"] + i * 0.08, 0.28, 900)
for i in range(4): thud(s3["churches"] + i * 0.15, 120, 0.35, 0.15)
thud(s3["churchChar"], 70, 0.7, 0.4); thud(s3["domeChar"], 60, 0.8, 0.5)
thud(s3["ruin"], 80, 1.1)
for at in np.arange(s4["line1"], s4["line1"] + 1.4, 0.075): tick(at, 0.22, 2400)
for at in np.arange(s4["line2"], s4["line2"] + 1.0, 0.075): tick(at, 0.22, 2400)
thud(s4["six"], 100, 0.55, 0.3)
for at in np.arange(s4["line3"], s4["line3"] + 1.2, 0.08): tick(at, 0.18, 2400)
slide(s5["match"] + 0.05, 0.3, 0.3)
for i in range(7): thud(s5["brick"] + i * 0.2, 150 + 8 * i, 0.4, 0.14)
scratch(s5["strike"], 0.45); slide(s5["tape"], 0.3, 0.3)
for i in range(4): thud(s5["wren"] + i * 0.12, 110, 0.35, 0.16)
rise(s5["monument"], s5["monument"] + 2.2, 0.3)
thud(s5["label"], 85, 0.7); thud(s5["title"], 78, 0.9)
peak = np.max(np.abs(sfx)); sfx = sfx / (peak or 1) * 0.55
write(HERE / "sfx-track.wav", sfx)
print("bed.wav + sfx-track.wav written", END, "s")
