"""
Entry point Blender runs for one figure (scripts/mythic3d.py writes the job and holds the host lock):

    blender -b --factory-startup --python-exit-code 1 --python src/blender/mythic3d/run.py -- --job <job.json>

Job: {"figure": id, "options": {...}, "look": "painted"|"bronze", "out_dir": dir, "views": [names],
"width": px, "height": px, "samples": n, "engine": "eevee"|"cycles"}. Writes <out_dir>/<figure>-<look>-<view>.png
and <out_dir>/<figure>-<look>.json (timings, mesh sizes, identity meta).
"""

import json
import math
import os
import sys
import time
import traceback

import bpy

VIEWS = {
    # name: (yaw, elevation, frame (fraction of the figure's frame height), target ('body' or 'head'), size)
    "hero": (24.0, -7.0, 1.0, "body", (1080, 1350)),
    "front": (0.0, 0.0, 1.0, "body", None),
    "q3": (40.0, 0.0, 1.0, "body", None),
    "profile": (90.0, 0.0, 1.0, "body", None),
    "q3back": (140.0, 0.0, 1.0, "body", None),
    "back": (180.0, 0.0, 1.0, "body", None),
    "head": (22.0, 0.0, 1.0, "head", (900, 900)),
    "head-front": (0.0, 0.0, 1.0, "head", (900, 900)),
    "head-profile": (90.0, 0.0, 1.0, "head", (900, 900)),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    job_path = argv[argv.index("--job") + 1]
    with open(job_path, encoding="utf-8-sig") as fh:
        job = json.load(fh)
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if kit not in sys.path:
        sys.path.insert(0, kit)
    from mythic3d import figures, looks, stage

    t0 = time.time()
    W, Hh = int(job.get("width", 900)), int(job.get("height", 1200))
    spec = figures.FIGURES[job["figure"]]
    st = stage.Stage(W, Hh, int(job.get("samples", 48)), job.get("engine", "eevee"), rim=spec.get("rim", "#F2C46B"))
    look = looks.Look(job.get("look", "painted"))
    info = figures.build(job["figure"], look, st, job.get("options") or {})
    t_build = time.time() - t0
    os.makedirs(job["out_dir"], exist_ok=True)
    stem = job["figure"] + ("-" + job["tag"] if job.get("tag") else "") + "-" + look.kind
    if job.get("check"):
        write_check(job, stem, info, t_build)
        return
    shots = []
    for name in job.get("views", ["hero", "front", "q3", "profile", "q3back", "back", "head"]):
        yaw, elev, frac, target, size = VIEWS[name]
        rw, rh = size or (W, Hh)
        st.scene.render.resolution_x, st.scene.render.resolution_y = rw, rh
        if target == "head":
            tgt, fh = info["head"], info["head_frame"]
        else:
            tgt, fh = info["center"], info["frame"] * frac
            if rw > rh:
                fh *= rh / rw * 1.0
        yaw = info.get("yaw_bias", 0.0) + yaw if name == "hero" else yaw
        if name == "hero":
            # A low, reverent camera (sacred images stay high): below the chest, never under the floor.
            dist = info.get("dist", 11.0)
            cam_z = max(0.55, tgt.z - 0.55)
            elev = math.degrees(math.asin(max(-0.5, min(0.5, (cam_z - tgt.z) / dist))))
        st.view(tgt, fh, yaw=yaw, elev=elev, dist=info.get("dist", 11.0))
        path = os.path.join(job["out_dir"], f"{stem}-{name}.png")
        t1 = time.time()
        st.render(path)
        shots.append({"view": name, "file": os.path.basename(path), "seconds": round(time.time() - t1, 2)})
        print(f"[mythic3d] {name} {shots[-1]['seconds']} s")
    meta = {"figure": job["figure"], "look": look.kind, "options": job.get("options") or {}, "blender": bpy.app.version_string,
            "engine": st.scene.render.engine, "samples": job.get("samples", 48), "build_seconds": round(t_build, 2),
            "faces": sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH"),
            "meta": info.get("meta", {}), "shots": shots}
    with open(os.path.join(job["out_dir"], f"{stem}.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print("[mythic3d] done " + json.dumps({k: meta[k] for k in ("figure", "look", "build_seconds", "faces")}))


def write_check(job, stem, info, t_build):
    """Build-only report for tests: every mesh's world bounds and vertex count, and a digest of all geometry
    (rounded to 0.1 mm) so two builds of the same figure can be compared for determinism."""
    import hashlib

    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    digest = hashlib.sha256()
    objs = {}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH" or ob.name in ("cyclorama",):
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        M = np.array(ob.matrix_world)
        co = co @ M[:3, :3].T + M[:3, 3]
        ev.to_mesh_clear()
        if len(co) == 0:
            continue
        digest.update(ob.name.encode())
        digest.update(np.round(co * 10000).astype(np.int64).tobytes())
        objs[ob.name] = {"verts": int(len(co)), "min": [round(float(x), 4) for x in co.min(0)], "max": [round(float(x), 4) for x in co.max(0)],
                         "on_turntable": ob.parent is not None}
    out = {"figure": job["figure"], "options": job.get("options") or {}, "build_seconds": round(t_build, 2), "digest": digest.hexdigest(),
           "head": [round(float(x), 4) for x in info["head"]], "meta": info.get("meta", {}), "objects": objs}
    with open(os.path.join(job["out_dir"], f"{stem}-check.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("[mythic3d] check " + json.dumps({"figure": job["figure"], "objects": len(objs), "digest": out["digest"][:12]}))


try:
    main()
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    sys.exit(1)
