---
name: session-handoff
description: Start or end a long Motion Lab work session honestly, across Windows and the Mac render host. Use at session start ("continue where the last session left off", "resume", "pick up the handoff"), before stopping ("pause", "write the handoff", "update the state files"), when queueing Mac-only work, or when an owner decision must be prepared. Covers the host probe, checking the tree matches the handoff, the four state files, the render queue and decision packs.
version: 1.0.0
---

# Session handoff: start honest, stop resumable

State lives in `prompts/state/` (gitignored; the owner carries it). Prompts live in `scripts/prompts/` (`00-shared-context.md` first).

## Start (before any edit)

| Check | How | Stop if |
| --- | --- | --- |
| Latest handoff | newest `prompts/state/handoff-*.md`, then `tracker.md` tail, `log.md` tail; `next-session-prompt.md` can be OLDER than these | two files disagree: trust the newest dated entry |
| Tree matches the handoff | compare `Studio.version` (`src/studio/studio-core.js`), `T3.anatomy` (`kits/fitness/anatomy3d.js`) and `F.t3d` (`kits/fitness/tibi3d.js`) versions and named exercises in `exercises3d.js` with the handoff | versions are older than the handoff: files were reverted. See "Revert recovery" |
| Branch and dirt | `git --no-pager status --short`, `git --no-pager branch --show-current` | never commit/push without the owner |
| Host lock | `.venv\Scripts\python.exe scripts/session-guard.py status` (macOS `.venv/bin/python`) | another session holds it: queue, never bypass. If the holder or queue matches a job the handoff says was started, it is still in flight: wait for its output file, do not start it again |
| Host tools | Windows: no HyperFrames/FFmpeg/Kokoro on PATH (see `host-windows.md`); macOS: render host | never claim a render, loudness or narration result you did not produce |

## Stop (before the turn ends or on "pause")

Update all four, append-only where dated: `log.md` (did / verified how / NOT verified / next), `render-queue.md` (exact command, branch, why, what to look at on the Mac), `decisions-needed.md`, `host-windows.md`; plus `tracker.md` and a dated `handoff-<date>.md` when work is mid-flight. Give exact start times and output paths of jobs still running, and say which next steps are already partly done. Leave no scratch project, no held lock, no half-applied edit; say so in the log.

## Owner decision pack

Options (2-4), evidence (sheet paths, numbers), cost, a recommendation, and what happens by default if unanswered. Record it in `decisions-needed.md`; never decide it in code (`00-shared-context.md` section 7).

## Revert recovery (seen 2026-11-25)

A VS Code chat editing session (`%APPDATA%\Code\User\workspaceStorage\<id>\chatEditingSessions\<chat>\state.json`) can write its old snapshot back over files it once edited. Symptom: many files with one identical new mtime and older versions. Do not build on it:

1. Back up the current files to `prompts/state/recovery/<date>-reverted/`.
2. Newest surviving copies: `projects/*/src/_studio/` (vendored, hash-listed in `studio.lock.json`), frozen kits under `prompts/state/**/kit/`, `**/pre/`.
3. Replay later changes from `~/.copilot/session-state/*/events.jsonl` (`edit` old/new strings, `create` text, full `view` results as checkpoints, PowerShell `WriteAllText`/`AppendAllText` commands in a TEMP sandbox), rebasing on every checkpoint.
4. Verify against recorded outputs (for example `known-limits/r3b/final-anatomy-check.txt`) before continuing.
