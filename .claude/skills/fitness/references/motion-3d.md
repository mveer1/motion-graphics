# Tibi in 3D: motion rules, rig and tools

Written 2026-11-12 after the upper-body-workout review: the bicep curl and chest press broke posture and the lats "appeared from nowhere". Everything below was measured on the lab project `projects/lab-3d-motion` (three 6 s clips, one skeleton, orbiting camera) and checked with the numeric and pixel tools named at the end.

## What was wrong with the 2D rig (diagnosis, so it is not repeated)

1. **Art swaps at thresholds.** `sculpt.js armState()` picks a different drawing by joint angle: below 50 degrees shoulder abduction the plain upper arm, above it the no-deltoid arm plus a deltoid cap plus the lat wing (`flare`), and above 60 degrees elbow flexion the flexed upper arm and a fist. Each rep of a curl, press or raise crosses those thresholds, so the shape snaps in one frame. This is the pop. It is structural: a view-per-drawing rig cannot avoid it without morphing between drawings. *Update 2026-11-23 (sculpt kit 2.2.0):* the drawings now blend across per-view angle windows (cap swells, lat wing grows from behind the torso, the arm stays opaque), which removed the edge-mode crossing events on the lateral raise and reduced them elsewhere; a true morph is still impossible (different plane counts), so the 3D rule stands for raises, presses and curls. Evidence: `prompts/state/p05/2d-report.md`.
2. **Views are separate drawings.** A turn is a cross-fade, so only the side, front, back or top views exist and the camera never moves. Lying and reclined poses (bench, incline) mix a side-view torso with front-view anatomy planes, which is why muscles float off the body in the press and curl frames.
3. **Moves are sampled, not continuous.** `RIG.to` with an anchor or IK samples a move at about 10 per second and tweens each piece linearly. Measured on the old render: per-frame motion rises in plateaus of 3-5 frames and steps up, constant velocity in pieces. That reads as "not smooth". *Update 2026-11-23 (sculpt kit 2.2.0):* the 2D Tibi's `t.to`/`t.sequence`/`t.cycle` now drive one setter tween per move that solves the exact pose each frame; the frame-to-frame velocity step on the wrist of a lateral raise fell from 2.10 to 0.72 px/frame (jerk-to-acceleration ratio 1.11 to 0.15).
4. **No gate saw it.** frame-review checks layout, the QA gates check streams and loudness. Only a human noticed. `scripts/motion-continuity.py --mode edge` flags the old press (38.5 s, 40.4 s), curl (209.5 s, 210.6 s) and raise events, and the flagged frames show the arm art changing between variants. Be precise about what a pixel tool can do: those 2D swaps change a thin crescent of the arm, so `edge` mode also fires on fast dumbbells (false positives) and `patch` mode (the default) does not see them at all. Pixels can screen; geometry settles it. For the 3D rig, continuity is guaranteed by construction and checked numerically (`rig3d-check.js`); the pixel tool's job there is colour snaps and anything the numbers cannot see.

## Was Blender used? No

Blender is not installed and was never part of the pipeline (`production.md`). The 2D rig is SVG. The 3D answer here is **Three.js (r158, vendored at `src/studio/vendor/three.min.js`) rendered by HyperFrames' own headless Chrome**, which keeps determinism, the render lock, captions, QA gates and the HTML overlays that the rest of the studio uses. Blender stays an option for photoreal or sculpted anatomy, and is the wrong tool for this look (flat cobalt planes) on an 8 GB host with a one-heavy-job rule.

## The 3D kit

| File | Role |
| --- | --- |
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

1. **Solve lower-body poses from contacts and balance, never pose a frame by hand.** Squat: the hip follows from the shin and thigh angles, and the trunk angle is solved so the bar stays over the midfoot (`T3.squatSolver`), which is what makes the knees-blocked squat lean further (33 vs 51 degrees at the bottom, matching the direction Fry 2003 reports). Hip thrust: the shoulder-blade contact is pinned to the bench edge and the hips rise on an arc around it. Calf raise: the ball of the foot is fixed and the ankle moves (`T3.heelLift`).
2. **A fixed knee turn-out only works when the knee travels far forward.** The blocked squat splayed its knees 59 units off the line of the foot; the turn-out is now solved per frame so the plane (hip, ankle, pole) contains the designed knee, and blended from the toe angle while the leg is nearly straight (there the solved pole is meaningless and twisted the thigh 44 degrees). `kneeTrack` checks within 26 units.
3. **A muscle under clothing rests in the cloth colour and warms through a deep role colour.** Through the pale tint it flashed on the dark shorts and partial activation read as a brown stain (found by the pixel tool on the motion-only render, at 0.27 s of the hip thrust). Limit colour, not only activation: `rig3d check` fails a colour change above 0.12 per channel per frame; sets ramp in over 1.0 s and fade over 1.2 s (0.6 s moved a colour 0.17 per frame).
4. **Side views of a barbell lift sit at az ~72, not 90.** At 90 the near plate covers the head and neck. Plates radius 46 (technique plates), not 62.
5. **Solve the camera from the layout, not by eye.** px per unit = 1280 / (0.4617 * dist) at fov 26. Take the standing height at the top of a rep (~840 units with the spark), the header bottom (~y 300-330) and the caption top (~y 900-915): e.g. top >= 330 and floor <= 895 gives dist ~4150, ty ~380 for a two-shot. In a calf film the heels must never sit under the caption plate. Close-ups that put the body behind the header need a paper plate under the title.
    Since 1.13 the kit solves it: `T3.scene(stage, id, {shot, fit: {rect: [left, top, right, bottom]}})` (or `fit: {margin}`) keeps the shot's az/el/fov and sets dist and target so every posed skin vertex, rigid part and prop stays inside `rect` through the whole set (`T3.fitScene`, `stage.fit`, `T3.framePoints`). Measured on a 720x1280 stage, the fixed `def.camera` loses up to 195 px of the press, 178 of the raise, 108 of the hip thrust and 17 of the front squat. `rig3d-check` fails a fitted shot that loses anything between its samples; `rig3d-stills.py --fit 0.04` uses it.
6. **Two figures: one world or two views.** Side by side in one world (z apart; camera at +x looks along -x, so +z is screen-left) for comparisons in the same pose; `stage.views` for a vertical and a horizontal lift together (each view its own camera and only its own figures, one canvas, scissored). `m.at` applies every started path in start order, so two figures can run paths at the same time (before, only the latest path applied and the other figure froze).
7. **Overlay text that follows the skeleton is a pure function of t** (`T3.film` in `onFrame`), and a label's text may change with t (`pin.text`). Tags over two figures are centred (`center: true`); side-anchored tags were clipped at the frame edge.

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

On Windows, call the sheet scripts with `.venv\Scripts\python.exe`. Both share `src/pipeline/browser_stills.py` (existing Puppeteer cache or `CHROME`, encoded file URLs, isolated profile, fresh-image and page-readiness checks). They fail rather than reuse an old cell when Chrome cannot render. The Mac cache layout and host lock remain in use; Windows results are preview evidence, not Mac render-host approval.

## Known limits of the 3D kit (runtime 1.14.0, anatomy 1.4.0, Tibi 0.6.0, 2026-11-23)

Fixed in 1.14.0, each with a gate in `anatomy3d-check.js` or `rig3d-check.js` that fails on the old shape (evidence `prompts/state/known-limits/`): the round glute ball under the shorts (now a profiled fan; gluteal-hip roughness gate), effort tint blobs through the shorts, the pale abs block and dark-red stains under cloth (tint weighted by the muscle's own shape, one straight ramp to a subdued tint under cloth), concentric rings in the glute cutaway (the deep stage now wipes the broad gluteus maximus from one edge instead of punching a centred hole), square female deltoids, the shoulder ridge at 90 degrees abduction (wider chest-to-arm weight blend), inner-fold crush at elbow 150, knee 150 and hip 120 (pose-driven correctives keep at least 0.6 of the resting fold distance), the rigid ponytail (damped follow-through as a pure function of the motion, rests on benches), the flat back on the bench (`T3.solveArch`, arch 22) and the two-piece shoe (one bending sole, heel rocker and toe-off via `T3.footRoll` and pose key `tf<side>`).

Still limited:

- Library: curl, bench press, lateral raise, back squat (and knees blocked), barbell hip thrust, standing and seated calf raise, plus the exercises added by prompt 04 (see the exercise list in `exercises3d.js`). Knowledge records marked `rig3d_status: "pending"` in `exercises.json` have no 3D yet.
- Shoulder at cross-body reach and overhead 175 still crushes (linear-blend skinning). A shoulder corrective moves torso skin as the arm rises, which the anti-lat-bulge gate forbids; it needs a scapula or twist-bone rig.
- Hip 120 loses about 3.5 % volume on the outer, gluteal side; the radial corrective cannot fix it without stretching the squat fold. The cutaway's inner muscles do not get the correctives. One hidden triangle in the inner elbow crease stretches 5.9x in the curl.
- Look: one toon-shaded skin with muscle relief. It reads as Tibi (cobalt, marigold spark, white shoes) but not as the 2D art's crescent shading (owner decision pending). Hands are stylised mittens; the female top is a torso-owned band, not a tailored garment; lat flare from the front is a design call.
- The ponytail is one rigid tail (it cannot drape around an edge; on the hip thrust it tucks toward the nape) and costs about 11-15 ms per female frame in node. The bench arch is carried by 22-25 degrees of neck bend because the spine has two bones. The heel rocker and toe-off are tested but no film walks or runs yet. The shoe upper compresses at the crease with no wrinkle.
- The glute cutaway's deep stage reads as a wipe, not a growing hole (a look call); the marigold tint under the shorts is faint.
- No cloth simulation. Kinematics are authored key poses, labelled "illustrative", never mocap.
- Render cost: HyperFrames compile spends most of its first minutes fetching Google Fonts the first time; per-frame WebGL on SwiftShader is software-rendered. Measured numbers are in `qa/` of `projects/lab-3d-motion`.
- The vendored three.min.js is r158 (the last release with a classic global build; it prints a deprecation notice that is harmless). Moving to a module build means changing how compositions load it.

## Lab results (projects/lab-3d-motion, 2026-11-12)

Three clips, 18.8 s, 720x1280, 30 fps, 564 frames, one skeleton, orbiting camera (`qa/contact-sheet.png`, `qa/rig3d-check.json`, `qa/continuity-patch.json`).

| Measure | Result |
| --- | --- |
| `rig3d check` (curl, press, raise, both genders) | all pass: no teleport spike (worst step/neighbour 1.07), muscles never hidden (smallest 87% of rest size), planted soles 0.00 units off the floor, IK in reach, elbow 0-144, knee 0-90, press forearms within 12 degrees of vertical, largest activation colour step 0.087 per frame (limit 0.10) |
| `motion-continuity` patch mode, final render | curl and raise: no event; press: one event of 0.05% of the region at the start of the activation ramp (a gradual colour onset, three frames, not a pop) |
| Defects the tools found and that were fixed | (1) press forearm up to 25 degrees off vertical with straight-line IK targets, fixed by building the elbow arc and holding the wrist a forearm above it; (2) velocity steps from sampled linear moves, fixed with `m.path`; (3) raise with an undeclared `lean` base became NaN and the whole upper body vanished from the render (the 14 s snapshot showed legs only); (4) activation fade-out of 0.2 s snapped the colour in one frame (found by the pixel tool, now also a numeric check) |
| Render | first compile 3 min 53 s (Google Fonts fetch), then 18-26 s compile, capture 25-27 s for 564 frames (about 21 frames per second), total 26-46 s, 5.6 MB, "hardware gpu", `--low-memory-mode` |
| Peak memory | not measured |
| Not done | the nine other exercises, a full 3D film with narration and captions, a human creative review of the look against the 2D art |

## Lower-body shorts (2026-11-12)

Three narrated shorts, portrait, series `sinew-lower-body-3d`: `knees-past-toes` (Fry 2003), `hip-thrust-vs-squat` (Plotkin 2023), `standing-vs-seated-calf` (Kinoshita 2023). Production notes in each `qa/production-report.md`.

| Measure | Result |
| --- | --- |
| `rig3d check` (8 exercises, both genders) | all pass; worst teleport ratio 1.09; knee tracking within 10 units (blocked squat 59 before rule 10); ball drift 0.00 in heel lifts; worst colour step 0.109 per frame (0.179 before rule 11) |
| Render | 71-78 s per 46-53 s film (720x1280, 30 fps, `--quality looks`, `--low-memory-mode`); a draft motion-only pass about the same |
| QA gates | all five pass on all three (-17.3, -17.2, -16.7 LUFS before the final re-render) |
| Pixel pops, motion layer only | camera cuts only, plus the glute flash (fixed, rule 11) and two activation ramps that look identical frame to frame |
| Defects found and fixed | knees splayed off the foot line (rule 10); thigh twist at standing (rule 10); a bench missing after an edit commented out its `stage.world.add` (new orphan-prop check); plate over the head in side views (rule 12); captions over the knees, the glutes and the heels (rule 13, caption lane `lower` in the hook); tags clipped at the frame edge (rule 15); glute flash and brown stain (rule 11); Whisper stretching a scene's last word into the next scene (captions clamp, src/pipeline/captions.py); respelled words reverting in captions on every re-run (`display_spellings` reads research.json's phonetic lexicon) |
| Not done | a human creative review of the 3D look against the 2D art; a long-form 3D film; the remaining lower-body lifts (limits above) |

## Anatomy 1.0 and the instructional layer (2026-11-13)

The body is now one continuous skin (`kits/fitness/anatomy3d.js`, skill `fitness-anatomy`); the old rigid-ellipsoid muscles are gone. New pose keys: `cut.<window>[@L|@R]` (0 closed, 1 skin out, 2 superficial layer out), `hi.<muscle>`, `view.ghost`, `view.layer`, `view.skel`, `view.effort`, `iso.<muscle>`. `fig.world('muscle@side')` is now a point ON the skin over that muscle (rides bulges and joints). The bind pose is an A-pose, so bones rest straight but the mesh was built with arms 26 and legs 4 degrees out.

 1. **Every motion key carries the figure id prefix, including those returned by `m.path` callbacks.** A path that returned `hxL` instead of `b.hxL` froze the dumbbell press in every composition (the stills bench has no id, so it worked there). `rig3d-check` now builds figures with an id and fails on a range of motion under 90 units (heel raises declare their own `minRom`).
 2. **Every exercise declares a `phaseMap`** (fractions of the rep period: start, eccentric, end range, concentric, lockout, reset; kind up, down or hold). `T3.phaseAt(def, {at, period, reps}, t)` and `T3.phaseTimes` expose it; the HUD, cue cards, 2D comparison and sound read it. `rig3d-check` fails when hold phases move or lifting phases do not.
 3. **Highlights are defensible**: each `acts` role (3 prime, 2 helper, 1 stabiliser) must be listed in `assets/fitness/data/exercises.json` for the exercise named in `knowledge`; `fitness.py check` audits it.

Tools added: `scenes3d.js` (`T3.scenes.demo`, `T3.scenes.cutaway`), `film3d.js` (`FX.hud`, `angle`, `trail`, `cue`, `sensor`, `chip`, `pin.set(p, a, dx, dy)`), `scripts/anatomy3d-check.js`, `scripts/anatomy3d-bench.py`, `scripts/fitness-qa.py`, `fitness-gates.py`, `fitness-animatic.py`, `fitness-publish.py`, `fitness-clip.py`, `fitness.py exercise`.

## Seek-order corrections (runtime 1.9.1, 2026-11-20)

 1. **Cache exact skin outputs, not rounded signatures.** A 0.01-degree elbow
    change or 0.00001 activation change could leave a neighbouring pose's
    arrays cached. `anatomy3d-check` now requires zero array difference on return
    to the same pose.
 2. **Set the toe pose in both leg-control branches.** Direct-angle (FK) legs
    reset the toe hinge instead of retaining the last solved-contact (IK) heel
    lift. `rig3d-check` verifies the switch.
 3. **Apply `T3.bind`'s `onFrame` before drawing, after current cameras are
    prepared.** Scene visibility set by the callback belongs to this frame, not
    the next one. Pins still project through this frame's cameras, including
    split views. Do not read completed canvas pixels inside `onFrame`; capture
    after the timeline seek returns.
 4. **Projection-camera copies contain no scene children.** Copying the light
    and its target every frame accumulated objects in each split-view camera.
    The real render camera retains its light rig.
 5. **Restore the shader variant when ghost mode closes.** Restoring opacity
    and side flags alone left small history-dependent pixel differences.

`python scripts/rig3d-seek.py --out qa/rig3d-seek` runs twenty temporal cases
(ten cases, both bodies) in one locked browser and writes a JSON report,
labelled comparison sheets and a thumbnail overview. `--baseline <report.json>`
adds the starting verdicts. It checks temporal parity, not the full anatomical
pose/camera matrix or G3 accuracy.

 1. **A profile's station coordinate is not its row number.** Runtime 1.9.2
    offers `profileSampling: 'distance'` on `stage.tibi` and `T3.scene`.
    Uneven trunk/limb stations previously fed an evenly indexed lookup table;
    this displaced the shoulder contour and opened visible gaps. The
    correction is opt-in because it changes the silhouette. Keep `legacy`
    as the default until the owner decides; never silently opt films in.
    No muscle shape, attachment or palette was redesigned.

Check either variant with `anatomy3d-check.js --profile legacy|distance`,
`rig3d-check.js --profile legacy|distance` and the seek tool's matching flag.
The corrected core must meet the authored torso contour to half a mesh cell;
the actual checker rejects deliberately restored row-index sampling.
`anatomy3d-bench.py --set matrix --gender both` defines the broader 240-cell
camera/joint/cutaway/phase slice and a reviewed, thumbnail-based HTML report.
The prototype does not settle garment tailoring, extreme-pose self-contact,
muscle fidelity or human G3 approval.

Portrait fitting example, Windows 2026-11-20: the resting distance-profile
candidate at `az=25, el=10, dist=4150, ty=360` fits y=344.95..890.12 at
720x1280. The earlier approximate `ty=380` trial failed the shoe boundary.
Use all posed mesh/accessory bounds, not only joints, and re-fit for a different
pose or equipment. The default raise bench still crops dumbbells at end range;
the diagnostic camera is not a universal production preset. Use `fit` (rule 13).

## Integrated body rules (1.10.0, 2026-11-20)

 1. **One mesh does not prove anatomy.** Inspect normal and clay region sheets.
    Lats are broad embedded fans, deltoids a tapered cap, pecs a broad fan and
    rectus a pair of continuous bands. Exterior-looking lobes are failures.
 2. **Normals belong to the figure and the current morph.** Recompute after
    bulge positions change; never mutate the cached base normals. Seek checks
    include normal fingerprints as well as positions/colours.
 3. **Measure the rendered colour inputs.** Fixed coverage weights mix
    per-vertex ramps inside the RGB gamut. Multiplying an already animated
    ramp by activation doubled its slope; actual skin/cloth array checks
    found the regression even though the individual ramp records passed.
 4. **Cloth follows the torso, not arm-dominated skin.** The top uses an
    ownership mask and analytic band edges; a coarse vertex-only edge looked
    torn. Its thickness is not a substitute for a tailored silhouette.
 5. **A skinning replacement must improve the actual joint.** The first DQ
    trial stretched overhead triangles more severely and was rejected.
    Do not adopt a fashionable algorithm or relax a gate without local
    before/after evidence.
 6. **Inspect supporting volumes, not only muscles.** The 1.10 deltoid pass
    missed an exposed joint sphere and flat-ended arm core. The full posed
    shoulder contour must descend from the neck without a perched crest;
    the 1.11 checker measures the actual mesh, including unmasked parts.
 7. **Separate geometry from stance.** Show identical-pose before/after
    images, then the intended neutral stance. `fig.defaultPose` supplies
    current neutral values; `T3.DEFAULT_POSE` retains authored-motion
    fallbacks. Never silently treat a changed posture as proof of a mesh fix.
 8. **A sheet muscle is thin along the surface normal.** The 1.10 serratus
    put its 10-unit radius along x, the flank's normal, and ended in a ledge
    under the arm; a glute-medius egg and the flat top of the leg tube did the
    same at the hip. Check the projected flank/hip width row by row (1.12
    `flank` gate), and look at a straight front view of the torso.

The current 3D default is `profileSampling: 'distance'`; explicit `legacy`
is a compatibility reference. Public pose keys/timing and 2D art remain
unchanged. Runtime 1.11 changes the neutral arm stance, not authored lift tracks.
See `docs/fitness-studio.md` sections 9-10 and the source references in
`assets/fitness/data/muscles.json`. Human anatomy/biomechanics approval is still
required; neither the local tests nor the design review manufactures it.

## Known-limit corrections (runtime 1.14.0, 2026-11-23)

 1. **Secondary motion is a pure function of the motion.** The ponytail samples
    `motion.at(t - k/30)` (the non-enumerable `__src` on a pose) through a ghost
    trunk chain; it never stores frame-to-frame state. A copied or hand-built
    pose dictionary has no history and gets the static hang. Rig-wide
    `ponytail-follow-through` and a seek-order case check it.
 2. **Lying and resting contacts are solved from the skin.** `T3.skinLow` gives
    the lowest skin point per bone over a pad; `T3.solveArch` solves pelvis
    tilt, height and neck flexion so glutes, shoulder blades and head rest on
    the bench; exercises register supports with `T3.restsOn` so hair cannot
    sink into them.
 3. **A sheet thinner than one mesh cell meshes as creases.** The round-1 glute
    fan (edges 1-3 units, cell 3.5) passed every numeric gate and crumpled in
    clay. Keep sheet minimum thickness at 0.6 of the belly; the gluteal-hip
    roughness gate (sharpest neighbouring-normal angle, limit 40 degrees)
    catches it. Look at clay, not only the coloured body.
 4. **A broad sheet in a cutaway is wiped from an edge, not holed from the
    centre.** A centred hole leaves a ring of the top layer around it; the
    glute window's deep stage sweeps from the medius side (ring-scanline gate).

## Exercise library and hinge/split/prone solvers (Tibi 0.7.0, 2026-11-23)

3D exercises: curl, press, raise, squat, squat-blocked, hipthrust, calfraise, seatedcalf; then deadlift, deadlift-rounded (mistake: rounded back), romanian-deadlift, split-squat, split-squat-valgus (mistake: front knee caves in), forward-lunge, push-up, push-up-sag (mistake: hips sag) and plank (a static hold with breathing drift, on a mat). Solvers: `T3.hingeSolver` (bar over midfoot, bar on the legs, a spine that hinges without rounding; `round` bends it), `T3.splitSolver` (front-shin angle, knee over the foot line, upright trunk; `kv` caves the knee), `T3.proneSolver` (hands under shoulders, a shoulder-ankle line; `sag` drops the hips). Helpers: `T3.palmFrame`, `T3.com`, `T3.spineFlex`, `T3.trunkAngle`, `T3.barLegGap`, `T3.hipLine`, `EQ.mat`. One-page sheet of every exercise: `prompts/state/p04/library-sheet.png` (not in git).

Pose keys: `kwS` (S = L or R): 1 makes the knee pole a world-frame direction (the yaw of the foot), so a knee tracks the foot line whatever the pelvis does (split stance, lunge). `kvS`: knee valgus in degrees; with `kwS = 1` the pole yaws inward by `kvS` (mistake variants only).

 1. **A contact the cue is about is measured on the posed skin and fed back into the solver** (bar on the legs, palm on the floor, forearm on the mat, back knee above the floor). Fixed offsets were 4-6 units wrong between bodies and skin profiles.
 2. **A solver root near a degenerate pose (a straight leg) is followed from the last depth**, never bisected over the whole range.
 3. **Hair hangs with gravity in every orientation**: a jointed tail (root plus free end) relaxed against a mirrored, symmetric skin point cloud with a smooth kernel; never a nearest-point rule (asymmetric, spiky) and never a sideways slide off the nape. Still a pure function of `motion.at(t)`. Gates (female): upright sideways tilt at most 3 degrees; face down, the tail tip within 50 degrees of gravity and at most 66 units from the head midplane.
 4. **A mistake variant is the correct exercise's solver with ONE parameter changed**, and its own check inverts the correct check (the mistake must be measurable at its worst frame).

Checker fix (2026-11-23): the reach, shoulder-limit and lifted-foot gates read unprefixed pose keys (`v['ik'+s]` instead of the figure-prefixed key), so they never ran. They run now, and `tests/test-rig3d.py` proves each one bites. New exercise gates: bar horizontal drift and spine flexion (hinge), front-shin angle and front-knee lateral drift (split), shoulder-ankle line and hand under shoulder (prone), and "the hold freezes" (plank).

Limits of this family: Tibi's thick thighs force a small second knee bend mid-deadlift and more RDL knee bend than many coaches show; push-up and plank knees stay about 8 degrees bent (the leg-reach gate forbids a locked leg); toes stand on their tips at the 45-degree toe-bend limit; the ponytail hangs but does not drape over the shoulder; only a left-leg-forward valgus variant exists.

## Shoulder girdle (Tibi 0.8.0, anatomy 1.6.0, runtime 1.15.0)

32b. **The shoulder is a girdle, not a hinge on the chest.** Each arm hangs from a girdle bone (`gdL`/`gdR`, scapula + clavicle) driven by the humerus (`T3.GIRDLE`: about 1 degree of scapular upward rotation per 2 at the joint above 20, 59 at 175; clavicle elevation to 12; protraction to 18 on forward/cross reach) plus a soft-tissue bone (`axL`/`axR`) that trails the humerus near the joint. IK hands land exactly; FK hands ride the shoulder. Use `gpS`/`geS` only when the cue is about the blades. Measure shoulder-relative cues against `fig.bone.shS`, not spec constants. Skin weights: `A.GIRDLE_WEIGHTS` (field stops 70 under the joint). Gates in `anatomy3d-check`: `shoulderCrush` (cap >= 0.7 of its distance; no armpit skin within 10 units of the joint centre; at most 0.5% inside-out rays), `armpitLift` (20 / 32 / 45 units at abduction 90 / overhead 175 / overhead abduction), `latInflation` (no lat lift through the morph or the bones). `A.GLIDE` (ribcage glide) is an experiment, off: switching it on fails the inside-out gate.

Limits: overhead, girdle-carried trunk skin still lifts off the ribs beside and behind the armpit ("wings"); from the side the armpit shows a flap and a dark pit; the female top's edge makes a corner where it meets the raised arm; across-body reach is only modestly better; axial +/-90 keeps its twist fold; the scapula does not slide, wing or tilt on the ribcage. Owner decision pending on one more fix round (`prompts/state/decisions-needed.md`).

## Machines, barbell bench and rack (motion family 2, 2026-11-24, runtime 1.15.0)

3D exercises added: leg-extension, leg-extension-misaligned (mistake: knee off the pivot), leg-curl (seated, thigh pad), leg-curl-short (mistake: the return stops at 48 deg), leg-press (45-degree sled), leg-press-deep (mistake `pelvis-lifts`: the pelvis rolls back, hips leave the pad), barbell-bench-press, squat-rack (back squat in a power rack with J-hooks and safety pins). Not yet: overhead press, row, pull-up, lat-pulldown, seated-cable-row, running gait.

Solvers and helpers: buildKneeMachine (lever pivot on the knee, roller solved on the shin skin, lap pad), buildLegPress (sled along d, ankles exact, legs `T3.legFK` to a tilted sole, back pad = common tangent of glutes and upper back, rolling pelvis past the hip limit), buildBenchBarbell (wrist driven, elbow solved in the side-view plane, bar posed at the fists after every apply), squatRack; `T3.legFK`, `T3.legKeys`, `T3.skinScan`, `T3.rollerGap`, `T3.planeGap`, `T3.benchRest`, `EQ.box/rod/disc/stack`. Pose key `mach.<k>` (figure-prefixed) carries a machine part's state; parts are posed after every `fig.apply`. The ponytail clearance gate counts girdle-bone skin (`gdS`, `axS`) as body.

 1. **Solve a two-link path from the quantity the gate limits.** Interpolating the upper-arm direction let the arm straighten past the IK reach mid-descent; driving the wrist distance from the shoulder keeps the elbow bend monotonic.
 2. **A held bar is posed from the hands** (midpoint of the fists after every apply), never the hands from a bar path.
 3. **A tilted prop is a support and an obstacle in its own frame**: register it as thin slices for the hair and test intrusion in the mesh's local box.
 4. **Do not show the contact the cue is about behind equipment**: plate horns below a leg-press platform; the bench side camera looks down 45 degrees over the near plate.

Limits: thigh-to-belly gap at the leg-press bottom is checked by eye only; leg-press hip flexion about 128 deg (beyond the hip-120 corrective); push-up-sag (female) ponytail body intrusion 0.91 units (passes the gate, a near miss; a fix needs tibi3d.js); no unrack in the rack squat.
