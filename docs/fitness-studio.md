# The Sinew fitness studio: architecture, decisions, open items

Written 2026-11-13 after two assignments given together: upgrade the fitness workspace into a professional content studio (P1) and redesign the anatomy so muscles belong to the body (P2, mandatory and first). This is the map, the audit, the decisions and what is not done. The skill entry point is `/fitness` (`.claude/skills/fitness/SKILL.md`).

Current 3D development body: runtime 1.10.0, section 9. The 1.9.x opt-in
notes below are historical; they are not the current default.

## 1. Architecture map (what exists, what talks to what)

```
brief + dossier (research)  ->  script/storyboard (story-writer)  ->  animatic + pacing lint
        |                                |                                   |
 assets/fitness/data/exercises.json  (knowledge: roles, phases, mistakes) -> fitness.py exercise (explanation plan)
        |                                |
 src/studio/kits/fitness/                |   one skin, one muscle table             -> scripts/anatomy3d-check.js, anatomy3d-bench.py
   anatomy3d.js  <- tibi3d.js (rig, stage, motion, bind) <- exercises3d.js (lifts, phaseMap, acts)
   film3d.js (HUD, pins, sensor, chip, angle, trail, cue)  <- scenes3d.js (demo, cutaway)
 2D: sculpt.js / exercises.js / graphics.js (mascot art, cards, charts)
        |
 composition (HTML, one paused GSAP timeline, pure functions of time)  -> hyperframes render (host lock)
        |
 audio: build-audio.py (Kokoro), captions (Whisper), sinew_sound.py (bed, SFX from phase map)  -> ffmpeg mux, loudnorm
        |
 QA: studio.py build gates (5) -> fitness-qa.py (diagnostics) -> fitness-gates.py (G1-G4, human sign-off) -> fitness-publish.py / fitness-clip.py
```

Retained unchanged: studio runtime and determinism rules, the render lock, the form system, the style template `body-lab`, the 2D Cobalt Sculpt generator (`src/fitness/tibi/`), the dossier protocol, the captions and sound stacks. Nothing was replaced for taste.

## 2. Audit findings (before any change)

| Finding | Evidence | Fixed by |
| --- | --- | --- |
| Muscles were rigid ellipsoids parented to bones over a skinned loft body: raised stickers, no deformation, glute and calf "attached" | `tibi3d.js` 0.2 `ell()`/`M()`; the three lower-body films | `anatomy3d.js`: one skin (ADR-1) |
| The dumbbell press never moved in any composition | `m.path` returned unprefixed keys; figures with an id ignore them; stills bench used no id | prefix fix, `rig3d-check` builds figures with an id, range-of-motion and phase-fidelity checks |
| The supplied 2D-vs-3D clips began on a stale pose, had no audio, compared an incline curl with a standing curl, at different scale and out of phase | `fitness-qa.py` on the originals: frame 0 jumps 48.1 vs 0.4; no audio | `qa/regression/lab-3d-compare` (one phase clock, equal scale, same variant), narrated lab clips |
| `lat` lit on the lateral raise with no basis; nothing audited highlights against knowledge | exercises3d vs exercises.json | `fitness.py check` role audit; lat removed |
| No instructional layer (rep, phase, angle, path, cue) and no scene reuse | the lab and film compositions | `film3d.js` HUD/angle/trail/cue/sensor/chip, `scenes3d.js` |
| QA saw layout and loudness only | `run-qa-gates.sh`, `frame-review.py` (needs Playwright, absent here) | `fitness-qa.py`, `anatomy3d-check.js`, gates with human sign-off |
| `titleCard` always faded in: a bare first frame | `fitness-qa.py` start check on the calf film | frame-0 rule in `graphics.js` |
| Runtime code used `performance.now()` | `hyperframes lint` (non-deterministic) | removed; timing lives in the test scripts |

## 3. Decisions (ADRs)

**ADR-1 Anatomy: one skin, one muscle table.** Rejected: (a) recolouring the old ellipsoids, (b) a transparent duplicate body over an opaque one, (c) baked sculpted mesh data. Chosen: signed-distance fields smooth-unioned from cores and muscle volumes, meshed once at load, A-pose bind and region-vote weights. One skin prevents separate-object drift, not exaggerated or anatomically wrong relief. The table yields the surface, masks, internal lofts, windows and anchors. Initial cost was about 25k vertices; the current integrated body uses about 36-39k and is measured per pass. It remains illustrative, without sliding-skin simulation. A sculpted GLB remains a separately approved alternative, not a dependency adopted here.
**ADR-2 Character: refine the blue Tibi, do not replace it.** The recognisable silhouette, palette and spark are the brand. Two bodies (m/f), four modes (normal, activation, anatomy, 2D storytelling) instead of four characters.
**ADR-3 Activation on the skin, computed on the CPU.** Per-vertex arrays give node and browser the same values. Current colour ramps start at each vertex's own resting colour and mix with fixed normalised coverage; overlapping masks cannot add light or double the fade slope. Cloth retains its deeper colour variant.
**ADR-4 Cutaways are windows in bind space, evaluated per fragment.** They stay registered and open in two stages (skin, then the superficial layer). Internal geometry is fitted inside the resting skin envelope. This does not certify every posed muscle/bone intersection or clinical layer geometry.
**ADR-5 A visual language with one meaning per colour** (see `assets/fitness/STYLE.md`): skin, effort, anatomy, ghost, measurement never share a colour. Sensors are drawn as sensors.
**ADR-6 Animation: authored key poses plus solved contacts, hybrid.** Mocap and external libraries were not adopted: the lifts are few, the poses are solved from contacts and balance, and an authored curve is explainable and "illustrative" by honest label. Revisit with a measured-motion source if a film needs real kinematics.
**ADR-7 One phase machine per exercise**, in the kit, read by the HUD, the cue cards, the 2D comparison rig and the sound: picture, sound and teaching share one rhythm.
**ADR-8 Automation fails, humans approve.** G1 and G3 (accuracy) need a named human in `qa/fitness-signoff.json`.
**ADR-9 No new dependencies.** Three.js (vendored), Chrome, ffmpeg, node, numpy, Pillow were already present.

**2026-11-20 addendum to ADR-1/3/4:** one connected skin prevents separate-object
drift, not exterior-looking anatomy. The full-body review found lat lobes,
pectoral discs and abdominal buttons despite numeric passes. The distance
body now uses embedded profiled fans/bands, per-vertex convex colour ramps
and exact local morph normals. Fitting internal vertices into the resting
envelope does not prove all posed pairwise intersections absent. Report
boundary and non-manifold edges separately; neither a mesh count nor a
generic triangle quantile is human anatomical approval.

## 4. What was verified, and how

- `node scripts/anatomy3d-check.js`: connected skin, open/non-manifold counts, resting internal-envelope checks, selected layer rays, soft masks, registration and triangle-area quantiles in five poses. These measurements do not certify every triangle, intersection or anatomical claim.
- `node scripts/rig3d-check.js`: all 8 exercises x 2 bodies: continuity, contacts, reach, limits, colour steps, range of motion, phase fidelity.
- `scripts/anatomy3d-bench.py`: contact sheets (`qa/anatomy3d/`) looked at, not only measured.
- Nine regression videos re-rendered and run through `fitness-qa.py` (see `qa/fitness-render-qa/`); the three lower-body films before/after compared frame by frame.

## 5. Not done, or limited (be honest)

- No human creative review or accuracy sign-off was recorded: `qa/fitness-review.json` rubrics are unscored, `qa/fitness-signoff.json` does not exist; gates G1 and G3 are awaiting a human.
- The look is stylised: the current body uses embedded fans/bands and limb volumes, but no full tendon/fascia model or skin sliding. The skeleton, hands and joint mechanics remain schematic; do not teach exact attachment sites from this character.
- The female top is a thinner, torso-owned colour region with analytic edges, not cloth simulation. The male shorts hem remains a small step. Legacy retains the earlier garment/body defects.
- Runtime 1.14.0 (2026-11-23) fixed the named acceptance limits (glute ball, effort tint under cloth, glute cutaway rings, female deltoid, shoulder ridge, fold crush at elbow/knee/hip, rigid ponytail, flat bench back, two-piece shoe); the remaining ones are listed in `.claude/skills/fitness/references/motion-3d.md`, Known limits. The shoulder at cross-body and overhead reach still crushes: it needs a scapula or twist-bone rig.
- Cutaway windows exist for calf, glute, quad, hams, upper arm (front and back) and chest; chest/arm/hams windows were built but only calf, glute and quad were composed into films.
- Deadlift, lunge, leg press, curls on machines, running are not ported to 3D. Kinematics remain authored.
- Historical 2026-11-08 limitation: the Yellow Dude production page then attempted returned 404. The published 2026 production account was retrieved on 2026-11-20; its process descriptions remain publisher-reported, not independently audited. See section 11. No full reference-video/audio study is claimed.
- Text-outside-safe-area and label-overlap checks are visual (snapshots), not automated: `frame-review.py` needs Playwright, which this host lacks.
- The compare fixture is a regression asset (`qa/regression/lab-3d-compare`), not a publishable project.
- Peak render memory was not measured; builds ran one at a time under the host lock.

## 6. Windows character-review loop

Use the existing Python 3.12 environment (`.venv\Scripts\python.exe` in PowerShell)
and set `$env:PYTHONUTF8 = '1'` for the older generator scripts. The two 3D sheet
tools share `src/pipeline/browser_stills.py`: it honours `CHROME` first, then
finds the platform's executable in the existing Puppeteer headless-shell cache.
An invalid explicit `CHROME` path is an error, not a silent fallback.

```powershell
& .\.venv\Scripts\python.exe scripts\anatomy3d-bench.py --set angles --out prompts\state\evidence\anatomy
& .\.venv\Scripts\python.exe scripts\rig3d-stills.py curl --times 0,1.0 --out prompts\state\evidence\curl.png
```

Both tools retain the host lock and SwiftShader rendering. Local file URLs are
encoded with `Path.as_uri()`, and each capture uses a temporary browser profile.
A process failure, unfinished bench page, missing image or wrong image size
stops the sheet; an old cell is never accepted as a new capture. These are
preview tools, not anatomical approval or final-film QA.

For a non-destructive 2D rebuild, set `TIBI_OUT` to a scratch directory before
running `src\fitness\tibi\page6.py`, then compare bytes with the existing review
page. Also compare with the Git blob: a CRLF checkout can match its own rebuild
while differing from the Mac's LF bytes. Do not bulk-normalise the approved
generator assets or change Git attributes without the owner's decision.

No new dependency is required. macOS still uses its original Puppeteer cache
layout; real Mac execution must be checked separately from Windows tests.

## 7. Temporal acceptance (runtime 1.9.1, 2026-11-20)

The same target must render the same way after any previously visited frame.
An initial twelve-case matrix found and fixed five mechanical defects without
changing body geometry, the muscle table, shading targets or approved 2D art:

| Defect | Correction | Regression |
| --- | --- | --- |
| Rounded skin signatures reused a nearby pose's arrays | Exact output signature, all colour channels | `anatomy3d-check` seek-order arrays; anatomy unit test |
| A direct-angle leg retained the previous heel-lift toe rotation | Reset the toe in the FK branch | `rig3d-check` direct-leg seek; rig unit test |
| Scene callbacks changed visibility after the canvas was drawn | `onFrame` after camera preparation, before draw | Rig unit test; named single/split figures in real suppressed-callback GSAP seeks |
| Split projection cameras copied lights repeatedly | Fresh childless projection camera; non-recursive copy | Rig unit test and browser object counts |
| Ghost-to-normal left the previous shader variant | Mark the restored material for recompilation | Real browser pixel comparison |

`T3.bind`'s callback signature is unchanged. Its timing is now explicit:
overlays and visibility update before rasterisation; callers that need finished
canvas pixels must read them after the seek returns. Ordinary `stage.render()`
still works; its optional `beforeDraw` callback runs after camera preparation.

```powershell
& .\.venv\Scripts\python.exe scripts\rig3d-seek.py --out qa\rig3d-seek
& .\.venv\Scripts\python.exe scripts\rig3d-seek.py --out qa\rig3d-seek-after --baseline qa\rig3d-seek\report.json
```

Presets: `skin`, `feet`, `scenes`, `modes`, or `all`; bodies: `m`, `f`, `both`.
The report includes fresh/revisited/difference sheets, thumbnails, numeric
state fingerprints and cold/warm timing. All twelve cases failed before and
pass after on Windows. This is a temporal acceptance slice, not an exhaustive
anatomical matrix, a human accuracy approval or Mac render evidence.
The source of the benchmark is `assets/fitness/lab3d/seek-bench.html`.

## 8. Profile-coordinate correction and broader acceptance (1.9.2)

The shoulder gaps were not only a skin-weight problem. `makeTube` indexes its
lookup table by distance along a limb or trunk, but the original `sampleKeys`
spaced samples by row number. The authored torso/limb stations are unevenly
spaced: a shoulder-width station was effectively moved down the trunk.
Widening the skin-weight blend did not remove the gaps; distance-based
sampling did. No muscle-table shape, attachment, palette or 2D art was edited.

The correction changes the silhouette, so it is **opt-in pending the owner's
look decision**, not a new default:

```javascript
const fig = stage.tibi({gender: 'm', id: 'a', profileSampling: 'distance'});
const demo = T3.scene(stage, 'curl', {gender: 'f', figId: 'b', profileSampling: 'distance'});
```

Omitting `profileSampling` (or choosing `legacy`) retains the old geometry.
Each body/profile has its own immutable geometry cache; figure-local dynamic
arrays remain separate. Unknown profile names throw. Studio 1.9.2 packages
Tibi 0.2.2 and anatomy 1.0.2; upgrading a project does not opt it in.

`anatomy3d-check.js --profile distance` adds a profile-station gate: the core
signed-distance value at each authored torso contour point must be within
half a mesh cell (2.25 rig units at the current resolution). The legacy
profile's mismatch is printed as a known limit, not hidden. An in-memory
mutation that restores row-index sampling makes the **actual checker** fail.
Both profile variants still run the existing topology, internal-layer,
coverage, deformation and registration checks. Eight non-manifold edges
in the legacy body meant four incident triangles per edge, not eight open
holes; the existing topology tolerance is unchanged.

```powershell
node scripts\anatomy3d-check.js --profile distance --json
node scripts\rig3d-check.js --profile distance --gender m --json
node scripts\rig3d-check.js --profile distance --gender f --json
& .\.venv\Scripts\python.exe scripts\anatomy3d-bench.py --set matrix --gender both --out qa\anatomy-legacy
& .\.venv\Scripts\python.exe scripts\anatomy3d-bench.py --set matrix --gender both --profile distance --out qa\anatomy-candidate --baseline qa\anatomy-legacy\report.json
& .\.venv\Scripts\python.exe scripts\rig3d-seek.py --profile distance --out qa\seek-candidate
```

The matrix defines **120 situations per body**, not a full Cartesian product:
32 azimuth/elevation cells, 12 joint stress poses in normal and activation
modes, arm/triceps/chest windows on both sides at four opening levels, and
five phase-map midpoints for each of the eight exercises. Figure IDs are
present; phase times come from the exercise's own map. Hip 120 and trunk
twist 45 are diagnostic inputs, not clinical range limits. Close-up crops
are intentional. Existing `--set all` still means the original three sets.

Individual PNGs, labelled sheets, hashes, JSON and a side-by-side HTML report
are retained. A fresh capture starts as `known-limit` with an explicit
unreviewed note. After looking at the images, pass `--report-only --review
<file.json>`; the review maps case IDs to `{status, note}` with statuses
`pass`, `known-limit`, or `fail`. Changed/missing PNGs are rejected.

The seek suite now has 20 cases: the original 12 plus bilateral shoulder
twist, overhead reach, deep flexion and partially open cutaways for both
bodies. `--profile` applies to every figure, including split and timing
fixtures. Timing is local build plus warm pose/render/GPU-finish frames;
the JS heap sample is not browser/process peak memory. Clinical accuracy,
continuous self-intersection, every overlay/layout and Mac execution remain
separate review work. A numeric pass never approves the proposed silhouette.

Windows verification on 2026-11-20: 56 anatomy/rig/fitness tests, 40 temporal
cases (20 per profile), and 258 paired situations (240 core plus 18 original
mode presets). Twenty contact sheets were inspected; the candidate has
87 targeted visual passes and 171 known limits, not a global creative pass.
All twelve original default reference frames remain pixel-identical.

The portrait diagnostic also checks posed skin/accessory vertices, not only
joint centres. At `az=25, el=10, dist=4150, ty=360`, the resting candidate
fits y=344.95..890.12 in 720x1280, inside the 330..895 header/caption bounds.
The approximate `ty=380` recipe failed first; no bound was relaxed. This is
one measured camera/pose, not a universal camera preset. Real film overlays
and wide raised-arm equipment still need per-scene fitting.

Evidence travels in the ignored handoff folder: `prompts/state/next-pass/`,
including design PNGs, galleries, current costs, negative controls and
`acceptance.md`. Mac execution, whole-browser peak memory and human G3
approval remain open.

## 9. Integrated full-body correction (1.10.0, 2026-11-20)

The owner requested a full examination after the lats still looked like
exterior objects and the shoulder/body rendering was weak. A neutral-clay
pass confirmed that the problem survived removal of the colour/crease
shader: one mesh had merely joined the old ornament-like volumes.

`distance` is now the **3D development default**, including the figure,
exercise factory and bench/checker CLIs. Explicit `legacy` retains the old
geometry/rendering for compatibility comparisons; it is not an anatomical
acceptance path. This intentionally changes 3D appearance, not the approved
2D art, palette tokens, pose names, bone lengths or exercise timing.

| Correction | Shared implementation / guard |
| --- | --- |
| Lat/pec fans, tapered deltoid cap, continuous rectus bands, embedded limb forms | Profiled volumes feed both the skin and internal loft; centres adapt to the selected torso |
| Brachialis on distal humerus, deep to biceps | Source references in `muscles.json`; actual biceps -> brachialis -> humerus ray |
| Shoulder/limb surface continuity and detail | 3.5-unit current grid; only negligible joint influences discarded; legacy retains 4.5 units and its old weights |
| Normals follow the bulged geometry | Figure-local normal arrays; exact recomputation and cross-instance/seek checks |
| Readable form without painted-on plates | Softer toon sampling, lower rest tint/crease; same palette |
| No clipping or accelerated colour onset from overlapping muscles | Convex per-vertex ramps and fixed coverage weights; RGB bounds for all three roles and actual per-frame skin/cloth deltas |
| Top belongs to torso, not lifted arms | Torso ownership plus actual bone weights, analytic band edges and thinner geometry |
| Cutaway anatomy stays inside the selected window | Explicit bind-space inner-fragment clipping; full layers, skeletons and isolated muscles remain intentional modes |
| Actual holes cannot pass a percentage tolerance | Zero boundary edges; non-manifold counts remain separately reported under the existing tolerance |

The anatomy checker also requires a broad visible lat footprint, a <=12-unit
lat and <=8-unit rectus contour-field relief measure, and no unvalidated
arm-elevation-only lat inflation. These are engineering bounds in rig units
(head = 100), not medical dimensions.

Eight in-memory controls exercise the **actual checker**: old row-index
sampling, lat lobe, elevation-only swelling, stale morph normals, additive
colour, forearm/superficial brachialis, a removed skin triangle and top-to-arm
bleed. No old threshold was weakened.
The actual-skin colour test caught a first compositor's doubled slope, which
was fixed at the source without retiming exercises.

```powershell
& .\.venv\Scripts\python.exe tests\test-anatomy3d.py
& .\.venv\Scripts\python.exe tests\test-rig3d.py
& .\.venv\Scripts\python.exe tests\test-fitness.py
& .\.venv\Scripts\python.exe scripts\anatomy3d-bench.py --set review --gender both --size 360x480 --out qa\body-review
& .\.venv\Scripts\python.exe scripts\anatomy3d-bench.py --set regions --gender both --shade clay --size 360x480 --out qa\body-clay
& .\.venv\Scripts\python.exe scripts\rig3d-seek.py --out qa\body-seek
& .\.venv\Scripts\python.exe scripts\rig3d-seek.py --set locality --out qa\body-locality
```

`regions` defines 29 views per body, from head/neck to shoes and a prone
geometry probe; `review` totals 316 normal situations with the existing camera,
joint, phase, window and mode sets. Clay is surface diagnosis, not cutaway
colour review. When reusing an earlier baseline, verify the saved renderer
source hashes and preserve its provenance instead of presenting it as fresh.

Final frame inspection also found internal anatomy speckling through uncut skin.
The old inner shader relied on depth occlusion instead of restricting fragments
to the open window. The separate `locality` pixel gate compares a skin-only
opening with its internal anatomy: pixels outside conservative projected window
bounds must not change, and at least 100 pixels inside must change. Its in-memory
`--unclipped-control` must fail. This is rendering containment, not proof that
every posed inner triangle remains inside the outer mesh. `--set all` remains
the twenty temporal cases; locality is a separate correctness check.

A local dual-quaternion trial was rejected: it reduced some compression but
greatly increased overhead-shoulder stretching with the trial's weights.
No new skinning dependency or unverified replacement was adopted. Linear-blend
kinematics remain illustrative; this is not a soft-tissue model, precise
scapulohumeral rig, fully manifold surface or clinical atlas. Human G3 and Mac
production review still apply. The private evidence/reproduction package is
`prompts/state/full-body-review/`.

## 10. Shoulder roof and arm separation (1.11.0, 2026-11-20)

The owner rejected the remaining perched deltoids and glued-looking arms in
1.10.0. Its numerical pass was not a successful visual acceptance. The supplied
crop and Yellow Dude reference were used to study anatomical flow and silhouette,
not to copy that character, its artwork, branding or costume.

The missed contributors were an unmasked spherical `shoulder-ball`, the broad
flat end of the upper-arm core, a sparse cap profile with pointed ends, and a
resting pose aimed mostly forward. Correcting muscle volumes alone missed them.

- Replace the exposed joint orb with a sloping shoulder envelope.
- Taper the proximal/medial arm core, keeping the wrist and bone anchors fixed.
- Use rounded-end, downward-tapering deltoid fans shared by surface and loft.
- Refine wrist/palm/thumb proportions. A segmented claw-like finger experiment
  was rejected; this is still a stylised hand, not an articulated finger rig.
- Make the current neutral stance `shL/shR=8`, `plL/plR=10`. Legacy retains
  `6/70`. `fig.defaultPose` exposes the figure's neutral values; static benches
  must read it. `T3.DEFAULT_POSE` remains the authored-motion fallback.

The posture change is intentional and is shown separately from the geometry
change. Matching cameras and the old pose isolate the shoulder correction;
the new neutral stance demonstrates the arm/waist separation. The approved
2D art, palette, bones, authored exercise tracks and equipment poses are unchanged.

The actual projected skin now has a contour/clearance gate, including unmasked
parts. Shoulder-crest rebound must be <=2.5 rig units in both the original and
new neutral pose. The neutral upper-arm/lower-arm/palm silhouette gaps must be
at least 3/15/12 units. These are engineering design guards, not clinical ranges.
Restoring the old orb, flat arm root or forward-hanging stance makes the actual
checker fail for the intended defect.

Windows verification: 59 tests pass without skips (23 anatomy, 9 rig, 27 fitness);
40 temporal cases pass. All 80 sampled authored exercise/phase states have
identical pose dictionaries, bone matrices and recorded prop geometry/transforms
before and after. All 20 explicit-legacy reference images remain pixel-identical.
Measured shoulder-crest rebound at the unchanged pose falls from 13.93/10.49
to 1.42/0.98 (male/female). The minimum current neutral palm gaps are about 24.29/16.53.
Evidence and matched PNGs: `prompts/state/shoulder-arm-refinement/`.

This is not a clinical/scapular/soft-tissue rig. Raw cross-body/deep-flexion
stress poses still show simplified deformation, and the existing raise camera
can crop dumbbell tips. Mac production and named-human G3 remain pending.

## 11. Reference-informed editorial onboarding (2026-11-20 UTC)

The owner requested broader Yellow Dude design, style and content learning.
The [source-linked study](../.claude/skills/fitness/references/yellow-dude-study.md)
records nine official pages and two inspected public layouts. The newly found
production article resolves the earlier retrieval gap, but its account of
software, staffing, analytics, voice and review remains a publisher report.
Video timing/audio, private metrics and the article science were not validated.

Fitness skill 2.1 routes the study into briefing, storytelling, visual design,
quality review and packaging. Body Lab v2 adds optional matched-contrast and
qualified-progression grammar and anti-patterns for unsupported hooks,
misleading comparisons and indiscriminate reference copying. Existing pacing
thresholds, runtime, Tibi identity, palette, voice and render formats do not change.
No new dependency, downloaded reference artwork or invented video-corpus record.

The authoring/review additions are explicit manual checks, not new automated
science gates: viewer problem/outcome, claim-to-drawing trace, qualified input
early, hook/body alignment, spoken-language cleanup, an unpolished animatic and
original packaging planned with the story. Existing G1/G3 and story sign-off
remain authoritative. Old style pins are reported, not silently re-pinned.
The next step is a Sinew film pilot; no retention or creative improvement is
claimed from onboarding alone.

## 12. Flank and hip contours (1.12.0, anatomy 1.3.0, 2026-11-21)

A straight front view of the 1.11 body showed a vertical plate on each side of
the rib cage ending in a ledge under the arm, a horn at the lateral end of each
pec, and (female most) a shelf at the top of the shorts. Every numeric gate
passed them. Measured in an orthographic front projection, the torso half-width
dropped 10.6 (male) and 9.4 (female) units in 5 at the bottom of the plate, and
the female hip jumped 8.2 units in 5 below the waistband.

| Defect | Cause in the muscle table or core | Correction |
| --- | --- | --- |
| Flank plate and ledge | Serratus radius 10 along x (the flank's normal), tilted against the rib cage's slope | Thin sheet (radius 4 across, 15 along the surface), tilted with the flank |
| Pec horn at the armpit | Sparse zero-ended profile and a lateral end 12 units in front of the chest wall | Dense rounded profile converging laterally; lateral end wrapped onto the ribs, clavicular edge recessed |
| Hip shelf above the shorts | Glute-medius egg 24 units wide ending at the waistband | Smaller, deeper volume below the band, still behind gluteus maximus in the hip cutaway |
| Hip shelf at the leg top | Leg tube's flat end at full thigh radius | Rounded top rows on the distance profile |

`anatomy3d-check` adds a `flank` gate: projected torso half-width per 5-unit row
from 60 below the shoulder to the waistband (authored rest and neutral), and from
the band to 20 below the hip joint (neutral, where the hands clear the hips).
A step over 5 units fails. After: worst 2.37 (male) and 3.16 (female). Restoring
the old serratus, the old glute medius or the flat leg top makes the actual
checker fail for that defect (tested in `tests/test-anatomy3d.py`).

Windows verification: anatomy 23, rig 9, fitness 27 and style-template 33 tests
pass; both checkers pass for both profiles; 40 temporal cases pass; all 81
explicit-legacy seek images are byte-identical to the 1.11 run (legacy code paths
are untouched). Mesh size falls slightly (male 38,855 to 38,641 vertices).
The approved 2D art, palette, bones, pose keys and authored tracks are unchanged.
Evidence and matched normal/clay boards: `prompts/state/torso-flank/`.

Still open: raw cross-body reach crushes the shoulder (linear-blend skinning),
mitten hands, a flat back with no lat flare from the front, a tube-top female
garment, and no human G3 or Mac render of this version.

## 13. Cameras fitted to the posed body and equipment (1.13.0, 2026-11-21)

Each exercise carries one fixed `camera` (tuned by eye, mostly for landscape).
On the default 720x1280 stage it loses part of the picture during the set:
up to 195 px of the dumbbell press, 178 of the lateral raise (the dumbbells at
shoulder height), 108 of the hip thrust and 17 of the front squat. Curl, calf
raises and side/three-quarter squats stay in frame.

`stage.fit(points, {rect | margin})` keeps az/el/fov and solves dist and target
so every point projects inside `rect`. `T3.framePoints(fig)` gives the posed skin
(every sixth vertex) plus boxes of visible rigid parts and props, and
`T3.fitScene(stage, scene)` gathers them at 48 moments of the set. The search
runs on the extreme points of 128 depth slices, then confirms on every point.
`T3.scene(stage, id, {shot, fit: true | {rect | margin}})` applies it; films pass
the rule-13 header/caption limits as `rect`. Fitting is pure geometry (no clock,
no randomness) and runs once at build, not per frame.

`rig3d-check` fits every declared shot (distance profile) and requires zero
overflow at every 1/8 s of the set, a denser and independent sampling. A fitter
reduced to two samples (start and end of a raise) fails it (`tests/test-rig3d.py`).
All 37 shots pass for both bodies. `rig3d-stills.py --fit 0.04` and
`still.html?fit=0.04` use it. The fixed cameras are unchanged, so existing films
keep their framing until they opt in.

The same pass re-viewed two older known limits on the 1.12 body: the seated
thigh no longer reads as a flat disc, and the hip-thrust glute under the bridged
pelvis is anatomically right; seeing it is a shot choice (low side or cutaway).
Evidence: `prompts/state/framing/`.

## 14. Known-limit corrections (1.14.0, anatomy 1.4.0, Tibi 0.6.0, 2026-11-23)

The prompt-02 acceptance page (2026-11-21) named its remaining limits. This
pass fixed them at the shared source, refined (`distance`) body only; the
explicit `legacy` body hashes identically before and after (skin, inner meshes
and window state over seven states).

| Limit | Cause | Fix | Gate (before -> after) |
| --- | --- | --- | --- |
| Glute reads as a ball under the shorts | the refined table had no gluteus maximus row; a 21-unit legacy ellipsoid stayed | profiled fan, 13 thick, minimum edge 0.6 of the belly | profile drop below the peak ~14 -> 6.4 per 5 units; gluteal-hip roughness 60.6/72.4 -> 29.6 degrees (limit 40) |
| Effort blobs through the shorts, pale abs block, dark-red stains | stabiliser mid colour whiter than its role colour; cloth ramp darkened coral, then jumped to full | tint weighted by the muscle's own shape; straight ramps; one subdued cloth tint (66-69 % to the role colour) | effort-shape, stabiliser-ramp and cloth-tint gates; colour step 0.113 (limit 0.12) |
| Glute cutaway rings | a centred deep-stage hole always left a ring of the broad gluteus maximus | deep stage wipes from the medius side behind a straight edge | scanlines crossing the maximus twice 32-45 % -> 0-7 % |
| Square female deltoids | she used the male cap scaled down | her own narrower, rounder, tapered cap | overhang 6.2 -> 0.7 |
| Shoulder ridge at 90 degrees abduction | chest-to-arm weight blend too narrow | wider blend (weights only; elevation-only bulge stays 0) | ridge rise 21.5/19.0 -> 3.8 |
| Fold crush at elbow 150, knee 150, hip 120 | linear-blend skinning | pose-driven radial correctives on the inner fold; smoother hip weights | fold distance 0.26/0.26/0.50 -> ~0.70 of rest (limit 0.6); squat stretch 4.40/4.34 -> 3.37/3.49 (refined limit tightened to 4.0) |
| Ponytail follows trunk lean only | one rigid group | damped follow-through sampled from `motion.at(t - k/30)`, no stored state; rests on registered supports | lag 0 -> 14.2 degrees on a 45-degree turn; 16.8 -> 0.5 into the bench pad; seek-order difference 0 |
| Flat back on the bench | trunk posed as a plank | `T3.solveArch` (arch 22) from `T3.skinLow` | lower-back gap 2.3/5.0 -> 14.1/17.5; blades and head on the pad |
| Two-piece shoe, no foot roll | rigid heel and toe pieces hinged at the ball | one lofted bending sole; `T3.footRoll` heel rocker, toe-off, pose key `tf<side>` | sole kink 22.6 -> 6.9 degrees; heel strike no longer 31.6 below the floor |

Every gate has a negative control in `tests/test-anatomy3d.py` or
`tests/test-rig3d.py` that restores the old behaviour and must fail.

Not fixed: the shoulder at cross-body and overhead reach (a corrective moves
torso skin as the arm rises, which the anti-lat-bulge gate forbids; it needs a
scapula or twist-bone rig), hip 120 outer volume (-3.5 %), correctives on the
cutaway's inner muscles, one hidden 5.9x triangle in the curl's elbow crease.
Look calls for the owner: the cutaway wipe, the faint marigold under the
shorts. Evidence and sheets: `prompts/state/known-limits/` (not in git).
Windows preview only; no Mac render, no human G3.
## 15. Shoulder girdle, exercise families 1-2, film helpers (1.15.0, 2026-11-25)

Released together after two days of unreleased work (anatomy 1.5.0-1.6.0,
Tibi 0.7.0-0.8.0, sculpt 2.2.0). Girdle bones `gdS`/`axS` move the shoulder
for an anatomical reason (rules in `motion-3d.md` "Shoulder girdle"); 18 new
3D exercises and mistake variants (hinge, split, prone, knee machines, leg
press, barbell bench, rack squat); `studio-film.js` (kicker, caption band,
stamp, tile grid, stations, odometer, scene drift, word-snapped cues) and
`kits/fitness/stations.js` (layout, exercise cards, one Tibi per station).

Verified on Windows (2026-11-25): `anatomy3d-check` output identical to the
recorded final-state output apart from timings; `rig3d-check` male and female
exit 0; `test-anatomy3d.py` 26 tests OK. `test-rig3d.py` 23 tests OK at 1.15.1 (one bite test split, see 1.15.1
below). Not verified: Mac renders, human G3 (see `prompts/state/log.md`).

On 2026-11-25 an old VS Code chat editing session wrote an 11-21 snapshot over
36 files. They were rebuilt from vendored `_studio/` copies and the Copilot
session logs and checked as above; the procedure is in the `session-handoff`
skill.

### 1.15.1 (2026-11-25): exercise card text floor

The portrait card fit shrank chips, cues, tip and swaps to 16.6-18.1 px, under
the 18.7 px frame-review floor (2.6% of the short side). They now stay at that
floor; a card that still overflows drops trailing muscle chips to 3, then
secondary ones only. The fit also measured the flex-grown slot, so every card
shrank whether it needed to or not: landscape cards now render at their design
size. `K.audit()` reports `card-below-floor` (negative control in
`tests/test-studio-runtime.py`). Sheets: `prompts/state/p06/sheets/`.

Also in 1.15.1: the barbell-bench touch bite in `test-rig3d.py` runs alone. In
the combined bite run the wrist-ahead patch moved the hands 40 units toward the
feet, which put the touch point back inside 40-120 and masked it; alone,
`touch: 20` still fails with "the bar touches 22 units from the shoulder".