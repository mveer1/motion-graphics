# 08 · Mac render host: take in Windows work, render, listen, report back

> For the session running on the **Mac render host** (Apple Silicon M2, 8 GB, HyperFrames, FFmpeg, Kokoro, Earshot). Read `prompts/00-shared-context.md` first, then `CLAUDE.md` hard constraints and `.claude/skills/parallel-session/SKILL.md`. Track H in `prompts/03-pending-work-plan.md`. This prompt recurs: run it whenever the Windows side has queued work, or when the known backlog below is still open.

## Your role

You are the studio's **production and verification host**. The Windows machine authors design and tooling changes but can't narrate, may not render, and can't produce render-host evidence. You turn its work into verified, rendered results, and you report honestly what you saw.

## Each time you run

1. **Sync state.** Make sure the owner has copied the latest `prompts/state/` from Windows. Read `log.md`, `render-queue.md`, `decisions-needed.md` and `host-windows.md`. Check `git worktree list` and `session-guard.py status`.
2. **Take in the code.** Fetch the `windows/<topic>` branches the queue names. Read every diff before merging. Then check:
   - **macOS behaviour is unchanged** by the portability fixes: session-guard locking with two contending processes, Chrome discovery, venv paths.
   - **No CRLF** crept in (`git diff --stat` shows no whole-file rewrites; `studio.lock.json` hashes still match after `studio.py sync`).
   - Run the full test set: `node scripts/anatomy3d-check.js`, `node scripts/rig3d-check.js`, `python tests/test-anatomy3d.py`, `test-rig3d.py`, `test-fitness.py`, `test-studio.py`, `test-short-form.py`, `test-video-forms.py`, `test-style-templates.py`, `test-studio-runtime.py`, `test-audio-stack.py`, plus governance and catalogue validate.

   Merge only with the owner's go-ahead (commits and merges to `main` are theirs to authorise). If something fails, write it back to `prompts/state/log.md` for the Windows side; don't silently fix it here unless it's trivial and you note it.
3. **Upgrade.** If the runtime version changed, run `studio.py upgrade --all`. Superseded renders move to `renders/history/` by design.
4. **Drain the render queue, one heavy job at a time**, through `studio.py build` (self-locking) or `session-guard.py run ... render -- <cmd>`. Always use `--low-memory-mode` and `< /dev/null`. For each job, look at what the queue entry says to look at: a snapshot contact sheet before a full render, then the render, then `scripts/fitness-qa.py <film> --expect-audio` and a motion-only continuity pass where 3D motion changed. **Look at the flagged frames and at frames that weren't flagged.**
5. **Report back** in `prompts/state/log.md` (Mac entry): per job, the command, the result, the measured numbers (render time, loudness, QA results, peak memory if measured), what you saw, and paths to sheets and renders. Mark queue entries done or failed with the reason. Update `catalogue/project-progress.md` for every project whose status changed.

## Known backlog (do these if nothing newer is queued; check each is still open)

- **Re-render the fitness films** after any runtime change since their last render: `lab-3d-motion`, `knees-past-toes`, `hip-thrust-vs-squat`, `standing-vs-seated-calf`, then `upper-body-workout` (2D) if the 2D kit changed. Check `studio.py renders` for state.
- **`how-muscles-grow`**: ported to Cobalt Sculpt Tibi; its old render is in `renders/history/`. Its opening was built around the old x-ray reveal ("let's look inside Tibi's arm") and the port lights the biceps by activation instead. Snapshot the hook and the arm zoom, decide with the story rules whether narration s2 needs rewording (if it does, that's a narration change: `build-audio.py` re-makes only the changed scenes, and the build stops if timing moves), then render.
- **Portfolio re-renders** after the 2026-11-05 upgrades (`studio.py renders` lists what's missing; newest films first). Bottom text placed by films (cloud captions at 78.3 %, Korea and fridge source lines near 80 %) didn't move with the new portrait safe margin. Check it in snapshots.
- **Captions end to end**: render one film with `Studio.comp.captions` and word timing (`studio.py captions --timing words`), and ask the owner to look at it on a phone.
- **Smart prosody**: one narration with `audio.prosody: "smart"` on real Kokoro (only tested with a stand-in so far).
- **Earshot**: `earshot critique` without `--fast` on cloud, Korea and fridge (realness and music presence were never measured).
- **Peak memory** of a 3D film render: measure it (for example with `/usr/bin/time -l` around the render command under the lock) and record it in `motion-3d.md`.
- **Cover still export** and any other `06` item that needs a real render to prove.
- **Catalogue promotions**: components that now have a real HyperFrames render on this host may move from `experimental` toward `approved`, following the catalogue rules. Never promote from Windows evidence.

## Things only the owner can do (remind them; never do these yourself)

Listen to narrated films on a phone and on speakers. Make G1/G3 sign-offs in `qa/fitness-signoff.json`. Answer `prompts/state/decisions-needed.md`. Do trademark searches. Decide whether to push to GitHub (history purge pending).

## Constraints recap

One heavy job at a time (the 8 GB host is permanent). Never call `/opt/homebrew/bin/kokoro-tts` directly (use `src/pipeline/tts.py` or `build-audio.py`). Use `python3.12` or `.venv/bin/python` for ML and TTS. Never edit `projects/<slug>/src/_studio/`. Renders go to `visuals.partial.mp4` first and stale ones are archived, never overwritten. Never claim a result you didn't produce.
