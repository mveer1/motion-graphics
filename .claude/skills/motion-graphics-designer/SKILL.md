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
  - Bottom safe zone: `--safe-bottom` is 23.4 % of the height (300 px at 720×1280, since 2026-11-05; it was 20 %), which clears the reel app's caption, handle and share stack. Text you position yourself must respect it too: `motion-qa` notes any text below the line (`platform-ui-zone`).
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

### E. Review of the three newest portrait films (2026-11-03): what to repeat, what to fix
Evidence: `out/<slug>-portrait.mp4` frames at 2 s spacing, `motion-qa`, `earshot critique --fast`, ffmpeg loudness. Nothing was re-rendered; the audio was measured, not listened to.

**Repeat (worked):**
- **Data as the picture, then reuse it.** Korea's 1 tile = 1 system waffle grid (647 tiles) carries "96 burned / 551 shut down" as area, and the same grid returns for recovery (6 % → 17 % → 89 % → 98 %). Fridge uses one 4 °C / −18 °C tile grid that heats to ~50 °C and returns cooled at the end. One reusable object, changing state, beat a new graphic per sentence.
- **Bookend motif.** Cloud opens and closes on the phone and cloud; fridge opens and closes on the tile grid; Korea closes on a folder and its copy plus a title card. The ending reads as designed.
- **Hook with an object in the first second, and a sound with it.** Cloud (phone) and fridge (tile grid) show the hero at frame 0; first sound lands at 0.12–0.28 s in all three (limit 0.58 s). Korea opens on 0.33 s of flat field (`flat-frame` warning); start its grid already drawn or fading in from frame 1.
- **Diegetic bed.** Fridge's bed is a compressor hum that cuts out when the first tile warms and returns when the grid cools. Prefer a bed that follows the story over a generic drone.
- **Honest labelling.** "Illustrative", "reports differ", "unconfirmed", per-frame source lines. This suits the accuracy half of the quality bar.

**Fix next time:**
- **Label size.** Cloud has 21 text-size-floor warnings (12.5–17 px labels against a floor of 2.6 % of the short side = 18.7 px at 720 wide), mostly timeline and map labels. Its own review scored readability 3 and shipped. Below the floor, cut the label or split the beat; do not shrink the type.
- **Collisions confirmed in the frames:** cloud 5 s, the phone's lower edge touches the "WHERE IT LIVES" kicker; cloud map, the "DELHI" tag sits on its node and route lines; fridge 33 s, the dotted leader runs through the word "ONLINE" in "2,765 EXPOSED ONLINE". Leader lines must stop at a label's box, and a kicker needs 16 px clear of the art above it.
- **Echo.** Captions in cloud repeat 100 % of the narration (s1) and fridge headlines 82–83 %. A caption band is a legitimate repeat (waive it); a headline that restates the voice wastes the strongest text slot. Use the headline for the claim the voice does not say (the number, the contrast, the date).
- **Same layout five times.** `repeat-layout-dom` fired in all three (cloud 5 of 6 scenes, fridge 4 of 6, Korea 3 of 6). Vary the hero's position or scale between scenes; a recurring grid is fine when its state changes, a recurring empty stage is not.
- **Low occupancy.** Every scene sampled sat at 3–11 % content coverage by the detector. The portrait safe area is deliberately empty at the bottom (23.4 % = 300 px since 2026-11-05; 20 % when this was measured), so enlarge the hero into the 65 % band above it, or declare `intent: minimal`.
- **The film's last 4–6 s.** Cloud and Korea hold the last frame for about 4 s after the narration ends, which is fine for a source line or title card, but the picture must still move slightly. Fridge's last 3.3 s were frozen.

---

### F. Craft rules adopted from reel and HyperFrames guidance (2026-11-05)

Source and limits: `docs/short-form-lessons.md`. Each rule is a starting value; the ones marked (checked) have a lead in `motion-qa` or `studio.py script`.

- **Ease is emotion.** Enter on `.out`, leave on `.in`, move between positions on `.inOut`. Vary eases and speeds across a scene and a film; do not default every tween to `power2.out` at 0.4 s. (checked)
- **Build, breathe, resolve.** Roughly 30% of a scene builds (staggered entrances), 40% breathes (content visible with one ambient motion), 30% resolves (a decisive end; exits are faster than entrances).
- **Choreography is hierarchy.** The element that moves first reads as most important: stagger by importance, overlap entries, keep a whole stagger under about 0.5 s.
- **Transitions are meaning.** Crossfade says "this continues", a hard cut says "wake up", a slow dissolve says "drift with me". Do not crossfade everything; keep hard cuts for disruption and register shifts. The transition is the exit: do not fade a scene out and then fade the next one in.
- **Offset the first move.** Start a scene's first entrance 0.1 to 0.3 s after the cut. (checked)
- **Frames are not pages.** Two focal points at least, three layers (background treatment, content, accent), anchor to edges, hero text at 60 to 80% of the width in portrait. A background is never empty: hairline rules, oversized faded type, a panel.
- **One element, one transform owner.** Do not run two tweens on the same property of one element at once; put the second on a parent or child wrapper. (checked)
- **Never embed a raw flat image.** Give it motion treatment: a slow zoom of 1.0 to 1.04, a perspective tilt, a device frame or a clipped scroll reveal.
- **Data in motion** (also in the `data-ledger` template, v2): no pie or dual-axis charts, at most three related metrics at once, no legend box (label the series where it is drawn), faint gridlines only at labelled values, a proportional visual beside every number, and keep successive figures for one concept in one visual space.
- **Show the noun on the word.** The picture lands on the frame its word is spoken and shows the literal thing named; get the frame from `audio/words.json` (`studio.py words`). Use real proportions: capture or draw the real thing and scale it uniformly rather than inventing a condensed card with inflated type.
- **Captions for reels:** 1 to 3 word phrases from `studio.py captions --timing words --grouping phrase`, rendered with `Studio.comp.captions`, which lights the word being spoken in `--c-caption-hl` (default: the style's `--c-accent-3`; `{highlight: false}` turns it off), never ending on a weak word ("the", "to", "had"), kept above the platform interface band (`platform-ui-zone`), and never over a face or the hero. On-screen cards are 6 words or fewer (checked by the `news-brief` and `storybook` templates for portrait-first films).
- **Where these disagree with each other.** The HeyGen guidance wants glows, ghost type and 2 to 5 decoratives per scene; the reel-editing guidance bans glows, sheens and pulse rings. `editorial-light` is closer to the second: crisp entrances (4 to 8 frames, strong ease-out, 2 to 4 frame stagger) and a clean hold. Pick per style system; do not mix both.

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
   - **Evidence that this mandate is not being met (Nov 2026).** `motion-qa` flagged static or low-energy stretches under speech in the three newest films: cloud-physical-infrastructure-india 20 stretches (41 s of 70), fridge-hack-europe 15 (44 s of 92), south-korea-data-center-fire 14 (79 s of 98, longest 12 s). None of the three calls `Studio.space.drift`, `Studio.comp.*`, `Studio.type.*` or `Studio.draw.*`; each hand-codes 620–730 lines and only registers through `Studio.build`.
   - **Give every scene a drift layer.** Wrap each scene's art group in one slow `fromTo` scale or pan for the scene's whole measured duration (`Studio.space.drift`, or `tl.fromTo(art, { scale: 1 }, { scale: 1.03, duration: sceneDur, ease: 'none', immediateRender: false }, sceneStart)` with the transform origin on the focal point). The detector counts a slow drift as alive (lag energy 0.9–1.9) and a frozen picture as 0.06–0.10, so this converts most 2–3 s "frozen" notes into passes. Not yet re-rendered to confirm.
   - **Audit gaps before the first render, per scene.** List each scene's visual event times against `audio/timeline.json` sentence onsets and flag any gap over 2 s. The same dead-air failure was recorded for polya-recurrence and repeated here, so a memory note was not enough; do it as a written table, not by eye.
   - **Small-area changes do not count.** In Korea, the 1-tile = 1-system grid changed a few tiles per beat; the changing area was 4–11 % of the frame. When the hero is a grid or a map, add a second moving layer (a counter, a travelling dot, a label sweep) so the frame as a whole changes.
   - **The two longest holds are the closing scene and the "answer" scene.** Fridge s6 (5.2 s + 5.4 s) and Korea s5/s6 (8.1 s, 3.8 s) carry the film's point on the least motion. Spend the hardest visual work there.
5. **Deterministic PRNG:** NEVER use `Math.random()`. Use a seeded generator (e.g. `mulberry32`) so renders produce identical frames across runs.
6. **Capability Catalogue & Dependency Vetting:** Never import unapproved or blocked libraries (e.g. Anime.js). Query the Motion Library Guide (`python3 scripts/motion-catalogue.py search`) to select verified recipes and check approval states before authoring custom effects.
