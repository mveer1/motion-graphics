# GSAP 3 Motion Patterns for HyperFrames

HyperFrames controls timeline playback by advancing the paused timeline registered at `window.__timelines['root']`.

---

## 1. Zero-Dip Crossfade Pattern

Never fade out an old scene before fading in the new one. Synchronize the crossfade:

```javascript
const FADE = 0.5; // seconds

function sceneCrossfade(outSelector, inSelector, atTime) {
  // Both tweens start at the exact same midpoint offset
  tl.to(outSelector, { opacity: 0, duration: FADE, ease: 'power1.inOut' }, atTime - FADE / 2);
  tl.to(inSelector,  { opacity: 1, duration: FADE, ease: 'power1.inOut' }, atTime - FADE / 2);
}
```

---

## 2. Animated Signal Travel Across Nodes

To make data packets or signals traverse an SVG connection between two coordinates $(x_1, y_1)$ and $(x_2, y_2)$:

```javascript
// Register dot position
tl.set('#signal-dot', { opacity: 0, attr: { cx: x1, cy: y1 } }, startTime);
tl.to('#signal-dot', { opacity: 1, duration: 0.15 }, startTime);

// Travel along edge with organic easing
tl.to('#signal-dot', {
  attr: { cx: x2, cy: y2 },
  duration: 0.6,
  ease: 'power1.inOut'
}, startTime + 0.15);

// Pulse target node on arrival
tl.to('#target-node', {
  scale: 1.25,
  transformOrigin: '50% 50%',
  duration: 0.2,
  yoyo: true,
  repeat: 1
}, startTime + 0.75);

tl.to('#signal-dot', { opacity: 0, duration: 0.2 }, startTime + 0.85);
```

---

## 3. Marching Dashed Backpropagation Arrows

To illustrate backward error flow without abrupt flashing:

```javascript
// Reveal group
tl.to('#backprop-arrows', { opacity: 1, duration: 0.4 }, startTime);

// Shift stroke-dashoffset backward smoothly
tl.fromTo('#backprop-arrows line',
  { strokeDashoffset: 0 },
  { strokeDashoffset: -60, duration: 3.0, ease: 'none' },
  startTime + 0.1
);
```

---

## 4. Clip-Path Line Chart Drawing

Reveal an SVG loss or metric curve from left to right:

```html
<defs>
  <clipPath id="chart-clip">
    <rect id="clip-rect" x="70" y="0" width="0" height="400" />
  </clipPath>
</defs>
<path d="..." stroke="#3fb950" stroke-width="3" clip-path="url(#chart-clip)" />
```

```javascript
// Animate width of clipping rectangle
tl.fromTo('#clip-rect',
  { attr: { width: 0 } },
  { attr: { width: chartWidth }, duration: 2.2, ease: 'power1.inOut' },
  startTime
);
```

