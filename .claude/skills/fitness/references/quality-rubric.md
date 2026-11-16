# Sinew quality rubric, accuracy standards and review process

Data: `specs/fitness-spec.json` `rubric`; record: `projects/<slug>/qa/fitness-review.json` (`specs/fitness-review-spec.json`); check: `python scripts/fitness.py review <slug>`. It sits beside the studio's 12-criterion `qa/creative-review.json` and the five technical QA gates; it does not replace them.

## 1. Dimensions (scored 1-10 with evidence)

| Dimension | Question | Critical |
|---|---|---|
| scientific_accuracy | Every claim supported by the dossier at the strength stated; numbers, populations and attributions exact | **yes** |
| anatomical_accuracy | Structures and muscles placed and named correctly for the level of stylisation | **yes** |
| biomechanical_accuracy | Movements and joint mechanics plausible; contacts planted; kinematics labelled illustrative | **yes** |
| visual_consistency | Sinew palette, type, layout, graphics | |
| character_consistency | Tibi on model in every view and expression | |
| storytelling | Understandable and engaging for the target viewer; arc and payoff | |
| animation_quality | Fluid motion, timing, no pops or sliding | |
| information_density | Every scene contributes; no dead stretches, no overload | |
| audio_quality | Clear narration, balanced mix, loudness on target | |
| production_efficiency | Built from the reusable kit in one build loop, not one-off art | |

## 2. Thresholds

Pass only when **all** hold: every score at least 6; each critical dimension at least 8; mean at least 7.5; **no open critical issue**. A scientific, anatomical or biomechanical error is a critical issue whatever the scores: attractive visuals never compensate. `verdict` must equal what the rubric computes (`fitness.py review` checks this).

## 3. Issues

Each issue records: id, scene, film time (`00:47.3` or a range), problem, severity (`critical`, `major`, `minor`), dimension, the fix, whether it needs a re-render, and status (`open`, `fixed` with `fixed_in`, `wontfix` with a reason in the fix field). Severity guide:
- **critical**: a false or unsupported claim, a wrong number or attribution, a fabricated data point, a mislabelled structure, an impossible joint motion, missing medical boundary on an injury topic.
- **major**: a claim without its badge or source line, illegible text, a broken contact (a foot sliding through the floor), captions covering a key visual, a loudness gate fail.
- **minor**: small overlaps, timing a beat early or late, colour or spacing drift.

## 4. Scientific accuracy standard

Every spoken sentence and on-screen number maps to a dossier claim (`claims[].where`). Charts plot only measured points; a line through them is labelled as such; separate studies on one chart are named per series with n. Units, populations and times as reported. Grades on screen match the dossier.

## 5. Anatomical accuracy standard

Muscles drawn in the right region, on the right side of the bone, crossing the right joints (for example the biceps on the front of the upper arm, crossing the elbow; the gastrocnemius crossing the knee, the soleus not). Names follow `assets/fitness/data/muscles.json`. Schematic plates are labelled schematic, and sizes come from a source. Never teach attachment sites from Tibi's stylised shapes.

## 6. Biomechanical accuracy standard

Contacts stay planted (anchors and IK), the joint order is plausible (squat: hips and knees together; deadlift: hips dominant), ranges are within normal human limits (the joint `min`/`max` in the rig), the bar path is close to vertical where it should be, and the gait has a flight phase only for running. Error poses are clearly shown as errors. Anything numeric is "illustrative" unless cited.

## 7. Review process (every film)

1. Extract frames from the delivered MP4 (`ffmpeg -vf fps=1/3,scale=384:-1,tile=6x6`) and look at all of them; look at full-size frames for every chart, card and source line.
2. Re-read the narration against the dossier, line by line. Re-check every number and attribution against the source record.
3. Read the QA gate output (streams, loudness, black frames, container, Earshot) and run `earshot timeline` on the film for the mix.
4. Score `qa/creative-review.json` (studio) and `qa/fitness-review.json` (Sinew), with evidence for each score.
5. Fix, re-render, re-review. Keep fixed issues in the file with `fixed_in` (the render they were fixed in).
6. Write `qa/production-report.md`: kit systems used, what was new, timings, scores, open items.

## 8. Calibration

The thresholds are a first guess, set on one film (how-muscles-grow, 2026-11-08). Revisit them after three films; record changes in `specs/fitness-spec.json` and here.
