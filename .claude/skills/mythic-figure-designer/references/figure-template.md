# Figure template: building a figure in code

## Coordinate system
- **Standing figures:** viewBox **400 x 820**, centre line `CX = 200`, ground (soles) at y 790.
  - Light comes from the viewer's **upper left**.
  - Landmarks: skull 84, brows 121, eyes 131, nose 151, chin 180, shoulders 212-224, nipples 262, navel 350-358, crotch 440, knees 596, ankles 752, soles 790.
- **Seated figures:** viewBox **400 x 640**, same head and torso. The lotus seat top is at 500 and the plinth runs to 634.
- **Sides:** `r` is the figure's own right (the viewer's **left**, `sg = -1`). `l` is its left (the viewer's right, `sg = 1`).
- **Weapons:** drawn in `armoury.js` at their own origin (the grip), pointing up (-y), in figure units.

## Part tree and ids (keep them: posing, tests and later views rely on them)
- **Aura:** `aura`, `aura-rays`, `aura-ring`. Always first, so they sit deepest.
- **Lower body:** `pelvis` (the lower garment), with `leg-r` and `leg-l` behind it.
- **Upper body:** `torso`, `girdle`.
- **Arms:**
  - `arm-r` > `fore-r` > `hand-r` > weapon, and the same on the left (`arm-l` > `fore-l` > `hand-l` > weapon).
  - A second pair of arms uses `arm2-r` > `fore2-r` > `hand2-r` and the same on the left.
- **Head:** `head` > `hair` > `jata`, `crown`, `helmet` or `hat`; also `kundala-r` and `kundala-l`, and `beard`.
- **Extras:** `tail`, `quiver`, `uttariya`, `cloak`, `ruff`, `raven-*`, `hair-back`.

## Skeleton of a standing heroic figure
```js
FIG['krishna-human'] = function (opt) {
  var o = opt || {}, P = SKIN['shyama-blue'], b = HERO.warrior, glow = '#FFD98A';
  var parts = M.auras.make('tejas', { cx: CX, cy: 150, r: 250 });             // 1. aura first (deepest)
  parts = parts.concat(dhotiPart({ colour: { b: '#E2A62B', s: '#B97D16', h: '#F5CD6A' }, hem: 590, fall: 668, wide: 20 }));
  parts.push(heroLeg(P, 'r', b, { glow: glow }), heroLeg(P, 'l', b, { glow: glow }));
  parts.push(streamer('uttariya', 'pelvis', [[CX - 96, 212], [CX - 150, 262], [CX - 200, 290], [CX - 240, 284]], 20, { b: '#B8321F', s: '#8A2316', h: '#E2735A' }));
  parts.push(heroTorso(P, b, { glow: glow, layers: threadLayers().concat(jewelLayers('haar', P)) }));
  parts = parts.concat(girdlePart({ style: 'sash', w: 64 }));
  var JR = armJ(b, 'r', [CX - 60, 250], 'out');   // shoulder, elbow, wrist from canonical arm lengths
  var JL = armJ(b, 'l', [CX + 60, 250], 'out');
  parts = parts.concat(heroArms(P, 'r', JR, b, { glow: glow, foreFront: true }), heroArms(P, 'l', JL, b, { glow: glow, foreFront: true }));
  armJewels(parts, 'r', JR, { k: b.k, hero: true }); armJewels(parts, 'l', JL, { k: b.k, hero: true });
  var fR = fistAt(JR, 12), fL = fistAt(JL, 12);                                 // fists beyond the wrists
  parts.push(fistPart(P, 'r', fR, { k: 1.25 }), fistPart(P, 'l', fL, { k: 1.25 }));
  parts = parts.concat(M.weapons.place(M.weapons.venu(), { id: 'flute', parent: 'hand-r', at: fR, angle: -8 }));
  parts.push(headPart(P, { tilak: 'vaishnava', smile: 1, brow: 'level' }));
  // ... hair (a part with parent 'head'), crown or peacock feather (parent 'hair') ...
  heroHead(parts, b.head, ['hair-back']);                                      // 2. heroic head scale, last
  return { viewBox: [400, 820], parts: parts, headCentre: [CX, 182 - (182 - 128) * b.head],
    meta: meta({ id: 'krishna-human', name: 'Krishna', tradition: 'indian', heroic: true, emblems: ['flute', 'peacock feather', 'pitambara'], check: 'figure-design.md: Krishna identity block' }) };
};
```
Then add `'krishna-human'` to `M.human.ids`.

## Gotchas
- **Order matters.**
  - A part is drawn over its parent.
  - `behind: true` puts a part under its parent, and a later `behind` part goes under an earlier one.
  - The aura must come first in the list.
- **Children of a transformed part use that part's local coordinates.**
  - Parts placed with `M.weapons.place` are transformed.
  - So a damaru hung on the trishula is placed at `[16, -214]` (trishula space), not in figure units.
- **Head scale goes last.**
  - `heroHead(parts, s, ['hair-back', 'ruff'])` scales the head and its children about the chin.
  - List any torso-parented head-space parts (back hair, a ruff) so they scale too.
- **Stay inside the viewBox** where you can.
  - A weapon or aura may rise above y 0; the SVG overflows visibly.
  - Compositions place figures by their box, so keep tops above about -40.
- **Proportions:** keep the figure inside the canon bands (`figure-design.md` section 8); `tests/mythic-kit/proportions.html` shows them.
- **Arms:**
  - Use `armJ(b, side, target, 'out' | 'low')`: canonical lengths (upper arm 1.45 H, forearm 1.15 H) and two-bone IK. Hand-picked elbows came out too short in the first build, which made the waist look high.
  - `M.human.geom.ik2(shoulder, wrist, upperLen, foreLen, bend)` gives the elbow for a target hand.
  - `foreFront: true` draws the forearm over the upper arm and torso, for raised or crossing arms.
- **Fists** grip a vertical shaft at their centre, so place weapons at the fist centre.
- **Palms:** `palmPart(P, side, wrist, {down})` draws the hand raised (abhaya) or lowered (varada).
- **One wind** for hair (`windLocks`), cloth (`streamer`) and cloaks.
- **Rim light** comes from the aura: pass the aura's glow colour as `glow` to every hero builder.
- **Deterministic only:** patterns come from fixed lattices or index maths, never `Math.random`.

## Adding a weapon or prop to the armoury
1. Read the weapon research (`figure-design.md` section 6), or research it with the playbook: the text, museum objects, how it is held.
2. In `armoury.js` add `W.<id> = function (o) { ... return { fill, d, layers, extra } }`.
   - Draw it at the grip, pointing up, lit from the upper left.
   - Layers: a base colour, a shadow on the right (`shadeRight` or a clipped rect), a highlight on the left, and ink detail strokes.
   - Put gold on sacred parts. Add a glow layer (radial gradient fill) only if the weapon is divine.
   - Sizes are in figure units (a gada head is about 108 wide).
3. Add the id to `W.ids` and a cell to `tests/mythic-kit/armoury.html`.
4. Run `python tests/mythic-kit/render-figures.py` and look at `armoury.png`.

## Adding an aura
1. Add a palette to `AURA`.
2. Add a branch in `makeAura` that fills one or more of:
   - `parts[0].layers` (inside the glow);
   - `ry.layers` (the rays, rotatable);
   - `ring.layers` (the ring, rotatable).
3. Call it with `M.auras.make(kind, {cx, cy, r})`.
4. Animate it with `M.turn(tl, p.part('aura-rays'), from, to, {degrees})` and `M.flicker`.

## Later views (three-quarter, profile, back)
- They are planned on the same landmark lines (`figure-design.md` section 5).
- Each view gets one part set with the same ids and pivots. Views are swapped, not rotated.
- One-sided details stay on the correct side.
- Until then, the front view is the only drawn view. The profile puppets in `figures.js` are a different, simpler build.
