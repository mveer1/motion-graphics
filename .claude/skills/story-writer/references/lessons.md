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

## From the owner's review of game-theory-trust (2026-11-07)

Source: the project owner watched the finished 46 s reel (`renders/portrait/final.mp4`, iteration 2 story) and ruled that each point below applies to **every future film**. `qa/creative-review.json` is still unscored, so the evidence is the owner's words, quoted, plus measurements from the film's own files. These four entries are promoted by owner ruling, not by the recurrence rule (SKILL.md section 6 now allows that, with the ruling quoted).

### L12. A hook that is intriguing but ambiguous
- **Film:** game-theory-trust.
- **Observation:** the hook "Nobody made a mistake. Both lost one year." named no one and gave a number with no unit. "Both" first got a referent at 6.8 s ("Two suspects", spoken). "Year" got its unit only on screen, at 10.0 s ("Years in prison: fewer is better"). The narration never says "prison" except inside the name "prisoner's dilemma".
- **Evidence:** owner: "the hook line is good but is not well placed. it says: 'both lost one year, so would you'. its hard to understand what year are we talking about. So for technical videos lets not put confusing hook lines. It should always be clear." The same line scored 100/100 on `studio.py hook score` and 8/8 on our rubric (`qa/story-review.json` iteration 2), so neither check can see ambiguity.
- **Rule:** a third hook gate, *Clear*: read cold, every noun, number and unit in the spoken hook and the card has its referent inside the line ("an extra year in prison", not "one year"). An ambiguous hook fails, whatever it scores.
- **Status:** promoted -> SKILL.md 3.3 and checklist 19 and 28; `specs/hook-formulas.json` note and `fails_when` of `nobody-did`, `number-collapse` and `chain-of-small-steps`. A lint for bare pronouns and unit-less numbers is a TODO (`TODO.md`).

### L13. Two mechanisms and a named tournament squeezed into a 46 s reel
- **Film:** game-theory-trust.
- **Observation:** the reel carried two mechanisms (one-round dominance; repeated-game reciprocity) and about six new terms or names (prisoner's dilemma, Robert Axelrod, a computer tournament and its entries, tit for tat, "copies your last move"). The tournament got 11.0 s (s5, 26.8-37.8 s, 28 words) for who, when, how many and who won. Nothing said how it was scored, how many rounds were played, who the rivals were or why tit for tat won.
- **Evidence:** owner: "in this video you are explaining a complex tournament summarized into 45s. That won't work. We can't compress complicated content into a short video." Iteration 2 had already filed two open research requests on that scene (r1, r2) as non-blocking and shipped.
- **Rule:** a scope check before writing. Count mechanisms and new terms against the type's budget (a reel: one mechanism, about three new terms). A named study, event, tournament or algorithm needs its setup (who, what, how it was scored, what happened, why: about 25 s or more), so it is never a reel's closing beat or re-hook. Over budget: cut, split into a series, or promote the type.
- **Status:** promoted -> SKILL.md 3.1 and checklist 27; `specs/video-types.json` `complexity_budget`; `specs/narrative-arcs.json` `reel-loop` pitfall. This film: Axelrod and tit for tat cut, kept as a part 2 idea (`docs/project-ideas.md`).

### L14. The visuals stayed empty where the narration skipped
- **Film:** game-theory-trust.
- **Observation:** s5 showed a ring of 15 chips, 14 of them anonymous, then a ranked column whose labels faded out "because the research gives only the winner's rank", a "1st" badge, the bare label "the simplest entry" and a faded second column (frames `qa/final/f-30.8.png`, `f-35.7.png`). The iteration-2 review accepted the unlabelled ring and column, and filed "'The simplest entry' is now a bare label" as a non-blocking request (r2).
- **Evidence:** owner: "we talked about the tournament but we only said 'the simplest entry' that leaves out a gap in knowledge, which leaves the user uncomfortable. lets at least add proper information in the visuals even if narration doesn't talk about it, instead of leaving the visuals empty."
- **Rule:** list every term, name, number and result that is spoken or shown, and where the viewer gets its explanation. When narration cannot afford it, the storyboard beats put it on screen (one-line definition, legend, rule written out, source line, table cells as plain sentences). No anonymous drawn object. A research gap behind a name already in the film blocks, or the name is cut: it never ships as a bare label.
- **Status:** promoted -> SKILL.md 3.6 and 3.8 and checklist 29; `specs/storyboard-spec.json` `on_screen_text` description. Already in `proof-canvas` v2 (anti-pattern) and `motion-graphics-designer` section G (main session, same day).

### L15. One speed for every scene
- **Film:** game-theory-trust.
- **Observation:** every scene ran at the film speed (am_adam 1.05). Measured clip rates were 2.67-3.08 words per second, and the payoff s4 ("Both do it: two years each, not one") was the fastest scene of the film (3.08 words per second, 31 words per 10 s) while it carried the key result. Nothing in the plan said where to slow down or speed up.
- **Evidence:** owner: "the system also needs to understand where to slow down and where to pick up the pace in a video." `audio/timeline.json` of the iteration-2 build.
- **Rule:** a pace map. Each scene is slow (the turn, the proof, a new concept, a key number: about 0.90-0.95, fewer words, a beat of silence after the payoff), normal (context: the film speed) or fast (recap, transitions, loop line: about 1.10-1.15, no new term or number). It is written as `pace` on each storyboard scene and `speed` on each `src/narration.json` scene, and the word budget follows the pace.
- **Status:** promoted -> SKILL.md 3.5 and 3.6 and checklist 30; `specs/storyboard-spec.json` `pace`. Per-scene `speed` is supported by `src/pipeline/narration.py` and `scripts/build-audio.py` (main session, same day). `style check` does not read `pace` yet (TODO).

### L16. Words per 10 s may misread a monosyllabic script
- **Film:** game-theory-trust (iteration 2).
- **Observation:** measured 28.0 words per 10 s against proof-canvas's 27, but 3.76 syllables per second, close to the calmest film (south-korea-data-center-fire, 3.55). Five scenes were waived on that evidence.
- **Evidence:** `qa/story-review.json` iteration 2, waiver on rule 10.
- **Next step:** compare with the creative review's `pacing` score once it is scored, and with the next proof-canvas film. Propose a syllable-rate check beside the word cap only if a second film agrees.
- **Status:** open.

### L17. A role word in the plan was read as an on-screen seat
- **Film:** game-theory-trust (iteration 2).
- **Observation:** the plan used "partner" for tit for tat's opponent while the narration called the viewer "you". The composition labelled the rows literally and inverted the rule: on screen, tit for tat copied "them" while the voice said "copies your last move".
- **Evidence:** `qa/story-review.json` iteration 2, `composition_deviations.unlisted_row_inversion` (frame at 39.3 s).
- **Rule:** when the narration addresses the viewer as "you", name the on-screen seats in `visual_concept` and keep each label to one meaning for the whole film.
- **Status:** open (one film). L8 (`reel-loop` untested) also stays open: this was the first `reel-loop` film, and no analytics exist.
