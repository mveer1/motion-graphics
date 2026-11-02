# Animation Recipes Guide

Animation recipes are modular, copy-pasteable GSAP 3 code patterns anchored to measured narration timestamps.

---

## 1. Zero-Dip Scene Crossfade (`zero-dip-scene-transition`)

- **Parent Effect:** `crossfade-dissolve`
- **When to Use:** At every scene boundary (`s1` $\to$ `s2`, `s2` $\to$ `s3`, etc.) to eliminate dark screen dips.
- **Code:**
  ```javascript
  const FADE = 0.5; // seconds
  function sceneCrossfade(outSelector, inSelector, atTime, fade = FADE) {
    tl.to(outSelector, { opacity: 0, duration: fade, ease: 'power1.inOut' }, atTime - fade / 2);
    tl.to(inSelector,  { opacity: 1, duration: fade, ease: 'power1.inOut' }, atTime - fade / 2);
  }
  ```
- **Validation:** Run Gate 3 blackdetect (`scripts/run-qa-gates.sh`). Black start must be null.

---

## 2. Node Network Signal Travel (`node-network-signal-transfer`)

- **Parent Effect:** `traveling-packet`
- **When to Use:** Distributed consensus message passing, gradient packet flow, data requests across servers.
- **Code:**
  ```javascript
  // Set initial origin
  tl.set('#signal-dot', { opacity: 0, attr: { cx: fromX, cy: fromY } }, startTime);
  tl.to('#signal-dot', { opacity: 1, duration: 0.15 }, startTime);

  // Move along connection vector
  tl.to('#signal-dot', {
    attr: { cx: toX, cy: toY },
    duration: travelDuration,
    ease: 'power1.inOut'
  }, startTime + 0.15);

  // Pulse destination node upon packet arrival
  tl.to(targetSelector, {
    scale: 1.25,
    transformOrigin: '50% 50%',
    duration: 0.2,
    yoyo: true,
    repeat: 1,
    ease: 'power2.out'
  }, startTime + 0.15 + travelDuration);

  tl.to('#signal-dot', { opacity: 0, duration: 0.15 }, startTime + 0.15 + travelDuration + 0.1);
  ```

---

## 3. Marching Dashed Flow (`backpropagation-flow`)

- **Parent Effect:** `marching-dashed-stroke`
- **When to Use:** Illustrating reverse gradient flow, error feedback, or continuous directional pipelining.
- **Code:**
  ```javascript
  tl.to('#backprop-arrows', { opacity: 1, duration: 0.4 }, startTime);
  tl.fromTo('#backprop-arrows line',
    { strokeDashoffset: 0 },
    { strokeDashoffset: -60, duration: duration, ease: 'none' },
    startTime + 0.1
  );
  ```

---

## 4. Clip-Path Line Curve Draw (`metric-curve-draw`)

- **Parent Effect:** `clip-path-reveal`
- **When to Use:** Graphing loss curves, database B-Tree search depths, or metric trajectories.
- **Code:**
  ```javascript
  tl.fromTo('#clip-rect',
    { attr: { width: 0 } },
    { attr: { width: chartWidth }, duration: duration, ease: 'power1.inOut' },
    startTime
  );
  ```

---

## 5. Active Entity Glow Pulse (`active-entity-glow`)

- **Parent Effect:** `glow-pulse`
- **When to Use:** Emphasizing selected server node (e.g. Raft Leader), active tensor, or focused database index block.
- **Code:**
  ```javascript
  tl.to(targetSelector, {
    boxShadow: `0 0 24px ${glowColor}`,
    scale: 1.05,
    duration: pulseDuration / 2,
    yoyo: true,
    repeat: repeatCount,
    ease: 'power1.inOut'
  }, startTime);
  ```

---

## 6. Cinematic Backdrop Blend (`cinematic-backdrop-blend`)

- **Parent Effect:** `hybrid-video-underlay`
- **When to Use:** Layering subtle Veo/Flow cinematic footage beneath razor-sharp vector SVG.
- **Code:**
  ```javascript
  tl.fromTo('#veo-bg', { opacity: 0 }, { opacity: 0.28, duration: 1.0, ease: 'power1.inOut' }, startTime);
  tl.from('#vector-stage text', { opacity: 0, y: 20, duration: 0.8, stagger: 0.2 }, startTime + 0.5);
  ```

