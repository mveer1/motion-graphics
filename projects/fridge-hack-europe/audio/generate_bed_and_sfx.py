#!/usr/bin/env python3
"""Synthesise this project's music bed and foley track. Original, deterministic (seeded), no samples, no licences.

  bed.wav        a refrigeration-compressor hum (55 Hz + harmonics, soft broadband) that CUTS OUT when the first tile
                 warms (6.1 s), as a compressor does when defrost starts; from scene 2 a dim minimalist pulse and low
                 pad that tighten through the heat (scene 4), thin out on the map (scene 5) and relax in scene 6;
                 the hum returns when the grid has cooled (88.6 s).
  sfx-track.wav  typewriter ticks for each kicker, thermostat-relay ticks that climb with temperature, stamp thuds,
                 pen scratches for draw-ons, frost pops, drips, flame crackle, tile taps for the map. No whooshes.
Cue times mirror src/index.html (visual events) against audio/timeline.json (measured narration).
Run: .venv/bin/python projects/fridge-hack-europe/audio/generate_bed_and_sfx.py   (needs numpy + scipy)
"""
import wave
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).parent
SR = 44100
END = 92.0
rng = np.random.default_rng(2611)


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
n_tt = len(tt)

# compressor hum: 0 - 6.1 s (cuts out at the first warming tile), returns 88.6 - 92 s
hum_env = np.interp(tt, [0, 0.4, 5.95, 6.1, 6.11, 88.5, 88.6, 90.0, 92.0], [0, 1, 1, 0, 0, 0, 0.0, 0.8, 0.8])
hum = np.zeros(n_tt)
for f, g in ((55.0, 0.8), (110.0, 0.5), (165.0, 0.22), (220.0, 0.1)):
    hum += g * np.sin(2 * np.pi * f * tt) * (0.9 + 0.1 * np.sin(2 * np.pi * 0.7 * tt + f))
hum += 0.25 * lp(rng.standard_normal(n_tt), 260)
hum *= hum_env

# low pad: A1 + E2 + C3 drone, fades in with scene 2
pad_env = np.interp(tt, [0, 12.5, 15.0, 44, 48, 57, 61, 74, 76, 86, 90, END],
                    [0, 0, 0.45, 0.45, 0.8, 0.8, 0.35, 0.35, 0.45, 0.45, 0.2, 0.0])
pad = np.zeros(n_tt)
for f, g in ((55.0, 0.7), (82.41, 0.4), (130.81, 0.22)):
    pad += g * (np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(2 * np.pi * 2 * f * tt)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.05 * tt + f))
# the pad creeps upward in pitch with the heat (scene 4), then settles
heat = np.interp(tt, [44, 50, 57, 61], [0, 1, 1, 0])
pad += 0.25 * heat * np.sin(2 * np.pi * (110 + 40 * heat) * tt)
pad *= pad_env

# minimalist pulse: soft low kick at 72 bpm from scene 2; doubles (half-beat) in scene 4; drops in scene 5
pulse = np.zeros(n_tt)
beat = 60.0 / 72
k = t(0.35)
kick = np.sin(2 * np.pi * 52 * (1 - 0.3 * k / 0.35) * k) * env(0.35, 0.004, 0.09)
at = 14.0
while at < END - 3:
    g = np.interp(at, [14, 20, 44, 48, 57, 61, 74, 86, 92], [0.0, 0.7, 0.7, 1.0, 1.0, 0.45, 0.45, 0.3, 0.0])
    place(pulse, kick, at, g)
    if 48 < at < 58:
        place(pulse, kick, at + beat / 2, g * 0.35)
    at += beat

bed = hum * 1.5 + pad * 1.0 + pulse * 0.9

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


def stamp(at, g=0.9):
    thud(at, 70, g, 0.32)
    tick(at, 0.4, 1400)


def scratch(at, dur=0.5, g=0.4):
    k = t(dur)
    x = rng.standard_normal(len(k))
    x = lp(x, 6000) - lp(x, 1500)
    place(sfx, x * np.minimum(k / 0.04, 1) * np.exp(-k / (dur * 0.5)), at, g)


def tap(at, g=0.5):
    k = t(0.08)
    place(sfx, np.sin(2 * np.pi * 1700 * k) * env(0.08, 0.001, 0.015), at, g * 0.4)


def plink(at, f=1800, g=0.3):
    k = t(0.35)
    place(sfx, np.sin(2 * np.pi * f * k) * env(0.35, 0.001, 0.07), at, g * 0.5)


def crackle(a, dur, g=0.3):
    k = t(dur)
    x = lp(rng.standard_normal(len(k)), 4500) * (rng.random(len(k)) > 0.9)
    place(sfx, x * np.minimum(k / 0.05, 1) * np.exp(-k / (dur * 0.5)), a, g * 1.6)


def breath(a, b, g=0.2, fc=600):
    k = t(b - a)
    x = lp(rng.standard_normal(len(k)), fc) * np.minimum(k / 0.8, 1) * np.minimum((b - a - k) / 0.8, 1)
    place(sfx, x, a, g * 2.0)


def type_run(at, chars, g=0.2):
    # kicker text types at 0.035 s per character (see kicker() in index.html)
    for i in range(chars):
        tick(at + 0.05 + i * 0.035, g, 2400 + 400 * (i % 3))


def count_run(a, b, g=0.2, f0=2400, step=0.08, climb=1.0):
    for at in np.arange(a, b, step):
        tick(at, g, f0 + 1400 * climb * (at - a) / max(b - a, 0.1))


# --- Scene 1 (0 - 13.9): hum, rings, the first tile ticks, the wave
type_run(0.4, 24)
scratch(3.2, 0.55, 0.22)
scratch(4.6, 0.55, 0.22)
count_run(6.1, 8.2, 0.16, 2000, 0.16, 0.8)   # origin tile, slow
count_run(6.9, 10.6, 0.14, 2200, 0.06, 1.4)  # wave crossing the grid
for at in np.sort(rng.uniform(7.0, 10.0, 40)):
    tick(at, 0.09, 1500 + float(rng.integers(0, 1400)))
tap(9.8, 0.45)
for i in range(4):
    thud(11.2 + 0.5 * i, 70, 0.4, 0.2)
# --- Scene 2 (13.9 - 26.4): defrost cutaway
thud(14.3, 62, 0.7, 0.4)
type_run(14.0, 22)
for i in range(18):
    tick(14.6 + i * 0.04, 0.07, 1300)
scratch(15.5, 1.1, 0.25)
for i in range(30):
    tick(16.1 + i * 0.045, 0.10, 2800 + 80 * (i % 5))
breath(17.5, 18.5, 0.16, 900)
for i in range(9):
    plink(18.85 + i * 0.12, 1500 + 70 * (i % 4), 0.28)
tap(19.9, 0.45)
for i in range(5):
    tick(20.2 + i * 0.12, 0.12, 2000)
count_run(21.9, 24.5, 0.16, 1500, 0.07, 1.2)
for i in range(12):
    tick(22.2 + i * 0.25, 0.06, 1100)
# --- Scene 3 (26.4 - 44.3): the controller
type_run(26.5, 25)
scratch(26.8, 1.0, 0.25)
tap(27.7, 0.4)
for at in np.sort(rng.uniform(29.8, 31.6, 60)):
    tick(at, 0.08, 1800 + float(rng.integers(0, 1400)))
count_run(30.9, 32.2, 0.18, 2200, 0.05, 1.0)
stamp(33.85, 0.95)
tap(37.0, 0.4)
scratch(37.7, 0.5, 0.22)
for i in range(8):
    tick(38.1 + i * 0.16, 0.20, 1500)
thud(40.9, 82, 0.6, 0.3)
plink(40.9, 900, 0.3)
# --- Scene 4 (44.3 - 61): alarms, heat, fire, the bin
type_run(44.5, 21)
scratch(45.6, 0.45, 0.3)
thud(46.0, 60, 0.5, 0.3)
count_run(48.06, 49.9, 0.18, 1800, 0.05, 1.8)
for at in np.sort(rng.uniform(48.3, 49.9, 40)):
    tick(at, 0.08, 1500 + float(rng.integers(0, 1400)))
scratch(50.15, 0.5, 0.24)
tick(50.65, 0.4, 3000)
for a, d in ((51.71, 1.0), (51.89, 1.0), (52.07, 1.0)):
    crackle(a, d, 0.35)
thud(51.8, 75, 0.4, 0.3)
for i in range(13):
    plink(53.45 + i * 0.12, 700 + 55 * i, 0.18)
for i in range(4):
    tap(53.3 + i * 0.25, 0.35)
for at in np.sort(rng.uniform(54.4, 56.3, 70)):
    tick(at, 0.09, 900 + float(rng.integers(0, 600)))
count_run(56.96, 58.4, 0.2, 1800, 0.05, 1.5)
scratch(57.3, 1.2, 0.2)
# --- Scene 5 (61 - 74.8): the map
type_run(61.2, 23)
for i in range(20):
    tick(61.55 + i * 0.05, 0.08, 1400 + 40 * i)
for at in (63.6, 64.25, 65.9, 66.45, 67.2, 67.45, 67.7):
    thud(at, 95, 0.55, 0.2)
    tick(at, 0.3, 2200)
tap(62.0, 0.3)
tap(68.9, 0.45)
for i in range(4):
    thud(70.6 + i * 0.4, 110, 0.25, 0.15)
# --- Scene 6 (74.8 - 92): who, what now, the cooling
type_run(75.0, 14)
plink(75.1, 800, 0.4)
thud(75.1, 90, 0.5, 0.3)
for i in range(3):
    plink(75.8 + i * 1.1, 1200, 0.18)
tap(76.4, 0.45)
tap(78.6, 0.45)
tap(80.5, 0.4)
for a in (82.2, 83.95, 85.05):
    thud(a, 120, 0.35, 0.12)
    tick(a, 0.35, 2600)
# cooling wave: descending ticks and a soft breath of air
for i, at in enumerate(np.arange(86.4, 89.6, 0.07)):
    tick(at, 0.11, 3000 - 16 * i * 3)
breath(86.4, 89.6, 0.14, 700)
thud(89.7, 55, 0.5, 0.5)

peak = np.max(np.abs(sfx))
sfx = sfx / (peak or 1) * 0.16
write(HERE / "sfx-track.wav", sfx)
print("bed.wav + sfx-track.wav written", END, "s; bed target %.1f dBFS rms" % target)
