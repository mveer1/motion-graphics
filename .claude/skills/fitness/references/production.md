# Sinew production: tools, pipeline, rendering and limits

## Tools on the render host (inspected 2026-11-08)

| Tool | State | Role for fitness films |
|---|---|---|
| HyperFrames 0.8.226 + GSAP 3.12.5 (vendored) | installed | the only renderer: HTML/SVG compositions, deterministic seek |
| `src/studio/` runtime 1.4.0 | canonical | adds `studio-rig.js` and `kits/fitness/*` (synced into every project) |
| FFmpeg | installed | mux, loudness, frame extraction for review |
| Kokoro 0.9.4 via `src/pipeline/tts.py` | installed | narration (`am_michael` 1.05, slow scenes 0.94) |
| Whisper small.en (hyperframes transcribe) | installed | word-timed captions |
| Earshot (`.venv/bin/earshot`) | installed | mix and sync listening (`timeline`, `measure`) |
| Python Playwright | **absent** | `frame-review.py` cannot run; use `hyperframes snapshot` and the sheet renderer |
| Blender | **absent** | see the 3D decision below |
| Revideo / Motion Canvas | CLI installed globally, wired into nothing | not used: the workspace standard is HyperFrames (a prior report rejected Revideo) |

## 3D decision (revised 2026-11-12)

The 2D rig cannot give smooth press, curl or raise motion (art swaps at joint thresholds pop; views are separate drawings) and cannot move the camera: `references/motion-3d.md` has the diagnosis and measurements.

- **Chosen: Three.js r158 in HyperFrames' headless Chrome.** Verified on this host through `hyperframes snapshot` and `hyperframes render` (software WebGL, real pixels, labels tracked from 3D anchors). It keeps determinism (pose is a pure function of film time, see motion-3d.md), the render lock, captions, QA gates and HTML overlays. Library record: `catalogue/data/libraries/threejs.json`.
- **Blender: still not installed.** It would give sculpted, subsurface-smooth anatomy, but it is a large dependency, a second toolchain with no determinism lint, no HTML overlay path, and the Cobalt Sculpt look is flat planes, which Three.js toon materials already produce. If Blender is wanted later (photoreal or sculpted anatomy plates): `brew install --cask blender`, register it in `catalogue/data/tools/`, consult `workspace-steward`, build the armature from the same joint names, export `T3.DEFAULT_POSE`-keyed tracks as JSON, render headless one job at a time under `session-guard run render --`, ingest with `scripts/ingest-asset.sh` and composite in HyperFrames. Anatomy meshes must come from cleared sources only (`source-registry.md`).

## Rig workflow (2D)

1. Pose authoring: add a named pose to `exercises.js` (`F.poses.side`/`front`) with anatomical angles. Use `flat` for feet, `anchor` for planted contacts (a sole or a grip), and `ik` for a second planted limb.
2. Preview: add the pose or exercise to `assets/fitness/sheets/poses.html` or `exercises.html` and run `python scripts/fitness.py sheets --only poses`.
3. Check: contacts planted, no limb through the floor, joints within limits, props following (followers).
4. Register: metadata in `assets/fitness/data/exercises.json`, `fitness.py library`, manifest entry, `fitness.py check`, `python tests/test-fitness.py`.
5. Ship the runtime: bump `Studio.version` and run `python scripts/studio.py upgrade --all`.

## Export pipeline (brand sources and previews)

- Master sources are code: the Cobalt Sculpt Tibi's Python generator `src/fitness/tibi/` (exported to `sculpt-data.js` by `fitness.py sculpt`; painter `sculpt.js`), `brand.js` (palette), `graphics.js` (logo, cards), `anatomy.js` (plates), `exercises.js` (poses).
- `assets/fitness/sheets/*.html` lay them out as boards. `python scripts/fitness.py sheets` renders each to `assets/fitness/previews/<name>.png` and, where a sheet sets `data-export-svg`, writes an editable SVG to `assets/fitness/brand/` (logo board, model sheet, thumbnail template). It runs headless Chrome from the HyperFrames install under the host render lock.
- Sheet pages load Google Fonts copies of Outfit, Inter and JetBrains Mono for previews only; films use the HyperFrames-bundled fonts.

## Rendering a film

```bash
python scripts/fitness.py new <slug> --topic "..." --type mid --formats landscape
# brief, research.json, research/dossier.json, story, narration
python3.12 scripts/build-audio.py <slug> --voice am_michael --speed 1.05
python3.12 scripts/studio.py captions <slug> --timing words [--grouping phrase]
# src/index.html from the template; audio/generate_bed_and_sfx.py via sinew_sound.py
python3.12 scripts/studio.py validate <slug> && python3.12 scripts/fitness.py check
python3 scripts/session-guard.py run --slug <slug> --cwd "$PWD/projects/<slug>/src" render -- hyperframes snapshot . --at ... --output <dir> < /dev/null
python3.12 scripts/studio.py build <slug>
python3.12 scripts/fitness.py review <slug> --init   # then score it after watching
```
Measured on the demo: a 97.5 s 1280x720 film renders in about 2.5 minutes (low-memory mode, screenshot capture), and the whole build with mux, QA gates and poster takes about 3 minutes.

## Known limitations

- 2D rig: views are separate drawings (a turn is a cross-fade); no foreshortening, so front-view squats and lunges are not authored; muscle and bone shapes are schematic. Art variants swap at joint thresholds, which pops on curls, presses and raises: use the 3D kit for those (`motion-3d.md`).
- 3D rig: three exercises so far; look is toon ellipsoids, not the 2D crescent art; no cloth or hair simulation. See `motion-3d.md`, Known limits.
- Kinematics are conceptual (authored angles), not motion capture. Measured kinematics would need a cited dataset and a "measured" label.
- The leg-press setup reads less clearly than the other movements (seat-back geometry); improve before featuring it.
- Anatomy plates cover muscle tissue, energy (mitochondrion, ATP), heart, lungs and a satellite cell; no vascular tree, no alveolus gas-exchange plate, no joint cross-sections yet.
- No 3D anatomy library: every open 3D source examined is share-alike, per-model or non-commercial (`source-registry.md`).
- Tibi lip-sync is word-level flaps, not phoneme visemes.
- Calibration: the rubric thresholds, the body-lab template rules and the pillar keywords are first guesses from one film.
