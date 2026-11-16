#!/usr/bin/env python3
"""fitness-gates.py: the four review gates of a fitness film, with automated evidence kept apart from human sign-off.

    .venv/bin/python scripts/fitness-gates.py <slug> [--json]

  G1 research and script     the dossier validates (fitness.py dossier), the story review says "complete"
  G2 storyboard and animatic the storyboard exists, `studio.py validate` passes, the animatic ran (qa/animatic.json)
  G3 animation and biomechanics   rig3d-check passes for every 3D exercise the composition uses, anatomy3d-check passes (both bodies), the fitness
                             review rubric (qa/fitness-review.json) has no critical failure
  G4 final export            the final film exists and fitness-qa.py passes on it (and the studio QA gates ran at build)

Automated checks can FAIL a gate; they can never APPROVE educational accuracy. G1 and G3 (scientific, anatomical and biomechanical accuracy) are
approved only when qa/fitness-signoff.json names a human reviewer for them. This script reads that file, it never writes it. Result: qa/gates.json.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable


def run(cmd, timeout=900):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return r.returncode, (r.stdout + r.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    pdir = ROOT / "projects" / a.slug
    qa = pdir / "qa"
    qa.mkdir(exist_ok=True)
    sign = json.loads((qa / "fitness-signoff.json").read_text()) if (qa / "fitness-signoff.json").exists() else {}
    gates = {}

    def gate(gid, title, checks, human=False):
        fails = [f"{n}: {why}" for n, ok, why in checks if ok is False]
        pend = [f"{n}: {why}" for n, ok, why in checks if ok is None]
        auto = "fail" if fails else ("pending" if pend else "pass")
        so = sign.get(gid)
        status = auto
        if auto == "pass" and human:
            status = "approved" if so and so.get("by") else "awaiting-human-signoff"
        gates[gid] = {"title": title, "automated": auto, "status": status, "failures": fails, "pending": pend, "human_signoff": so, "needs_human": human}

    # G1
    brief = json.loads((pdir / "brief.json").read_text()) if (pdir / "brief.json").exists() else {}
    need_res = brief.get("research", {}).get("required", True)
    c1 = []
    if (pdir / "research" / "dossier.json").exists():
        rc, out = run([PY, "scripts/fitness.py", "dossier", a.slug])
        c1.append(("dossier", rc == 0, out.strip().splitlines()[-1] if out.strip() else "dossier check failed"))
    else:
        c1.append(("dossier", None if need_res else True, "no research/dossier.json" if need_res else "research not required by the brief"))
    sr = qa / "story-review.json"
    if sr.exists():
        v = json.loads(sr.read_text()).get("verdict")
        c1.append(("story review", v == "complete", f"verdict is '{v}'"))
    else:
        c1.append(("story review", None, "qa/story-review.json missing"))
    gate("G1", "Research and script approval", c1, human=True)

    # G2
    c2 = [("storyboard", (pdir / "storyboard.json").exists(), "storyboard.json missing")]
    rc, out = run([PY, "scripts/studio.py", "validate", a.slug])
    c2.append(("studio validate", rc == 0, "\n".join(l for l in out.splitlines() if "ERROR" in l)[:300] or "validation failed"))
    an = qa / "animatic.json"
    c2.append(("animatic", True if an.exists() else None, "run fitness-animatic.py"))
    gate("G2", "Storyboard and animatic approval", c2)

    # G3
    html = (pdir / "src" / "index.html").read_text() if (pdir / "src" / "index.html").exists() else ""
    ids = sorted(set(re.findall(r"T3\.scene\(\s*stage\s*,\s*'([a-z-]+)'", html)) | set(re.findall(r"id:\s*'([a-z]+)'", html)) & {"curl", "press", "raise", "squat", "hipthrust", "calfraise", "seatedcalf"})
    c3 = []
    if ids:
        rc, out = run(["node", "scripts/rig3d-check.js"] + ids)
        c3.append((f"rig3d-check {' '.join(ids)}", rc == 0, "\n".join(l.strip() for l in out.splitlines() if "FAIL" in l)[:300] or "failed"))
        rc, out = run(["node", "scripts/anatomy3d-check.js"])
        c3.append(("anatomy3d-check", rc == 0, "\n".join(l.strip() for l in out.splitlines() if "FAIL" in l)[:300] or "failed"))
    else:
        c3.append(("3D exercises", True, "this film uses no 3D exercise"))
    fr = qa / "fitness-review.json"
    if fr.exists():
        d = json.loads(fr.read_text())
        todo = "TODO" in json.dumps(d)
        rc, out = run([PY, "scripts/fitness.py", "review", a.slug])
        c3.append(("fitness review rubric", None if todo else rc == 0, "rubric not scored yet (TODO fields)" if todo else (out.strip().splitlines() or ["failed"])[-1]))
    else:
        c3.append(("fitness review rubric", None, "qa/fitness-review.json missing (fitness.py review <slug> --init)"))
    gate("G3", "Animation and biomechanical review", c3, human=True)

    # G4
    finals = sorted((pdir / "renders").glob("*/final.mp4"))
    c4 = [("final film", bool(finals), "no renders/<format>/final.mp4")]
    if finals:
        rc, out = run([PY, "scripts/fitness-qa.py", str(finals[0].relative_to(ROOT)), "--expect-audio", "--allow-hold", "2.0", "--motion", "0.8"])
        c4.append(("fitness-qa.py", rc == 0, "\n".join(l.strip() for l in out.splitlines() if "FAIL" in l)[:400] or "failed"))
    gate("G4", "Final editing and export review", c4)

    res = {"slug": a.slug, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "gates": gates,
           "note": "Automated checks can fail a gate, never approve accuracy: G1 and G3 need a named human in qa/fitness-signoff.json."}
    (qa / "gates.json").write_text(json.dumps(res, indent=1))
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        for gid, g in gates.items():
            print(f"{gid}  {g['status']:<24} {g['title']}")
            for f in g["failures"]:
                print("      FAIL: " + f)
            for f in g["pending"]:
                print("      pending: " + f)
    return 1 if any(g["automated"] == "fail" for g in gates.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
