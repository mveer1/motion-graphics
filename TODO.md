# TODO

Open decisions and follow-ups. Delete an item when it is done; record the outcome in the relevant spec or doc.

## Decide

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

## Follow up

- [ ] Decide whether categories should drive defaults (suggested narrative arc, suggested style) or stay tags only. Proposed: the style template drives defaults (style, scene grammar, pacing) and categories stay hints that feed `style recommend`; nothing is applied automatically.
- [ ] Decide how a series is rendered or published as a unit (shared intro/outro, cross-part recap, naming of `out/` files). Today `series.json` only records membership and checks consistency.
- [ ] Decide whether to build a JEV.
- [ ] Analyse and refine the reference material (run through `reference-analyst`; keep observation separate from interpretation).
- [ ] Style templates, next steps (see [docs/style-templates.md](docs/style-templates.md) "Honest limits"):
  - Backfill `style_template` on the nine studio projects (`style check` shows a suggestion for each; cloud-physical-infrastructure-india is a genuine close call between `systems-blueprint` and `news-brief`).
  - Make `motion-qa` read the project's template: waive the caption band, and set the label floor and static-hold limit from `rules`.
  - Build a light scientific "plate" style for `science-atlas` (sci-viz and cinematic-dark are both dark).
  - Calibrate the rule values (`proof-canvas` words per 10 s is the clearest guess) from the first films made to each template; merge `data-ledger` and `news-brief` if they stay indistinguishable in paint.
  - Require storyboard `beats` (film time) so the gap rule can run before the first render.
- [ ] From the 2026-11-03 review of cloud-physical-infrastructure-india, south-korea-data-center-fire and fridge-hack-europe (see `motion-graphics-designer` §1.E):
  - Promote the helpers each film re-implements (typed kicker, caption band, stamp, tile grid, counter roll, per-scene drift) into `src/studio/`; all three hand-code 620–730 lines and use only `Studio.build`.
  - Add a pre-render gap audit (visual event times vs `audio/timeline.json`, flag gaps over 2 s), either in `studio.py validate` or as a script. Static-hold is only caught after the render today. Partly done 2026-11-05: `studio.py script` flags sentences of 3 s or more with no storyboard beat; the film-time audit of the composition's own tweens is still open (`tween-probe.mjs` now dumps them).
  - `motion-qa`: waive `low-contrast` and `text-echoes-narration` automatically for a declared caption band (rgba pills read as 1.0:1), and make `static-hold` account for how much of the frame changes.
  - Score `qa/creative-review.json` for south-korea-data-center-fire and fridge-hack-europe, and run `earshot critique` without `--fast` on all three (realness and music presence were not measured).
  - Decide whether the studio mux should write stereo (all three mixes are mono; earshot flags stereo width) and whether cloud's ending should be re-cut with `scene-revise.py`-style splice for the audio only.
- [ ] From the 2026-11-05 short-form adoption (see [docs/short-form-lessons.md](docs/short-form-lessons.md)):
  - Add a `why` to every storyboard scene; all existing films warn `why-missing`. Nothing was backfilled.
  - Confirm cloud's `tween-conflict` in the rendered frames (one `<g>` group: entrance `scale` 0.35-1.4 s against a pulse `scale` from 1.15 s) and split it onto a wrapper if it shows.
  - Rework Korea's 9.8 s opening sentence and cloud's 20/100 hook; both are film-specific, not template problems.
  - Make the first film to the `reel-loop` arc (portrait, 15-45 s). It is the only way to calibrate the hook scorer, the 6-word card limit and the loop check; promote or retire them after that.
  - Run `studio.py captions --timing words --grouping phrase` on a real film at its next build and look at the highlighted word in the caption band (runtime 1.1.0; only films that use `Studio.comp.captions` get it: none of the current ones do, cloud draws its own band).
  - Re-render the portfolio after the 2026-11-05 upgrade (runtime 1.1.0, portrait `safe_area.bottom` 0.234): every studio project's render moved to `renders/history/` (25 renders in 22 projects, counting `weight-space-programming`), and the 17 delivered files that existed moved to `out/archive/`. `studio.py renders` lists what is missing; build one at a time, newest films first. Bottom text the films place themselves (cloud's captions at 78.3 %, Korea and fridge source lines near 80 %) did not move with the margin; lift it per film if it should clear the reel interface.
  - Motion-variety thresholds are calibrated on three films; revisit once more are scanned. Confirm `tween-transform-overlap` (from()/transform overlap hiding an element) on this runtime or drop it.

## DONE

- [x] 2026-11-05: Closed the three session worktrees (cloud, Korea, weight-space-programming). Brought `projects/weight-space-programming/` (new film, untracked in its worktree), cloud's and Korea's QA snapshots and the build-timing log lines into main; the worktrees' renders and `out/` files were byte-identical to the copies already in `renders/history/`, and their tooling files were older copies of main's. Deleted the merged `session/*` branches (including a leftover `session/bhopal-gas-tragedy`) and committed all pending work.
- [x] 2026-11-05: Upgrades are no longer held back by stale videos. Portrait `safe_area.bottom` moved to 0.234 (top and right unchanged), runtime 1.1.0 highlights the spoken word in word-timed captions, `studio.py upgrade --all` re-synced all 22 studio projects, and `build`/`upgrade`/`renders --archive` move superseded renders to `renders/history/` instead of overwriting them. Also fixed: `studio.py` restarted itself part-way through a command when the catalogue import re-executed into python3.12.
- [x] 2026-11-03: Backfilled `categories`: every studio project's `brief.json` carries them and `studio.py validate` raises no missing-category warning. Legacy projects have no `brief.json`, so the rule does not apply to them.
- [x] 2026-11-03: Assessed `cjpais/Handy` (https://github.com/cjpais/Handy), a Rust/Tauri offline speech-to-text dictation app (MIT, v0.10.0 released 2026-11-02, ~37k stars, active, signed release assets, downloads models from Hugging Face and checks GitHub for updates). **Verdict: do not adopt for the pipeline.** It is dictation (voice in, text out); the studio goes text to Kokoro speech, and transcription already comes from `earshot` and `reference-corpus.py`. Optional personal use for dictating briefs, outside the repo. Not installed or run; memory use on the 8 GB host not measured.
- [x] 2026-11-03: Created the `agy` (Antigravity) delegation skill at `.claude/skills/agy/` (`SKILL.md`, `scripts/agy-ask.sh`), registered as `catalogue/data/skills/agy.json`; the delegation policy is in `CLAUDE.md`.
- [x] 2026-11-03: Evaluated and onboarded part of `Panniantong/Agent-Reach` (https://github.com/Panniantong/Agent-Reach), a read-only CLI for searching and reading web platforms. **Verdict: adopt `web`, `github` and `youtube` as a Stage 0 research fallback; `reddit`, `instagram` and `linkedin` were added on request the same day (see below).** Safe? Mostly (MIT, installed from the official release zip not PyPI, read-only; but the `web` channel sends queries to Jina and Exa, the release is unsigned, and the login-copying channels are excluded). Efficient? Yes for those three (0.5 to 6 s per call, no browser, checked live); browser channels would collide with the one-heavy-job rule on 8 GB. Helpful? Moderately (fills gaps WebFetch leaves: clean page text, repo and issue threads, YouTube captions). Value? A little, near-zero cost. It was already installed on 2026-10-30 (v1.6.0, user level). Follow-up on request: removed Bilibili and V2EX (and `bili-cli`); updated to 1.6.1 (needed because Chrome PID 42556 holds port 9222, so the browser port was set to 9333); rebuilt the browser with `browser setup --retry-cloak` after the update left a stale path; added Reddit, Instagram and LinkedIn. Live results: Reddit search works without login (titles and snippets), Reddit post read gets a block page, Instagram and LinkedIn need a login that only the user can do (`agent-reach login <channel>`; not done, not verified). Browser stopped afterwards. Not added: X, Facebook, Xiaohongshu, Boss, Xueqiu, Xiaoyuzhou. Registered as `catalogue/data/integrations/agent-reach.json` (`experimental`); pointer added to `technical-researcher`. Full write-up: [docs/agent-reach-assessment.md](docs/agent-reach-assessment.md).
- [x] 2026-11-03: Assessed `h4ckf0r0day/obscura` (headless agent browser, https://github.com/h4ckf0r0day/obscura). **Verdict: do not adopt.** Safe? Moderate (Apache-2.0 Rust, SSRF defaults, but young, unaudited, unauthenticated CDP by default, unsigned artifacts, off-mission stealth features). Efficient? Unknown (30 MB vs 200+ MB is a vendor claim; an independent review measured 5.2 s vs 2.1 s median on live pages). Helpful? No (render, frame-review, dom-probe, reference decode and collage all need Chromium fidelity). Value? Little (only a markdown research capture that WebFetch and agent-reach already cover). Not installed or run; decided not to adopt.
