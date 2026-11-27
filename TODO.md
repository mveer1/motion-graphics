# TODO

Open decisions and follow-ups. Delete an item when it is done; record the outcome in the relevant spec or doc.

## Decide

- [ ] **Blender plates on the M2 render host** (`docs/visual-engines.md`, adopted 2026-11-24 as experimental, verified on Windows only). Run `python scripts/visual-director.py install-blender`, render one plate per template under the host lock, measure peak memory and seconds per frame for EEVEE and Cycles on Metal, and build one film with a plate before promoting `tool-blender` and `shared-blender-plate-kit`. Also decide: an open-licensed asset source for Blender (HDRIs, textures), and for math briefs whether to vendor an equation typesetter (MathJax SVG or KaTeX) before considering Manim (`tool-manim`, proposed).
- [ ] **Confirm the definition of a "visual style".** Proposed in [docs/style-templates.md](docs/style-templates.md): a style *system* is paint (tokens and CSS), a *design profile* is DNA, and a new **style template** is the decision unit that binds both and adds scene grammar, measurable pacing rules, anti-patterns and a versioned revision log. A brief's creative direction is one film's choice inside the template. Built and tested (7 templates, `studio.py style ...`, 30 tests) but all `experimental` and uncalibrated. Open: who may add a template, and what evidence promotes one (proposed: two films made to it, rendered on the render host, passing `qa/creative-review.json`).
- [ ] **Review the initial category tags on styles.** They are a first guess from each style's `suitable_for` text. Revisit once the style definition above is settled. Current tags:
  - abstract-geometric: mathematics, technology
  - archival: history, news
  - cinematic-dark: storytelling
  - dark-tech: technology
  - data-journalism: finance, news
  - mixed-media: storytelling
  - paper-cut: storytelling
  - sci-viz: science, technology
  - editorial-light, swiss-minimal: untagged (general-purpose, fit any category)
- [ ] **Approve (or not) the figure-authoring libraries.** Evaluated 2026-11-24 in [.claude/skills/mythic-figure-designer/references/tooling.md](.claude/skills/mythic-figure-designer/references/tooling.md), nothing installed:
  - authoring-time geometry: Paper.js 0.17.0, paperjs-offset 2.2.2, bezier-js 6.1.4 and svgpath 2.6.0, all MIT;
  - GSAP 3.13 for MorphSVG view swaps, under a proprietary no-charge licence that needs sign-off;
  - Blender with MPFB2 for turnaround references;
  - whether to try local AI reference stills on the 8 GB Mac (FLUX.1 schnell is marginal; SD 1.5 is the realistic option).
- [ ] **Review the heroic mythic figures** (`projects/_mythic-figures/figures-human*.png`, `armoury.png`). Artistic licence taken for heroism needs sign-off:
  - Athena's raised spear, her shield and her radiant aura;
  - Odin's storm aura and glowing eye;
  - Hanuman's gada on the shoulder;
  - Rama's default blue skin.

  The next step after approval is the three-quarter, profile and back views (`figure-design.md` section 5).

## Follow up

- [ ] Pilot the source-linked Yellow Dude adaptations in the next suitable
  Sinew film (fitness skill 2.1, Body Lab v2; guide
  `.claude/skills/fitness/references/yellow-dude-study.md`). Record whether the
  rough animatic, matched comparison, claim/drawing trace and original cover
  communicate the intended distinction. No retention benefit is established.
  Full reference-video/audio analysis still needs permitted local media;
  web/still observations and publisher-reported process are not substitutes.

- [ ] From the 2026-11-19 Windows Tibi takeover: choose the cross-medium direction
  before changing the approved 2D look. The local decision pack is
  `prompts/state/design-direction.md` (copy with the handoff folder). Confirm
  common proportion landmarks and the line-ending policy.
  The owner's 2026-11-20 full-body request is implemented in runtime 1.10.0:
  integrated lats, shoulder caps, chest/abdominal/limb forms, corrected
  brachialis, morph normals, bounded activation colour, torso-owned top and
  window-local cutaways. `distance` is now the development default;
  explicit `legacy` retains the old body. The approved 2D art is unchanged.
  The owner rejected the remaining shoulder/arm fit: 1.11.0 now replaces
  the exposed joint orb/flat arm root, rounds the tapered deltoid fans and
  exposes the new neutral stance through `fig.defaultPose`. The authored
  motion fallback remains `T3.DEFAULT_POSE`. New matched geometry/stance
  PNGs and controls are in `prompts/state/shoulder-arm-refinement/`.
  See `docs/fitness-studio.md` section 9 and the matched design PNGs under
  `prompts/state/full-body-review/`. Rerun the 0.4.0 benches, 20-case seek
  suite per profile and separate cutaway-locality gate on the Mac, then
  rebuild the actual fitness films sequentially.
  Zero boundary edges is now required; three male / four female non-manifold
  edges remain under the unchanged tolerance, so do not claim a strictly
  manifold surface. Exact tissue/scapular mechanics, extreme-pose contact,
  exercise equipment framing, wardrobe redesign, cross-medium art direction
  and human G3 approval remain separate follow-ups.
- [ ] Decide whether categories should drive defaults (suggested narrative arc, suggested style) or stay tags only. Proposed: the style template drives defaults (style, scene grammar, pacing) and categories stay hints that feed `style recommend`; nothing is applied automatically.
- [ ] Decide how a series is rendered or published as a unit (shared intro/outro, cross-part recap, naming of `out/` files). Today `series.json` only records membership and checks consistency.
- [ ] Decide whether to build a JEV.
- [ ] Analyse and refine the reference material (run through `reference-analyst`; keep observation separate from interpretation).
- [ ] Style templates, next steps (see [docs/style-templates.md](docs/style-templates.md) "Honest limits"):
  - Backfill `style_template` on the nine studio projects (`style check` shows a suggestion for each; cloud-physical-infrastructure-india is a genuine close call between `systems-blueprint` and `news-brief`).
  - Build a light scientific "plate" style for `science-atlas` (sci-viz and cinematic-dark are both dark).
  - Calibrate the rule values (`proof-canvas` words per 10 s is the clearest guess) from the first films made to each template; merge `data-ledger` and `news-brief` if they stay indistinguishable in paint.
  - Require storyboard `beats` (film time) so the gap rule can run before the first render.
- [ ] From the 2026-11-03 review of cloud-physical-infrastructure-india, south-korea-data-center-fire and fridge-hack-europe (see `motion-graphics-designer` §1.E):
  - Promote the helpers each film re-implements (typed kicker, caption band, stamp, tile grid, counter roll, per-scene drift) into `src/studio/`; all three hand-code 620–730 lines and use only `Studio.build`.
  - Score `qa/creative-review.json` for south-korea-data-center-fire and fridge-hack-europe, and run `earshot critique` without `--fast` on all three (realness and music presence were not measured).
  - Decide whether the studio mux should write stereo (all three mixes are mono; earshot flags stereo width) and whether cloud's ending should be re-cut with `scene-revise.py`-style splice for the audio only.
- [ ] From the 2026-11-05 short-form adoption (see [docs/short-form-lessons.md](docs/short-form-lessons.md)):
  - Add a `why` to every storyboard scene; all existing films warn `why-missing`. Nothing was backfilled.
  - Confirm cloud's `tween-conflict` in the rendered frames (one `<g>` group: entrance `scale` 0.35-1.4 s against a pulse `scale` from 1.15 s) and split it onto a wrapper if it shows.
  - Rework Korea's 9.8 s opening sentence and cloud's 20/100 hook; both are film-specific, not template problems.
  - Make the first film to the `reel-loop` arc (portrait, 15-45 s). It is the only way to calibrate the hook scorer, the 6-word card limit and the loop check; promote or retire them after that.
  - Run `studio.py captions --timing words --grouping phrase` on a real film at its next build and look at the highlighted word in the caption band (runtime 1.1.0; only films that use `Studio.comp.captions` get it: none of the current ones do, cloud draws its own band).
  - Re-render the portfolio after the 2026-11-05 upgrades (runtime 1.1.0, then 1.2.0 with vendored GSAP; portrait `safe_area.bottom` 0.234): every studio project's render moved to `renders/history/` (25 renders in 22 projects, counting `weight-space-programming`), and the 17 delivered files that existed moved to `out/archive/`. `studio.py renders` lists what is missing; build one at a time, newest films first. Bottom text the films place themselves (cloud's captions at 78.3 %, Korea and fridge source lines near 80 %) did not move with the margin; lift it per film if it should clear the reel interface.
  - Motion-variety thresholds are calibrated on three films; revisit once more are scanned. Confirm `tween-transform-overlap` (from()/transform overlap hiding an element) on this runtime or drop it.

- [ ] From the 2026-11-06 four-phase lifecycle and `social-media-skills` adoption (see [docs/social-media-skills-lessons.md](docs/social-media-skills-lessons.md)):
  - Run the `story-writer` on its first real film (`write <slug>`). It is `experimental` until one film has gone through all four phases with it. No existing film has `qa/story-review.json`, so `studio.py validate` warns on every one; nothing was backfilled.
  - Decide where publishing metadata lives: title, description (value line first, search phrase in lines 2-3), chapters, tags, the not-professional-advice line, CC BY music attribution, `madeForKids`. Proposed: `out/<slug>-publish.md`, written at the end of phase 4 from `qa/story-review.json` `packaging`. Never re-post an identical file: platforms suppress unoriginal re-uploads, so a re-run changes one variable.
  - Decide the AI-content disclosure. The narration is synthetic Kokoro speech. EU AI Act transparency obligations apply from August 2026, and YouTube and TikTok have synthetic-content labels. Proposed: a standing line in every description, plus the platform toggle where the platform asks for one. This needs a human (or legal) decision; the story-writer only records it per film.
  - Decide how a long film's reel is produced. The pipeline renders one composition in every format, so a 3-minute landscape explainer's portrait version is 3 minutes long. The story-writer now proposes the reel as its own film in a series `collection`; confirm that, or build a cut-down path.
  - Decide on an analytics source. The retro mode's analytics table and test rules need retention, swipe-away and share numbers from published films; nothing in the workspace reads them yet.
  - Settle the three open experiments (story-writer `lessons.md` L9-L11): reel length 30 s against 45 s, caption chunk size, and 1.5 s beat spacing in Shorts.

- [ ] From the owner's review of game-theory-trust (2026-11-07; story-writer rulebook 1.2.0, `lessons.md` L12-L15). The rules are in the rulebook. These are the tooling gaps the story-writer could not close, because they sit outside its files (hook clarity, pace budgets, speed-aware estimates and the named_things check were done 2026-11-23, see DONE):
  - `voice-director` skill: record that the per-scene pace map and `speed` numbers come from the story-writer (rulebook 1.2.0 section 1), and that voice-director tunes inside a band, never across it.

- [ ] From the 2026-11-08 Sinew fitness build (`.claude/skills/fitness/`, `projects/how-muscles-grow`):
  - Trademark search for "Sinew" and "Tibi" (classes 41 and 9) before any commercial publish.
  - Listen to `out/how-muscles-grow-landscape.mp4` on a phone and on speakers (audio reviewed by Earshot only); owner review of the brand and mascot.
  - Run the `story-writer` subagent's `review how-muscles-grow` (the sign-off was written by the main session applying the rulebook).
  - Calibrate the `body-lab` rules and the fitness rubric thresholds after three films; promote the kit and skill from `experimental` then.
  - Kit gaps: phoneme lip-sync (not wanted now). Done 2026-11-23 (sculpt kit 2.2.0, `prompts/state/p05/2d-report.md`): vascular tree, alveolus gas exchange, knee/hip/shoulder joint sections, front-view squat (reads parallel-ish: fixed paint order), a rebuilt leg-press setup.
  - Decide whether a 3D anatomy path (Blender plus BodyParts3D, share-alike handled) is worth adding (`references/production.md`). Blender itself is now in the stack as an experimental plate engine (2026-11-24, `docs/visual-engines.md`); this item is only about anatomy meshes and their licence.
  - First short-form Sinew film (portrait) to check Tibi's scale and caption lanes in 9:16.

- [ ] From the 2026-11-09 Tibi Cobalt Sculpt integration and the upper-body workout film (`projects/upper-body-workout`, guide `.claude/skills/fitness/references/character-guidelines.md`):
  - Done on the owner's rulings: classic Tibi retired (`tibi.js` deleted, `how-muscles-grow` ported, logo icon and thumbnail redrawn); back-view squat and running, prone and supine poses from above, finger joints, fist and grip hands, a two-piece shoe, curved straps and more back-muscle detail added; the movement library rebuilt for the new figure (12 upper-body exercises).
  - Faces, expressions and lip-sync are not required now (owner, 2026-11-09). Other next steps the owner can pick: a contact-sheet script; a Lottie/Rive export. Done 2026-11-23 in 2D (sculpt kit 2.2.0): barbell and machine lifts (back squat, deadlift, bench press, leg press, cable pulldown). Not feasible in 2D without a per-pose paint order: a back-view push-up. Waiting on the owner: the prepared dead-code removal and rounding-fix patches (`prompts/state/p05/2d-decisions.md`); the 2D kit 2.2.0 was released with runtime 1.15.0 (2026-11-25).
  - Re-render `how-muscles-grow` (ported to the new Tibi, its old render is in `renders/history/`); its opening was built around the old x-ray reveal (narration s2: "let's look inside Tibi's arm"); the port lights the biceps by activation instead, so check the hook and the zoom into the arm in a snapshot before re-rendering.
  - Done 2026-11-24/25 (runtime 1.15.0): the upper-body film's patterns are in `src/studio/studio-film.js` (word-snapped cues `Studio.cues.fromWords`, kicker, caption plate, stations) and `kits/fitness/stations.js` (exercise card, fitness bands: portrait rail 340, floor 870, caption lane 882-980; `K.captionLane`, `K.audit`), the `fitness-explainer` template and body-lab v3. Open: the fixed-state frames were reviewed on Windows only; square format and the 3D station path are untested.
  - Portrait long-form is allowed by the owner (2026-11-09; `specs/video-types.json` `formats_note`); decide whether `long-form` skill defaults and the segment planner need a portrait default.
  - Human listen to the film's audio (Y-raise, lats, delts, rear-delt pronunciations were judged by recogniser match only) and a trademark check for "Sinew" and "Tibi" before any publish.
  - Handover dead code kept until the owner confirms (handover section 13): curly hair, `chest_bralette`, face style B, the legacy before/after panels in `page6.py` (`build_v1.py`, `rig_v1.py`, `v3_defs.txt`), unused data keys.
  - Generator quirk mirrored on purpose: `build2.figure()` rounds segment scales to one decimal, so the female leg art is drawn unscaled (0.965 -> 1) and hands at 1.1, not 1.15. Fixing it would change the approved look; ask before changing.
  - PNG exports (`src/fitness/tibi/export_assets.py`) and the generator's own browser checks need Playwright, absent on this host; the handover PNGs were not copied (24 MB), only the contact sheets.

## DONE

- [x] 2026-11-23: Studio-tooling backlog, prompt 06 items 2-8 (report `prompts/state/p06/report.md`). All new lints are warnings or notes, uncalibrated until a film is rendered with them on the Mac. (2) Film-time gap audit: `tweens.narration_gaps` + `scriptlint.gap_findings` read the tween dump `qa/motion/tweens.json` (written by `studio.py script --probe` or `motion-qa`) against `audio/timeline.json`; `visual-gap` warns in `script` and `validate` (docs/short-form-lessons.md). (3) `motion-qa` reads the pinned style template: static-hold limit (`rules.static_hold_sec`, else `max_beat_gap_sec`), label floor (`rules.label_floor_fraction`), caption band (`rules.caption_band`, runtime `st-caption`, storyboard `caption-band` lanes) waives `low-contrast` and `text-echoes-narration`; static-hold notes a stretch where only part of the frame changes (docs/style-templates.md). (4) Hook clarity notes (`hooks.clarity_notes`, `hook-unclear`), never scored. (5) `style check` pace budgets (slow 0.9x, fast 1.1x). (6) Speed-aware estimates and "audio is stale" in the sentence sheet, `beatmap.py storyboard` and `style check`. (7) NAMED THINGS table and `named-unexplained` / `named-not-listed` in `studio.py script`. (8) `studio.py build` exports `packaging.cover` to `out/<slug>-<format>-cover.png` (story-writer skill step 7); first real run queued in `prompts/state/p06/render-queue-additions.md`.
- [x] 2026-11-07: Caption design added to the flow (runtime 1.3.0, all 23 studio projects upgraded): `specs/caption-presets.json` (five presets, style map, lanes, roles), `studio.py captions` picks the preset and writes a role, lane and emphasised numbers per cue, `studio.py new` turns captions on and wires `Studio.comp.captions` into the template, `validate` lints the cues, storyboard scenes take `caption_lane`, `caption-designer` skill and `docs/caption-design.md`. Open: render one film with captions end to end and look at it on a phone; confirm Montserrat 800 and Nunito 800 are bundled weights; decide whether a long reel really wants four-word phrases; see `open_questions` in the spec.

- [x] 2026-11-06: Lifecycle regrouped into four phases with gates (`AGENTS.md` section 1, `ARCHITECTURE.md` 0.1, `CLAUDE.md`): brief and research, story and structure, then audio, visuals and sound as one sequential loop (not parallel: visuals are timed to measured speech and the heavy steps share the host lock), then render and review. New `story-writer` subagent and rulebook (`.claude/agents/story-writer.md`, `.claude/skills/story-writer/`) own the story and sign off in `qa/story-review.json`; `studio.py validate` warns when the sign-off is missing, not complete, or stale. `research.json` `scene_blueprint` is deprecated (optional; dropped from the templates). Reel length: 45 s preferred, up to 60 s only for a complicated topic. Adopted rules from `social-media-skills` (MIT) into the rulebook (v1.1.0) and `data-ledger` (v3).

- [x] 2026-11-05: Architecture review (findings 8, 11–16 in [docs/architecture-audit.md](docs/architecture-audit.md)). Narration is fingerprinted against `audio/timeline.json` and re-made per changed scene, and the build stops when new narration moves scene timing. Renders write a partial file first. `scene-revise.py` keeps its splice. `validate` errors when speech outruns `duration_sec`. **Decided:** GSAP is vendored (runtime 1.2.0, all 23 studio projects upgraded; fonts unchanged). Smart prosody is opt-in per project (`audio.prosody: "smart"`); raw stays the default. Open: run one smart-prosody narration on real Kokoro (tested with a stand-in only).

- [x] 2026-11-05: Closed the three session worktrees (cloud, Korea, weight-space-programming). Brought `projects/weight-space-programming/` (new film, untracked in its worktree), cloud's and Korea's QA snapshots and the build-timing log lines into main; the worktrees' renders and `out/` files were byte-identical to the copies already in `renders/history/`, and their tooling files were older copies of main's. Deleted the merged `session/*` branches (including a leftover `session/bhopal-gas-tragedy`) and committed all pending work.
- [x] 2026-11-05: Upgrades are no longer held back by stale videos. Portrait `safe_area.bottom` moved to 0.234 (top and right unchanged), runtime 1.1.0 highlights the spoken word in word-timed captions, `studio.py upgrade --all` re-synced all 22 studio projects, and `build`/`upgrade`/`renders --archive` move superseded renders to `renders/history/` instead of overwriting them. Also fixed: `studio.py` restarted itself part-way through a command when the catalogue import re-executed into python3.12.
- [x] 2026-11-03: Backfilled `categories`: every studio project's `brief.json` carries them and `studio.py validate` raises no missing-category warning. Legacy projects have no `brief.json`, so the rule does not apply to them.
- [x] 2026-11-03: Assessed `cjpais/Handy` (<https://github.com/cjpais/Handy>), a Rust/Tauri offline speech-to-text dictation app (MIT, v0.10.0 released 2026-11-02, ~37k stars, active, signed release assets, downloads models from Hugging Face and checks GitHub for updates). **Verdict: do not adopt for the pipeline.** It is dictation (voice in, text out); the studio goes text to Kokoro speech, and transcription already comes from `earshot` and `reference-corpus.py`. Optional personal use for dictating briefs, outside the repo. Not installed or run; memory use on the 8 GB host not measured.
- [x] 2026-11-03: Created the `agy` (Antigravity) delegation skill at `.claude/skills/agy/` (`SKILL.md`, `scripts/agy-ask.sh`), registered as `catalogue/data/skills/agy.json`; the delegation policy is in `CLAUDE.md`.
- [x] 2026-11-03: Evaluated and onboarded part of `Panniantong/Agent-Reach` (<https://github.com/Panniantong/Agent-Reach>), a read-only CLI for searching and reading web platforms. **Verdict: adopt `web`, `github` and `youtube` as a Stage 0 research fallback; `reddit`, `instagram` and `linkedin` were added on request the same day (see below).** Safe? Mostly (MIT, installed from the official release zip not PyPI, read-only; but the `web` channel sends queries to Jina and Exa, the release is unsigned, and the login-copying channels are excluded). Efficient? Yes for those three (0.5 to 6 s per call, no browser, checked live); browser channels would collide with the one-heavy-job rule on 8 GB. Helpful? Moderately (fills gaps WebFetch leaves: clean page text, repo and issue threads, YouTube captions). Value? A little, near-zero cost. It was already installed on 2026-10-30 (v1.6.0, user level). Follow-up on request: removed Bilibili and V2EX (and `bili-cli`); updated to 1.6.1 (needed because Chrome PID 42556 holds port 9222, so the browser port was set to 9333); rebuilt the browser with `browser setup --retry-cloak` after the update left a stale path; added Reddit, Instagram and LinkedIn. Live results: Reddit search works without login (titles and snippets), Reddit post read gets a block page, Instagram and LinkedIn need a login that only the user can do (`agent-reach login <channel>`; not done, not verified). Browser stopped afterwards. Not added: X, Facebook, Xiaohongshu, Boss, Xueqiu, Xiaoyuzhou. Registered as `catalogue/data/integrations/agent-reach.json` (`experimental`); pointer added to `technical-researcher`. Full write-up: [docs/agent-reach-assessment.md](docs/agent-reach-assessment.md).
- [x] 2026-11-03: Assessed `h4ckf0r0day/obscura` (headless agent browser, <https://github.com/h4ckf0r0day/obscura>). **Verdict: do not adopt.** Safe? Moderate (Apache-2.0 Rust, SSRF defaults, but young, unaudited, unauthenticated CDP by default, unsigned artifacts, off-mission stealth features). Efficient? Unknown (30 MB vs 200+ MB is a vendor claim; an independent review measured 5.2 s vs 2.1 s median on live pages). Helpful? No (render, frame-review, dom-probe, reference decode and collage all need Chromium fidelity). Value? Little (only a markdown research capture that WebFetch and agent-reach already cover). Not installed or run; decided not to adopt.
