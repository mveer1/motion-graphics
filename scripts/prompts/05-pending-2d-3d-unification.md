# 05 · Unify the two Tibis, close the 2D kit gaps, and export the character

> Read `prompts/00-shared-context.md`, `src/fitness/tibi/HANDOVER.md` (all of it) and `.claude/skills/fitness/references/character-guidelines.md`. Track E in `prompts/03-pending-work-plan.md`. Several items here wait on owner decisions. Prepare them, don't take them.

## The goal

One character, two renderers. Today the 2D Cobalt Sculpt art (crescent light and shade planes, separate drawings per view) and the 3D one-skin body (toon bands, free camera) are visibly different people in different films, and the 2D rig pops on every rep of an arm lift. Close that gap, deliberately and with the owner's consent on look, and make the character usable outside HyperFrames as well.

## Part 1: the look decision pack (do first; the owner decides)

The owner has had "3D look vs 2D crescent look" open since 2026-11-12. Give them a pack they can decide from in five minutes:

- matched poses and cameras (front, side, three-quarter, back) of 2D and 3D, both bodies, at feed size and full frame
- **2-4 concrete directions**, each prototyped enough to judge from a sheet, for example:
  - **3D toward 2D**: a camera-relative two-plane "crescent" shading pass for the 3D skin (light plane / shade plane / muscle-tone plane, no outlines), true to `STYLE.md`'s "a 24 % darkening, never an outline"
  - **2D toward 3D**: render 2D brand cards and storytelling poses *from* the 3D body with a flat shader (one source of truth, any angle, no pops)
  - **Keep both, define the boundary**: 2D only for static storytelling and brand, 3D for anything that moves a joint, with a strict rule and a matched palette and proportion table
  - any better idea you have
- for each direction: what changes in existing films, cost, risk, performance on the 8 GB Mac, and your recommendation

Put it in `prompts/state/decisions-needed.md` with paths to the sheets. Then carry on with Parts 2–4, which don't depend on the answer.

## Part 2: 2D structural fixes (no look change)

- **The arm-swap pop** (`sculpt.js armState()`: drawings switch at 50° shoulder and 60° elbow). Options: morph between drawings (shared point topology); add intermediate drawings with cross-fades too short to read; or route every arm lift to 3D and keep 2D arms for static poses. Measure each with `scripts/motion-continuity.py --mode edge` on a motion-only render, and look at the frames. Recommend one.
- **Sampled moves** (`RIG.to` with anchor or IK samples about 10 per second, giving velocity steps): make them continuous.
- **Front-view squat foreshortening** (kit gap from 2026-11-08).
- Keep the 2D baseline **byte-identical** unless a change is intended. When it is intended, record the new baseline (the expected numbers in `HANDOVER.md` §0 and `character-guidelines.md`).

## Part 3: kit gaps the films have asked for

From `TODO.md`: a vascular tree, alveolus gas exchange, joint cross-sections (knee, hip, shoulder), and a clearer leg-press setup. Also from the owner's list, choose what has value: barbell, cable and machine equipment in 2D (back squat, deadlift, bench press, pulldown), a back-view push-up, a contact-sheet script. Build them in `graphics.js` / `sculpt.js` with a manifest entry and a sheet (`fitness.py sheets`), in the Sinew visual language: rosewood and ivory for inside the body, never the effort colours. Anatomy needs sources. Label every illustration "illustrative" where precision would be implied.

**Not wanted now** (owner, 2026-11-09): faces, expressions, lip-sync.

## Part 4: exports and portability of the character

- **PNG exports** (`src/fitness/tibi/export_assets.py`) and the generator's browser checks (`verify3.py`) need Playwright. If the Windows host has it, run them, compare against the handover's baseline numbers, and record the result. The handover PNGs (24 MB) were never copied into the repo, by choice. Don't add them to git.
- **Lottie / Rive export** (owner's list): assess honestly. What can a 2D SVG rig export to (Lottie via bodymovin-style JSON from the rig's transforms; Rive needs its own editor format)? What would it be used for (social stickers, app, web)? What it costs to maintain? Build a proof of concept for one pose loop only if the assessment says it's worth it, and ask before adding any dependency.
- **3D asset export**: is a GLB of the current 3D body (bind mesh + skeleton + weights) useful for thumbnails, a web viewer or Blender look-dev? A GLB export from the kit is cheap with Three.js' exporter if vendored. That is a dependency decision, so write the case.

## Part 5: generator hygiene (owner decides)

- **Dead code** kept until the owner confirms (`HANDOVER.md` §13): curly hair, `chest_bralette`, face style B, the legacy before/after panels in `page6.py` (`build_v1.py`, `rig_v1.py`, `v3_defs.txt`), unused data keys. Prepare a removal diff and show what disappears from the review page. Don't apply it without a yes.
- **Rounding quirk** (`build2.figure()` rounds segment scales to one decimal, so the female leg art is drawn unscaled and hands at 1.1, not 1.15): fixing it changes the approved look. Show before and after, and ask.

## Deliverables

- the look decision pack (sheets + recommendation)
- 2D structural fixes with motion evidence, and the baseline numbers updated where intentionally changed
- new kit graphics with sheets and sources
- an export assessment, plus a proof of concept only if justified
- prepared, not applied, diffs for the dead-code removal and the rounding fix
- docs updated: `character-guidelines.md`, `HANDOVER.md` only where it describes current behaviour (it is otherwise a historical handover; say so at the top if you change it), `STYLE.md`, and the fitness skills
