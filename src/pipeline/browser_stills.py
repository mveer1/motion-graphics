"""Shared Chrome discovery and checked capture for the Tibi still benches."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def chrome() -> str:
    override = os.environ.get("CHROME")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"CHROME does not name an existing executable: {path}")
        return str(path.resolve())
    name = "chrome-headless-shell.exe" if sys.platform == "win32" else "chrome-headless-shell"
    cache = Path.home() / ".cache" / "puppeteer" / "chrome-headless-shell"
    hits = sorted(p for p in cache.glob(f"*/*/{name}") if p.is_file())
    if not hits:
        raise FileNotFoundError(
            f"No headless Chrome found in {cache}. Set CHROME to an existing Chrome/Chromium executable."
        )
    return str(hits[-1])


def capture(
    executable: str,
    page: Path,
    query: str,
    out: Path,
    width: int,
    height: int,
    *,
    budget_ms: int,
) -> None:
    from PIL import Image

    out = out.resolve()
    out.unlink(missing_ok=True)
    url = f"{page.resolve().as_uri()}?w={width}&h={height}&{query}"
    with tempfile.TemporaryDirectory(prefix="tibi-chrome-") as profile:
        result = subprocess.run(
            [
                executable,
                "--headless",
                "--no-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile}",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
                f"--screenshot={out}",
                f"--window-size={width},{height}",
                f"--virtual-time-budget={budget_ms}",
                "--hide-scrollbars",
                "--dump-dom",
                url,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=90,
        )
    if result.returncode:
        raise RuntimeError(f"Chrome exited {result.returncode}: {result.stderr[-2000:]}")
    if "<title>ready</title>" not in result.stdout:
        raise RuntimeError(f"Tibi bench did not finish rendering: {url}\n{result.stderr[-2000:]}")
    if not out.is_file():
        raise RuntimeError(f"Chrome reported success but did not write a screenshot: {out}")
    with Image.open(out) as image:
        if image.size != (width, height):
            raise RuntimeError(f"Wrong screenshot size {image.size}; expected {(width, height)}")
        image.verify()
