# Visual engines: evaluation and decision (2026-11-24)

**Decision.** HyperFrames stays the only compositor and the default engine. **Blender is adopted as an experimental plate engine** for the visual jobs the browser cannot fake. **Remotion and Revideo are not adopted** (blocked). **Manim is proposed**, not installed, for equation morphing if a brief ever needs it. A visual director (skill + subagent + `scripts/visual-director.py`) routes each storyboard scene to an engine and composites the results.

Operational rules: `.claude/skills/visual-director/`. Machine-readable registry: `specs/visual-engines.json`.

## The question

Proposed split from the owner:

| Proposed engine | Proposed role |
|---|---|
| Blender | 3D environments, camera movement and depth, particles, fluids, simulations, cinematic lighting and rendering |
| HyperFrames | kinetic typography, 2D diagrams and charts, text overlays |
| Revideo / Remotion | math animations, algorithm explanations, animated diagrams, code-driven educational visuals |

## What the workspace already had

- **HyperFrames 0.8.226 + GSAP 3.12.5 + studio runtime 1.14.0** (approved): deterministic seek of a paused GSAP timeline in headless Chrome. It already draws everything in the third row: SVG diagrams, splines, counters, gauges, particle streams, morphs, connectors, algorithm recipes (`backpropagation-flow`, `node-network-signal-transfer`), per-format layouts from one source. Peak about 410 MB, about 1.5 s per film second at 720p (`specs/motion-graphics-evolution-report.md` section 6.1).
- **Three.js r158 inside the HyperFrames page** (experimental): real 3D, rendered as a pure function of film time; carries the 3D Tibi with tracked labels (`catalogue/data/libraries/threejs.json`). No global illumination, volumetrics or physics.
- **Video footage path**: `ingest-asset.sh` and the approved `hybrid-video-underlay` effect for footage under vector graphics.
- **Remotion**: evaluated and blocked 2026-10-30 (`catalogue/data/skills/claude-remotion.json`). **Revideo**: rejected in `specs/motion-graphics-evolution-report.md` section 5.2.

## Capability comparison

| Visual job | HyperFrames (SVG/DOM/Canvas) | Three.js in the page | Blender | Remotion / Revideo |
|---|---|---|---|---|
| Kinetic type, captions, labels | native, best | via HTML overlay | no (text stays out of plates) | yes (duplicate) |
| 2D diagrams, charts, maps | native, best | possible | no | yes (duplicate) |
| Math as geometry (axes, curves, vectors) | native (SVG + GSAP) | 3D surfaces | possible | yes (duplicate) |
| LaTeX equation typesetting and morphing | **gap**: no typesetter vendored | no | no | via add-ons; Manim is the specialist |
| Algorithm and data-structure walkthroughs | native (recipes exist) | 3D variants | no | yes (duplicate) |
| Stylised 3D with tracked labels | 2.5D only | native | possible, labels must be HTML | via three.js |
| Glass, caustics, subsurface, global illumination | no | approximations | **native** | no |
| Fog, god rays, smoke, fire (volumetrics) | fake with gradients | limited | **native** | no |
| Rigid body, cloth, fluids, particle sims with light | 2D fakes | hand-rolled | **native** (baked) | no |
| Real depth of field, motion blur, camera through a 3D set | fake (blur filters, parallax) | partial | **native** | no |

Remotion and Revideo render React/TSX components in headless Chrome, the same pixel engine HyperFrames drives. On every row where they can do the job, HyperFrames already does it, so they add no capability. Blender is the only candidate that fills cells nothing else fills.

## Blender: intake check

| Check | Finding |
|---|---|
| Need | Light transport, volumetrics, simulations and real lenses have no faithful native or Three.js equivalent (`catalogue/data/references/rendered-3d-objects.json` was a documented backlog item seen in 5 of 14 reference films). |
| Maintainer health | Blender Foundation; three releases a year, one LTS with two years of fixes. 5.2 LTS current at 5.2.4 (2026-11-10), supported to 2028-07 (blender.org/releases). |
| Licence | GPL-2.0-or-later for the application. Used as an external program, nothing linked or vendored; renders are the author's own work (blender.org/about/license). Plate scripts run inside Blender and are workspace code. |
| Install-time / import-time code | Portable archive; no installer hooks. Started with `--factory-startup`, so no user add-ons or startup scripts run. |
| Network and telemetry | None in headless rendering. The installer downloads only from download.blender.org over HTTPS. |
| Pinning | Exact version 5.2.4 with SHA-256 per platform in `specs/visual-engines.json` (copied from the official `blender-5.2.4.sha256`); `install-blender` refuses a mismatched archive. A different Blender version changes every plate's fingerprint. |
| Fit with the 8 GB M2 | Only through the host render lock (one heavy job at a time). EEVEE by default; Cycles on Metal for glass and caustics. Plates are rendered once and cached by fingerprint, so a film re-render does not re-run Blender. Peak memory on the M2: **not measured yet**. |
| Determinism | Seeds from the plan, `lab.rng()` only, baked simulations, pinned version, `Standard` view transform. The plate lint rejects module-level random, wall-clock time and text objects. |

**Measured on this Windows host (Intel Iris Xe, 16 GB), 2026-11-24:** first EEVEE render compiles shaders in 40-70 s; a 720x1280 frame at 16 samples takes about 2.9 s; a 4.4 s portrait plate (132 frames) took 6.4 min in Blender. HyperFrames 0.8.226 seeked the H.264 plate frame-accurately under DOM text and hid it after `data-duration` (snapshots at 0.6, 2.2 and 4.1 s).

## Remotion: decision held (blocked)

- No new capability: a second headless-Chrome frame renderer; React components instead of a GSAP timeline.
- Heavier: Webpack bundling and multi-process rendering, measured above 2 GB at the earlier evaluation on the 8 GB host.
- Licence: source-available, not OSI. Free for individuals, non-profits and for-profit organisations of up to 3 employees; a paid company licence above that (remotion-dev/remotion `LICENSE.md`). Fine for a personal studio, but a cost and a review item if the work moves into an organisation.

## Revideo: decision held (blocked)

- No new capability (a Motion Canvas fork; TSX generator functions, Vite build).
- Upstream activity slowed in 2025 when its lead contributor left (github.com/midrender/revideo issue 356); commits since are sparse.

## The real gap for math films, and Manim

The third row's genuine gap is **equation typesetting and equation-to-equation morphing**, not a renderer. Options, cheapest first:

1. Draw equations as SVG paths in HyperFrames (works today for short formulas).
2. Vendor a typesetter (MathJax SVG output or KaTeX) into the studio runtime: a library intake, no new engine.
3. **Manim Community** (MIT, Python) as a plate engine like Blender: the specialist for LaTeX morphs, but it needs a LaTeX distribution (gigabytes) and a third plate pipeline.

Manim is recorded as `proposed` (`catalogue/data/tools/manim.json`) and not installed; option 2 should be evaluated first when a math brief arrives.

## What was built

| Piece | Where |
|---|---|
| Engine registry, routing signals, pinned Blender builds, not-adopted list | `specs/visual-engines.json` |
| Visual plan schema | `specs/visual-plan-spec.json` → `projects/<slug>/visual-plan.json` |
| CLI: engines, doctor, templates, plan, add-plate, check, render, install-blender | `scripts/visual-director.py` |
| Blender kit (`lab` API) and runner | `src/blender/mlab.py`, `src/blender/run_plate.py` |
| Plate templates | `templates/blender/plates/` (hero-orbit, particle-field, rigid-collapse, light-shafts) |
| Skill and subagent | `.claude/skills/visual-director/`, `.claude/agents/visual-director.md` |
| Studio integration | `studio.py`: `validate` runs the plan checks; `build` adds a `plates` stage before render; `formats` points each format's entry file at its own plate |
| Tests | `tests/test-visual-director.py` |

## Open items

- **Sample film, 2026-11-24 (Windows host):** `projects/sample-engine-mix` ("How Light Bends", 24 s portrait) combines all three engines: a Blender `light-shafts` plate under the hook title, a HyperFrames Snell's-law diagram, a Three.js prism with labels tracked from 3D anchors, and a Blender glass-lens plate under a counter. The plates took 6.6 and 12 min in Blender; the film passed the QA gates (720 frames, no black frames). The test found and fixed three kit problems: EEVEE refraction flags, the world-volume fog that blocks sun light, and face-on light shafts. Two problems are still open: `studio.py build` cannot start `hyperframes` on Windows (it is a `.cmd` shim, so the stages after `plates` ran by hand), and `hyperframes render` there fell back to system fonts where `snapshot` used the bundled ones.
- Render a plate and a full film on the M2 host; measure peak memory and seconds per frame for EEVEE and Cycles on Metal; then decide promotion from `experimental`.
- Alpha plates (`plate-over`, VP9 WebM) are verified through HyperFrames on Windows only.
- Asset sources for Blender (HDRIs, textures, models): only open-licensed sources with recorded licences (for example CC0 libraries) through `workspace-steward`; none is wired in yet. Plates are procedural today.
