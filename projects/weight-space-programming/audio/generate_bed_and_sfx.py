#!/usr/bin/env python3
"""Synthesise this project's music bed and foley track. Original, deterministic (seeded), no samples, no licences.

  bed.wav        a dim modular-synth bed that follows the chapters: an A drone under the premise; a soft 80 bpm
                 pulse from the gradient-descent scene; minor pads for READ and FIX; a muted pentatonic arpeggio for
                 WRITE; a rising, dissonant pad under the Qwen loop that RESOLVES to C major on "forty-eight point one"
                 (187.0 s); thinned out for LIMITS; A minor to A major for the close, ringing out after the last word.
  sfx-track.wav  typewriter ticks for kickers and equations, counter ticks for number rolls, soft stamp thuds,
                 pen scratches for draw-ons, cell pops, stone clacks, a small car motor, plinks for matches and
                 results. No whooshes on scene changes.
Cue times mirror src/index.html (scene start from audio/timeline.json + the offsets used in each scene builder).
Run: .venv/bin/python projects/weight-space-programming/audio/generate_bed_and_sfx.py   (needs numpy + scipy)
"""
import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).parent
SR = 44100
END = 239.5
rng = np.random.default_rng(20261102)
SC = {s["id"]: s["start_time_sec"] for s in json.loads((HERE / "timeline.json").read_text())["scenes"]}


def at(sid, t):
    return SC[sid] + t


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


def place(buf, snd, start, gain=1.0):
    i = int(start * SR)
    j = min(len(buf), i + len(snd))
    if 0 <= i < len(buf):
        buf[i:j] += gain * snd[: j - i]


def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    return lfilter([1 - a], [1, -a], x)


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)


def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


# ---------------------------------------------------------------- music bed
tt = t(END)
n_tt = len(tt)
bed = np.zeros(n_tt)

# chapter boundaries (film seconds)
READ, FIX, WRITE, IMPROVE, LIMITS, CLOSE = at("s4", -0.25), at("s6", -0.25), at("s7", -0.25), at("s9", -0.25), at("s11", -0.25), at("s12", -0.25)
RELEASE = at("s10", 14.95)  # "forty-eight point one"

# drone: A1 + A2 with slow beating, whole film
drone_env = np.interp(tt, [0, 1.5, CLOSE, END - 1.2, END], [0.55, 0.8, 0.8, 0.8, 0.0])
drone = (np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 110.4 * tt) + 0.2 * np.sin(2 * np.pi * 164.8 * tt))
drone *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.07 * tt)
bed += 0.9 * drone * drone_env


def pad(chord, a, b, g=1.0, fade=1.5):
    """Soft additive pad over [a, b] with equal fades; chord is a list of MIDI notes."""
    k = (tt >= a - fade) & (tt <= b + fade)
    x = tt[k]
    e = np.clip(np.minimum((x - (a - fade)) / fade, ((b + fade) - x) / fade), 0, 1)
    s = np.zeros(len(x))
    for i, n in enumerate(chord):
        f = hz(n)
        s += (np.sin(2 * np.pi * f * x + i) + 0.25 * np.sin(2 * np.pi * 2 * f * x)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * x + i))
    bed[k] += g * 0.32 * lp(s, 1400) * e


pad([57, 64], 1.0, at("s2", 0))                      # premise: open fifth
pad([57, 60, 64], at("s2", 0), READ, 0.8)            # descent: A minor
pad([57, 60, 64, 67], READ, FIX, 0.9)                # READ: Am7
pad([50, 57, 62, 65], FIX, WRITE, 1.0)               # FIX: Dm
pad([53, 57, 60, 64], WRITE, IMPROVE, 0.9)           # WRITE: Fmaj7
pad([52, 58, 63], IMPROVE, RELEASE, 1.0, 1.0)        # IMPROVE: tense (E, Bb, Eb)
pad([48, 55, 64, 67], RELEASE, LIMITS, 1.15, 0.6)    # release: C major
pad([57, 64], LIMITS, CLOSE, 0.6)                    # LIMITS: thin fifth
pad([57, 60, 64], CLOSE, at("s12", 15.4), 0.8)       # close: A minor
pad([57, 61, 64, 69], at("s12", 15.4), END - 0.6, 1.0, 0.6)  # resolve: A major, held to the end

# the loop scene: a slow rising sine sweep under the pad, cut on the release
k = (tt >= IMPROVE) & (tt < RELEASE)
x = tt[k] - IMPROVE
sweep_f = 220 + 140 * (x / (RELEASE - IMPROVE))
ph = 2 * np.pi * np.cumsum(sweep_f) / SR
bed[k] += 0.12 * np.sin(ph) * np.minimum(x / 3, 1) * np.minimum((RELEASE - IMPROVE - x) / 0.3, 1)

# soft pulse at 80 bpm from the descent scene to the close, thinner in LIMITS
beat = 60.0 / 80
kk = t(0.3)
kick = np.sin(2 * np.pi * 50 * (1 - 0.3 * kk / 0.3) * kk) * env(0.3, 0.004, 0.08)
p = at("s2", 6.84)
while p < END - 3:
    g = float(np.interp(p, [at("s2", 6.84), READ, IMPROVE, RELEASE, LIMITS, CLOSE, END - 4],
                        [0.35, 0.55, 0.75, 0.6, 0.25, 0.4, 0.0]))
    place(bed, kick, p, g)
    p += beat

# WRITE: muted pentatonic arpeggio (A C D E G), sixteenths at 80 bpm
scale = [57, 60, 62, 64, 67, 69, 72]
p, i = WRITE + 0.3, 0
pl = t(0.25)
while p < IMPROVE - 0.5:
    n = scale[(i * 3 + (i // 4)) % len(scale)]
    tone = np.sin(2 * np.pi * hz(n + 12) * pl) * env(0.25, 0.002, 0.06)
    place(bed, tone, p, 0.22 * float(np.interp(p, [WRITE, WRITE + 2, IMPROVE - 2, IMPROVE], [0, 1, 1, 0])))
    p += beat / 4
    i += 1

# level the bed against the measured narration so it sits ~16 dB under the voice after the mux (x0.6)
voice_path = HERE / "narration-full.wav"
with wave.open(str(voice_path), "rb") as w:
    v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
target = rms_db(v) - 11.6
bed = bed / (np.sqrt(np.mean(np.square(bed))) + 1e-9) * 10 ** (target / 20)
write(HERE / "bed.wav", bed)

# ---------------------------------------------------------------- foley
sfx = np.zeros(int(END * SR))


def tick(a, g=0.3, f=3200):
    k = t(0.03)
    place(sfx, (rng.standard_normal(len(k)) * 0.5 + np.sin(2 * np.pi * f * k)) * env(0.03, 0.0005, 0.006), a, g * 0.6)


def thud(a, f=88, g=0.9, dur=0.28):
    k = t(dur)
    body = np.sin(2 * np.pi * f * (1 - 0.35 * k / dur) * k) * env(dur, 0.002, 0.07)
    nz = lp(rng.standard_normal(len(k)), 1800) * env(dur, 0.001, 0.02)
    place(sfx, body + 0.5 * nz, a, g * 0.8)


def stamp(a, g=0.9):
    thud(a, 70, g, 0.32)
    tick(a, 0.4, 1400)


def scratch(a, dur=0.5, g=0.4):
    k = t(dur)
    x = rng.standard_normal(len(k))
    x = lp(x, 6000) - lp(x, 1500)
    place(sfx, x * np.minimum(k / 0.04, 1) * np.exp(-k / (dur * 0.5)), a, g)


def tap(a, g=0.5, f=1700):
    k = t(0.08)
    place(sfx, np.sin(2 * np.pi * f * k) * env(0.08, 0.001, 0.015), a, g * 0.4)


def plink(a, f=1800, g=0.3):
    k = t(0.35)
    place(sfx, np.sin(2 * np.pi * f * k) * env(0.35, 0.001, 0.07), a, g * 0.5)


def chime(a, notes, g=0.35, step=0.07):
    for i, n in enumerate(notes):
        plink(a + i * step, hz(n), g)


def breath(a, b, g=0.2, fc=600):
    k = t(b - a)
    x = lp(rng.standard_normal(len(k)), fc) * np.minimum(k / 0.5, 1) * np.minimum((b - a - k) / 0.5, 1)
    place(sfx, x, a, g * 2.0)


def clack(a, g=0.5):
    k = t(0.06)
    place(sfx, (np.sin(2 * np.pi * 900 * k) + 0.6 * rng.standard_normal(len(k))) * env(0.06, 0.0005, 0.01), a, g * 0.45)


def motor(a, b, f0=70, f1=110, g=0.25):
    k = t(b - a)
    f = np.linspace(f0, f1, len(k))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.3 * lp(rng.standard_normal(len(k)), 400))
    x *= np.minimum(k / 0.1, 1) * np.minimum((b - a - k) / 0.15, 1)
    place(sfx, x, a, g)


def type_run(a, chars, cps=34, g=0.2):
    for i in range(chars):
        tick(a + i / cps, g, 2400 + 400 * (i % 3))


def count_run(a, b, g=0.18, f0=2400, step=0.07, climb=1.0):
    for x in np.arange(a, b, step):
        tick(x, g, f0 + 1400 * climb * (x - a) / max(b - a, 0.1))


# --- s1: the wall, the heatmap, the block, the stamp
type_run(0.12, 14, 28)
count_run(0.39, 1.39, 0.16, 2000, 0.06)
thud(1.4, 90, 0.4, 0.22)
plink(2.42, 1320, 0.3)
for r in range(26):
    tick(3.85 + r * 0.055, 0.08, 1500 + 30 * r)
thud(6.08, 60, 0.45, 0.4)
for i in range(4):
    tap(6.4 + i * 0.16, 0.4, 1200 + 150 * i)
breath(8.45, 9.5, 0.12, 2400)
for i in range(19):
    tick(9.3 + i * 0.03, 0.07, 2600)
stamp(at("s1", 10.41), 0.9)
tap(11.0, 0.35, 2000)
tap(11.55, 0.3, 2000)
# --- s2: descent
type_run(at("s2", 0.1), 14, 28)
scratch(at("s2", 0.7), 1.2, 0.2)
for i in range(14):
    tick(at("s2", 1.22) + i * 0.03, 0.06, 1800)
tick(at("s2", 3.84), 0.35, 1400)
thud(at("s2", 5.92), 80, 0.35, 0.25)
type_run(at("s2", 6.0), 14, 22, 0.18)
for j in range(21):
    tap(at("s2", 6.84) + j * 0.19, 0.22, 900 - 18 * j)
tick(at("s2", 8.89), 0.25, 2200)
thud(at("s2", 10.28), 70, 0.45, 0.3)
# --- s3: the claim
type_run(at("s3", 0.41), 16, 28)
for i in range(4):
    tick(at("s3", 1.9 + i * 0.16), 0.25, 2000 + 200 * i)
thud(at("s3", 3.91), 90, 0.45, 0.22)
scratch(at("s3", 5.85), 0.35, 0.35)
breath(at("s3", 6.41), at("s3", 7.0), 0.1, 1200)
scratch(at("s3", 7.6), 0.5, 0.2)
tap(at("s3", 7.89), 0.45, 900)
plink(at("s3", 9.9), 1500, 0.3)
breath(at("s3", 10.53), at("s3", 11.2), 0.08, 1200)
type_run(at("s3", 11.4), 41, 34, 0.12)
scratch(at("s3", 13.5), 0.35, 0.3)
tick(at("s3", 13.7), 0.4, 1300)
scratch(at("s3", 15.3), 0.35, 0.3)
tick(at("s3", 15.5), 0.4, 1300)
type_run(at("s3", 16.0), 19, 26, 0.18)
thud(at("s3", 16.55), 62, 0.6, 0.4)
for i in range(3):
    tap(at("s3", 17.1 + i * 0.18), 0.5, 1100 + 220 * i)
# --- s4: which game
tick(at("s4", -0.25), 0.3, 3000)
type_run(at("s4", 0.2), 14, 28)
for i in range(4):
    thud(at("s4", 1.9 + i * 0.18), 110, 0.22, 0.15)
breath(at("s4", 6.2), at("s4", 8.9), 0.08, 2600)
for i in range(4):
    stamp(at("s4", 9.38 + i * 0.22), 0.4)
chime(at("s4", 10.21), [72, 76, 79], 0.3)
thud(at("s4", 11.0), 60, 0.35, 0.35)
for i in range(19):
    tick(at("s4", 12.9) + i * 0.025, 0.06, 2600)
for c in range(10):
    tick(at("s4", 14.4) + c * 0.11, 0.18, 1600 + 120 * c)
scratch(at("s4", 15.24), 0.6, 0.2)
tap(at("s4", 16.8), 0.4, 2100)
# --- s5: copying heads
type_run(at("s5", 0.2), 14, 28)
for i in range(24):
    tick(at("s5", 2.4) + i * 0.04, 0.07, 2000 + 40 * (i % 6))
scratch(at("s5", 4.0), 0.35, 0.3)
scratch(at("s5", 4.6), 0.35, 0.3)
breath(at("s5", 5.44), at("s5", 6.1), 0.08, 1000)
for i in range(26):
    tick(at("s5", 6.41) + i * 0.02, 0.06, 2800)
for i in range(26):
    tick(at("s5", 8.0) + i * 0.018, 0.05, 1600)
tick(at("s5", 9.0), 0.35, 1300)
for i in range(36):
    tick(at("s5", 10.33) + i * 0.012, 0.04, 2400)
for r in range(6):
    tap(at("s5", 11.1) + r * 0.12, 0.25, 1400 + 100 * r)
for i, f in enumerate((1568, 1760, 2093)):
    plink(at("s5", 12.82 + i * 0.3), f, 0.35)
scratch(at("s5", 15.26), 0.6, 0.22)
tap(at("s5", 15.95), 0.5, 1900)
thud(at("s5", 17.0), 100, 0.25, 0.15)
thud(at("s5", 17.4), 100, 0.25, 0.15)
chime(at("s5", 18.04), [76, 79, 84], 0.3)
stamp(at("s5", 21.0), 0.75)
# --- s6: the car
tick(at("s6", -0.25), 0.3, 3000)
scratch(at("s6", 0.5), 0.6, 0.2)
motor(at("s6", 2.0), at("s6", 3.5), 60, 95, 0.18)
thud(at("s6", 3.5), 55, 0.35, 0.3)
motor(at("s6", 4.2), at("s6", 5.35), 60, 90, 0.16)
thud(at("s6", 5.35), 55, 0.3, 0.3)
tick(at("s6", 3.75), 0.3, 1200)
scratch(at("s6", 5.16), 1.2, 0.15)
stamp(at("s6", 6.94), 0.6)
scratch(at("s6", 8.42), 3.2, 0.12)
for r in range(8):
    plink(at("s6", 8.42 + r * 3.2 / 7), hz(64 + 2 * r), 0.22)
motor(at("s6", 12.05), at("s6", 13.1), 80, 60, 0.18)
motor(at("s6", 13.29), at("s6", 14.36), 60, 150, 0.24)
breath(at("s6", 14.36), at("s6", 15.0), 0.1, 1600)
thud(at("s6", 15.02), 70, 0.6, 0.3)
chime(at("s6", 15.1), [67, 71, 74], 0.3)
tick(at("s6", 15.39), 0.3, 2200)
count_run(at("s6", 18.3), at("s6", 19.5), 0.14, 2000, 0.06)
chime(at("s6", 20.6), [72, 76, 79, 84], 0.3)
# --- s7: write from zero
tick(at("s7", -0.25), 0.3, 3000)
type_run(at("s7", 0.2), 14, 28)
for i in range(56):
    tick(at("s7", 1.0) + (i // 8) * 0.06 + (i % 8) * 0.015, 0.04, 1800)
for i in range(8):
    tick(at("s7", 3.45) + i * 0.03, 0.12, 1000)
thud(at("s7", 4.0), 100, 0.3, 0.2)
for i in range(4):
    tick(at("s7", 4.38 + i * 0.45), 0.15, 2600)
for i in range(56):
    tick(at("s7", 7.93) + i * 0.026, 0.12, 2400 + 300 * (i % 3))
thud(at("s7", 10.42), 90, 0.35, 0.22)
scratch(at("s7", 12.16), 1.1, 0.15)
tap(at("s7", 13.3), 0.45, 1600)
for i in range(6):
    tick(at("s7", 14.53) + i * 0.15, 0.25, 1500)
for i in range(5):
    tap(at("s7", 15.3) + i * 0.2, 0.18, 2200)
tap(at("s7", 16.3), 0.4, 2400)
for gi in range(3):
    for kb in range(3):
        plink(at("s7", 18.22 + gi * 0.25 + kb * 0.08), hz(60 + 4 * kb + 2 * gi), 0.16)
for gi in range(3):
    plink(at("s7", 20.59 + gi * 0.25), hz(79 + 2 * gi), 0.3)
# --- s8: Go
type_run(at("s8", 0.15), 14, 28)
count_run(at("s8", 0.41), at("s8", 1.5), 0.16, 1800, 0.06)
breath(at("s8", 0.45), at("s8", 1.6), 0.08, 800)
thud(at("s8", 4.1), 100, 0.3, 0.2)
for i in range(5):
    type_run(at("s8", 4.7 + i * 0.32), 10, 48, 0.08)
scratch(at("s8", 6.1), 0.9, 0.15)
for i in range(18):
    clack(at("s8", 8.0) + i * 0.04, 0.55)
for i in range(6):
    plink(at("s8", 8.95) + i * 0.06, 2093, 0.12)
scratch(at("s8", 9.84), 0.5, 0.25)
for i in range(16):
    tick(at("s8", 11.25) + i * 0.03, 0.05, 2000)
tap(at("s8", 12.2), 0.5, 1300)
for i in range(50):
    tick(at("s8", 13.4) + i * 0.026, 0.09, 2200)
stamp(at("s8", 15.26), 0.7)
count_run(at("s8", 17.6), at("s8", 19.0), 0.12, 1800, 0.07)
# --- s9: the loop
tick(at("s9", -0.25), 0.3, 3000)
type_run(at("s9", 0.15), 14, 28)
for i in range(24):
    tick(at("s9", 0.6) + i * 0.045, 0.05, 1500)
thud(at("s9", 2.14), 85, 0.35, 0.22)
for x in np.arange(at("s9", 7.0), at("s9", 12.0), 0.11):
    tick(x, 0.06, 2600)
for i in range(85):
    tick(at("s9", 9.8) + i * 0.016, 0.05, 1200)
stamp(at("s9", 12.12), 0.85)
scratch(at("s9", 12.45), 0.8, 0.15)
plink(at("s9", 14.3), 1760, 0.35)
thud(at("s9", 16.41), 60, 0.4, 0.35)
thud(at("s9", 19.27), 60, 0.4, 0.35)
# --- s10: the edit
type_run(at("s10", 0.1), 14, 28)
for i in range(64):
    tick(at("s10", 0.41) + i * 0.012, 0.05, 2400)
thud(at("s10", 1.46), 90, 0.3, 0.2)
type_run(at("s10", 2.2), 17, 26, 0.15)
plink(at("s10", 2.3), 1320, 0.25)
plink(at("s10", 2.7), 1100, 0.25)
scratch(at("s10", 2.87), 0.4, 0.15)
plink(at("s10", 4.5), 880, 0.3)
count_run(at("s10", 4.5), at("s10", 5.9), 0.14, 1800, 0.06)
tap(at("s10", 7.0), 0.45, 2200)
for i in range(4):
    plink(at("s10", 7.4 + i), 2637, 0.08)
count_run(at("s10", 13.77), at("s10", 14.9), 0.12, 1600, 0.07, 1.5)
chime(at("s10", 14.95), [72, 76, 79, 84], 0.4, 0.06)
count_run(at("s10", 15.2), at("s10", 16.2), 0.1, 1800, 0.07)
count_run(at("s10", 17.0), at("s10", 17.9), 0.1, 1800, 0.07)
stamp(at("s10", 17.97), 0.6)
count_run(at("s10", 18.25), at("s10", 19.2), 0.1, 2600, 0.07, -0.8)
tick(at("s10", 21.58), 0.25, 1500)
tap(at("s10", 22.13), 0.4, 900)
# --- s11: limits
tick(at("s11", -0.25), 0.3, 3000)
type_run(at("s11", 0.15), 14, 28)
breath(at("s11", 3.08), at("s11", 4.5), 0.08, 2600)
stamp(at("s11", 3.71), 0.6)
tick(at("s11", 4.58), 0.3, 1100)
for x in (8.35, 8.92):
    count_run(at("s11", x), at("s11", x + 0.6), 0.08, 1600, 0.05)
chime(at("s11", 9.88), [74, 77, 81], 0.25)
scratch(at("s11", 11.3), 1.0, 0.12)
scratch(at("s11", 13.0), 1.2, 0.15)
scratch(at("s11", 16.35), 0.6, 0.15)
# --- s12: close
type_run(at("s12", 0.1), 14, 28)
for x in (0.68, 2.17, 3.62, 5.1):
    tap(at("s12", x), 0.35, 1500)
thud(at("s12", 6.21), 80, 0.3, 0.22)
scratch(at("s12", 8.93), 0.5, 0.15)
scratch(at("s12", 10.36), 0.35, 0.3)
type_run(at("s12", 10.54), 19, 26, 0.15)
for r in range(9):
    tick(at("s12", 11.08) + r * 0.08, 0.06, 1800)
for i, x in enumerate((13.24, 13.8, 14.4)):
    plink(at("s12", x), hz(76 + 3 * i), 0.3)
thud(at("s12", 15.43), 70, 0.45, 0.35)
thud(at("s12", 17.21), 70, 0.45, 0.35)
scratch(at("s12", 18.1), 0.9, 0.18)
for i in range(4):
    tick(at("s12", 19.0) + i * 0.66, 0.12, 2600)
peak = np.max(np.abs(sfx))
sfx = sfx / (peak or 1) * 0.16

# the closing hit lands on the last visual event (the caret, 236.3 s) and rings out over the tail;
# added after normalisation so it does not pull every other cue down, peaking near 0.42
body = np.zeros_like(sfx)
_main = sfx
sfx = body
thud(at("s12", 19.0), 55, 1.0, 0.7)
chime(at("s12", 19.0), [57, 64, 69, 73, 76, 81], 0.9, 0.05)
k = t(2.4)
ring = sum(np.sin(2 * np.pi * hz(n) * k) for n in (45, 57, 64, 69, 73)) * np.minimum(k / 0.01, 1) * np.exp(-k / 0.9)
place(sfx, ring, at("s12", 19.0), 0.35)

close_peak = np.max(np.abs(sfx)) or 1
sfx = _main + sfx / close_peak * 0.42
write(HERE / "sfx-track.wav", sfx)
print("bed.wav + sfx-track.wav written", END, "s; bed target %.1f dBFS rms" % target)
