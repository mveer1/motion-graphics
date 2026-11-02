#!/usr/bin/env python3
"""Synthesise this project's music bed and foley track. Original, deterministic (seeded), no samples, no licences.

  bed.wav        D-minor drone with sparse slow plucks; night-insect ambience that the gas cuts off;
                 a low swell under the cloud; thins in the numbers scenes; warms slightly at dawn
  sfx-track.wav  typewriter and counter ticks, pen scratches, stamp thuds, a thin siren that stops abruptly,
                 window clicks, footsteps, truck rumble. No whooshes on scene dissolves.
Cue times mirror src/index.html (visual events) against audio/timeline.json (measured narration).
Run: .venv/bin/python audio/generate_bed_and_sfx.py   (from the repo root; needs numpy + scipy)
"""
import wave
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).parent
SR = 44100
END = 104.5
rng = np.random.default_rng(1984)


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
# D2 A2 F3 C4 drone, slow breathing
for f, g in ((73.42, 0.6), (110.0, 0.42), (174.61, 0.3), (261.63, 0.14)):
    bed += g * (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt)) * (0.78 + 0.22 * np.sin(2 * np.pi * 0.06 * tt + f))
# a cold minor second hangs under the cloud and the numbers
bed += 0.10 * np.sin(2 * np.pi * 77.78 * tt) * np.interp(tt, [0, 38, 42, 58, 70, 104.5], [0, 0, 1, 1, 0.3, 0])
level = np.interp(tt, [0, 1.5, 13, 14, 39, 43, 50, 58, 60, 87, 95, 101, END],
                  [0.0, 0.50, 0.50, 0.40, 0.55, 0.85, 0.85, 0.55, 0.30, 0.30, 0.50, 0.50, 0.0])
bed *= level
# swell under the cloud
sw = np.interp(tt, [39.5, 44, 50, 54, 58.5], [0, 0.35, 0.5, 0.3, 0])
bed += sw * lp(rng.standard_normal(len(tt)), 140) * 4.0
# sparse falling plucks (D minor pentatonic), slow
scale = [293.66, 261.63, 220.0, 196.0, 174.61, 146.83]
n = 0
for at in np.arange(2.0, END - 3.0, 4.2):
    q = 0.09 if 59 < at < 87 else (0.20 if 40 < at < 58 else 0.14)
    f = scale[int(rng.integers(0, len(scale)))] * (0.5 if n % 3 == 0 else 1.0)
    d = 2.2
    k = t(d)
    snd = (np.sin(2 * np.pi * f * k) + 0.3 * np.sin(2 * np.pi * 2 * f * k) * np.exp(-k * 4)) * env(d, 0.01, 0.9)
    place(bed, snd, at, q * 0.3)
    n += 1
# night insects: quiet high pulses, cut off when the gas arrives
ins = np.zeros_like(tt)
for c0 in (4300.0, 4650.0):
    ph = np.sin(2 * np.pi * c0 * tt) * (np.sin(2 * np.pi * 7.0 * tt + c0) > 0.55)
    ins += 0.05 * ph * np.interp(tt, [0, 2, 11, 13, 13.4], [0, 1, 1, 0.5, 0]) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * tt))
bed += ins

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


def breath(a, b, g=0.2, fc=600):
    k = t(b - a)
    x = lp(rng.standard_normal(len(k)), fc) * np.minimum(k / 0.8, 1) * np.minimum((b - a - k) / 0.8, 1)
    place(sfx, x, a, g * 2.0)


def type_run(at, chars, cps, g=0.22):
    for i in range(chars):
        tick(at + i / cps, g, 2400 + 400 * (i % 3))


def count_run(a, b, g=0.2, f0=2800, step=0.08):
    for at in np.arange(a, b, step):
        tick(at, g, f0 + 8 * (at - a) * 100)


# Scene 1 (0 - 13.3)
type_run(0.3, 30, 30)
for at in np.arange(0.6, 4.8, 0.55):
    scratch(at, 0.4, 0.22)
count_run(5.6, 8.3, 0.2, 2600, 0.09)
tap(9.8, 0.4)
breath(11.4, 14.0, 0.18, 500)
# Scene 2 (13.3 - 39.45)
type_run(13.6, 28, 28)
for at in np.arange(13.9, 16.4, 0.5):
    scratch(at, 0.35, 0.2)
breath(15.2, 18.6, 0.22, 380)
thud(16.6, 90, 0.8)
scratch(19.6, 0.5, 0.25)
for i, at in enumerate(np.arange(22.5, 35.9, 0.7)):
    tick(at, 0.18 + 0.01 * i, 1800 + 60 * i)
for at in np.arange(35.9, 39.2, 0.13):
    tick(at, 0.3, 2200 + float(rng.integers(-200, 200)))
tap(26.1, 0.45)
thud(27.5, 82, 0.7)
for at, g in ((33.0, 0.45), (35.5, 0.45), (37.6, 0.45)):
    scratch(at, 0.5, g)
    thud(at + 0.55, 70, 0.4, 0.2)
# Scene 3 (39.45 - 58.5): wave of windows, siren, running
for at in np.sort(rng.uniform(43.6, 49.3, 70)):
    tick(at, 0.12, 900 + float(rng.integers(0, 500)))
thud(40.3, 62, 0.7, 0.5)
# thin siren: wails up for 1.6 s, then stops dead
k = t(2.0)
f = np.linspace(520, 760, len(k))
sir = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(k / 0.15, 1)
place(sfx, sir, 47.0, 0.18)
thud(49.05, 55, 0.5, 0.35)
# footsteps: soft patter from the first runner on
for at in np.arange(50.2, 58.3, 0.17):
    k2 = t(0.05)
    place(sfx, lp(rng.standard_normal(len(k2)), 900) * env(0.05, 0.001, 0.012), at + float(rng.uniform(0, 0.05)), 0.10 + 0.04 * min(1, (at - 50.2) / 3))
thud(55.9, 70, 0.7, 0.5)
# Scene 4 (58.5 - 69.67)
type_run(59.2, 14, 24)
count_run(61.5, 64.8, 0.2, 2200, 0.07)
for i in range(38):
    tick(61.6 + i * 3.0 / 38, 0.10, 1500)
count_run(66.0, 68.7, 0.22, 2400, 0.06)
for i in range(0, 192, 3):
    tick(66.1 + i * 2.7 / 192, 0.08, 1300)
# Scene 5 (69.67 - 87.13)
count_run(71.9, 74.5, 0.2, 2400, 0.08)
scratch(75.0, 0.8, 0.22)
for i in range(7):
    thud(77.8 + i * 0.34 + 0.1, 150 + 8 * i, 0.32, 0.14)
thud(80.1, 90, 0.9)
scratch(81.9, 1.1, 0.22)
for i in range(15):
    tick(83.4 + i * 0.16, 0.14, 1900)
scratch(84.4, 0.7, 0.22)
# Scene 6 (87.13 - 104.5): trucks leave, the number, the hold
rum = lp(rng.standard_normal(int(12 * SR)), 180) * np.interp(t(12), [0, 2, 8, 12], [0, 1, 1, 0])
place(sfx, rum, 90.4, 0.9)
count_run(90.2, 92.6, 0.2, 2400, 0.08)
count_run(94.6, 97.2, 0.2, 2600, 0.07)
thud(98.9, 65, 0.7, 0.6)
thud(100.4, 60, 0.6, 0.8)

peak = np.max(np.abs(sfx))
sfx = sfx / (peak or 1) * 0.16
write(HERE / "sfx-track.wav", sfx)
print("bed.wav + sfx-track.wav written", END, "s; bed target %.1f dBFS rms" % target)
