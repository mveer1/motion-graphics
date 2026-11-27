# Scene recipes: the mythic kit in a composition

Load after the studio runtime:
```html
<script src="_studio/kits/mythic/mythic.js"></script>
```
and build inside `Studio.build(function (tl, f, S) { var M = S.kit.mythic; ... })`. The working example is `templates/projects/mythic-film/src/index.html`; the self-test exercising every call is `tests/mythic-kit/index.html`.

## 1. The piece model (read this first)
Every visual builder returns a **piece** `{el, art, body}`:
- `el` (div): position; free for travel moves you write yourself (`tl.fromTo(piece.el, {x: ...}, ...)`).
- `art` (svg): entrances and exits (`place`, `rise`, `lift`, `haloIn`).
- `body` (g): ambient life (`breathe`, `sway`, `turn`).

Three nested elements means three tweens can run at once without fighting over one transform. Put pieces in **stage layers** and move the camera with `Studio.space.camera(tl, stage.el, at, {scale, x, y, duration})` for parallax; never tween the layer element yourself.

Colours are tokens (`'--c-accent'`) or literals. Every mythic style defines the same token contract (paper, ink, accents, `--c-gold`, `--c-gold-light`, `--c-lamp`, `--c-malachite`, `--c-sky`, `--c-lotus`, `--c-saffron`, `--c-peacock`, `--c-night`, `--c-leather-red|ochre|green|blue`), so switching style never breaks a film; outside the mythic styles the kit falls back to the core tokens.

## 2. API
| Call | Returns / does |
|---|---|
| `M.stage(parent, {ground, fibre})` | `{el, ground, layer(depth 0-5)}` paper ground with fibre |
| `M.lamp(parent, {x, y, radius, vignette, color})` | lamp glow and vignette; `M.flicker(tl, lamp, from, to, {fps, amount, seed})`; `M.lampTo(tl, lamp, at, {x, y, duration})` |
| `M.tint(tl, parent, from, to, {color, blend, amount, fade})` | palette swap for a threat or grief |
| `M.sheet(parent, {shape, x, y, w, h, fill, deckle, seed, shadow, stroke, d, ...})` | cut paper: `rect hills peaks waves clouds disc niche arch flames lotus` (+ `peaks`, `crests`, `puffs`, `tongues`, `petals`, `thickness`, `spring`, `pointed`); `d` takes a traced silhouette path instead |
| `M.plate(parent, {src, x, y, w, h, frame, duotone, border, fit})` | photo plate: `rect niche disc cutout` |
| `M.halo(parent, {x, y, r, kind, rays, fill})` | `nimbus prabhavali mandorla sun`; `.gold` is its gradient for `glint` |
| `M.border(parent, {tradition, motif, band, inset, ground, color})` | tradition preset or one of `M.motifs`; `M.borderIn(tl, border, at)` |
| `M.frieze(parent, {panels, visible, w, h})` / `M.friezeTo(tl, fr, at, index)` | strip of panels that travels panel to panel |
| `M.registers(parent, {rows, order})` | stacked bands, `top-down` (folio) or `bottom-up` (picture stone) |
| `M.panelsIn(tl, panelsOrLayout, at, {from, stagger})` | reveal panels or registers in reading order |
| `M.doors(parent, {x, y, w, h, fill})` / `M.open(tl, doors, at, {duration, angle})` | kaavad doors |
| `M.scroll(parent, {x, y, w, h, content})` / `M.unroll(tl, scroll, at, {from})` | phad scroll |
| `M.puppet(parent, {figure, look, h, x, y, parts, rods})` / `M.cutout(...)` | jointed figure (section 3); `look`: `silhouette leather paper painted` |
| `M.pose(tl, p, at, {part: deg}, {duration, steps})` | rotate joints from their pivots; `steps: true` moves on twos |
| `M.cartouche(parent, {kicker, title, plate})` / `M.cartoucheIn(tl, c, at)` | "As told in" source label |
| `M.title(parent, {kicker, title, sub, top, plate})` / `M.titleIn(tl, t, at)` | invocation or teaching title, word by word |
| `M.credit(parent, text)` | image credit line at the text floor, above the bottom safe area |
| `M.gold(w)` / `M.glint(tl, url, at)` | gold-leaf gradient and its shine |
| `M.place`, `M.lift`, `M.rise`, `M.haloIn`, `M.turn`, `M.breathe`, `M.sway` | motion (section 1 says which element each moves); `place` and `sway` take `steps` |
| `M.stepped(ease, duration, fps)` | an ease that updates `fps` times a second, for any tween ("on twos" = 12) |
| `M.shower(tl, parent, from, to, {count, kind: 'petal'|'ember', colors})` | blossoms or embers |

## 3. Figure library (`kits/mythic/figures.js`)
Load after `mythic.js`. Every figure is built on one skeleton, so the same pose works on all of them.

| Id | Tradition | Emblems drawn | Layout |
|---|---|---|---|
| `rama` | indian | bow, arrows, quiver, tall crown, dark skin | standing, profile |
| `hanuman` | indian | mace, tail, monkey face, crown | standing, profile |
| `shiva` | indian | trident, damaru, crescent, serpent, matted locks, tiger skin | standing, profile |
| `ganesha` | indian | elephant head, broken tusk, modak, axe, noose, mouse on the pedestal | seated, frontal |
| `athena` | greek | crested helmet, spear, round shield, aegis | standing, profile |
| `odin` | norse | one eye, wide hat, cloak, spear, two ravens | standing, profile |
| `tirthankara` | jain | meditation, shrivatsa, triple umbrella, lanchhana in the pedestal (`figureOptions: {emblem: 'lion' (Mahavira) | 'bull' | 'deer' | 'conch' | 'snake'}`) | seated, frontal |
| `buddha` | buddhist | earth-touching gesture, ushnisha, robe, lotus seat | seated, frontal |

- Standing part ids: `pelvis`, `leg-back`, `leg-front`, `garment`, `torso`, `arm-back`, `hand-back`, `head`, `arm-front`, `hand-front`, plus attributes (`crown`, `prop-front`, `prop-back`, `tail`, `quiver`, `locks`, `serpent`, `helmet`, `ravens`...). Seated figures pose only gently (`head`, arms; never a Tirthankara).
- A leap (from the samples): `pose({torso: 16, 'arm-front': 30, 'arm-back': -20}, {steps: true})` to crouch, then `pose({'arm-front': -165, 'arm-back': -150, 'leg-front': -14, 'leg-back': 22})` and tween `piece.el` along an arc with a rotation.
- **Builds:** every figure has a `classic` build (default) and a `heroic` build on the same joints, so the same pose works on both: `puppet({figure: 'hanuman-heroic'})` or `figureOptions: {build: 'heroic'}` (`M.heroicIds`). Heroic means the classical ideal of the traditions' own sculpture: broad shoulders, deep chest, narrow waist, defined arms, quads and calves, abdominal lines only on bare torsos. Bounded by iconography: Ganesha keeps his belly (Lambodara, 'pot-bellied'); the Tirthankara and the Buddha get the smooth 'lion-like' torso of the classical image, never ripped; Athena is athletic and never sexualised. Compare: `python tests/mythic-kit/render-figures.py` writes `figures-compare.png` (classic paper, heroic paper, heroic leather).
- `p.meta` gives `{name, tradition, emblems, check, build}` for the label and the iconography gate.
- These are stylised storytelling figures, not icons; a tradition reviewer still signs off gate 2. Missing so far: Krishna, Devi/Durga, Vishnu, Thor, Loki, Zeus; add them with `M.geom.tube`, `M.glyphs` and `M.props` on the same skeleton.
- Review sheets: `python tests/mythic-kit/render-figures.py` (every figure in every look, every motif, a frieze, registers and a leap pose).

### Human build (`kits/mythic/figures-human.js`)
Load after `figures.js`. Front-view figures drawn as believable people on one proportion grid (8 heads; landmarks in `figure-design.md` section 3), with faces, hair, dress, ornament and two-tone lamp-side shading, each set from an identity block in `figure-design.md` section 4. Best in the new `look: 'illustrated'` (base, shading layers, ink outline last, a lifted shadow); `paper` and `painted` keep the layers; `silhouette` shows the outline alone.

| Id | Options | Layout |
|---|---|---|
| `rama-human` | `tone: 'blue'` (default) \| `'brown'`; `attire: 'forest'` (default: jata, bark cloth, no jewels) \| `'royal'` (kirita, yellow silk, jewels) | standing, front |
| `hanuman-human` | `form: 'veera'` (default: mace, raised hand) \| `'dasa'` (anjali, no mace) | standing, front |
| `shiva-human` | | standing, front |
| `ganesha-human` | `tone: 'red'` (default, the Atharvashirsha) \| `'gold'` | seated, front |
| `athena-human` | | standing, front |
| `odin-human` | | standing, front |
| `tirthankara-human` | `emblem` as `tirthankara`; `sect: 'digambara'` (default) \| `'svetambara'` | seated, front |
| `buddha-human` | | seated, front |

- `puppet(stage.layer(3), {figure: 'rama-human', figureOptions: {tone: 'brown'}, look: 'illustrated', h, x, y})`; standing viewBox 400 x 820, seated 400 x 640 (same head and torso, so a seated and a standing figure share a ground line when scaled by 820 and 640).
- Part ids (r = the figure's own right, the viewer's left): `pelvis`, `leg-r`, `leg-l`, `torso`, `girdle`, `arm-r`, `fore-r`, `hand-r`, `arm-l`, `fore-l`, `hand-l`, `head`, `hair`, plus attributes (`bow`, `arrow`, `quiver`, `jata`, `crown`, `gada`, `tail`, `trishula`, `damaru`, `cobra`, `spear`, `shield`, `aegis`, `helmet`, `hat`, `beard`, `raven-r`, `raven-l`, `trunk`, `ears`, `chhatra`, `halo`...). Ganesha's raised arms are `arm2-r`, `fore2-r`, `hand2-r` and the same on the left. Pose gently: `pose(tl, p, at, {'fore-r': -20, head: 3})`.
- `M.human.ids` lists them; `M.human.parts` exposes the body, head, hand, dress and ornament builders and `M.human.geom` the Bezier, mirror and muscled-limb helpers for new figures. Every figure has `meta.build: 'human'` and `meta.view: 'front'`; three-quarter, profile and back views come next on the same landmarks (`figure-design.md` section 5).
- Review sheet: `tests/mythic-kit/figures-human.html` (`?ids=rama-human:tone=brown,hanuman-human:form=dasa&cols=4&H=760&pad=110`), rendered with the others by `render-figures.py` (`--ids <ids> [--look silhouette]` for one sheet).
- **Heroic build** (2026-11-24): Rama, Hanuman, Shiva, Ganesha, Athena and Odin are drawn heroic (muscle as cel shapes, a wide stance, the head scaled about the chin, an iconic pose, one wind) with an aura first in the part list: parts `aura`, `aura-rays`, `aura-ring` (kept in every look; turn the rays with `M.turn(tl, p.part('aura-rays'), t0, t1, {degrees: 20})`). Weapons are parts placed from the armoury: `bow`, `arrow`, `quiver` (Rama), `gada` (Hanuman), `trishula` and its child `damaru` (Shiva), `ankusha`, `pasha` (Ganesha), `spear`, `shield` (Athena), `spear` (Odin). Extra parts: `uttariya`, `himation`, `cloak`, `raven-r`, `raven-l`, `ruff`, `tail`.

### Armoury (`kits/mythic/armoury.js`)
Load after `figures-human.js`. `M.weapons.<id>(opts)` returns a drawing at its grip pointing up; `M.weapons.place(spec, {id, parent, at, angle, scale, flip, behind})` returns parts (the drawing moved by `tf`). Ids: `M.weapons.ids` (kodanda, shara, tuna, gada, trishula, damaru, ankusha, pasha, parashu, chakra, shankha, vajra, khadga, venu, padma, dory, aspis, gungnir, mjolnir, keraunos). `M.auras.make(kind, {cx, cy, r})` returns the aura parts (kinds `M.auras.kinds`). A weapon on its own, for a scene: `M.puppet(stage.layer(3), {figure: {viewBox: [200, 800], parts: M.weapons.place(M.weapons.gada(), {id: 'gada', at: [100, 600]})}, look: 'illustrated', h, x, y})`. New figures, weapons and auras: the `mythic-figure-designer` skill.

## 4. Tradition presets
`M.traditions` sets the border motif and colours and says whether the tradition puts haloes on its gods.

| Tradition | Motifs (first is the default) | Halo |
|---|---|---|
| `indian` | `lotus`, `pattachitra`, `ruled` | `prabhavali` |
| `jain` | `ruled`, `beads`, `lotus` | `prabhavali` |
| `buddhist` | `lotus`, `beads` | `nimbus` |
| `greek`, `roman` | `meander`, `egg-dart`, `wave` | none |
| `norse` | `knot`, `urnes`, `chevron` | none |

## 5. Recipes by scene role
- **Invocation:** `lamp` + `flicker` for the whole film; `border` + `borderIn` at 0.3 s; `title` words; `cartouche` naming the telling; `doors` opening onto the world (the storyteller's box). Frame 0 already shows the doors and the lamp.
- **World:** 3-5 `sheet`s far to near (sky disc, clouds, peaks, hills, waves) placed 1-1.5 s apart; `sway` on clouds and waves; a camera push after the last plane.
- **Revelation:** an `arch` or `niche` frame placed; the figure (`plate` cut-out or `puppet`) `rise`s; `halo` + `haloIn` behind it, `turn` until the end of the film; `breathe` on the figure; a `cartouche` naming the figure and **one emblem**; `glint` on the halo; the camera bows in (push and hold, never orbit).
- **Trial / conflict:** `tint` to `--c-accent`, `shower` embers, `pose` the puppet on the spoken verb, camera closer; violence by silhouette and cut, never gore.
- **Turn:** a reveal device (doors, scroll, `lampTo` carrying the light to the figure); the `tint` lifts.
- **Aftermath:** the opening composition again, changed: a `lotus` placed, `shower` blossoms (pushpa vrishti), a figure missing.
- **Teaching:** one `title` with `plate: true` (paper backing over busy art), attributed ("The tradition reads it as ...").
- **Closing:** `lampTo` back to the opening point, a dim layer fades to about 0.2, credits; hold 2 s or more.

## 6. Per style
Worked examples: the four `projects/style-sample-mythic-*` projects tell the same 22 s storyboard (Hanuman's leap) in each look; compare their contact sheets in `qa/frame-review/`.
- **mythic-paper:** everything above; figures as `cutout` (paper look, lifted shadow); `M.border({tradition})`.
- **shadow-lantern:** a screen, not a diorama: `stage({ground: '--c-screen-glow'})`, scenery as flat lamp-black sheets (`fill: '--c-ink', deckle: 0, shadow: false, fibre: false, edge: false`), figures as `puppet({look: 'leather'})` (Tholu Bommalata) or `'silhouette'` (Reiniger), every limb and the scenery sway `steps: true`, the lamp follows the action with `lampTo`; puppets enter and leave by the screen edge (`tl.fromTo(p.el, {x: -W}, {x: 0})`).
- **painted-folio:** a tradition `border` from frame 0, `registers` (show all grounds early, then fill each in reading order; an empty register for 10 s reads as a void), flat sheets with an ink contour (`deckle: 0, shadow: false, fibre: false, stroke: '--c-ink'`), figures `look: 'painted'`, one figure per register (continuous narration: the same hero appears in each); no camera moves inside a folio.
- **carved-relief:** museum `plate`s (`frame: 'niche'` for a standing image, `'rect'` for an object in motion) duotoned to `['--c-basalt', '--c-marble']` on 3-4 depth layers; slow `Studio.space.camera` pushes; a `credit` on screen whenever a plate is held; no puppets; titles in spaced capitals.

## 7. Formats
Size with `S.u()` and `S.pick({portrait, landscape, square})`, never fixed pixels. Portrait: cartouche top in the safe area, figure on the upper-middle third, captions low. Landscape: frame the figure with a narrower `arch` (about 60% of the width); a full-width arch swallows the frame and the cartouche.

## 8. Pitfalls found while building the kit
- The scaffold's times are written for 45 s and scaled by `T()`; a mid or long film stretched this way has 3-4 s dead stretches. Re-plan the beats per scene from measured audio.
- Text over art needs `plate: true` (frame review measured 2.2-4.1:1 over the vermilion arch and the gold sun without it).
- Cards must stay up long enough to read (frame review `line_unread`: about 1.5 s for 5 words, 2 s for a 2-4 word card at the end); bring the cartouche in at the scene's start, not mid-scene.
- A big scenery sheet placed in front of a figure's feet hides the figure: place the hero on the near edge of its mountain and keep figure layers above the scenery they stand on.
- Search noise is real: the Met returned "Hawks for Cranes" for "Shiva", Commons returns scanned books and battleships. `myth-sources.py` drops DjVu and PDF; a person still looks at every plate. One plate was rejected while making the samples (a Mewar "Battle at Lanka" folio: severed heads, gate 3).
- Put credits where captions are not, or set the scene's `caption_lane` to `upper`.
- Declare the bundled font families literally in the page's `<style>` (the scaffold does): HyperFrames injects a family only when a declaration names it.
- Plates must sit under `src/` and be referenced relatively.
- Never call `Math.random`, timers or infinite repeats; pass `seed` to anything you want to stay the same when you add pieces before it.
