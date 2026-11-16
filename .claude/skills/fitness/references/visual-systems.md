# Fitness visual systems: kit API

Load order in a composition (the `fitness-explainer` template does it): `_studio/vendor/gsap.min.js`, `studio-core.js` ... `studio-compositions.js`, then `studio-rig.js`, `kits/fitness/brand.js`, `sculpt-data.js`, `sculpt.js`, `exercises.js`, `anatomy.js`, `graphics.js`, `library.js`. Everything is under `Studio.kit.fitness` (`K` below; `G = K.graphics`, `A = K.anatomy`). All methods add explicit `fromTo` tweens; add rig moves for one Tibi in time order.

## A. Character animation

**Tibi (Cobalt Sculpt, current):** male or female; views side, front, back, top (prone, from above) and above (supine, from above). Full guide: `character-guidelines.md`.

```js
var t = K.sculpt(svgGroup, {gender: 'male', view: 'side', x: 640, floor: 600, scale: 1, face: 'faceless', top: 'sport'});
t.set('stand'); t.to(tl, 'squat', at, 1.1);                    // poses: K.sculpt.poses('male', 'side'|'front'|'back'|'top'|'above')
t.cycle(tl, K.gait.keys('jog'), at, 0.73, 10, {floor: t.soleFloor()});   // walk, jog, sprint gaits
t.activate(tl, 'run-mid', at, 0.4);                            // or {quadriceps: 3, 'gluteus-maximus': 2, 'hams@far': 2}; null clears
t.muscle('gluteus-maximus', 'run-mid');                        // [{name, level, far, x, y}] anchors for labels
t.markers(tl, true, at); t.spark(tl, false, at);
```
Exercises: `var ex = K.exercise(t, 'pull-up'); ex.reps(tl, at, n, {pause: 0.12}); t.activate(tl, ex.acts, at)`; `K.exercise.ids()` lists them. The Tibi's view must match `K.exercises[id].view`. Equipment is placed from Tibi's joints (`K.equipment`). Move a whole Tibi (step aside for a diagram) by tweening the `transform` attribute of the parent group.

## B. Anatomy visualisation

- Cobalt Sculpt Tibi: muscle activation by role on the body's own planes, `t.activate(tl, set|map, at, dur)` (see A); label it illustrative.
- Anatomy callouts: `t.muscle('quadriceps', pose)` gives the world point of a muscle plane for a leader line (follow it with `t.fig.follow` if Tibi moves).
- Plates (`anatomy.js`): `A.muscle`, `A.fascicle`, `A.fibre`, `A.myofibril`, `A.sarcomere` (`contract`, `relax`: sliding filaments with head strokes), `A.crossSection` (`grow`), `A.satelliteCell` (`donate`), `A.mitochondrion` (`emit` ATP), `A.atp`, `A.heart` (`beat`), `A.lungs` (`breathe`).
- Scale dive: `A.zoomLadder([{wrap, g}, ...], {cx, cy, zoom}).step(tl, from, to, at, dur)`; give each level a name and a size from a source (OpenStax §10.2 gives fibre, myofibril and sarcomere sizes).
- Clip the diagram panel (`clipPath`) so zooms never spill outside it.

## C. Biomechanics (illustrative unless measured)

- `G.bio.angle(g, t, ['hipR', 'kneeR', 'ankleR'])`: `.sample(tl, pose, at, dur)`, `.track(tl, from, to, at, dur, n, ease)` follows a rig move with the same sampling as the rig.
- `G.bio.force(g, {x, y, angle, length, label})` (ground reaction, load, muscle pull), `G.bio.path(g, t, joint, local, poses)` (bar path; draws on), `G.bio.centreOfMass(t, pose)` plus `G.bio.comMarker`.
- Label: "illustrative kinematics" whenever numbers appear. Measured data needs its source line and the word "measured".

## D. Scientific infographics

- `G.sci.chart(g, {x, y, w, h, xDomain, yDomain, xTicks, xLabel, yLabel, baseline, series:[{id, points, color, label}], area:{between:[a,b]}})`: `.axes`, `.draw(tl, id, at, dur)`, `.fillArea`, `.map(x, y)` (chart-local; put labels inside `chart.g` so they move with it).
- `G.sci.flow(g, {nodes:[{label, sub, color}], vertical})`: `.light(tl, i, at)` for pathways (tension -> mTOR -> synthesis; ATP systems; feedback loops).
- Evidence: `G.evidenceBadge` and `G.citation` next to every claim; `G.mythStamp` once per myth.
- Plot only published numbers; mixed studies on one chart need each series' source and n on screen.

## E. Exercise animation

`var ex = K.exercise(t, 'back-squat'); ex.reps(tl, at, 3, {tempo: 1, pause: 0.3}); ex.phase(tl, 'squat-bottom', at, 0.8);`
Ids: `back-squat`, `deadlift`, `bench-press`, `overhead-press`, `pull-up`, `push-up`, `barbell-row`, `lat-pulldown`, `biceps-curl`, `triceps-pushdown`, `lunge`, `leg-press`, `calf-raise`, `walk`, `jog`, `sprint` (gait: `ex.run(tl, at, seconds)`, `ex.speed` = belt speed for a scrolling floor). Error poses for coaching: `squat-error-heels`, `deadlift-error-round`, `pushup-error-sag`, `curl-error-swing`. Metadata (muscles, phases, landmarks, camera, errors) is in `K.library.exercises[id]`; highlight `muscles.primary` and never claim isolation.

## F. Environments and props

`G.env.gym`, `G.env.track` (`scroll(tl, from, to, speed)`: use `ex.speed`), `G.env.outdoor` (`scroll`), `G.env.plate`. Equipment `K.equipment`: `plate` (`ghost` for see-through), `barbellEnd`, `dumbbell`, `dumbbellEnd`, `bench`, `rack`, `pullupBar`, `cableTower`, `seat`.

## G. Motion graphics components

`G.logo`, `G.spark`, `G.titleCard`, `G.lowerThird`, `G.chapterCard`, `G.callout`, `G.sting`, `G.endCard`; plus every shared studio component (`Studio.comp.captions`, `Studio.type.count`, transitions). Number counters on SVG text: tween `textContent` with `snap`, with units in a separate element.

## Gotchas found while building the demo

- A layer shown at frame 0 and faded in again later: the later fade must use `immediateRender: false`, or the layer is invisible from frame 0.
- Never name a method `play` in a composition (the determinism lint bans `.play(`).
- Plates or props in front of the face: use `ghost` plates.
- Keep text above y of about 570 in landscape: the caption plate sits roughly 580-662.
