# Video forms: short, mid and long

Motion Lab makes three forms of video. A brief declares one (`deliverables.video_type`), `studio.py new --type` requires it, and `studio.py validate` holds the project to it. The numbers live in `specs/video-types.json`; this page is the guide. Each form has its own playbook skill for storytelling, scripting, pacing and editing; subject knowledge (history, technology, science, finance, ...) comes from the brief's categories and the style template, not from the form.

| | Short-form | Mid-form | Long-form |
|---|---|---|---|
| Id | `short` | `mid` | `long` |
| What | Micro explainer: one idea, fact or insight | Focused explainer: one concept, process, event or question | Documentary or deep dive: a complex subject told in chapters |
| Length | 20-60 s (45 preferred) | 60-180 s (150 target) | 5-12 min (8 target) |
| Allowed (+-15 s) | 15-75 s | 60-195 s | 285-735 s |
| Format | portrait | portrait or landscape | landscape |
| Platforms | Instagram Reels, YouTube Shorts | Instagram, YouTube, LinkedIn | YouTube |
| Structure | Hook, Explanation, Payoff | Hook, Context, Explanation, Visual demonstration, Conclusion | Cold open, Context, Narrative development, Deep explanation, Resolution |
| Arc | `reel-loop` | `explainer-demonstration` | `documentary-chapters` |
| Re-hook | one near 35 s | every 35-45 s (portrait), 45-60 s (landscape) | every 60-90 s, one per chapter |
| Budget | 1 mechanism, ~3 new terms | 1 mechanism + 1 worked case (or 2 linked), ~6 terms | 1 mechanism and ~3 terms per chapter; ~8 mechanisms, ~25 terms in all |
| Playbook | `.claude/skills/short-form` | `.claude/skills/mid-form` | `.claude/skills/long-form` |
| Render | one pass | one pass | segments of ~90 s, resumable |

195-285 s belongs to no form on purpose: cut it to mid-form or build it out to long-form. A series may mix forms (a long-form film with short-form cut-downs); each cut-down is its own film with its own hook and payoff. Only one format is rendered per film (`docs/VISION.md`).

## Old ids

Before 2026-11-08 the three types were `reel` (45-60 s), `long-reel` (60-180 s, portrait) and `youtube` (over 180 s, landscape). They still work everywhere as aliases (`reel` = `short`, `long-reel` = `mid`, `youtube` = `long`) and `validate` notes the rename. The one real difference: a legacy `youtube` film of 3-5 minutes has no form now and must be re-typed (cut to mid, or build out to long). No existing project is in that case: `weight-space-programming` (240 s, portrait) has no `video_type` and is not checked against a window.

## What a long-form film needs that a short one does not

- **Chapters** (`storyboard.json` `chapters`): contiguous, 45-150 s, on scene edges, each with a descriptive title (the YouTube chapter label), one `mechanism`, at most three `new_terms` and a `rehook`. `validate` checks them and the film-wide budget.
- **Segmented render.** Above 180 s `studio.py build` calls `scripts/render-segments.py` instead of a single `hyperframes render`. It renders segments of about 90 s (`hyperframes render --start --end`, a fresh Chrome per segment, cut at a scene edge when one is near), keeps each finished segment in `renders/<format>/chunks/`, resumes after a killed build, joins them by stream copy and checks the frame count. Any edit under `src/` discards the segments, because the fingerprint covers the whole composition. Single scenes of a finished film are revised with `scene-revise.py`.
- **Length-aware review.** `frame-review.py` samples one frame per 20 s (up to 60) and scans at 2 then 1 frame a second over 3 and 7 minutes.
- **Authoring per chapter.** One `src/index.html` for 12 minutes is more than a session can hold in view; write, build and review chapter by chapter (see the `long-form` skill).

## What is verified, and what is not

Verified on the M2 host on 2026-11-08: a 22 s film rendered in three 8 s segments joins to exactly 660 frames, matches a single-pass render (PSNR 43 dB or better on every frame, no change at the cuts), and a build killed after the first segment resumes by skipping it. Pure-Python checks for the form windows, aliases, chapters and the segment planner are in `tests/test-video-forms.py`.

Not verified, because no such film exists yet:
- a 5-12 minute film through `studio.py build` (memory, time and disk over 21,600 frames; `segment_sec` is a guess to adjust from `logs/build-timings.jsonl`);
- the timings in the `documentary-chapters` and `explainer-demonstration` arcs, the mid-form and long-form complexity budgets, and the caption defaults for them;
- Kokoro and Whisper on 1,400-2,100 words in one project (they work per scene, so this should hold, but it has not been run);
- the mux of a long narration with a background bed shorter than the film (the bed is not looped).

Build the first mid-form and long-form films as pilots, run `studio.py review`, and write what the review finds back into the playbook skills and `specs/video-types.json`.
