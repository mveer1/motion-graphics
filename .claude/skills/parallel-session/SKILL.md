---
name: parallel-session
description: Coordinates concurrent multi-project production sessions in this workspace without hardware contention, memory crashes on Apple Silicon, or false-positive governance failures.
---

# Parallel Session Skill (`parallel-session`)

This skill coordinates autonomous or semi-autonomous agent sessions producing motion graphics concurrently in this workspace.

---

## 0. Prime Directive: Quality First, Concurrency Second

1. **Zero Quality Compromise:** Parallelism must never reduce video bitrate, skip QA gates, lower framerates, bypass review rubrics, or disable loudness normalization. Speed and concurrency are strictly secondary to delivery quality.
2. **Transparent Fallback:** When working on a single project in isolation (no parallel sessions), standard commands (`python scripts/studio.py build <slug>`, `./scripts/build-project.sh <slug>`) function normally. This skill wraps and protects execution only when multi-session safety is required.

---

## 1. Concurrency Architecture

The workspace operates on an **Apple Silicon M2 (8 GB Unified Memory)** host.
Memory is shared between CPU and GPU (Metal).

### Stage Independence Breakdown

- **Stages 0, 1, 2, 4, 5 (Shared-Nothing / Fully Concurrent):**
  - Stage 0 & 0R (Brief & Research: `brief.json`, `research.json`)
  - Stage 1 (Storyboard: `storyboard.json`)
  - Stage 2 (Scriptwriting: `narration.json`)
  - Stage 4 (Composition: `src/index.html`, `studio.py formats`, `studio.py sync`)
  - Stage 5 (Local Project Validation: `python scripts/studio.py validate <slug>`)
  *Rule:* Run these freely in parallel across distinct project slugs.

- **Stages 3 & 6 (Hardware Contention / Mutually Exclusive):**
  - **Stage 3 (Speech Synthesis):** PyTorch resident memory in Kokoro TTS. Guarded by `tts` lock.
  - **Stage 6 (Visual Rendering & Preview QA):** Headless Chromium with ANGLE Metal GPU rasterization. Guarded by `render` lock. Never run multiple Chromium render instances simultaneously.

---

## 2. Using Session Guard CLI

When working with this skill attached, route hardware-bound and governance commands through `scripts/session-guard.py`.

### 1. Isolated Git Worktree Sessions
Spawn an isolated working tree on a dedicated session branch so parallel sessions never collide on git status or uncommitted files:
```bash
# Start an isolated session (optionally scaffold a project template):
python3 scripts/session-guard.py session-start <slug> [--template illustrated-explainer]

# List all active sessions and worktrees:
python3 scripts/session-guard.py session-list

# Tear down the session when finished (optionally merge to main branch):
python3 scripts/session-guard.py session-end <slug> [--merge]
```

### 2. Project-Scoped Governance Audit
Avoid global repository audit failures caused by other in-progress projects:
```bash
python3 scripts/session-guard.py govern <slug>
# Equivalent to: python3 scripts/workspace-governance.py --project <slug>
```

### 3. Guarded Neural Audio Synthesis (Stage 3)
Acquires the `tts` lock so PyTorch memory does not collide with other voice jobs:
```bash
python3 scripts/session-guard.py audio <slug> [--speed 1.15] [--voice am_adam]
```

### 4. Guarded Preview QA (Stage 6 Preview)
Acquires the `render` lock to protect Playwright Chromium memory:
```bash
python3 scripts/session-guard.py review <slug> [--fonts google]
```

### 5. Guarded Master Render & Multiplexing (Stage 6 Render & Stage 8)
Acquires exclusive access to the Chromium + Metal GPU render pipeline. If another session is rendering, it automatically pauses, logs status every 10s, and resumes seamlessly when the host is free:
```bash
python3 scripts/session-guard.py build <slug> [--quality looks|delivery] [--formats landscape,portrait,square]
```

### 6. Inspecting or Clearing Locks
```bash
# Check who currently holds hardware locks
python3 scripts/session-guard.py status

# Self-heal / clear stale locks if a previous process died abruptly
python3 scripts/session-guard.py unlock
```

---

## 3. Best Practices for Parallel Agents

1. **Unique Project Slugs:** Always ensure the project directory `projects/<slug>` is unique.
2. **Local Asset Isolation:** Download sound effects directly into `projects/<slug>/audio/sfx/` and ingested videos into `projects/<slug>/assets/` to avoid filename clashes in root `assets/`.
3. **Canonical Runtime Protection:** Do not modify canonical files in `src/studio/` during active production runs. If modifications are required, coordinate with `workspace-steward`.

