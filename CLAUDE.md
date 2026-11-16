# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Motion Lab is a low-memory motion graphics pipeline for Apple Silicon macOS (M2, 8 GB). It produces narrated explainers and multi-format studio videos from `projects/<slug>/` folders. `AGENTS.md` holds the hard production rules, and `ARCHITECTURE.md` section 0 is the design reference for the studio. Read those before changing a render, audio or QA path.

Business context (goals, scale, subjects, non-goals): @docs/VISION.md

## Hard constraints (read before running anything heavy)

- **One heavy job at a time.** Never run concurrent `hyperframes render`, headless Chrome or Kokoro jobs. Any number of sessions may author in parallel (`session-guard.py session-start <slug>`, one git worktree each), but render, TTS and analysis share one host lock in `.locks/` and queue first-come-first-served. Anything not listed below as self-locking goes through `scripts/session-guard.py` (`run [--slug S] [--cwd D] render -- <cmd>`, `build`, `audio`, `review`); `session-guard.py status` shows the holder, the queue and free memory. Full playbook: `.claude/skills/parallel-session/SKILL.md`.
- Always pass `--low-memory-mode` and redirect stdin: `hyperframes render . --fps 30 --quality looks --low-memory-mode --output ../renders/visuals.mp4 < /dev/null`. Without `< /dev/null` the rating survey blocks.
- Render duration is not a constraint. Don't cut visual density to save time.
- Never hold back a runtime, preset or template upgrade because it makes earlier videos stale. Make the upgrade, run `studio.py upgrade --all` (re-syncs `src/_studio/`, regenerates entry files, moves superseded renders to `renders/history/`), and re-render what needs it, one build at a time.
- `studio.py build` takes the render lock itself and stamps each render (`renders/<fmt>/visuals.stamp.json`): an edited composition re-renders on its own, and the stale render is first moved to `renders/history/<fmt>/<when>/` (its `out/` copy to `out/archive/`) with a `history.json` naming the files that changed, so nothing is overwritten. An unstamped legacy render is reused until `studio.py renders <slug> --archive --unstamped` retires it. Renders go to `visuals.partial.mp4` and are renamed only on success. Narration is re-made when `src/narration.json`, the voice or the speed no longer match what `audio/timeline.json` records (`build-audio.py` re-synthesises only the changed scenes and keeps the replaced audio in `audio/history/`); if the new audio moves scene timing, the build stops so the cue times hand-copied into `src/` can be re-timed (`--allow-narration-shift` overrides). `validate` warns on stale narration and errors when speech outruns `duration_sec`. `scene-revise.py` re-stamps the render after a splice, so the mux build keeps it. `build-audio.py`, `src/pipeline/tts.py`, `frame-review.py`, `reference-corpus.py doctor|analyze|strip` and the render stage of `build-project.sh`/`render.sh` take the same host lock themselves (re-entrant under a parent that holds it), so calling them directly is safe. Per-stage timings go to `logs/build-timings.jsonl`. Audit evidence: `docs/architecture-audit.md`.
- TTS goes through `src/pipeline/tts.py` (or `scripts/build-audio.py`). Never call `/opt/homebrew/bin/kokoro-tts` directly; it breaks on kokoro 0.9.x.
- Use `python3.12` or `.venv/bin/python` for ML, TTS and schema work.

## Delegating to Gemini (`agy`) to save Claude tokens

`agy` (Antigravity CLI, already installed) runs Gemini headless and reads workspace files itself, so only its short answer enters your context. Use the `agy` skill (`.claude/skills/agy/SKILL.md`) for any task that is **low in complexity and large in input or output**: summarizing long files, research dossiers or logs, bulk extraction, boilerplate and first drafts (catalogue records, docs, commit text), mechanical edits, and test-output triage. Call it through `.claude/skills/agy/scripts/agy-ask.sh`, default model `gemini-3.8-flash-medium` (`-m gemini-3.8-flash-low` for mechanical work).

- Delegate before reading or generating a big chunk yourself. Don't delegate what one `Grep` or a small `Read` answers: each call has a fixed overhead and takes 4–30 s.
- Never delegate renders, TTS, QA verdicts, creative review or frame judgment, determinism-critical composition code, architecture or governance decisions, or anything with secrets. Prompts and files go to Google.
- agy cannot write files or run commands unless granted (`-w <exact file>`). Prefer having it return text and writing the file yourself. Never use `--dangerously-skip-permissions`.
- Treat output as a draft: check numbers, names and quotes against the source before they reach narration or on-screen text, validate generated JSON, and read `git diff` after any edit. After two failed delegations on the same task, do it yourself.

## Commands

Setup (once per clone):
```bash
git submodule update --init --recursive        # tools/earshot, tools/clipwing-skills
source .venv/bin/activate && pip install -e tools/earshot
```

Studio projects (`project.json` present), the main path. Every project is exactly one of three forms (`specs/video-types.json`, guide `docs/video-forms.md`), each with a 15 s margin at both ends of its range, and `new` requires `--type`. Each form has its own playbook skill for storytelling, scripting, pacing and editing (`.claude/skills/short-form`, `mid-form`, `long-form`); subject knowledge comes from the brief's categories and the style template:

| `--type` | What | Format | Nominal length | Allowed (with margin) | Render |
|---|---|---|---|---|---|
| `short` | Short-form micro explainer: Hook, Explanation, Payoff | portrait | 20-60 s (45 preferred) | 15-75 s | one pass |
| `mid` | Mid-form focused explainer: Hook, Context, Explanation, Demonstration, Conclusion | portrait or landscape (`--formats`) | 60-180 s | 45-195 s | one pass |
| `long` | Long-form documentary or deep dive, told in chapters | landscape (portrait when the brief asks) | 5-12 min | 285-735 s | segments of ~90 s, resumable |

The form fixes the allowed platforms and formats and the length window. `validate` errors when the project or brief falls outside them (195-285 s belongs to no form: cut it to mid or build it out to long); a legacy brief with no `deliverables.video_type` only gets a warning. The pre-2.0 ids `reel`, `long-reel` and `youtube` are accepted as aliases of `short`, `mid` and `long`. Any form can join a series, and one series may mix forms. A long film's `storyboard.json` carries `chapters` (descriptive title, one mechanism, at most three new terms, a re-hook), checked by `validate`. Above 180 s `studio.py build` renders through `scripts/render-segments.py`: segments cut at scene edges, a checkpoint after each in `renders/<fmt>/chunks/`, resume after a killed build, any `src/` edit restarts. Verified on a 22 s film; no 5-12 minute film has been built yet, so treat the long-form numbers as a first guess.
```bash
python scripts/studio.py new <slug> --template illustrated-explainer --type short|mid|long [--formats portrait|landscape] --category history,finance
python scripts/studio.py validate <slug>               # schema + cross-reference + determinism lint
python scripts/frame-review.py <slug> --fonts google   # Playwright contact sheets in qa/frame-review/
python scripts/studio.py build <slug> --dry-run        # print per-format plan; runs anywhere
python scripts/studio.py build <slug>                  # render host only: render, mux, QA, then the poster
python scripts/studio.py poster <slug> | --all        # poster.jpg = last non-black frame of the finished film (build does this itself)
python scripts/studio.py review <slug> --init          # then score qa/creative-review.json
python scripts/studio.py hook score "line one" "line two"   # rank hook lines (a lint, not a view predictor); `hook formulas` lists specs/hook-formulas.json
python scripts/studio.py script <slug>                 # pre-render script and story lint: timed sentence sheet, hook, rhythm, loop, asks, storyboard why-table
python scripts/studio.py captions <slug> --timing words [--preset id]        # local Whisper word times (takes the analysis lock itself) -> cues + audio/words.json + the caption design (preset from the style, lane per section); grouping follows the video type, phrase for reels, sentence for YouTube
python scripts/studio.py words <slug> "four degrees"   # film time a phrase is spoken, to snap a storyboard beat to its noun
python scripts/studio.py sync <slug>                   # refresh src/_studio/ from src/studio/
python scripts/studio.py upgrade <slug>... | --all     # after a runtime or preset change: sync + formats, superseded renders -> renders/history/
python scripts/studio.py renders [<slug>...] [--archive [--unstamped]]   # render state per format (current/stale + changed files/unstamped/missing)
python scripts/studio.py formats <slug>                # regenerate src/index.<format>.html
```

Categories and series. `specs/categories.json` lists the subject categories (technology, finance, science, history, mathematics, news, storytelling). A brief takes one or more in `categories` (first is primary), and `validate` warns when it has none. Style records may be tagged with `categories`; a style with none is general-purpose. A series (`series/<slug>/series.json`, `specs/series-spec.json`) groups projects as `sequential` (numbered parts) or `collection` (unordered, same theme); the series owns membership:
```bash
python scripts/studio.py series new <slug> --kind sequential|collection --category history
python scripts/studio.py series add <series> <project> [--part N] [--planned [--type short|mid|long]]
python scripts/studio.py series show|list|validate [<series>]
```
Style templates. A style template (`catalogue/data/style-templates/`, `docs/style-templates.md`) is the unit you pick per film and the unit you refine: seven records split by visual job (`systems-blueprint`, `proof-canvas`, `data-ledger`, `chronicle`, `storybook`, `news-brief`, `science-atlas`). Each binds a style system and a design profile and adds scene grammar, measurable pacing rules, anti-patterns and a versioned revision log. `project.json` pins `style_template: {id, version}`; refine a template, bump its version, and `style check` lists every project that is behind. `validate` prints the same findings as warnings, never errors:
```bash
python scripts/studio.py style recommend <slug>        # or --category finance --text "..."
python scripts/studio.py style show <id> | list
python scripts/studio.py style adopt <slug> <id>       # pin id and current version (also re-pins)
python scripts/studio.py style check [<slug>]          # one project, or the whole portfolio
python scripts/studio.py new <slug> --template illustrated-explainer --style-template <id> --category <c>
python tests/test-style-templates.py
```
Fitness films (Sinew brand, mascot Tibi): start with the `/fitness` skill (`.claude/skills/fitness/SKILL.md`), an orchestrator that loads capability skills on demand (`fitness-anatomy`, `fitness-animation`, `fitness-qa`, `fitness-publish`). It specialises the pipeline above; it is not a separate one. Architecture, audit, decisions and open items: `docs/fitness-studio.md`; look and language: `assets/fitness/STYLE.md`. Tibi exists in 2D (Cobalt Sculpt; master source `src/fitness/tibi/`, exported to `sculpt-data.js` by `fitness.py sculpt`, never edit that file) and in real 3D (Three.js, vendored): since runtime 1.9.0 the 3D body is ONE continuous skin whose muscles are surface relief and surface regions (`anatomy3d.js`), with cutaways, isolation and skeleton modes; muscles are never separate objects on the body. Rules and tools: `references/motion-3d.md`.
```bash
python scripts/fitness.py plan "<topic>" [--type short|mid|long]      # pillar, form, visual systems, kit assets, steps
python scripts/fitness.py new <slug> --topic "..." --type mid [--formats landscape]   # fitness-explainer template + dossier skeleton
python scripts/fitness.py exercise <id|list> --goal technique|muscle|mistake|compare  # knowledge record -> visual explanation plan
python3.12 scripts/fitness.py dossier <slug>                           # evidence-graded research/dossier.json
python3.12 scripts/fitness.py review <slug> [--init]                   # 10-dimension rubric; science/anatomy/biomech errors are critical
python3.12 scripts/fitness.py check | library | assets | sheets        # manifest, schema, 3D highlight-role audit; library.js; sheets (render lock)
python3.12 scripts/fitness.py sculpt [--check]                         # regenerate (or check) the 2D Tibi runtime data, then studio.py upgrade --all
node scripts/rig3d-check.js [ids] [--gender m|f]                       # numeric QA of every 3D exercise (continuity, contact, reach, range of motion, phase fidelity)
node scripts/anatomy3d-check.js                                        # anatomical acceptance tests (watertight skin, no protrusion, layer order, registration)
.venv/bin/python scripts/anatomy3d-bench.py [--set angles|poses|modes|all]   # contact sheets to LOOK at (render lock)
.venv/bin/python scripts/fitness-animatic.py <slug>                    # stills per scene + pacing lint, before audio
.venv/bin/python scripts/fitness-qa.py <film.mp4> --expect-audio       # frozen frames, first-frame jump, cuts, rhythm, fps labels, A/V sync, loudness
.venv/bin/python scripts/fitness-gates.py <slug>                       # four review gates; accuracy gates need a human in qa/fitness-signoff.json
.venv/bin/python scripts/fitness-publish.py <slug>                     # titles, chapters, sources, credits, thumbnail, platform fit
.venv/bin/python scripts/fitness-clip.py <film.mp4> --cut name:a:b --out out/dir   # frame-exact clips with honest metadata
python3.12 tests/test-fitness.py && python3.12 tests/test-rig3d.py && python3.12 tests/test-anatomy3d.py
```
Open decisions live in `TODO.md` (root).

Legacy technical explainers (no `project.json`): `./scripts/build-project.sh <slug>` runs the full Stage 0–9 chain. Individual steps: `python3 scripts/validate-research.py projects/<slug>`, `python3 scripts/build-audio.py <slug> [--speed 1.15] [--voice am_adam]`, `./scripts/build-all.sh` for the whole portfolio.

Catalogue and governance:
```bash
python scripts/motion-catalogue.py validate
python scripts/motion-catalogue.py search "<intent>" --type effect|recipe|primitive|composition|template|style|technique|source
python scripts/workspace-governance.py                 # run after any component change
python scripts/reference-corpus.py report --backlog
```

Creative intelligence layer (optional; see `specs/creative-intelligence-guide.md`). Use `.venv/bin/python` for these; run heavy ones under `session-guard.py run render --`:
```bash
python scripts/beatmap.py arcs | init <slug> --arc <id> | validate <slug> | storyboard <slug>
python scripts/design-dna.py kb for-beat projects/<slug>/beatmap.json <beat>   # also: measure, extract, verify, validate
python scripts/bakeoff.py run <slug> --beat beat.json --profiles a,b,c         # then: decide
python scripts/assets.py providers | procedural | import | list | export <slug> <ids>
python scripts/motion-qa.py project <slug> --expect-audio                     # objective / measured / judgment; never a creative pass
python scripts/scene-revise.py <slug> --scene s3                               # re-render one scene and splice it in
python tests/test-creative-intelligence.py                                     # 54 tests; needs .venv (Pillow, NumPy, jsonschema)
```

Tests. There is no test runner. Each `tests/test-*.py` is a standalone script, so run one file directly:
```bash
python tests/test-studio.py              # CLI, QA-gate scripts, build delegation (needs bash; stubs ffmpeg/ffprobe)
python tests/test-studio-runtime.py      # headless Chromium via Playwright; skips without it
python tests/test-video-forms.py         # the three forms, chapters, segment planner, segmented build plan (pure Python)
python tests/test-short-form.py          # hooks, word-timed captions, script/story lint, tween variety and conflicts (pure Python, no browser)
python tests/test-motion-catalogue.py
python tests/test-motion-primitives.py
python tests/test-reference-corpus.py
python tests/test-workspace-governance.py
python tests/test-audio-stack.py         # fails on hosts without Earshot and FFmpeg
```
There is no per-test filter. To narrow a run, edit the file or run the single script you need. `pyproject.toml` configures ruff (`line-length = 100`, rules E/F/W/I); run `ruff check` on the Python you touch.

## Architecture: the big picture

**Two tracks, one toolchain.** Studio projects (`projects/<slug>/project.json`, schema `specs/video-spec.json`) are driven by `scripts/studio.py`. Legacy explainers (no `project.json`) are driven by `scripts/build-project.sh`. `studio.py build` delegates legacy projects to that script, and `build-project.sh` delegates studio projects back to `studio.py build`. Keep both entry points working when you change either one.

**Studio lifecycle: four phases, each ending at a gate** (full table: `ARCHITECTURE.md` section 0.1, steps: `AGENTS.md` section 1).
1. **Brief and research:** `brief.json` sets categories, formats, length range and style template. `research.json`/`research.md` hold facts only, and only when `brief.research.required`.
2. **Story and structure:** the `story-writer` subagent writes `beatmap.json`, `storyboard.json` and the `src/narration.json` text, loops with research, and signs off in `qa/story-review.json`. `creative-director` then settles the look.
3. **Audio, visuals and sound, as one sequential loop:** measured audio, then `src/index.html` (plus generated `src/index.<format>.html`) snapped to it, then SFX. They are not parallel: visuals are timed to measured speech, and the heavy steps share the host lock. Ends at the pre-render gate: `studio.py validate` + `frame-review.py`.
4. **Render and review:** `build` (per-format HyperFrames render, FFmpeg mux, QA gates) → `review` → story-writer `retro`.

Specs for each file are in `specs/`, and project templates are in `templates/projects/`.

**Runtime and determinism.** `src/studio/` is the canonical runtime (`studio-core.js` for format, safe area, seeded randomness and timeline registration; `studio-draw/type/motion/compositions.js`; `styles/`). HyperFrames serves only the project folder, so `studio.py sync` copies it into `projects/<slug>/src/_studio/` and records SHA-256 hashes in `studio.lock.json`. Edits to the copy are rejected. A runtime change reaches projects through `studio.py upgrade` (version label `Studio.version`; 1.1.0 added the spoken-word caption highlight; 1.3.0 added caption presets and lanes (`specs/caption-presets.json`, `docs/caption-design.md`: a preset per style system, a lane per section, `caption_lane` on a storyboard scene); 1.2.0 vendored GSAP 3.12.5 as `_studio/vendor/gsap.min.js`, so renders need no network: load it from there, never from a CDN; 1.4.x added the rig and the fitness kit; 1.5.0 added the Cobalt Sculpt Tibi and the rig's `derive` hook for pose-dependent attributes; 1.6.0 retired the classic Tibi and added per-joint foreshortening, back, top and above views, a bending shoe, grip hands and the 12-exercise library). Compositions must register one paused GSAP timeline through `Studio.build`. `studio.py validate` enforces the rules: no `Math.random`, no wall-clock time, no timers or `requestAnimationFrame`, no infinite repeats, and entrances use `fromTo` with `immediateRender`.

**Layouts are composed per format, not cropped.** Each format is set by `specs/format-presets.json`. Authors write one `src/index.html`, and layout adapts through `#root[data-format=…]` rules and `Studio.pick({landscape, portrait, square})`. Sizes use `--u` (1% of the short side) and `--safe-*`, not pixel values.

**Capability catalogue.** `catalogue/data/` holds libraries, primitives, effects, recipes, compositions, styles, templates, techniques and reference sources. Each record validates against `catalogue/schemas/`, and `motion-catalogue.py validate` checks cross-references. New components start as `experimental` and are promoted only after a HyperFrames render on the render host. Components with `approved` status need render-host evidence, so don't mark one approved from a Windows or non-Mac host.

**Reference corpus.** Videos stay outside the repo, and `scripts/reference-corpus.py` writes analysis caches to `reference/analysis/` (untracked). Only technique records (`catalogue/data/references/`) and source records (`catalogue/data/reference-sources/`) are committed. Learn techniques, never assets. Logos, footage and shot sequences are excluded.

**QA.** Three layers: `scripts/frame-review.py` (Playwright preview: clipped text, safe areas, contrast, dead stretches), `.claude/skills/video-assembler/scripts/run-qa-gates.sh` (the five technical gates: streams, EBU R128 loudness, black gaps, bitrate, Earshot), and `qa/creative-review.json` (12 criteria scored 1–5; passes when every score is ≥3 and the mean is ≥3.5). Automated checks do not replace looking at the frames.

**Audio.** Narration is 24 kHz mono WAV from Kokoro with measured durations (`ffprobe`), 0.5 s pause buffers between scenes, and the default voice `am_adam` at 1.15×. SFX come from `scripts/sfx-openverse.py` (CC0/CC BY, public preview CDN URLs only, never Freesound `apiv2`) or from `.venv/bin/earshot sfx render`. The final mix is FFmpeg `amix` of narration, ducked SFX and a dim background bed (about −22 to −28 dBFS). No whoosh sounds on educational scene cross-dissolves.

**Governance.** `.claude/skills/` holds the project skills (including `workspace-steward`, which owns placement and registration of new components) and `.claude/skills/parallel-session/` for multi-session coordination. Consult `workspace-steward` before adding a library, tool, skill or integration. Never commit secrets or machine-specific credentials.

**Posters.** Every project has `poster.jpg` (plus `poster.json`: source film, time, film length) in its folder, or in each version folder for a legacy project. It is the last non-black frame of the finished film (the primary format's current render, else the newest in `renders/history/`), made by `scripts/poster.py`. `studio.py build` makes it as its last stage and `build-project.sh` after the legacy export, so a new project gets one without a separate step; re-run `studio.py poster <slug>` after a `scene-revise` splice. Posters are small (about 100 KB each). The catalogue (`python3 scripts/build-catalogue.py` -> `out/catalogue.html`) shows the poster on every tile, tags it with a video type (the brief's `video_type`, else by the film's length: up to 60 s reel, up to 180 s long reel, longer YouTube) and a progress stage (in production, rendered, reviewed, plus a re-render flag). The story-writer's publishing cover is a separate, chosen frame; the poster is the workspace's own thumbnail.

**Ideas backlog.** `docs/project-ideas.md` is the source of the catalogue's Ideas tab, an editable sheet (add, edit, delete, sort, search, paste rows from Excel, copy out for Excel) split into sheets by video length (`reel`, `long-reel`, `youtube`). Every idea carries a `[length]` tag, which the builder requires. The sheet keeps edits in the browser only: use its "Download .md" and save the file over `docs/project-ideas.md`, then rebuild with `python3 scripts/build-catalogue.py`. The download matches the file's own format byte for byte.

**Output paths.** Renders go to `projects/<slug>/renders/` (gitignored), and finished files go to `out/<slug>-<format>.mp4`. `*.mp4`, `*.wav` under `audio/` and `.hyperframes/` are gitignored. Generated `index.<format>.html` files are tracked, and `studio.py validate` fails when they are stale.

## Conventions

- Project folders hold versions (`v1`, `v3-studio`, `archive/`), and `archive/` is for superseded work. Don't delete old versions to make room.
- Visual defaults: light off-white canvas (`#FBFBFA` / `#F5F3EF` / `#F4EFE6`) with vermilion, ultramarine, marigold, emerald and charcoal accents. Dark themes only when the brief asks for them. Keep `editorial-light` as the default style.
- Anti-laziness rule: narration must never play over a static frame. The visual should change every 2–3 seconds, using multi-beat scenes, progressive reveals and continuous drift.
- Format sizes: landscape 1280×720, portrait 720×1280, square 1080×1080, all at 30 fps. Scale to 1080p or 60 fps only when the brief asks for it.
- Non-Mac hosts (Windows) have no HyperFrames, FFmpeg or Kokoro. There, run `studio.py validate`, `frame-review.py` and `studio.py build --dry-run`, and never claim a render or loudness result that you did not produce.
