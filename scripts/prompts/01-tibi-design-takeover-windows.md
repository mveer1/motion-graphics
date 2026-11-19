# 01 · Take over Tibi's design (2D and 3D) on the Windows machine

> Read `prompts/00-shared-context.md` first. It holds the workspace rules, the map of both Tibis, the Windows hazards and the handoff protocol. This prompt doesn't repeat them.

## Start here: the design of record

Before you change anything, read the "Design of record" table in `prompts/00-shared-context.md` section 3a. It names the master source for each Tibi. The 2D master is `src/fitness/tibi/` (the generator), and the 3D master is `src/studio/kits/fitness/anatomy3d.js` and its neighbours. The SVGs, PNGs, sheets and the review page are copies. `HANDOVER.md`'s `/home/claude/out/` paths do not exist here, so use the repo paths instead.

## Your role

From now on you are **Tibi's lead character designer and technical artist**. You own both bodies: the 2D Cobalt Sculpt mascot and the 3D one-skin Tibi. You own them as one character, so that a viewer who sees a 2D brand card and then a 3D lift sees the same person. You also own the tools that build, check and show the character.

You have a lot of freedom. The owner wants your judgment, not a checklist executed. What follows is the situation, the bar, the constraints and the things you must hand back. How you get there is up to you. When you disagree with an earlier decision (an ADR, a rule, a threshold), say so with evidence, propose the change and ask before you overturn it.

## Where things stand (2026-11-19)

- **2D**: a finished design deliverable from an earlier design session (`src/fitness/tibi/HANDOVER.md`). It covers 15 poses × 2 genders, activation variants, three face options (faceless is the default), and back, side and front views, with round-7 additions: finger joints, fist and grip hands, a two-piece shoe, curved straps, more back detail, prone and supine poses from above, and a back-view squat and run. The runtime painter `sculpt.js` animates it on the studio rig. A known structural flaw: `armState()` **swaps drawings at angle thresholds** (shoulder 50°, elbow 60°), so a curl, press or raise "pops" every rep. Views are separate drawings, so turns are cross-fades. This is why 3D exists.
- **3D**: Three.js, one continuous skin since runtime 1.9.0 (`anatomy3d.js`). An SDF union of cores and muscle volumes is meshed once with surface nets (~25k verts) from an A-pose bind. Activation is CPU per-vertex colour deltas, cutaway windows live in bind space, and there are ghost, isolate, layer and skeleton modes. Eight exercises (curl, bench press, lateral raise, back squat, knees-blocked squat, barbell hip thrust, standing and seated calf raise) pass `rig3d-check` for both bodies. Three narrated 3D shorts exist on the Mac.
- **Honest weaknesses already recorded** (`docs/fitness-studio.md` §5, `motion-3d.md` "Known limits"): deltoid and pec read as soft ovals up close; no tendon or fascia detail; the female crop top is a straight-edged colour band; the shorts hem is a small step; the quad reads as a flat disc on a horizontal thigh; the 3D shoe is two rigid pieces with no foot roll; the bench spine is flat; the ponytail only follows trunk lean; the hip-thrust glute is only visible from a low side camera; and the 3D look doesn't match the 2D crescent shading. **The owner has not yet ruled on whether the 3D look is acceptable next to the 2D art.**
- No human has signed off anatomy (G3) on any film.

## The bar

Tibi should hold up as a **premium, recognisable mascot** from any camera, in any supported pose, at any size, from a 120-px thumbnail to a full-frame close-up of the shoulder. Concretely:

- The same character in 2D and 3D: silhouette, proportions (male 7.66 heads, shoulder:waist 1.62; female 7.55 heads, 1.79, waist:hip 0.62), palette tokens and spark. Anyone should be able to tell it's Tibi in silhouette alone.
- Anatomy that is believable and **teachable**: a viewer can point at the deltoid, the pec or the glute and know which it is, and nothing looks stuck on, floating, intersecting or melted at a joint.
- Motion with no pops, swaps or velocity steps, and contacts that stay planted.
- The colour language (`STYLE.md`: one meaning per colour) is never blurred.
- Every improvement is in the master source (the generator or the kit), versioned, tested, documented and visible in a before/after sheet.

## Constraints you must respect

All of `00-shared-context.md`, plus:

- **Don't break existing films.** The kit's public API (`T3.tibi`, `fig.roles`, `act.*`, `cut.*`, `hi.*`, `view.*`, `iso.*`, `fig.world('muscle@side')`, `fig.point`, the pose keys and units in `motion-3d.md`, `K.sculpt`) is used by compositions you may not have on this machine. Extend it, don't rename it. If a break is truly worth it, write a migration and list every affected project.
- **Determinism**: same input, same pixels, in node and in Chrome. No randomness, clocks or timers. A mesh is built at load and must be identical every time.
- **Memory**: the Mac has 8 GB and renders one job at a time. Keep the figure within a sane budget: measure vertex counts and load time before and after (today about 25k verts and about 300 ms build), and justify growth.
- **The approved 2D look** is the owner's. Fixing structural problems (swaps, pops, missing views) is in scope. Restyling the 2D art isn't, unless the owner agrees. The 2D baseline must still rebuild byte-identical unless a change is intended and recorded.
- **No new dependencies** without a written case (ADR-9). That includes Blender: it isn't part of the pipeline. You may write the case for it if your analysis says a sculpted or baked asset is the right step (ADR-1 left "a sculpted GLB" open). Prototype outside the repo, show evidence, and let the owner decide.

## Suggested shape of the work (adapt it)

**Phase 0: make the machine honest.** Probe the host and write `prompts/state/host-windows.md`. Fix only the portability blockers that stop the design loop (lock, Chrome discovery, file URIs, venv paths, line endings), keep macOS behaviour unchanged, and record each fix. Prove the loop works: rebuild the 2D review page byte-identical, run `fitness.py sculpt --check`, run both node checkers and `tests/test-anatomy3d.py`, `test-rig3d.py` and `test-fitness.py`, and produce one bench sheet and one stills sheet. If HyperFrames is present, render one motion-only lab clip to a scratch folder. If it isn't, say so and plan around Chrome stills.

**Phase 1: own the current state.** Before changing anything, produce a **design state report** (`prompts/state/design-audit.md` plus sheets in a scratch or `qa/` folder; ask before committing images). Cover both Tibis side by side at matched poses and cameras, every known weakness confirmed or refuted with a picture, new weaknesses you find, a 2D↔3D consistency table (proportions measured, not eyeballed), a performance profile (verts, build ms, per-frame ms in Chrome), and how good the tests really are: which real defects each one catches and which it can't. Run a test on a deliberately broken case to prove it bites.

**Phase 2: set direction.** Write a short design-direction note with 2-4 options for the big open questions, each with sheets and cost. The questions: how close the 3D shading should come to the 2D crescent look (for example a toon or NPR pass that reproduces light and shade planes from any angle, versus the 2D art moving toward the 3D look); how far anatomical fidelity should go within the SDF approach versus a sculpted asset; and what the female body needs (top tailoring, bust, hip line) to read as designed rather than derived. Put the decisions in `prompts/state/decisions-needed.md`. Carry on with work that doesn't depend on them.

**Phase 3: improve, in small verified steps.** Pick the highest-value fixes. `02-tibi-3d-perfection.md` is the deep 3D programme, and `05-pending-2d-3d-unification.md` covers the 2D side and exports. For each step: write the hypothesis, make the change in the master source, run the numeric checks, make a before/after sheet, look at it, and write down what you saw. Bump `Studio.version` with a changelog line when the runtime changes, update the skill and reference docs in the same change, and queue Mac renders of affected films in `prompts/state/render-queue.md`.

**Phase 4: leave the character easier to work on.** If you repeated something three times, it should be a script, a bench preset or a skill (see `07-ai-skills-for-repetitive-work.md`). Update `character-guidelines.md`, `fitness-anatomy`, `motion-3d.md` and `STYLE.md` to match reality.

## Deliverables

1. `prompts/state/host-windows.md`, the probe results and portability fixes, plus a `windows/portability` branch if the owner authorises commits.
2. `prompts/state/design-audit.md`, the state report with its sheets.
3. A design-direction note and its entries in `prompts/state/decisions-needed.md`.
4. Improvements to the generator and kit, each with before/after evidence, passing tests and updated docs.
5. An up-to-date `prompts/state/log.md` and `render-queue.md`.
6. A closing report to the owner: what changed, what you saw (attach sheets), what you didn't verify, what needs the Mac, what needs their decision, and what you'd do next and why.

## Traps others fell into (don't repeat them)

- A figure built without an id passes the stills bench while every real composition freezes (motion rule 16). Test the way films use the kit.
- An undeclared track base became NaN and the upper body silently vanished. Only a picture caught it.
- A pixel-diff tool on a narrated film flags about 75 "events" from overlays. Test the motion layer alone.
- `hyperframes snapshot` reads only `index.html`, and `--composition` takes an id, not a file name.
- Colour ramps under dark cloth need at least 1.0 s, or they flash and stain (rule 11).
- Never trust a check you haven't seen fail.
