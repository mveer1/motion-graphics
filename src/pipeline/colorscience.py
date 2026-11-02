"""Deterministic colour measurement for the Design DNA layer.

Perception drifts toward familiar palettes, so palettes are measured: stratified pixel
sampling with a fixed hash (no random state), farthest-point k-means, perceptual merging of
near-duplicate clusters, and coverage fractions. The approach follows design-dna's measure /
verify loop (MIT, zanwei/design-dna); this module is an independent Python implementation on
Pillow + NumPy with CIEDE2000 added next to CIE76.

Pure functions, no I/O except `load_rgb`. Same input always gives the same output.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

MAX_SAMPLED_PIXELS = 160_000


# ----------------------------------------------------------------------------- colour spaces
def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb: Sequence[float]) -> str:
    r, g, b = (int(round(min(255, max(0, v)))) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb: (...,3) in 0..255 -> CIE L*a*b* (D65)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e76(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    return np.linalg.norm(np.asarray(lab1) - np.asarray(lab2), axis=-1)


def delta_e2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """CIEDE2000 (Sharma, Wu, Dalal 2005)."""
    l1, a1, b1 = np.moveaxis(np.asarray(lab1, dtype=np.float64), -1, 0)
    l2, a2, b2 = np.moveaxis(np.asarray(lab2, dtype=np.float64), -1, 0)
    c1, c2 = np.hypot(a1, b1), np.hypot(a2, b2)
    cbar7 = ((c1 + c2) / 2.0) ** 7
    g = 0.5 * (1 - np.sqrt(cbar7 / (cbar7 + 25.0 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    dl, dc = l2 - l1, c2p - c1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where((c1p * c2p) == 0, 0.0, dh)
    dH = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh) / 2)
    lbar, cbar = (l1 + l2) / 2.0, (c1p + c2p) / 2.0
    hsum = h1p + h2p
    hbar = np.where(np.abs(h1p - h2p) <= 180, hsum / 2, np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2))
    hbar = np.where((c1p * c2p) == 0, hsum, hbar)
    t = (1 - 0.17 * np.cos(np.radians(hbar - 30)) + 0.24 * np.cos(np.radians(2 * hbar))
         + 0.32 * np.cos(np.radians(3 * hbar + 6)) - 0.20 * np.cos(np.radians(4 * hbar - 63)))
    dtheta = 30 * np.exp(-(((hbar - 275) / 25) ** 2))
    rc = 2 * np.sqrt(cbar ** 7 / (cbar ** 7 + 25.0 ** 7))
    sl = 1 + 0.015 * (lbar - 50) ** 2 / np.sqrt(20 + (lbar - 50) ** 2)
    sc, sh = 1 + 0.045 * cbar, 1 + 0.015 * cbar * t
    rt = -np.sin(np.radians(2 * dtheta)) * rc
    return np.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dH / sh) ** 2 + rt * (dc / sc) * (dH / sh))


def relative_luminance(rgb: Sequence[float]) -> float:
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def contrast_ratio(a: Sequence[float], b: Sequence[float]) -> float:
    """WCAG 2.x contrast ratio between two sRGB colours."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hsv_of(rgb: Sequence[float]) -> Tuple[float, float, float]:
    r, g, b = (float(v) / 255.0 for v in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    s = 0.0 if mx == 0 else d / mx
    l = (mx + mn) / 2
    if d == 0:
        h = 0.0
    elif mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)
    return h % 360, s, l


# ----------------------------------------------------------------------------- sampling
def _mix32(x: np.ndarray) -> np.ndarray:
    x = (x.astype(np.uint64) + np.uint64(0x9E3779B9)) & np.uint64(0xFFFFFFFF)
    x = ((x ^ (x >> np.uint64(16))) * np.uint64(0x21F0AAAD)) & np.uint64(0xFFFFFFFF)
    x = ((x ^ (x >> np.uint64(15))) * np.uint64(0x735A2D97)) & np.uint64(0xFFFFFFFF)
    return (x ^ (x >> np.uint64(15))) & np.uint64(0xFFFFFFFF)


def stratified_sample(pixels: np.ndarray, max_pixels: int = MAX_SAMPLED_PIXELS) -> np.ndarray:
    """pixels: (N,3). One pixel from each of `count` equal strata, offset by a fixed hash.

    A fixed stride would alias periodic detail (1 px stripes); the hashed offset breaks the
    phase while staying deterministic, and never interpolates, so no invented colours.
    """
    n = len(pixels)
    count = min(n, max_pixels)
    if count == n:
        return pixels
    idx = np.arange(count, dtype=np.uint64)
    start = (idx * np.uint64(n)) // np.uint64(count)
    end = ((idx + np.uint64(1)) * np.uint64(n)) // np.uint64(count)
    span = np.maximum(end - start, np.uint64(1))
    pick = start + (_mix32(idx) % span)
    return pixels[pick.astype(np.int64)]


def load_rgb(path: str, max_side: int = 1280):
    """Load an image as an (H,W,3) uint8 array, flattened on white, downscaled by area if large."""
    from PIL import Image

    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    if max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BOX)
    return np.asarray(im)


# ----------------------------------------------------------------------------- k-means
def _kmeans(px: np.ndarray, k: int, iters: int = 24):
    px = px.astype(np.float64)
    order = np.argsort(px[:, 0] * 3 + px[:, 1] * 6 + px[:, 2], kind="stable")
    centers = [px[order[0]].copy()]
    nearest = np.full(len(px), np.inf)
    while len(centers) < k:
        d = ((px - centers[-1]) ** 2).sum(axis=1)
        nearest = np.minimum(nearest, d)
        far = int(np.argmax(nearest))
        if nearest[far] <= 0:
            break
        centers.append(px[far].copy())
    c = np.array(centers)
    assign = np.zeros(len(px), dtype=np.int64)
    for _ in range(iters):
        d = ((px[:, None, :] - c[None, :, :]) ** 2).sum(axis=2)
        new = d.argmin(axis=1)
        if np.array_equal(new, assign) and _ > 0:
            break
        assign = new
        for j in range(len(c)):
            m = assign == j
            if m.any():
                c[j] = px[m].mean(axis=0)
    counts = np.bincount(assign, minlength=len(c)).astype(np.float64)
    out = [(c[j], counts[j] / len(px)) for j in range(len(c)) if counts[j] > 0]
    out.sort(key=lambda t: -t[1])
    return out


def _merge_similar(clusters, max_de: float):
    merged: List[List] = []
    for center, share in clusters:
        lab = srgb_to_lab(center)
        for m in merged:
            if float(delta_e76(srgb_to_lab(m[0]), lab)) <= max_de:
                tot = m[1] + share
                m[0] = (m[0] * m[1] + center * share) / tot
                m[1] = tot
                break
        else:
            merged.append([center.copy(), share])
    merged.sort(key=lambda m: -m[1])
    return merged


def _assign_roles(clusters) -> List[Dict]:
    ents = []
    for center, share in clusters:
        h, s, l = hsv_of(center)
        ents.append({"rgb": center, "share": share, "s": s, "l": l, "role": "other"})
    if not ents:
        return ents
    ents[0]["role"] = "background"
    bg_l, taken = ents[0]["l"], {0}
    best, text = 0.0, -1
    for i, e in enumerate(ents):
        if i in taken or e["share"] < 0.005:
            continue
        c = abs(e["l"] - bg_l)
        if c > best:
            best, text = c, i
    if text >= 0 and best > 0.25:
        ents[text]["role"] = "text"
        taken.add(text)
    bg_lab = srgb_to_lab(ents[0]["rgb"])
    scored = []
    for i, e in enumerate(ents):
        if i in taken or e["s"] < 0.25 or e["share"] < 0.002 or not 0.08 <= e["l"] <= 0.92:
            continue
        de = float(delta_e76(srgb_to_lab(e["rgb"]), bg_lab))
        scored.append((e["s"] * de * np.sqrt(min(e["share"], 0.02) / 0.02), i))
    if scored:
        ents[max(scored)[1]]["role"] = "accent"
    return ents


# ----------------------------------------------------------------------------- public API
def measure_palette(rgb_image: np.ndarray, k: int = 8, jpeg: bool = False) -> Dict:
    """Measure the dominant palette of an (H,W,3) uint8 image."""
    k = max(2, min(16, int(k)))
    flat = rgb_image.reshape(-1, 3)
    px = stratified_sample(flat)
    clusters = _merge_similar(_kmeans(px, k), 5.0 if jpeg else 2.5)
    ents = _assign_roles(clusters)
    return {
        "measured": True,
        "measurement": {
            "method": "deterministic_stratified+farthest_point_kmeans",
            "k": k,
            "max_pixels": MAX_SAMPLED_PIXELS,
            "sampled_pixels": int(len(px)),
            "merge_delta_e76": 5.0 if jpeg else 2.5,
            "source_size": [int(rgb_image.shape[1]), int(rgb_image.shape[0])],
        },
        "palette": [{"hex": rgb_to_hex(e["rgb"]), "coverage": round(float(e["share"]), 4), "role": e["role"]} for e in ents],
    }


def verify_against(reference_palette: List[Dict], implementation: Dict,
                   mean_max: float = 5.0, max_max: float = 20.0, drift_max: float = 0.35) -> Dict:
    """Compare a measured implementation palette to a reference palette (design-dna thresholds).

    Reports CIE76 (for comparability with design-dna) and CIEDE2000 (the better perceptual
    metric); pass/fail uses CIE76 so thresholds mean what design-dna says they mean.
    """
    sig = 0.005
    ref_lab = np.array([srgb_to_lab(np.array(hex_to_rgb(p["hex"]))) for p in reference_palette])
    imp = implementation["palette"]
    imp_lab = np.array([srgb_to_lab(np.array(hex_to_rgb(p["hex"]))) for p in imp])
    d76 = delta_e76(imp_lab[:, None, :], ref_lab[None, :, :])
    d00 = delta_e2000(imp_lab[:, None, :], ref_lab[None, :, :])
    near = d76.argmin(axis=1)
    mean_de = sum(float(d76[i, near[i]]) * imp[i]["coverage"] for i in range(len(imp)))
    w = sum(p["coverage"] for p in imp) or 1.0
    mean_de /= w
    mean_de00 = sum(float(d00[i, near[i]]) * imp[i]["coverage"] for i in range(len(imp))) / w
    impl_sig = [i for i, p in enumerate(imp) if p["coverage"] >= sig]
    max_impl = max([float(d76[i, near[i]]) for i in impl_sig] or [0.0])
    ref_sig = [j for j, p in enumerate(reference_palette) if p.get("coverage", 0) >= sig]
    max_ref = max([float(d76[:, j].min()) for j in ref_sig] or [0.0])
    max_de = max(max_impl, max_ref)
    drift = 0.0
    for j, p in enumerate(reference_palette):
        cov = sum(imp[i]["coverage"] for i in range(len(imp)) if near[i] == j)
        drift += abs(p.get("coverage", 0) - cov)
    return {
        "mean_delta_e76": round(mean_de, 2),
        "mean_delta_e2000": round(mean_de00, 2),
        "max_delta_e76": round(max_de, 2),
        "coverage_drift": round(drift, 4),
        "thresholds": {"mean_delta_e76": mean_max, "max_delta_e76": max_max, "coverage_drift": drift_max},
        "pass": bool(mean_de <= mean_max and max_de <= max_max and drift <= drift_max),
    }


def layout_map(rgb_image: np.ndarray, cols: int = 16, rows: int = 9) -> np.ndarray:
    """Coarse luminance map (rows x cols, 0..1) used to compare composition structure."""
    h, w = rgb_image.shape[:2]
    y = (0.2126 * rgb_image[..., 0] + 0.7152 * rgb_image[..., 1] + 0.0722 * rgb_image[..., 2]) / 255.0
    out = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            out[r, c] = y[r * h // rows:(r + 1) * h // rows, c * w // cols:(c + 1) * w // cols].mean()
    return out


def layout_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute difference of two layout maps after removing each map's mean level,
    so a global brightness change alone does not count as a different layout."""
    return float(np.abs((a - a.mean()) - (b - b.mean())).mean())


def ink_coverage(rgb_image: np.ndarray, tol: float = 6.0) -> float:
    """Fraction of pixels perceptibly different from the dominant (modal) colour."""
    flat = rgb_image.reshape(-1, 3)
    q = (flat // 8).astype(np.int64)
    key = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    vals, counts = np.unique(key, return_counts=True)
    mode = vals[counts.argmax()]
    mrgb = np.array([(mode // 1024) * 8 + 4, ((mode // 32) % 32) * 8 + 4, (mode % 32) * 8 + 4])
    lab = srgb_to_lab(flat[:: max(1, len(flat) // 200_000)])
    mlab = srgb_to_lab(mrgb)
    return float((delta_e76(lab, mlab) > tol).mean())


def border_background(rgb_image: np.ndarray, band: float = 0.03) -> np.ndarray:
    """Background colour estimated as the per-channel median of the frame's border band.

    More robust than the most common colour: a large foreground sheet can out-vote the ground
    (and flip an ink map), but the outer 3% of a composed frame is almost always ground."""
    h, w = rgb_image.shape[:2]
    bh, bw = max(2, int(h * band)), max(2, int(w * band))
    ring = np.concatenate([rgb_image[:bh].reshape(-1, 3), rgb_image[-bh:].reshape(-1, 3), rgb_image[:, :bw].reshape(-1, 3), rgb_image[:, -bw:].reshape(-1, 3)])
    return np.median(ring, axis=0)


def ink_map(rgb_image: np.ndarray, cols: int = 16, rows: int = 9, tol: float = 8.0) -> np.ndarray:
    """Per-cell fraction of pixels perceptibly different from the background (border median).

    Unlike a luminance map this is invariant to palette: the same composition in two colour schemes
    gives (nearly) the same ink map, so distances between ink maps measure STRUCTURE (where things are),
    which is what separates a real alternative from a re-skin.
    """
    h, w = rgb_image.shape[:2]
    flat = rgb_image.reshape(-1, 3)
    ink = (delta_e76(srgb_to_lab(flat), srgb_to_lab(border_background(rgb_image))) > tol).reshape(h, w)
    out = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            out[r, c] = ink[r * h // rows:(r + 1) * h // rows, c * w // cols:(c + 1) * w // cols].mean()
    return out


def structure_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute difference of two ink maps (0 = same structure, ~0.5 = unrelated)."""
    return float(np.abs(a - b).mean())
