# Prompts: handing Tibi and the pending work to another model

Mission prompts for a capable model taking over Tibi's 2D and 3D design on a **Windows machine without Kokoro**, plus the complex pending work and the skills to make repetitive work cheaper. Written 2026-11-19.

This folder is **gitignored** (owner rule: prompt files stay out of git), so it doesn't arrive with `git clone`. Copy it to the Windows machine by hand, and copy `prompts/state/` back to the Mac after each Windows session.

## Files

| File | For | What it asks |
|---|---|---|
| `00-shared-context.md` | **every session, read first** | owner's standing orders, the map of both Tibis, the Windows hazards, what is and isn't in git, the handoff protocol (`prompts/state/`), decisions reserved for the owner, definition of done |
| `01-tibi-design-takeover-windows.md` | Windows | own Tibi's design (2D and 3D as one character): make the host honest, audit, set direction, improve in verified steps |
| `02-tibi-3d-perfection.md` | Windows | analyse and perfect 3D Tibi across a situation matrix (cameras, poses, extremes, modes, framing, sizes, motion), with new numeric checks proven to bite, fixes at the source and an acceptance suite |
| `03-pending-work-plan.md` | everyone | **the plan**: tracks A–I, order, host, dependencies and owner decisions for all complex pending work |
| `04-pending-3d-exercise-library.md` | Windows (authoring), Mac (films) | port hinge, lunge, push-up, presses, pulls, machines and running to 3D, with knowledge, solvers, checks and stills |
| `05-pending-2d-3d-unification.md` | Windows | the look decision pack, 2D pop fixes, kit gaps, exports, generator hygiene (owner-gated) |
| `06-pending-studio-tooling.md` | either | the studio lint and runtime backlog from `TODO.md` |
| `07-ai-skills-for-repetitive-work.md` | either | find recurring procedures from evidence and turn the worthwhile ones into registered, trialled skills |
| `08-mac-render-host-handoff.md` | **Mac** | take in Windows branches, verify macOS behaviour, upgrade, drain the render queue, run audio work, report back |

## How to start a session

- **Windows, first time:** give the model `00` + `01` and say how much autonomy it has (for example, "you may commit on `windows/*` branches; don't push"). After `01` Phase 1, continue with `02`, then `04`/`05`, using `03` to choose.
- **Windows, any tooling session:** `00` + `06` (or `07`).
- **Mac:** `00` + `08` whenever `prompts/state/render-queue.md` has entries.

Suggested opening line: *"Read prompts/00-shared-context.md and prompts/0N-….md, then prompts/state/ if it exists, and carry on from where the log stops."*

## Before the first Windows session, the owner should

1. Clone the repo on Windows with line endings preserved: `git config --global core.autocrlf false` **before** cloning.
2. Copy this `prompts/` folder over.
3. Optionally copy the reference projects the 3D work learns from (not in git): `projects/lab-3d-motion`, `knees-past-toes`, `hip-thrust-vs-squat`, `standing-vs-seated-calf`, `upper-body-workout`, `how-muscles-grow`. Leave out `renders/` and `audio/*.wav` to keep the copy small.
4. Install what the tools expect if possible: Python 3.12 with a `.venv`, Node, and Chrome/Playwright. HyperFrames and FFmpeg are optional; the prompts tell the model to probe for them and plan around what's missing.

`prompts/state/` is created by the model on its first session.
