# Compositing plates in HyperFrames

## Placing a plate

```html
<section class="st-scene" id="s1">
  <!-- Blender plate (visual-plan.json s1-plate): the runtime seeks it; never play() or tween its time. -->
  <video class="clip plate" id="s1-plate" src="plates/s1-plate.portrait.mp4"
         data-start="0" data-duration="4.4" muted playsinline></video>
  <div class="st-split-copy" id="s1-copy"></div>
</section>
```

```css
.plate { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
#s1-copy { position: relative; z-index: 2; }
```

- `src` names the plate for the **primary** format. `studio.py formats` rewrites `plates/<id>.<format>.<ext>` in every generated `index.<format>.html` to that format's own plate, and `validate` fails when an entry file is stale.
- `data-start` / `data-duration` equal the plan's `start_sec` / `duration_sec` (`check` warns when they drift by more than a frame). Time the `<video>` or its wrapper, never both.
- HyperFrames owns the playhead: never call `play()`, `pause()` or set `currentTime`. The studio lint rejects `.play(`.
- Plates are silent (`muted`); sound comes from the SFX and music tracks.
- Opaque plates are `.mp4` (H.264). Alpha plates are `.webm` (VP9 with alpha); HyperFrames reads their alpha in the browser and its layout check measures text hidden under a transparent `<video>`.

## Paint order

| Layer | z-index | Holds |
|---|---|---|
| scene background | 0 | the section's paper colour (hidden under a `plate-full`) |
| plate (`plate-full`, `plate-under`) | 0-1 | the Blender film |
| HyperFrames stage | 2-5 | diagrams, charts, SVG, Three.js canvas |
| plate (`plate-over`, alpha) | 6 | objects, particles, fog in front of the stage |
| text, labels, captions | 10+ | always on top; never under a plate |

Never use a negative `z-index` for a plate (HyperFrames' lint explains why: it can vanish behind the root background).

## Legibility over a plate

- Design the plate with the text's place in mind: `subject_y` and `lab.pick` keep the hero out of the title zone per format, and keep the area behind body text low in detail and contrast (the cyclorama, a defocused background).
- If the text still fights the plate, add a HyperFrames scrim (a gradient from `--c-paper` at 0.0-0.85 opacity) under the copy, not a darker plate.
- Captions use their preset's backing plate (`docs/caption-design.md`); the `caption_lane` rule still holds.

## Timing

- Snap plate motion to narration: `python scripts/studio.py words <slug> "the phrase"` gives film seconds; subtract the plate's `start_sec` and put it in the plan's `cues`; the script reads `lab.cue('name')`.
- HyperFrames beats above the plate keep their own GSAP timeline; land a callout on the frame the plate's motion settles (for example the `settle` cue of `hero-orbit`).
- Give a plate 0.3-0.5 s of extra length at both ends when it cross-fades (`Studio.transition`), so the dissolve never shows a frozen first or last frame.

## Transitions in and out of a plate

- Cut on motion: end the plate scene during the camera move, start the next scene with a matching direction (`match-cut`, `push-transition`).
- Cross-fade the section that holds the plate (the `<video>` fades with its parent); do not tween the video element itself.
- Palette continuity: the plate's set colour (`paper-2` by default) should match the next scene's background, so the cut reads as one space.

## QA

- `python scripts/visual-director.py check <slug>`: plan, scripts, lint, renders, `<video>` tags.
- `python scripts/studio.py validate <slug>`: the same checks, as `visual plan:` lines.
- Look at frames: `hyperframes snapshot . --at <plate start + 0.5>,<middle>,<end - 0.3> --output <dir> < /dev/null` (under `session-guard.py run render --`), or `frame-review.py`. Verified 2026-11-24: HyperFrames 0.8.226 seeks an H.264 plate frame-accurately under DOM text, and hides it after `data-duration`.
- After the build, `motion-qa.py project <slug>` treats the plate like any other footage: a static-hold flag over a plate usually means the plate's camera does not move enough.
