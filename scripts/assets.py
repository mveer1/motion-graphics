#!/usr/bin/env python3
"""Creative asset engine CLI: plan, generate, track, reuse and import assets.

  providers                         what each provider can do, whether it is usable now, how far it was verified
  plan <task> [--aspect 16:9 ...]   which providers fit a request (and why not)
  generate <project> --task T --provider P[,fallback..] [--model M] --prompt "..." [--param k=v ...]
  procedural <project> --recipe R --width W --height H --seed N --colors #aaa,#bbb   (offline, deterministic)
  import <project> <file> --license-status user-supplied [--prompt "..."]             (register a manual download)
  jobs [--open]                     job records; `resume` continues unfinished ones without re-submitting
  resume
  list [--project P --type image]   library records
  show <asset-id>
  export <project-dir> <asset-id>...   copy assets into <project>/src/assets/ with a manifest (HyperFrames serves only the composition folder)
  approve|reject <asset-id>

Library: assets/library/ (index.jsonl, content-addressed files, jobs/). Media is gitignored; the index and job
records are small JSON and may be committed. Credentials: environment variables only (see `providers`).
Needs .venv/bin/python (Pillow, NumPy).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pipeline.assets import base  # noqa: E402
from pipeline.assets.engine import Engine  # noqa: E402
from pipeline.assets.providers import default_providers  # noqa: E402
from pipeline.assets.providers.procedural import RECIPES  # noqa: E402
from pipeline.assets.secrets import redact  # noqa: E402


def engine() -> Engine:
    return Engine(ROOT, default_providers())


def kv(items):
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


def cmd_providers(a):
    for name, p in engine().providers.items():
        c = p.capabilities()
        why = p.available()
        env = c["auth"].get("env_var")
        print(f"{name:<11} {'usable' if why is None else 'NOT usable: ' + why:<34} verification={c['verification']['level']:<18} tasks={', '.join(c['tasks'])}" + (f"  env={env}" if env else ""))
        for u in c["verification"].get("unverified", []):
            print(f"{'':<13}unverified: {u}")
    return 0


def cmd_plan(a):
    for e in engine().plan(a.task, aspect=a.aspect, resolution=a.resolution, duration=a.duration, references=a.references):
        print(f"{e['provider']:<11} fits={e['fits']!s:<5} available={e['available']!s:<5} local={e['local']!s:<5} {e['verification']:<18} {'; '.join(e['notes'] + ([e['unavailable_reason']] if e['unavailable_reason'] else []))}")
    return 0


def run_one(eng, res, poll):
    if res.get("reused"):
        print(f"reused {res['asset']['id']} (identical request already in the library; no provider called)")
        return 0
    job = res["job"]
    print(("resuming " if res.get("resumed") else "submitted ") + job["id"])
    eng.run([job], poll_sec=poll, on_event=lambda m: print("  " + m))
    job = eng.jobs.load(job["id"])
    if job["state"] == base.SUCCEEDED:
        print("assets:", ", ".join(job["asset_ids"]))
        return 0
    print(f"job {job['state']}: {job.get('error', {}).get('kind')}: {job.get('error', {}).get('message')}")
    return 2


def cmd_generate(a):
    eng = engine()
    req = {"prompt": a.prompt, **kv(a.param)}
    if a.reference:
        req["references"] = a.reference
    chain = a.provider.split(",")
    res = eng.submit(project=a.project, task=a.task, request=req, providers=chain, model=a.model or "", max_attempts=a.attempts, deadline_sec=a.deadline, beat=a.beat or "", shot=a.shot or "", force=a.force)
    return run_one(eng, res, a.poll)


def cmd_procedural(a):
    eng = engine()
    req = {"recipe": a.recipe, "width": a.width, "height": a.height, "seed": a.seed, "colors": a.colors.split(",") if a.colors else [], "options": kv(a.option), "prompt": a.note or ""}
    res = eng.submit(project=a.project, task="procedural-image", request=req, providers=["procedural"], model=a.recipe, beat=a.beat or "")
    return run_one(eng, res, 0.0)


def cmd_import(a):
    eng = engine()
    req = {"path": str(Path(a.file).expanduser().resolve()), "prompt": a.prompt or "", "license": {"status": a.license_status, **({"attribution": a.attribution} if a.attribution else {})}}
    res = eng.submit(project=a.project, task="import", request=req, providers=["import"], beat=a.beat or "")
    return run_one(eng, res, 0.0)


def cmd_jobs(a):
    for j in engine().jobs.all():
        if a.open and j["state"] in base.TERMINAL:
            continue
        print(f"{j['id']} {j['state']:<10} {j['provider']:<10} {j['task']:<16} attempts={j['attempts']}/{j['max_attempts']} {j.get('error', {}).get('kind', '')}")
    return 0


def cmd_resume(a):
    done = engine().resume_all(poll_sec=a.poll, on_event=lambda m: print("  " + m))
    print(f"{len(done)} jobs processed")
    return 0


def cmd_list(a):
    for r in engine().lib.search(project=a.project, type=a.type, approval=a.approval):
        print(f"{r['id']} {r['type']:<6} {r['source']:<10} {r.get('provider', '-'):<10} {r.get('width', '?')}x{r.get('height', '?')} {r['approval']:<8} {r['path']}")
    return 0


def cmd_export(a):
    import shutil
    eng = engine()
    pdir = Path(a.project)
    if not pdir.is_dir():
        pdir = ROOT / "projects" / a.project
    # HyperFrames serves only the composition folder, so media must live under <project>/src/ (or <project>/ for a bare composition)
    out = (pdir / "src" if (pdir / "src").is_dir() else pdir) / "assets"
    out.mkdir(exist_ok=True)
    man_path = out / "manifest.json"
    man = json.loads(man_path.read_text()) if man_path.exists() else {}
    for i, aid in enumerate(a.ids):
        r = eng.lib.get(aid)
        if not r:
            sys.exit(f"unknown asset {aid}")
        name = a.name[i] if a.name and i < len(a.name) else aid
        dst = out / (name + Path(r["path"]).suffix)
        shutil.copy2(ROOT / r["path"], dst)
        man[name] = {"asset_id": aid, "file": dst.name, "sha256": r["sha256"], "source": r["source"], "provider": r.get("provider"), "model": r.get("model"),
                     "prompt": r.get("prompt"), "params": r.get("params"), "license": r.get("license"), "request_key": r.get("request_key")}
        print(f"{aid} -> {dst.relative_to(ROOT)}")
    man_path.write_text(redact(json.dumps(man, indent=2)) + "\n")
    return 0


def cmd_show(a):
    r = engine().lib.get(a.id)
    if not r:
        sys.exit("not found")
    print(redact(json.dumps(r, indent=2)))
    return 0


def cmd_approval(state):
    def f(a):
        r = engine().lib.set_approval(a.id, state, a.note or "")
        print(f"{r['id']} -> {r['approval']}")
        return 0
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="cmd", required=True)
    s.add_parser("providers").set_defaults(fn=cmd_providers)
    p = s.add_parser("plan"); p.add_argument("task"); p.add_argument("--aspect"); p.add_argument("--resolution"); p.add_argument("--duration", type=float); p.add_argument("--references", type=int, default=0); p.set_defaults(fn=cmd_plan)
    p = s.add_parser("generate"); p.add_argument("project"); p.add_argument("--task", required=True); p.add_argument("--provider", required=True); p.add_argument("--model"); p.add_argument("--prompt", required=True)
    p.add_argument("--param", action="append"); p.add_argument("--reference", action="append"); p.add_argument("--attempts", type=int, default=3); p.add_argument("--deadline", type=float, default=600); p.add_argument("--poll", type=float, default=3)
    p.add_argument("--beat"); p.add_argument("--shot"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_generate)
    p = s.add_parser("procedural"); p.add_argument("project"); p.add_argument("--recipe", required=True, choices=RECIPES); p.add_argument("--width", type=int, default=1280); p.add_argument("--height", type=int, default=720)
    p.add_argument("--seed", type=int, default=1); p.add_argument("--colors"); p.add_argument("--option", action="append"); p.add_argument("--note"); p.add_argument("--beat"); p.set_defaults(fn=cmd_procedural)
    p = s.add_parser("import"); p.add_argument("project"); p.add_argument("file"); p.add_argument("--license-status", default="unknown", choices=["verified", "unknown", "user-supplied", "provider-terms", "not-applicable"])
    p.add_argument("--attribution"); p.add_argument("--prompt"); p.add_argument("--beat"); p.set_defaults(fn=cmd_import)
    p = s.add_parser("jobs"); p.add_argument("--open", action="store_true"); p.set_defaults(fn=cmd_jobs)
    p = s.add_parser("resume"); p.add_argument("--poll", type=float, default=3); p.set_defaults(fn=cmd_resume)
    p = s.add_parser("list"); p.add_argument("--project"); p.add_argument("--type"); p.add_argument("--approval"); p.set_defaults(fn=cmd_list)
    p = s.add_parser("show"); p.add_argument("id"); p.set_defaults(fn=cmd_show)
    p = s.add_parser("export"); p.add_argument("project"); p.add_argument("ids", nargs="+"); p.add_argument("--name", action="append", help="file stem per id, in order"); p.set_defaults(fn=cmd_export)
    for name, st in (("approve", "approved"), ("reject", "rejected")):
        p = s.add_parser(name); p.add_argument("id"); p.add_argument("--note"); p.set_defaults(fn=cmd_approval(st))
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
