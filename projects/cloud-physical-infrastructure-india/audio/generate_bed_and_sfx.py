#!/usr/bin/env python3
"""Synthesise this project's music bed and foley track. Original, deterministic (seeded), no samples, no licences.

  bed.wav        a low modular-synth drone (A1/E2/A2 with a slow filter breath) and a soft pulse; it tenses
                 under the incident (scenes 2-4), opens up for the rebuild (scene 5) and settles at the close
  sfx-track.wav  keyboard ticks for typed kickers, UI pops, stamp thuds, a power-down sweep, LED ticks, a low
                 ripple swell, a cloud thud. No whooshes on scene dissolves.
Cue times mirror src/index.html (visual events) against audio/timeline.json (measured narration).
Run: .venv/bin/python audio/generate_bed_and_sfx.py   (from the repo root; needs numpy + scipy)
"""
import wave
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).parent
SR = 44100
END = 70.0
rng = np.random.default_rng(2026)


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
for f, g in ((55.0, 0.7), (82.41, 0.5), (110.0, 0.4), (164.81, 0.18)):
    bed += g * (np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(2 * np.pi * 2 * f * tt)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * tt + f))
# a cold minor second under the incident
bed += 0.12 * np.sin(2 * np.pi * 58.27 * tt) * np.interp(tt, [0, 8, 10, 35, 40, 70], [0, 0, 1, 1, 0, 0])
# soft pulse, one beat per 1.2 s, strongest while traffic is rerouted
pulse = np.zeros_like(tt)
for at in np.arange(1.0, END - 2, 1.2):
    k = t(0.5)
    snd = np.sin(2 * np.pi * 82.41 * k) * env(0.5, 0.01, 0.12)
    place(pulse, snd, at, 1.0)
bed += 0.25 * pulse * np.interp(tt, [0, 10, 24, 36, 46, 58, 70], [0.2, 0.5, 0.7, 1.0, 0.6, 0.3, 0.0])
# slow high shimmer that lifts in the rebuild
sh = lp(rng.standard_normal(len(tt)), 900) * np.interp(tt, [44, 50, 58, 66, 70], [0, 0.25, 0.3, 0.1, 0])
bed += sh
level = np.interp(tt, [0, 1.5, 24, 36, 46, 58, 66, END], [0.0, 0.6, 0.7, 0.85, 0.65, 0.5, 0.45, 0.0])
bed *= level
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


def tick(at, g=0.3, f=3000):
    k = t(0.03)
    place(sfx, (rng.standard_normal(len(k)) * 0.5 + np.sin(2 * np.pi * f * k)) * env(0.03, 0.0005, 0.006), at, g * 0.6)


def pop(at, g=0.5, f=620):
    k = t(0.14)
    place(sfx, np.sin(2 * np.pi * (f + 900 * np.exp(-k * 30)) * k) * env(0.14, 0.002, 0.04), at, g * 0.5)


def thud(at, f=88, g=0.9, dur=0.3):
    k = t(dur)
    body = np.sin(2 * np.pi * f * (1 - 0.35 * k / dur) * k) * env(dur, 0.002, 0.07)
    nz = lp(rng.standard_normal(len(k)), 1800) * env(dur, 0.001, 0.02)
    place(sfx, body + 0.5 * nz, at, g * 0.8)


def type_run(at, chars, cps, g=0.22):
    for i in range(chars):
        tick(at + i / cps, g, 2300 + 400 * (i % 3))


# kickers typed (cps from the composition)
type_run(0.2, 17, 30); type_run(4.2, 14, 28); type_run(8.45, 20, 26)
type_run(24.35, 20, 28); type_run(35.55, 16, 28); type_run(46.75, 17, 26); type_run(58.5, 12, 28)
# scene 1: tap, answer, chips, pin drop
pop(1.1, 0.5, 700); tick(1.5, 0.3); tick(1.6, 0.3); tick(1.7, 0.3)
for at in (5.5, 6.2, 6.85): pop(at, 0.45, 560)
thud(7.0, 70, 0.6, 0.3)
# scene 2: fire, stamps, lens, power-down
thud(10.3, 60, 0.5, 0.5)
for at in np.sort(rng.uniform(10.4, 13.0, 40)): tick(at, 0.08, 900 + float(rng.integers(0, 600)))
thud(13.6, 90, 0.6, 0.25)
pop(15.6, 0.4, 480)
k = t(0.9)
sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(900, 90, len(k))) / SR) * np.minimum(k / 0.02, 1) * np.exp(-k / 0.5)
place(sfx, sweep, 18.3, 0.5)
for i in range(12): tick(18.6 + i * 0.09, 0.2, 1800 - 60 * i)
thud(18.9, 80, 0.9, 0.3)
thud(21.6, 100, 0.5, 0.2)
# scene 3: darkness, ripples, packet loss
thud(27.4, 48, 0.8, 0.9)
for at, f in ((28.4, 520), (29.3, 480), (30.4, 440)): pop(at, 0.4, f)
for at in (32.6, 33.1, 33.7, 34.5): tick(at, 0.3, 1200)
thud(32.9, 100, 0.4, 0.2)
# scene 4: reroute, queue, no workaround
for i in range(12): tick(40.7 + i * 0.17, 0.16, 1700 + 20 * i)
for i in range(12): tick(41.0 + i * 0.17, 0.14, 1500 + 20 * i)
thud(44.3, 90, 0.9, 0.3)
# scene 5: timeline ticks, roads return, hard hat, normal
for at in (46.95, 49.4, 50.9, 55.2): pop(at, 0.4, 700)
for at in (49.8, 51.3, 55.6): pop(at, 0.3, 900)
pop(52.4, 0.4, 420)
# scene 6: cloud lands, icons
thud(60.7, 70, 0.9, 0.5); thud(61.25, 80, 0.4, 0.2); thud(61.6, 90, 0.25, 0.15)
for at in (62.2, 62.9, 63.6): pop(at, 0.4, 600)
k = t(1.6)
chime = (np.sin(2 * np.pi * 523.25 * k) + 0.5 * np.sin(2 * np.pi * 783.99 * k)) * env(1.6, 0.01, 0.5)
place(sfx, chime, 64.2, 0.35)

peak = np.max(np.abs(sfx))
sfx = sfx / (peak or 1) * 0.16
write(HERE / "sfx-track.wav", sfx)
print("bed.wav + sfx-track.wav written", END, "s; bed target %.1f dBFS rms" % target)
