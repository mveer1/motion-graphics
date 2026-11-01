#!/usr/bin/env python3
"""
scripts/session-guard.py
Concurrency Coordinator & Lock Engine for Motion Lab multi-session workflows.

Provides mutual exclusion locks for hardware-bound bottlenecks (Chromium render host,
Kokoro TTS, Playwright frame-review) on Apple Silicon macOS without compromising quality
or altering existing single-project pipelines.

Usage:
  python scripts/session-guard.py build <slug> [--quality Q] [--formats F] [--dry-run]
  python scripts/session-guard.py audio <slug> [--speed S] [--voice V]
  python scripts/session-guard.py review <slug> [--fonts google]
  python scripts/session-guard.py govern <slug> [--strict]
  python scripts/session-guard.py run <resource-name> -- <command...>
  python scripts/session-guard.py status
  python scripts/session-guard.py unlock [--force]
"""

import argparse
import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCK_DIR = REPO_ROOT / ".locks"
PROJECTS_DIR = REPO_ROOT / "projects"
WORKTREES_DIR = REPO_ROOT / ".worktrees"

# Defined hardware-critical shared resources
RESOURCE_RENDER = "render"       # HyperFrames Headless Chromium + Metal GPU & Playwright
RESOURCE_TTS = "tts"             # Kokoro Neural Voice Synthesis (PyTorch Resident Memory)
RESOURCE_ANALYSIS = "analysis"   # Reference video corpus analysis


def is_pid_alive(pid: int) -> bool:
    """Check if process with PID is currently running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@contextlib.contextmanager
def acquire_lock(
    resource: str,
    slug: Optional[str] = None,
    timeout_sec: int = 7200,
    poll_interval: float = 2.0,
) -> Generator[Path, None, None]:
    """
    Acquire a cross-process mutual exclusion file lock using fcntl.flock.
    If the lock is busy, waits and logs a heartbeat until released or timed out.
    Automatically detects and cleans stale locks if the holding PID died.
    """
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_DIR / f"{resource}.lock"
    meta_file = LOCK_DIR / f"{resource}.json"

    start_time = time.time()
    waited = False

    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        while True:
            try:
                # Try non-blocking exclusive lock
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                # Lock is currently held. Check metadata to inspect holder
                holder_info = "Unknown"
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        holder_pid = meta.get("pid")
                        holder_slug = meta.get("slug", "unknown")
                        holder_time = meta.get("acquired_at", "")
                        
                        # Detect dead holder process (stale lock cleanup)
                        if holder_pid and not is_pid_alive(holder_pid):
                            print(f"[SessionGuard] ⚠️ Found stale lock held by dead PID {holder_pid} ({holder_slug}). Cleaning up...")
                            try:
                                fcntl.flock(fd, fcntl.LOCK_UN)
                            except Exception:
                                pass
                            if meta_file.exists():
                                meta_file.unlink(missing_ok=True)
                            time.sleep(0.5)
                            continue

                        holder_info = f"PID {holder_pid} (project: '{holder_slug}', since {holder_time})"
                    except Exception:
                        pass

                elapsed = int(time.time() - start_time)
                if elapsed > timeout_sec:
                    raise TimeoutError(
                        f"[SessionGuard] Timed out after {timeout_sec}s waiting for '{resource}' lock held by {holder_info}."
                    )

                if not waited:
                    print(f"[SessionGuard] ⏳ Resource '{resource}' is busy, held by {holder_info}.")
                    print(f"[SessionGuard] ⏳ Waiting politely for lock release (preserves 8 GB Apple Silicon stability)...")
                    waited = True
                elif elapsed % 10 == 0:
                    print(f"[SessionGuard] ⏳ Still waiting for '{resource}' lock ({elapsed}s elapsed)...")

                time.sleep(poll_interval)

        # Successfully acquired lock
        lock_meta = {
            "resource": resource,
            "pid": os.getpid(),
            "slug": slug or "workspace",
            "acquired_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": time.time(),
        }
        meta_file.write_text(json.dumps(lock_meta, indent=2), encoding="utf-8")
        print(f"[SessionGuard] 🔒 Lock '{resource}' acquired for project '{slug or 'workspace'}' (PID {os.getpid()}).")

        try:
            yield lock_file
        finally:
            meta_file.unlink(missing_ok=True)
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
            print(f"[SessionGuard] 🔓 Lock '{resource}' released.")
    finally:
        os.close(fd)


# --------------------------------------------------------------------------- Subcommands

def cmd_status(args: argparse.Namespace) -> int:
    """List active locks and their holding processes."""
    print("=" * 65)
    print("SESSION GUARD CONCURRENCY STATUS")
    print("=" * 65)
    if not LOCK_DIR.exists():
        print("No locks directory found (.locks/). All resources are idle.")
        return 0

    found = False
    for meta_path in sorted(LOCK_DIR.glob("*.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pid = meta.get("pid")
            alive = is_pid_alive(pid) if pid else False
            status_str = "ACTIVE" if alive else "STALE (Process Dead)"
            print(f"  • Resource   : {meta.get('resource')}")
            print(f"    Project    : {meta.get('slug')}")
            print(f"    PID        : {pid} [{status_str}]")
            print(f"    Acquired At: {meta.get('acquired_at')}")
            print("-" * 65)
            found = True
        except Exception as e:
            print(f"  • Error reading {meta_path.name}: {e}")

    if not found:
        print("All resources (render, tts, analysis) are IDLE. No active locks.")
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    """Force release all or stale locks."""
    if not LOCK_DIR.exists():
        print("No locks to clear.")
        return 0
    cleared = 0
    for p in LOCK_DIR.glob("*"):
        if args.force:
            p.unlink(missing_ok=True)
            cleared += 1
        elif p.suffix == ".json":
            try:
                meta = json.loads(p.read_text(encoding="utf-8"))
                pid = meta.get("pid")
                if pid and not is_pid_alive(pid):
                    p.unlink(missing_ok=True)
                    lock_file = LOCK_DIR / f"{meta.get('resource')}.lock"
                    lock_file.unlink(missing_ok=True)
                    cleared += 1
                    print(f"Cleared stale lock for '{meta.get('resource')}' (dead PID {pid}).")
            except Exception:
                pass
    if args.force:
        print(f"Force-cleared {cleared} lock artifact(s).")
    elif cleared == 0:
        print("No stale locks detected. Use --force to clear all active locks.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """
    Safely build a project with concurrency locks.
    Acquires 'render' lock to ensure exclusive access to Chromium & Metal GPU.
    Runs full studio pipeline or legacy build with zero quality compromises.
    """
    slug = args.slug
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import studio
        pdir = studio.project_dir(slug)
    except SystemExit:
        print(f"Error: Project '{slug}' not found in projects/.", file=sys.stderr)
        return 1

    # First, validate locally (non-blocking)
    print(f"[SessionGuard] Pre-build validation for '{slug}'...")
    val_cmd = [sys.executable, "scripts/studio.py", "validate", slug]
    v_res = subprocess.run(val_cmd, cwd=REPO_ROOT)
    if v_res.returncode != 0:
        print(f"[SessionGuard] ❌ Validation failed for '{slug}'. Aborting build.", file=sys.stderr)
        return v_res.returncode

    # Build command
    build_cmd = [sys.executable, "scripts/studio.py", "build", slug]
    if args.quality:
        build_cmd += ["--quality", args.quality]
    if args.formats:
        build_cmd += ["--formats", args.formats]
    if args.dry_run:
        build_cmd += ["--dry-run"]
        # Dry run doesn't touch the GPU, run immediately
        return subprocess.run(build_cmd, cwd=REPO_ROOT).returncode

    # Acquire exclusive render lock across sessions
    with acquire_lock(RESOURCE_RENDER, slug=slug):
        res = subprocess.run(build_cmd, cwd=REPO_ROOT)
        return res.returncode


def cmd_audio(args: argparse.Namespace) -> int:
    """
    Safely synthesize speech with concurrency lock.
    Acquires 'tts' lock to avoid PyTorch memory pressure on Apple Silicon.
    """
    slug = args.slug
    cmd = [sys.executable, "scripts/build-audio.py", slug]
    if args.speed:
        cmd += ["--speed", str(args.speed)]
    if args.voice:
        cmd += ["--voice", args.voice]

    with acquire_lock(RESOURCE_TTS, slug=slug):
        res = subprocess.run(cmd, cwd=REPO_ROOT)
        return res.returncode


def cmd_review(args: argparse.Namespace) -> int:
    """
    Safely run Playwright preview frame-review with concurrency lock.
    Shares the 'render' lock with HyperFrames to prevent Chromium memory collisions.
    """
    slug = args.slug
    cmd = [sys.executable, "scripts/frame-review.py", slug]
    if args.fonts:
        cmd += ["--fonts", args.fonts]
    if args.strict:
        cmd += ["--strict"]
    if args.json:
        cmd += ["--json"]

    with acquire_lock(RESOURCE_RENDER, slug=slug):
        res = subprocess.run(cmd, cwd=REPO_ROOT)
        return res.returncode


def cmd_govern(args: argparse.Namespace) -> int:
    """Run project-scoped workspace governance audit."""
    slug = args.slug
    cmd = [sys.executable, "scripts/workspace-governance.py", "--project", slug]
    if args.strict:
        cmd += ["--strict"]
    if args.json:
        cmd += ["--json"]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


# --------------------------------------------------------------------------- Git Worktree Session Management

def cmd_session_start(args: argparse.Namespace) -> int:
    """
    Spawn an isolated Git worktree for a parallel project session.
    Protects the main working branch from concurrent file modifications.
    """
    slug = args.slug
    branch = args.branch or f"session/{slug}"
    wt_dir = Path(args.dir).resolve() if args.dir else (WORKTREES_DIR / slug)

    if wt_dir.exists():
        print(f"Error: Session directory '{wt_dir}' already exists.", file=sys.stderr)
        return 1

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)

    # Check if branch already exists
    branch_check = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=REPO_ROOT
    )
    branch_exists = (branch_check.returncode == 0)

    print("=" * 65)
    print(f"🚀 INITIALIZING ISOLATED WORKTREE SESSION: {slug}")
    print("=" * 65)
    print(f"  • Session Path: {wt_dir}")
    print(f"  • Git Branch:   {branch} ({'existing' if branch_exists else 'new branch'})")

    add_cmd = ["git", "worktree", "add"]
    if not branch_exists:
        add_cmd += ["-b", branch]
    add_cmd += [str(wt_dir)]
    if branch_exists:
        add_cmd += [branch]

    res = subprocess.run(add_cmd, cwd=REPO_ROOT)
    if res.returncode != 0:
        print("[SessionGuard] ❌ Failed to create git worktree.", file=sys.stderr)
        return res.returncode

    # Symlink virtualenv if present in root repo
    root_venv = REPO_ROOT / ".venv"
    wt_venv = wt_dir / ".venv"
    if root_venv.exists() and not wt_venv.exists():
        try:
            wt_venv.symlink_to(root_venv, target_is_directory=True)
            print("  • Virtualenv:   Linked root .venv into session worktree.")
        except Exception as e:
            print(f"  • Virtualenv:   Note: could not symlink .venv ({e})")

    # Optionally scaffold project if template provided
    if args.template:
        print(f"  • Template:     Scaffolding from '{args.template}'...")
        scaff_cmd = [sys.executable, "scripts/studio.py", "new", slug, "--template", args.template]
        if args.style:
            scaff_cmd += ["--style", args.style]
        if args.formats:
            scaff_cmd += ["--formats", args.formats]
        s_res = subprocess.run(scaff_cmd, cwd=wt_dir)
        if s_res.returncode != 0:
            print(f"[SessionGuard] Warning: Project scaffolding exited with code {s_res.returncode}.")

    print("-" * 65)
    print("✅ Parallel session workspace is ready!")
    print(f"To work in this isolated session:")
    print(f"    cd \"{wt_dir}\"")
    print(f"When finished, merge and remove worktree:")
    print(f"    python scripts/session-guard.py session-end {slug} [--merge]")
    print("=" * 65)
    return 0


def cmd_session_list(args: argparse.Namespace) -> int:
    """List all active git worktree sessions."""
    print("=" * 65)
    print("ACTIVE PARALLEL SESSIONS (GIT WORKTREES)")
    print("=" * 65)
    res = subprocess.run(["git", "worktree", "list"], cwd=REPO_ROOT)
    return res.returncode


def cmd_session_end(args: argparse.Namespace) -> int:
    """
    Safely tear down a parallel session worktree, optionally merging back to main.
    """
    slug = args.slug
    branch = args.branch or f"session/{slug}"
    wt_dir = Path(args.dir).resolve() if args.dir else (WORKTREES_DIR / slug)

    if not wt_dir.exists():
        # Check if worktree list knows about it
        res = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True, cwd=REPO_ROOT)
        matching = [line for line in res.stdout.splitlines() if slug in line]
        if not matching:
            print(f"Error: Worktree for '{slug}' not found at {wt_dir}.", file=sys.stderr)
            return 1

    # Remove symlinked .venv if present
    wt_venv = wt_dir / ".venv"
    if wt_venv.is_symlink() or wt_venv.exists():
        try:
            wt_venv.unlink()
        except Exception:
            pass

    # Check for uncommitted changes in worktree
    status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=wt_dir)
    if status_res.stdout.strip() and not args.force:
        print(f"[SessionGuard] ❌ Worktree at {wt_dir} has uncommitted changes:", file=sys.stderr)
        print(status_res.stdout, file=sys.stderr)
        print("Commit your changes or pass --force to discard them.", file=sys.stderr)
        return 1

    # Remove worktree
    rm_cmd = ["git", "worktree", "remove", str(wt_dir)]
    if args.force:
        rm_cmd.append("--force")
    rm_res = subprocess.run(rm_cmd, cwd=REPO_ROOT)
    if rm_res.returncode != 0:
        return rm_res.returncode

    print(f"[SessionGuard] 🧹 Removed worktree for '{slug}'.")

    # Merge branch if requested
    if args.merge:
        print(f"[SessionGuard] 🔀 Merging '{branch}' into current branch...")
        m_res = subprocess.run(["git", "merge", branch], cwd=REPO_ROOT)
        if m_res.returncode != 0:
            print(f"[SessionGuard] ❌ Merge conflict or error merging '{branch}'. Resolve manually.", file=sys.stderr)
            return m_res.returncode
        print(f"[SessionGuard] ✅ Successfully merged '{branch}'.")

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Arbitrary command guarded by a designated resource lock."""
    resource = args.resource
    cmd = args.command
    slug = args.slug or "generic"
    if not cmd:
        print("Error: No command provided to run.", file=sys.stderr)
        return 1

    with acquire_lock(resource, slug=slug):
        return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Session Guard: Concurrency Coordinator for Motion Lab projects on Apple Silicon."
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_stat = sub.add_parser("status", help="Show active resource locks")
    p_stat.set_defaults(func=cmd_status)

    # unlock
    p_unl = sub.add_parser("unlock", help="Release stale or all locks")
    p_unl.add_argument("--force", action="store_true", help="Force clear all locks regardless of holder")
    p_unl.set_defaults(func=cmd_unlock)

    # build
    p_bld = sub.add_parser("build", help="Safely build a project with exclusive render lock")
    p_bld.add_argument("slug", help="Project slug under projects/")
    p_bld.add_argument("--quality", choices=["looks", "delivery"], help="Render quality preset")
    p_bld.add_argument("--formats", help="Comma-separated format filter (e.g. landscape,portrait)")
    p_bld.add_argument("--dry-run", action="store_true", help="Print plan without running or locking")
    p_bld.set_defaults(func=cmd_build)

    # audio
    p_aud = sub.add_parser("audio", help="Safely synthesize audio with exclusive tts lock")
    p_aud.add_argument("slug", help="Project slug under projects/")
    p_aud.add_argument("--speed", type=float, help="Playback speed multiplier (e.g. 1.15)")
    p_aud.add_argument("--voice", help="Kokoro voice persona (e.g. am_adam, af_bella)")
    p_aud.set_defaults(func=cmd_audio)

    # review
    p_rev = sub.add_parser("review", help="Safely run frame-review with exclusive render lock")
    p_rev.add_argument("slug", help="Project slug under projects/")
    p_rev.add_argument("--fonts", choices=["system", "google"], default="google", help="Font resolution mode")
    p_rev.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    p_rev.add_argument("--json", action="store_true", help="Emit JSON report")
    p_rev.set_defaults(func=cmd_review)

    # govern
    p_gov = sub.add_parser("govern", help="Run workspace governance scoped to this project")
    p_gov.add_argument("slug", help="Project slug under projects/")
    p_gov.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    p_gov.add_argument("--json", action="store_true", help="Emit JSON report")
    p_gov.set_defaults(func=cmd_govern)

    # session-start
    p_sstart = sub.add_parser("session-start", help="Spawn an isolated Git worktree for a parallel project session")
    p_sstart.add_argument("slug", help="Project slug for the session")
    p_sstart.add_argument("--branch", help="Git branch name (default: session/<slug>)")
    p_sstart.add_argument("--dir", help="Custom worktree directory path (default: .worktrees/<slug>)")
    p_sstart.add_argument("--template", help="Automatically scaffold from project template (e.g. illustrated-explainer)")
    p_sstart.add_argument("--style", help="Style system to use with template")
    p_sstart.add_argument("--formats", help="Formats to configure (e.g. landscape,portrait,square)")
    p_sstart.set_defaults(func=cmd_session_start)

    # session-list
    p_slist = sub.add_parser("session-list", help="List active parallel session worktrees")
    p_slist.set_defaults(func=cmd_session_list)

    # session-end
    p_send = sub.add_parser("session-end", help="Remove an isolated Git worktree session")
    p_send.add_argument("slug", help="Project slug for the session")
    p_send.add_argument("--branch", help="Git branch name (default: session/<slug>)")
    p_send.add_argument("--dir", help="Worktree directory path (default: .worktrees/<slug>)")
    p_send.add_argument("--merge", action="store_true", help="Merge session branch into current branch before removal")
    p_send.add_argument("--force", action="store_true", help="Force remove worktree even with uncommitted changes")
    p_send.set_defaults(func=cmd_session_end)

    # run (generic)
    p_run = sub.add_parser("run", help="Run arbitrary command guarded by a lock")
    p_run.add_argument("resource", choices=[RESOURCE_RENDER, RESOURCE_TTS, RESOURCE_ANALYSIS], help="Resource name to guard")
    p_run.add_argument("--slug", help="Project slug for tracking")
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="Command and arguments to execute")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

