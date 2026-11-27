---
name: mid-form
description: Playbook for a mid-form Motion Lab film (video_type mid, 60-180 s, portrait for Instagram or landscape for YouTube and LinkedIn): the focused explainer on one concept, process, event or question, Hook -> Context -> Explanation -> Visual demonstration -> Conclusion. Use when briefing, scripting, pacing, editing or reviewing a film of one to three minutes.
version: 0.1.0
---

# Mid-form: focused explainers

One concept, process, event or question explained in real depth, without becoming a documentary. Spec: `specs/video-types.json` (`mid`). Words: `.claude/skills/story-writer/SKILL.md`. **Uncalibrated:** the numbers here are a first guess; no film has been finished under this form yet, so record what the review finds in `docs/video-forms.md`.

## Shape
- **Structure:** Hook -> Context -> Explanation -> Visual demonstration -> Conclusion. Arc `explainer-demonstration` (default); `hook-payoff` and `problem-mechanism-consequence` also fit.
- **Length:** about 150 s target, 60-180 s. Under 90 s it is closer to a short; over 180 s it is a long-form film or a cut.
- **Budget:** one mechanism plus one worked case, or two linked mechanisms and no worked case; about six new terms. A named case costs 25 s of setup.
- **Words:** about 2.9 words a second, so 150 s is about 400 words.

## The demonstration is the point
Explanation tells; the demonstration runs it: a simulation, a worked example with real numbers, a before/after, an animated sequence, a diagram that builds. It must show something the explanation could not and is the beat a viewer shares. If the mechanism cannot be shown running, the film is a short or a long-form chapter, not mid-form.

## Pace and editing
- Re-hook about every 35-45 s in portrait, 45-60 s in landscape: a stake, a contradiction or a question the next step answers.
- More detailed diagrams, supporting evidence on screen with its source, and animated sequences than a short; slower reveals (a step lands, holds a beat, then develops). Still a visual change every 2-4 s; never narration over a static frame.
- **Pick the format in the brief:** portrait for Instagram (phrase captions, 4 words), landscape for YouTube or LinkedIn (sentence captions, two lines). One format per film (`docs/VISION.md`).
- Close on the hook's own words and at most one late ask.
- Reference evidence (`docs/reference-playbook.md`): 40-55 s demos and explainers in the corpus give each step or section about 6 s, change in place on one stage rather than cutting, and breathe on the empty stage for 0.07-0.4 s at a section turn (`empty-stage-dip`). A photo-led brand explainer gives sections 6-13 s and turns chapters with a 0.4 s side push that alternates light and dark sections (`section-push-slide`, `ref-c6d0aa55f6`). A light product demo can tour one canvas with a camera instead of cutting (4 moves of 0.6-1.0 s and 2-5 s holds in 30 s; `canvas-camera-tour`, `ref-ad023ce9dc`). Narration pace from references: 1 narrated reference among 64 inspected (2026-11-27), a 60 s app explainer whose pauses median 0.50 s (max 1.12 s) and whose copy changes only in those pauses; its words per second is only a band (1.35-3.65), so the pace rules here are unchanged.

## Gates
As short-form, plus `studio.py validate` checks the form's window and budget. Renders in one pass up to 180 s.
