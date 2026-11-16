#!/usr/bin/env python3
"""Build the three 2D-vs-3D comparison videos (regression fixture, 1080x1080, 30 fps, with sound).

    .venv/bin/python qa/regression/lab-3d-compare/build.py [curl press raise]

For each exercise: copy entries/compare-<x>.html to src/index.html (the only entry file HyperFrames reads; one root composition per folder), render under the host lock, make the Sinew
bed and rep SFX from the 3D rig's own phase map (node reads T3.exercises[id].phaseMap, so sound and picture share one rhythm), mux with the
studio's loudness chain, run the five QA gates, deliver to out/lab-3d-review/compare-<x>-2D-vs-3D.mp4 (the file it replaces goes to archive/).
Run `python scripts/studio.py sync qa/regression/lab-3d-compare` first when the runtime changed.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EX = {"curl": ("curl", "dumbbell-curl"), "press": ("press", "dumbbell-bench-press"), "raise": ("raise", "lateral-raise")}
PER, REPS, LEAD, FPS = 2.9, 3, 0.5, 30
DUR = round(LEAD + REPS * PER + 0.9, 3)
OUT = ROOT / "out" / "lab-3d-review"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, cwd=kw.pop("cwd", ROOT), **kw)


def phase_map(ex3d: str):
    js = ("global.window=global;const w=console.warn;console.warn=()=>{};global.THREE=require('./src/studio/vendor/three.min.js');console.warn=w;global.Studio={};"
          "['brand','tibi3d','anatomy3d','exercises3d'].forEach(f=>require('./src/studio/kits/fitness/'+f+'.js'));"
          f"console.log(JSON.stringify(Studio.kit.fitness.t3d.exercises['{ex3d}'].phaseMap))")
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, cwd=ROOT, check=True).stdout)


def sound(ex3d: str):
    # sinew_sound sets the bed level relative to a narration track; the comparison has none, so the lab narration is used as the level REFERENCE only (never mixed)
    shutil.copyfile(ROOT / "projects/lab-3d-motion/audio/narration-full.wav", HERE / "audio" / "narration-full.wav")
    spec = importlib.util.spec_from_file_location("sinew_sound", ROOT / ".claude/skills/fitness/scripts/sinew_sound.py")
    ss = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ss)
    pm = phase_map(ex3d)
    up = next(p for p in pm if p["kind"] == "up")
    end = next(p for p in pm if p["id"] == "end-range") if any(p["id"] == "end-range" for p in pm) else next(p for p in pm if p["kind"] == "hold" and p["a"] > up["a"])
    ev = [(0.05, "pop")]
    for r in range(REPS):
        t0 = LEAD + r * PER
        ev += [(t0 + up["a"] * PER, "tick"), (t0 + end["a"] * PER, "rep")]
    ev.append((DUR - 0.9, "spark"))
    return ss.build(HERE, duration=DUR, events=ev, sections=[(0.0, "lift")], gains={"rep": 0.5, "tick": 0.4})


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (HERE / "renders").mkdir(exist_ok=True)
    for name in names:
        ex3d, _ = EX[name]
        print(f"=== {name}")
        shutil.copyfile(HERE / "entries" / f"compare-{name}.html", HERE / "src" / "index.html")
        vis = HERE / "renders" / f"{name}-visuals.mp4"
        run(["python3.12", "scripts/session-guard.py", "run", "--slug", f"lab-3d-compare-{name}", "--cwd", str((HERE / "src").relative_to(ROOT)), "render", "--", "hyperframes", "render", ".",
             "--fps", str(FPS), "--quality", "looks", "--low-memory-mode", "--output", f"../renders/{name}-visuals.mp4"], stdin=subprocess.DEVNULL)
        print(sound(ex3d))
        fin = HERE / "renders" / f"{name}-final.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(vis), "-stream_loop", "-1", "-i", str(HERE / "audio" / "bed.wav"), "-i", str(HERE / "audio" / "sfx-track.wav"),
             "-filter_complex", f"[1:a]volume=0.6,afade=t=out:st={DUR - 1.5}:d=1.5[a2];[2:a]volume=0.85[a3];[a2][a3]amix=inputs=2:duration=longest:dropout_transition=2,"
                                "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]",
             "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(DUR),
             "-metadata", f"title={name.title()}: 2D vs 3D", "-metadata", f"comment=1080x1080 · {FPS} fps · same exercise, same scale, same phase clock", str(fin)])
        run(["bash", ".claude/skills/video-assembler/scripts/run-qa-gates.sh", str(fin), "--expect-width", "1080", "--expect-height", "1080", "--expect-fps", str(FPS),
             "--expect-duration", str(DUR), "--expect-lufs", "-16", "--lufs-tolerance", "2"])
        dst = OUT / f"compare-{name}-2D-vs-3D.mp4"
        if dst.exists():
            (OUT / "archive" / stamp).mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(OUT / "archive" / stamp / dst.name))
        shutil.copyfile(fin, dst)
        print("delivered", dst.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or list(EX)))
