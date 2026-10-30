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
from pathlib import Path

# Auto-delegate to Python 3.12 on Apple Silicon macOS if current python lacks kokoro / torch
if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import kokoro
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

import numpy as np


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


def generate_pause_wav(out_path: Path, duration_sec: float = 0.5, sample_rate: int = 24000):
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


def build_audio(project_dir: Path, speed_override: float = None, voice_override: str = None, pause_sec: float = 0.5):
    # Determine settings
    research_file = project_dir / "research.json"
    narration_file = project_dir / "src" / "narration.json"
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    voice = voice_override
    speed = speed_override

    # Try reading defaults from research.json
    research_data = {}
    if research_file.exists():
        try:
            with open(research_file, "r", encoding="utf-8") as f:
                research_data = json.load(f)
            acoustic = research_data.get("acoustic_guidance", {})
            if not voice:
                voice = acoustic.get("recommended_voice")
            if speed is None:
                speed = acoustic.get("speech_rate")
            if "inter_scene_pause_sec" in acoustic and pause_sec == 0.5:
                pause_sec = acoustic.get("inter_scene_pause_sec", 0.5)
        except Exception as e:
            print(f"Warning: Could not read research.json: {e}")

    # Fallback defaults
    if not voice:
        voice = "am_adam"
    if speed is None:
        # Default to 1.15 (20% faster than initial 0.95 benchmark)
        speed = 1.15

    print("=" * 65)
    print(f"🎙️  MOTION LAB AUDIO ENGINE: {project_dir.name}")
    print("=" * 65)
    print(f"  • Voice Persona:  {voice}")
    print(f"  • Speech Speed:   {speed}x (configurable)")
    print(f"  • Inter-Scene:    {pause_sec}s pause buffer")

    # Load scenes
    scenes = []
    if narration_file.exists():
        with open(narration_file, "r", encoding="utf-8") as f:
            narr = json.load(f)
            scenes = narr.get("scenes", [])
    elif research_data.get("scene_blueprint"):
        for sb in research_data["scene_blueprint"]:
            scenes.append({
                "id": sb["scene_id"],
                "title": sb["title"],
                "text": sb.get("pedagogical_objective", "")
            })
    else:
        print(f"Error: Neither {narration_file} nor scene_blueprint in research.json found.", file=sys.stderr)
        sys.exit(1)

    if not scenes:
        print("Error: No scenes found to synthesize.", file=sys.stderr)
        sys.exit(1)

    # Prepare pause buffer
    pause_wav = audio_dir / "pause.wav"
    generate_pause_wav(pause_wav, duration_sec=pause_sec)

    # Import TTS pipeline wrapper
    repo_root = Path(__file__).resolve().parent.parent
    tts_script = repo_root / "src" / "pipeline" / "tts.py"
    if not tts_script.exists():
        print(f"Error: TTS wrapper not found at {tts_script}", file=sys.stderr)
        sys.exit(1)

    # Initialize Kokoro
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a")

    timeline_scenes = []
    current_time = 0.0
    pcm_chunks_master = []

    print("-" * 65)
    print(f"{'Scene ID':<10} | {'Duration':<10} | {'Timeline Range':<18} | {'Title'}")
    print("-" * 65)

    for i, sc in enumerate(scenes):
        scene_id = sc.get("id", f"s{i+1}")
        title = sc.get("title", f"Scene {i+1}")
        text = sc.get("text", "")
        out_wav = audio_dir / f"{scene_id}.wav"

        # Synthesize via Kokoro
        chunks = []
        for res in pipe(text, voice=voice, speed=speed):
            chunks.append(res.audio.numpy())

        if not chunks:
            print(f"Error: No audio produced for scene '{scene_id}'", file=sys.stderr)
            sys.exit(1)

        combined = np.concatenate(chunks)
        pcm = np.int16(np.clip(combined * 32767.0, -32768, 32767))

        with wave.open(str(out_wav), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm.tobytes())

        dur = len(pcm) / 24000.0
        start_time = round(current_time, 3)
        end_time = round(current_time + dur, 3)

        pcm_chunks_master.append(pcm)

        timeline_scenes.append({
            "id": scene_id,
            "title": title,
            "text": text,
            "clip_path": f"audio/{scene_id}.wav",
            "duration_sec": round(dur, 3),
            "start_time_sec": start_time,
            "end_time_sec": end_time
        })

        time_range = f"{start_time:05.2f}s -> {end_time:05.2f}s"
        print(f"{scene_id:<10} | {dur:05.2f}s     | {time_range:<18} | {title}")

        current_time += dur

        # Append pause buffer between scenes (except after last scene)
        if i < len(scenes) - 1:
            pause_samples = int(pause_sec * 24000)
            pause_pcm = np.zeros(pause_samples, dtype=np.int16)
            pcm_chunks_master.append(pause_pcm)
            current_time += pause_sec

    # Write master concatenated narration audio
    master_wav = audio_dir / "narration-full.wav"
    master_pcm = np.concatenate(pcm_chunks_master)
    with wave.open(str(master_wav), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(master_pcm.tobytes())

    total_duration = round(len(master_pcm) / 24000.0, 3)

    # Build timeline dictionary
    timeline_data = {
        "project": project_dir.name,
        "voice": voice,
        "speed": speed,
        "pause_sec": pause_sec,
        "total_duration_sec": total_duration,
        "target_fps": 30,
        "total_frames": int(np.ceil(total_duration * 30)),
        "scenes": timeline_scenes
    }

    timeline_json = audio_dir / "timeline.json"
    with open(timeline_json, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2)

    print("-" * 65)
    print(f"✅ Total Narration Duration: {total_duration:05.2f}s ({timeline_data['total_frames']} frames @ 30fps)")
    print(f"📁 Master Audio:            {master_wav.relative_to(project_dir.parent.parent)}")
    print(f"🗺️  Timeline Map:            {timeline_json.relative_to(project_dir.parent.parent)}")
    print("=" * 65)

    return timeline_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Motion Lab Audio Synthesizer & Timeline Map")
    parser.add_argument("project", help="Project name or path (e.g. benchmark-neural-network)")
    parser.add_argument("--speed", type=float, default=None, help="Voice speed modifier (e.g. 1.15)")
    parser.add_argument("--voice", default=None, help="Kokoro voice persona (e.g. am_adam, af_bella)")
    parser.add_argument("--pause", type=float, default=0.5, help="Inter-scene pause duration in seconds")
    args = parser.parse_args()

    p_dir = resolve_project_dir(args.project)
    build_audio(p_dir, speed_override=args.speed, voice_override=args.voice, pause_sec=args.pause)

