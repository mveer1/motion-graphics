---
name: short-form
description: Playbook for a short-form Motion Lab film (video_type short, 20-60 s, portrait, Instagram Reels and YouTube Shorts): the micro explainer with one idea, Hook -> Explanation -> Payoff. Use when briefing, scripting, pacing, editing or reviewing a film under about a minute. Subject knowledge comes from the category and style template, not from here.
version: 0.1.0
---

# Short-form: micro explainers

One interesting idea, fact, discovery or insight, told fast and dense, with one satisfying takeaway. Spec: `specs/video-types.json` (`short`). Rulebook for the words: `.claude/skills/story-writer/SKILL.md` (the short-form rules were calibrated on `game-theory-trust`, cloud, Korea and fridge). Lessons: `docs/short-form-lessons.md`, `docs/caption-design.md`.

## Shape
- **Structure:** Hook -> Explanation -> Payoff. Arc `reel-loop` (default); `hook-payoff` or `problem-mechanism-consequence` when the topic needs the room.
- **Length:** 45 s preferred. 20-35 s is one fact or number with no named case. 45-60 s only for a complicated topic that needs more animated beats, not more words.
- **Budget:** one mechanism, about three new terms. A named study, event or algorithm is the film's whole subject or it is out.
- **Words:** about 2.9 words a second, so 45 s is about 130 words. Every sentence grabs, advances or sets up the payoff.

## Pace and editing
- The hook lands in the first 3 s, the hero object already on screen and the hook card up on frame 1. No greeting, title or logo.
- A visual change every 2-3 s; kinetic type, hard cuts and striking transitions are right here. A mid-film re-hook near 35 s once the film passes about 35 s.
- Captions: phrase cues of one to three words, mid lane in the hook window, lower lane in the body (`caption-designer`).
- Portrait 720x1280, safe area from `specs/format-presets.json`. Style: any registered style template; `editorial-light` by default.
- Reference evidence (`docs/reference-playbook.md`): 15-20 s reels in the corpus hold shots for a median 1.8-2.8 s, cut word sections every 0.23-0.75 s on the beat, and spend their 2-4 big transitions (flash, bloom, zoom-through) on the turns. A portrait reference keeps its hook line fixed in the top band for the whole film. A one-verb-per-card list runs at 1.00 s per card with the proof (a UI action) about half a second into each card (`ref-b4e79aa0a4` 0.97-9.98 s); a portrait list can build a line every 0.5-1.0 s on the beat with the earlier lines dimmed (`dim-previous-line-stack`, `ref-32fea7dae3`).

## Gates (all existing)
`studio.py validate`, `studio.py script`, `frame-review.py`, `studio.py build`, `studio.py review`. Renders in one pass. When the same idea has a longer treatment, this film is its own cut-down with its own hook and payoff, never a trimmed copy.
