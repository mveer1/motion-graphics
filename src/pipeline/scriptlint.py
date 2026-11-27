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

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import captions as capmod
import hooks
import style_templates
import tweens as tw

SHORT_FORM_MAX_SEC = 60.0
LONG_SENTENCE_SEC = 8.0
ABSTRACT_RUN = 3
MIN_WHY_WORDS = 4
LABEL_WORDS = 3  # an on-screen card this short, with no pronoun or function word, is a label or a term; uncalibrated
PRONOUNS = {"he", "she", "her", "his", "him", "it", "its", "we", "you", "i", "our", "they", "them", "their", "no", "too"}
TWEEN_DUMP = Path("qa") / "motion" / "tweens.json"
COMPOSITION_SUFFIXES = {".html", ".js", ".css"}
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
        "story_review": maybe("qa/story-review.json"),
    }


# --------------------------------------------------------------------------- sentence sheet
REFERENCE_SPEED = 1.15  # hooks.DEFAULT_WPS was measured at am_adam 1.15x; words per second scale with speed


def film_speed(inputs: Dict[str, Any]) -> float:
    """The film's narration speed: project.json audio.speed, else what audio/timeline.json records, else 1.15."""
    audio = (inputs.get("project") or {}).get("audio") or {}
    return float(audio.get("speed") or (inputs.get("timeline") or {}).get("speed") or REFERENCE_SPEED)


def scene_wps(scene: Dict[str, Any], inputs: Dict[str, Any], wps: float = hooks.DEFAULT_WPS) -> float:
    """Estimated words per second for one src/narration.json scene: `wps` at 1.15x, scaled by the scene's own
    `speed` (story-writer pace map), else the film speed."""
    speed = float(scene["speed"]) if scene.get("speed") is not None else film_speed(inputs)
    return wps * speed / REFERENCE_SPEED


def sentence_rows(inputs: Dict[str, Any], wps: float = hooks.DEFAULT_WPS) -> Tuple[List[Dict[str, Any]], str]:
    """One row per spoken sentence with film-time start and end. Returns (rows, timing source).

    When the narration text changed after audio/timeline.json was made, the old clips and word times describe
    other words, so every sentence is estimated instead and the source says the audio is stale."""
    narration = (inputs.get("narration") or {}).get("scenes", [])
    stale = stale_scenes(inputs)
    tl = {} if stale else {s["id"]: s for s in (inputs.get("timeline") or {}).get("scenes", [])}
    word_times = {} if stale else (inputs.get("words") or {}).get("scenes", {})
    rows: List[Dict[str, Any]] = []
    source = "estimated from words per second at each scene's speed (narration not yet measured)"
    if stale:
        source = (f"audio is stale (narration text changed in {', '.join(stale)} since audio/timeline.json was made); "
                  "estimated from words per second at each scene's speed until build-audio.py re-makes it")
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
        rate = scene_wps(sc, inputs, wps)
        for s in sents:
            d = hooks.spoken_seconds(s, rate)
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
    if source.startswith("audio is stale"):
        out.append(("note", "audio-stale", f"{source.split(';')[0]}: sentence times below are estimates, not the old clip lengths."))
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
    # clarity reads the whole hook window: "Nobody made a mistake. Both lost one year." is two sentences, one hook
    window = " ".join(r["text"] for r in rows if r["start"] < first["start"] + hooks.HOOK_WINDOW_SEC)
    for note in hooks.clarity_notes(window):
        out.append(("note", "hook-unclear", f"hook {note}"))

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


# --------------------------------------------------------------------------- film-time gap audit
def stale_scenes(inputs: Dict[str, Any]) -> List[str]:
    """Scenes whose src/narration.json text differs from the text audio/timeline.json says it was made from.

    Empty when the timeline does not record text (an older format): staleness cannot be told then."""
    tl = {s["id"]: s for s in (inputs.get("timeline") or {}).get("scenes", []) if "id" in s}
    out = []
    for sc in (inputs.get("narration") or {}).get("scenes", []):
        old = tl.get(sc.get("id"))
        if old is not None and "text" in old and old["text"] != sc.get("text", ""):
            out.append(sc["id"])
    return out


def composition_hash(pdir: Path) -> str:
    """SHA-256 of the authored composition (src/ html, js and css, without the vendored _studio/ runtime).

    Line endings are normalised so a Windows and a Mac checkout of the same composition agree."""
    h = hashlib.sha256()
    src = pdir / "src"
    if src.is_dir():
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if not p.is_file() or rel.parts[0] == "_studio" or p.suffix not in COMPOSITION_SUFFIXES:
                continue
            h.update(rel.as_posix().encode("utf-8") + b"\0")
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def load_tween_dump(pdir: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    """(dump, 'current' | 'stale' | 'missing'): the tween dump `studio.py script --probe` or motion-qa cached."""
    p = pdir / TWEEN_DUMP
    if not p.exists():
        return None, "missing"
    try:
        dump = load_json(p)
    except ValueError:
        return None, "missing"
    return dump, ("current" if dump.get("composition_sha256") == composition_hash(pdir) else "stale")


def write_tween_dump(pdir: Path, dump: Dict[str, Any]) -> Path:
    p = pdir / TWEEN_DUMP
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({**dump, "composition_sha256": composition_hash(pdir)}, indent=1) + "\n", encoding="utf-8")
    return p


def narration_spans(timeline: Optional[Dict[str, Any]]) -> List[Tuple[float, float, str]]:
    spans = []
    for s in (timeline or {}).get("scenes", []):
        a = float(s.get("start_time_sec", 0.0))
        b = float(s.get("end_time_sec", a + float(s.get("duration_sec", 0.0))))
        if b > a:
            spans.append((a, b, s.get("id", "?")))
    return spans


def gap_findings(pdir: Path, inputs: Dict[str, Any]) -> List[Finding]:
    """Narration stretches over 2 s with no visual event, from the composition's own tweens. Warnings, never errors:
    the 2 s limit is the anti-laziness rule, and the event/ambient split is uncalibrated (see docs/short-form-lessons.md)."""
    probe_hint = f"`python scripts/studio.py script {pdir.name} --probe` on a host with the HyperFrames browser"
    dump, state = load_tween_dump(pdir)
    if state == "missing":
        return [("note", "gap-audit", f"no tween dump ({TWEEN_DUMP.as_posix()}), so narration stretches with no visual change are not "
                                      f"checked before the render; run {probe_hint}.")]
    if state == "stale":
        return [("note", "gap-audit", f"the composition changed since {TWEEN_DUMP.as_posix()} was written; re-run {probe_hint}.")]
    spans = narration_spans(inputs.get("timeline"))
    if not spans:
        return [("note", "gap-audit", "narration is not measured yet (no audio/timeline.json scenes); the gap audit needs measured speech.")]
    stale = stale_scenes(inputs)
    if stale:
        return [("note", "gap-audit", f"audio is stale: narration text changed in {', '.join(stale)} since audio/timeline.json was made, "
                                      f"so speech times are unknown. Run `python scripts/build-audio.py {pdir.name}`, then re-run.")]
    gaps = tw.narration_gaps(dump.get("tweens", []), spans, film_end=dump.get("duration"))
    hard = [g for g in gaps if g["ambient_share"] < 0.5]
    soft = [g for g in gaps if g["ambient_share"] >= 0.5]
    out: List[Finding] = []

    def show(gs: List[Dict[str, Any]]) -> str:
        return "; ".join(f"{g['scene']} {g['start']:.1f}-{g['end']:.1f}s ({g['sec']:.1f}s)" for g in gs[:6])

    if hard:
        out.append(("warn", "visual-gap", f"{len(hard)} narration stretch(es) over {tw.GAP_WARN_SEC:g}s where nothing in the timeline changes the picture "
                                          f"({show(hard)}). Snap a reveal, highlight or counter to a spoken word in each (`studio.py words`)."))
    if soft:
        out.append(("note", "ambient-only-gap", f"{len(soft)} narration stretch(es) over {tw.GAP_WARN_SEC:g}s where only a drift or pulse layer moves "
                                                f"({show(soft)}). Alive, but no visual event; consider a beat."))
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


# --------------------------------------------------------------------------- named things
def spoken_names(text: str, known_caps: Optional[set] = None) -> List[str]:
    """Names and figures a viewer hears: runs of capitalised words, and figures or number words with the word they
    count ('22 days', 'seven hundred stores'). A lone sentence-opening word counts only when the same word is also
    capitalised mid-sentence in the text (or in `known_caps`, the film's other text). Heuristic, no parser."""
    sents = [[re.sub(r"['’]s$", "", t.rstrip(".")) for t in re.findall(r"[A-Za-z0-9$%][A-Za-z0-9$%'’.-]*", s)] for s in split_sentences(text)]
    mid_caps = {t for toks in sents for t in toks[1:] if t[:1].isupper()} | (known_caps or set())
    out: List[str] = []
    for toks in sents:
        i = 0
        while i < len(toks):
            t = toks[i]
            if t[:1].isdigit() or t[:1] == "$" or t.lower() in hooks.NUMBER_WORDS - {"one", "half", "double"}:
                j = i
                while j + 1 < len(toks) and (toks[j + 1].lower() in hooks.NUMBER_WORDS or toks[j + 1][:1].isdigit()):
                    j += 1
                counted = j + 1 < len(toks) and toks[j + 1][:1].islower() and toks[j + 1] not in hooks.FUNCTION_WORDS
                if counted or "$" in t or "%" in toks[j]:  # a bare number is no name; '22 days', '$2.5' and '38%' are
                    out.append(" ".join(toks[i: j + 1 + counted]))
                i = j + 1 + counted
                continue
            if t[:1].isupper() and len(t) > 1:
                j = i
                while j + 1 < len(toks) and toks[j + 1][:1].isupper():
                    j += 1
                start = i
                while start <= j and (toks[start].lower() in hooks.FUNCTION_WORDS | STOP | PRONOUNS):
                    start += 1  # "Then Nash", "The Valmiki Ramayana": a capitalised opener is not part of the name
                if start <= j and (start or j > start or toks[start] in mid_caps):
                    out.append(" ".join(toks[start: j + 1]))
                i = j + 1
                continue
            i += 1
    unique: List[str] = []
    for n in out:
        if n.lower() not in {u.lower() for u in unique}:
            unique.append(n)
    return unique


def _listed(candidate: str, things: List[str]) -> bool:
    c = candidate.lower()
    toks = {w for w in re.findall(r"[a-z0-9]{3,}", c) if w not in STOP and w not in hooks.NUMBER_WORDS}
    for th in things:
        t = th.lower()
        if c in t or t in c or (toks and toks & set(re.findall(r"[a-z0-9]{3,}", t))):
            return True
    return False


def named_things(inputs: Dict[str, Any]) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """The story-writer's named_things list: qa/story-review.json, else a top-level storyboard.json entry."""
    for key, where in (("story_review", "qa/story-review.json"), ("storyboard", "storyboard.json")):
        doc = inputs.get(key) or {}
        if isinstance(doc.get("named_things"), list):
            return doc["named_things"], where
    return None, ""


def named_rows(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Per scene: on-screen labels and spoken names beside the named_things entries, with what is not listed.

    A card of LABEL_WORDS words or fewer is a label or a term and counts whole; a longer card is a sentence, and
    only the names and figures in it count."""
    things, _ = named_things(inputs)
    listed = [str(t.get("thing", "")) for t in (things or []) if isinstance(t, dict)]
    narration = {s["id"]: s.get("text", "") for s in (inputs.get("narration") or {}).get("scenes", [])}
    scenes = sorted((inputs.get("storyboard") or {}).get("scenes", []), key=lambda s: s["start_sec"])
    caps = {t for s in split_sentences(" ".join(narration.values())) for t in re.findall(r"[A-Za-z][A-Za-z'’-]*", s)[1:] if t[:1].isupper()}
    rows = []
    for sc in scenes:
        shown: List[str] = []
        for card in (t.strip() for t in sc.get("on_screen_text", [])):
            toks = [w.lower().strip(".,;:!?") for w in hooks.words(card)]
            if not toks:
                continue
            label = len(toks) <= LABEL_WORDS and not set(toks) & (hooks.FUNCTION_WORDS | PRONOUNS)
            shown += [card] if label else spoken_names(card, caps)
        spoken = spoken_names(narration.get(sc["id"]) or sc.get("narration", ""), caps)
        unlisted = [n for n in shown + spoken if not _listed(n, listed)] if things is not None else []
        if shown or spoken:
            rows.append({"scene": sc["id"], "shown": shown, "spoken": spoken, "unlisted": unlisted})
    return rows


def named_findings(rows: List[Dict[str, Any]], inputs: Dict[str, Any]) -> List[Finding]:
    """Leads only: the extraction is a heuristic (capitalised runs and counted figures), calibrated on no film yet."""
    things, where = named_things(inputs)
    if things is None:
        if not rows:
            return []
        return [("note", "named-things-missing", "no named_things list (qa/story-review.json, story-writer step 6), so names and figures "
                                                 "cannot be checked for an explanation; the table below lists what the scenes show and say.")]
    out: List[Finding] = []
    gaps = [t for t in things if isinstance(t, dict) and (not str(t.get("explained_by", "")).strip() or "MISSING" in str(t.get("explained_by", "")))]
    if gaps:
        shown = "; ".join(f"{t.get('thing', '?')} ({t.get('named_in', '?')})" for t in gaps[:6])
        out.append(("warn", "named-unexplained", f"{len(gaps)} of {len(things)} named_things in {where} have no explanation yet ({shown}). "
                                                 "Add a card, label, legend or definition, or cut the name."))
    unlisted = [(r["scene"], n) for r in rows for n in r["unlisted"]]
    if unlisted:
        shown = "; ".join(f"{s}: {n[:40]}" for s, n in unlisted[:8])
        out.append(("note", "named-not-listed", f"{len(unlisted)} on-screen label(s) or spoken name(s) are not in {where} named_things ({shown}). "
                                                "List each with where it is explained, or confirm it needs none."))
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
    nrows = named_rows(inputs)
    findings = (script_findings(rows, inputs, source) + gap_findings(pdir, inputs) + story_findings(srows, inputs)
                + named_findings(nrows, inputs))
    return {"project": pdir.name, "timing_source": source, "sentences": rows, "story": srows, "named": nrows,
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
    if rep.get("named"):
        lines.append("NAMED THINGS (shown | spoken; * = not in named_things)")
        for r in rep["named"]:
            mark = lambda n: ("*" if n in r["unlisted"] else "") + n[:36]  # noqa: E731
            lines.append(f"  {r['scene']:<10} {', '.join(mark(n) for n in r['shown']) or '-'}  |  {', '.join(mark(n) for n in r['spoken']) or '-'}")
        lines.append("")
    for level, fid, msg in rep["findings"]:
        lines.append(f"  [{level.upper():4}] {fid}: {msg}")
    lines.append("")
    lines.append("Judgment checks (a script cannot run these):")
    lines += [f"  - {p}" for p in rep["prompts"]]
    return "\n".join(lines)
