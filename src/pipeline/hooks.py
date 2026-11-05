"""Hook scoring and the hook-formula library.

A hook is the first spoken sentence of a film. This module scores one on five properties that can be
computed from the text alone, names the best-fitting formula from specs/hook-formulas.json, and ranks
several candidates so the creative director writes three and picks, instead of accepting the first.

What the score is: a lint. It catches greetings, preambles, hooks with nothing concrete in them and hooks
that take too long to say. What it is not: a prediction of views. The idea (five text-only properties and a
preamble cap) comes from Jake Schincariol's short-form skills (MIT); the rules, word lists and weights here
are written for explainers and are uncalibrated. He measured his own panel at AUC 0.83 separating real hooks
from deliberately bad ones and 0.56 separating one creator's hits from the same creator's misses. Treat a high
score as "no obvious defect", never as "this will work".

Everything here is pure Python and runs anywhere.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
FORMULAS_PATH = ROOT / "specs" / "hook-formulas.json"

# Spoken pace for the workspace voice: am_adam at 1.15x lands near 2.9 words per second on the recent films.
DEFAULT_WPS = 2.9
HOOK_WINDOW_SEC = 3.0

WEIGHTS = {"length": 20, "specificity": 25, "stakes": 20, "frontload": 20, "tension": 15}
PREAMBLE_CAP = 30

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million", "billion",
    "trillion", "half", "dozen", "double", "triple",
}
STAKES_WORDS = {
    "lose", "lost", "loses", "losing", "loss", "cost", "costs", "costly", "die", "died", "dead", "death", "kill",
    "killed", "fail", "failed", "failure", "crash", "crashed", "collapse", "collapsed", "destroy", "destroyed",
    "wrong", "risk", "danger", "dangerous", "threat", "mistake", "stolen", "stole", "hack", "hacked", "fire",
    "burn", "burned", "burnt", "ban", "banned", "bankrupt", "broke", "broken", "secret", "hidden", "trap",
    "disaster", "outage", "shutdown", "leak", "leaked", "panic", "fraud", "scam", "free", "save", "saved",
    "wasted", "waste", "never", "nobody", "illegal", "war", "debt", "wiped",
}
TENSION_PATTERNS = [
    r"\?",
    r"\b(but|yet|except|instead|actually|only|still)\b",
    r"\b(nobody|no one|never|nothing|not a|wasn't|weren't|isn't|aren't|didn't|doesn't|couldn't)\b",
    r"^(why|how|what|when|where|who)\b",
    r"\b(the real|the truth|turns out|turned out|here's why|here is why)\b",
    r"\bthan\b.*\bthought\b|\bthought\b.*\bwas\b",
]
PREAMBLE_PATTERNS = [
    (r"^(hi|hey|hello|hiya|yo|welcome|good (morning|evening|afternoon))\b", "greeting"),
    (r"\b(in this (video|film|short|reel)|today (we|i)|today's (video|topic)|let's (talk|dive|look|explore|get)|"
     r"let me (tell|show|explain)|i('m| am) going to (show|tell|explain)|we('re| are) going to)\b", "preamble"),
    (r"^(have you ever (wondered|thought)|did you know|ever wondered)\b", "stock opener"),
    (r"^(so|okay|ok|alright|right|well|um|uh)[, ]", "filler opener"),
]

_TOKEN = re.compile(r"[A-Za-z0-9$%][A-Za-z0-9$%'’.,-]*")


def words(text: str) -> List[str]:
    return _TOKEN.findall(text)


def spoken_seconds(text: str, wps: float = DEFAULT_WPS) -> float:
    """Estimated speaking time. A figure like $18,000 is a few spoken words but one token; count it as two."""
    n = 0.0
    for w in words(text):
        n += 2.0 if re.search(r"\d", w) else 1.0
    return n / wps


def _concrete_positions(tokens: List[str]) -> List[int]:
    """Indices of tokens that carry something checkable: a figure, a number word, a name or a date."""
    out = []
    for i, tok in enumerate(tokens):
        bare = tok.strip(".,'’").lower()
        if re.search(r"\d", tok) or bare in NUMBER_WORDS:
            out.append(i)
        elif i > 0 and tok[:1].isupper() and len(bare) > 2 and bare not in {"the", "and", "but", "this", "that", "when"}:
            out.append(i)
    return out


def score_hook(text: str, wps: float = DEFAULT_WPS) -> Dict[str, Any]:
    """Score one hook line. Returns the total, the per-property points, the verdict and the reasons."""
    line = " ".join(text.split())
    tokens = words(line)
    lower = line.lower()
    props: Dict[str, float] = {}
    notes: List[str] = []

    sec = spoken_seconds(line, wps)
    if sec <= HOOK_WINDOW_SEC:
        props["length"] = 1.0
    elif sec <= HOOK_WINDOW_SEC + 1.0:
        props["length"] = 0.5
        notes.append(f"takes about {sec:.1f}s to say; the hook window is {HOOK_WINDOW_SEC:g}s")
    else:
        props["length"] = 0.0
        notes.append(f"takes about {sec:.1f}s to say, well past the {HOOK_WINDOW_SEC:g}s hook window. Split it: the claim first, the detail in the next sentence")

    concrete = _concrete_positions(tokens)
    props["specificity"] = 0.0 if not concrete else (0.6 if len(concrete) == 1 else 1.0)
    if not concrete:
        notes.append("nothing concrete (no figure, date or name)")

    stakes = [w for w in re.findall(r"[a-z']+", lower) if w in STAKES_WORDS]
    props["stakes"] = 0.0 if not stakes else (0.6 if len(stakes) == 1 else 1.0)
    if not stakes:
        notes.append("no stake (nothing lost, gained, broken or at risk)")

    marks = sorted(set(concrete) | {i for i, t in enumerate(tokens) if t.strip(".,'’").lower() in STAKES_WORDS})
    if not marks:
        props["frontload"] = 0.0
    elif marks[0] <= 3:
        props["frontload"] = 1.0
    elif marks[0] <= 7:
        props["frontload"] = 0.6
        notes.append(f"first concrete or high-stakes word arrives at word {marks[0] + 1}; lead with it")
    else:
        props["frontload"] = 0.2
        notes.append(f"the payload arrives at word {marks[0] + 1}; the viewer has decided by then")

    tension = [p for p in TENSION_PATTERNS if re.search(p, lower)]
    props["tension"] = 1.0 if tension else 0.0
    if not tension:
        notes.append("no tension (no question, contrast or unknown)")

    total = sum(WEIGHTS[k] * v for k, v in props.items())
    capped: Optional[str] = None
    for pat, label in PREAMBLE_PATTERNS:
        if re.search(pat, lower):
            capped = label
            total = min(total, PREAMBLE_CAP)
            notes.insert(0, f"{label}: cut it, start at the sentence you would reach at second six")
            break
    total = int(round(total))
    verdict = "STRONG" if total >= 70 else "OK" if total >= 50 else "WEAK"
    return {
        "text": line, "score": total, "verdict": verdict, "spoken_sec": round(sec, 1), "words": len(tokens),
        "points": {k: round(WEIGHTS[k] * v, 1) for k, v in props.items()}, "capped_by": capped, "notes": notes,
        "formula": classify(line),
    }


# --------------------------------------------------------------------------- formulas
def load_formulas() -> List[Dict[str, Any]]:
    return json.loads(FORMULAS_PATH.read_text(encoding="utf-8"))["formulas"]


def classify(text: str) -> Optional[str]:
    """Best-fitting formula id by its `signals` patterns, or None. A suggestion, not a label to trust."""
    low = text.lower()
    best, best_hits = None, 0
    for f in load_formulas():
        hits = sum(1 for p in f.get("signals", []) if re.search(p, low))
        if hits > best_hits:
            best, best_hits = f["id"], hits
    return best


def formulas_for(category: Optional[str] = None) -> List[Dict[str, Any]]:
    fs = load_formulas()
    if category:
        fs = [f for f in fs if category in f.get("best_for", []) or not f.get("best_for")]
    return fs


def rank(lines: List[str], wps: float = DEFAULT_WPS) -> List[Dict[str, Any]]:
    results = [score_hook(t, wps) for t in lines if t.strip()]
    return sorted(results, key=lambda r: -r["score"])


def check_formulas(data: Dict[str, Any]) -> List[str]:
    """Structural problems in specs/hook-formulas.json (used by the tests)."""
    errs: List[str] = []
    seen = set()
    for f in data.get("formulas", []):
        fid = f.get("id", "?")
        if fid in seen:
            errs.append(f"duplicate formula id {fid}")
        seen.add(fid)
        for key in ("id", "name", "template", "example", "fails_when"):
            if not f.get(key):
                errs.append(f"{fid}: missing {key}")
        for p in f.get("signals", []):
            try:
                re.compile(p)
            except re.error as exc:
                errs.append(f"{fid}: bad signal pattern {p!r}: {exc}")
    return errs
