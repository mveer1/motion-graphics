# Story lessons

Append-only log for the `story-writer` retro mode (`../SKILL.md` section 6). Each entry: date, film, observation, evidence, proposed rule, status (`open` or `promoted -> <where>`). Evidence is a measurement or a quoted review score, never an impression alone.

## Seeded from earlier reviews (2026-11-02 to 2026-11-05)

### L1. Storyboards planned too few visual beats
- **Films:** cloud-physical-infrastructure-india, fridge-hack-europe, south-korea-data-center-fire.
- **Observation:** every scene of all three storyboards planned one visual event every 3 to 7 s.
- **Evidence:** `style check` beat-gap failure in every scene; after render, `motion-qa` found 41 s (of 70), 44 s (of 92) and 79 s (of 98) of static or low-energy stretches (`docs/style-templates.md`, calibration).
- **Rule:** plan beats at or under `max_beat_gap_sec`, scene tails included.
- **Status:** promoted -> checklist 11.

### L2. Closing scenes go empty
- **Film:** polya-recurrence.
- **Observation:** a 5.5 s near-empty stretch opened the closing scene while narration played.
- **Evidence:** blackdetect 62.4-67.9 s on the first render.
- **Rule:** scene tails, closing and quote scenes especially, need planned beats.
- **Status:** promoted -> checklist 11 (tails) and 16.

### L3. Hook and closing scenes run over the word budget
- **Films:** cloud (s1 36, s6 35 words per 10 s against 33), fridge (s2 32.5).
- **Evidence:** `voice-director` item 8, measured clips.
- **Rule:** they are written last, so budget per scene and write the hook first.
- **Status:** promoted -> process 3.3 and 3.5, checklist 10.

### L4. The value lands late, or never
- **Films:** fridge (core message first in scene 3), cloud (scene 6).
- **Evidence:** `studio.py script` on 2026-11-05. None of the three had a `why` on any scene.
- **Status:** promoted -> checklist 5 and 7.

### L5. Slow, dense openings
- **Films:** Korea, which opens on one 9.8 s sentence (date, place, event and agency together); cloud, whose hook scores 20/100 (nothing concrete, no stake).
- **Evidence:** `docs/short-form-lessons.md`.
- **Status:** promoted -> checklist 4.

### L6. Cards too long
- **Films:** over 6 words in cloud 2 of 35 on-screen items, fridge 3 of 27, Korea 9 of 51.
- **Status:** promoted -> process 3.6, checklist 4.

### L7. Endings fade instead of landing
- **Film:** cloud, whose final moment is 19.1 LU below the body (bed ramped to 0 over the last 4 s). Korea's thud and ring-out on a live bed was the only launch-grade ending of the three.
- **Rule:** the story side is checklist 14 and 16; the mix side belongs to `video-assembler`.
- **Status:** promoted -> checklist 14 and 16.

### L8. `reel-loop` untested
- **Observation:** no film has been made to the `reel-loop` arc yet, so whether the loop line helps replays is unknown.
- **Next step:** record it in the first retro of a film that uses it.
- **Status:** open.

## Open experiments from third-party guidance (2026-11-06)

Source: `docs/social-media-skills-lessons.md`. These conflict with a rule we hold, and none is backed by our own data, so each stays an experiment until a test of the kind described in SKILL.md section 6 settles it.

### L9. Reel length: 45 s sits between two claimed sweet spots
- **Claim:** Shorts performance is "bimodal": under 30 s gets higher completion, 50-60 s gets more total views (`youtube-shorts`). TikTok virality is said to sit at about 7-34 s (`tiktok-script`).
- **Ours:** 45 s preferred, up to 60 s for a complicated topic (the user's decision, 2026-11-06).
- **Test:** the same film cut at about 30 s and about 45 s, once analytics exist.
- **Status:** open.

### L10. Caption chunk size
- **Claim:** 4-7 word chunks (`short-form-video-script`), or two lines of 32-42 characters (`youtube-shorts`).
- **Ours:** 1-3 word phrases with the spoken word highlighted.
- **Test:** keep 1-3 words for portrait. Try two-line subtitles on the first landscape long-form film.
- **Status:** open.

### L11. Beat spacing in Shorts
- **Claim:** a new visual or information beat every 1-2 s, with no establishing shots (`youtube-shorts`).
- **Ours:** every 2-3 s; template `max_beat_gap_sec` 2.0-2.5.
- **Test:** one portrait film at 1.5 s, the experiment already proposed in `docs/short-form-lessons.md`.
- **Status:** open.
