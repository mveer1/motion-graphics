#!/usr/bin/env python3
"""
build-audio.py
Automated voice synthesis and exact timeline measurement for Motion Lab projects.

Features:
  - Reads narration scripts from src/narration.json or research.json.
  - Supports configurable voice speed (default 1.15x, 20% faster than benchmark).
  - Configurable voice persona (am_adam, af_bella, am_michael, etc.).
  - Inserts calibrated pause buffers between clips.
  - Measures millisecond-accurate clip durations.
  - Concatenates audio into audio/narration-full.wav.
  - Emits audio/timeline.json for GSAP animation keyframing.
  - Re-synthesises only the scenes whose text, voice or speed changed (--force redoes all); the audio it
    replaces is kept in audio/history/<when>/ (the WAVs are gitignored, so nothing else would keep them).

Usage:
  python3 scripts/build-audio.py projects/benchmark-neural-network
  python3 scripts/build-audio.py benchmark-neural-network --speed 1.15 --voice am_adam
"""

import argparse
import json
import os
import shutil
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from pipeline import narration  # noqa: E402

SAMPLE_RATE = 24000
SMART_SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "kokoro-smart-tts-skill" / "scripts"


def delegate_to_py312() -> None:
    """Re-run under Homebrew python3.12 when this interpreter lacks kokoro (the venv has none)."""
    if sys.executable == "/opt/homebrew/bin/python3.12":
        return
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import kokoro  # noqa: F401
        except ImportError:
            os.execv(py12, [py12] + sys.argv)


def resolve_project_dir(target_str: str) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    candidate = Path(target_str)

    if (repo_root / "projects" / target_str).is_dir():
        return (repo_root / "projects" / target_str).resolve()
    if candidate.is_dir():
        return candidate.resolve()
    if (repo_root / target_str).is_dir():
        return (repo_root / target_str).resolve()

    print(f"Error: Project '{target_str}' not found.", file=sys.stderr)
    sys.exit(1)


def generate_pause_wav(out_path: Path, duration_sec: float = 0.5, sample_rate: int = SAMPLE_RATE):
    num_samples = int(duration_sec * sample_rate)
    silence = np.zeros(num_samples, dtype=np.int16)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(silence.tobytes())


def get_wav_duration(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        return frames / float(rate)


def read_pcm(wav_path: Path):
    """int16 mono PCM of a scene clip written by this script, or None if it is not one."""
    try:
        with wave.open(str(wav_path), "rb") as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != SAMPLE_RATE:
                return None
            return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    except (OSError, wave.Error, EOFError):
        return None


def archive_previous(audio_dir: Path, scene_ids) -> Path:
    """Copy narration-full.wav, timeline.json and the named scene clips to audio/history/<when>/."""
    timeline = audio_dir / "timeline.json"
    master = audio_dir / "narration-full.wav"
    ref = timeline if timeline.exists() else master
    label = datetime.fromtimestamp(ref.stat().st_mtime, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = audio_dir / "history" / label
    n = 1
    while dest.exists():
        n += 1
        dest = audio_dir / "history" / f"{label}-{n}"
    dest.mkdir(parents=True)
    for p in [master, timeline] + [audio_dir / f"{sid}.wav" for sid in scene_ids]:
        if p.exists():
            shutil.copy2(p, dest / p.name)
    return dest


def synth_smart(pipe, text: str, out_wav: Path, voice: str, speed: float, preset: str):
    """One scene through kokoro-smart-tts-skill (normalisation, breath groups, edge fades); returns its PCM."""
    if str(SMART_SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SMART_SKILL_SCRIPTS))
    from smart_synth import synthesize_smart
    synthesize_smart(text=text, out_path=str(out_wav), preset=preset, voice=voice, speed=speed, lang=voice[0], pipe=pipe)
    return read_pcm(out_wav)


def build_audio(project_dir: Path, speed_override: float = None, voice_override: str = None, pause_sec: float = None,
                force: bool = False, prosody: str = None, preset: str = None):
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    req = narration.resolve_request(project_dir, speed=speed_override, voice=voice_override, pause=pause_sec,
                                    prosody=prosody, preset=preset)
    voice, speed, pause_sec, scenes = req["voice"], req["speed"], req["pause"], req["scenes"]
    engine = narration.engine_label()
    fps = 30
    if (project_dir / "project.json").exists():
        fps = json.loads((project_dir / "project.json").read_text(encoding="utf-8")).get("fps", 30)

    print("=" * 65)
    print(f"🎙️  MOTION LAB AUDIO ENGINE: {project_dir.name}")
    print("=" * 65)
    print(f"  • Voice Persona:  {voice}")
    print(f"  • Speech Speed:   {speed}x (configurable)")
    print(f"  • Inter-Scene:    {pause_sec}s pause buffer")
    print(f"  • Prosody:        {req['prosody']}")

    if not scenes:
        print(f"Error: No scenes found to synthesize (neither {project_dir / 'src' / 'narration.json'} "
              f"nor a scene_blueprint in research.json).", file=sys.stderr)
        sys.exit(1)

    # Which scene clips can be reused: same id, text, voice and speed as the timeline that made them
    previous = {}
    old_timeline = {}
    if (audio_dir / "timeline.json").exists():
        try:
            old_timeline = json.loads((audio_dir / "timeline.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old_timeline = {}
    if not force:
        for old in old_timeline.get("scenes") or []:
            match = next((s for s in scenes if s["id"] == old.get("id")), None)
            if match and narration.scene_matches(old, match, old_timeline, req, engine):
                previous[match["id"]] = old
    state, reasons = narration.narration_state(project_dir, req)
    redo = [s["id"] for s in scenes if s["id"] not in previous]
    gone = [s.get("id") for s in old_timeline.get("scenes") or [] if s.get("id") not in {x["id"] for x in scenes}]
    if (audio_dir / "narration-full.wav").exists() and (redo or gone or state != "current"):
        why = "; ".join(reasons) or ("forced" if force else f"engine {old_timeline.get('engine')} -> {engine}")
        dest = archive_previous(audio_dir, redo + gone)
        print(f"  • Previous audio: {state} ({why}); kept in {dest.relative_to(project_dir)}")

    # Prepare pause buffer
    pause_wav = audio_dir / "pause.wav"
    generate_pause_wav(pause_wav, duration_sec=pause_sec)

    pipe = None  # Kokoro loads (about 1.4 GB) only if a scene needs synthesis

    timeline_scenes = []
    current_time = 0.0
    pcm_chunks_master = []

    print("-" * 65)
    print(f"{'Scene ID':<10} | {'Duration':<10} | {'Timeline Range':<18} | {'Title'}")
    print("-" * 65)

    for i, sc in enumerate(scenes):
        scene_id = sc["id"]
        title = sc["title"]
        text = sc["text"]
        scene_spd = narration.scene_speed(sc, req)      # per-scene pace from src/narration.json, else the film's
        out_wav = audio_dir / f"{scene_id}.wav"

        pcm = read_pcm(out_wav) if scene_id in previous else None
        reused = pcm is not None
        if pcm is None and pipe is None:
            from kokoro import KPipeline
            pipe = KPipeline(lang_code=voice[0])  # Kokoro voice ids start with their language code (am_ -> a)
        if pcm is None and req["prosody"] != "raw":
            pcm = synth_smart(pipe, text, out_wav, voice, scene_spd, req["prosody"].split(":", 1)[1])
            if pcm is None or not len(pcm):
                print(f"Error: No audio produced for scene '{scene_id}'", file=sys.stderr)
                sys.exit(1)
        if pcm is None:
            # Synthesize via Kokoro
            chunks = []
            for res in pipe(text, voice=voice, speed=scene_spd):
                chunks.append(res.audio.numpy())

            if not chunks:
                print(f"Error: No audio produced for scene '{scene_id}'", file=sys.stderr)
                sys.exit(1)

            combined = np.concatenate(chunks)
            pcm = np.int16(np.clip(combined * 32767.0, -32768, 32767))

            with wave.open(str(out_wav), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(pcm.tobytes())

        dur = len(pcm) / float(SAMPLE_RATE)
        start_time = round(current_time, 3)
        end_time = round(current_time + dur, 3)

        pcm_chunks_master.append(pcm)

        timeline_scenes.append({
            "id": scene_id,
            "title": title,
            "text": text,
            "speed": scene_spd,
            "clip_path": f"audio/{scene_id}.wav",
            "duration_sec": round(dur, 3),
            "start_time_sec": start_time,
            "end_time_sec": end_time
        })

        time_range = f"{start_time:05.2f}s -> {end_time:05.2f}s"
        print(f"{scene_id:<10} | {dur:05.2f}s     | {time_range:<18} | {title}{' (reused)' if reused else ''}")

        current_time += dur

        # Append pause buffer between scenes (except after last scene)
        if i < len(scenes) - 1:
            pause_samples = int(pause_sec * SAMPLE_RATE)
            pause_pcm = np.zeros(pause_samples, dtype=np.int16)
            pcm_chunks_master.append(pause_pcm)
            current_time += pause_sec

    # Write master concatenated narration audio
    master_wav = audio_dir / "narration-full.wav"
    master_pcm = np.concatenate(pcm_chunks_master)
    with wave.open(str(master_wav), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(master_pcm.tobytes())

    total_duration = round(len(master_pcm) / float(SAMPLE_RATE), 3)

    # Build timeline dictionary
    timeline_data = {
        "project": project_dir.name,
        "voice": voice,
        "speed": speed,
        "pause_sec": pause_sec,
        "engine": engine,
        "prosody": req["prosody"],
        "total_duration_sec": total_duration,
        "target_fps": fps,
        "total_frames": int(np.ceil(total_duration * fps)),
        "scenes": timeline_scenes
    }

    timeline_json = audio_dir / "timeline.json"
    with open(timeline_json, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2)

    print("-" * 65)
    print(f"✅ Total Narration Duration: {total_duration:05.2f}s ({timeline_data['total_frames']} frames @ {fps}fps)")
    print(f"📁 Master Audio:            {master_wav.relative_to(project_dir.parent.parent)}")
    print(f"🗺️  Timeline Map:            {timeline_json.relative_to(project_dir.parent.parent)}")
    if old_timeline.get("scenes"):
        shifts = narration.scene_shifts(old_timeline, timeline_data, 1.0 / fps)
        if shifts:
            print("⚠️  Scene timing moved; cue times copied from the old timeline into src/ need re-timing:")
            for line in shifts:
                print(f"     {line}")
    print("=" * 65)

    return timeline_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Motion Lab Audio Synthesizer & Timeline Map")
    parser.add_argument("project", help="Project name or path (e.g. benchmark-neural-network)")
    parser.add_argument("--speed", type=float, default=None, help="Voice speed modifier (e.g. 1.15)")
    parser.add_argument("--voice", default=None, help="Kokoro voice persona (e.g. am_adam, af_bella)")
    parser.add_argument("--pause", type=float, default=None,
                        help="Inter-scene pause in seconds (default: research.json acoustic_guidance, else 0.5)")
    parser.add_argument("--force", action="store_true", help="Re-synthesise every scene, even unchanged ones")
    parser.add_argument("--prosody", choices=["raw", "smart"], default=None,
                        help="raw (default): plain Kokoro; smart: kokoro-smart-tts-skill breath groups and pauses")
    parser.add_argument("--preset", default=None, help="Smart-prosody preset (default technical-explainer)")
    args = parser.parse_args()

    delegate_to_py312()
    p_dir = resolve_project_dir(args.project)
    # Kokoro is a heavy job: one at a time on 8 GB, shared with renders
    from pipeline.hostlock import heavy_lock

    with heavy_lock("tts", slug=p_dir.name):
        build_audio(p_dir, speed_override=args.speed, voice_override=args.voice, pause_sec=args.pause, force=args.force,
                    prosody=args.prosody, preset=args.preset)
