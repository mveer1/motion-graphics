---
name: motion-graphics-designer
description: Creative direction, design system and animation guidelines for short motion pieces (explainers, promos, kinetic typography, how-tos, title sequences) in 16:9, 9:16 and 1:1 using HyperFrames, SVG, GSAP 3 and the studio runtime; also covers legacy technical explainers.
---

# Motion Graphics Designer Skill

This skill governs the aesthetic direction, layout system, and animation choreography for technical video productions.

## 0. Studio Projects (read first)

For any project with `project.json` (see `ARCHITECTURE.md` section 0):
- **Work in order:** brief (objective, audience, formats) → 1-3 distinct directions (style system, motion personality, composition approach) → choose and record why → storyboard with catalogue capabilities and meaningful transitions → layout per format → execution → frame review → creative review.
- **Light first (Default Theme):** default style `editorial-light` or light themes (off-white, warm ivory, clean cream `#FBFBFA` / `#F5F3EF` / `#F4EFE6`) with warm, rich, vibrant, high-contrast colors (vermilion/terracotta, electric ultramarine, marigold amber, emerald, deep charcoal ink). Light backgrounds must feel dynamic, colorful, and alive. Dark palettes (`cinematic-dark`, `dark-tech`) are strictly opt-in only when the brief explicitly requests them.
- **Anti-Laziness Mandate:** The framework must NOT be lazy. Hardware warnings on Apple M2 constrain concurrency and worker count only; **render time is not a concern**. Never freeze frames or cut animations to save render time. Narration must never play over a static visual.
- **Use the runtime, not one-off code:** `Studio.comp.*` compositions, `Studio.type/draw/fx/space/rhythm/texture` effects (`src/studio/`). Search before writing: `python scripts/motion-catalogue.py search "<intent>" --type effect`.
- **Learn from references, then make it original:** before writing directions run `python scripts/motion-catalogue.py recommend --brief projects/<slug>/brief.json` (or `--text`) for techniques, components and reference precedents. Combine principles from several references; never reuse a reference's logo, characters, footage, copy or shot sequence. Record what you used in `brief.references[].technique_ids` (checked by `studio.py validate`, which warns when a technique is only observed or specified). Example: `projects/paper-plane-field-notes` combines word beats, element blooms, a frame HUD, a step tracker, shape morphs, margin callouts and a pen-led path.
- **Compose each format:** size with `--u` (1 % of the short side) and `--safe-*`; adapt with `#root[data-format="portrait"]` rules and `Studio.pick`. Never hard-code 1280×720 in a studio project.
- **Inspect frames:** run `scripts/frame-review.py <slug>` and look at the contact sheets; automated passes are not creative approval.

The sections below remain the rules for legacy technical explainers.

## Quick References & Examples

- **Motion Library Guide & Capability Catalogue:** Consult [`motion-library-guide`](../motion-library-guide/SKILL.md) and run `python3 scripts/motion-catalogue.py search` to select approved capability recipes and check dependency approval states.
- **GSAP AI Skills:** Use official GreenSock skills ([`gsap-core`](../gsap-core/SKILL.md), [`gsap-timeline`](../gsap-timeline/SKILL.md), [`gsap-plugins`](../gsap-plugins/SKILL.md), [`gsap-utils`](../gsap-utils/SKILL.md), [`gsap-performance`](../gsap-performance/SKILL.md)) for tween syntax, position parameter choreography, and transform optimizations.
- **Motion Design Principles:** Consult [`motion-design`](../motion-design/SKILL.md) for Disney animation principles adapted to UI, timing/easing tables, hero element staging, and 1/3 rules (motion distance $\le 33\%$, max 3 simultaneous dynamic elements).
- **Algorithmic Art:** Consult [`algorithmic-art`](../algorithmic-art/SKILL.md) when authoring generative canvas visuals, flow fields, or mathematical sketches.
- **Color Palettes:** Read [`references/palettes.md`](./references/palettes.md) for calibrated technical hex values (Dark Tech, Cyber Cyan, Quantum Violet) used by legacy explainers; studio projects take colours from their style system (`src/studio/styles/`).
- **GSAP Animation Patterns:** Read [`references/gsap-patterns.md`](./references/gsap-patterns.md) for crossfades, traveling signal dots, dashed strokes, and clipPath curves.
- **Reference Template:** Inspect [`examples/scene-template.html`](./examples/scene-template.html) for a complete starter composition.

---

## 1. Visual Hierarchy & Design System

### A. The 720p/1080p Landscape Canvas Grid (16:9)
- Standard resolution: `data-width="1280"` and `data-height="720"` on `#root`.
- Safe margin: 80px horizontal padding, 60px vertical padding.
- Canvas hierarchy: header group positioned at `top: 28px–32px`, diagram stage at `top: 145px–155px`.
- Centered elements must use explicit CSS `transform: translate(-50%, -50%)` or flexbox containers.

### B. Vertical Reel / Shorts Layout Grid (720×1280 @ 30fps, 9:16)
- Dimensions: `data-width="720"` and `data-height="1280"` on `#root`.
- Vertical Tiers:
  - Progress / Chapter Segment indicator: `top: 32px`, height `3px`.
  - Headline Group (kicker + title + subtitle): `top: 90px–110px`.
  - Hero Stage / Data Visualization Viewport: `top: 320px–780px`.
  - Takeaway Badge / Key Principle Card: `bottom: 90px–130px`.
- Safe Areas: Respect Instagram Reels / TikTok / YouTube Shorts UI overlays:
  - Top safe zone: `top: 80px–128px` (clears account header/status bar).
  - Bottom safe zone: `bottom: 120px–256px` (clears captions, caption overlay, share/like icon stack).
- Light Theme Standards: `#FBFBFA` or `#F4EFE6` canvas, frosted glass cards (`background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(0, 0, 0, 0.08)`), high-contrast charcoal typography (`#111827` or `#1E1B16`), and warm punchy accents.

### C. Typography Rules
- Display font: `'Playfair Display', serif` or `'SF Pro Display', 'Helvetica Neue', Arial, sans-serif`.
- Math/Code font: `'SF Mono', 'JetBrains Mono', 'Menlo', monospace`.
- High letter-spacing on uppercase labels (`0.06em` to `0.16em`).

### D. Standard Reusable Studio Primitives (`src/studio/`)
Always leverage the canonical studio primitives in `src/studio/` rather than re-inventing one-off CSS or manual pixel offsets:
1. **Composition Stages (`studio-compositions.js`):**
   - `Studio.comp.heroStage(container, { header, visual, takeaway, direction })`: Centers and balances visual content, ensuring $\ge 65\%$ frame utilization and eliminating accidental voids.
   - `Studio.comp.splitStage(container, { ratio: '50-50', direction: 'auto' })`: Side-by-side comparison in landscape, vertical stacked in portrait/square.
   - `Studio.comp.monumentStat(container, { number, label, subtext, format })`: Monumental focal statistics ($>80\text{px}$ numbers, animated rolls via `Studio.type.formatCount`).
2. **Typography Primitives (`studio-type.js`):**
   - `Studio.type.heroHeader(container, { kicker, title, subtitle })`: High-contrast, WCAG AA compliant responsive header.
   - `Studio.type.punch(container, text, { size, tone, transform })`: Kinetic punchy typography callouts.
   - `Studio.type.formatCount(element, start, end, { duration, ease, format })`: Deterministic counter roll.
3. **Procedural Draw Primitives (`studio-draw.js`):**
   - `Studio.draw.chart.line(points, { stroke, strokeWidth, tension })`: Catmull-Rom smooth spline curve; accepts both `[x,y]` and `{x,y}` point structures.
   - `Studio.draw.chart.area(points, { fill, baselineY })`: Area fill under spline curve with gradient support.
   - `Studio.draw.chart.gauge(container, { value, max, radius, color })`: Radial liquidation/status gauge.
   - `Studio.draw.particleStream(container, { count, path, color, speed })`: Seeded flow particles representing financial volume, liquidity, or contagion.
4. **Camera & Transitions (`studio-motion.js` & `studio-core.js`):**
   - `Studio.space.drift(target, { scale: 1.035, duration, ease: 'none' })`: Virtual cinematic camera drift preventing visual freeze.
   - `Studio.transition(tl, type, outEl, inEl, atTime, { duration, ease })`: Composable transitions (`crossfade`, `slide-left`, `slide-up`, `curtain`, `zoom-through`) with continuous visual anchor.

---

## 2. Animation Rules & The Anti-Laziness Mandate

1. **Paused Root Timeline:** Always construct with `{ paused: true }` and mount to `window.__timelines['root']`.
2. **Absolute Timestamps:** Always anchor tweens using exact timestamps calculated from narration audio durations (`audio/timeline.json`).
3. **Seamless Cross-Dissolves:** Use synchronous crossfades to avoid dipping into black:
   ```javascript
   function sceneFade(outId, inId, at, fade = 0.5) {
     tl.to(`#${outId}`, { opacity: 0, duration: fade, ease: 'power1.inOut' }, at - fade / 2);
     tl.to(`#${inId}`,  { opacity: 1, duration: fade, ease: 'power1.inOut' }, at - fade / 2);
   }
   ```
4. **Anti-Laziness Mandate (Zero Static Frames During Speech):**
   - The framework must NOT be lazy. **Render time is not a concern** — never hold back on visual richness or animation frequency to speed up rendering.
   - Narration must **NEVER** speak over a static, frozen screen. Every spoken phrase or 2–3 seconds must be accompanied by visual evolution:
     - **Multi-Beat Staging:** A 12–16 second scene is 3 to 5 micro-beats, not 1 entrance tween followed by a static freeze.
     - **Progressive Data Tracing:** Continuously draw curves, animate gauges, step indicators, and increment counters as numbers are spoken.
     - **Kinetic Spoken Emphasis:** Spoken terms must trigger visual feedback (callout badges pop, keyword glows, underline strokes, node pulses).
     - **Camera & Focus Shifts:** Subtle scale drifts (`scale: 1.05`), focus pans, or depth transitions keep long explanations cinematic.
   - Static holds exceeding 2 seconds while speech continues are strictly prohibited.
5. **Deterministic PRNG:** NEVER use `Math.random()`. Use a seeded generator (e.g. `mulberry32`) so renders produce identical frames across runs.
6. **Capability Catalogue & Dependency Vetting:** Never import unapproved or blocked libraries (e.g. Anime.js). Query the Motion Library Guide (`python3 scripts/motion-catalogue.py search`) to select verified recipes and check approval states before authoring custom effects.
