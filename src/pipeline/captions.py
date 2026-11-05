"""Word-timed captions: align the script to measured word times, then group words into short phrases.

Narration is synthetic, so the script text is known exactly and the only thing missing is when each word is
spoken. `hyperframes transcribe` (local Whisper) supplies word times; this module aligns them to the script so
the on-screen spelling is the script's (a recogniser writes "11" for "eleventh" and "Danfoss" for "DAN-foss"),
fills any gap by interpolation, and groups the words into 1 to 3 word phrases for fast portrait captions.

  tokenize        script text -> tokens with sentence / comma flags
  align           script tokens + recogniser words -> a (start, end) per token, and how much was matched
  phrases         timed tokens -> caption cues of 1 to 3 words
  word_index      find the film time at which a phrase is spoken (to snap a storyboard beat to its noun)

The phrase rules are a port of an idea (not code) from Jake Schincariol's master-skills `/edit` (MIT): break
after . ! ? and after a comma once a phrase has two words, break on a pause, cap the length in characters, never
end on a weak opener, and let a phrase that would flash by grow a word. Everything is pure Python.
"""
from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

WEAK_ENDINGS = {
    "the", "a", "an", "to", "of", "and", "or", "but", "in", "on", "at", "for", "with", "by", "from", "as",
    "is", "are", "was", "were", "that", "this", "than", "into", "its", "it's", "our", "your", "their", "his", "her",
    "had", "has", "have", "been", "be", "will", "would", "can", "could", "should", "did", "does", "do", "not",
}
MAX_WORDS = 3
MAX_CHARS = 18
PAUSE_BREAK_SEC = 0.30
MIN_SHOWN_SEC = 0.35
TAIL_HOLD_SEC = 0.12


def norm(token: str) -> str:
    return re.sub(r"[^a-z0-9]", "", token.lower())


def tokenize(text: str) -> List[Dict[str, Any]]:
    """Whitespace tokens of the script, each flagged when it ends a sentence or a clause."""
    out = []
    for raw in text.split():
        stripped = raw.rstrip("\"'”’)")
        out.append({
            "text": raw,
            "norm": norm(raw),
            "sent_end": bool(re.search(r"[.!?…]$", stripped)),
            "clause_end": bool(re.search(r"[,;:—–]$", stripped)),
        })
    return out


def align(tokens: List[Dict[str, Any]], asr: Sequence[Dict[str, Any]], span: Tuple[float, float]) -> Tuple[List[Tuple[float, float]], float]:
    """Give every script token a (start, end) in seconds. Returns (times, matched_fraction).

    asr: [{text, start, end}] in the same clock as `span` (the scene's start and end). Exact matches take the
    recogniser's times. A run that differs ("18" against "eighteen", "11." against "eleventh") shares the
    recogniser's span for that run in proportion to character length. Tokens with no counterpart are
    interpolated between their neighbours. With no usable words at all, the scene span is shared by length."""
    n = len(tokens)
    if n == 0:
        return [], 1.0
    a_norm = [norm(w["text"]) for w in asr]
    s_norm = [t["norm"] for t in tokens]
    times: List[Optional[Tuple[float, float]]] = [None] * n
    matched = 0
    if asr:
        sm = difflib.SequenceMatcher(a=s_norm, b=a_norm, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    w = asr[j1 + k]
                    times[i1 + k] = (float(w["start"]), float(w["end"]))
                matched += i2 - i1
            elif tag == "replace":
                t0, t1 = float(asr[j1]["start"]), float(asr[j2 - 1]["end"])
                _share(tokens, times, i1, i2, t0, t1)
    if all(t is None for t in times):
        _share(tokens, times, 0, n, span[0], span[1])
    else:
        _fill_gaps(tokens, times, span)
    return [t if t is not None else span for t in times], matched / n


def _share(tokens: List[Dict[str, Any]], times: List[Optional[Tuple[float, float]]], i1: int, i2: int, t0: float, t1: float) -> None:
    weights = [max(len(tokens[i]["norm"]), 1) for i in range(i1, i2)]
    total = float(sum(weights))
    t = t0
    for k, i in enumerate(range(i1, i2)):
        d = (t1 - t0) * weights[k] / total
        times[i] = (t, t + d)
        t += d


def _fill_gaps(tokens: List[Dict[str, Any]], times: List[Optional[Tuple[float, float]]], span: Tuple[float, float]) -> None:
    n = len(tokens)
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        left = times[i - 1][1] if i > 0 and times[i - 1] else span[0]
        right = times[j][0] if j < n and times[j] else span[1]
        if right < left:
            right = left
        _share(tokens, times, i, j, left, right)
        i = j


# --------------------------------------------------------------------------- phrases
def phrases(tokens: List[Dict[str, Any]], times: List[Tuple[float, float]], *, max_words: int = MAX_WORDS,
            max_chars: int = MAX_CHARS) -> List[Dict[str, Any]]:
    """Group timed tokens into caption cues of 1..max_words words. Cues never overlap."""
    groups: List[List[int]] = []
    cur: List[int] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            groups.append(cur)
            cur = []

    for i, tok in enumerate(tokens):
        if cur:
            gap = times[i][0] - times[cur[-1]][1]
            chars = len(" ".join(tokens[k]["text"] for k in cur + [i]))
            if len(cur) >= max_words or chars > max_chars or gap >= PAUSE_BREAK_SEC:
                flush()
        cur.append(i)
        if tok["sent_end"] or (tok["clause_end"] and len(cur) >= 2):
            flush()
    flush()

    # never end a cue on a weak opener: hand the word to the next cue of the same sentence, else absorb the next word
    k = 0
    while k < len(groups):
        g = groups[k]
        last = g[-1]
        weak = tokens[last]["norm"] in WEAK_ENDINGS and not tokens[last]["sent_end"]
        if weak and k + 1 < len(groups) and len(g) > 1:
            groups[k + 1].insert(0, g.pop())
        elif weak and k + 1 < len(groups) and len(g) == 1:
            nxt = groups[k + 1]
            g.append(nxt.pop(0))
            if not nxt:
                groups.pop(k + 1)
        k += 1

    # a lone closing word ("in.") borrows the last word of the cue before it, so the sentence does not end on a flash;
    # the cue it borrows from must not be left ending on a weak word either, so those words travel together
    k = 1
    while k < len(groups):
        g, prev = groups[k], groups[k - 1]
        if (len(g) == 1 and tokens[g[0]]["sent_end"] and not tokens[prev[-1]]["sent_end"] and len(prev) >= 2
                and times[g[0]][1] - times[g[0]][0] < MIN_SHOWN_SEC):
            moved = [prev.pop()]
            while prev and tokens[prev[-1]]["norm"] in WEAK_ENDINGS:
                moved.insert(0, prev.pop())
            g[0:0] = moved
            if not prev:
                groups.pop(k - 1)
                continue
        k += 1

    # a cue that would flash by absorbs the following word of its own sentence
    k = 0
    while k < len(groups):
        g = groups[k]
        shown = times[g[-1]][1] - times[g[0]][0]
        nxt = groups[k + 1] if k + 1 < len(groups) else []
        # taking the next word must not strand a lone, quick closing word again
        strands = len(nxt) == 2 and tokens[nxt[1]]["sent_end"] and times[nxt[1]][1] - times[nxt[1]][0] < MIN_SHOWN_SEC
        if shown < MIN_SHOWN_SEC and len(g) < max_words and nxt and not tokens[g[-1]]["sent_end"] and not strands:
            g.append(nxt.pop(0))
            if not nxt:
                groups.pop(k + 1)
            continue
        k += 1

    cues = []
    for gi, g in enumerate(groups):
        start = times[g[0]][0]
        end = times[g[-1]][1] + TAIL_HOLD_SEC
        if gi + 1 < len(groups):
            end = min(end, times[groups[gi + 1][0]][0])
        cues.append({
            "start": round(start, 3), "end": round(max(end, start + 0.05), 3),
            "text": " ".join(tokens[i]["text"] for i in g),
            "words": [{"text": tokens[i]["text"], "start": round(times[i][0], 3), "end": round(times[i][1], 3)} for i in g],
        })
    return _resolve_overlaps(cues)


def _resolve_overlaps(cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cues never overlap. A cue squeezed to nothing by the next one is merged into it."""
    out: List[Dict[str, Any]] = []
    for c in cues:
        if out and c["start"] < out[-1]["end"]:
            prev = out[-1]
            if c["start"] - prev["start"] >= 0.05:
                prev["end"] = round(c["start"], 3)
            else:  # the earlier cue would last under 50 ms: fold it into this one
                c = {**c, "start": prev["start"], "text": prev["text"] + " " + c["text"],
                     "words": prev.get("words", []) + c.get("words", [])}
                out.pop()
        out.append(c)
    return out


def sentence_cues(tokens: List[Dict[str, Any]], times: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
    """One cue per sentence, with exact start and end from the word times."""
    cues, cur = [], []
    for i, tok in enumerate(tokens):
        cur.append(i)
        if tok["sent_end"] or i == len(tokens) - 1:
            cues.append({"start": round(times[cur[0]][0], 3), "end": round(times[cur[-1]][1], 3),
                         "text": " ".join(tokens[k]["text"] for k in cur),
                         "words": [{"text": tokens[k]["text"], "start": round(times[k][0], 3), "end": round(times[k][1], 3)} for k in cur]})
            cur = []
    return cues


# --------------------------------------------------------------------------- lookup
def word_index(scene_words: Dict[str, List[Dict[str, Any]]], phrase: str) -> List[Dict[str, Any]]:
    """Every place a phrase is spoken: [{scene, start, end, text}] in film time. Case and punctuation ignored."""
    want = [norm(w) for w in phrase.split() if norm(w)]
    hits = []
    if not want:
        return hits
    for sid, ws in scene_words.items():
        have = [norm(w["text"]) for w in ws]
        for i in range(len(have) - len(want) + 1):
            if have[i:i + len(want)] == want:
                hits.append({"scene": sid, "start": ws[i]["start"], "end": ws[i + len(want) - 1]["end"],
                             "text": " ".join(w["text"] for w in ws[i:i + len(want)])})
    return hits


def check_cues(cues: List[Dict[str, Any]]) -> List[str]:
    """Problems in a cue list: overlaps, empty text, or an end before a start (used by the tests)."""
    errs = []
    for i, c in enumerate(cues):
        if c["end"] <= c["start"]:
            errs.append(f"cue {i} ends before it starts")
        if not c["text"].strip():
            errs.append(f"cue {i} is empty")
        if i and c["start"] < cues[i - 1]["end"] - 1e-6:
            errs.append(f"cue {i} overlaps the previous cue")
    return errs
