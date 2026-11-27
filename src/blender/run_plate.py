"""
Entry point Blender runs for one plate job (do not call directly; scripts/visual-director.py does):

    blender -b --factory-startup --python-exit-code 1 --python src/blender/run_plate.py -- --job <job.json>

The job (written by visual-director.py) carries the plate script path, size, fps, duration, palette,
seed, engine, alpha and the frames folder. The script's build(lab, job) makes the scene; this file
configures rendering first (so build() sees the engine), bakes simulations, renders PNG frames
and writes <frames_dir>/../done.json.
"""

import importlib.util
import json
import os
import sys
import time
import traceback

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 2 or argv[0] != "--job":
        raise SystemExit("usage: blender -b --python run_plate.py -- --job <job.json>")
    with open(argv[1], encoding="utf-8-sig") as fh:
        job = json.load(fh)

    sys.path.insert(0, job["kit_dir"])
    import mlab

    started = time.time()
    mlab.reset_scene()
    lab = mlab.Lab(job)
    settings = mlab.configure(lab, job)

    spec = importlib.util.spec_from_file_location("plate_script", job["script"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build"):
        raise SystemExit(f"{job['script']} defines no build(lab, job)")
    module.build(lab, job)

    if bpy.context.scene.camera is None:
        raise SystemExit(f"{job['script']}: build() made no camera (use lab.camera(...))")

    if bpy.context.scene.rigidbody_world is not None or any(
            m.type in ("PARTICLE_SYSTEM", "CLOTH", "FLUID") for o in bpy.data.objects for m in o.modifiers):
        # bake first, so a preview that skips frames still sees the simulation state of each frame
        with bpy.context.temp_override(scene=bpy.context.scene):
            bpy.ops.ptcache.bake_all(bake=True)

    os.makedirs(job["frames_dir"], exist_ok=True)
    bpy.ops.render.render(animation=True)

    scene = bpy.context.scene
    done = {
        "plate": job.get("plate"),
        "format": job.get("format"),
        "blender": bpy.app.version_string,
        "engine": settings["engine"],
        "device": settings["device"],
        "samples": settings["samples"],
        "frames": len(range(scene.frame_start, scene.frame_end + 1, scene.frame_step)),
        "seconds": round(time.time() - started, 2),
    }
    with open(os.path.join(os.path.dirname(job["frames_dir"].rstrip("/\\")), "done.json"), "w", encoding="utf-8") as fh:
        json.dump(done, fh, indent=2)
    print("[mlab] done " + json.dumps(done))


try:
    main()
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    sys.exit(1)
