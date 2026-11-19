# 03 · Plan for the complex pending work

> Read `prompts/00-shared-context.md` first. This file is the **plan**: what is open, how it is grouped, the order, which machine runs it and who decides. Each track that is big enough has its own prompt (`04`–`08`). A capable model should run one track at a time, reading this plan to see where its track sits.

Sources: `TODO.md`, `docs/fitness-studio.md` §5, `.claude/skills/fitness/references/motion-3d.md` "Known limits", and the memory of the 2026-11-12/13 fitness sessions. Re-check each item against the code before starting: some may have been done since 2026-11-19.

## Tracks at a glance

| # | Track | Prompt | Host | Size | Depends on | Owner decision blocks? |
|---|---|---|---|---|---|---|
| A | Windows host enablement (portability, lock, Chrome discovery, line endings) | `01` Phase 0 | Windows | S–M | none | No |
| B | Tibi takeover: audit, direction, 2D↔3D consistency | `01` | Windows | L | A | Partly (look) |
| C | 3D Tibi perfection across situations (skinning, muscle shape, shading, clothing, acceptance suite) | `02` | Windows (looks), Mac (film re-renders) | XL | A | Look-changing options only |
| D | 3D exercise and equipment library expansion | `04` | Windows (author and check), Mac (films) | XL | A; best after C's skinning fixes | No |
| E | 2D/3D unification, 2D kit gaps, exports (Lottie/Rive, PNG), generator hygiene | `05` | Windows | L | A, B's direction note | **Yes**: look, dead-code removal, rounding quirk |
| F | Studio tooling backlog (pure Python and lint work) | `06` | Either (Windows fine) | L | none | Some items |
| G | Skills for repetitive work | `07` | Either | M | Do after a first pass of B/C/D, so the skills encode real repetition | No |
| H | Render-host queue: re-renders, audio, listens, measurements | `08` | **Mac only** | M, recurring | whatever the other tracks queue | No |
| I | Owner decisions | none (prepared by every track) | Owner | n/a | n/a | They *are* the decisions |

**Recommended order:** A → B (audit only) → C ∥ F → D → E → G → H drains continuously. F is independent and can fill gaps while waiting for owner answers. Never run two heavy jobs at once, even on Windows.

## Track details

### A · Windows host enablement (inside `01`, Phase 0)
`session-guard.py` (`fcntl`), Chrome discovery and `file://` URLs in `anatomy3d-bench.py` and `rig3d-stills.py`, `.venv/bin` and `/opt/homebrew` assumptions (about 20 scripts), CRLF vs SHA-256 locks and byte-identical baselines, and `python3.12` naming. **Accept** when the full Tibi design loop runs on Windows (2D rebuild byte-identical, `sculpt --check`, node checks, the fitness/anatomy/rig tests, one bench sheet and one stills sheet) and macOS behaviour is unchanged (state what you checked; the Mac session re-runs the tests from `08`).

### B · Tibi takeover (`01`)
A design state report, a 2D↔3D consistency table, a test-strength audit, and a design-direction note. **Accept** when the owner can make the look decision from the decision pack alone.

### C · 3D perfection (`02`)
The situation matrix, new numeric checks that are proven to bite, a defect taxonomy, fixes at the source, and an acceptance suite. Known items to settle: deltoid and pec ovals; tendon and fascia; the female top; the shorts hem; the flat-disc quad on a horizontal thigh; the floor-facing hip-thrust glute; the shoe sole and foot roll; the bench spine curve; ponytail secondary motion; skinning artefacts at deep flexion. **Accept** when the acceptance report shows start vs end per situation and every remaining fail is a named, explained limit.

### D · Exercise and equipment library (`04`)
Port, in a sensible order: deadlift and RDL (hip hinge with a bar path), lunge and split squat, push-up (and a back-view push-up), plank, leg press, leg curl and extension (machines), lat pulldown and cable row (cable stack), barbell bench press, back squat with a rack, running gait. Each needs a knowledge record, `phaseMap`, `acts` audited by `fitness.py check`, `shots`, `checks`, and stills from four angles. **Accept** per exercise when it is in the library, passes `rig3d-check` for both bodies with its own assertions, and has a stills sheet that was looked at.

### E · 2D/3D unification and 2D kit (`05`)
Depends on the owner's look decision. Without it, prepare both directions. Other items: the 2D arm-swap pops (`armState()` thresholds) and whether 2D lifts should simply move to 3D; front-view squat foreshortening; kit gaps (a vascular tree, alveolus gas exchange, joint cross-sections, a clearer leg-press setup); a Lottie/Rive export; PNG export via Playwright; the handover's dead code (owner); the rounding quirk (owner); faces and lip-sync **not** wanted now (owner, 2026-11-09). **Accept** per item.

### F · Studio tooling backlog (`06`)
Not Tibi-specific, but complex and pending: promote the repeated film helpers into `src/studio/`; a pre-render film-time gap audit; make `motion-qa` read the style template; hook clarity lint; pace budgets in `style check`; speed-aware time estimates in `scriptlint` and `beatmap storyboard`; a `named_things` check; the cover still export; the publish metadata location (proposal only); the test fixture for `tests/test-studio.py` on a fresh clone (proposal only); and the fitness kit lessons folded into the `fitness-explainer` template. **Accept** per item with a test.

### G · Skills (`07`)
After real repetition is visible in the logs.

### H · Render-host queue (`08`)
Known items already waiting, before anything new: re-render `how-muscles-grow` (ported to the new Tibi; check its hook and arm zoom first); the portfolio re-renders after runtime upgrades (`studio.py renders` lists them; newest first); the fitness films after any runtime change from C/D; render one captioned film end to end and look at it on a phone; one smart-prosody narration on real Kokoro; `earshot critique` without `--fast` on cloud, Korea and fridge; measure peak render memory of a 3D film; and a human listen to the upper-body film's pronunciations (the owner).

### I · Owner decisions (keep `prompts/state/decisions-needed.md` current)
The 3D look vs 2D crescent; how far anatomy fidelity goes and whether a sculpted asset or Blender is allowed (an ADR-1/ADR-9 case); 2D dead-code removal and the rounding quirk; G1/G3 sign-offs; trademark searches; AI-content disclosure; the definition of a "visual style" and the style tags; how a series is published; the publish metadata location; whether to build a JEV; history purge and force-push; the analytics source; the test-fixture approach.

## Risks the plan accounts for

- **The Windows and Mac trees diverge.** All code goes through `windows/<topic>` branches and the Mac session (`08`) merges, re-tests and renders. Never edit the same kit file on both machines between merges.
- **Stale films after kit changes** are expected (owner rule). Queue the re-renders and don't hold back the change.
- **Over-fitting to the bench.** Every kit change is checked the way films use it (figures built with ids, real cameras, overlays present), and at least one real composition (`qa/regression/lab-3d-compare` is in git) is snapshotted before a version bump.
- **Look drift without consent.** Look-changing work ships behind an option until the owner rules.
- **Silent test weakness.** Every new check is shown to fail on a broken case.
