#!/usr/bin/env python3
"""
scripts/session-guard.py
Concurrency Coordinator & Lock Engine for Motion Lab multi-session workflows.

Any number of sessions (git worktrees) can author in parallel. The 8 GB Apple Silicon host runs ONE
heavy job at a time: Chromium render / Playwright review ("render"), Kokoro TTS ("tts") and reference
analysis ("analysis") all share one host lock ("heavy"), so a Kokoro job and a render can never overlap.
Waiting sessions queue first-come-first-served. Killing the holder (SIGTERM/SIGHUP/SIGINT) also kills its
whole process tree before the lock is released, so no orphaned Chrome or ffmpeg keeps running unguarded.

Usage:
  python scripts/session-guard.py build <slug> [--quality Q] [--formats F] [--dry-run]
  python scripts/session-guard.py audio <slug> [--speed S] [--voice V]
  python scripts/session-guard.py review <slug> [--fonts google]
  python scripts/session-guard.py govern <slug> [--strict]
  python scripts/session-guard.py run [--slug S] [--cwd DIR] <resource> -- <command...>
  python scripts/session-guard.py status
  python scripts/session-guard.py unlock [--force]
  python scripts/session-guard.py session-start <slug> [--template T]
  python scripts/session-guard.py session-list
  python scripts/session-guard.py session-end <slug> [--merge] [--force]

Environment:
  MOTION_LAB_LOCK_DIR       override the lock directory (tests, unusual layouts)
  MOTION_LAB_LOCK_TIMEOUT   seconds a job waits in the queue before giving up (default 7200)
  MOTION_LAB_LOCK_POLL      seconds between queue checks (default 1.0)
"""

import argparse
import collections
import contextlib
import fcntl
import filecmp
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


def _env_number(name: str, default, cast):
    try:
        return cast(os.environ[name])
    except (KeyError, ValueError):
        return default


def resolve_main_root() -> Path:
    """The main checkout, shared by every git worktree.

    A worktree carries its own copy of this script, so deriving shared state from __file__ gave each
    parallel session a private .locks/ and the render lock never excluded anything. Resolve through
    the git common dir instead.
    """
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            common = Path(res.stdout.strip())
            common = (common if common.is_absolute() else REPO_ROOT / common).resolve()
            if common.name == ".git":
                return common.parent
    except (OSError, subprocess.SubprocessError):
        pass
    return REPO_ROOT


def resolve_lock_dir() -> Path:
    """One lock directory per machine checkout. MOTION_LAB_LOCK_DIR overrides."""
    override = os.environ.get("MOTION_LAB_LOCK_DIR")
    return Path(override) if override else resolve_main_root() / ".locks"


MAIN_ROOT = resolve_main_root()
LOCK_DIR = resolve_lock_dir()
QUEUE_DIR = LOCK_DIR / "queue"
HELD_ENV = "MOTION_LAB_LOCKS_HELD"  # comma list of lock names/resources held by an ancestor process
PROJECTS_DIR = REPO_ROOT / "projects"
WORKTREES_DIR = MAIN_ROOT / ".worktrees"

LOCK_TIMEOUT_SEC = _env_number("MOTION_LAB_LOCK_TIMEOUT", 7200, int)
LOCK_POLL_SEC = _env_number("MOTION_LAB_LOCK_POLL", 1.0, float)
HEARTBEAT_SEC = 30

# Defined hardware-critical shared resources
RESOURCE_RENDER = "render"       # HyperFrames Headless Chromium + Metal GPU & Playwright
RESOURCE_TTS = "tts"             # Kokoro Neural Voice Synthesis (PyTorch Resident Memory)
RESOURCE_ANALYSIS = "analysis"   # Reference video corpus analysis
HEAVY_RESOURCES = (RESOURCE_RENDER, RESOURCE_TTS, RESOURCE_ANALYSIS)
HEAVY_LOCK = "heavy"             # the single host lock all heavy resources share (one job at a time)

# Rough working sets measured on the M2 (docs/architecture-audit.md): used only for the advisory line.
HEAVY_RESERVE_GB = 1.5

# Gitignored paths that are caches or environments, not session output (never copied back to main).
ARTIFACT_SKIP_PARTS = {".venv", "__pycache__", "node_modules", ".hyperframes", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
# Areas a session normally writes to; anything else it touches is shared and may conflict at merge.
SESSION_OWNED_PREFIXES = ("projects/", "series/", "out/")
TOOLING_PREFIXES = ("scripts/", "specs/", "src/", "catalogue/", "templates/", ".claude/", "tests/", "CLAUDE.md", "AGENTS.md")


def is_pid_alive(pid: int) -> bool:
    """Check if process with PID is currently running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True  # exists, owned by someone else
    except OSError:
        return False


def _git(*args: str, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd or REPO_ROOT, capture_output=True, text=True)


_session_slug_cache: Optional[str] = None


def session_slug() -> str:
    """Name of the session this process belongs to: the slug of a session/<slug> branch, else 'workspace'."""
    global _session_slug_cache
    if _session_slug_cache is None:
        branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        _session_slug_cache = branch[len("session/"):] if branch.startswith("session/") else "workspace"
    return _session_slug_cache


def fmt_age(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def memory_available_gb() -> Optional[float]:
    """Free + reclaimable memory in GB on macOS (vm_stat); None where it cannot be read."""
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
        page = int(re.search(r"page size of (\d+) bytes", out).group(1))
        pages = sum(int(m.group(1)) for key in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable")
                    for m in [re.search(rf"{key}:\s+(\d+)", out)] if m)
        return pages * page / 1024 ** 3
    except (OSError, subprocess.SubprocessError, AttributeError, ValueError):
        return None


def memory_line() -> Optional[str]:
    avail = memory_available_gb()
    if avail is None:
        return None
    note = "" if avail >= HEAVY_RESERVE_GB else f"  ⚠️ below the ~{HEAVY_RESERVE_GB} GB a Kokoro job needs: close other apps before a heavy job"
    return f"Memory available: ~{avail:.1f} GB (one Kokoro job ~1.4 GB, one render ~0.8 GB){note}"


# --------------------------------------------------------------------------- Process-tree teardown

def _process_table() -> Dict[int, Tuple[int, str]]:
    """pid -> (ppid, stat) for every process."""
    try:
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,stat="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    table = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), parts[2])
    return table


def live_descendants(root_pid: int) -> List[int]:
    """Non-zombie descendants of root_pid (Chrome detaches into its own process group but keeps its parent)."""
    table = _process_table()
    children: Dict[int, List[int]] = collections.defaultdict(list)
    for pid, (ppid, _) in table.items():
        children[ppid].append(pid)
    found, stack = [], [root_pid]
    while stack:
        for child in children.get(stack.pop(), []):
            found.append(child)
            stack.append(child)
    return [p for p in found if not table[p][1].startswith("Z")]


def terminate_descendants(grace_sec: float = 8.0) -> int:
    """SIGTERM every descendant of this process, SIGKILL the survivors after grace_sec. Returns the count."""
    victims = live_descendants(os.getpid())
    for pid in victims:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + grace_sec
    while victims and time.monotonic() < deadline:
        time.sleep(0.2)
        alive = set(live_descendants(os.getpid()))
        victims = [p for p in victims if p in alive]
    for pid in victims:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)
    return len(victims)


def _install_signal_handlers():
    """On SIGTERM/SIGHUP/SIGINT: kill our job tree, then unwind so the lock is released only after the job is dead.

    Without this, killing the guard (an agent tool timeout, a closed terminal) frees the flock while its
    Chromium or Kokoro child keeps running, and the next queued job starts on top of it. A signal that is
    deliberately ignored (nohup) stays ignored. Returns a function that restores the previous handlers.
    """
    if threading.current_thread() is not threading.main_thread():
        return lambda: None

    def handler(signum, _frame):
        terminate_descendants()
        if signum == signal.SIGINT:
            raise KeyboardInterrupt
        raise SystemExit(128 + signum)

    previous = {}
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        try:
            old = signal.getsignal(sig)
            if old in (signal.SIG_DFL, signal.default_int_handler):
                previous[sig] = signal.signal(sig, handler)
        except (ValueError, OSError):
            pass

    def restore():
        for sig, old in previous.items():
            with contextlib.suppress(ValueError, OSError):
                signal.signal(sig, old)
    return restore


# --------------------------------------------------------------------------- Lock engine

def lock_name_for(resource: str) -> str:
    return HEAVY_LOCK if resource in HEAVY_RESOURCES else resource


def _meta_path(lock_name: str) -> Path:
    return LOCK_DIR / f"{lock_name}.json"


def _read_meta(lock_name: str) -> Optional[dict]:
    try:
        return json.loads(_meta_path(lock_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_meta(lock_name: str, meta: dict) -> None:
    path = _meta_path(lock_name)
    tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    os.replace(tmp, path)  # atomic: `status` never reads half a file


def lock_is_held(lock_name: str) -> bool:
    """True while some live process holds the flock (the kernel drops it when the holder dies)."""
    path = LOCK_DIR / f"{lock_name}.lock"
    if not path.exists():
        return False
    fd = os.open(str(path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)


def _tickets(lock_name: str) -> List[Path]:
    return sorted(QUEUE_DIR.glob(f"*-{lock_name}.ticket")) if QUEUE_DIR.exists() else []


def _ticket_pid(ticket: Path) -> int:
    try:
        return int(ticket.name.split("-")[1])
    except (IndexError, ValueError):
        return 0


def _enqueue(lock_name: str, resource: str, slug: str) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    ticket = QUEUE_DIR / f"{time.time_ns():020d}-{os.getpid()}-{lock_name}.ticket"
    ticket.write_text(json.dumps({
        "pid": os.getpid(), "slug": slug, "resource": resource,
        "queued_at": time.strftime("%Y-%m-%d %H:%M:%S"), "timestamp": time.time(),
    }), encoding="utf-8")
    return ticket


def _queue_position(lock_name: str, ticket: Path) -> int:
    """Live tickets ahead of ours (0 = our turn). Tickets of dead processes are dropped as we pass them."""
    ahead = 0
    for other in _tickets(lock_name):
        if other == ticket:
            return ahead
        if not is_pid_alive(_ticket_pid(other)):
            other.unlink(missing_ok=True)
            continue
        ahead += 1
    return 0  # our ticket vanished (unlock): fall back to the flock alone


def _describe_holder(lock_name: str) -> str:
    meta = _read_meta(lock_name)
    if not meta:
        return "Unknown"
    return f"PID {meta.get('pid')} ({meta.get('resource', lock_name)} for project '{meta.get('slug', 'unknown')}', since {meta.get('acquired_at', '?')})"


def _await_turn(fd: int, lock_name: str, resource: str, ticket: Path, timeout_sec: float, poll_sec: float) -> None:
    start = time.monotonic()
    last_note = None
    while True:
        position = _queue_position(lock_name, ticket)
        if position == 0:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except OSError:
                pass
        now = time.monotonic()
        if now - start > timeout_sec:
            raise TimeoutError(
                f"[SessionGuard] Timed out after {int(timeout_sec)}s waiting for the host lock ({resource}); "
                f"held by {_describe_holder(lock_name)}. Raise MOTION_LAB_LOCK_TIMEOUT or run `session-guard.py status`."
            )
        if last_note is None or now - last_note >= HEARTBEAT_SEC:
            where = f"position {position + 1} in the queue" if position else "next in line"
            if last_note is None:
                print(f"[SessionGuard] ⏳ Host is busy with {_describe_holder(lock_name)}.")
                print(f"[SessionGuard] ⏳ '{resource}' is {where}; waiting politely (one heavy job at a time on 8 GB Apple Silicon)...")
            else:
                print(f"[SessionGuard] ⏳ Still waiting for '{resource}' ({int(now - start)}s elapsed, {where})...")
            last_note = now
        time.sleep(poll_sec)


def _take_legacy_lock(resource: str, timeout_sec: float, poll_sec: float) -> int:
    """Also hold the per-resource lock file that worktrees created before the single host lock still use.

    A worktree branches from the last commit and keeps its own copy of this script, so a session started
    before the host lock was unified locks only render.lock / tts.lock. Taking that file as well keeps a
    new-style job and an old-style job of the same resource mutually exclusive during the transition.
    Costs nothing once those sessions are gone; delete this function and its call with the last of them.
    """
    fd = os.open(str(LOCK_DIR / f"{resource}.lock"), os.O_CREAT | os.O_RDWR, 0o644)
    start, noted = time.monotonic(), False
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if time.monotonic() - start > timeout_sec:
                os.close(fd)
                raise TimeoutError(f"[SessionGuard] Timed out waiting for an older session's '{resource}' lock ({resource}.lock).")
            if not noted:
                print(f"[SessionGuard] ⏳ A session started before the unified host lock holds '{resource}.lock'; waiting for it...")
                noted = True
            time.sleep(poll_sec)


@contextlib.contextmanager
def acquire_lock(
    resource: str,
    slug: Optional[str] = None,
    timeout_sec: Optional[float] = None,
    poll_interval: Optional[float] = None,
) -> Generator[Path, None, None]:
    """
    Acquire the cross-process lock for a resource with fcntl.flock, waiting in a first-come-first-served queue.

    render, tts and analysis all map to the single "heavy" lock, so two heavy jobs never overlap. The lock
    is re-entrant for child processes through MOTION_LAB_LOCKS_HELD: `session-guard build` -> `studio.py
    build` -> `build-audio.py` is one job, not three. A holder that dies releases the flock automatically
    (the kernel drops it); its queue ticket is pruned by whoever is behind it.
    """
    lock_name = lock_name_for(resource)
    held = [r for r in os.environ.get(HELD_ENV, "").split(",") if r]
    if resource in held or lock_name in held:
        yield LOCK_DIR / f"{lock_name}.lock"
        return

    timeout_sec = LOCK_TIMEOUT_SEC if timeout_sec is None else timeout_sec
    poll_interval = LOCK_POLL_SEC if poll_interval is None else poll_interval
    slug = slug or session_slug()
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_DIR / f"{lock_name}.lock"

    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o644)
    ticket = _enqueue(lock_name, resource, slug)
    restore_signals = _install_signal_handlers()
    previous_held = os.environ.get(HELD_ENV)
    locked = False
    legacy_fd = None
    try:
        _await_turn(fd, lock_name, resource, ticket, timeout_sec, poll_interval)
        locked = True
        if lock_name != resource:
            legacy_fd = _take_legacy_lock(resource, timeout_sec, poll_interval)
        ticket.unlink(missing_ok=True)
        _write_meta(lock_name, {
            "resource": resource,
            "pid": os.getpid(),
            "slug": slug,
            "acquired_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": time.time(),
        })
        os.environ[HELD_ENV] = ",".join(dict.fromkeys(held + [resource, lock_name]))
        print(f"[SessionGuard] 🔒 Lock '{resource}' acquired for project '{slug}' (PID {os.getpid()}).")
        yield lock_file
    finally:
        ticket.unlink(missing_ok=True)
        if locked:
            if previous_held is None:
                os.environ.pop(HELD_ENV, None)
            else:
                os.environ[HELD_ENV] = previous_held
            _meta_path(lock_name).unlink(missing_ok=True)  # before unlocking, so a successor's metadata is never removed
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            print(f"[SessionGuard] 🔓 Lock '{resource}' released.")
        restore_signals()
        if legacy_fd is not None:
            os.close(legacy_fd)  # drops the legacy flock
        os.close(fd)


# --------------------------------------------------------------------------- Subcommands

def _queue_rows() -> List[dict]:
    rows = []
    for ticket in _tickets(HEAVY_LOCK):
        pid = _ticket_pid(ticket)
        try:
            data = json.loads(ticket.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        rows.append({"pid": pid, "alive": is_pid_alive(pid), **data})
    return rows


def cmd_status(args: argparse.Namespace) -> int:
    """Who holds the host, who is waiting, and how much memory is left."""
    print("=" * 65)
    print("SESSION GUARD CONCURRENCY STATUS")
    print("=" * 65)
    held = lock_is_held(HEAVY_LOCK)
    meta = _read_meta(HEAVY_LOCK)
    print(f"Heavy host (render, tts, analysis share it: ONE job at a time): {'BUSY' if held else 'IDLE'}")
    if held and meta:
        print(f"  • Running : {meta.get('resource')} for project '{meta.get('slug')}' (PID {meta.get('pid')}), "
              f"since {meta.get('acquired_at')} ({fmt_age(time.time() - meta.get('timestamp', time.time()))})")
    elif meta:
        print(f"  • Stale metadata from dead PID {meta.get('pid')} ('{meta.get('slug')}'); `unlock` clears it, the next job overwrites it.")
    waiting = [r for r in _queue_rows() if r["alive"]]
    if waiting:
        print("  • Queue   :")
        for i, row in enumerate(waiting, 1):
            print(f"      {i}. {row.get('resource')} for '{row.get('slug')}' (PID {row['pid']}), "
                  f"waiting {fmt_age(time.time() - row.get('timestamp', time.time()))}")
    elif held:
        print("  • Queue   : empty")
    mem = memory_line()
    if mem:
        print(mem)
    sessions = max(0, len(_worktree_entries()) - 1)
    print(f"Sessions  : {sessions} worktree session(s); `session-guard.py session-list` for details.")
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    """Clear stale queue tickets and metadata. With --force, also stop a live holder."""
    cleared = 0
    for row_ticket in _tickets(HEAVY_LOCK):
        if not is_pid_alive(_ticket_pid(row_ticket)):
            row_ticket.unlink(missing_ok=True)
            cleared += 1
    held = lock_is_held(HEAVY_LOCK)
    meta = _read_meta(HEAVY_LOCK)
    if meta and not held:
        _meta_path(HEAVY_LOCK).unlink(missing_ok=True)
        cleared += 1
        print(f"Cleared stale lock metadata for '{meta.get('resource')}' (dead PID {meta.get('pid')}).")
    for resource in HEAVY_RESOURCES:  # per-resource files written by older versions of this script
        legacy = LOCK_DIR / f"{resource}.json"
        try:
            pid = json.loads(legacy.read_text(encoding="utf-8")).get("pid")
        except (OSError, ValueError):
            continue
        if not (pid and is_pid_alive(pid)):
            legacy.unlink(missing_ok=True)
            cleared += 1
    if held and args.force and meta and meta.get("pid"):
        pid = int(meta["pid"])
        print(f"Stopping live holder PID {pid} ({meta.get('resource')} for '{meta.get('slug')}'): SIGTERM, it tears down its job tree...")
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 30
        while lock_is_held(HEAVY_LOCK) and time.monotonic() < deadline:
            time.sleep(0.5)
        if lock_is_held(HEAVY_LOCK):
            print("Holder ignored SIGTERM; sending SIGKILL. Check `ps` for orphaned Chrome/ffmpeg.")
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)
        cleared += 1
    elif held:
        print(f"Lock is held by a live process (PID {meta.get('pid') if meta else '?'}); not touching it. Use --force to stop it.")
    print(f"Cleared {cleared} stale lock artifact(s)." if cleared else "No stale locks detected.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """
    Safely build a project with concurrency locks.
    Acquires the host lock to ensure exclusive access to Chromium & Metal GPU.
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

    # Acquire exclusive host lock across sessions
    with acquire_lock(RESOURCE_RENDER, slug=slug):
        res = subprocess.run(build_cmd, cwd=REPO_ROOT)
        return res.returncode


def cmd_audio(args: argparse.Namespace) -> int:
    """
    Safely synthesize speech with concurrency lock.
    Shares the host lock with renders so Kokoro's PyTorch memory never stacks on a Chromium render.
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
    Shares the host lock with HyperFrames to prevent Chromium memory collisions.
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


def cmd_run(args: argparse.Namespace) -> int:
    """Arbitrary command guarded by a resource lock (cwd defaults to the repo root)."""
    cmd = list(args.command)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("Error: No command provided to run.", file=sys.stderr)
        return 1
    with acquire_lock(args.resource, slug=args.slug):
        try:
            return subprocess.run(cmd, cwd=args.cwd or REPO_ROOT).returncode
        except FileNotFoundError as exc:
            print(f"[SessionGuard] ❌ Cannot run {cmd[0]!r}: {exc}", file=sys.stderr)
            return 127


# --------------------------------------------------------------------------- Git Worktree Session Management

SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _worktree_entries() -> List[dict]:
    """[{path, head, branch}] from `git worktree list --porcelain`; the first entry is the main checkout."""
    res = _git("worktree", "list", "--porcelain", cwd=MAIN_ROOT)
    entries, cur = [], {}
    for line in res.stdout.splitlines() + [""]:
        if not line.strip():
            if cur:
                entries.append(cur)
            cur = {}
            continue
        key, _, value = line.partition(" ")
        cur[key] = value
    return [{"path": Path(e["worktree"]), "head": e.get("HEAD", ""), "branch": e.get("branch", "").replace("refs/heads/", "")}
            for e in entries if "worktree" in e]


def ignored_artifacts(wt: Path) -> List[str]:
    """Gitignored files in a worktree that are session output (renders, audio, out/*.mp4, logs), not caches."""
    res = _git("ls-files", "--others", "--ignored", "--exclude-standard", "-z", cwd=wt)
    keep = []
    for rel in (p for p in res.stdout.split("\0") if p):
        path = Path(rel)
        if ARTIFACT_SKIP_PARTS & set(path.parts) or path.name == ".DS_Store" or path.suffix == ".pyc":
            continue
        keep.append(rel)
    return keep


def rescue_artifacts(wt: Path, dest_root: Path, slug: str) -> Tuple[int, int, List[str]]:
    """Copy a worktree's gitignored output into the main checkout, at the same relative path.

    `git worktree remove` deletes these files and they exist nowhere else (a merge never carries them).
    Returns (copied, identical, diverged): a destination that already exists with different content is
    left alone and the session's copy is saved beside it as <name>.session-<slug>. JSONL logs are merged
    line by line. Raises OSError when a copy fails, so the caller can stop before deleting anything.
    """
    copied = identical = 0
    diverged: List[str] = []
    for rel in ignored_artifacts(wt):
        src, dst = wt / rel, dest_root / rel
        if src.is_symlink() or not src.is_file():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".jsonl":
            have = set(dst.read_text(encoding="utf-8").splitlines()) if dst.exists() else set()
            new = [ln for ln in src.read_text(encoding="utf-8").splitlines() if ln and ln not in have]
            if new:
                with dst.open("a", encoding="utf-8") as fh:
                    fh.write("\n".join(new) + "\n")
                copied += 1
            else:
                identical += 1
        elif not dst.exists():
            shutil.copy2(src, dst)
            copied += 1
        elif filecmp.cmp(src, dst, shallow=False):
            identical += 1
        else:
            shutil.copy2(src, dst.with_name(dst.name + f".session-{slug}"))
            diverged.append(rel)
    return copied, identical, diverged


def merge_conflicts(branch: str) -> Optional[List[str]]:
    """Files that would conflict merging branch into the main checkout's HEAD (no changes made). None if git cannot tell."""
    res = _git("merge-tree", "--write-tree", "--name-only", "--no-messages", "HEAD", branch, cwd=MAIN_ROOT)
    if res.returncode == 0:
        return []
    if res.returncode == 1:
        return [ln for ln in res.stdout.splitlines()[1:] if ln.strip()]
    return None


def _uncommitted_tooling() -> List[str]:
    """Uncommitted changes in the main checkout that a worktree branched from HEAD will not contain."""
    res = _git("status", "--porcelain", cwd=MAIN_ROOT)
    paths = [ln[3:].split(" -> ")[-1].strip('"') for ln in res.stdout.splitlines() if len(ln) > 3]
    return [p for p in paths if p.startswith(TOOLING_PREFIXES)]


def cmd_session_start(args: argparse.Namespace) -> int:
    """
    Spawn an isolated Git worktree for a parallel project session.
    Protects the main working branch from concurrent file modifications.
    """
    slug = args.slug
    if not SLUG_RE.fullmatch(slug):
        print(f"Error: '{slug}' is not a valid session slug (letters, digits, '.', '_', '-').", file=sys.stderr)
        return 1
    branch = args.branch or f"session/{slug}"
    wt_dir = Path(args.dir).resolve() if args.dir else (WORKTREES_DIR / slug)

    if wt_dir.exists():
        print(f"Error: Session directory '{wt_dir}' already exists.", file=sys.stderr)
        return 1

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)

    # Check if branch already exists
    branch_check = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=MAIN_ROOT
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

    res = subprocess.run(add_cmd, cwd=MAIN_ROOT)
    if res.returncode != 0:
        print("[SessionGuard] ❌ Failed to create git worktree.", file=sys.stderr)
        return res.returncode

    # Symlink virtualenv if present in root repo
    root_venv = MAIN_ROOT / ".venv"
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

    sessions = max(0, len(_worktree_entries()) - 1)
    print(f"  • Sessions:     {sessions} active (no limit; heavy jobs queue one at a time, authoring runs in parallel)")
    mem = memory_line()
    if mem:
        print(f"  • {mem}")
    missing = _uncommitted_tooling()
    if missing:
        shown = ", ".join(missing[:6]) + (f", +{len(missing) - 6} more" if len(missing) > 6 else "")
        print(f"  ⚠️  {len(missing)} uncommitted tooling change(s) in the main checkout are NOT in this worktree: {shown}")
        print("     A worktree branches from the last commit. Commit them first, or this session runs older scripts/specs.")

    print("-" * 65)
    print("✅ Parallel session workspace is ready!")
    print(f"To work in this isolated session:")
    print(f"    cd \"{wt_dir}\"")
    print(f"When finished, merge and remove worktree (renders/audio are copied back to main first):")
    print(f"    python scripts/session-guard.py session-end {slug} --merge")
    print("=" * 65)
    return 0


def cmd_session_list(args: argparse.Namespace) -> int:
    """Dashboard of every worktree session: progress, merge risk, unmerged output and host-lock activity."""
    print("=" * 65)
    print("ACTIVE PARALLEL SESSIONS (GIT WORKTREES)")
    print("=" * 65)
    entries = _worktree_entries()
    if not entries:
        print("No git worktrees found.")
        return 0
    main = entries[0]
    base = main["branch"] or "HEAD"
    print(f"main checkout: {main['path']}  [{base}]")
    held_meta = _read_meta(HEAVY_LOCK) if lock_is_held(HEAVY_LOCK) else None
    queue = [r for r in _queue_rows() if r["alive"]]
    for entry in entries[1:]:
        wt, branch = entry["path"], entry["branch"]
        slug = branch[len("session/"):] if branch.startswith("session/") else wt.name
        print(f"\n  {slug}   [{branch or 'detached'}]   {wt}")
        if not wt.exists():
            print("      ⚠️ directory is missing (run `git worktree prune`)")
            continue
        counts = _git("rev-list", "--left-right", "--count", f"{base}...{branch}", cwd=MAIN_ROOT).stdout.split()
        behind, ahead = (counts + ["?", "?"])[:2] if len(counts) == 2 else ("?", "?")
        dirty = len([ln for ln in _git("status", "--porcelain", cwd=wt).stdout.splitlines() if ln.strip()])
        artifacts = len(ignored_artifacts(wt))
        changed = _git("diff", "--name-only", f"{base}...{branch}", cwd=MAIN_ROOT).stdout.split()
        shared = [p for p in changed if not p.startswith(SESSION_OWNED_PREFIXES)]
        conflicts = merge_conflicts(branch) if branch else None
        conflict_txt = "unknown" if conflicts is None else ("none" if not conflicts else f"{len(conflicts)} file(s): " + ", ".join(conflicts[:3]))
        print(f"      {ahead} commit(s) ahead / {behind} behind {base} · {dirty} uncommitted · {artifacts} render/audio file(s) not in main")
        print(f"      merge conflicts with {base}: {conflict_txt}")
        if shared:
            print(f"      shared files touched ({len(shared)}): " + ", ".join(shared[:4]) + (", ..." if len(shared) > 4 else ""))
        if held_meta and held_meta.get("slug") == slug:
            print(f"      🔒 holding the host: {held_meta.get('resource')} (PID {held_meta.get('pid')})")
        for i, row in enumerate(queue, 1):
            if row.get("slug") == slug:
                print(f"      ⏳ queued #{i} for the host: {row.get('resource')}")
    if len(entries) == 1:
        print("\nNo session worktrees. Start one: python scripts/session-guard.py session-start <slug>")
    print()
    return 0


def cmd_session_end(args: argparse.Namespace) -> int:
    """
    Tear down a parallel session worktree, optionally merging back to main.

    Before the worktree is deleted, its gitignored output (renders, audio, out/*.mp4) is copied into the
    main checkout, because `git worktree remove` destroys it and a merge never carries it. With --merge
    the merge is checked for conflicts first, so a failing merge never leaves main half-merged.
    """
    slug = args.slug
    branch = args.branch or f"session/{slug}"
    wt_dir = Path(args.dir).resolve() if args.dir else (WORKTREES_DIR / slug)

    if not wt_dir.exists():
        # Check if worktree list knows about it (e.g. created with --dir elsewhere)
        matching = [e for e in _worktree_entries()[1:] if e["path"].name == slug or e["branch"] == branch]
        if not matching or not matching[0]["path"].exists():
            print(f"Error: Worktree for '{slug}' not found at {wt_dir}.", file=sys.stderr)
            return 1
        wt_dir = matching[0]["path"]

    # Check for uncommitted changes in worktree
    status_res = _git("status", "--porcelain", cwd=wt_dir)
    if status_res.stdout.strip() and not args.force:
        print(f"[SessionGuard] ❌ Worktree at {wt_dir} has uncommitted changes:", file=sys.stderr)
        print(status_res.stdout, file=sys.stderr)
        print("Commit your changes or pass --force to discard them.", file=sys.stderr)
        return 1

    if args.merge:
        conflicts = merge_conflicts(branch)
        if conflicts:
            print(f"[SessionGuard] ❌ Merging '{branch}' would conflict in {len(conflicts)} file(s); nothing was changed:", file=sys.stderr)
            for path in conflicts:
                print(f"    {path}", file=sys.stderr)
            print(f"Merge the main branch into the session first (cd \"{wt_dir}\" && git merge <main-branch>), resolve, commit, then retry.", file=sys.stderr)
            return 1
        shared = [p for p in _git("diff", "--name-only", f"HEAD...{branch}", cwd=MAIN_ROOT).stdout.split()
                  if not p.startswith(SESSION_OWNED_PREFIXES)]
        if shared:
            print(f"[SessionGuard] Note: '{branch}' also changes shared files: {', '.join(shared[:6])}" + (", ..." if len(shared) > 6 else ""))

    # Keep the session's renders, audio and delivered mp4s: the worktree removal below deletes them.
    try:
        copied, identical, diverged = rescue_artifacts(wt_dir, MAIN_ROOT, slug)
    except OSError as exc:
        print(f"[SessionGuard] ❌ Could not copy the session's renders/audio into the main checkout ({exc}). Worktree kept.", file=sys.stderr)
        return 1
    print(f"[SessionGuard] 📦 Session output copied to the main checkout: {copied} new, {identical} already identical.")
    for rel in diverged:
        print(f"[SessionGuard] ⚠️ {rel} differs from main's copy; kept both (the session's copy is {rel}.session-{slug}).")

    # Remove symlinked .venv if present
    wt_venv = wt_dir / ".venv"
    if wt_venv.is_symlink() or wt_venv.exists():
        try:
            wt_venv.unlink()
        except Exception:
            pass

    # Remove worktree
    rm_cmd = ["git", "worktree", "remove", str(wt_dir)]
    if args.force:
        rm_cmd.append("--force")
    rm_res = subprocess.run(rm_cmd, cwd=MAIN_ROOT)
    if rm_res.returncode != 0:
        return rm_res.returncode

    print(f"[SessionGuard] 🧹 Removed worktree for '{slug}'.")

    # Merge branch if requested
    if args.merge:
        print(f"[SessionGuard] 🔀 Merging '{branch}' into current branch...")
        m_res = subprocess.run(["git", "merge", "--no-edit", branch], cwd=MAIN_ROOT)
        if m_res.returncode != 0:
            print(f"[SessionGuard] ❌ Merge error merging '{branch}'. Resolve manually.", file=sys.stderr)
            return m_res.returncode
        print(f"[SessionGuard] ✅ Successfully merged '{branch}'.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Session Guard: Concurrency Coordinator for Motion Lab projects on Apple Silicon."
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_stat = sub.add_parser("status", help="Show the host lock holder, the queue and free memory")
    p_stat.set_defaults(func=cmd_status)

    # unlock
    p_unl = sub.add_parser("unlock", help="Clear stale lock state; --force also stops a live holder")
    p_unl.add_argument("--force", action="store_true", help="SIGTERM a live holder (it kills its own job tree) and release the lock")
    p_unl.set_defaults(func=cmd_unlock)

    # build
    p_bld = sub.add_parser("build", help="Safely build a project with exclusive render lock")
    p_bld.add_argument("slug", help="Project slug under projects/")
    p_bld.add_argument("--quality", choices=["looks", "delivery"], help="Render quality preset")
    p_bld.add_argument("--formats", help="Comma-separated format filter (e.g. landscape,portrait)")
    p_bld.add_argument("--dry-run", action="store_true", help="Print plan without running or locking")
    p_bld.set_defaults(func=cmd_build)

    # audio
    p_aud = sub.add_parser("audio", help="Safely synthesize audio under the host lock")
    p_aud.add_argument("slug", help="Project slug under projects/")
    p_aud.add_argument("--speed", type=float, help="Playback speed multiplier (e.g. 1.15)")
    p_aud.add_argument("--voice", help="Kokoro voice persona (e.g. am_adam, af_bella)")
    p_aud.set_defaults(func=cmd_audio)

    # review
    p_rev = sub.add_parser("review", help="Safely run frame-review under the host lock")
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
    p_slist = sub.add_parser("session-list", help="Dashboard of session worktrees: progress, merge risk, unmerged output, host-lock activity")
    p_slist.set_defaults(func=cmd_session_list)

    # session-end
    p_send = sub.add_parser("session-end", help="Remove an isolated Git worktree session (renders/audio are copied to main first)")
    p_send.add_argument("slug", help="Project slug for the session")
    p_send.add_argument("--branch", help="Git branch name (default: session/<slug>)")
    p_send.add_argument("--dir", help="Worktree directory path (default: .worktrees/<slug>)")
    p_send.add_argument("--merge", action="store_true", help="Merge session branch into current branch after removal (refuses if it would conflict)")
    p_send.add_argument("--force", action="store_true", help="Force remove worktree even with uncommitted changes")
    p_send.set_defaults(func=cmd_session_end)

    # run (generic)
    p_run = sub.add_parser("run", help="Run arbitrary command guarded by the host lock")
    p_run.add_argument("--slug", help="Project slug for tracking")
    p_run.add_argument("--cwd", help="Working directory for the command (default: repo root)")
    p_run.add_argument("resource", choices=list(HEAVY_RESOURCES), help="Resource name to guard")
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="Command and arguments to execute")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    try:
        return args.func(args)
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        return 75


if __name__ == "__main__":
    sys.exit(main())
