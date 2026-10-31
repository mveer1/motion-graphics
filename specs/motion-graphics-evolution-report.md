# Motion Graphics Workspace Upgrade: Architecture & Research Report
**Stage 1: Investigation, Research, Baseline Measurement, and Implementation Plan**

> **Author:** Motion Graphics Engineering Lab  
> **Host Environment:** Apple Silicon macOS (M2, 8 GB Unified RAM), Python 3.12 / 3.14, Node.js 24.22.1, FFmpeg 9.0.2  
> **Scope:** Multi-stage upgrade from technical slideshow-style videos to professionally directed, visually engaging explainers.  
> **Status:** Stage 1 Investigation & Planning (Strictly non-destructive; zero architectural alterations in this stage).

---

## 1. Current Architecture

The production pipeline currently operates under a dual-track architecture: the **Legacy Explainer Pipeline** (`scripts/build-project.sh`) and the **Studio Multi-Format Pipeline** (`scripts/studio.py`). Both converge on an identical visual rendering and audio multiplexing stack.

```
                           ┌─────────────────────────────┐
                           │   Stage 0 & 1: Planning     │
                           │  (brief.json, storyboard)   │
                           └──────────────┬──────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼                                             ▼
       ┌───────────────────────┐                     ┌───────────────────────┐
       │   Stage 2 & 3: Audio  │                     │  Stage 4: Composition │
       │ Kokoro TTS (24kHz WAV)│                     │  HTML5 / CSS / SVG    │
       │ Measured Timeline JSON│                     │  GSAP 3 Paused Root TL│
       └───────────┬───────────┘                     └───────────┬───────────┘
                   │                                             │
                   │                                             ▼
                   │                                 ┌───────────────────────┐
                   │                                 │ Stage 6: Render Engine│
                   │                                 │ HyperFrames v0.8.223  │
                   │                                 │ (Headless Chromium    │
                   │                                 │  + ANGLE Metal GPU)   │
                   │                                 │  visuals.mp4 (H.264)  │
                   │                                 └───────────┬───────────┘
                   │                                             │
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │ Stage 8: FFmpeg Assembly│
                             │  3-Track Audio Multiplex│
                             │  (Voice + SFX + BGM Bed)│
                             └────────────┬────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │ Stage 9: Automated QA   │
                             │ run-qa-gates.sh (5-Gate)│
                             │ final.mp4 Output        │
                             └─────────────────────────┘
```

### 1.1 Tooling & Engine Inventory

| Tool / Component | Verified Version | Installation Path | Actual Role in Workspace |
| --- | --- | --- | --- |
| **HyperFrames** | `0.8.223` | `/opt/homebrew/bin/hyperframes` | **Active Primary Renderer.** Orchestrates headless Chromium via CDP, evaluates `window.__timelines`, steps GSAP frame-by-frame, and renders MP4/WebM with hardware GPU acceleration. |
| **Revideo CLI** | `0.11.0` | `/opt/homebrew/bin/revideo` | **Installed but Inactive.** Fork of Motion Canvas; requires TypeScript/React compilation and JSX templates. Currently not wired into project scaffolding or build scripts. |
| **FFmpeg / ffprobe** | `9.0.2` | `/opt/homebrew/bin/ffmpeg` | Audio duration measurement, multi-track multiplexing (`amix`), loudness normalisation (EBU R128), and black-gap detection. |
| **Kokoro TTS** | `0.9.x` (PyTorch) | `src/pipeline/tts.py` (via `.venv`) | Speech synthesis generating 24 kHz mono PCM WAV narration clips. |
| **GSAP (GreenSock)** | `3.12.x` | `src/studio/` & CDN bundle | Core tweening, timeline sequencing, and procedural animation engine. |
| **Studio Runtime** | `1.0.0` | `src/studio/` (`src/_studio/` per project) | Deterministic helpers: format handling, seeded PRNG (`mulberry32`), SVG manipulation, transitions, and audio sync. |

---

## 2. Identified Root Causes

Detailed empirical inspection of `projects/china-market-crash-v2` and `projects/china-market-crash-v3` reveals five interrelated failure modes that transform what should be cinematic explainers into static slideshows.

### 2.1 Excessive Empty Space (The "Shrinking Island" Problem)
* **Measurement:** 
  * Total portrait canvas: $720 \times 1280\text{ px} = 921,600\text{ px}^2$.
  * Declared safe insets: Top $128\text{ px}$ (10%), Bottom $256\text{ px}$ (20%), Left $43\text{ px}$ (6%), Right $72\text{ px}$ (10%).
  * Usable safe area: $605 \times 896\text{ px} = 542,080\text{ px}^2$ (**only 58.8% of canvas**).
  * In Scene 1, `.stage-viewport` is constrained to $489.6\text{ px}$ height, and `.phone-mock` is sized to $345.6 \times 460.8\text{ px}$ ($159,252\text{ px}^2$).
  * **Result:** The primary visual anchor occupies **only 17.3% of the canvas area**, leaving **82.7% of the screen as dead empty space**.
* **Root Cause:** 
  1. Compounding margins: safe-area padding on the scene root, combined with container viewport margins, combined with internal card padding.
  2. Over-conservative compliance with automated linters (`frame-review.py`) which penalise safe-zone intrusions, prompting defensive shrinkage.
  3. Lack of full-bleed framing, background atmosphere, or multi-layered environmental depth.

### 2.2 Undersized Typography (The "Desktop SaaS" Trap)
* **Measurement:** 
  * Although `specs/format-presets.json` defines a text floor of $2.6\%$ of the short side ($18.72\text{ px}$ for $720\text{p}$ portrait), `china-market-crash-v3/src/index.html` contains **12 distinct font-size declarations below this floor**:
    * Kicker tags / micro-indicators: $7.9\text{ px}$ ($1.1\%$), $8.6\text{ px}$ ($1.2\%$), $10.8\text{ px}$ ($1.5\%$).
    * Telemetry & captions: $11.5\text{ px}$ ($1.6\%$), $13.0\text{ px}$ ($1.8\%$), $15.8\text{ px}$ ($2.2\%$).
    * Over $60\%$ of all typography rules in the project violate the legibility floor.
    * The main scene title is capped at $40.3\text{ px}$ ($5.6\%$ of short side).
* **Root Cause:** 
  1. The compositions were styled like responsive web applications viewed on a 27-inch desktop monitor rather than motion videos viewed on handheld mobile screens.
  2. Absence of kinetic typographic hierarchies (e.g. hero words at $64\text{ px} - 96\text{ px}$, dynamic word-by-word reveal masks).

### 2.3 Repetitive Dashboard-Based Compositions
* **Measurement:** 
  * In both v2 and v3, every single scene ($S_1, S_2, S_3, S_4$) follows an identical layout archetype:
    * Centered header group (`kicker` pill badge + `main-title` + muted subtitle).
    * Centered `.stage-viewport` enclosing a rounded card (`border: 1px solid rgba(0,0,0,0.08)`, `border-radius: 12px`, white background).
    * Scene 1: phone mockup card. Scene 2: tremor card + radial gauge card. Scene 3: split card + order book card. Scene 4: bailout barrier card + monument card.
* **Root Cause:** 
  1. The template and composition helpers (`studio-compositions.js`) prioritize UI widgets (`frameHud`, `itemList`, `callout`) over motion-graphic storytelling.
  2. Absence of cinematic visual metaphors (e.g., liquidity waterfalls, collapsing structures, kinetic typography monuments, domino runs, volumetric depth).

### 2.4 Weak Transitions (The Hard-Cut Slideshow)
* **Measurement:** 
  * Across the entire 66-second video, transitions between scenes are exclusively implemented via:
    ```javascript
    S.cut(tl, '#s1', '#s2', cue('s2')); // instantaneous 1ms switch
    S.cut(tl, '#s2', '#s3', cue('s3'));
    S.cut(tl, '#s3', '#s4', cue('s4'));
    ```
  * Zero spatial transitions, zero match cuts, zero camera pans/wipes.
* **Root Cause:** 
  1. Misinterpretation of the sound-design guideline in `AGENTS.md` ("Prohibit Transition Whooshes") as an instruction to avoid visual transitions altogether.
  2. Available motion primitives in `src/studio/studio-motion.js` (`FX.wipe`, `FX.iris`, `FX.push`, `FX.liquid`, `FX.matchCut`, `SP.camera`) were never invoked in the composition timelines.

### 2.5 Poor Motion Continuity and Pacing
* **Measurement:** 
  * Elements enter with brief $0.4\text{s} - 0.6\text{s}$ tweens at the beginning of each beat, after which the canvas enters long stretches of near-total visual freeze ($3\text{s} - 8\text{s}$) while narration plays.
  * Timeline events are strictly tied to macroscopic scene bounds ($t = 0\text{s}, 17.65\text{s}, 33.25\text{s}, 50.025\text{s}$) rather than continuous narrative progression.
* **Root Cause:** 
  1. Lack of continuous secondary vitality (no camera drift, no ambient flow, no rhythmic pulse).
  2. Animation is not choreographed to the syllabic cadence or semantic emphasis of the spoken narration.

---

## 3. Existing Capabilities to Reuse

The workspace already possesses a rich foundation of audited tools and libraries. **No new software dependencies or engine replacements are required.**

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EXISTING REUSABLE STACK                         │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Runtime Engine           │ HyperFrames v0.8.223 (Chromium + Metal GPU) │
│ Choreography Core        │ GSAP 3.12 (Timelines, Tweens, CustomEase)   │
│ Camera & Spatial Motion  │ `src/studio/studio-motion.js` (SP.camera)   │
│ Cinematic Transitions    │ `FX.wipe`, `FX.iris`, `FX.push`,            │
│                          │ `FX.matchCut`, `FX.liquid`, `FX.bloom`      │
│ Kinetic Typography       │ `src/studio/studio-type.js` (T.split,       │
│                          │  T.rise, T.cascade, T.fit, T.highlight)    │
│ Procedural Drawing       │ `src/studio/studio-draw.js` (D.stroke,      │
│                          │  D.morph, D.pen, D.particles, D.drift)      │
│ Deterministic PRNG       │ `Studio.rng` (Mulberry32 seeded PRNG)       │
│ Multi-Track Audio Mux    │ FFmpeg 9.0.2 (Voice + SFX + BGM Ducking)    │
│ Acoustic Verification    │ Earshot 0.1.0 (`earshot measure`)           │
│ Production CLI           │ `scripts/studio.py`                         │
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

## 4. Proposed Implementation Changes

To transition from "technical slideshows" to "professionally directed explainers", the following architectural shifts must be implemented in the composition authoring layer:

```
SLIDESHOW PARADIGM (CURRENT)            DIRECTED EXPLAINER PARADIGM (PROPOSED)
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Centered Title (Small)      │        │  BLEED HERO TYPOGRAPHY       │
│                              │        │  (Masked Kinetic SplitText)  │
│  ┌────────────────────────┐  │        │  ══════════════════════════  │
│  │ Dashboard Card Box     │  │  ───►  │  FULL-CANVAS METAPHOR STAGE │
│  │ (Tiny 10px telemetry)  │  │        │  (Dynamic SVG Illustration,  │
│  └────────────────────────┘  │        │   Continuous Camera Drift,   │
│                              │        │   Match-Cut Transitions)     │
│  [Instant Hard Cut to Next]  │        │  ══════════════════════════  │
└──────────────────────────────┘        └──────────────────────────────┘
```

1. **Full-Bleed Stage Design (Eradicating the Empty Box):**
   * Eliminate artificial container boxes (`.phone-mock`, `.card`, `.tremor-card`).
   * Visual elements must scale to occupy $70\% - 85\%$ of the active canvas.
   * Safe areas must protect interactive UI overlays (captions, top handles) without artificially compressing background graphics, depth textures, or ambient environmental layers.
2. **Kinetic Display Typography:**
   * Enforce a hard typographic minimum: Display titles $\ge 54\text{ px}$ ($7.5\%$ of short side), Section kickers $\ge 22\text{ px}$ ($3.0\%$), and body/telemetry $\ge 24\text{ px}$ ($3.3\%$).
   * Implement masked split-text word reveals using `Studio.type.split` and `Studio.type.rise`.
   * Synchronize keyword highlights and weight shifts with spoken voice cues.
3. **Active Virtual Camera System:**
   * Utilize `Studio.space.camera(tl, '#stage', at, { scale, x, y, duration, ease })` to establish continuous, deliberate camera moves throughout each scene.
   * Subtle push-ins ($1.00 \to 1.06$) during dramatic revelations, slow lateral tracking across complex charts, and macro cut-aways.
4. **Cinematic Spatial Transitions:**
   * Ban `Studio.cut` on primary scene boundaries.
   * Deploy **Match Cuts** (`FX.matchCut`): transform a focal point from Scene $N$ (e.g., the needle of a liquidation gauge) directly into the focal anchor of Scene $N+1$ (e.g., a plummeting trendline).
   * Deploy **Directional Push & Clip-Path Wipes** (`FX.wipe`, `FX.push`) with easing curves that maintain kinetic momentum across scenes.
5. **Continuous Vitality Mandate:**
   * Implement secondary ambient vitality (subtle floating drift, rhythmic data stream updates, breathing glows) so that zero frames remain frozen while narration speaks.

---

## 5. Relevant Research Findings

### 5.1 HyperFrames Engine Evaluation
* **Rendering Architecture:** HyperFrames v0.8.223 operates on an embedded Headless Chromium engine utilizing Apple Silicon ANGLE Metal hardware GPU acceleration.
* **Timeline Contract:** HyperFrames polls `window.__timelines[compositionId]`. When a paused GSAP timeline is registered, HyperFrames advances the timeline deterministically frame-by-frame (`tl.seek(frameTime)`), ensuring exact frame reproducibility independent of wall-clock render speed.
* **Fast Capture Support:** Supports `--experimental-fast-capture` via Chrome's `drawElementImage` API, which directly extracts DOM paint records (~2x faster than screenshot capture).

### 5.2 Revideo Evaluation
* **Findings:** Revideo CLI v0.11.0 is installed globally on the macOS host. However:
  * Revideo relies on a completely different paradigm (Motion Canvas TSX/React generator functions) requiring external compilation, Vite bundlers, and package dependencies.
  * HyperFrames natively supports HTML5, CSS3, procedural SVG, Canvas 2D, and GSAP 3 with zero build steps and full multi-format compatibility (`portrait`, `landscape`, `square`).
* **Conclusion:** Replacing or compounding HyperFrames with Revideo is technically unnecessary, adds heavy tooling complexity, and offers no visual capability beyond what GSAP 3 + SVG natively delivers.

---

## 6. Performance Considerations for 8 GB Apple Silicon M2

Empirical benchmarking was executed on the host system to establish real-world memory and rendering limits:

### 6.1 Empirical Benchmark Results (5-Second Render Slice)
* **Command:** `hyperframes render . --fps 30 --quality looks --low-memory-mode --start 0 --end 5`
* **Elapsed Time:** $17.41\text{s}$ total ($\sim 10.0\text{s}$ browser launch / DOM stabilization + $1.48\text{s}$ per video second).
* **Peak RSS Memory:** **$410.4\text{ MB}$** (Chromium process + Node runner).
* **Memory Safety Headroom:** Peak consumption of $\sim 410\text{ MB}$ leaves $> 7.0\text{ GB}$ of Unified RAM untouched, completely eliminating memory crash risks.
* **Extrapolated Full Render (66-Second Video):** $\sim 105\text{s} - 115\text{s}$ ($\sim 1.8\text{ minutes}$).

### 6.2 Host Invariants
1. **Low-Memory Invariant:** Always pass `--low-memory-mode` to pin Chrome to 1 worker and avoid parallel process thrashing.
2. **Non-Interactive Stdin Invariant:** Always redirect stdin (`< /dev/null`) to prevent interactive rating prompts from hanging execution.
3. **Render Time Is Not a Constraint:** Render duration of $1.5 - 3\text{ minutes}$ is completely acceptable on Apple Silicon M2. Agents must never compromise visual richness or animation complexity out of fear of render time.

---

## 7. Baseline Measurements (China Market Crash 66s Video)

| Metric | Measured Fact vs Judgment | china-market-crash-v2 | china-market-crash-v3 | Target Direction |
| --- | --- | --- | --- | --- |
| **Resolution** | Measured Fact | $720 \times 1280$ (9:16) | $720 \times 1280$ (9:16) | $720 \times 1280$ (9:16) |
| **Duration** | Measured Fact | $66.000\text{s}$ | $66.000\text{s}$ | $66.000\text{s}$ |
| **Frame Rate** | Measured Fact | $30.0\text{ fps}$ | $30.0\text{ fps}$ | $30.0\text{ fps}$ |
| **Container Size** | Measured Fact | $3.99\text{ MB}$ | $5.30\text{ MB}$ | $4.5 - 6.5\text{ MB}$ |
| **Overall Bitrate** | Measured Fact | $483.7\text{ kbps}$ | $642.0\text{ kbps}$ | $600 - 800\text{ kbps}$ |
| **Integrated Loudness** | Measured Fact | $-17.0\text{ LUFS}$ | $-16.9\text{ LUFS}$ | $-16.0 \pm 1\text{ LUFS}$ |
| **Loudness Range (LRA)**| Measured Fact | $2.3\text{ LU}$ | $3.4\text{ LU}$ | $3.5 - 5.5\text{ LU}$ |
| **Black Screen Gaps** | Measured Fact | $0$ frames | $0$ frames | $0$ frames |
| **Render Peak RSS** | Measured Fact | $\sim 410\text{ MB}$ | $\sim 410\text{ MB}$ | $< 600\text{ MB}$ |
| **Min Text Size** | Measured Fact | $8.6\text{ px}$ ($1.2\%$) | $7.9\text{ px}$ ($1.1\%$) | $\ge 24\text{ px}$ ($\ge 3.3\%$) |
| **Max Title Size** | Measured Fact | $54.7\text{ px}$ ($7.6\%$) | $60.5\text{ px}$ ($8.4\%$) | $72 - 96\text{ px}$ ($10 - 13\%$) |
| **Hero Stage Occupancy**| Measured Fact | $14.8\%$ of canvas | $17.3\%$ of canvas | $65 - 85\%$ of canvas |
| **Scene Transitions** | Measured Fact | 3 hard cuts (`S.cut`) | 3 hard cuts (`S.cut`) | 3 spatial match/push cuts |
| **Visual Variety** | Visual Judgment | Low (all card widgets) | Low (all card widgets) | High (cinematic metaphors) |
| **Motion Continuity** | Visual Judgment | Low (slide-like steps) | Low (slide-like steps) | High (camera drift & flow) |

---

## 8. Phased Implementation Plan

```
┌────────────────────────────────────────────────────────────────────────┐
│                        UPGRADE ROADMAP (PHASED)                        │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE 1: Layout & Typographic Overhaul                                 │
│  • Expand hero stage from 17% to 75%+ canvas occupancy                │
│  • Enforce 24px minimum font-size floor; 64px+ kinetic display titles  │
│  • Strip restrictive card containers in favor of full-bleed elements   │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE 2: Virtual Camera & Spatial Transitions Choreography            │
│  • Implement SP.camera continuous drift (push-ins, pans, reframes)     │
│  • Replace instant S.cut with FX.matchCut, FX.wipe, and FX.push        │
│  • Eliminate static visual freezes between narration cues             │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE 3: Visual Metaphor Redesign & Secondary Vitality                 │
│  • Re-engineer Scene 1-4 assets into expressive visual metaphors       │
│  • Introduce ambient particle drift, dynamic grid flows, and pulses   │
│  • Word-level SplitText synchronization with narration emphasis       │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE 4: Full Assembly, Verification & Creative QA                     │
│  • Execute full 66s render and 3-track audio multiplex                 │
│  • Verify 5 technical QA gates via run-qa-gates.sh                    │
│  • Generate snapshot matrix and complete creative review audit         │
└────────────────────────────────────────────────────────────────────────┘
```

### Detailed Phase Tasks

* **Phase 1: Layout & Typographic Overhaul**
  * Remove container-within-container wrappers (`.phone-mock`, `.card-panel`) that squeeze graphics into tiny boxes.
  * Redesign typography scale for mobile portrait reels: Title ($64 - 84\text{ px}$), Subtitle ($28 - 34\text{ px}$), Metrics ($36 - 54\text{ px}$), Badges / Captions ($22 - 26\text{ px}$).
  * Implement masked character/word entrances (`Studio.type.rise`, `Studio.type.split`) with clean overflow clipping.

* **Phase 2: Virtual Camera & Spatial Transitions Choreography**
  * Bind `#stage` to `Studio.space.camera`, choreographing slow push-ins during critical data reveals ($0.0 - 17.6\text{s}$, $17.6 - 33.2\text{s}$).
  * Replace the 3 hard cuts at $17.65\text{s}$, $33.25\text{s}$, and $50.025\text{s}$ with:
    * Cut 1 ($17.65\text{s}$): Match-cut zoom expanding the portfolio into the macro liquidity gauge.
    * Cut 2 ($33.25\text{s}$): Downward momentum push transition into the cascading order-book void.
    * Cut 3 ($50.025\text{s}$): Directional wipe shattering the rescue barrier into the final $-\$2.4\text{T}$ monument.

* **Phase 3: Visual Metaphor Redesign & Secondary Vitality**
  * Replace dashboard cards with metaphorical motion design:
    * *Scene 1 (Euphoria):* Towering procedural candlestick pillars that outgrow the frame.
    * *Scene 2 (The Trap):* Mechanical vise / liquidity drain curve constricting collateral.
    * *Scene 3 (The Stampede):* A surging waterfall of retail sell orders overpowering a collapsing bid barrier.
    * *Scene 4 (The Reckoning):* Volumetric crumbling monument stat ($-\$2.4\text{T}$) holding with steady cinematic dignity.
  * Implement micro-animations every $1.5 - 2.5\text{s}$ to guarantee zero static freezes during speech.

* **Phase 4: Full Assembly, Verification & Creative QA**
  * Execute full-duration render via `scripts/studio.py build china-market-crash-v3`.
  * Verify QA Gates 1–5: $720 \times 1280$, $30\text{ fps}$, $66.000\text{s}$, integrated loudness $-16 \pm 2\text{ LUFS}$, zero black frames.
  * Run `frame-review.py` snapshot matrix to visually verify text legibility, contrast, and layout balance.
  * Score `qa/creative-review.json` with visual frame evidence.

---

## 9. Acceptance Criteria for Final Explainer Video

The upgraded video must satisfy both technical and directorial criteria before sign-off:

1. **Composition & Layout:**
   * Hero graphical elements must occupy $\ge 65\%$ of the active canvas width/height.
   * Zero artificial "card within card" desktop containers.
   * Total background dead space must not exceed $30\%$.
2. **Typography & Readability:**
   * Absolute minimum font size: $\ge 22\text{ px}$ ($3.0\%$ of short side) for any on-screen text.
   * Scene titles must be $\ge 54\text{ px}$ ($7.5\%$ of short side) and legible on a mobile phone screen from $1\text{ meter}$.
   * Display headlines must use kinetic reveals (masked rise or split stagger), never simple raw opacity pops.
3. **Transitions & Spatial Continuity:**
   * Zero hard visual cuts (`Studio.cut`) on major scene transitions.
   * All scene transitions must use spatial continuity (match-cuts, camera push, directional wipes, or morphs).
   * Transitions must remain sonically clean (no cheesy cartoon whooshes, preserving narrative voice clarity).
4. **Motion Continuity & Pacing:**
   * Anti-Laziness Mandate: No visual freezes exceeding $2.0\text{ seconds}$ while narration is active.
   * Continuous camera movement (subtle drift, zoom, or pan) across all major narrative beats.
5. **Technical & Audio Quality:**
   * Exact resolution: $720 \times 1280$ at $30\text{ fps}$.
   * Exact duration: $66.000\text{s} \pm 0.15\text{s}$.
   * Integrated loudness: $-16.0 \pm 1.5\text{ LUFS}$ with true peak $< -1.0\text{ dBTP}$.
   * Zero dropped frames or black screen flashes.
   * Peak rendering RSS memory $< 650\text{ MB}$ on the 8 GB M2 host.

