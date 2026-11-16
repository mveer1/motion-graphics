#!/usr/bin/env python3
"""motion-continuity.py: find pops in a rendered film (art that appears, vanishes or snaps in one frame).

    .venv/bin/python scripts/motion-continuity.py <video.mp4> [--range 35,43] [--roi 0.15,0.80]
                     [--k 4.0] [--min-area 0.004] [--sheet out.png] [--json]

Why: the 2D Tibi swapped art at joint-angle thresholds (lats, deltoid caps, flexed arm), and none of the
automated gates saw it: frame-review checks layout, the QA gates check streams and loudness, a human saw the pop.
This is the missing objective check. It decodes the film small (gray, 180 px wide), measures how many pixels
change between consecutive frames inside a region of interest (the figure area, not the captions), and flags
frames whose change is a spike against the surrounding motion: a smooth move changes a thin, steady band of
pixels each frame, a pop changes a whole patch at once.

Modes (measured on the upper-body-workout 2D film and the lab-3d-motion film, see references/motion-3d.md):
  patch  (default) filled patches only: a muscle, cap or limb appearing, a colour snapping in one frame. Radius 16 px
         so fast limbs and dumbbells count as "beside" their last position; a morphological opening drops hairline
         edges (the first frame of a move after a hold). Found: the 3D press activation colour snap (0.2 s fade).
         Did NOT find the old 2D art swaps: they change a thin crescent of the arm, indistinguishable from motion.
  edge   radius 5, no opening: also reports thin outline swaps. Found the old 2D press (38.5 s, 40.4 s), curl
         (209.5 s, 210.6 s) and raise events, confirmed by eye as arm art variants changing; it also fires on
         fast dumbbell moves, so every edge-mode POP must be looked at before it is believed.

Reading the result:
  POP    unforeseen change > k x the rolling median of its neighbours (+/- 8 frames) and > min-area of the ROI
  CUT    more than 35% of the ROI changed: a hard cut or crossfade edge, listed but not a failure
Evidence over verdict: it never says "good", only "no pop found in <range>"; look at the --sheet frames before
and after every POP (frame t-1 | t | t+1, difference highlighted).
Exit code 1 when a POP is found. Light job (ffmpeg decode at 180 px), but run it under `session-guard.py run render --`
on a loaded host.
"""
import argparse
import json
import subprocess
import sys

import numpy as np


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height,r_frame_rate:format=duration', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    w, h = j['streams'][0]['width'], j['streams'][0]['height']
    n, d = j['streams'][0]['r_frame_rate'].split('/')
    return w, h, float(n) / float(d), float(j['format']['duration'])


def decode(path, w, h, t0, t1, fps, width=180):
    sh = int(round(h * width / w / 2) * 2)
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0), '-i', path, '-vf',
           f'fps={fps},scale={width}:{sh}', '-pix_fmt', 'gray', '-f', 'rawvideo', '-']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, sh, width), sh


def dilate(mask, r):
    """Binary dilation by a (2r+1) square, numpy only."""
    out = mask.copy()
    for _ in range(r):
        o = out.copy()
        o[1:] |= out[:-1]
        o[:-1] |= out[1:]
        o[:, 1:] |= out[:, :-1]
        o[:, :-1] |= out[:, 1:]
        out = o
    return out


def opened(mask, r=2):
    """Morphological opening: erode then dilate, so hairline edges (the first frame of a move after a hold) vanish and only filled patches remain."""
    eroded = ~dilate(~mask, r)
    return dilate(eroded, r)


def analyse(frames, roi, k, min_area, fps, t0, radius=16, open_r=2):
    """Per frame: how many changed pixels have NO changed pixel within `radius` px in the previous two frame pairs.
    Smooth motion moves an edge band a pixel or two, so its change always sits next to last frame's change.
    A pop (a muscle, a cap, a limb variant appearing or vanishing) is a patch of change with nothing around it."""
    h = frames.shape[1]
    y0, y1 = int(roi[0] * h), int(roi[1] * h)
    r = frames[:, y0:y1].astype(np.int16)
    ch = np.abs(np.diff(r, axis=0)) > 14                       # ch[i] = change between frame i and i+1
    total = float(ch.shape[1] * ch.shape[2])
    changed = ch.reshape(len(ch), -1).sum(axis=1) / total
    novel = np.zeros(len(ch))
    for i in range(1, len(ch)):
        prev = ch[i - 1] | (ch[i - 2] if i >= 2 else False)
        m = ch[i] & ~dilate(prev, radius)
        novel[i] = (opened(m, open_r) if open_r else m).sum() / total
    events = []
    for i in range(1, len(ch)):
        t = t0 + (i + 1) / fps
        if changed[i] > 0.35:
            events.append({'t': round(t, 3), 'frame': i + 1, 'kind': 'CUT', 'changed': round(float(changed[i]), 4)})
            continue
        lo, hi = max(1, i - 8), min(len(ch), i + 9)
        nb = np.concatenate([novel[lo:i], novel[i + 1:hi]])
        base = max(float(np.median(nb)) if len(nb) else 0.0, min_area / 4)
        if novel[i] > min_area and novel[i] > k * base:
            events.append({'t': round(t, 3), 'frame': i + 1, 'kind': 'POP', 'changed': round(float(novel[i]), 5), 'neighbour_median': round(base, 5), 'ratio': round(float(novel[i] / base), 1)})
    return novel, events


def contact_sheet(frames, events, path, roi):
    from PIL import Image
    pops = [e for e in events if e['kind'] == 'POP'][:8]
    if not pops:
        return
    h, w = frames.shape[1], frames.shape[2]
    sheet = Image.new('RGB', (w * 4, h * len(pops)), (30, 30, 30))
    for row, e in enumerate(pops):
        i = e['frame']
        a, b = frames[i - 1].astype(np.int16), frames[i].astype(np.int16)
        c = frames[min(i + 1, len(frames) - 1)]
        d = np.zeros((h, w, 3), np.uint8)
        d[..., 0] = np.clip(np.abs(b - a) * 4, 0, 255)
        d[..., 1] = frames[i] // 3
        d[..., 2] = frames[i] // 3
        for col, im in enumerate([frames[i - 1], frames[i], c]):
            sheet.paste(Image.fromarray(im).convert('RGB'), (col * w, row * h))
        sheet.paste(Image.fromarray(d), (3 * w, row * h))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--range', help='start,end seconds (default: the whole film)')
    ap.add_argument('--roi', default='0.15,0.80', help='vertical band to watch as fractions of the height (default 0.15,0.80: skips the title and the captions)')
    ap.add_argument('--k', type=float, default=4.0)
    ap.add_argument('--min-area', type=float, default=0.0004, help='unforeseen change, as a share of the ROI, below which nothing is reported (default 0.04%%)')
    ap.add_argument('--mode', choices=['patch', 'edge'], default='patch', help='patch (default): filled patches only, radius 16, opening 2 (colour snaps, parts appearing). edge: radius 5, no opening, also reports thin outline swaps, with false positives on fast limbs')
    ap.add_argument('--radius', type=int, default=None, help='how far (px at 240 wide) last frame\'s motion may be from this frame\'s change before it counts as unforeseen; raise it for fast moves')
    ap.add_argument('--fps', type=float, default=30)
    ap.add_argument('--sheet')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    w, h, _, dur = probe(a.video)
    t0, t1 = (float(x) for x in a.range.split(',')) if a.range else (0.0, dur)
    roi = [float(x) for x in a.roi.split(',')]
    frames, _ = decode(a.video, w, h, t0, t1, a.fps, width=240)
    radius = a.radius if a.radius is not None else (16 if a.mode == 'patch' else 5)
    changed, events = analyse(frames, roi, a.k, a.min_area, a.fps, t0, radius, 2 if a.mode == 'patch' else 0)
    if a.sheet:
        contact_sheet(frames, events, a.sheet, roi)
    pops = [e for e in events if e['kind'] == 'POP']
    if a.json:
        print(json.dumps({'video': a.video, 'range': [t0, t1], 'frames': len(frames), 'events': events}, indent=1))
    else:
        print(f'{a.video}  {t0:.1f}-{t1:.1f}s  {len(frames)} frames  roi {roi}')
        print(f'  unforeseen change per frame: median {float(np.median(changed)) * 100:.3f}% of the ROI, max {float(changed.max()) * 100:.3f}%')
        for e in events:
            if e['kind'] == 'POP':
                print(f"  POP  t={e['t']:.2f}s  {e['changed'] * 100:.2f}% of the ROI changed with no motion beside it in the last frames ({e['ratio']}x its neighbours)")
            else:
                print(f"  cut  t={e['t']:.2f}s  {e['changed'] * 100:.0f}% changed (hard cut or fade edge)")
        print(f"  -> {len(pops)} pop(s)" if pops else '  -> no pop found in this range (look at the frames anyway)')
    sys.exit(1 if pops else 0)


if __name__ == '__main__':
    main()
