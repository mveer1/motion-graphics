# Engine matrix: which engine draws a scene

Decide per scene, from the scene's **visual job** (what the viewer must see), not from its subject. A chart about water is a chart; a glass lens whose refraction is the point is light transport.

## Decision procedure

Ask in order; stop at the first yes.

1. **Is the job words, numbers, a 2D diagram, a chart, a map, a timeline, an equation, code, an algorithm step or UI?** → `hyperframes`, `native`.
2. **Is it 3D that must stay stylised (flat, toon, low-poly), carry labels that track 3D points, or change whenever the composition changes?** → `threejs`, `native` (a canvas in the page; `catalogue/data/libraries/threejs.json`).
3. **Does it need light transport, volume, simulation or a real lens?** Glass, caustics, subsurface skin or wax, fog and god rays, smoke or fire, a liquid pour, cloth, objects that fall and collide, a camera flying through a 3D set with true depth of field or motion blur. → `blender`, a plate.
4. **None of the above clearly?** → `hyperframes`. Fake depth with `Studio.space.drift`, `depth-layer`, `parallax-camera`, gradients and grain before reaching for a plate.

Cost check before choosing Blender: a 4-5 s portrait plate at 720x1280 with EEVEE took 6.4 min on an Intel Iris Xe laptop GPU (2026-11-24); Cycles is several times slower. On the M2 the order is similar. If the plate is on screen under 2 s or under heavy overlay, it rarely pays.

## Modes for a Blender scene

| Mode | Plate | HyperFrames above it | Use for |
|---|---|---|---|
| `plate-full` | opaque, fills the frame | titles, captions, small labels | hooks, establishing shots, product hero, environment fly-through |
| `plate-under` | opaque or alpha behind the stage | the diagram or chart is the hero; the plate is atmosphere | a chart over a lit set, data over a particle field |
| `plate-over` | **alpha** (VP9 WebM) above some DOM layers, below the text | text and key labels | an object or particles in front of a diagram, fog drifting across a map |

A scene may use several plates (a backdrop plus an alpha object). Keep it to two; more is a sign the scene wants to be a Blender shot with HyperFrames only for type.

## Routing signals (the heuristic draft)

`visual-director.py plan` scores `specs/visual-engines.json` `routing.signals` against the scene's title, visual, layout, beats, capabilities and asset refs:

- **Treatment terms** (always count, weight 2): photoreal, cinematic lighting, volumetric, god rays, caustics, subsurface, depth of field, bokeh, motion blur, fly-through, simulation, rigid body, shatter, collapse, product hero...
- **Subject terms** (weight 1, ignored when the scene names a 2D form such as chart, diagram, equation, map): fog, smoke, fire, water, pour, cloth, glass, refraction, terrain, planet, galaxy...
- **Form terms** (HyperFrames, weight 1): chart, graph, diagram, equation, code, algorithm, timeline, map, table, counter, label...

Cheapest engine wins ties; a non-HyperFrames engine needs a score of at least 2. Treat the draft as a list of questions: read every scene, and write the `reason` yourself.

## Worked examples

| Storyboard visual | Decision | Why |
|---|---|---|
| "A photoreal glass torus turns on a studio set; the camera dollies around it with depth of field." | blender, `plate-full`, `hero-orbit` (glass) | refraction and a real lens are the point |
| "A ray diagram: the light path bends through the glass, with labelled angles." | hyperframes, native | the diagram is the explanation; glass is the subject |
| "A chart of refractive index for water, glass and diamond." | hyperframes, native | a chart (form term vetoes the subject terms) |
| "A rotating molecule with atoms labelled as each is named." | threejs, native | stylised 3D + tracked labels |
| "Banks fall like dominoes as the crisis spreads." | blender `rigid-collapse` under HyperFrames bank names, or hyperframes with `drop-bounce` if the film is flat-styled | physics reads as consequence; choose by the style template |
| "Millions of transactions drift past as glowing points." | blender `particle-field` (`plate-under`) with a HyperFrames counter on top; or `Studio.draw.particleStream` for a flat style | depth and glow vs. flat streams |
| "Dawn light breaks through the window as the title appears." | blender `light-shafts` (`plate-full`) + HyperFrames title | volumetric light |
| "Binary search narrows the array step by step." | hyperframes, native | an algorithm walkthrough |

## Combination patterns

- **Blender establishes, HyperFrames explains.** Open on a plate (hook), cut or cross-fade to a native diagram for the mechanism, return to the plate world for the payoff. Match the palette so the cut reads as one film.
- **Plate as a living backdrop.** A slow camera drift or particle field under a chart keeps the frame alive during long narration (the anti-laziness rule) without competing with the data: keep it dim and low-contrast where text sits.
- **Object over diagram.** An alpha plate of a real object (a cell, a coin, a chip) sitting in a HyperFrames diagram, with SVG callouts pointing at it. Freeze the object's position at the callout times so the arrows land.
- **Three.js for labels, Blender for beauty.** When labels must track a moving 3D model, keep the model in Three.js; use a Blender plate only for the environment behind it.

## When to say no

- Brief asks for "3D" but the style template is flat (`editorial-light` explainer, `proof-canvas`): propose isometric SVG or Three.js toon first.
- The plate would sit under a dense chart: a gradient and grain will read the same at phone size.
- The host has no Blender and the deadline is near: `doctor` says so; plan HyperFrames-native and note the scene for a later plate.
