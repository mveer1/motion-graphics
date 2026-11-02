# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Motion Lab is a low-memory motion graphics pipeline for Apple Silicon macOS (M2, 8 GB). It produces narrated explainers and multi-format studio videos from `projects/<slug>/` folders. `AGENTS.md` holds the hard production rules, and `ARCHITECTURE.md` section 0 is the design reference for the studio. Read those before changing a render, audio or QA path.

## Hard constraints (read before running anything heavy)

- **One render at a time.** Never run concurrent `hyperframes render`, headless Chrome or Kokoro jobs. Multi-session work goes through `scripts/session-guard.py` (`run render -- <cmd>`, `build`, `audio`, `review`), which takes the lock files in `.locks/`.
- Always pass `--low-memory-mode` and redirect stdin: `hyperframes render . --fps 30 --quality looks --low-memory-mode --output ../renders/visuals.mp4 < /dev/null`. Without `< /dev/null` the rating survey blocks.
- Render duration is not a constraint. Don't cut visual density to save time.
- TTS goes through `src/pipeline/tts.py` (or `scripts/build-audio.py`). Never call `/opt/homebrew/bin/kokoro-tts` directly; it breaks on kokoro 0.9.x.
- Use `python3.12` or `.venv/bin/python` for ML, TTS and schema work.

## Commands

Setup (once per clone):
```bash
git submodule update --init --recursive        # tools/earshot, tools/clipwing-skills
source .venv/bin/activate && pip install -e tools/earshot
```

Studio projects (`project.json` present), the main path:
```bash
python scripts/studio.py new <slug> --template illustrated-explainer --formats landscape,portrait,square
python scripts/studio.py validate <slug>               # schema + cross-reference + determinism lint
python scripts/frame-review.py <slug> --fonts google   # Playwright contact sheets in qa/frame-review/
python scripts/studio.py build <slug> --dry-run        # print per-format plan; runs anywhere
python scripts/studio.py build <slug>                  # render host only: render, mux, QA
python scripts/studio.py review <slug> --init          # then score qa/creative-review.json
python scripts/studio.py sync <slug>                   # refresh src/_studio/ from src/studio/
python scripts/studio.py formats <slug>                # regenerate src/index.<format>.html
```

Legacy technical explainers (no `project.json`): `./scripts/build-project.sh <slug>` runs the full Stage 0–9 chain. Individual steps: `python3 scripts/validate-research.py projects/<slug>`, `python3 scripts/build-audio.py <slug> [--speed 1.15] [--voice am_adam]`, `./scripts/build-all.sh` for the whole portfolio.

Catalogue and governance:
```bash
python scripts/motion-catalogue.py validate
python scripts/motion-catalogue.py search "<intent>" --type effect|recipe|primitive|composition|template|style|technique|source
python scripts/workspace-governance.py                 # run after any component change
python scripts/reference-corpus.py report --backlog
```

Tests. There is no test runner. Each `tests/test-*.py` is a standalone script, so run one file directly:
```bash
python tests/test-studio.py              # CLI, QA-gate scripts, build delegation (needs bash; stubs ffmpeg/ffprobe)
python tests/test-studio-runtime.py      # headless Chromium via Playwright; skips without it
python tests/test-motion-catalogue.py
python tests/test-motion-primitives.py
python tests/test-reference-corpus.py
python tests/test-workspace-governance.py
python tests/test-audio-stack.py         # fails on hosts without Earshot and FFmpeg
```
There is no per-test filter. To narrow a run, edit the file or run the single script you need. `pyproject.toml` configures ruff (`line-length = 100`, rules E/F/W/I); run `ruff check` on the Python you touch.

## Architecture: the big picture

**Two tracks, one toolchain.** Studio projects (`projects/<slug>/project.json`, schema `specs/video-spec.json`) are driven by `scripts/studio.py`. Legacy explainers (no `project.json`) are driven by `scripts/build-project.sh`. `studio.py build` delegates legacy projects to that script, and `build-project.sh` delegates studio projects back to `studio.py build`. Keep both entry points working when you change either one.

**Studio lifecycle.** `brief.json` → optional `research.json`/`research.md` (only when `brief.research.required`) → `storyboard.json` → `src/narration.json` and `audio/` (only with narration) → `src/index.html` (plus generated `src/index.<format>.html`) → `studio.py validate` → `build` (per-format HyperFrames render, FFmpeg mux, QA gates) → `review`. Specs for each file are in `specs/`, and project templates are in `templates/projects/`.

**Runtime and determinism.** `src/studio/` is the canonical runtime (`studio-core.js` for format, safe area, seeded randomness and timeline registration; `studio-draw/type/motion/compositions.js`; `styles/`). HyperFrames serves only the project folder, so `studio.py sync` copies it into `projects/<slug>/src/_studio/` and records SHA-256 hashes in `studio.lock.json`. Edits to the copy are rejected. Compositions must register one paused GSAP timeline through `Studio.build`. `studio.py validate` enforces the rules: no `Math.random`, no wall-clock time, no timers or `requestAnimationFrame`, no infinite repeats, and entrances use `fromTo` with `immediateRender`.

**Layouts are composed per format, not cropped.** Each format is set by `specs/format-presets.json`. Authors write one `src/index.html`, and layout adapts through `#root[data-format=…]` rules and `Studio.pick({landscape, portrait, square})`. Sizes use `--u` (1% of the short side) and `--safe-*`, not pixel values.

**Capability catalogue.** `catalogue/data/` holds libraries, primitives, effects, recipes, compositions, styles, templates, techniques and reference sources. Each record validates against `catalogue/schemas/`, and `motion-catalogue.py validate` checks cross-references. New components start as `experimental` and are promoted only after a HyperFrames render on the render host. Components with `approved` status need render-host evidence, so don't mark one approved from a Windows or non-Mac host.

**Reference corpus.** Videos stay outside the repo, and `scripts/reference-corpus.py` writes analysis caches to `out/reference-analysis/` (untracked). Only technique records (`catalogue/data/references/`) and source records (`catalogue/data/reference-sources/`) are committed. Learn techniques, never assets. Logos, footage and shot sequences are excluded.

**QA.** Three layers: `scripts/frame-review.py` (Playwright preview: clipped text, safe areas, contrast, dead stretches), `.agents/skills/video-assembler/scripts/run-qa-gates.sh` (the five technical gates: streams, EBU R128 loudness, black gaps, bitrate, Earshot), and `qa/creative-review.json` (12 criteria scored 1–5; passes when every score is ≥3 and the mean is ≥3.5). Automated checks do not replace looking at the frames.

**Audio.** Narration is 24 kHz mono WAV from Kokoro with measured durations (`ffprobe`), 0.5 s pause buffers between scenes, and the default voice `am_adam` at 1.15×. SFX come from `scripts/sfx-openverse.py` (CC0/CC BY, public preview CDN URLs only, never Freesound `apiv2`) or from `.venv/bin/earshot sfx render`. The final mix is FFmpeg `amix` of narration, ducked SFX and a dim background bed (about −22 to −28 dBFS). No whoosh sounds on educational scene cross-dissolves.

**Governance.** `.agents/skills/` holds the project skills (including `workspace-steward`, which owns placement and registration of new components) and `.agents/skills/parallel-session/` for multi-session coordination. Consult `workspace-steward` before adding a library, tool, skill or integration. Never commit secrets or machine-specific credentials.

**Output paths.** Renders go to `projects/<slug>/renders/` (gitignored), and finished files go to `out/<slug>-<format>.mp4`. `*.mp4`, `*.wav` under `audio/` and `.hyperframes/` are gitignored. Generated `index.<format>.html` files are tracked, and `studio.py validate` fails when they are stale.

## Conventions

- Project folders hold versions (`v1`, `v3-studio`, `archive/`), and `archive/` is for superseded work. Don't delete old versions to make room.
- Visual defaults: light off-white canvas (`#FBFBFA` / `#F5F3EF` / `#F4EFE6`) with vermilion, ultramarine, marigold, emerald and charcoal accents. Dark themes only when the brief asks for them. Keep `editorial-light` as the default style.
- Anti-laziness rule: narration must never play over a static frame. The visual should change every 2–3 seconds, using multi-beat scenes, progressive reveals and continuous drift.
- Format sizes: landscape 1280×720, portrait 720×1280, square 1080×1080, all at 30 fps. Scale to 1080p or 60 fps only when the brief asks for it.
- Non-Mac hosts (Windows) have no HyperFrames, FFmpeg or Kokoro. There, run `studio.py validate`, `frame-review.py` and `studio.py build --dry-run`, and never claim a render or loudness result that you did not produce.
