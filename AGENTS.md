# Operational Guide for AI Agents (AGENTS.md)

This repository is optimized for motion graphics production on Apple Silicon macOS, configured with **VS Code as the primary development workstation** and **Antigravity as the secondary autonomous accelerator**. For VS Code Copilot & IDE directives, see `.github/copilot-instructions.md` and `.vscode/`.

---

## 0. Workspace Governance Entry Point (`workspace-steward`)
Whenever discovering, introducing, installing, modifying, registering, or retiring any workspace component (libraries, tools, skills, subagents, integrations, shared assets):
- **Always consult `workspace-steward` first** before creating files, changing dependencies, or altering architecture.
- Enforce the **7-Domain Placement Policy** (`.agents/skills/workspace-steward/references/component-placement-policy.md`). Never copy third-party code without licence clearance and explicit justification.
- Ensure every component in active use is registered in `catalogue/data/` conforming to `catalogue/schemas/`.
- **Zero Secrets Rule:** Never commit secrets, private keys, API tokens, or machine-specific credentials to source code or catalogue records.
- Run `python3 scripts/workspace-governance.py` after component changes to verify schema validity and detect drift.

---

## 1. Mandatory Production Lifecycle
Two tracks share one toolchain (details: `ARCHITECTURE.md` section 0):

**Studio projects** (any deliverable: explainer, promo, kinetic type, recipe, title sequence; any project with `project.json`):
1. `python scripts/studio.py new <slug> --template <id>` (templates: `python scripts/motion-catalogue.py list` or `templates/projects/`).
2. Stage 0 `brief.json`: objective, audience, formats, 1-3 genuinely distinct creative directions, the selected one and why. Research (Stage 0R) only when `brief.research.required`; narration only when the brief asks for it.
3. Stage 1 `storyboard.json` with catalogue capabilities and explicit transitions; pick a registered style system (default `editorial-light`; off-white or lighter background with warm, high-contrast, vibrant colors; dark themes only when explicitly requested).
4. Stage 4 `src/index.html` on the vendored runtime (`src/_studio/`, synced from `src/studio/`; never edit the copy). Compose each format; use `--u`, `--safe-*`, `#root[data-format]` rules and `Studio.pick` instead of hard-coded pixel sizes. Follow the **Anti-Laziness Mandate**: zero static visual freezes while narration is speaking.
5. `python scripts/studio.py validate <slug>` and `python scripts/frame-review.py <slug> --fonts google`; look at the contact sheets, fix, repeat.
6. Render host only: `python scripts/studio.py build <slug>` (per-format render, 3-track audio mux with voice, SFX and dim themed background music bed, QA with expectations), then `python scripts/studio.py review <slug> --init` and score `qa/creative-review.json` with evidence.

**Legacy technical explainers** (no `project.json`) keep the original stages below; `scripts/build-project.sh` behaves as before.

**Reference videos** (the user supplies examples to learn from): use `reference-analyst`. Videos stay outside the repository; `scripts/reference-corpus.py ingest` then `analyze --pending --root <folder>` write evidence to the untracked `out/reference-analysis/`; inspect it, write source and technique records, run `python scripts/motion-catalogue.py validate` and `python scripts/reference-corpus.py report --backlog`. Learn techniques, never assets: brand marks, characters, footage and shot sequences are excluded (`ARCHITECTURE.md` section 0.8).

Every explainer video produced in this repository must follow the phased lifecycle defined in `ARCHITECTURE.md`:
1. **Stage 0 (Research & Investigation):** Research the technical domain, verify formulas/algorithms, formulate visual metaphors, and produce both `projects/<project_name>/research.json` (validated against `specs/research-spec.json` via `scripts/validate-research.py`) and `projects/<project_name>/research.md`. **Never** write scripts before validating the research dossier.
2. **Stage 1 & 2 (Storyboarding & Voice Script):** Generate `narration.json` using the `voice-director` skill and phonetic respellings.
3. **Stage 3 (Speech Synthesis & Measurement):** Synthesize voice clips with `src/pipeline/tts.py` and measure exact millisecond durations via `ffprobe` to build the timeline map.
4. **Stage 4 (Motion Graphics Composition):** Search the capability catalogue (`scripts/motion-catalogue.py search`) via `motion-library-guide` to select approved capability recipes and verify dependency states, then author `src/index.html` using GSAP 3 timelines anchored to measured timestamps (`motion-graphics-designer` skill). Adopt off-white / light backgrounds with warm, vibrant, high-contrast colors by default. Strictly enforce the **Anti-Laziness Mandate**: zero static visual freezes while narration speaks.
5. **Stage 4B (Sound Design & Foley Choreography):** Extract animation moments from `src/index.html` via `from_hyperframes.py`, source CC0 assets via `scripts/sfx-openverse.py` or synthesize micro-SFX via `.venv/bin/earshot sfx render`, plan cues with `suggest_cues.py`, render `audio/sfx-track.wav` with `real-sfx mix.py`, and source a dim themed background music bed (`audio/bgm.wav`) to hook viewer attention.
6. **Stage 5–6 (Lint & Render):** Lint with `hyperframes lint`, render visuals non-interactively with `hyperframes render --low-memory-mode < /dev/null`.
7. **Stage 8 (Multi-Track Multiplexing):** Combine visuals, voice narration, ducked SFX bed, and dim themed background music bed with FFmpeg `amix`.
8. **Stage 9 (Automated QA & Verification):** Execute `run-qa-gates.sh` verifying all 5 gates (Streams, EBU R128 loudness, black gaps, bitrate, and Earshot acoustic metrics).

---

## 2. Project-Specific Skills

Specialized skills are available under `.agents/skills/`:
- **`workspace-steward`**: Workspace-wide governance over component discovery, 7-domain placement policy, registration, licensing audit, architecture documentation, and automated drift detection (`scripts/workspace-governance.py`).
- **`technical-researcher`**: Stage 0 deep research, mathematical truth verification, visual metaphor archetypes, and `research.json` schema validation.
- **`motion-library-guide`**: Capability catalogue navigation, dependency vetting, approval states (approved/proposed/blocked), verified licensing, and deterministic GSAP animation recipes.
- **`motion-graphics-designer`**: Color palettes, layout rules, GSAP 3 animation patterns, and deterministic PRNG rules.
- **`reference-analyst`**: Reference video ingest and analysis (`scripts/reference-corpus.py`), source and technique records with observation separate from interpretation, capability classes (native, approximation, additional dependencies, resource-constrained, research required), provenance, brand-asset exclusion and the capability backlog.
- **`gsap-core` / `gsap-timeline` / `gsap-plugins` / `gsap-utils` / `gsap-performance`**: Official GreenSock AI skills for GSAP 3 core tweens, timeline choreography, plugin registration, and rendering performance.
- **`kinetic-typography`**: Specialized kinetic typography choreography, overflow mask reveals, variable-font weight shifts, and accessibility protections (preserving screen-reader `aria-label` on text mutations).
- **`motion-design`**: LottieFiles motion design principles, Disney animation principles adapted for UI, timing/easing curves, hero staging, and 1/3 rules (motion distance $\le 33\%$, max 3 simultaneous dynamic elements).
- **`epic-design`**: Cinematic 2.5D pseudo-3D staging, 6-layer depth system (`data-depth="0"` to `"5"` with standardized parallax/scale/blur tokens), hero-companion spatial hierarchy, and directional clip-path transitions without WebGL.
- **`collage-design`**: Procedural mixed-media collage styling (torn paper deckle edges via SVG `feTurbulence`, blueprint grids, cut masking tape, halftone patterns) rasterized natively via headless Chromium.
- **`algorithmic-art`**: Generative and algorithmic art systems (flow fields, attractors, shaders) adapted for deterministic HyperFrames rendering.
- **`voice-director`**: Kokoro voice personas, speech pacing, silence buffers, and phonetic pronunciations.
- **`real-sfx`**: Sound design and foley placement for motion graphics; extracts cues from HyperFrames compositions (`from_hyperframes.py`), maps visual events to real recordings, and renders balanced SFX audio tracks.
- **`earshot`**: Acoustic verification, sync measurement, loudness/spectral checks, and procedural sound synthesis (`earshot forge`/`sfx`).
- **`video-assembler`**: Render profiles, low-memory management, multi-track FFmpeg multiplexing, and automated QA gates.

---

## 3. Sound Effects & Audio Sourcing Engine
- **Openverse Asset Sourcing:** Use `scripts/sfx-openverse.py "<query>" --limit <N> --download --out-dir assets/audio/sfx` to search and retrieve free, Creative Commons CC0 / CC BY sound assets (whooshes, UI clicks, risers, impacts, ambient music loops) with zero API keys.
  - *CRITICAL:* Never attempt downloading Freesound `apiv2` URLs which require authentication. Always use the public preview CDN URL in `item["url"]`.
- **Dim Themed Background Music / Ambient Bed:** Every explainer video incorporates a continuous, dim background music bed matching the project theme (e.g. minimalist techno pulse for finance/crises, modular synth drone for AI/systems, warm acoustic/marimba for lifestyle/recipes) at `-22` to `-28 dBFS` integrated loudness (~15 to 20 dB below voice). This eliminates dead air, hooks viewer attention, and sustains engagement.
- **Prohibit Transition Whooshes in Educational Explainers:** Do NOT use whoosh sounds on scene cross-dissolves in educational explainers. Scene transitions should be visually seamless and sonically transparent.
- **Tactile Micro-Sound Foley:** Punctuate data changes, counter rolls, chart draws, and badge reveals with subtle tactile micro-sounds (soft thuds, switch clicks, typewriter runs at `-12` to `-18 dB` below voice).
- **Procedural Sound FX:** Use `.venv/bin/earshot sfx render <id> -o <path.wav>` for instant, zero-latency code-synthesized micro-sounds (pops, thocks, clicks, chime runs).
- **Acoustic Quality Audit:** Use `.venv/bin/earshot measure <file>` or `run-qa-gates.sh` to measure true peak, integrated loudness, noise floor, and frequency bands.

---

## 4. Hardware & Memory Management (CRITICAL)
- **Host Specs:** Apple M2, 8 GB Unified RAM, macOS 26.3.
- **Rules:**
  - **NEVER** run parallel rendering commands or multiple headless Chrome instances.
  - **ALWAYS** pass `--low-memory-mode` to `hyperframes render` to pin the worker count to 1 and use screenshot capture.
  - **NON-INTERACTIVE RENDER INVARIANT:** Always execute `hyperframes render` with stdin redirected: `< /dev/null` (e.g., `hyperframes render . --fps 30 --quality looks --low-memory-mode --output ../renders/visuals.mp4 < /dev/null`) to prevent the interactive rating survey prompt from blocking autonomous execution.
  - **RENDER TIME IS NOT A CONSTRAINT (ANTI-LAZINESS DIRECTIVE):** Apple Silicon M2 memory management rules are strictly about **concurrency and worker limits** to prevent RAM exhaustion. **Render duration is NOT a constraint — time is not a concern.** Whether rendering takes 30 seconds or 3 minutes is completely acceptable. Agents must **NEVER** hold back on visual richness, animation density, kinetic choreography, or multi-step evolutions out of fear of render time or hardware warnings. The framework must NOT be lazy.
  - **Python Environment:** Always invoke `python3.12` (or rely on auto-delegating wrappers) for ML/TTS and schema validation.
  - **Supported Aspect Ratios & Formats:**
    - **Landscape (Default):** `1280×720 @ 30fps` (16:9).
    - **Vertical Reel / Shorts:** `720×1280 @ 30fps` (9:16) with top chapter/progress indicator, headline group (`top: 90–110px`), hero stage (`top: 320–780px`), bottom takeaway card (`bottom: 90–130px`), and safe zones (`top: 80–128px`, `bottom: 120–256px`).
    - **Square:** `1080×1080 @ 30fps` (1:1).
    - Only scale to 1080p or 60fps when explicitly instructed in the brief.
  - **Non-Mac hosts (e.g. Windows):** HyperFrames, FFmpeg and Kokoro may be absent. Use `studio.py validate`, `frame-review.py` and `studio.py build --dry-run`; never claim a render or loudness result that was not produced.

---

## 5. TTS & Narration Engine
- Do **not** call the legacy `/opt/homebrew/bin/kokoro-tts` script directly because it fails on `kokoro 0.9.x`'s generator return type.
- **ALWAYS** invoke the verified wrapper at `src/pipeline/tts.py`.
- **Audio Output:** 24 kHz mono PCM WAV.
- Always measure the synthesized audio's duration with `ffprobe` before coding keyframe timestamps in GSAP.
- Insert a 0.5s pause buffer (`pause.wav`) between scene audio clips to prevent abrupt speech transitions.
- Available voices: `am_adam` (default technical), `af_bella` (warm/conversational), `am_michael` (documentary), `af_sarah` (academic), `bm_george` / `bf_emma` (British academic).
- Standard speech pacing is **1.15x speed** (configurable via `--speed <float>`).

---

## 6. HyperFrames Coding Rules
- Ensure `data-width="1280"` and `data-height="720"` are set on `#root` (or `720×1280` for vertical reels, `1080×1080` for square).
- Set `data-fps="30"` and `data-duration="<seconds>"`.
- Standardize vertical canvas hierarchy: header group positioned at `top: 28px–32px`, diagram stage at `top: 145px–155px` (landscape) or vertical tiers (portrait).
- **Default Theme (Light Canvas, Warm & Contrasty Colors):** Use an off-white, warm ivory, or clean light canvas (`#FBFBFA` / `#F5F3EF` / `#F4EFE6`) by default, paired with rich, warm, vibrant, and punchy contrast accents (vermilion/terracotta, electric ultramarine, marigold amber, emerald, and charcoal typography). Light backgrounds must feel dynamic, colorful, and alive. Dark themes are strictly opt-in when requested.
- **Anti-Laziness & Visual Vitality Mandate (Zero Static Frames During Speech):**
  Narration must **NEVER** play over a frozen or static visual. When narration is active, the screen must visually evolve every 2 to 3 seconds:
  - **Multi-Beat Scene Structure:** A 15-second scene is NOT 1 visual beat; it is 3 to 5 micro-beats (anchor entrance → data development → complication/highlight → detail revelation → takeaway lock).
  - **Progressive Reveals:** Continuously reveal data, extend graph curves, increment counters, or step through timeline milestones as words are spoken.
  - **Kinetic Spoken Emphasis:** Spoken key terms must trigger instant visual feedback (highlight glow, weight shifts, callout arrows, badge stamps).
  - **Continuous Secondary Vitality:** Maintain subtle motion (signal pulses along curves, telemetry tickers, slow parallax drifts, particle streams).
- **Standard Layout & Motion Primitives (`src/studio/`):**
  - Use `Studio.comp.heroStage(parent, opts)` and `Studio.comp.splitStage(parent, opts)` instead of manual pixel-absolute containers to guarantee consistent $\ge 65\%$ stage occupancy and prevent empty voids.
  - Use `Studio.comp.monumentStat(parent, opts)` for large takeaway metrics ($>80\text{px}$ numbers, crisp labels).
  - Use `Studio.type.heroHeader(parent, opts)` to standardize hierarchy (`kicker` 14–16px, `title` 36–52px, `subtitle` 18–24px) passing WCAG AA contrast.
  - Use `Studio.type.formatCount(element, start, end, opts)` for live counter rolls.
  - Use `Studio.draw.chart.line/area(points, opts)` for smooth Catmull-Rom spline charting with auto-normalized points (`[x,y]` or `{x,y}`).
  - Use `Studio.draw.chart.gauge(parent, opts)` for circular/radial metrics and `Studio.draw.particleStream(parent, opts)` for directional liquidity/contagion particle flows.
  - Use `Studio.space.drift(target, opts)` to maintain continuous virtual camera motion (e.g. scale $1.0 \to 1.035$) during spoken explanations.
  - Use `Studio.transition(tl, type, outEl, inEl, atTime, opts)` for choreographing composable transitions (`crossfade`, `slide-left`, `slide-up`, `zoom-through`, `curtain`) with element continuity.
- Use synchronous cross-dissolves (`sceneTransition(outId, inId, atTime, fade=0.40)`) to eliminate black gaps.
- Use **GSAP 3** for timeline management. Always create the timeline with `{ paused: true }` and register it on `window.__timelines['root']`.
- **NEVER use `Math.random()` in composition scripts.** Use a seeded PRNG (such as `mulberry32`) to ensure deterministic rendering across frames.
- Run `hyperframes lint index.html` before executing renders.
- Use `hyperframes snapshot . --at <timestamps>` to visually review frames before or after rendering.

---

## 7. Multi-Track Audio-Video Assembly & External Footage
- Render video track without audio using HyperFrames with stdin redirected (`renders/visuals.mp4 < /dev/null`).
- External video clips (Veo / stock / 3D) must be ingested via `./scripts/ingest-asset.sh <file> [slug]`, which normalizes them to 1280×720 @ 30fps silent H.264 into `assets/generated/`.
- Multi-track mux audio with FFmpeg `amix` (preserving narration intelligibility with ducked SFX and dim themed background music bed):
  ```bash
  # 3-Track Multiplexing (Narration + SFX + Dim Themed Background Music Bed)
  ffmpeg -y \
    -i visuals.mp4 \
    -i narration-full.wav \
    -i sfx-track.wav \
    -i bgm.wav \
    -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[3:a]volume=0.25,afade=t=in:st=0:d=0.5,afade=t=out:st=28.5:d=1.5[a_bgm];[a_voice][a_sfx][a_bgm]amix=inputs=3:duration=first:dropout_transition=2[aout]" \
    -map 0:v -map "[aout]" \
    -c:v copy -c:a aac -b:a 192k -shortest final.mp4
  ```
- Fallback to 2-track mix if no background music is available:
  ```bash
  ffmpeg -y \
    -i visuals.mp4 \
    -i narration-full.wav \
    -i sfx-track.wav \
    -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[a_voice][a_sfx]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
    -map 0:v -map "[aout]" \
    -c:v copy -c:a aac -b:a 192k -shortest final.mp4
  ```
- Always execute `.agents/skills/video-assembler/scripts/run-qa-gates.sh` after assembly.
