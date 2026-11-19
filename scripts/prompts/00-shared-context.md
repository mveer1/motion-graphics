# 00 · Shared context for every prompt in this folder

Read this file first, whichever prompt you were given. The numbered prompts assume you know everything here and do not repeat it.

Written 2026-11-19 on the Mac render host. The facts below describe the repository on that date. Verify them before you rely on them, because the code moves faster than this note.

---

## 1. Who you are working for and what they value

The owner runs **Motion Lab**, a local motion-graphics studio that makes narrated explainers: short (20-60 s, portrait), mid (60-180 s) and long (5-12 min) films. **Sinew** is its fitness-education brand ("See what your body is doing."), and **Tibi** is Sinew's mascot. Tibi is a cobalt-skinned athletic body (male and female) with a marigold flame "spark" on the head, white shoes and charcoal shorts with a marigold waistband. Working muscles light up on the skin by role.

Things the owner has said, ruled or shown repeatedly. Treat them as standing orders:

- **Premium visual craft and accurate explanation are equally important.** Neither is traded for the other. Speed of shipping is not a priority, and render time is never a reason to cut quality.
- **Honesty over optimism.** Never claim a render, a loudness figure, a test pass or a visual result you did not produce on the machine you are on. Say what you did not check. The owner distrusts automated checks that were never validated against the real defect: "the tests catch geometry; only a human catches ugly". **Look at the frames.**
- **Fix the system, not the one video.** A recurring visual problem gets fixed in the kit, the style template or the generator (versioned), not patched in a single composition.
- **Upgrades never wait on stale videos.** Make the runtime change, bump `Studio.version`, run `studio.py upgrade --all`, and re-render what needs it later, one job at a time.
- **Refine Tibi, do not replace him** (ADR-2 in `docs/fitness-studio.md`). The silhouette, palette and spark are the brand. The 3D failure was the anatomy, not the character.
- **Automation can fail a gate but never approves accuracy.** Gates G1 (science) and G3 (anatomy and biomechanics) need a named human in `qa/fitness-signoff.json`. Never write that file.
- **Git holds the tool only.** No projects, `out/`, `series/` or prompt files go in git, and there is no fixture exception. Never `git add -f` into an ignored folder. Commit only when the owner asks, on a branch, never straight to `main`. Pushing needs the owner's explicit go-ahead.
- **Record progress as you go**, not at the end: `TODO.md` for open decisions, the relevant doc or spec for outcomes, `catalogue/project-progress.md` for project status, and `prompts/state/` for your own working log (section 6).
- Clear, plain English in everything you write: docs, labels, commit messages and reports. Explain jargon the first time you use it.

## 2. Read before you touch anything

In this order. Skim what doesn't apply to your prompt, but don't skip the first five.

1. `CLAUDE.md`: commands, hard constraints and architecture. Also read `AGENTS.md` (hard production rules) and `ARCHITECTURE.md` section 0.
2. `docs/VISION.md`: the business goals and the non-goals (no cloud rendering, no live action, no voice actors).
3. `docs/fitness-studio.md`: the Sinew architecture map, the audit, ADR-1..9 and an honest "not done" list.
4. `.claude/skills/fitness/SKILL.md` (the orchestrator), then `fitness-anatomy`, `fitness-animation`, `fitness-qa` and `fitness-publish` in `.claude/skills/`.
5. `.claude/skills/fitness/references/motion-3d.md`: 3D motion rules 1-18, the rig's units and pose keys, determinism, tools, measured lab results and known limits. **Each rule is a defect that was actually seen.**
6. `assets/fitness/STYLE.md`: the visual language (one meaning per colour), type, camera language, motion principles.
7. `.claude/skills/fitness/references/character-guidelines.md` and `src/fitness/tibi/HANDOVER.md`: the 2D Cobalt Sculpt character, its generator and its baselines.
8. `TODO.md`: the open decisions and follow-ups for the whole workspace.

## 3. The two Tibis: a map

| | 2D Tibi ("Cobalt Sculpt") | 3D Tibi (one-skin, runtime 1.9.0) |
|---|---|---|
| Master source | `src/fitness/tibi/` (Python, stdlib only): `rig.py`, `rig_f.py`, `rig_back.py`, `rig_ext.py`, `build2.py` | `src/studio/kits/fitness/anatomy3d.js` (skin, muscle table, windows), `tibi3d.js` (rig, stage, motion, bind), `exercises3d.js`, `film3d.js`, `scenes3d.js` |
| Runtime | `src/studio/kits/fitness/sculpt.js` + `sculpt-data.js` (**generated** by `python scripts/fitness.py sculpt`, never hand-edit) | Three.js r158, vendored at `src/studio/vendor/three.min.js` (classic global build, never a CDN) |
| Look | flat cobalt planes, crescent light and shade planes, no outlines | toon shading in four bands; muscles are SDF ellipsoid volumes smooth-unioned into one skin |
| Review surface | `assets/fitness/tibi/site/tibi_cobalt_sculpt_v6.html`, `assets/fitness/tibi/svg/`, `sheets/` | `assets/fitness/lab3d/still.html`, `assets/fitness/lab3d/anatomy-bench.html`, `qa/anatomy3d/`, `qa/rig3d/` |
| Checks | `page6.py` byte-identical rebuild, `verify3.py` (needs Playwright), `fitness.py sculpt --check` | `node scripts/anatomy3d-check.js`, `node scripts/rig3d-check.js`, `python tests/test-anatomy3d.py`, `tests/test-rig3d.py`, `tests/test-fitness.py` |
| Look tools | `export_assets.py`, `lab.py`/`lab4.py` crops | `scripts/anatomy3d-bench.py`, `scripts/rig3d-stills.py` (headless Chrome + SwiftShader) |
| Knowledge | `assets/fitness/data/exercises.json`, `muscles.json`; schema `specs/fitness-exercise-spec.json`; `fitness.py check` audits every 3D highlight against it | same |

Every composition must stay deterministic: one paused GSAP timeline registered through `Studio.build`; no `Math.random`, wall-clock time, timers or `requestAnimationFrame`; 3D is driven by `T3.bind` (one linear tween whose property setter poses the rig, because HyperFrames' seek suppresses GSAP callbacks). The project copy `projects/<slug>/src/_studio/` is never edited. Change `src/studio/`, bump `Studio.version` in `src/studio/studio-core.js`, then `studio.py upgrade --all`.

## 3a. Design of record: where to pick the design from

Start from these files. Everything else is a copy, a preview or a record of an earlier decision.

| Question | Pick the design from | Read-only copies (do not edit these) |
|---|---|---|
| The 2D Tibi (shape, proportions, colours, poses, faces, clothing) | the generator `src/fitness/tibi/` (`build2.py` with `rig.py`, `rig_f.py`, `rig_back.py`, `rig_ext.py`). Its runtime painter is `src/studio/kits/fitness/sculpt.js` with `sculpt-data.js`, which is generated from the master by `python scripts/fitness.py sculpt` | `assets/fitness/tibi/svg/`, `assets/fitness/tibi/sheets/`, `assets/fitness/previews/tibi-sculpt-*.png`, `assets/fitness/tibi/site/tibi_cobalt_sculpt_v6.html` (the review page; rebuild it with `python3.12 src/fitness/tibi/page6.py` and check it against the baseline in `HANDOVER.md` §0) |
| The 3D Tibi (the body, muscles, cutaways, colour language) | `src/studio/kits/fitness/anatomy3d.js` (skin and muscle table), then `tibi3d.js`, `exercises3d.js`, `film3d.js`, `scenes3d.js` | `qa/anatomy3d/`, `qa/rig3d/`, `qa/regression/lab-3d-compare/` (tracked stills and a comparison project); `assets/fitness/lab3d/*.html` are benches, not designs |
| Rules for the look (palette, type, camera, one meaning per colour) | `assets/fitness/STYLE.md`, `.claude/skills/fitness/references/character-guidelines.md` | none |
| Why a decision was made | `docs/fitness-studio.md` (ADR-1 to ADR-9), `src/fitness/tibi/HANDOVER.md` (historical, 2D) | none |

**Rules that follow from this table:**

1. If a PNG, SVG or preview disagrees with the master source, the master wins. Fix the master, then regenerate the copy.
2. `HANDOVER.md` was written in a cloud workspace. Its paths under `/home/claude/out/` do not exist on your machine. Replace them with the repo paths in the table above, and read its numbers as a baseline, not as a live spec.
3. Not in git, so not available unless the owner copies them: the handover's full PNG set (about 24 MB), `projects/` (the reference 3D films `lab-3d-motion`, `knees-past-toes`, `hip-thrust-vs-squat`, `standing-vs-seated-calf`, plus `upper-body-workout` and `how-muscles-grow`) and `out/`. If you need one of these to judge the 3D look, say so and work from `qa/` meanwhile. Never recreate a film from memory.
4. The Playwright-based exports and `verify3.py` need Playwright, which may not exist on Windows. Check first; do not regenerate PNGs from a different renderer and call them the design.

## 4. The Windows machine: what it can and cannot do

The owner is handing design work to a **Windows** machine. **Kokoro (the TTS) is not installed there.** Whatever else is or isn't present (HyperFrames, FFmpeg, Chrome, Playwright, Node, Python 3.12, Blender, a GPU) is **unknown until you probe it**. `CLAUDE.md` says non-Mac hosts lack HyperFrames, FFmpeg and Kokoro. That was true for an earlier Windows host. Check this one yourself.

**Known portability hazards** found by reading the code (verify each one, then fix what blocks you):

- `scripts/session-guard.py` imports `fcntl`, which does not exist on Windows. Heavy-job locking breaks. A portable lock (for example `msvcrt.locking`, or an `O_CREAT|O_EXCL` lock file with stale-PID recovery) must keep working unchanged on macOS.
- `scripts/anatomy3d-bench.py` and `scripts/rig3d-stills.py` find Chrome at `~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell` (no `.exe`) and build `file://{ROOT}/...` URLs by string. Both are wrong on Windows (use `Path.as_uri()`, and search for `chrome-headless-shell.exe`, or honour a `CHROME` env var as `src/fitness/tibi/chrome.py` does).
- About twenty scripts mention `.venv/bin` or `/opt/homebrew`. On Windows the venv interpreter is `.venv\Scripts\python.exe`, and `python3.12` may be `py -3.12`.
- **Line endings are a silent killer.** `studio.lock.json` holds SHA-256 hashes of runtime files, `validate` fails when generated `index.<format>.html` files are stale, and the 2D review page must rebuild byte-identical. Make sure git does not convert to CRLF (`git config core.autocrlf false`, or a `.gitattributes` with `* -text` for the generated and hashed files; propose the attribute file to the owner before committing it). Make generators write `\n` explicitly (`newline="\n"`).
- Paths: the Mac checkout path contains a space (`motion graphics`). Code that is safe there with quoting may still break on drive letters and backslashes.

Rules for portability fixes: the Mac render host is the production machine, so **nothing may change behaviour on macOS.** Keep fixes minimal and behind a platform check. Add a test where cheap. Record every fix in `prompts/state/host-windows.md` and in a short section of `docs/` that a Windows user would find (ask the workspace-steward rules in `.claude/skills/workspace-steward/` where it belongs).

**Heavy-job discipline still applies on Windows**: one render, headless-Chrome batch or ML job at a time. The owner's Mac has 8 GB and the rule is permanent there. The Windows box may be bigger, but keep the habit so the tools stay honest for the Mac.

**What needs the Mac render host** (queue it, don't fake it): anything with narration (Kokoro: `build-audio.py`, `src/pipeline/tts.py`), final narrated renders, the five QA gates on a narrated mix (loudness, Earshot), `studio.py build` of a narrated film, and promotion of a catalogue component to `approved` (render-host evidence only).

## 5. What is (and isn't) on the Windows machine

- **From git** (`https://github.com/mveer1/motion-graphics`, branch `main`): all the tool code, the 3D and 2D kits, the 2D generator `src/fitness/tibi/`, the design assets in `assets/fitness/`, the tracked QA fixtures `qa/anatomy3d/`, `qa/rig3d/`, `qa/fitness-render-qa/`, and `qa/regression/lab-3d-compare/` (a 2D-vs-3D curl comparison project, tracked as a regression asset).
- **Not in git**: `projects/` (every film, including the reference 3D compositions `lab-3d-motion`, `knees-past-toes`, `hip-thrust-vs-squat`, `standing-vs-seated-calf`, and the 2D films `upper-body-workout` and `how-muscles-grow`), `out/`, `series/`, and **this `prompts/` folder**. The owner copies these by hand. If a project you need is missing, say so and work from the benches and `qa/regression/lab-3d-compare` meanwhile. Don't recreate a film from memory.
- `tests/test-studio.py` reads untracked projects (`masala-chai/v1-recipe`, `neural-network-learning`) and fails on a fresh clone. That is known and not your bug. Note it, don't "fix" it by committing a project. Moving a trimmed fixture into `tests/fixtures/` was proposed, not decided.

## 6. Working log and handoff (how work travels between machines)

- Code changes travel by **git branch**: work on `windows/<topic>` branches, commit only when the owner asks (or when the prompt you were given says the owner has authorised commits on that branch), and never push without the owner's go-ahead.
- Everything else travels in **`prompts/state/`** (gitignored; the owner carries the folder between machines). Keep:
  - `prompts/state/host-windows.md`: the probe results (tool, version, path, works yes/no) and the portability fixes you made.
  - `prompts/state/log.md`: a dated, append-only log with one entry per working session. Each entry says what you did, what you verified and how, what you didn't verify, and the next steps.
  - `prompts/state/render-queue.md`: jobs that need the Mac render host, each with the exact command, the branch or commit, why it's needed, and what the Mac session should look at in the result. `prompts/08-mac-render-host-handoff.md` is the prompt that drains it.
  - `prompts/state/decisions-needed.md`: questions only the owner can answer, each with options, a recommendation, and pictures (paths to contact sheets) where the choice is visual.
- Before you stop for any reason, bring all four files up to date. A successor (human or model) must be able to continue from them alone.

## 7. Decisions that are NOT yours

Prepare them well with options, evidence, pictures and a recommendation, but don't make them: the 3D look versus the 2D crescent look (the owner's call has been pending since 2026-11-12); anything that changes the approved 2D look (including the generator's rounding quirk in `build2.figure()`, `TODO.md`); deleting the handover's dead code (`HANDOVER.md` section 13); G1/G3 sign-off; trademark ("Sinew", "Tibi"); AI-content disclosure; rewriting git history or force-pushing; adding a new dependency (ADR-9: no new dependencies without a case. Write the case and ask); the definition of a "visual style"; anything in `TODO.md` under "Decide".

## 8. Definition of done (applies to every prompt)

A change is done when all of these hold:

- the relevant numeric tests pass: `node scripts/anatomy3d-check.js`, `node scripts/rig3d-check.js`, and the `tests/test-*.py` you touched, each run directly. There is no test runner.
- `ruff check` is clean on the Python you touched.
- `python scripts/workspace-governance.py` and `python scripts/motion-catalogue.py validate` pass.
- you **looked** at before/after contact sheets of the affected cases and wrote down what you saw.
- `Studio.version` was bumped with a one-line changelog comment if the runtime changed, `upgrade --all` was run where projects exist, and the docs and skills that describe the changed behaviour were updated in the same change.
- the render queue holds anything that needs the Mac.
- the log says what was not verified.
