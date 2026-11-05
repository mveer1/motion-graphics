---
name: parallel-session
description: Coordinates concurrent multi-project production sessions in this workspace without hardware contention, memory crashes on Apple Silicon, or false-positive governance failures. Any number of sessions can author in parallel; heavy jobs (render, TTS, analysis) queue one at a time.
---

# Parallel Session Skill (`parallel-session`)

This skill coordinates autonomous or semi-autonomous agent sessions producing motion graphics concurrently in this workspace.

---

## 0. Prime Directive: Quality First, Concurrency Second

1. **Zero Quality Compromise:** Parallelism must never reduce video bitrate, skip QA gates, lower framerates, bypass review rubrics, or disable loudness normalization. Speed and concurrency are strictly secondary to delivery quality.
2. **Transparent Fallback:** When working on a single project in isolation (no parallel sessions), standard commands (`python scripts/studio.py build <slug>`, `./scripts/build-project.sh <slug>`) function normally. This skill wraps and protects execution only when multi-session safety is required.

---

## 1. Capacity: how many sessions?

**There is no session limit.** Each session is a git worktree (`.worktrees/<slug>`) on its own `session/<slug>` branch, so 2, 5 or 10 sessions can all author at once. What is limited is the **heavy host**: the 8 GB Apple Silicon machine runs **one heavy job at a time**, across all sessions.

| Work | Runs in parallel across sessions? |
|---|---|
| Brief, research, storyboard, narration script, composition, `studio.py validate/formats/sync`, `session-guard.py govern` | **Yes**, any number |
| Heavy jobs: Chromium render, Playwright frame-review (`render`), Kokoro TTS (`tts`), reference analysis and Whisper (`analysis`) | **No**, one at a time. They share a single host lock, so a Kokoro job and a render never overlap either |

Sessions that need the host wait in a first-come-first-served queue and start by themselves when it frees up. A portrait render is about 100 to 120 s, so even a deep queue clears in minutes. The wait limit is `MOTION_LAB_LOCK_TIMEOUT` (default 7200 s).

What actually bounds the session count is memory, not code: each agent session holds roughly 250 MB, a render about 0.8 GB and Kokoro about 1.4 GB. Check headroom any time with `python3 scripts/session-guard.py status`; it warns when less than the ~1.5 GB a Kokoro job needs is free. If it warns, close other apps (browsers, editors) before starting a heavy job. Sessions that only author cost almost nothing.

### Stage independence

- **Stages 0, 1, 2, 4, 5 (shared-nothing, fully concurrent):** brief and research (`brief.json`, `research.json`), storyboard, narration script (`narration.json`), composition (`src/index.html`, `studio.py formats`, `studio.py sync`), local validation (`studio.py validate <slug>`). Run these freely across distinct project slugs.
- **Stages 3 and 6 (hardware, serialized):** speech synthesis and visual rendering / preview QA. Never launch `hyperframes render`, headless Chromium or Kokoro by hand; use the commands below.

### Which entry points lock for you

These take the host lock themselves, so calling them directly is safe: `studio.py build`, `studio.py captions --timing words`, `build-audio.py`, `src/pipeline/tts.py`, `frame-review.py`, `reference-corpus.py doctor|analyze|strip`, the render stage of `build-project.sh` and `render.sh`. The lock is re-entrant: `session-guard build` calling `studio.py build` calling `build-audio.py` is one job, not three. Anything else heavy (a raw `hyperframes render`/`snapshot`, `node` probes) goes through `session-guard.py run`.

---

## 2. Playbook for N parallel sessions

1. **Commit first.** A worktree branches from the last commit, not from your working tree. Uncommitted edits to `scripts/`, `specs/`, `src/`, `catalogue/`, `.claude/` are missing from the new session, and `session-start` lists them. Commit them, or the session runs older tooling.
2. **Start a session per film:** `python3 scripts/session-guard.py session-start <slug> [--template illustrated-explainer]`, then `cd .worktrees/<slug>`.
3. **Stay inside `projects/<slug>/`** (plus its `series/` entry and `out/`). Do not edit `src/studio/`, `specs/`, `catalogue/` or generated files such as `catalogue/index.json` in a session branch; two sessions touching the same shared file conflict at merge. `session-list` shows which sessions touched shared files.
4. **Heavy steps just run.** `python scripts/studio.py build <slug>` waits its turn and prints its queue position. Watch the host with `session-guard.py status`.
5. **Finish with** `python3 scripts/session-guard.py session-end <slug> --merge` (after committing in the worktree). It checks the merge for conflicts first and changes nothing if there would be any, copies the session's gitignored renders, audio and `out/*.mp4` into the main checkout (removing the worktree would delete them), removes the worktree, then merges. Afterwards run `studio.py validate <slug>` in main, because the session may have used older specs.
6. **Worktrees created before a tooling change keep the old `session-guard.py`** (a worktree carries its own copy of every script). A new-style job also takes the old per-resource lock file, so a new render and an old-style render still exclude each other; a new Kokoro job and an old-style render do not. Finish or recreate old worktrees after committing, and use `session-list`/`status` to see who is running what. Delete `_take_legacy_lock` in `scripts/session-guard.py` once no old worktree remains.

---

## 3. Using Session Guard CLI

Route hardware-bound and governance commands through `scripts/session-guard.py`.

### 1. Isolated Git Worktree Sessions
```bash
# Start an isolated session (optionally scaffold a project template):
python3 scripts/session-guard.py session-start <slug> [--template illustrated-explainer]

# Dashboard of every session: commits ahead/behind, uncommitted files, renders not yet in main,
# predicted merge conflicts, shared files touched, and who holds or waits for the host:
python3 scripts/session-guard.py session-list

# Finish: conflict check, copy renders/audio to main, remove worktree, merge:
python3 scripts/session-guard.py session-end <slug> [--merge]
```

### 2. Project-Scoped Governance Audit
Avoid global repository audit failures caused by other in-progress projects:
```bash
python3 scripts/session-guard.py govern <slug>
# Equivalent to: python3 scripts/workspace-governance.py --project <slug>
```

### 3. Guarded Neural Audio Synthesis (Stage 3)
```bash
python3 scripts/session-guard.py audio <slug> [--speed 1.15] [--voice am_adam]
```

### 4. Guarded Preview QA (Stage 6 Preview)
```bash
python3 scripts/session-guard.py review <slug> [--fonts google]
```

### 5. Guarded Master Render & Multiplexing (Stage 6 Render & Stage 8)
If another session holds the host, this queues and resumes by itself, logging status every 30 s:
```bash
python3 scripts/session-guard.py build <slug> [--quality looks|delivery] [--formats landscape,portrait,square]
```

### 6. Any other heavy command
Options go before the resource name; the command runs in the repo root unless `--cwd` is given:
```bash
python3 scripts/session-guard.py run --slug <slug> --cwd /abs/path/to/src render -- hyperframes snapshot . --at 4 --output /abs/out < /dev/null
```
Resources are `render`, `tts` and `analysis`; all three share the one host lock.

### 7. Inspecting or Clearing the Lock
```bash
# Who holds the host, who is queued (in order), and free memory:
python3 scripts/session-guard.py status

# Clear stale state left by a crashed process (a dead holder frees the lock by itself):
python3 scripts/session-guard.py unlock

# Stop a hung live holder: SIGTERM, it kills its own job tree, then the lock frees:
python3 scripts/session-guard.py unlock --force
```

### Crash safety
If a guarded process is stopped (SIGTERM, SIGHUP, Ctrl-C, an agent tool timeout), it first kills every process it started, including detached Chrome helpers, then releases the lock. The next queued session never starts on top of a half-dead render. A `kill -9` on the guard cannot be intercepted: afterwards check `ps` for stray `chrome`/`ffmpeg`/`node` before the next job.

---

## 4. Best Practices for Parallel Agents

1. **Unique Project Slugs:** Always ensure the project directory `projects/<slug>` is unique.
2. **Local Asset Isolation:** Download sound effects directly into `projects/<slug>/audio/sfx/` and ingested videos into `projects/<slug>/assets/` to avoid filename clashes in root `assets/`.
3. **Canonical Runtime Protection:** Do not modify canonical files in `src/studio/` during active production runs. If modifications are required, coordinate with `workspace-steward`.
4. **Never bypass the queue.** Do not run `hyperframes render`, a headless browser or Kokoro directly while other sessions are active.
5. **Tuning knobs (environment):** `MOTION_LAB_LOCK_TIMEOUT` (queue wait, seconds), `MOTION_LAB_LOCK_POLL` (queue check interval, seconds), `MOTION_LAB_LOCK_DIR` (lock directory; tests only).
