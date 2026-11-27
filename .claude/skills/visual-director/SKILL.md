---
name: visual-director
description: Decide, per storyboard scene, which render engine draws it - HyperFrames (the compositor and default for type, 2D diagrams, charts, math and algorithm visuals), Three.js inside the page (stylised real-time 3D with tracked labels) or a Blender plate (photoreal light, volumetrics, simulations, cinematic cameras) - then author the plates, composite them in HyperFrames and get them rendered. Use after the story is signed off and before or while composing src/index.html, whenever a brief or storyboard asks for 3D, realism, depth, particles, fluids, fog, physics or camera moves, or when asked which engine or tool to use, whether to use Blender, Remotion, Revideo or Manim, or how to combine engines.
---

# Visual Director

You choose the cheapest engine that can carry each scene's visual job, then make the pieces fit into one HyperFrames film. You do not write the story (story-writer) or pick the style (creative-director); you decide how each planned beat gets drawn.

## The one rule

**HyperFrames is always the compositor.** Every film is one `src/index.html` rendered by `studio.py build`. Other engines only supply layers to it:

| Engine | Status | Draws | Output into the film |
|---|---|---|---|
| HyperFrames + GSAP + studio runtime | approved | type, captions, 2D diagrams, charts, maps, math as SVG, algorithm walkthroughs, UI, all text | itself |
| Three.js r158 (vendored) | experimental | stylised/toon 3D, turntables, globes, molecules, 3D charts, the 3D Tibi, labels tracking 3D anchors | a canvas inside the page |
| Blender 5.2 LTS (headless `bpy`) | experimental | physically based light (glass, caustics, subsurface), volumetrics (fog, god rays, smoke), simulations (rigid body, cloth, particles, fluids), real depth of field and motion blur, camera moves through 3D sets | a plate: `src/plates/<id>.<format>.mp4` (opaque) or `.webm` (alpha), placed as a timed `<video>` |

Not adopted (`specs/visual-engines.json` `not_adopted`, evidence `docs/visual-engines.md`): **Remotion** and **Revideo** duplicate HyperFrames (another headless-Chrome frame renderer) and stay blocked; **Manim** is `proposed` for equation-to-equation morphing only and is not installed. Math, algorithm and code visuals are HyperFrames work: SVG + GSAP, `Studio.draw.*`, the recipe catalogue.

## Procedure

1. **Read** `brief.json`, `storyboard.json` (signed off), the style template and `qa/story-review.json`. Run `python scripts/visual-director.py doctor` to see which engines this host has.
2. **Draft** `python scripts/visual-director.py plan <slug>` (prints) then `--write` (saves `visual-plan.json`, copies plate templates into `blender/`). The draft is a keyword heuristic; you decide.
3. **Decide each scene** with `references/engine-matrix.md`. Record `engine`, `mode`, a `reason` naming the visual job a cheaper engine cannot do, and `overlay` (what HyperFrames draws above a plate). When every scene is decided set `"decided_by": "director"`.
4. **Author plates** (`references/blender-plates.md`): start from a template (`visual-director.py templates`, `add-plate <slug> <id> --template ... --scene sN [--alpha]`), edit `blender/<id>.py`, look at `render <slug> --plate <id> --preview` (contact sheet in `renders/plates/<id>/<format>/preview/contact.png`). Iterate on the preview, never on full renders.
5. **Composite** (`references/compositing.md`): place each plate as `<video class="clip plate" src="plates/<id>.<primary-format>.<ext>" data-start data-duration muted playsinline>`; `studio.py formats` points each format's entry file at its own plate. Snap plate cues to spoken words (`studio.py words`).
6. **Gate**: `python scripts/visual-director.py check <slug>` and `python scripts/studio.py validate <slug>` (which runs the same checks), then `frame-review.py` / `hyperframes snapshot` at each plate's first, middle and last beat. Look at the frames: text legible over the plate, hero in the free zone, no seam at the plate's in and out.
7. **Render**: `studio.py build` renders stale plates first (stage `plates`, under the host lock), then the film. A plate whose script, kit, job or Blender version changed is re-rendered; the film re-renders because its inputs (`src/plates/`) changed.

## Rules that are not negotiable

- **No text in plates.** Words, numbers, labels and captions live in HyperFrames (sharp at every format, editable, checked by QA). The plate lint rejects text objects.
- **Deterministic plates.** Randomness only from `lab.rng()`; no wall-clock time; simulations are baked by the runner. Pin the Blender version (`specs/visual-engines.json` `blender.pinned_version`); a different version is a different plate.
- **One heavy job at a time.** `render` and `build` take the host render lock; never start Blender beside a HyperFrames render, TTS or analysis job.
- **Per-format plates, not crops.** Each format renders its own plate from one script (`lab.pick`, `fov_short`, `subject_y`), the same way the page composes per format.
- **The plate earns its cost.** A Blender plate costs minutes per scene and a second toolchain. If SVG, a gradient, `Studio.space.drift` or Three.js reads the same at delivery size, use them. Write the reason down.
- **Palette continuity.** Plates take colours by palette role from the project's style sheet (`lab.color('accent')`), rendered with the `Standard` view transform so the hex values match the page.
- **Anti-laziness still applies.** A plate is not a static backdrop: the camera drifts or moves, the subject or the light evolves every 2-3 s, and HyperFrames beats keep landing above it.
- Never edit `src/blender/` from a project; copy a template into `projects/<slug>/blender/`. Kit changes go to `src/blender/mlab.py` and re-render every plate that used it (the fingerprint does this).

## Handoffs

- Story changes (a scene needs a different job) go back to **story-writer**.
- Look and style questions go to **creative-director**; you implement within the chosen style.
- GSAP choreography of the overlay: **motion-graphics-designer**, `gsap-*`, `kinetic-typography`.
- New engines, libraries or Blender add-ons: **workspace-steward** first (`dependency-intake-check`).
- Review after the build: **motion-director**.

## References

- `references/engine-matrix.md`: the decision procedure, signals, worked examples, combination patterns.
- `references/blender-plates.md`: the `lab` API, templates, previews, render cost, determinism, troubleshooting.
- `references/compositing.md`: placing plates in HyperFrames, alpha, z-order, timing, transitions, QA.
- `docs/visual-engines.md`: the evaluation behind these choices (capabilities, licences, memory, evidence).
- `docs/explanation-devices.md`: the explanation device per narrator job (runtime 1.18.0, `studio-explain.js`). Every device there is HyperFrames DOM/SVG: equation build, slider, trace pair, simulation, bar race, progression, canvas tour, dip, copy slot, UI widgets and headlines need no plate. A storyboard scene's `device` does not change the engine decision; a plate can sit behind a device, never carry its text.
- `docs/reference-playbook.md`: transitions and motion learned from inspected reference videos, grouped by family, with the runtime API per technique and the reference moments behind it. Engine signals seen there: photoreal sun, Earth or eye shots and lit product turntables (`rendered-3d-objects`, `product-hero-turntable`) are plate work; one-take camera moves across tilted UI cards (`css-3d-staging`), blooms, zoom-throughs, container transforms, flashes and particle glyphs (`particle-assemble-glyph`, Canvas 2D) stay in HyperFrames. Object-to-object transformation chains (rings to a sphere, particles, ink) put their 3D and fluid stages on plates (`fluid-type-resolve`; `ref-19cee08f9c` 2.5-11.3 s) while the dot, line and type stay in HyperFrames; real rim light on a dark mark is plate work, a travelling glint is not (`rim-light-sweep-reveal`).
