---
name: long-form
description: Playbook for a long-form Motion Lab film (video_type long, 5-12 minutes, landscape, YouTube): the documentary or deep dive on a complex subject, event, discovery or paper, told in chapters, Cold open -> Context -> Narrative development -> Deep explanation -> Resolution. Use when briefing, scripting, pacing, editing, rendering or reviewing a film over about five minutes.
version: 0.1.0
---

# Long-form: documentaries and deep dives

Narrative-driven films that earn their length through storytelling, depth, accuracy and an immersive picture. Spec: `specs/video-types.json` (`long`); guide: `docs/video-forms.md`. Words: `.claude/skills/story-writer/SKILL.md` (arc `documentary-chapters`). **Uncalibrated:** the structure and timings are a first guess; no film has been finished under this form yet. The render path was verified on a 22 s film in segments, not on 12 minutes.

## Shape
- **Structure:** cold open -> context -> narrative development -> deep explanation -> resolution. Arc `documentary-chapters` (or `documentary-investigation`, `chronological`, `question-investigation-revelation`).
- **Length:** 480 s target, 300-720 s. Words: about 2.9 a second, so 8 minutes is about 1,400 words and 12 minutes about 2,100. Scripts are written chapter by chapter, never as one block.
- **Chapters are the unit of everything.** `storyboard.json` `chapters`: contiguous, 45-150 s, each starting and ending on a scene edge, each with a descriptive `title` (it becomes the YouTube chapter label), one `mechanism`, its `new_terms` (at most three) and a `rehook` into the next. `studio.py validate` checks them. Film budget: about 25 new terms and eight mechanisms in all.
- **Re-hook every 60-90 s.** Every chapter ends on a turn, a setback or a question the next one picks up. A chapter that could be cut without the viewer noticing is cut.
- **Cold open (30-60 s)** shows the question, scene or result the film exists to answer. The resolution pays it off in its own words and ends on the strongest image, held.

## The picture
- Cinematic animation, 2D/3D visualisation, maps, data stories, elaborate transitions: the capability catalogue and the `chronicle`, `science-atlas`, `data-ledger` and `systems-blueprint` style templates are the toolkit. Stamp dates and places on the picture; give the viewer a map or timeline as an anchor.
- No explanation stretch over 90 s without a change of mode (image, data, scene, voice). Variety across chapters (different hero object, camera move, layout) so minute 7 does not look like minute 2; the Anti-Laziness mandate holds throughout.
- Sound design carries more here: a bed that changes between chapters, tactile micro-sounds on data, silence used on purpose. No whooshes on educational dissolves.
- Captions are a reading aid: sentence cues, two lines, quiet and consistent.

## Production on one 8 GB machine
- **Author per chapter.** One `src/index.html` for 12 minutes is too large for a session to hold. Write one scene or chapter at a time, build and review it, then continue; `studio.py words` snaps beats to measured speech.
- **Narration** re-synthesises only changed scenes (`build-audio.py`); keep the script in chapters so an edit re-times one chapter.
- **Render:** `studio.py build` renders films over 180 s in segments of about 90 s (`scripts/render-segments.py`), cut at scene edges, with a checkpoint after each. An interrupted build resumes at the first unfinished segment. Any edit to `src/` discards the segments (the whole composition is the fingerprint). Revise a finished film's single scene with `scene-revise.py`.
- **Review:** `frame-review.py` scales its samples and scan rate to the length; read the contact sheet chapter by chapter. Creative review scores the whole film plus a pace pass per chapter.
- **Cut-downs:** the film's strongest single insight becomes a short-form film of its own, in a series (`studio.py series add`, mixed forms are fine). A long-form film is never re-rendered at 9:16.
