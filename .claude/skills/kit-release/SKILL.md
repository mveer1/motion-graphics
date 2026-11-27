---
name: kit-release
description: Release a change to the studio runtime or a kit under src/studio/ (fitness 3D anatomy, Tibi rig, exercises, 2D sculpt, film helpers). Use when you bumped or must bump Studio.version, "release the kit", "upgrade all projects", "finish the runtime change", or before handing kit work to another session or the Mac.
version: 1.0.0
---

# Kit release: one ritual, every step

A runtime change is not done until every project carries it and every check that reads it has run. Order matters: version first, upgrade last.

| # | Step | Command (repo root; Windows: `.venv\Scripts\python.exe`, macOS: `.venv/bin/python`) |
| --- | --- | --- |
| 1 | Bump the label with ONE changelog comment that names every sub-version (anatomy, Tibi, sculpt, helpers) | edit `Studio.version` in `src/studio/studio-core.js` |
| 2 | Same version in the catalogue | `catalogue/data/shared/studio-runtime.json` and `fitness-kit.json` (`version`, `last_verified`) |
| 3 | Syntax | `node --check` on every changed `.js` |
| 4 | Numeric gates, one at a time under the lock | `python scripts/session-guard.py run render -- node scripts/anatomy3d-check.js` (also `--profile legacy`), `... node scripts/rig3d-check.js` and `--gender f` |
| 5 | Kit audits | `python scripts/fitness.py check`, `python scripts/fitness.py sculpt --check` |
| 6 | Tests you touched (no runner) | `python tests/test-fitness.py`, `test-studio-runtime.py`; the long ones (`test-anatomy3d.py`, `test-rig3d.py`) under the lock |
| 7 | Governance | `python scripts/motion-catalogue.py validate`, `python scripts/workspace-governance.py`, `ruff check <touched .py>` |
| 8 | Release to projects | `python scripts/studio.py upgrade --all` (re-sync `_studio/`, regenerate `index.<format>.html`, move stale renders to `renders/history/`) |
| 9 | Prove the release | `python scripts/studio.py validate <slug>` on each local project; `studio.lock.json` hashes now match the canonical files |
| 10 | Record | docs/skills that describe the change, `prompts/state/render-queue.md` (Mac re-renders), `log.md` (what was NOT run) |

Rules

- Never edit `projects/*/src/_studio/`; never hold a bump back because old videos go stale.
- `upgrade --all` touches every project, including other sessions' work: check `session-guard.py status` and `session-list` first and say which projects moved.
- Legacy profile must hash identically unless the change is meant to alter it.
- No render/loudness claim on Windows (no HyperFrames/FFmpeg/Kokoro there).
- If the tree's versions do not match the last handoff, stop and investigate before releasing (see `session-handoff`).
