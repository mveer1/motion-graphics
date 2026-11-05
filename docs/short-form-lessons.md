# Short-form and motion craft lessons (adopted 2026-11-05)

On 2026-11-03 the public repos of Jake Schincariol (`github.com/Jakeschincariol`) were read for anything useful to video, motion graphics and reel generation. This note records what was adopted into this workspace, where it lives, what it measured on our own films, and what was left out. Nothing was copied: every module here is original code written from the published ideas.

## What was adopted

| Lesson | Source | Where it lives now | Status |
|---|---|---|---|
| Pre-render script lint: timed beat sheet, hook window, abstract runs, loop, one ask | `instagram-agent-skill` `ig-reel` (MIT) | `src/pipeline/scriptlint.py`, `studio.py script`, warnings in `studio.py validate` | Working; timings come from measured Kokoro clips, not a words-per-minute guess |
| Reel shape: hook 0-2 s, stake, body, payoff, a closing line that echoes the hook | `ig-reel` | New arc `reel-loop` in `specs/narrative-arcs.json`; `rules.short_form.closing` in `news-brief` and `storybook` | Unused so far; no film has been made to it |
| One ask, no greeting or "in this video", cards of 6 words or fewer | `ig-reel` | `scriptlint` (`hook-preamble`, `filler-frame`, `many-asks`); `news-brief` v2 and `storybook` v2 anti-patterns and `rules.short_form.max_card_words` | Checked before render |
| Hook craft: write three from three formulas, score, choose | `ig-reel`, `youtube-agent-skill` (MIT) | `specs/hook-formulas.json` (12 formulas, original wording), `src/pipeline/hooks.py`, `studio.py hook score\|formulas`; step 2b in `creative-director` | A lint, not a predictor (see limits) |
| Value first: the claim lands by scene 2, delete-test, a `why` per scene, props traced to the subject | HeyGen `hyperframes-creative` `story-spine.md` (Apache-2.0) | Optional `why` field in `specs/storyboard-spec.json`; story table and `value-late` / `why-missing` leads in `studio.py script`; step 2c in `creative-director`; `arc` criterion text in the creative review | The delete-test is a judgment prompt; only the table and the lexical lead are automated |
| Motion variety: vary eases, speeds and entrance directions; `.out` to enter, `.in` to leave; enter slower than you exit; do not start on the cut | HeyGen `motion-principles.md` | `scripts/tween-probe.mjs` + `src/pipeline/tweens.py`, run by `motion-qa.py composition\|project`; rules in `motion-graphics-designer` section F | Measured leads, thresholds uncalibrated |
| Overlapping tweens on one element | `motion-principles.md` | `tween-conflict` (warn) and `tween-transform-overlap` (note) | The conflict check found a real overlap in cloud (below) |
| Data in motion: no pie or dual-axis, 3 metrics at most, no legend, a visual beside every number, one space per concept | `data-in-motion.md` | `data-ledger` v2 (four anti-patterns, faint gridlines at labelled values only) | Unrendered; v2 stays `experimental` |
| Connector-line test: name start, end and job or cut it | `motion-principles.md` | Judgment prompt in the `motion-qa` critique pack, rule in `motion-director` | Prompt only |
| Word-timed captions: 1-3 word phrases, no weak ending, grow a quick phrase | `master-skills` `/edit` `captions.py` (MIT) | `src/pipeline/captions.py`, `studio.py captions --timing words --grouping phrase`, `audio/words.json`, `studio.py words` | Tested on one clip (fridge s1, 95% matched); the full-film run has not been done. Since runtime 1.1.0 each cue keeps its word times and `Studio.comp.captions` lights the spoken word (`--c-caption-hl`, default `--c-accent-3`); checked in the runtime self-test page, not yet in a render |
| Show the noun on the word | `/edit` house rules | `studio.py words <slug> "<phrase>"` gives the frame; rule in `voice-director` and `motion-graphics-designer` | Manual: the author snaps a beat to the frame |
| Reel interface margins | `/edit`, `ig-reel` | `platform_ui_reference` in `specs/format-presets.json` (portrait) and a `platform-ui-zone` note in `motion-qa` | Bottom adopted: portrait `safe_area.bottom` is 0.234 since 2026-11-05 (was 0.20); top and right stay at the workspace defaults |

The portrait `safe_area` is now top 10 %, bottom 23.4 %, right 10 %. Only the bottom follows the reference (top 12 %, bottom 23.4 %, right 12 % below 52 % of the height): the reference comes from third-party guidance that disagrees with itself on the right margin (130 px in one repo, 230 px in the other), and is not published by any platform, so top and right stay notes. The first version of this note kept the bottom at 20 % because the change would make every portrait render stale; that is no longer a reason to hold an upgrade back. `studio.py upgrade --all` applied it, moved the superseded renders to `renders/history/`, and every project validates. Re-running `motion-qa composition` on cloud, Korea and fridge afterwards found no new collision, off-frame, contrast or size finding. Their own bottom text (cloud's captions at 78.3 %, source lines near 80 %) is placed by film CSS, not by `--safe-bottom`, so it did not move.

## What it measured on our films

Run on 2026-11-05 against `cloud-physical-infrastructure-india`, `south-korea-data-center-fire` and `fridge-hack-europe` (nothing in the films was changed).

- **Script lint.** Korea opens on one 9.8 s sentence (date, place, event and agency together); the window is about 3 s. Cloud's hook scores 20/100 (nothing concrete, no stake). All three lack a `why` on every scene. Fridge's core message first appears in scene 3, cloud's in scene 6.
- **Card length.** Over 6 words: cloud 2 of 35 on-screen items, fridge 3 of 27, Korea 9 of 51.
- **Tween conflict.** Cloud has a real one: a `<g>` group enters on `scale` from 0.35 to 1.4 s (`back.out(1.7)`) while a pulse tween on the same `scale` starts at 1.15 s. A second pair of `scaleY` tweens overlaps at 10.8 to 11.1 s. Not yet confirmed in the rendered frames.
- **Variety.** Nothing fired except a note on Korea s3 (3 of 4 entrance recipes on `power1.out`). Entrance medians were 0.35 to 0.5 s, with 5 to 8 distinct eases per film. These films are not template-uniform by these thresholds.
- **Interface bands.** Cloud's captions end at 78.3 % of the height against the 76.6 % reference line; four right-hand labels reach 93.8 % against 88 %.
- **Calibration choice.** The first overlap threshold (0.03 s) flagged fridge for a fade-out that starts 0.05 s before a fade-in ends. That is a hand-off, so the threshold is 0.12 s (four frames).

## Deliberately not adopted

- **Shot length.** "No shot over 1.5 s, median under 1 s" is for talking-head footage. Our rule (a visual change every 2 to 3 s under speech) stands. Portrait shorts could test 1.5 to 2.5 s; nothing has.
- **Glows, ghost type and 2 to 5 decoratives per scene** (HeyGen house style) against **no glows, sheens or pulse rings** (reel guidance). The two disagree. `editorial-light` follows the second; neither is imposed.
- **`deadspace.py`, stop-motion and stock SFX/LUTs.** Live-action editing is a non-goal; real-sfx and Earshot cover sound.
- **`media-use` providers, HeyGen cloud rendering, publishing and growth skills.** They break the no-cloud rule or are out of scope.
- **`arena-skill` (100 sub-agents) and `promptmaster`.** Token-heavy or irrelevant to the pipeline.

## Limits that matter

- `hookscore`'s author reports AUC 0.83 for real versus deliberately bad hooks and 0.56 for one creator's hits versus misses. Ours is a rewrite with different word lists and weights and has not been calibrated against our films; a high score means no obvious defect, nothing more. Short curiosity questions ("Why does ice float?") score low because the lint rewards concrete figures and stakes.
- Word-timed captions use `hyperframes transcribe` (local Whisper `small.en`) per scene clip. Digits and respellings are handled by aligning to the script text; the command prints the match per scene and warns under 80 %. Phrase captions render through the existing caption band, and since runtime 1.1.0 the band highlights the spoken word. No current film uses `Studio.comp.captions` (cloud draws its own band), so no render shows it yet.
- The `why` field is optional. Nothing fails without it; `studio.py validate` prints a warning for each project that lacks it. No existing storyboard was edited.
- Style template changes (`data-ledger` v2, `news-brief` v2, `storybook` v2) are unrendered. No project is pinned to a template yet, so `style check` shows none behind.
- `ruff` is not installed in the workspace venv; the new files were checked with `uvx ruff` (clean). `studio.py` and `motion-qa.py` carry the same pre-existing findings as before.

## Attribution

- Jake Schincariol, `instagram-agent-skill`, `youtube-agent-skill`, `master-skills`: MIT (each repo has a LICENSE). Ideas adopted: beat sheet, five hook properties, hook formula library, caption phrase rules, reel structure. No code or data files were copied.
- HeyGen `hyperframes` skills (Apache-2.0 upstream), read through Schincariol's `video-production-skills` repository, which has no licence file of its own: story spine, motion principles, data in motion. Only the rules were restated; no text, code or assets were copied. If more is wanted, take it from `github.com/heygen-com/hyperframes` instead.
- `talking-head-recut` is adapted from `notedit/vtake-skills` (MIT) and was not used.
