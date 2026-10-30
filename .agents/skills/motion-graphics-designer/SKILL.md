---
name: motion-graphics-designer
description: Motion graphics design system and animation guidelines for technical and scientific explainers using HyperFrames, SVG, and GSAP 3.
---

# Motion Graphics Designer Skill

This skill governs the aesthetic direction, layout system, and animation choreography for technical video productions.

## Quick References & Examples

- **Motion Library Guide & Capability Catalogue:** Consult [`motion-library-guide`](../motion-library-guide/SKILL.md) and run `python3 scripts/motion-catalogue.py search` to select approved capability recipes and check dependency approval states.
- **Color Palettes:** Read [`references/palettes.md`](./references/palettes.md) for calibrated technical hex values (Dark Tech, Cyber Cyan, Quantum Violet).
- **GSAP Animation Patterns:** Read [`references/gsap-patterns.md`](./references/gsap-patterns.md) for crossfades, traveling signal dots, dashed strokes, and clipPath curves.
- **Reference Template:** Inspect [`examples/scene-template.html`](./examples/scene-template.html) for a complete starter composition.

---

## 1. Visual Hierarchy & Design System

### A. The 720p/1080p Canvas Grid
- Standard resolution: `data-width="1280"` and `data-height="720"` on `#root`.
- Safe margin: 80px horizontal padding, 60px vertical padding.
- Centered elements must use explicit CSS `transform: translate(-50%, -50%)` or flexbox containers.

### B. Typography Rules
- Main font: `'SF Pro Display', 'Helvetica Neue', 'Segoe UI', Arial, sans-serif`.
- Math/Code font: `'SF Mono', 'JetBrains Mono', 'Menlo', monospace`.
- High letter-spacing on uppercase labels (`0.06em` to `0.08em`).

---

## 2. Animation Rules

1. **Paused Root Timeline:** Always construct with `{ paused: true }` and mount to `window.__timelines['root']`.
2. **Absolute Timestamps:** Always anchor tweens using exact timestamps calculated from narration audio durations.
3. **Seamless Cross-Dissolves:** Use synchronous crossfades to avoid dipping into black:
   ```javascript
   function sceneFade(outId, inId, at, fade = 0.5) {
     tl.to(`#${outId}`, { opacity: 0, duration: fade, ease: 'power1.inOut' }, at - fade / 2);
     tl.to(`#${inId}`,  { opacity: 1, duration: fade, ease: 'power1.inOut' }, at - fade / 2);
   }
   ```
4. **Continuous Secondary Motion:** Avoid static holds exceeding 2 seconds while speech continues. Add traveling signal pulses, subtle edge glimmers, or marching dashed strokes (`strokeDashoffset`).
5. **Deterministic PRNG:** NEVER use `Math.random()`. Use a seeded generator (e.g. `mulberry32`) so renders produce identical frames across runs.
6. **Capability Catalogue & Dependency Vetting:** Never import unapproved or blocked libraries (e.g. Anime.js). Query the Motion Library Guide (`python3 scripts/motion-catalogue.py search`) to select verified recipes and check approval states before authoring custom effects.
