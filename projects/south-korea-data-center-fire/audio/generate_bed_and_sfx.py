#!/usr/bin/env python3
"""Synthesise this project's music bed and foley track. Original, deterministic (seeded), no samples, no licences.

  bed.wav        A-minor drone with sparse slow plucks; a server-room hum (mains harmonics plus fan noise)
                 that dies as the wall goes dark, returns thinly with the count, and swells back with the recovery
  sfx-track.wav  typewriter and counter ticks, pen scratches, stamp thuds, ember and flame crackle,
                 soft switch-off clicks, blue-tile blips. No whooshes on scene dissolves.
Cue times mirror src/index.html (visual events) against audio/timeline.json (measured narration).
Run: .venv/bin/python audio/generate_bed_and_sfx.py   (from the repo root; needs numpy + scipy)
"""
import wave
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).parent
SR = 44100
END = 98.0
rng = np.random.default_rng(2025)


def t(n):
    return np.arange(int(n * SR)) / SR


def write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def env(n, a=0.005, d=0.2):
    k = t(n)
    return np.minimum(k / a, 1) * np.exp(-k / d)


def place(buf, snd, at, gain=1.0):
    i = int(at * SR)
    j = min(len(buf), i + len(snd))
    if 0 <= i < len(buf):
        buf[i:j] += gain * snd[: j - i]


def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    return lfilter([1 - a], [1, -a], x)


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)


# ---------------------------------------------------------------- music bed
tt = t(END)
bed = np.zeros_like(tt)
# A1 E2 C3 A3 drone, slow breathing
for f, g in ((55.0, 0.6), (82.41, 0.42), (130.81, 0.30), (220.0, 0.12)):
    bed += g * (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt)) * (0.78 + 0.22 * np.sin(2 * np.pi * 0.05 * tt + f))
level = np.interp(tt, [0, 1.5, 13, 14, 27, 28, 44, 46, 65, 66, 82, 86, 94, END],
                  [0.0, 0.45, 0.45, 0.35, 0.35, 0.45, 0.55, 0.30, 0.30, 0.40, 0.55, 0.50, 0.40, 0.0])
bed *= level
# a cold minor second hangs under the fire and the burn
bed += 0.10 * np.sin(2 * np.pi * 58.27 * tt) * np.interp(tt, [0, 20, 23, 38, 46, END], [0, 0, 1, 1, 0, 0])
# sparse falling plucks (A minor pentatonic), slow
scale = [440.0, 392.0, 329.63, 293.66, 261.63, 220.0]
n = 0
for at in np.arange(2.0, END - 3.0, 4.4):
    q = 0.10 if 45 < at < 66 else (0.18 if 20 < at < 40 else 0.14)
    f = scale[int(rng.integers(0, len(scale)))] * (0.5 if n % 3 == 0 else 1.0)
    d = 2.2
    k = t(d)
    snd = (np.sin(2 * np.pi * f * k) + 0.3 * np.sin(2 * np.pi * 2 * f * k) * np.exp(-k * 4)) * env(d, 0.01, 0.9)
    place(bed, snd, at, q * 0.3)
    n += 1
# server-room hum: mains harmonics + fan noise. Full while the wall is lit, gone when it dims,
# faint under the count, absent while the shelves burn, and returning with the recovery.
fan = lp(rng.standard_normal(len(tt)), 900) - lp(rng.standard_normal(len(tt)), 250)
hum = (0.5 * np.sin(2 * np.pi * 100 * tt) + 0.35 * np.sin(2 * np.pi * 200 * tt) + 0.2 * np.sin(2 * np.pi * 300 * tt)) + 0.9 * fan
hum_level = np.interp(tt, [0, 1.0, 4.8, 9.9, 13.2, 27.5, 29, 32.3, 38, 39, 62, 63, 68, 75, 76.5, 82, END],
                      [0, 0.30, 0.30, 0.18, 0.0, 0.0, 0.14, 0.14, 0.0, 0.0, 0.0, 0.0, 0.0, 0.22, 0.10, 0.0, 0.0])
bed += 0.18 * hum * hum_level

# level the bed against the measured narration so it sits ~16 dB under the voice after the mux (x0.6)
voice_path = HERE / "narration-full.wav"
if voice_path.exists():
    with wave.open(str(voice_path), "rb") as w:
        v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    target = rms_db(v) - 11.6
else:
    target = -30.0
bed = bed / (np.sqrt(np.mean(np.square(bed))) + 1e-9) * 10 ** (target / 20)
write(HERE / "bed.wav", bed)

# ---------------------------------------------------------------- foley
sfx = np.zeros(int(END * SR))


def tick(at, g=0.3, f=3200):
    k = t(0.03)
    place(sfx, (rng.standard_normal(len(k)) * 0.5 + np.sin(2 * np.pi * f * k)) * env(0.03, 0.0005, 0.006), at, g * 0.6)


def thud(at, f=88, g=0.9, dur=0.28):
    k = t(dur)
    body = np.sin(2 * np.pi * f * (1 - 0.35 * k / dur) * k) * env(dur, 0.002, 0.07)
    nz = lp(rng.standard_normal(len(k)), 1800) * env(dur, 0.001, 0.02)
    place(sfx, body + 0.5 * nz, at, g * 0.8)


def scratch(at, dur=0.5, g=0.4):
    k = t(dur)
    x = rng.standard_normal(len(k))
    x = lp(x, 6000) - lp(x, 1500)
    place(sfx, x * np.minimum(k / 0.04, 1) * np.exp(-k / (dur * 0.5)), at, g * 1.0)


def tap(at, g=0.5):
    k = t(0.08)
    place(sfx, np.sin(2 * np.pi * 1700 * k) * env(0.08, 0.001, 0.015), at, g * 0.4)


def blip(at, f, g=0.3):
    k = t(0.09)
    place(sfx, np.sin(2 * np.pi * f * k) * env(0.09, 0.002, 0.03), at, g * 0.5)


def roar(a, b, g=0.2, fc=500):
    k = t(b - a)
    x = lp(rng.standard_normal(len(k)), fc) * np.minimum(k / 1.0, 1) * np.minimum((b - a - k) / 1.0, 1)
    place(sfx, x, a, g * 2.0)


def crackle(a, b, rate, g=0.25):
    for at in np.sort(rng.uniform(a, b, int((b - a) * rate))):
        k = t(0.02)
        place(sfx, rng.standard_normal(len(k)) * env(0.02, 0.0004, 0.004), at, g * float(rng.uniform(0.4, 1.0)))


def type_run(at, chars, cps, g=0.22):
    for i in range(chars):
        tick(at + i / cps, g, 2400 + 400 * (i % 3))


def count_run(a, b, g=0.2, f0=2800, step=0.08):
    for at in np.arange(a, b, step):
        tick(at, g, f0 + 8 * (at - a) * 100)


# Scene 1 (0 - 13.97): tiles lay out, date, ember, the wall dims
type_run(0.3, 27, 30)
for at in np.arange(0.5, 3.1, 0.06):
    tick(at, 0.07, 3400)
thud(1.5, 80, 0.4, 0.3)
crackle(4.9, 9.9, 7, 0.2)
for i in range(60):
    tick(5.6 + i * 0.05, 0.10, 1200)
for at in np.sort(rng.uniform(9.9, 12.9, 70)):
    tick(at, 0.08, 900 + float(rng.integers(0, 400)))
# Scene 2 (13.97 - 27.6): cutaway, batteries, sparks, smoke, flames, the question
type_run(14.2, 15, 28)
for at in np.arange(14.4, 15.6, 0.3):
    scratch(at, 0.3, 0.2)
for n_, at in enumerate((17.5, 18.05, 18.6)):
    thud(at + 1.9 + 0.7, 100, 0.35, 0.12)
crackle(20.99, 23.0, 14, 0.3)
roar(21.87, 27.2, 0.18, 380)
crackle(22.89, 27.0, 10, 0.22)
tap(24.4, 0.4)
thud(25.4, 82, 0.8)
# Scene 3 (27.6 - 44.9): count, the burn, the dim, the Offline stamps
count_run(28.6, 31.2, 0.2, 2600, 0.07)
crackle(32.4, 34.0, 30, 0.25)
count_run(32.4, 33.6, 0.18, 2400, 0.06)
thud(32.6, 70, 0.4, 0.2)
count_run(34.4, 36.2, 0.18, 2200, 0.07)
for at in np.sort(rng.uniform(34.3, 37.9, 40)):
    tick(at, 0.09, 700 + float(rng.integers(0, 300)))
for at in (39.08, 40.5, 41.9):
    scratch(at, 0.3, 0.18)
for at in (42.7, 43.2, 43.7):
    thud(at + 0.2, 75, 0.7, 0.3)
# Scene 4 (44.9 - 65.77): shelves, backups, G-Drive, the count, the fire
type_run(45.2, 7, 28)
for i in range(5):
    tick(46.0 + i * 0.18, 0.18, 1900)
    thud(48.0 + 0.8 + i * 0.25, 110, 0.28, 0.12)
thud(50.5, 80, 0.5, 0.3)
thud(51.3, 78, 0.9)
count_run(56.1, 58.5, 0.2, 2300, 0.07)
crackle(63.1, 65.5, 28, 0.28)
roar(63.1, 65.8, 0.16, 420)
# Scene 5 (65.77 - 82.8): the recovery, the folder that does not fill
type_run(66.0, 8, 26)
for a, b, nt in ((68.7, 70.5, 20), (71.4, 73.0, 40), (73.8, 75.3, 30)):
    for i, at in enumerate(np.linspace(a, b, nt)):
        blip(at, 700 + 900 * i / nt, 0.18)
    count_run(a, b, 0.14, 2500, 0.08)
for i in range(3):
    tap(77.2 + 0.55 * i + 0.3, 0.4)
for at in np.linspace(79.4, 81.1, 16):
    tick(at, 0.12, 1700)
# Scene 6 (82.8 - 98): faces-less outlines, the stamp, the folder and its copy
type_run(83.2, 14, 26)
for i in range(4):
    thud(84.2 + 0.4 * i + 0.2, 140 + 10 * i, 0.3, 0.14)
thud(87.5, 80, 0.9)
thud(89.8, 75, 0.5, 0.25)
tap(93.3, 0.5)
thud(95.7, 62, 0.6, 0.8)

peak = np.max(np.abs(sfx))
sfx = sfx / (peak or 1) * 0.16
write(HERE / "sfx-track.wav", sfx)
print("bed.wav + sfx-track.wav written", END, "s; bed target %.1f dBFS rms" % target)
