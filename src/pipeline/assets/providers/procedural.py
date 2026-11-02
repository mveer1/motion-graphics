"""Procedural image provider: deterministic textures and layers from Pillow + NumPy.

No network, no credentials, no model. Same request (including seed) gives byte-identical output, which is
what lets the asset library treat these as reusable. This is the offline stand-in for generated plates:
paper, halftone, haze and silhouette layers are things code can make well; it does NOT pretend to be a
photographic image generator.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .. import base

RECIPES = ["paper-grain", "halftone", "gradient-field", "torn-paper", "depth-haze", "silhouette-layer", "caustics"]


def _rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _noise(rng: np.random.Generator, w: int, h: int, cells: int) -> np.ndarray:
    """Smooth value noise in 0..1 (one octave): a small random grid upscaled bicubically."""
    g = rng.random((max(2, cells * h // max(w, h)) + 2, cells + 2)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


def _fbm(rng: np.random.Generator, w: int, h: int, base_cells: int = 4, octaves: int = 4) -> np.ndarray:
    out, amp, tot = np.zeros((h, w), np.float32), 1.0, 0.0
    for o in range(octaves):
        out += amp * _noise(rng, w, h, base_cells * 2 ** o)
        tot += amp
        amp *= 0.5
    return out / tot


def render(recipe: str, w: int, h: int, seed: int, colors: List[str], opts: Dict[str, Any]) -> Image.Image:
    rng = np.random.default_rng(seed)
    cols = [_rgb(c) for c in (colors or ["#f2e8d5", "#2a2522", "#b5401f"])]
    if recipe == "paper-grain":
        base_c = np.array(cols[0], np.float32)
        grain = _fbm(rng, w, h, 40, 3) - 0.5
        fib = _noise(rng, w, h, 300) - 0.5
        a = base_c[None, None, :] * (1 + 0.10 * grain[..., None] + 0.05 * fib[..., None])
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
    if recipe == "halftone":
        step = int(opts.get("cell", 14))
        field = _fbm(rng, w, h, 3, 3)
        bg, ink = Image.new("RGB", (w, h), cols[0]), cols[1] if len(cols) > 1 else (30, 30, 30)
        d = ImageDraw.Draw(bg)
        for y in range(step // 2, h, step):
            for x in range(step // 2, w, step):
                r = step * 0.5 * float(field[min(y, h - 1), min(x, w - 1)]) ** 1.3
                if r > 0.6:
                    d.ellipse((x - r, y - r, x + r, y + r), fill=ink)
        return bg
    if recipe == "gradient-field":
        n1, n2 = _fbm(rng, w, h, 2, 3), _fbm(rng, w, h, 3, 3)
        k = len(cols)
        t = np.clip(n1 * 0.7 + n2 * 0.3, 0, 0.9999) * (k - 1)
        i, f = t.astype(int), (t - t.astype(int))[..., None]
        arr = np.array(cols, np.float32)
        a = arr[i] * (1 - f) + arr[np.minimum(i + 1, k - 1)] * f
        return Image.fromarray(a.astype(np.uint8), "RGB")
    if recipe == "depth-haze":  # vertical gradient + haze bands + drifting particles (plankton / dust)
        top, bot = np.array(cols[0], np.float32), np.array(cols[1] if len(cols) > 1 else (5, 10, 18), np.float32)
        y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        a = np.repeat(top * (1 - y) + bot * y, w, axis=1)
        haze = (_fbm(rng, w, h, 3, 4) - 0.35).clip(0, 1)[..., None]
        glow = np.array(cols[2] if len(cols) > 2 else (120, 170, 190), np.float32)
        a = a * (1 - 0.35 * haze) + glow * 0.18 * haze * (1 - y)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
        d = ImageDraw.Draw(im, "RGBA")
        for _ in range(int(opts.get("particles", 160))):
            x, yy, r = rng.random() * w, rng.random() * h, 0.6 + rng.random() * 2.2
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=(*glow.astype(int).tolist(), int(40 + rng.random() * 90)))
        return im
    if recipe == "caustics":  # soft light network used on shallow-water layers
        a = np.zeros((h, w), np.float32)
        for k in range(3):
            n = _fbm(rng, w, h, 5 + 3 * k, 2)
            a += 1.0 - np.abs(np.sin(n * 18 + k))
        a = (a / 3) ** 6
        tint = np.array(cols[0], np.float32)
        im = (a[..., None] * tint[None, None, :] * 1.6).clip(0, 255).astype(np.uint8)
        return Image.fromarray(im, "RGB")
    if recipe == "torn-paper":  # RGBA cut-out sheet with a ragged edge and a soft hard shadow baked beside it
        pad = 40
        W, H = w, h
        base_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        edge_amp = float(opts.get("roughness", 14))
        pts: List[Tuple[float, float]] = []
        def side(p0, p1, n):
            for i in range(n):
                t = i / n
                x = p0[0] + (p1[0] - p0[0]) * t + (rng.random() - .5) * edge_amp
                y = p0[1] + (p1[1] - p0[1]) * t + (rng.random() - .5) * edge_amp
                pts.append((x, y))
        c = [(pad, pad), (W - pad, pad), (W - pad, H - pad), (pad, H - pad)]
        for i in range(4):
            side(c[i], c[(i + 1) % 4], 46)
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).polygon([(x + 10, y + 12) for x, y in pts], fill=(0, 0, 0, 70))
        base_img.alpha_composite(shadow)
        sheet = Image.new("RGBA", (W, H), (*cols[0], 255))
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        grain = (_fbm(rng, W, H, 60, 2) - .5) * 40
        arr = np.asarray(sheet).astype(np.float32)
        arr[..., :3] += grain[..., None]
        sheet = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        sheet.putalpha(mask)
        base_img.alpha_composite(sheet)
        return base_img
    if recipe == "silhouette-layer":  # RGBA ridge with a transparent sky, for parallax stacks
        base_y = float(opts.get("horizon", 0.6)) * h
        amp = float(opts.get("amplitude", 0.08)) * h
        n = _fbm(rng, w, 1, 6, 4)[0]
        ys = base_y + (n - 0.5) * 2 * amp
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).polygon([(0, h)] + [(x, float(ys[x])) for x in range(w)] + [(w, h)], fill=(*cols[0], 255))
        return im.filter(ImageFilter.GaussianBlur(float(opts.get("blur", 0))))
    raise base.ProviderError("invalid-request", f"unknown recipe {recipe!r}; available: {', '.join(RECIPES)}")


class ProceduralProvider(base.Provider):
    name = "procedural"

    def capabilities(self) -> Dict[str, Any]:
        return {"provider": "procedural", "summary": "Deterministic textures and layers drawn by code (Pillow/NumPy). Offline, no credentials.",
                "tasks": {"procedural-image": {"input_formats": [], "requires": ["recipe"], "models": RECIPES, "resolutions": ["any up to 4096 px a side"]}},
                "auth": {"method": "none"}, "local": True,
                "verification": {"level": "local", "checked_on": "2026-11-02", "sources": ["tests/test-creative-intelligence.py"]}}

    def available(self) -> Optional[str]:
        return None

    def submit(self, task: str, request: Dict[str, Any]) -> str:
        if task != "procedural-image":
            raise base.ProviderError("unsupported", f"procedural provider does not do {task}")
        recipe = request.get("recipe") or request.get("_model")
        w, h = int(request.get("width", 1280)), int(request.get("height", 720))
        if not (16 <= w <= 4096 and 16 <= h <= 4096):
            raise base.ProviderError("invalid-request", "width/height must be 16..4096")
        im = render(str(recipe), w, h, int(request.get("seed", 1)), request.get("colors") or [], request.get("options") or {})
        out = Path(request.get("_out_dir") or "/tmp") / f"{request['_job']}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, optimize=False)
        return str(out)

    def status(self, remote_id: str) -> base.RemoteStatus:
        return base.RemoteStatus(base.SUCCEEDED, result_paths=[remote_id])

    def fetch(self, status: base.RemoteStatus, dest_dir: str, stem: str) -> List[str]:
        return list(status.result_paths)
