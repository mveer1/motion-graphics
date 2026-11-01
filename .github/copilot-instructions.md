# Motion Lab: AI Operational Guide & Rules (VS Code Primary)

This workspace is **Motion Lab**: a reproducible, high-performance motion graphics and video production pipeline optimized for Apple Silicon macOS (8 GB Unified RAM). 

In this repository, **VS Code is the primary interactive development workstation**, while **Antigravity acts as the secondary autonomous accelerator** for deep research dossiers, batch generation, and multi-agent workflows.

---

## 1. Master Creative Directives & Invariants

### A. The Anti-Laziness & Visual Vitality Mandate (CRITICAL)
- **Zero Static Visual Freezes While Narration Speaks:** Narration must NEVER play over a frozen or static visual. The canvas must visibly evolve every 2 to 3 seconds.
- **Multi-Beat Scene Structure:** A 15-second scene is not 1 visual beat; it is 3 to 5 micro-beats:
  `Anchor entrance` $\to$ `Data development` $\to$ `Complication/Highlight` $\to$ `Detail revelation` $\to$ `Takeaway lock`.
- **Progressive Reveals:** Continuously reveal data, extend spline curves, roll counters, or highlight timeline milestones as words are spoken.
- **Kinetic Spoken Emphasis:** Spoken key terms must trigger instant visual feedback (highlight glow, typographic weight shift, callout arrow, badge stamp).
- **Continuous Secondary Vitality:** Maintain subtle motion (e.g., virtual camera drift via `Studio.space.drift`, telemetry tickers, signal pulses along curves, liquidity particle streams).

### B. Default Color Palette & Design System
- **Default Theme (Light Canvas):** Use clean, warm off-white / ivory canvas (`#FBFBFA` / `#F5F3EF` / `#F4EFE6`) by default.
- **Accents:** Pair with rich, warm, vibrant, and high-contrast accents:
  - Terracotta / Vermilion (`#E05A47` / `#D9483B`)
  - Electric Ultramarine (`#1D4ED8` / `#2563EB`)
  - Marigold Amber (`#D97706` / `#F59E0B`)
  - Emerald Forest (`#059669` / `#10B981`)
  - Charcoal Typography (`#1E293B` / `#0F172A`)
- **Dark Theme:** Strictly opt-in only when explicitly requested in the project brief.

### C. Standard Formats & Stage Hierarchies
- **Landscape (Default):** `1280×720 @ 30fps` (16:9). Header at `top: 28px–32px`, diagram stage at `top: 145px–155px`.
- **Vertical Reel / Shorts:** `720×1280 @ 30fps` (9:16). Header at `top: 90–110px`, hero stage at `top: 320–780px`, bottom takeaway card at `bottom: 90–130px`, safe zones top `80–128px`, bottom `120–256px`.
- **Square:** `1080×1080 @ 30fps` (1:1).

---

## 2. HyperFrames & GSAP 3 Coding Rules

1. **Root Attributes:**
   Set `data-width="1280"` (or format width), `data-height="720"`, `data-fps="30"`, and exact `data-duration="<seconds>"` on `#root`.
2. **GSAP Timeline Registration:**
   All animations must attach to a paused master timeline registered on `window.__timelines['root']`:
   ```javascript
   const tl = gsap.timeline({ paused: true });
   window.__timelines = window.__timelines || {};
   window.__timelines['root'] = tl;
   ```
3. **Deterministic Rendering (Zero Math.random):**
   NEVER use `Math.random()`. Use a seeded PRNG (such as `mulberry32` or `gsap.utils.random`) to guarantee identical frame-by-frame renders across runs.
4. **Studio Runtime Primitives (`src/_studio/`):**
   Compose scenes using registered studio primitives:
   - `Studio.comp.heroStage(parent, opts)` / `Studio.comp.splitStage(parent, opts)`
   - `Studio.comp.monumentStat(parent, opts)`
   - `Studio.type.heroHeader(parent, opts)`
   - `Studio.type.formatCount(el, start, end, opts)`
   - `Studio.draw.chart.line/area(points, opts)`
   - `Studio.draw.chart.gauge(parent, opts)`
   - `Studio.draw.particleStream(parent, opts)`
   - `Studio.space.drift(target, opts)`
   - `Studio.transition(tl, type, outEl, inEl, atTime, opts)`
   *Note:* Never edit `src/_studio/` directly; make edits in `src/studio/` and sync with `python scripts/studio.py formats <slug>`.

---

## 3. Audio & Narration Standards

1. **Voice Synthesis (Kokoro TTS):**
   - Output: 24 kHz mono PCM WAV via `src/pipeline/tts.py`.
   - Pacing: default 1.15x speed.
   - Voices: `am_adam` (technical), `af_bella` (warm), `am_michael` (documentary), `af_sarah` (academic).
   - Audio timeline measured with exact sub-millisecond precision via `ffprobe`.
   - Always insert 0.5s pause buffer between scenes.
2. **3-Track Multiplexing:**
   - Track 1: Voice narration (`volume=1.0`).
   - Track 2: Tactile SFX bed ducked (`volume=0.85`).
   - Track 3: Continuous dim ambient music bed (`-22` to `-28 dBFS`, ~15–20 dB below voice).
   - Prohibit transition whooshes on educational scene cross-dissolves.

---

## 4. Hardware & Memory Invariants (Apple Silicon M2 / 8 GB RAM)

- **Single Worker Only:** NEVER execute concurrent renders.
- **Low-Memory Mode:** Always pass `--low-memory-mode` to `hyperframes render`.
- **Non-Interactive Stdin Redirection:**
  Always redirect stdin with `< /dev/null` when running HyperFrames to prevent terminal hang from the interactive rating survey:
  ```bash
  hyperframes render . --fps 30 --quality looks --low-memory-mode --output ../renders/visuals.mp4 < /dev/null
  ```
- **Render Time is NOT a Constraint:** Concurrency is strictly limited, but duration is unconstrained. Do NOT hold back on visual richness, particle density, or kinetic detail out of fear of render time.

---

## 5. Available Skills & Capability Index (`.agents/skills/`)

Consult these specialized skills when crafting animations, audio, or research:

| Skill | Path | Description & Use Case |
| :--- | :--- | :--- |
| `motion-graphics-designer` | `.agents/skills/motion-graphics-designer` | Layout rules, palettes, kinetic typography, dynamic stage occupancy. |
| `gsap-core` / `gsap-timeline` | `.agents/skills/gsap-core` / `gsap-timeline` | Official GreenSock animation choreography and timeline sequencing. |
| `gsap-plugins` / `gsap-utils` | `.agents/skills/gsap-plugins` / `gsap-utils` | Flip, SplitText, SVG drawing, clamp, mapRange, Mulberry32 PRNG. |
| `kinetic-typography` | `.agents/skills/kinetic-typography` | Overflow masks, variable-font weight shifts, SplitText accessibility. |
| `epic-design` | `.agents/skills/epic-design` | 2.5D pseudo-3D parallax, 6-layer depth tokens (`data-depth="0"`–`"5"`). |
| `motion-design` | `.agents/skills/motion-design` | Disney animation principles adapted for UI, easing curves, 1/3 rules. |
| `real-sfx` | `.agents/skills/real-sfx` | Tactile foley, cue extraction from HyperFrames, mix balancing. |
| `earshot` | `.agents/skills/earshot` | Acoustic measurement (EBU R128 loudness), procedural micro-SFX synthesis. |
| `voice-director` | `.agents/skills/voice-director` | Kokoro TTS voice persona tuning, speech pacing, phonetic respellings. |
| `technical-researcher` | `.agents/skills/technical-researcher` | Stage 0 research dossiers, formula verification, visual metaphor archetypes. |
| `video-assembler` | `.agents/skills/video-assembler` | FFmpeg multiplexing, low-memory render configs, automated QA gates. |
| `workspace-steward` | `.agents/skills/workspace-steward` | 7-Domain component placement, schema audits, drift verification. |

---

## 6. VS Code Tasks & Workflow

Use VS Code's Task Runner (`Cmd+Shift+B` or `Terminal -> Run Task`):
- **Studio: Validate Project**: Validates schema conformity, format consistency, and asset links.
- **Studio: Frame Review Contact Sheets**: Generates contact sheets in `projects/<slug>/qa/frame-review/` for visual verification.
- **Studio: Build Full Project**: Executes full render, audio mix, and 5-gate automated QA.
- **Live Preview / Live Server**: Right-click `projects/<slug>/src/index.html` $\to$ **Open with Live Server** to preview and scrub the GSAP timeline in real-time in Chrome.

