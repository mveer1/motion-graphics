#!/usr/bin/env python3
"""Sinew sound identity: the brand bed, the sonic logo and the micro-SFX, synthesised (numpy, no samples).

Original and deterministic (seeded): project-owned audio, no licence or attribution needed. A project's
audio/generate_bed_and_sfx.py imports this module, lists its events from the composition's cue times and calls
build(). Levels follow the workspace mix rules (AGENTS.md section 3): the bed sits about 17 dB under the voice after
the studio mux (which applies x0.6 to the bed and x0.85 to SFX), SFX peaks about 12 dB under the voice, no whooshes on
cross-dissolves.

Sound identity (brand guidelines, "Sound"):
  bed      warm major-seventh pad (D - F# - A - C#) over a soft 96 bpm pulse; it lifts to the IV chord in
           mechanism scenes and resolves home on the logo. No melody, so it never competes with narration.
  spark    the sonic logo: two marimba-like notes a fifth apart (A5 then E6) with a shimmer tail.
  rep      a soft rubber thud for each lifted rep (concentric start).
  tick     a dry click for chart points and labels.
  pop      a rounded blip for badges and cards.
  stamp    a low thump plus a short paper burst for the myth stamp.
  swell    a filtered-noise rise into a scale dive (zoom), 0.9 s.
  pulse    a low heartbeat-like double thump for signal moments.

Usage (from a project script):
  import importlib.util, sys
  spec = importlib.util.spec_from_file_location('sinew_sound', ROOT/'.claude/skills/fitness/scripts/sinew_sound.py')
  ss = importlib.util.module_from_spec(spec); spec.loader.exec_module(ss)
  ss.build(project_dir, duration=97.5, events=[(0.2, 'pop'), ...], sections=[(0, 'home'), (21, 'lift'), (92.8, 'home')])
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

SR = 44100


def _t(sec: float) -> np.ndarray:
    return np.arange(int(sec * SR)) / SR


def _env(sec: float, attack: float = 0.004, decay: float = 0.2) -> np.ndarray:
    k = _t(sec)
    return np.minimum(k / max(attack, 1e-4), 1.0) * np.exp(-k / decay)


def _lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    # one-pole low-pass; scipy when available, a plain loop otherwise
    a = np.exp(-2 * np.pi * cutoff / SR)
    try:
        from scipy.signal import lfilter
        return lfilter([1 - a], [1, -a], x)
    except ImportError:
        pass
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def note(freq: float, sec: float, decay: float = 0.6, partials: Sequence[Tuple[float, float]] = ((1, 1), (4, 0.18), (10, 0.05))) -> np.ndarray:
    """A marimba-like struck note: fundamental plus inharmonic bar partials, fast decay on the highs."""
    k = _t(sec)
    out = np.zeros_like(k)
    for mult, amp in partials:
        out += amp * np.sin(2 * np.pi * freq * mult * k) * np.exp(-k / (decay / (1 + mult * 0.4)))
    return out * np.minimum(k / 0.002, 1)


# --------------------------------------------------------------------------- SFX palette
def sfx(kind: str, rng: np.random.Generator) -> np.ndarray:
    if kind == 'spark':
        a = note(880.0, 1.6, 0.9)
        b = note(1318.5, 1.6, 1.1)
        out = np.zeros(int(2.2 * SR))
        out[:len(a)] += a
        off = int(0.14 * SR)
        out[off:off + len(b)] += b * 0.9
        shimmer = rng.standard_normal(len(out)) * np.exp(-_t(len(out) / SR) / 0.5) * 0.02
        return out * 0.5 + _lowpass(shimmer, 6000)
    if kind == 'rep':
        k = _t(0.28)
        f = 60 + 50 * np.exp(-k / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(0.28, 0.003, 0.07) * 0.9
    if kind == 'tick':
        n = rng.standard_normal(int(0.03 * SR))
        return _lowpass(n, 4500) * _env(0.03, 0.0005, 0.006) * 1.4
    if kind == 'pop':
        k = _t(0.16)
        f = 520 + 380 * np.exp(-k / 0.02)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(0.16, 0.002, 0.045) * 0.7
    if kind == 'stamp':
        k = _t(0.4)
        thump = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-k / 0.02)) / SR) * _env(0.4, 0.002, 0.09)
        burst = _lowpass(rng.standard_normal(len(k)), 2500) * _env(0.4, 0.001, 0.03) * 0.6
        return (thump + burst) * 0.9
    if kind == 'swell':
        k = _t(0.9)
        n = rng.standard_normal(len(k))
        rise = (k / 0.9) ** 2
        return _lowpass(n, 1800) * rise * np.exp(-np.maximum(k - 0.82, 0) / 0.03) * 0.35
    if kind == 'pulse':
        one = np.sin(2 * np.pi * 48 * _t(0.18)) * _env(0.18, 0.003, 0.05)
        out = np.zeros(int(0.5 * SR))
        out[:len(one)] += one
        off = int(0.2 * SR)
        out[off:off + len(one)] += one * 0.7
        return out
    raise ValueError(f'unknown sfx kind {kind!r}')


# --------------------------------------------------------------------------- bed
CHORDS = {
    'home': [146.83, 185.00, 220.00, 277.18],   # Dmaj7
    'lift': [196.00, 246.94, 293.66, 369.99],   # Gmaj7 (IV)
    'turn': [164.81, 196.00, 246.94, 293.66],   # Em7 (ii), for complications
}


def bed(duration: float, sections: Sequence[Tuple[float, str]], bpm: float = 96.0, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    out = np.zeros(n)
    k = np.arange(n) / SR
    # pad: each section's chord, cross-faded over 1.5 s; slow detuned sines with gentle tremolo
    secs = list(sections) + [(duration, sections[-1][1])]
    for (start, name), (stop, _) in zip(secs[:-1], secs[1:]):
        a, b = int(max(0, start - 0.75) * SR), int(min(duration, stop + 0.75) * SR)
        seg = k[a:b]
        w = np.ones(b - a)
        fade = int(1.5 * SR)
        w[:fade] = np.linspace(0, 1, min(fade, len(w)))[:len(w[:fade])]
        w[-fade:] = np.minimum(w[-fade:], np.linspace(1, 0, len(w[-fade:])))
        for i, f in enumerate(CHORDS[name]):
            det = 1 + (i - 1.5) * 0.0012
            out[a:b] += w * (np.sin(2 * np.pi * f * det * seg + i) + 0.35 * np.sin(2 * np.pi * f * 2 * seg + i * 0.7)) * (0.9 if i else 1.1)
    out *= 0.6 + 0.4 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * k))
    out = _lowpass(out, 1400)
    # soft pulse on the beat (felt more than heard)
    beat = 60.0 / bpm
    kick = np.sin(2 * np.pi * np.cumsum(50 + 40 * np.exp(-_t(0.25) / 0.02)) / SR) * _env(0.25, 0.004, 0.08)
    t0 = sections[0][0] + 0.25
    while t0 < duration - 0.5:
        i = int(t0 * SR)
        seg = kick[: max(0, min(len(kick), n - i))]
        out[i:i + len(seg)] += seg * 1.6
        t0 += beat
    # air: very quiet filtered noise
    out += _lowpass(rng.standard_normal(n), 900) * 0.15
    # fade in and out
    fi, fo = int(1.2 * SR), int(2.5 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    return out


# --------------------------------------------------------------------------- io and levels
def read_wav(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), 'rb') as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def write_wav(path: Path, x: np.ndarray) -> None:
    x = np.clip(x, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def rms_db(x: np.ndarray, gate: float = 0.01) -> float:
    v = x[np.abs(x) > gate]
    if not len(v):
        v = x
    return 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-12)


def build(project_dir: Path, duration: float, events: Iterable[Tuple[float, str]], sections: Sequence[Tuple[float, str]],
          bed_under_voice_db: float = 12.6, sfx_peak: float = 0.16, seed: int = 11, gains: Optional[dict] = None) -> dict:
    """Write audio/bed.wav and audio/sfx-track.wav for a project. Returns the levels it set."""
    project_dir = Path(project_dir)
    rng = np.random.default_rng(seed)
    voice, _ = read_wav(project_dir / 'audio' / 'narration-full.wav')
    v_db = rms_db(voice)
    b = bed(duration, sections, seed=seed)
    b *= 10 ** ((v_db - bed_under_voice_db - rms_db(b, 0.0)) / 20)
    write_wav(project_dir / 'audio' / 'bed.wav', b)
    n = int(duration * SR)
    track = np.zeros(n)
    g = {'spark': 1.0, 'rep': 0.8, 'tick': 0.5, 'pop': 0.7, 'stamp': 1.0, 'swell': 0.8, 'pulse': 0.8}
    g.update(gains or {})
    count = 0
    for t0, kind in sorted(events):
        s = sfx(kind, rng) * g.get(kind, 1.0)
        i = int(t0 * SR)
        if i >= n:
            continue
        seg = s[: n - i]
        track[i:i + len(seg)] += seg
        count += 1
    peak = np.max(np.abs(track)) or 1.0
    track *= sfx_peak / peak
    write_wav(project_dir / 'audio' / 'sfx-track.wav', track)
    return {'voice_rms_db': round(v_db, 1), 'bed_rms_db': round(rms_db(b, 0.0), 1), 'sfx_events': count, 'sfx_peak': sfx_peak}
