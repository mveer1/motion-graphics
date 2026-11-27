# Blender plates: authoring, previewing, rendering

A plate is a Python script, `projects/<slug>/blender/<plate-id>.py`, that defines `build(lab, job)`. The runner (`src/blender/run_plate.py`) starts Blender headless with factory settings, empties the scene, applies the job's render settings, calls `build`, bakes any simulation and renders PNG frames; `visual-director.py` encodes them into `src/plates/<id>.<format>.mp4|webm` and stamps the result.

## The plan entry

```json
{ "id": "s1-plate", "script": "blender/s1-plate.py", "template": "hero-orbit", "scene": "s1",
  "start_sec": 0, "duration_sec": 4.4, "alpha": false, "engine": "eevee", "samples": 16,
  "cues": { "settle": 1.0 }, "params": { "shape": "torus", "material": "glass", "arc_deg": 30 } }
```

- `start_sec` / `duration_sec`: film time of the plate (its `<video>` gets the same `data-start` / `data-duration`). Plate time starts at 0.
- `alpha`: `true` renders a transparent film (VP9 WebM with alpha); required for `plate-over`.
- `engine`: `eevee` (default, fast, rasterised with good volumetrics and soft shadows), `cycles` (path-traced: true caustics, glass, shadow catchers on alpha plates; several times slower), `workbench` (flat previews only).
- `cues`: named moments in plate seconds, read with `lab.cue(name)`. Fill them from `studio.py words <slug> "<phrase>"` minus `start_sec`, so the motion lands on the spoken word.
- `params`: free parameters the script reads with `lab.param(name, default)`.
- `formats`: optional subset; by default every format in `project.json` gets its own render.

## The `lab` API (src/blender/mlab.py)

| Area | Calls |
|---|---|
| Time | `lab.f(t)` seconds → frame; `lab.duration`, `lab.fps`, `lab.frames`; `lab.cue(name, default)` |
| Format | `lab.format`, `lab.width`, `lab.height`, `lab.aspect`, `lab.pick(landscape=, portrait=, square=)` |
| Randomness | `rng = lab.rng(salt)` → seeded `random.Random`; never the `random` module functions |
| Params | `lab.param(name, default)`, `job` (the whole job dict) |
| Colour | `lab.color('accent')` → linear RGBA from the style sheet's `--c-accent`; any `#hex` also works |
| Materials | `lab.material(name, color, roughness, metallic, transmission, ior, emission, emission_strength, coat)`, `lab.glass()`, `lab.emissive()`, `lab.assign(obj, mat)` |
| Geometry | `lab.primitive('sphere'|'ico'|'cube'|'cylinder'|'cone'|'torus'|'plane', ...)`, `lab.mesh_object(name, verts, faces)`, `lab.bevel(obj)` |
| Set | `lab.world(color, strength)`, `lab.cyclorama(color)` (seamless sweep, no horizon), `lab.floor(color)`, `lab.fog(density, color, anisotropy, extent, center)` (a haze box, never a world volume) |
| Light | `lab.light(kind, name, location, energy, color, size, target)`, `lab.studio_lights(target, scale, key, rim)` |
| Camera | `lab.camera(location, target, fov_short, dof_focus, fstop, subject_y)`, `lab.motion_blur(shutter)` |
| Animation | `lab.key(obj, 'location', [(t, value), ...], ease='expo.out')` (GSAP ease names), `lab.orbit(cam, center, radius, height, start_deg, end_deg, ease=)`, `lab.on_frame(fn)` (pure function of plate time, for many objects) |
| Simulation | `lab.particles(emitter, count, ...)`, `lab.rigid(obj, kind, mass, ...)`, `lab.rigid_world()` |

`fov_short` is the field of view across the frame's **short** side, so the subject keeps its size relative to `--u` in every format. `subject_y` lifts the subject by a fraction of the frame height with a lens shift (no perspective change): put the hero in the zone the page layout leaves free (portrait: title and copy usually sit in the lower half, so `subject_y` around 0.2).

## Templates (`templates/blender/plates/`, `visual-director.py templates`)

| Template | Job | Key params |
|---|---|---|
| `hero-orbit` | a hero object on a seamless studio sweep, slow camera arc, real DOF | `shape`, `material` (glass, satin, metal, clay), `color`, `arc_deg`, `subject_y`, `behind` (bars that glass refracts); cue `settle` |
| `particle-field` | seeded glowing motes in depth, camera push, shallow focus | `count`, `colors`, `glow`, `push`, `background`; cue `gather` |
| `rigid-collapse` | a block stack toppled by a falling weight (baked rigid-body physics) | `rows`, `cols`, `block_color`, `accent_every`; cue `impact` |
| `light-shafts` | diagonal sun shafts through a slatted ceiling into haze, onto a lit pillar; dark until the reveal | `density`, `beam_color`, `strength`, `slats`, `sweep_deg`, `subject`; cue `reveal` |

Copy one with `add-plate`, then edit the copy. A template that proves itself in a shipped film can be improved in `templates/` (and the kit in `src/blender/`), never inside a project's `_studio/`.

## Iterate on previews

```bash
python scripts/visual-director.py render <slug> --plate <id> --preview          # every 6th frame, half size, 8 samples
# look at projects/<slug>/renders/plates/<id>/<format>/preview/contact.png and frames/
python scripts/visual-director.py render <slug> --plate <id> --format portrait  # one format, full quality
python scripts/visual-director.py render <slug>                                  # every stale plate, every format
```

Read the contact sheet like a storyboard: is the hero where the layout leaves room, does something evolve every 2-3 s, are highlights clipped, does the last frame hold well for the cut?

## Determinism and staleness

- The stamp (`renders/plates/<id>/<format>/stamp.json`) holds a fingerprint of the kit, the script, the job (size, fps, duration, palette, params, cues, seed, engine, samples) and the Blender version. `render` skips a plate whose fingerprint matches; a change anywhere re-renders it, and the film re-renders because `src/plates/` changed.
- `lab.rng()` is seeded from the plate id (or `seed` in the plan). Particle systems and Cycles take the same seed. Simulations are baked before rendering, so previews that skip frames see the same physics.
- `check` rejects: module-level `random`, `numpy.random`, wall-clock time, text objects, and `bpy.ops.render` in a script. It warns when a script sets size, fps or frame range itself.

## Cost and memory

- First render of a session compiles shaders (about 40-70 s on EEVEE). Later frames: about 2.9 s per 720x1280 frame at 16 EEVEE samples on an Intel Iris Xe (measured 2026-11-24); the M2's Metal backend has not been measured yet.
- Keep scenes modest on the 8 GB host: under about 1 M polygons, no 4K textures, particle counts in the low thousands, fluid domains small. Mantaflow fluids and high-resolution smoke are `resource-constrained`: bake at low resolution or fake them.
- Never run plate renders in parallel; `render` waits in the host queue like any other heavy job.

## Troubleshooting

- Glass looks milky or grey instead of refracting (EEVEE): Blender 4.2+ refracts only with `use_raytrace_refraction` on the material and ray tracing on the scene. `lab.material(..., transmission>0)` and `lab.glass()` set both; a hand-made material must too. Glass also needs something behind it to bend (`hero-orbit`'s `behind` bars).
- Everything is black once fog is added: a **world** volume in EEVEE 4.2+ is infinite and absorbs all sun and world light. `lab.fog()` therefore fills a box (`extent`, `center`); keep the camera and the light's path inside it, and end the box below any occluder the beams come through.
- Light shafts read as an even glow: the sheets of light are seen face-on. Turn the occluder (slats, blinds, leaves) so the sheets run along the view axis and light from the side; `use_volumetric_shadows` (set by `lab.fog()`) makes the occluders cut the haze.
- `render` exits with a frame-count mismatch: read `renders/plates/<id>/<format>/blender.log` (the full Blender output).
- Colours look washed out: something set a view transform other than `Standard`, or a colour was given in sRGB to a socket directly; use `lab.color()`.
- Black frames on an alpha plate: the subject is outside the camera or behind the cyclorama; EEVEE hides the floor/sweep on alpha plates (no shadow catcher), Cycles turns it into a shadow catcher.
- `bpy` API differences between Blender versions: the kit uses version-tolerant socket and action helpers (`_set_input`, `_fcurves`). Upgrade the pinned version only with a re-render of every plate and a look at the sheets.
