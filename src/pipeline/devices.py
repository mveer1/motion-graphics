"""Explanation devices: check that a storyboard's per-scene `device` choices are sound.

The device table lives in specs/explanation-devices.json (which device serves which narrator job, per-film caps,
devices that must not run under narration); the handbook is docs/explanation-devices.md. `studio.py validate`
calls check_storyboard_devices() and reports its findings; tests/test-explanation-devices.py covers it.

Findings are (level, message) with level 'error' (an id or job that does not exist), 'warn' (a choice that
breaks a rule: wrong job, over the cap, under narration, declared but never called) or 'note'.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "specs" / "explanation-devices.json"

Finding = Tuple[str, str]


def load_spec(path: Path = SPEC_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def device_table(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Every device id (new devices and existing runtime pieces) -> {api, jobs, max_per_film?}."""
    table = {d["id"]: d for d in spec.get("devices", [])}
    for k, v in (spec.get("existing") or {}).items():
        if not k.startswith("$"):
            table.setdefault(k, dict(v, id=k))
    return table


def devices_for_job(spec: Dict[str, Any], job: str) -> List[str]:
    return [i for i, d in device_table(spec).items() if job in d.get("jobs", [])]


def api_pattern(api: str) -> "re.Pattern[str]":
    """Regex that finds a call of `api` however the film aliases the namespace (Studio.comp.x, S.comp.x, C.x)."""
    last = api.split(".")[-1]
    if last == "ui":
        return re.compile(r"\bui\.(?:input|button|toggle|cursor|notify)\s*\(")
    return re.compile(r"\." + re.escape(last) + r"\s*\(")


def _has_narration(scene: Dict[str, Any]) -> bool:
    return bool(str(scene.get("narration") or "").strip())


def check_storyboard_devices(sb: Dict[str, Any], html: Optional[str], video_type: Optional[str],
                             spec: Optional[Dict[str, Any]] = None) -> List[Finding]:
    spec = spec or load_spec()
    table = device_table(spec)
    jobs = spec.get("jobs", {})
    out: List[Finding] = []
    scenes = sorted(sb.get("scenes", []), key=lambda s: s.get("start_sec", 0))

    banned = set((spec.get("not_under_narration") or {}).get("techniques", []))
    banned |= set((spec.get("not_under_narration") or {}).get("capabilities", []))
    for s in scenes:
        if not _has_narration(s):
            continue
        caps = list(s.get("capabilities", []))
        cap_out = (s.get("transition_out") or {}).get("capability")
        if cap_out:
            caps.append(cap_out)
        hit = sorted(set(caps) & banned)
        if hit:
            out.append(("warn", f"scene '{s['id']}' has narration but uses {', '.join(hit)}, which must sit in a narration "
                                "pause or over music (specs/explanation-devices.json not_under_narration)."))

    declared = [(s, s["device"]) for s in scenes if s.get("device")]
    if scenes and not declared:
        out.append(("note", "no storyboard scene names a `device` ({job, id}); pick one per scene from "
                            "docs/explanation-devices.md so the film's devices are chosen, not improvised."))
        return out

    counts: Dict[str, int] = {}
    prev_id = None
    for s, dev in declared:
        sid, job, did = s["id"], dev.get("job"), dev.get("id")
        if job not in jobs:
            out.append(("error", f"scene '{sid}': device job '{job}' is unknown; jobs are {', '.join(sorted(jobs))}."))
            continue
        if did not in table:
            out.append(("error", f"scene '{sid}': device '{did}' is unknown; for '{job}' use "
                                 f"{', '.join(devices_for_job(spec, job)) or 'a scene of its own'}."))
            continue
        d = table[did]
        if job not in d.get("jobs", []):
            out.append(("warn", f"scene '{sid}': device '{did}' is not listed for job '{job}' (it serves "
                                f"{', '.join(d.get('jobs', []))}); for '{job}' use {', '.join(devices_for_job(spec, job))}."))
        counts[did] = counts.get(did, 0) + 1
        if html is not None and d.get("api") and not api_pattern(d["api"]).search(html):
            out.append(("warn", f"scene '{sid}' declares device '{did}' but src/index.html never calls {d['api']}."))
        if did == prev_id:
            out.append(("note", f"scene '{sid}' repeats device '{did}' from the scene before; fine for a continuation, "
                                "otherwise vary the device."))
        prev_id = did

    for did, n in sorted(counts.items()):
        cap = table[did].get("max_per_film")
        if cap and n > cap:
            out.append(("warn", f"device '{did}' is used in {n} scenes (cap {cap} per film); repeated tricks stop "
                                "carrying meaning."))
    rules = spec.get("film_rules") or {}
    limit = rules.get(f"max_distinct_devices_{video_type}") if video_type else None
    if limit and len(counts) > limit:
        out.append(("warn", f"{len(counts)} distinct devices in a {video_type} film (limit {limit}); a few devices "
                            "that recur with meaning read as designed, a new trick per scene reads as a demo reel."))
    return out
