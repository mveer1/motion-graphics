# Tibi in 3D: motion rules, rig and tools

Written 2026-11-12 after the upper-body-workout review: the bicep curl and chest press broke posture and the lats "appeared from nowhere". Everything below was measured on the lab project `projects/lab-3d-motion` (three 6 s clips, one skeleton, orbiting camera) and checked with the numeric and pixel tools named at the end.

## What was wrong with the 2D rig (diagnosis, so it is not repeated)

1. **Art swaps at thresholds.** `sculpt.js armState()` picks a different drawing by joint angle: below 50 degrees shoulder abduction the plain upper arm, above it the no-deltoid arm plus a deltoid cap plus the lat wing (`flare`), and above 60 degrees elbow flexion the flexed upper arm and a fist. Each rep of a curl, press or raise crosses those thresholds, so the shape snaps in one frame. This is the pop. It is structural: a view-per-drawing rig cannot avoid it without morphing between drawings.
2. **Views are separate drawings.** A turn is a cross-fade, so only the side, front, back or top views exist and the camera never moves. Lying and reclined poses (bench, incline) mix a side-view torso with front-view anatomy planes, which is why muscles float off the body in the press and curl frames.
3. **Moves are sampled, not continuous.** `RIG.to` with an anchor or IK samples a move at about 10 per second and tweens each piece linearly. Measured on the old render: per-frame motion rises in plateaus of 3-5 frames and steps up, constant velocity in pieces. That reads as "not smooth".
4. **No gate saw it.** frame-review checks layout, the QA gates check streams and loudness. Only a human noticed. `scripts/motion-continuity.py --mode edge` flags the old press (38.5 s, 40.4 s), curl (209.5 s, 210.6 s) and raise events, and the flagged frames show the arm art changing between variants. Be precise about what a pixel tool can do: those 2D swaps change a thin crescent of the arm, so `edge` mode also fires on fast dumbbells (false positives) and `patch` mode (the default) does not see them at all. Pixels can screen; geometry settles it. For the 3D rig, continuity is guaranteed by construction and checked numerically (`rig3d-check.js`); the pixel tool's job there is colour snaps and anything the numbers cannot see.

## Was Blender used? No.

Blender is not installed and was never part of the pipeline (`production.md`). The 2D rig is SVG. The 3D answer here is **Three.js (r158, vendored at `src/studio/vendor/three.min.js`) rendered by HyperFrames' own headless Chrome**, which keeps determinism, the render lock, captions, QA gates and the HTML overlays that the rest of the studio uses. Blender stays an option for photoreal or sculpted anatomy, and is the wrong tool for this look (flat cobalt planes) on an 8 GB host with a one-heavy-job rule.

## The 3D kit

| File | Role |
|---|---|
| `src/studio/kits/fitness/tibi3d.js` | `T3.tibi` skinned figure (male or female), `T3.stage` (renderer, camera, light, floor), `T3.motion` (tracks), `T3.bind`, equipment |
| `src/studio/kits/fitness/exercises3d.js` | `T3.exercises`: curl, press, raise; squat, squat-blocked, hipthrust, calfraise, seatedcalf (lower body, 2026-11-12). Each authors tracks, builds equipment, lists camera `shots`, and may carry `checks`; `T3.squatSolver`, `T3.reps`, `T3.gastroLine`, `T3.heelLift` |
| `src/studio/kits/fitness/film3d.js` | `T3.film`: SVG overlay over the canvas, joint pins and projected lines updated per frame, opacity windows (`win`), camera shots as tracks (`shot`), measured-number bar panels (`bars`) |
| `src/studio/vendor/three.min.js` | three r158, MIT, vendored like GSAP (never a CDN) |
| `assets/fitness/lab3d/still.html` | still-frame bench for the 3D rig |
| `scripts/rig3d-check.js` | numeric QA, node only |
| `scripts/rig3d-stills.py` | contact sheet from several camera angles |
| `scripts/motion-continuity.py` | pop and discontinuity detector for any rendered film |

Load order in a composition: `vendor/three.min.js` (in `<head>` next to GSAP), `studio-core.js`, `kits/fitness/brand.js`, `tibi3d.js`, `exercises3d.js`, `film3d.js`. Reference compositions: `projects/lab-3d-motion/src/index.html` (clips, no narration); narrated films `projects/knees-past-toes` (two figures, one world), `projects/hip-thrust-vs-squat` (split screen with `stage.views`), `projects/standing-vs-seated-calf` (anatomy close-ups and a muscle line).

### Units, axes, pose parameters

Head = 100 units, standing height 760, hip joint 370 above the floor. The figure faces +z, its left is +x, y is up. A pose is a flat dictionary of numbers (degrees):

- root: `x y z yaw pitch roll` (`y` is the hip height; lying supine on a bench is `pitch -90, yaw 90`, head toward -x)
- trunk: `lean twist bend neckF headF headY`
- arms per side `L`/`R`: `sh` elevation (0 hanging, 90 horizontal), `pl` plane (0 out to the side, 90 forward), `rt` axial rotation, `el` elbow flexion, `wr` wrist flexion, `pr` forearm pronation, `gax gay gaz` (a world direction a held bar should lie along; the hand rolls to match)
- arm IK per side: `ik=1`, `hx hy hz` wrist offset from the shoulder in world units, `px py pz` elbow pole (the direction the elbow points); `ikc=1` reads both in the CHEST frame (a bar on the back or across the hips rides the trunk)
- legs per side: IK to a planted foot (`fx fy fz fyaw`, `fy` = sole lift, `kf` = knee turn-out, `hl` = heel lift in degrees: the shoe hinges at the ball, which stays where `fx fz` put it; `T3.heelLift(deg)` gives the ankle offset to add to the root) or FK (`ikLeg=0`, `hp ha kn an`)
- pelvis: the root IS the pelvis; `pitch` tilts it (hip hinge), `lean` bends the spine on top. A squat's trunk angle is split 0.72 pitch, 0.28 lean
- activation: `act.<muscle>` 0..1 (the colour role comes from `fig.roles({...})`, intensity from the track)
- camera: `cam.az cam.el cam.dist cam.fov cam.tx cam.ty cam.tz`; split screen: `stage.views = [{rect, cam, figs}]`, driven by `cam<i>.<k>` and `view<i>.x|y|w|h` tracks, `stage.project(v, i)`
- muscles: lower body adds `glute` and the upper `adductor` (glute rests in the shorts colour and glows through them), `soleus` under a two-headed `calf` (gastrocnemius); `fig.point(bone, x, y, z)` gives any bone-local point in the world

The shoulder is a swing-twist model, not three Euler angles: direction from (elevation, plane), then twist. No gimbal flips, and any two poses interpolate along a sane arc. The right arm mirrors the left, so `sym({sh: 10, el: 90})` poses both.

### Determinism: pure functions of time

HyperFrames seeks with `totalTime(t, true)`, which **suppresses GSAP callbacks** (`onUpdate` never fires on a seek). The 3D figure therefore never reads tween state:

- `T3.motion()` holds named tracks. `m.base`, `m.to(at, dur, values, ease)`, `m.cycle(at, period, count, steps)` and `m.path(at, dur, fn, ease)` build them. `m.at(t)` returns the whole pose, camera and activation at film time `t`, and calling it in any order gives the same answer.
- `T3.bind(tl, stage, motion, duration, onFrame)` adds ONE linear tween over the whole film whose **property setter** poses the rig, moves the camera and renders. GSAP property writes are not suppressed on seek; callbacks are. `onFrame(values, t)` is where overlays (labels tracked with `stage.project(fig.world('biceps@L'))`, scene visibility) update from the same values.
- No rAF, no clock, no `Math.random`, no timers. The renderer uses `preserveDrawingBuffer`.

## Motion authoring rules (each one is a failure that was seen)

1. **One continuous parameter set per movement. No art swaps, no visibility switches, no thresholds.** Muscles are regions of the ONE skin (`anatomy3d.js`); activation is a colour gradient on the skin, bulge is a displacement along the normal (biceps swell with elbow flexion). `rig3d-check` fails a superficial muscle with no skin coverage or a bulge outside -3..9 units.
2. **Declare a base value for every key you move.** A track with no base started from `undefined`, became NaN, and everything above the spine silently vanished from the render (found by the 14 s snapshot). `m.at` now falls back to the rig default and `rig3d-check` fails on a non-finite value, but declare the base anyway.
3. **Plant contacts with IK targets, not hand-tuned angles.** Feet are `ikLeg` targets on the floor, so soles stay at 0 in every frame (`rig3d-check` measures it). Hands on a bar or dumbbell use arm IK when the path must be exact.
4. **Build a path when two coupled keys must stay related; never sample a curve into short linear moves.** The press path sweeps the elbow along an arc around the shoulder and holds the wrist one forearm length straight above it (`m.path`), so the forearm is vertical at every frame (the cue "forearms vertical at the bottom" is true in the animation, checked to within 12 degrees). Interpolating two end poses linearly bowed the forearm up to 25 degrees off vertical in between; sampling the arc at 10 per second gave velocity steps.
5. **Reps have a rhythm.** Eased moves with short holds at the ends (`cycle` steps with `v: null`), a slower, `sine.inOut` eccentric (lowering) and a faster `power2.inOut` concentric (lifting). Do not make every move the same duration or ease.
6. **Activation follows the work.** Ramp in over the concentric, ease off on the eccentric, baseline 0 (a non-zero baseline tints the resting muscles pink). Colour goes blue to a pale tint of the role colour to the role colour; straight blue to coral goes muddy purple.
7. **Keep the light on the camera.** The key light is a child of the camera, so the light and shade planes read the same from any angle during an orbit. Do not place lights in world space.
8. **Frame for the title and captions.** Portrait standing figure: `dist ~2500`, target `ty ~480`; supine on a bench: `dist ~2200`, `tx -120, ty 235`. Closer than that crops the head or the shoes. In a narrated film, solve the camera from two limits instead (rule 13).

### Lower body (2026-11-12, three narrated shorts; each rule is a defect that was seen)

9. **Solve lower-body poses from contacts and balance, never pose a frame by hand.** Squat: the hip follows from the shin and thigh angles, and the trunk angle is solved so the bar stays over the midfoot (`T3.squatSolver`), which is what makes the knees-blocked squat lean further (33 vs 51 degrees at the bottom, matching the direction Fry 2003 reports). Hip thrust: the shoulder-blade contact is pinned to the bench edge and the hips rise on an arc around it. Calf raise: the ball of the foot is fixed and the ankle moves (`T3.heelLift`).
10. **A fixed knee turn-out only works when the knee travels far forward.** The blocked squat splayed its knees 59 units off the line of the foot; the turn-out is now solved per frame so the plane (hip, ankle, pole) contains the designed knee, and blended from the toe angle while the leg is nearly straight (there the solved pole is meaningless and twisted the thigh 44 degrees). `kneeTrack` checks within 26 units.
11. **A muscle under clothing rests in the cloth colour and warms through a deep role colour.** Through the pale tint it flashed on the dark shorts and partial activation read as a brown stain (found by the pixel tool on the motion-only render, at 0.27 s of the hip thrust). Limit colour, not only activation: `rig3d check` fails a colour change above 0.12 per channel per frame; sets ramp in over 1.0 s and fade over 1.2 s (0.6 s moved a colour 0.17 per frame).
12. **Side views of a barbell lift sit at az ~72, not 90.** At 90 the near plate covers the head and neck. Plates radius 46 (technique plates), not 62.
13. **Solve the camera from the layout, not by eye.** px per unit = 1280 / (0.4617 * dist) at fov 26. Take the standing height at the top of a rep (~840 units with the spark), the header bottom (~y 300-330) and the caption top (~y 900-915): e.g. top >= 330 and floor <= 895 gives dist ~4150, ty ~380 for a two-shot. In a calf film the heels must never sit under the caption plate. Close-ups that put the body behind the header need a paper plate under the title.
14. **Two figures: one world or two views.** Side by side in one world (z apart; camera at +x looks along -x, so +z is screen-left) for comparisons in the same pose; `stage.views` for a vertical and a horizontal lift together (each view its own camera and only its own figures, one canvas, scissored). `m.at` applies every started path in start order, so two figures can run paths at the same time (before, only the latest path applied and the other figure froze).
15. **Overlay text that follows the skeleton is a pure function of t** (`T3.film` in `onFrame`), and a label's text may change with t (`pin.text`). Tags over two figures are centred (`center: true`); side-anchored tags were clipped at the frame edge.

## Camera shots (what each is for)

An orbit is one tween on `cam.az`: front (0 to 20) names the muscle on the front, three-quarter (30 to 45) is the default for lifts, side (90) shows range and joint angles, back (180) shows lats, rear delts, traps, above (`el` 60 to 70) shows bar path and elbow flare, head-end (`az` 270 on the bench) shows symmetry. Cut between shots on a spoken cue, or orbit slowly (60 to 100 degrees over 6 s); never both at once. Each exercise lists its good shots in `shots`.

## Tools and what they prove

```bash
python3.12 scripts/fitness.py rig3d check [curl press raise]     # numeric QA, no render, exit 1 on failure
python3.12 scripts/fitness.py rig3d stills curl --shots front,three,side,back --times 0,1.0
.venv/bin/python scripts/motion-continuity.py <render.mp4> --range 35,43 --roi 0.22,0.62 --sheet qa/pops.png
```

- `rig3d check` reports, per exercise: teleport spikes (a frame moving more than 3x its neighbours), maximum speed and acceleration of wrists, elbows, head, hips and knees, muscle presence and size, activation AND colour step per frame, planted-sole error, IK reach saturation of arms and legs (a stretched leg lifts the foot off its target), props built but never added to the scene (a bench once vanished from an edit and every other check still passed), joint limits (elbow 0-150, knee 0-150, shoulder 0-175) and the exercise's own assertions (`checks`: knee tracking, kneecap behind the board, hip-thrust shins at lockout, ball of the foot fixed in a heel lift); `exercise` prints their measurements.
- **On a narrated film the pixel tool flags every overlay fade, caption word and camera cut** (about 75 events per 50 s film, against a neighbour median near zero, because the 3D motion itself is that smooth). Run it on the motion layer alone: a temporary `src/qa-motion.html` that adds `#root > svg, .st-captions { display: none !important }`, rendered with `--composition qa-motion.html --quality draft` to the scratchpad, then deleted (a file left in `src/` changes the render fingerprint). On the three lower-body films that left only the camera cuts, two activation ramps and one real defect (rule 11).
- `motion-continuity.py` counts, per frame, the changed pixels that have no changed pixel nearby in the previous two frame pairs (`patch`: radius 16 px at 240 wide plus a morphological opening, so only filled patches count; `edge`: radius 5, no opening). Smooth motion moves an edge band beside last frame's, a pop is a patch with nothing around it. It reports POP and CUT events, writes a before/after sheet, exits 1 on a pop. It never certifies a film: look at the frames it flags, and at the frames it does not. Measured results are in the lab report below.
- `rig3d stills` is for looking: posture, contact, equipment, activation. Run it from at least front, three-quarter, side and back for every new exercise before writing the composition.

## Known limits of the 3D kit (first version)

- Eight exercises: curl, bench press, lateral raise, back squat (and knees blocked), barbell hip thrust, standing and seated calf raise. Not yet: deadlift and RDL (hip hinge with a bar path), lunge and split squat (feet apart front to back), leg press, leg curl and extension (machines), running. Port one at a time, run `rig3d check`, then `rig3d stills`.
- On a horizontal thigh (seated) the quad ellipsoid reads as a flat disc; the shoe is two rigid pieces (heel and toe box), not a bending sole; the hip-thrust glute faces the floor, so it is only visible from a low side camera.
- Look: one toon-shaded skin with muscle relief (anatomy 1.0, 2026-11-13). It reads as Tibi (cobalt, marigold spark, white shoes) but not as the 2D art's crescent shading; muscles are tapered ellipsoid volumes, so deltoids and pecs read as soft ovals up close. See `fitness-anatomy`.
- No cloth or hair simulation (the ponytail follows the trunk lean only); no foot roll; no spine curve on the bench (the back is flat).
- Kinematics are authored key poses, labelled "illustrative", never mocap.
- Render cost: HyperFrames compile spends most of its first minutes fetching Google Fonts the first time; per-frame WebGL on SwiftShader is software-rendered. Measured numbers are in `qa/` of `projects/lab-3d-motion`.
- The vendored three.min.js is r158 (the last release with a classic global build; it prints a deprecation notice that is harmless). Moving to a module build means changing how compositions load it.

## Lab results (projects/lab-3d-motion, 2026-11-12)

Three clips, 18.8 s, 720x1280, 30 fps, 564 frames, one skeleton, orbiting camera (`qa/contact-sheet.png`, `qa/rig3d-check.json`, `qa/continuity-patch.json`).

| Measure | Result |
|---|---|
| `rig3d check` (curl, press, raise, both genders) | all pass: no teleport spike (worst step/neighbour 1.07), muscles never hidden (smallest 87% of rest size), planted soles 0.00 units off the floor, IK in reach, elbow 0-144, knee 0-90, press forearms within 12 degrees of vertical, largest activation colour step 0.087 per frame (limit 0.10) |
| `motion-continuity` patch mode, final render | curl and raise: no event; press: one event of 0.05% of the region at the start of the activation ramp (a gradual colour onset, three frames, not a pop) |
| Defects the tools found and that were fixed | (1) press forearm up to 25 degrees off vertical with straight-line IK targets, fixed by building the elbow arc and holding the wrist a forearm above it; (2) velocity steps from sampled linear moves, fixed with `m.path`; (3) raise with an undeclared `lean` base became NaN and the whole upper body vanished from the render (the 14 s snapshot showed legs only); (4) activation fade-out of 0.2 s snapped the colour in one frame (found by the pixel tool, now also a numeric check) |
| Render | first compile 3 min 53 s (Google Fonts fetch), then 18-26 s compile, capture 25-27 s for 564 frames (about 21 frames per second), total 26-46 s, 5.6 MB, "hardware gpu", `--low-memory-mode` |
| Peak memory | not measured |
| Not done | the nine other exercises, a full 3D film with narration and captions, a human creative review of the look against the 2D art |

## Lower-body shorts (2026-11-12)

Three narrated shorts, portrait, series `sinew-lower-body-3d`: `knees-past-toes` (Fry 2003), `hip-thrust-vs-squat` (Plotkin 2023), `standing-vs-seated-calf` (Kinoshita 2023). Production notes in each `qa/production-report.md`.

| Measure | Result |
|---|---|
| `rig3d check` (8 exercises, both genders) | all pass; worst teleport ratio 1.09; knee tracking within 10 units (blocked squat 59 before rule 10); ball drift 0.00 in heel lifts; worst colour step 0.109 per frame (0.179 before rule 11) |
| Render | 71-78 s per 46-53 s film (720x1280, 30 fps, `--quality looks`, `--low-memory-mode`); a draft motion-only pass about the same |
| QA gates | all five pass on all three (-17.3, -17.2, -16.7 LUFS before the final re-render) |
| Pixel pops, motion layer only | camera cuts only, plus the glute flash (fixed, rule 11) and two activation ramps that look identical frame to frame |
| Defects found and fixed | knees splayed off the foot line (rule 10); thigh twist at standing (rule 10); a bench missing after an edit commented out its `stage.world.add` (new orphan-prop check); plate over the head in side views (rule 12); captions over the knees, the glutes and the heels (rule 13, caption lane `lower` in the hook); tags clipped at the frame edge (rule 15); glute flash and brown stain (rule 11); Whisper stretching a scene's last word into the next scene (captions clamp, src/pipeline/captions.py); respelled words reverting in captions on every re-run (`display_spellings` reads research.json's phonetic lexicon) |
| Not done | a human creative review of the 3D look against the 2D art; a long-form 3D film; the remaining lower-body lifts (limits above) |

## Anatomy 1.0 and the instructional layer (2026-11-13)
The body is now one continuous skin (`kits/fitness/anatomy3d.js`, skill `fitness-anatomy`); the old rigid-ellipsoid muscles are gone. New pose keys: `cut.<window>[@L|@R]` (0 closed, 1 skin out, 2 superficial layer out), `hi.<muscle>`, `view.ghost`, `view.layer`, `view.skel`, `view.effort`, `iso.<muscle>`. `fig.world('muscle@side')` is now a point ON the skin over that muscle (rides bulges and joints). The bind pose is an A-pose, so bones rest straight but the mesh was built with arms 26 and legs 4 degrees out.

16. **Every motion key carries the figure id prefix, including those returned by `m.path` callbacks.** A path that returned `hxL` instead of `b.hxL` froze the dumbbell press in every composition (the stills bench has no id, so it worked there). `rig3d-check` now builds figures with an id and fails on a range of motion under 90 units (heel raises declare their own `minRom`).
17. **Every exercise declares a `phaseMap`** (fractions of the rep period: start, eccentric, end range, concentric, lockout, reset; kind up, down or hold). `T3.phaseAt(def, {at, period, reps}, t)` and `T3.phaseTimes` expose it; the HUD, cue cards, 2D comparison and sound read it. `rig3d-check` fails when hold phases move or lifting phases do not.
18. **Highlights are defensible**: each `acts` role (3 prime, 2 helper, 1 stabiliser) must be listed in `assets/fitness/data/exercises.json` for the exercise named in `knowledge`; `fitness.py check` audits it.

Tools added: `scenes3d.js` (`T3.scenes.demo`, `T3.scenes.cutaway`), `film3d.js` (`FX.hud`, `angle`, `trail`, `cue`, `sensor`, `chip`, `pin.set(p, a, dx, dy)`), `scripts/anatomy3d-check.js`, `scripts/anatomy3d-bench.py`, `scripts/fitness-qa.py`, `fitness-gates.py`, `fitness-animatic.py`, `fitness-publish.py`, `fitness-clip.py`, `fitness.py exercise`.
