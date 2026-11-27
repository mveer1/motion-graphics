---
name: fitness-qa
description: Quality control for Sinew fitness films: the four review gates (research and script, storyboard and animatic, animation and biomechanics, final export), the automated render diagnostics (frozen frames, black or blank frames, first-frame jumps, unexpected cuts, motion and rep rhythm, frame-rate and metadata labels, A/V sync, loudness), the anatomy acceptance tests, and the rule that automation never approves accuracy. Use before shipping any fitness film or clip, or when a render "looks fine" but something feels off.
version: 1.0.0
---

# Fitness QA: a finished render is not a finished film

| Gate | Automated evidence | Human sign-off |
|---|---|---|
| G1 Research and script | `fitness.py dossier <slug>`, `qa/story-review.json` verdict complete | **required**: scientific accuracy |
| G2 Storyboard and animatic | `studio.py validate`, `scripts/fitness-animatic.py <slug>` (stills per scene + pacing lint) | story-writer / owner |
| G3 Animation and biomechanics | `rig3d-check.js`, `anatomy3d-check.js`, `qa/fitness-review.json` rubric | **required**: anatomical and biomechanical accuracy |
| G4 Final export | `studio.py build` (5 gates) + `scripts/fitness-qa.py <final.mp4> --expect-audio` | creative review (`studio.py review`) |

`python scripts/fitness-gates.py <slug>` evaluates all four into `qa/gates.json`. It can FAIL a gate; it can never APPROVE accuracy: G1 and G3 are `awaiting-human-signoff` until `qa/fitness-signoff.json` names a reviewer (`{"G1": {"by": "name", "at": "date", "note": ""}}`). Never write that file yourself.

**fitness-qa.py** (objective only): container and frame-rate agreement (r_frame_rate == avg_frame_rate == expected, title/comment/file-name labels say the real rate), A/V sync within 0.12 s, decode errors, frozen picture longer than 1.5 s (narration over a static frame), black and blank frames, **frame 0 jump** (a stale or unsettled first pose; also flags a bare first frame with no hook), unexpected scene cuts (`--cuts N`), share of seconds with motion, dominant repetition period against `--period`, loudness. Tune with `--allow-hold`, `--motion`; clips with captions use the picture above the caption band automatically. Not covered: text outside safe areas, overlapping labels, anatomy: use `hyperframes snapshot` contact sheets and the rubric. Test it on a known-bad file now and then.

Lessons that became checks: press frozen by unprefixed keys (rig3d range of motion), supplied clips with a stale first frame (fitness-qa start jump), muscle stickers (anatomy3d-check protrusion/coverage), colour pops (motion-continuity.py, activation step), fps label mismatches (fitness-clip.py verifies and stamps).
Runtime 1.9.1 adds `scripts/rig3d-seek.py`: twelve fresh/revisited-frame cases
for skin, toes, scene visibility, split-camera copies and ghost-mode reset.
Its pixel/state parity gate is separate from the full anatomical matrix and
never grants G3 sign-off.
Runtime 1.9.2 expands that suite to 20 cases and adds a 240-cell anatomy
matrix (both bodies, not the full Cartesian product). The corrected
distance-sampled body is opt-in. Test `legacy` and `distance` separately;
never label the legacy profile's station mismatch fixed by a runtime upgrade.
Matrix captures are `known-limit` until an explicit visual-review note is
recorded; numeric checks do not assign a creative pass. See
`docs/fitness-studio.md` section 8.
Runtime 1.10.0 adds a whole-body region/clay review and defaults to the
integrated distance body. `--set review` defines 316 situations; `--set regions
--shade clay` isolates the actual geometry. One connected skin can still have
exterior-looking muscles: a lat wing, misplaced brachialis, shoulder pad or
stale normal is a defect, not an automatic pass because topology succeeded.
New tests exercise actual checker failures for these classes and for colour
clipping, open boundaries and top-to-arm bleed. See section 9 of the architecture
guide. Do not infer human accuracy or fully simulated joint mechanics from them.
Scoring the rubric: `references/quality-rubric.md`; scientific, anatomical or biomechanical errors are critical failures whatever the other scores.
