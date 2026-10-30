# Creative Studio Evolution: Audit and Implementation Plan

**Status:** Implemented in part. See "Delivery status" at the end for what is built, what is validated, and what is still planned.

**Date:** 2026-10-30. Audited on a Windows host; the production render host described elsewhere is an Apple M2 (8 GB) Mac.

## 1. Capabilities worth preserving

| Capability | Where | Why keep it |
| --- | --- | --- |
| HTML + SVG + GSAP 3 compositions seeked by HyperFrames | `projects/*/src/index.html` | Deterministic, agent-friendly, no build step. Upstream HyperFrames (Apache-2.0) already supports MP4/WebM/MOV, `check`, `snapshot --review`, `beats`, captions. |
| Paused root timeline on `window.__timelines['root']`, seeded PRNG, zero-dip crossfade | skills, recipes | Correct determinism contract; matches upstream rules. |
| Audio-first timing (Kokoro TTS, measured durations, `audio/timeline.json`) | `scripts/build-audio.py` | Exact narration sync for narrated work. |
| Two-pass assembly (silent visuals, then FFmpeg mux) | `scripts/build-project.sh` | Avoids A/V drift; cheap on 8 GB. |
| Capability catalogue with approval states and licence gating | `catalogue/`, `scripts/motion-catalogue.py` | Prevents unvetted dependencies. |
| Governance gates and placement policy | `workspace-steward`, `scripts/workspace-governance.py` | Keeps the registry and the disk in step. |
| Research dossier for factual topics | `technical-researcher`, `specs/research-spec.json` | Anti-hallucination gate for technical and scientific work. |

## 2. Architectural limitations found

| # | Limitation | Evidence |
| --- | --- | --- |
| L1 | Every project is assumed to be a narrated technical explainer. There is no creative brief; Stage 0 is always technical research. | `AGENTS.md` section 1, `ARCHITECTURE.md` section 4, `research-spec.json` domain enum (a finance piece had to use `physics_mathematics`). |
| L2 | One aesthetic. All palettes are dark (Dark Tech, Cyber Cyan, Quantum Violet); the starter and every project use cards, glowing nodes and progress bars. | `motion-graphics-designer/references/palettes.md`, `scripts/new-project.sh`, `out/posters/*.png`. |
| L3 | Resolution is hardcoded to 1280x720 in CSS, `body` size, scaffolder and QA. The one portrait project hardcodes 720x1280. HyperFrames cannot reshape an aspect ratio at render time, so formats need separate entry files. | `new-project.sh`, `projects/china-market-crash-2026/src/index.html`, upstream `render --resolution` docs. |
| L4 | Effect vocabulary is technical: 8 effects (crossfade, packet, dashed stroke, clip reveal, glow, video underlay, brush, Lottie). No typography, masks/wipes, morphs, 2.5D, texture, rhythm or loop primitives. | `catalogue/data/effects/`. |
| L5 | Catalogue has libraries/effects/recipes only. No primitives, reusable compositions, project templates, style systems, or a way to record reference-derived techniques without implying they are implemented. | `scripts/motion-catalogue.py` COLLECTIONS. |
| L6 | Every composition re-implements helpers inline (PRNG, fades, builders). Nothing is shared or testable. HyperFrames serves only the project directory, so a shared runtime must be copied into each project. | `projects/*/src/index.html`, copied `p5-brush/vendor/brush.js`. |
| L7 | QA is technical only and partly informational: Gate 1 prints but never asserts resolution/fps; a video without audio aborts Gate 2 (`grep` under `pipefail`); no creative review. | `.agents/skills/video-assembler/scripts/run-qa-gates.sh`. |
| L8 | Governance fails on Windows (backslash paths vs registered `/` paths) and treats a machine-local `.venv` binary as a missing workspace file. | Baseline run on this host: 22 false failures. |
| L9 | Documentation describes features as verified that cannot be re-verified from the repo (absolute macOS paths, fixed loudness numbers that disagree between files). | `ARCHITECTURE.md`, `README.md` (-21.2 LUFS vs -16 to -14 LUFS). |

## 3. Changes

### 3.1 Creative workflow (fixes L1, L2)

- New Stage 0 **Brief and direction**: `brief.json` (what the piece must achieve) validated by `specs/brief-spec.json`, with up to three genuinely distinct creative directions and a recorded choice.
- New Stage 1 **Storyboard / scene plan** for complex work: `storyboard.json` validated by `specs/storyboard-spec.json` (beats, layout intent per format, capabilities, transitions, audio cues). Optional for simple briefs.
- Technical research becomes **Stage 0R**, required only when the brief sets `research.required: true` (factual, technical or scientific claims).
- **Production spec** (how to render) moves to `project.json`, validated by `specs/video-spec.json` (rewritten from an unused draft): formats, fps, quality, style system, template, audio plan, timing source.
- Light-first default: style system `editorial-light`. Dark styles remain available on request.

### 3.2 Component model (fixes L4, L5, L6)

Six layers, kept distinct in the catalogue:

| Layer | Collection | Implementation lives in |
| --- | --- | --- |
| Primitives | `catalogue/data/primitives/` | `src/studio/*.js` helpers, native SVG/CSS |
| Effects (+ recipes) | `effects/`, `recipes/` (existing) | `src/studio/*.js` |
| Compositions | `catalogue/data/compositions/` | `src/studio/compositions.js` |
| Project templates | `catalogue/data/project-templates/` | `templates/projects/<id>/` |
| Style systems | `catalogue/data/styles/` | `src/studio/styles/<id>.css` |
| Reference-derived techniques | `catalogue/data/references/` | documentation only until `implemented_by` points at an effect/recipe/composition |

The workspace runtime (`src/studio/`) is copied into each project as `src/_studio/` by `scripts/studio.py sync`, with a SHA-256 lock file so drift is detectable.

### 3.3 Formats (fixes L3)

- Presets: landscape 16:9 1280x720, portrait 9:16 720x1280, square 1:1 1080x1080; 30 fps default, 60 optional; 1080p/4K presets declared.
- One source composition (`src/index.html`) authored in format-relative units; `scripts/studio.py formats` generates `src/index.<format>.html` entry files with the correct root size, `data-format` and safe-area variables. Layout adapts through `[data-format]` rules, not stretching.

### 3.4 QA (fixes L7)

- Technical: `run-qa-gates.sh` gains `--expect-*` assertions and handles silent videos.
- Visual/creative: `scripts/frame-review.py` (Playwright, already installed) seeks the timeline per format, writes contact sheets and a JSON report: blank frames, dead stretches, text below size floor, text outside frame or safe area, text collisions, reading-time floor, first frame empty. It honours HyperFrames `data-layout-*` opt-outs. `hyperframes check` remains the authoritative gate where HyperFrames is installed.
- Creative review rubric recorded per project (`qa/creative-review.json`), never auto-passed.

### 3.5 Governance (fixes L8, L9)

- Path normalisation and `.venv` leniency in governance; new collections validated and cross-referenced; tests extended.
- Architecture docs rewritten to describe what exists, with verification status.

## 4. Dependencies and risks

| Item | Decision |
| --- | --- |
| New packages | None installed. Python stdlib + existing `jsonschema`, `Pillow`, `numpy`, `playwright` (optional, QA only). |
| GSAP | Stay on approved 3.12.5 core. SplitText/DrawSVG/MorphSVG need GSAP >= 3.13 and remain `proposed`; the runtime covers split text, stroke draw and compatible-path morphs itself. |
| Fonts | Only HyperFrames-bundled families (Inter, Playfair Display, EB Garamond, Archivo Black, Nunito, Oswald, JetBrains Mono, IBM Plex Mono, ...) plus generic fallbacks. No font files added. Variable-weight animation is `experimental` (bundle ships fixed weights). |
| Render host | HyperFrames and FFmpeg are not installed on the Windows host used for this change, so MP4 renders, audio QA and `hyperframes check` must run on the Mac. Frame review in Chromium is preview-grade. |
| Risk | Font metrics differ between hosts; frame review can inject the same OFL families from Google Fonts at QA time (`--fonts google`) to reduce the gap. |

## 5. Validation criteria

1. `python scripts/motion-catalogue.py validate` and `python scripts/workspace-governance.py` pass with 0 errors on Windows.
2. Existing suites pass (`tests/test-motion-catalogue.py`, `tests/test-workspace-governance.py`) plus a new `tests/test-studio.py`.
3. All four existing research dossiers still validate; existing project files are unchanged.
4. Representative non-technical project validates (`studio.py validate`) and frame review passes in landscape, portrait and square, with contact sheets inspected.
5. Regression: the benchmark technical explainer loads and seeks without console errors in frame review; `studio.py build --dry-run` produces the legacy command plan for it.
6. Bash scripts pass `bash -n`.

## Delivery status

Results are recorded in `ARCHITECTURE.md` section 0.7 ("Verification Status"). Not delivered in this change: the kinetic-typography, product-promo and technical-explainer project templates (registered as `proposed`), HyperFrames renders and audio QA on the M2, and promotion of any new component beyond `experimental`.
