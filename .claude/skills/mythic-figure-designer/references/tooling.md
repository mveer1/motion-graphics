# Tooling: libraries evaluated for figure generation (2026-11-24)

Evaluated with the dependency-intake checklist. Repository pages, registry metadata and LICENSE files were read; nothing was installed or run. **Nothing here is adopted yet.** Every item marked ADOPT or NEEDS HUMAN DECISION waits for the owner's approval, then a pinned, hash-recorded vendoring through `workspace-steward` (a `catalogue/data/libraries/` record).

## Principle: bake, don't ship
The render bundle stays GSAP + Three.js. Geometry libraries run **at authoring time**, in Node or an authoring page, and emit static SVG path strings that go into the kit. A library that is only used at authoring time adds no render risk on the 8 GB host.

## Summary
| Candidate | Use for us | Licence (from) | Pin | Verdict |
|---|---|---|---|---|
| Paper.js | boolean ops (unite or cut armour, clip shapes), curve fitting `simplify()` | MIT (LICENSE.txt) | 0.17.0, `dist/paper-core.min.js` | ADOPT pinned, authoring-time; awaits approval |
| paperjs-offset | stroke-to-outline and offsets on top of Paper (rims, limb outlines) | MIT (npm field) | 2.2.2 | ADOPT pinned; awaits approval |
| bezier-js | offsets, arc length, evenly spaced studs along a curve | MIT (npm, GitHub) | 6.1.4 | ADOPT pinned; awaits approval |
| svgpath | normalise, mirror, transform and unarc path data | MIT (npm field) | 2.6.0 | ADOPT pinned; awaits approval |
| GSAP 3.13+ (MorphSVG, DrawSVG, MotionPath) | morph between views (a head turn), draw weapon trails | Webflow Standard "No Charge" licence (proprietary; forbids competing no-code animation builders) | 3.13.0, then golden-frame diff against 3.12.5 | NEEDS HUMAN DECISION (licence sign-off) |
| perfect-freehand | brush-tapered strokes | MIT | 1.2.3 | NEEDS HUMAN DECISION (look) |
| Rough.js | hand-drawn ink variant | MIT | 4.6.6 | NEEDS HUMAN DECISION (look) |
| MPFB2 (MakeHuman) for Blender | muscular base bodies rendered from any angle as proportion references for the three-quarter, profile and back views | code GPLv3; assets CC0; output is the user's (LICENSE.md section D) | v2.0.18 | ADOPT later, authoring-time |
| Blender | reference renders, depth and silhouette passes | GPL; output is the user's | installed LTS | IN USE (2026-11-25): 5.2.4 renders the 3D figures (`src/blender/mythic3d/`, original procedural code; no MPFB2 or other assets) on the Windows host |
| Anny (Naver Labs) | parametric human with muscle and age controls | code Apache-2.0, data CC0 (avoid its SMPL-X topology: non-commercial) | commit pin | NEEDS HUMAN DECISION (pilot; PyTorch on 8 GB unverified) |
| MediaPipe tasks-vision | pose landmarks from a reference photo to set joint angles | Apache-2.0 (model files unverified) | 1.2.3 | ADOPT later, authoring-time |
| imagetracerjs | trace a reference silhouette | Unlicense | 1.2.6 | optional |
| FLUX.1 schnell (local) | AI reference stills | Apache-2.0 | n/a | NEEDS HUMAN DECISION: 8 GB is marginal to unworkable |
| SD 1.5 + ControlNet pose from our own rig | pose-locked AI reference stills | CreativeML OpenRAIL-M (secondary sources) | n/a | NEEDS HUMAN DECISION; draw the pose skeleton from our rig, never the OpenPose annotator (non-commercial) |
| Recraft API (vector generation) | cloud vector drafts | developer terms: you own outputs, no training use | n/a | NEEDS HUMAN DECISION (network, un-jointed output) |

## Rejected
- Licence:
  - Spine: runtime needs an editor licence per user.
  - Live2D Cubism: proprietary plus a publication licence.
  - SMPL / SMPL-X: non-commercial.
  - FLUX.1 dev: non-commercial.
  - OpenPose code: non-commercial.
- Redundant or poor fit:
  - Rive (proprietary editor, 2.4 MB wasm);
  - DragonBones (dormant);
  - Lottie (playback only);
  - Two.js and SVG.js (renderers we don't need);
  - flubber (2018; MorphSVG supersedes it);
  - polybooljs, polygon-clipping and simplify-js (Paper covers them);
  - clipper-lib (2019).
- Local SVG-generating LLMs (StarVector, OmniSVG): far beyond 8 GB.

## Re-authored instead of adopted
- **2-bone IK:** `M.human.geom.ik2`, about 10 lines, in place of IK libraries.
- **Catmull-Rom to Bezier, tapered limbs, mirrored halves:** already in `figures-human.js`, in place of d3-shape.
- **Pose skeleton rendering for any future ControlNet use:** draw it from the rig's own joints.

## Next steps if approved
1. Vendor Paper.js, paperjs-offset, bezier-js and svgpath into an authoring-only folder: `tools/figure-authoring/`, never `src/studio/`.
2. Pin each by version and sha256. Record the licence text and register each in `catalogue/data/libraries/`.
3. Write an authoring script that bakes armour plates, weapon outlines and garment folds into path strings.
4. Upgrade GSAP to 3.13 behind a golden-frame diff, then use MorphSVG for view swaps.
5. Install MPFB2 on the Mac and render turnaround references of the five `HERO` presets for the later views. Until then the procedural 3D figures (`figure-design.md` section 9, Blender only, no third-party assets) give a five-view turnaround of each figure.

## Not checked
- The LICENSE files of paperjs-offset, bezier-js, svgpath, perfect-freehand and Rough.js. Only their npm licence fields were read.
- Hugging Face model cards; the network proxy blocked them.
- GSAP 3.13 regressions against 3.12.5.
- Any benchmark on the 8 GB Mac.
