# Tibi: character guidelines (v2.1, Cobalt Sculpt)

Tibi is drawn in the **Cobalt Sculpt** style from 2026-11-09: a male and a female athlete, anatomically proportioned, flat cobalt planes with crescent shading, no outlines. The design came from a separate design session (handover: `src/fitness/tibi/HANDOVER.md`) and is the brand's mascot for every new film. The earlier cartoon Tibi (v1.0, `tibi.js`) was retired on 2026-11-09 on the owner's ruling: the only design that stays is the Cobalt Sculpt one, and `projects/how-muscles-grow` was ported to it.

| What | Where |
|---|---|
| Master source (Python, stdlib only) | `src/fitness/tibi/`: `rig.py` (male), `rig_f.py` (female), `rig_back.py` (back views), `rig_ext.py` (round 7: hands, toes, straps, back detail), `build2.py` (builder and painter, poses), `page6.py` (review page), `export_assets.py` (standalone SVG/PNG), `export_kit.py` (runtime data) |
| Runtime kit | `src/studio/kits/fitness/sculpt.js` (painter on the studio rig) + `sculpt-data.js` (generated: `python scripts/fitness.py sculpt`, never edit) |
| Design review page | `assets/fitness/tibi/site/tibi_cobalt_sculpt_v6.html` (every option and control; rebuild with `python3.12 src/fitness/tibi/page6.py`, byte-identical to the handover) |
| Standalone exports | `assets/fitness/tibi/svg/figures/*.svg` (65), `svg/heads/*.svg` (12), `assets/fitness/tibi/sheets/*.png` (contact sheets) |
| Previews from the runtime | `assets/fitness/previews/tibi-sculpt-model.png`, `tibi-sculpt-activation.png`, `tibi-sculpt-motion.png` (`python scripts/fitness.py sheets --only tibi-sculpt-model` etc.) |

## Construction

| | Male | Female |
|---|---|---|
| Height | 7.66 heads | 7.55 heads |
| Shoulder : waist | 1.62 : 1 (198 : 122) | 1.79 : 1 (168 : 94) |
| Waist : hip | 0.81 | 0.62 (shorts 151 wide on a 94 waist) |
| Legs | 100 % | 96.5 % at the joints (the leg art itself is not scaled: the generator rounds the factor to 1) |
| Muscles | full set | planes about 10 % smaller, arms and calves about 15 % slimmer; abs, serratus and quads stay visible |
| Clothing | charcoal shorts, slim marigold band, white trainers, no shirt | the same plus a sports top (default) or a push-up top |
| Hair | none (smooth hood) | ponytail with a marigold tie |
| Signature | marigold flame spark on the head | the same |

Style rules (do not change without the owner): no outlines, shading by planes only (a light plane and a crescent shade on every muscle, light from the top left), flat fills, slim marigold accents, no logos anywhere (shoes included). Tokens: body `#2F56E0`, light plane `#4F75EC`, shade plane `#2244B8`, face plane `#3F66E8`, visor `#1B338F`, navy `#18286F`, marigold `#FFB224` (glow `#FFE08A`), charcoal `#22243A`, hair `#1C3AA3`/`#3558CF`/`#132A80`, shoes `#FBFBFA`/`#B9C2DE`/`#CFD4E6`. They are in `F.sculptData.colors`.

## Options

| Choice | Default | Other | API |
|---|---|---|---|
| Gender | male | female | `gender: 'male' \| 'female'` |
| View | side | front, back; `top` (prone, seen from above), `above` (supine, seen from above) | `view` |
| Face | faceless (a lighter face plane) | `minimal` (navy oval eyes, catch-light, small smile; hers adds a lash flick), `ember` (dark visor, marigold eyes) | `face` |
| Female top | sports top (racerback from behind) | push-up top (cups, clasp from behind) | `top: 'sport' \| 'push'` |
| Spark | on | off | `spark: false`, `t.spark(tl, on, at)` |

Faces have no expressions or mouth shapes yet, so the Cobalt Sculpt Tibi cannot lip-sync: the narrator speaks and Tibi demonstrates. Use the faceless default unless the brief asks for a face.

## The runtime figure

```js
var t = K.sculpt(stage, {gender: 'female', view: 'side', x: 640, floor: 600, scale: 1});
t.set('stand');
t.to(tl, 'squat', 0.5, 1.1);                    // poses tween; the planted foot stays planted
t.activate(tl, 'squat', 0.8, 0.5);               // coral prime movers, marigold secondary, pale stabilisers
var quad = t.muscle('quadriceps', 'squat')[0];   // {x, y} anchor for a label or leader line
t.markers(tl, true, 2, 0.3);                     // joint dots and dashed bones (biomechanics overlays)
```

- **Scale:** 1.0 is about 422 units sole to crown. Standing full body: 0.8-0.9 in a portrait frame below a header block, 1.0-1.2 in landscape. The origin is the pelvis; `floor` puts the soles on the floor line (`y` is the pelvis for `top`/`above`).
- **Rig:** joint ids pelvis, spine, chest, neck, head, shoulder/elbow/wrist, hip/knee/ankle, and in side view `toe` (the ball of the foot; the shoe is two pieces and bends), each with L/R; side view flexion positive and near limbs R; front/back/top/above abduction positive. Every segment is the generator's art at its joint, painted in the generator's order (far limbs behind and dimmed).
- **Foreshortening (`pose.f`, runtime 1.6.0):** a segment pointing toward or away from the camera keeps its in-plane angle while its children's offsets shrink along its axis by `f` (negative folds back, as a running shin seen from behind); the segment art is scaled by the same `f`. A pose states `f` for every joint so nothing leaks from the previous pose. This is how back-view squats and running, and every view from above, are built.
- **Hands:** the open hand has finger joints (knuckle creases) and a thumb; `fist` is a closed hand seen from the back of the hand (front/back/top/above views, four knuckles, a thumb pad); the side view has an open `hand` and a `grip` (curled fingers around a handle). `pose.ch.grip = 1` closes the hands; `t.grip('R')` returns the handle point for `follow()` or `attach()`.
- **Shoe:** two pieces (heel and forefoot `toes`) that bend at the ball; running toe-off bends it, a calf raise keeps the toes flat while the heel lifts.
- **Straps:** curved, not rigid: front straps bow over the chest, the racerback hugs the shoulder blades from behind, side-view straps follow the bust.
- **Back detail:** upper (`trap`), middle (`midtrap`) and lower (`lowtrap`) trapezius, rhomboids (a deep plane that shows over the surface only when activated, like the glutes), teres major, infraspinatus, lats and two erector columns.
- **Named poses** (`K.sculpt.poses(gender, view)`): side `stand squat calf pushup plank run-strike run-mid run-off run-fly`; front `relaxed flex lateral squat` (the front squat, kit 2.2.0: thighs foreshortened toward the camera, arms reaching forward, activation set `front-squat`); back `relaxed flex lateral squat run-strike run-mid run-off run-fly`; top (prone) `pushup pushup-bottom plank fly-low fly-high y-high`; above (supine) `fly-high fly-low`. Exercise poses are grounded by contact (planted foot or pelvis plus floor); the movement library builds its own poses on top.
- **Arm art follows the pose** in front, back, top and above views: hanging arms use the plain upper arm and hand; raised arms (abduction 50+) add the deltoid cap and lat wing and switch to the no-deltoid upper arm, or to the flexed upper arm when the elbow bends past 60 degrees; hands show as a fist while gripping or flexing. Since sculpt kit 2.2.0 (2026-11-23) the drawings **blend** instead of switching: inside a per-view abduction window (front 25-75, back 24-58, top 50-70, above 30-70 degrees) the drawing on top fades in over the opaque one underneath, which then fades out, the deltoid cap swells from the top of the arm and the lat wing grows out from behind the torso; the flexed arm and the fist fade in over a short ramp inside the elbow window (35-85 degrees). Outside the windows the art is exactly the old drawing: all 118 named poses and exercise end poses render byte-identical to kit 2.1 (audit in `prompts/state/p05/2d-report.md`; `tests/test-fitness.py` checks the named poses). A new static pose must sit outside its view's window.
- **Moves are continuous** (kit 2.2.0): `t.to`, `t.sequence` and `t.cycle` drive one tween per move whose setter solves the exact pose for each frame (the 3D kit's `T3.bind` pattern), instead of `RIG.to`'s 6-10 linear samples a second that stepped the speed at every sample edge. Explicit contact targets (a pelvis moved to a point, a hand IK'd to a bar) travel from where they are to the target instead of jumping to it on the first sample; gait cycles pass through their keys on a Catmull-Rom spline. `op.sampled: true` keeps the old sampling. `F.sculpt.solver(fig, from, to, ease)` gives the same continuous solve to overlays (`G.bio.angle.track` uses it on a sculpt Tibi).
- **Shading follows the light:** crescent masks are counter-rotated against each segment's world angle on every move sample, so the light stays top-left while limbs swing, and a mirrored figure (`facing: -1`) is lit correctly too.
- **Activation:** levels 3 (coral `#F2553D`), 2 (marigold `#FFB224`), 1 (pale cobalt `#8CAEFA`), 0 (idle). Named sets in `K.sculpt.acts`; maps take sculpt keys (`quad`, `glute`, `delt@far`, `midtrap`, `lowtrap`, `rhomb`, `teres`, `infra`) or `muscles.json` ids (`quadriceps`, `gluteus-maximus`, `rhomboids`). Glutes, hip flexors and rhomboids sit under the shorts or the trapezius and show only at level 2+.
- **Movement library** (`src/studio/kits/fitness/exercises.js`, data in `assets/fitness/data/exercises.json`): 12 upper-body exercises (push-up, dumbbell bench press, dumbbell fly, pull-up, one-arm row, rear-delt fly, seated press, lateral raise, prone Y-raise, incline curl, overhead triceps extension, dip), standing curl, bodyweight squat, calf raise and the walk/jog/sprint gaits. Each exercise declares its camera (`K.exercises[id].view`), builds its equipment from Tibi's own joints (`K.equipment`: dumbbells, benches, seat, bars, dip rails), closes the hands around the handle and exposes `ex.reps()`, `ex.phase()`, `ex.acts` and `ex.repDuration()`. Barbell and machine lifts (kit 2.2.0): `back-squat`, `deadlift`, `barbell-bench-press`, `leg-press` (side view) and `lat-pulldown` (back view, cable), with a loaded bar seen along its length (450 mm plates at Tibi's scale), rack uprights, a 45-degree leg press whose sled follows the soles along the rail, and a pulldown station; the deadlift's bottom depth is solved so the plates rest on the floor for either body and any scale.

## Consistency rules

- Build Tibi only through `Studio.kit.fitness.sculpt(...)`. Never redraw him or her by hand, and never edit `sculpt-data.js`: change the generator in `src/fitness/tibi/`, then `python scripts/fitness.py sculpt` and `python scripts/studio.py upgrade --all`.
- One Tibi per shot unless the story needs a comparison (the male and female pair share the scale).
- Activation colours mean roles, not EMG amplitude: label them "illustrative" and never put a percentage on them.
- **3D Tibi (2026-11-12):** a second, parallel Tibi in real 3D (`K.t3d`, `tibi3d.js`) with a free camera, built because the 2D rig's art variants swap at joint thresholds and pop (lats, deltoid cap, flexed arm; kit 2.2.0 blends them, which reduces but does not remove the change) and its views are separate drawings. Same palette, same marigold spark, same white shoes, same activation roles (coral prime, marigold secondary, pale cobalt stabiliser). Use it for curls, presses, raises, rows and pulls and for any shot that wants an angle other than side, front, back or top; rules, tools and limits in `motion-3d.md`. Never put a 2D and a 3D Tibi in the same frame.
- **3D anatomical correction (1.10.0, 2026-11-20):** the default body uses integrated fan/band volumes, body-relative centres and softer surface shading. Lats must not appear as hanging exterior lobes and shoulder muscles must not read as separate pads. These are geometry defects even in a single mesh. Inspect both normal and neutral-clay views; 2D art, its ratios and the palette are not changed by this correction.
- **Shoulder/arm correction (1.11.0):** the owner rejected the remaining shoulder knobs. A sloping shoulder envelope replaces the joint orb; rounded deltoid fans taper into the arm. Show the shape change at the original pose, and the new neutral arm/waist separation separately. Read `fig.defaultPose` for that neutral stance. Yellow Dude was studied for anatomical flow, not copied. The 2D master remains unchanged.
- Camera follows the movement: side view for sagittal work, front view for raises and presses, back view for pulling and the posterior chain, from above for prone and lying work. A change of view is a 0.2-0.3 s cross-fade between two Tibis.
- Never sexualise, injure or humiliate Tibi; the push-up top is a wardrobe option, not a framing device. Mistakes are shown as technique errors, not pain.

## Known limits (from the handover and round 7; be honest about them)

- The construction ratios above describe the 2D design, not a verified 3D match.
  Measure both engines with the same landmarks before changing proportions:
  a joint span, a torso outline and an arm-inclusive silhouette are different
  measurements. The 2D body fill is `#2F56E0`; 3D uses `#2A4FD8`.
- No facial expressions or lip-sync (the owner ruled this fine for now: the narrator talks, Tibi demonstrates).
- Fingers have joints in the open hand only; the fist and grip are one closed shape.
- Far limbs in side views are the near limb's shapes, dimmed (a depth cue, not separate drawings).
- Views from above show the arms foreshortened by a scale factor, not true 3D: very large reaches can look flat.
- Arm-art blend (kit 2.2.0): the drawings are different shapes, so a fast raise still shows one or two in-between frames with a pale deltoid cap or flexed-arm edge (measured and looked at in `prompts/state/p05/2d-report.md`); the windows cannot widen past the named poses that bound them (top-view push-up bottom at 48 degrees, pull-up top at 61). A true morph needs drawings with shared point topology (they have different plane counts). For a raise, press or curl that is the subject of the shot, the 3D Tibi is still the better tool.
- The front squat reads as a parallel-ish squat: the front view paints the legs before the shorts, so foreshortened thighs sit behind the pelvis (a per-pose paint order would be needed for a deep one). A back-view push-up is not built for the same reason (the legs nearest the camera would have to paint over the trunk): push-ups are shown from the side and from above.
- Barbell lifts in side view: the near 450 mm plate sits between the camera and Tibi, so it is drawn ghosted (a faint plate tone, a denser rim band and an opaque sleeve hub; `EQ.barbellEnd(g, s, 'near', {solid: true})` restores the opaque plate) and the body reads through it; the far plate stays solid behind Tibi. The 3D rule 12 in `motion-3d.md` moves the camera instead. The equipment kinematics are conceptual, like the rest of the library.
- Back-muscle names beyond the planes listed above (rotator cuff, serratus from behind) are not drawn separately.

Next steps the owner can pick from: facial expressions and visemes, a Lottie/Rive export, a contact-sheet script. They are listed in `TODO.md`. Prepared but not applied (owner decision, `prompts/state/p05/2d-decisions.md`): the dead-code removal of HANDOVER section 13 and the `build2.figure()` rounding fix.

## Maintaining the generator

Run from anywhere (each script finds its neighbours): `python3.12 src/fitness/tibi/page6.py` (review page; prints `written 1577 KB {'m': 7.66, 'f': 7.55}` since round 7, and must stay byte-identical to the committed `assets/fitness/tibi/site/tibi_cobalt_sculpt_v6.html` unless the design changes; the handover's 1469 KB is the pre-round-7 number; on Windows set `TIBI_OUT` to a scratch folder and compare `git hash-object` of the rebuild with the committed blob), `python3.12 src/fitness/tibi/export_assets.py` (SVGs; PNGs need Playwright, which this host lacks), `python scripts/fitness.py sculpt` (runtime data). After any data or builder change: rebuild, look at the affected figures for both genders, plain and activated, near and far limbs, then re-export and `python scripts/fitness.py sheets --only tibi-sculpt-model` (and the activation, motion and blend sheets). The handover's recipes for new poses, faces and tops are in `src/fitness/tibi/HANDOVER.md` section 10; a new pose also needs an entry in `export_kit.py` so the runtime gets it (a front-view depth pose goes in `build2.BACK3D` with a `front_` name), and it must sit outside the arm-blend windows of its view (`tests/test-fitness.py`).
