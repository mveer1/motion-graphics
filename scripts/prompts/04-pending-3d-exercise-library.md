# 04 · Grow the 3D exercise and equipment library

> Read `prompts/00-shared-context.md`, then `.claude/skills/fitness-animation/SKILL.md` and `.claude/skills/fitness/references/motion-3d.md` (rules 1-18). Track D in `prompts/03-pending-work-plan.md`. Best started after `02` has fixed skinning at deep flexion, because hinges, lunges and push-ups will stress exactly those joints.

## The goal

Make 3D Tibi able to demonstrate the movements Sinew films actually need, correctly, smoothly and explainably, so the 2D rig's per-rep "pops" stop being a reason to avoid a lift. Every new movement should be as trustworthy as the eight that exist now, and it should come with the knowledge that justifies its highlights and cues.

## What exists

- **In 3D** (`src/studio/kits/fitness/exercises3d.js`): `curl`, `press` (dumbbell bench), `raise` (lateral), `squat`, `squat-blocked`, `hipthrust`, `calfraise`, `seatedcalf`. Each has authored tracks or a solved `m.path`, equipment from joints, `shots`, `phaseMap`, `acts` (roles 3/2/1), `knowledge` (an id in `exercises.json`) and sometimes `checks`. Solvers: `T3.squatSolver` (bar over midfoot), the hip-thrust arc around the bench contact, and `T3.heelLift` (ball of the foot fixed).
- **Knowledge records with no 3D yet** (`assets/fitness/data/exercises.json`, 21 records): push-up, dumbbell fly, pull-up, one-arm row, rear-delt fly, overhead press, prone Y-raise, incline curl, overhead triceps extension, dip, bodyweight squat, walk, jog, sprint. Several are 2D-only today (the 12-exercise 2D upper-body library).
- **Not in knowledge or 3D**: deadlift, Romanian deadlift, lunge and split squat, leg press, leg curl and leg extension (machines), lat pulldown and cable row (cable stack), barbell bench press, back squat from a rack, plank, a back-view push-up.

## What to build (choose the order; justify it)

A reasonable order is by teaching value and reuse of solvers: **hip hinge** (deadlift and RDL, which unlock "back safety" topics and need a bar-path solver with the bar over the midfoot and a spine that hinges rather than rounds), **lunge and split squat** (feet apart front to back, balance over a narrow base), **push-up and plank** (hands and feet both planted, a body line), **overhead press, row, pull-up and pulldown** (shoulder elevation extremes, scapular motion), **machines and cables** (leg press, curl, extension, cable stack: equipment that constrains the path), then **running gait** (walk, jog, sprint: cyclic, both feet leave the floor, arm swing; knowledge records already exist with a `kinematics_source`).

Equipment is part of the job: barbell and plates already exist (technique plates, radius 46). Add a rack, a pull-up bar, a cable stack with handle and rope, leg-press, curl and extension machines, a plyo box, a mat. Keep them in the Cobalt Sculpt language (`STYLE.md`): simple planes, few colours, nothing that steals focus from the body. A machine is built from joints and the motion it constrains, never hand-placed per frame.

## The standard for every new exercise

For each exercise, all of this, in one change:

1. **Knowledge first.** A record in `exercises.json` that validates against `specs/fitness-exercise-spec.json`: muscles with roles, phases, cues, common errors and corrections, camera angles, and an evidence grade with real sources. Use Europe PMC or another verifiable source, and never fabricate a citation, number or activation percentage. `fitness.py exercise <id> --goal technique` must print a sensible plan from it.
2. **Motion from contacts and balance**, not hand-posed frames (rules 3, 9). Write a solver when the lift has a defining constraint: bar path, centre of mass over the base, a hand or back pinned to equipment, a fixed pivot. Keep coupled joints on one `m.path` (rule 4). Every key carries the figure id prefix (rule 16), and every moved key has a declared base (rule 2).
3. **A `phaseMap`** that describes the motion (holds are still, lifting phases move), and a rhythm: a slower eccentric with `sine.inOut` and a faster concentric with `power2.inOut`, plus short holds (rule 5).
4. **`acts` audited by `fitness.py check`** against the knowledge record (rule 18). Activation ramps follow the work, colour steps stay under the limit, and ramps under cloth last at least 1.0 s (rule 11).
5. **Exercise-specific `checks`** that prove what the cues claim: a bar path within N units of vertical over the midfoot; a neutral spine within N degrees through a hinge; the front shin near vertical in a split squat when the cue says so; hands under the shoulders in a push-up; a hip line in a plank. If a cue can't be checked, say so in the record.
6. **Both bodies** pass `node scripts/rig3d-check.js <id>` (continuity, contacts, reach, limits, range of motion, phase fidelity, colour steps, orphan props).
7. **Stills sheet** from at least front, three-quarter, side and back, plus the exercise's own `shots`, at every phase, for both bodies. Look at it and write down what you saw. Fix posture problems at the solver, not with a per-frame override.
8. **Mistake variants** where the knowledge lists a common error worth teaching (as `squat-blocked` does): the same solver with one parameter changed, so correct and wrong can be shown side by side, in one world or in split views.
9. **Docs**: the motion-3d.md exercise list and limits, the fitness-animation skill if the workflow changed, and a changelog line on the `Studio.version` bump.

## Things that will bite (from past sessions)

- A lift that crosses the joint-limit edges (elbow 150, knee 150, shoulder 175) needs skinning that survives it. Check `02`'s findings first, and add the new extreme poses to its situation matrix.
- Two figures running paths at once both need to be applied (rule 14, fixed). Keep it working.
- Side views of barbell lifts sit at az ~72, not 90, or the plate covers the head (rule 12).
- The portrait layout limits (rule 13) decide the camera. Solve the camera from the header and caption limits, not by eye.
- Running needs both feet off the floor. The planted-sole check must understand flight phases instead of being switched off.
- Never invent lat, core or "isolation" claims for highlights. If the knowledge doesn't support a role, don't light it.

## Deliverables

- New exercises and equipment in the kit, each meeting the standard above, in a sensible number of version bumps (not one per exercise, and not one giant bump: group by solver)
- New knowledge records with verified sources
- Stills sheets, looked at, with notes in `prompts/state/log.md`
- A one-page "library" sheet: every 3D exercise at its key phases, both bodies, for the owner
- Render-queue entries for the Mac: a short motion-only lab clip per new solver family (via a `lab-3d-motion`-style project the Mac session can create), so the motion is judged in a real render too
- Updated `motion-3d.md` limits: what still isn't possible, and why
