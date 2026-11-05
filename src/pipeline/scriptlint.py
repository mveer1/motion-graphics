"""Pre-render script and story lint.

Everything the motion checks find after a render, this finds before one, from files that already exist:
src/narration.json (the words), audio/timeline.json (measured clip lengths), audio/words.json (measured word
times, when `studio.py captions --timing words` has run), storyboard.json and brief.json.

  script_report   a timed sentence sheet plus findings about the hook, rhythm, loop and asks
  story_rows      the storyboard as a proposal table: Frame | Beat | On screen | Why
  findings        every finding is (level, id, message); level is "warn" (needs a decision) or "note"

The sentence sheet and the hook, abstract-run, loop and ask checks adapt the beat-sheet idea in Jake Schincariol's
instagram-agent-skill `ig-reel/beats.py` (MIT) to this pipeline: timings come from the measured Kokoro clips, not
from a words-per-minute guess. The story checks adapt the "value first" rules in HeyGen's hyperframes-creative
`story-spine.md`. All thresholds are starting values and are reported as leads, not verdicts.

Pure Python, no render host needed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import captions as capmod
import hooks
import style_templates

SHORT_FORM_MAX_SEC = 60.0
LONG_SENTENCE_SEC = 8.0
ABSTRACT_RUN = 3
MIN_WHY_WORDS = 4
CTA_PATTERNS = [
    ("follow", r"\bfollow (me|us|for|the)\b|\bfollow\.?$"),
    ("subscribe", r"\bsubscribe\b"),
    ("comment", r"\bcomment\b|\bdrop (it|a) (in )?the comments\b"),
    ("save", r"\bsave (this|it)\b"),
    ("share", r"\bshare (this|it)\b"),
    ("link", r"\blink in (my |the )?(bio|description)\b|\blink below\b"),
    ("like", r"\blike (and|this)\b|\bhit the like\b"),
]
FILLER_FRAMES = r"\b(in this (video|film|short|reel)|welcome to|thanks for watching|before we (start|begin|get started))\b"
STOP = {
    "that", "this", "with", "from", "have", "were", "will", "their", "there", "which", "about", "would", "could",
    "should", "into", "than", "then", "them", "they", "what", "when", "where", "while", "been", "being", "does",
    "more", "most", "some", "such", "only", "also", "even", "very", "just", "like", "over", "under", "after",
    "before", "because", "every", "many", "much", "other", "these", "those", "your", "ours", "each", "both",
}

Finding = Tuple[str, str, str]  # (level, id, message)


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def split_sentences(text: str) -> List[str]:
    return [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]


def content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def is_short_form(project: Dict[str, Any]) -> bool:
    """Portrait-first films are the reel / short deliverable (docs/VISION.md: the default format is portrait)."""
    return style_templates.is_portrait_first(project)


def load_inputs(pdir: Path) -> Dict[str, Any]:
    def maybe(rel: str) -> Optional[Any]:
        p = pdir / rel
        return load_json(p) if p.exists() else None

    return {
        "project": maybe("project.json") or {},
        "brief": maybe("brief.json"),
        "storyboard": maybe("storyboard.json"),
        "narration": maybe("src/narration.json"),
        "timeline": maybe("audio/timeline.json"),
        "words": maybe("audio/words.json"),
    }


# --------------------------------------------------------------------------- sentence sheet
def sentence_rows(inputs: Dict[str, Any], wps: float = hooks.DEFAULT_WPS) -> Tuple[List[Dict[str, Any]], str]:
    """One row per spoken sentence with film-time start and end. Returns (rows, timing source)."""
    narration = (inputs.get("narration") or {}).get("scenes", [])
    tl = {s["id"]: s for s in (inputs.get("timeline") or {}).get("scenes", [])}
    word_times = (inputs.get("words") or {}).get("scenes", {})
    rows: List[Dict[str, Any]] = []
    source = "estimated from words per second (narration not yet measured)"
    t_cursor = 0.0
    for sc in narration:
        sid, text = sc["id"], sc.get("text", "")
        sents = split_sentences(text)
        if not sents:
            continue
        measured = tl.get(sid)
        exact = word_times.get(sid)
        if exact:
            tokens = capmod.tokenize(text)
            idx = 0
            for s in sents:
                n = len(capmod.tokenize(s))
                chunk = exact[idx: idx + n]
                idx += n
                if chunk:
                    rows.append(_row(sid, s, chunk[0]["start"], chunk[-1]["end"]))
            if len(tokens) == len(exact):
                source = "measured word times (audio/words.json)"
            continue
        if measured:
            start, dur = float(measured["start_time_sec"]), float(measured["duration_sec"])
            total = sum(len(s) for s in sents) or 1
            t = start
            for s in sents:
                d = dur * len(s) / total
                rows.append(_row(sid, s, t, t + d))
                t += d
            if source.startswith("estimated"):
                source = "measured clip lengths (audio/timeline.json), split by sentence length"
            continue
        t = t_cursor
        for s in sents:
            d = hooks.spoken_seconds(s, wps)
            rows.append(_row(sid, s, t, t + d))
            t += d
        t_cursor = t + 0.5
    return rows, source


def _row(scene: str, text: str, start: float, end: float) -> Dict[str, Any]:
    toks = hooks.words(text)
    return {
        "scene": scene, "text": text, "start": round(start, 2), "end": round(end, 2),
        "dur": round(end - start, 2), "words": len(toks),
        "concrete": bool(hooks._concrete_positions(toks)),
    }


def tag_beats(rows: List[Dict[str, Any]], storyboard: Optional[Dict[str, Any]]) -> None:
    """Count storyboard beats that fall inside each sentence. None when the scene plans no beats."""
    scenes = {s["id"]: s for s in (storyboard or {}).get("scenes", [])}
    for r in rows:
        sc = scenes.get(r["scene"])
        if not sc or not sc.get("beats"):
            r["beats"] = None
            continue
        start = sc["start_sec"]
        times = [b["at_sec"] for b in sc["beats"]]
        if times and min(times) < start - 0.05 and start > 0.5:  # scene-relative beats
            times = [t + start for t in times]
        r["beats"] = sum(1 for t in times if r["start"] - 0.05 <= t <= r["end"] + 0.05)


# --------------------------------------------------------------------------- findings
def script_findings(rows: List[Dict[str, Any]], inputs: Dict[str, Any], source: str) -> List[Finding]:
    out: List[Finding] = []
    project = inputs.get("project") or {}
    if not rows:
        return [("note", "no-narration", "no src/narration.json scenes with text; nothing to lint.")]
    total = project.get("duration_sec") or rows[-1]["end"]
    short_form = is_short_form(project)
    reel_length = bool(total) and total <= SHORT_FORM_MAX_SEC

    first = rows[0]
    h = hooks.score_hook(first["text"])
    where = f"hook (first sentence, {first['dur']:.1f}s): \"{first['text'][:70]}\""
    if h["capped_by"]:
        out.append(("warn", "hook-preamble", f"{where} is a {h['capped_by']}. Start at the sentence you would reach at second six."))
    elif first["dur"] > hooks.HOOK_WINDOW_SEC + 0.5:
        out.append(("warn", "hook-long", f"{where} runs past the {hooks.HOOK_WINDOW_SEC:g}s hook window; say the claim first, move the detail to the next sentence."))
    if h["score"] < 50 and not h["capped_by"]:
        out.append(("note", "hook-weak", f"hook scores {h['score']}/100 ({'; '.join(h['notes'][:2]) or 'see studio.py hook score'}). A lint, not a prediction; write two alternatives from other formulas."))

    # abstract runs: consecutive sentences with nothing checkable in them
    run: List[Dict[str, Any]] = []
    for r in rows + [None]:  # type: ignore[list-item]
        if r is not None and not r["concrete"]:
            run.append(r)
            continue
        if len(run) >= ABSTRACT_RUN:
            level = "warn" if reel_length else "note"
            out.append((level, "abstract-run", f"{len(run)} sentences in a row with no figure, date or name ({run[0]['start']:.1f}-{run[-1]['end']:.1f}s, scene {run[0]['scene']}). "
                                               "Give the viewer something to check or see" + ("." if reel_length else "; mechanism sentences are often legitimately abstract, so this is a lead on a film over 60 s.")))
        run = []

    # long sentences, and sentences that carry a visual event too rarely
    for r in rows:
        if r["dur"] > LONG_SENTENCE_SEC:
            out.append(("note", "long-sentence", f"one sentence runs {r['dur']:.1f}s in scene {r['scene']} ({r['start']:.1f}s): consider splitting it for rhythm and for a visual change."))
    blind = [r for r in rows if r.get("beats") == 0 and r["dur"] >= 3.0]
    if blind:
        shown = ", ".join(f"{r['start']:.0f}s" for r in blind[:6])
        out.append(("note", "sentence-without-beat", f"{len(blind)} sentence(s) of 3s or more carry no planned storyboard beat (at {shown}). Narration over an unchanged frame breaks the anti-laziness rule."))

    # filler frames anywhere
    narr_text = " ".join(r["text"] for r in rows)
    m = re.search(FILLER_FRAMES, narr_text.lower())
    if m:
        out.append(("warn", "filler-frame", f"narration contains \"{m.group(0)}\": cut the framing sentence."))

    # one ask at most
    asks = {name for name, pat in CTA_PATTERNS if re.search(pat, narr_text.lower())}
    sb_text = " ".join(t for s in (inputs.get("storyboard") or {}).get("scenes", []) for t in s.get("on_screen_text", []))
    asks |= {name for name, pat in CTA_PATTERNS if re.search(pat, sb_text.lower())}
    if len(asks) > 1:
        out.append(("warn", "many-asks", f"asks for {len(asks)} different actions ({', '.join(sorted(asks))}). End on one."))

    # loop: the last sentence should echo something from the hook
    if len(rows) >= 3:
        hook_words, last_words = content_words(first["text"]), content_words(rows[-1]["text"])
        shared = hook_words & last_words
        if not shared:
            level = "warn" if (short_form and reel_length) else "note"
            out.append((level, "no-loop", "the last sentence shares no content word with the hook, so a replay does not land cleanly. "
                                          "Echo one word or image from the hook in the closing line" + ("." if level == "warn" else " (reel-length films only; this film runs over 60 s).")))

    pace = sum(r["words"] for r in rows) / max(rows[-1]["end"] - rows[0]["start"], 1e-6)
    speed = (inputs.get("timeline") or {}).get("speed")
    voice = f"this voice runs at {speed}x" if speed else "the voice speed is not recorded yet"
    out.append(("note", "pace", f"{pace:.1f} words per second over the spoken span; natural speech is about 2.5 and {voice}. Timing source: {source}."))
    return out


def story_rows(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    sb = inputs.get("storyboard") or {}
    rows = []
    for i, sc in enumerate(sorted(sb.get("scenes", []), key=lambda s: s["start_sec"]), 1):
        rows.append({
            "n": i, "id": sc["id"], "title": sc.get("title", ""), "start": sc["start_sec"], "end": sc["end_sec"],
            "on_screen": " / ".join(sc.get("on_screen_text", [])[:3]), "why": sc.get("why", ""),
            "purpose": sc.get("purpose", ""),
        })
    return rows


def story_findings(rows: List[Dict[str, Any]], inputs: Dict[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    if not rows:
        return [("note", "no-storyboard", "no storyboard.json; the story checks need scenes.")]
    missing = [r["id"] for r in rows if len(r["why"].split()) < MIN_WHY_WORDS]
    if len(missing) == len(rows):
        out.append(("warn", "why-missing", "no scene has a `why` (its job in the story, traced to the message). Add one per scene; a scene whose why cannot be traced to the message is a scene to cut."))
    elif missing:
        out.append(("warn", "why-missing", f"scenes without a usable `why`: {', '.join(missing)}."))

    brief = inputs.get("brief") or {}
    core = (brief.get("message") or {}).get("core_message", "")
    narration = {s["id"]: s.get("text", "") for s in (inputs.get("narration") or {}).get("scenes", [])}
    if core and narration:
        want = content_words(core)
        order = [r["id"] for r in rows]
        seen_at: Optional[int] = None
        best = 0.0
        for i, sid in enumerate(order):
            have = content_words(" ".join(narration.get(s, "") for s in order[: i + 1]))
            frac = len(want & have) / max(len(want), 1)
            best = max(best, frac)
            if frac >= 0.3 and seen_at is None:
                seen_at = i + 1
        if seen_at is None:
            out.append(("warn", "value-never-stated", f"the narration never reaches a third of the brief's core message words ({best:.0%} at the end). Is the message in the film?"))
        elif seen_at > 2:
            out.append(("note", "value-late", f"the core message's words are not in the narration until scene {seen_at}. Value-first rule: state it by scene 2, then spend the rest as evidence. Lexical overlap is a lead only."))
    return out


def delete_test_prompts(rows: List[Dict[str, Any]]) -> List[str]:
    """The two judgment checks a script cannot run. Printed for the reviewer."""
    ev = [r["id"] for r in rows if r["why"] and re.search(r"\b(evidence|proof|demonstrat|example|detail|number|source)\b", r["why"].lower())]
    return [
        "Delete the evidence scenes" + (f" ({', '.join(ev)})" if ev else "") + ": do the remaining scenes still state the value on their own?",
        "Delete the value scenes: if the film still seems to work, it was a feature tour, not a story.",
        "For each key visual: could it appear unchanged in another film on a different subject? If so, replace it with something only this subject could produce (its own number, phrase, filename or object).",
    ]


# --------------------------------------------------------------------------- top level
def script_report(pdir: Path, wps: float = hooks.DEFAULT_WPS) -> Dict[str, Any]:
    inputs = load_inputs(pdir)
    rows, source = sentence_rows(inputs, wps)
    tag_beats(rows, inputs.get("storyboard"))
    srows = story_rows(inputs)
    findings = script_findings(rows, inputs, source) + story_findings(srows, inputs)
    return {"project": pdir.name, "timing_source": source, "sentences": rows, "story": srows,
            "findings": findings, "prompts": delete_test_prompts(srows),
            "hook": hooks.score_hook(rows[0]["text"]) if rows else None}


def render_text(rep: Dict[str, Any], *, sheet: bool = True) -> str:
    lines = [f"SCRIPT AND STORY LINT: {rep['project']}", f"timing: {rep['timing_source']}", ""]
    if sheet and rep["sentences"]:
        lines.append(f"{'time':>11}  {'dur':>5}  {'w':>3}  {'beats':>5}  sentence")
        for r in rep["sentences"]:
            b = "-" if r.get("beats") is None else str(r["beats"])
            mark = " " if r["concrete"] else "~"
            lines.append(f"{r['start']:5.1f}-{r['end']:5.1f}  {r['dur']:5.1f}  {r['words']:3d}  {b:>5} {mark}{r['scene']}: {r['text'][:78]}")
        lines.append("   (~ = nothing concrete in the sentence; beats - = scene plans none)")
        lines.append("")
    if rep["story"]:
        lines.append("STORY PROPOSAL")
        lines.append(f"{'#':>2}  {'scene':<10} {'time':>11}  on screen  ->  why")
        for r in rep["story"]:
            lines.append(f"{r['n']:>2}  {r['id']:<10} {r['start']:5.1f}-{r['end']:5.1f}  {r['on_screen'][:44] or '(none)'}  ->  {r['why'] or '(no why)'}")
        lines.append("")
    for level, fid, msg in rep["findings"]:
        lines.append(f"  [{level.upper():4}] {fid}: {msg}")
    lines.append("")
    lines.append("Judgment checks (a script cannot run these):")
    lines += [f"  - {p}" for p in rep["prompts"]]
    return "\n".join(lines)
