# Explanation devices: the handbook

A film explains well when each scene uses the right device for what the narrator is doing at that moment. This
handbook makes that choice a lookup instead of a guess. A careful model and a quick one should pick the same
device for the same beat, and code it the same way.

- **Table (source of truth):** [`specs/explanation-devices.json`](../specs/explanation-devices.json). It holds the
  jobs, the devices, the caps and the bans.
- **Runtime:** [`src/studio/studio-explain.js`](../src/studio/studio-explain.js) (runtime 1.18.0), plus
  `Studio.fx.containerTransform` and `Studio.type.strikeCorrect` from 1.17.0.
- **Golden scenes:** [`tests/reference-derived/explain-*`](../tests/reference-derived/). Copy their patterns, not
  their words. Each one passes frame review with 0 errors and 0 warnings.
- **Checks:** `studio.py validate` reads each storyboard scene's `device` and reports problems under "devices:".

Where the devices came from: 96 technique records measured from 64 reference videos
([`docs/reference-playbook.md`](reference-playbook.md)). A council on 2026-11-28 picked about 13 devices by the job
they do for the narration. The rest stay as rules or recipes.

## The method (do it in this order)

1. **Name the job of each scene** (phase 2, story-writer). Ask what the narration does in that scene, then pick
   exactly one of the 12 jobs below. If a scene does two jobs, split it into two scenes.
2. **Pick the device** from the decision table. Prefer the first device listed for the job unless its "avoid when"
   applies.
3. **Write it into the storyboard scene.** `"device": {"job": "build-up", "id": "equation-build", "why": "the figure
   shows each term"}`. The `why` line is required thinking, even though the schema allows you to leave it out.
4. **Code it from the golden scene** (phase 3). Open the golden page for the device and copy its call pattern. Snap
   every call to a spoken word with `Studio.cues.fromWords` or `studio.py words <slug> "<phrase>"`.
5. **Check it.** Run `python scripts/studio.py validate <slug>` and fix every "devices:" warning. Then run
   `python scripts/frame-review.py <slug> --fonts google`, open the contact sheets and look at them.

## Decision table

| Narrator's job | Use | Avoid when |
| --- | --- | --- |
| `hook-headline`: open with the claim | `headline-pair` (set-up line, accent punch line), `headline-build` (a short phrase word by word) | Line 2 is longer than line 1; more than about 7 words |
| `introduce-term`: name a thing and show it | `headline-build`, `equation-build`, `container-transform` (a tile opens into its detail); existing `highlight`, `monument-stat` | Nothing on screen shows what the term refers to |
| `build-up`: assemble a whole part by part | `equation-build` (formula), `progression` (parts on one stage) | No figure shows the terms; more than about 6 terms or 7 items |
| `compare`: two things, one difference | `headline-pair`, `slider` (before and after values); existing `split-stage`, `monument-stat` | The difference is not one number or one line |
| `trace-cause`: change X and Y changes | `slider` (one input, one output), `trace-pair` (one variable, two views), `canvas-tour` | More than one input; the views are not driven by the same variable |
| `process-step`: walk through steps or parts | `progression` (all parts on one stage), `canvas-tour` (a map larger than the frame), `copy-slot` (a changing line beside a demo), `container-transform`; existing `stations`, `timeline` | Each step needs a different picture (use scenes) |
| `change-over-time`: a value or shape changes | `trace-pair`; existing `line-chart`, `timeline` | Only the end value matters |
| `rank-over-time`: who leads and when | `bar-race` | Only the final ranking matters; steps faster than 0.25 s |
| `system-running`: watch behaviour emerge | `simulation` | More than about 10 events a second; no regime captions |
| `demo-interaction`: someone uses an interface | `ui-demo`, `copy-slot` | Copying a real product's interface or brand |
| `correct-myth`: belief, struck, corrected | `strike-correct` | The claim is not actually wrong (use `compare`) |
| `change-chapter`: turn to a new section | `empty-stage-dip`; existing `scene-crossfade` | Every scene change; a hold over 0.5 s |

## Film-level rules (validate enforces them)

- **Caps per film:**
  - `simulation`, `bar-race`, `trace-pair`, `canvas-tour`: 1 each.
  - `headline-build`, `slider`, `container-transform`, `strike-correct`: 2 each.
  - `headline-pair`, `equation-build`, `progression`: 3 each.
  - `copy-slot`, `ui-demo`: 4 each.
  - `empty-stage-dip`: 6.

  A device that repeats too often stops carrying meaning.
- **Distinct devices:** at most 4 in a short film, 7 in a mid film and 12 in a long film. A few devices that recur
  with meaning read as designed; a new trick in every scene reads as a demo reel.
- **Never under narration:** `flash-cut`, `flash-cut-turn`, `beat-pulse`, and the techniques flash-frame cut, glitch
  type, chromatic punch, cut on beat, beat-grid arrivals and word-per-beat. Put them in a narration pause or over
  music only.
- **The same device in two scenes back to back** is noted. That is fine for a continuation; otherwise vary the
  device.

## Rules every device already follows (do not undo them)

- **Seek safety:** each device keeps its state in one number and tweens only that number, so every frame renders
  the same whichever way the timeline reached it. Call a device's state-changing methods (`drag`, `run`, `play`,
  `to`, `swap`, `type`, `flip`, `moveTo`) in time order.
- **Determinism:** randomness comes from seeds (`Studio.comp.simulationScript(seed, phases)`, `Studio.rng`). Never use
  `Math.random`, timers or `requestAnimationFrame`.
- **Text floor:** device text is at least 2.6% of the frame's short side (`2.6u`); frame review warns below it. When
  you resize text in a golden pattern, keep it at or above `2.6u`.
- **Colour comes from the style tokens:** `--c-accent`, `--c-accent-2`, `--c-positive`, `--c-negative`, `--c-ink`,
  `--c-rule`. On a light canvas, coloured text fails contrast below 4.5:1, so the simulation log keeps its outcome
  text in ink and puts the colour on a marker dot.

## Device cards

Each card gives the call, the timing that matters and the golden scene to copy.

### `headline-pair` and `headline-build`: `Studio.comp.headline`

```js
var pair = C.headline('#pair', { line1: 'Big goals fail.', line2: 'Small ones stick.' }, { line2At: at('small') });
pair.enter(tl, at('big'));                       // words rise 0.08 s apart; line 2 waits for its spoken word
var build = C.headline('#build', { text: 'Start small, repeat daily.' }, { preset: 'build' });
build.enter(tl, at('start'), { times: [at('start'), at('small'), at('repeat'), at('daily')] });
```

- Keep each line short: five words or fewer.
- Line 2 must not be longer than line 1; `pair.warnings` says so when it is.
- Size the hook on the parent: `#pair .st-hl { font-size: calc(var(--u) * 13); }`.
- Golden scene: `tests/reference-derived/explain-headline-copy/`.

### `equation-build`: `Studio.comp.equation`

```js
var eq = C.equation('#eq', { terms: ['y', '=', 'sin', { text: '(θ)', tone: 'accent' }] });
eq.build(tl, [at('y'), at('equals'), at('sine'), at('theta')]);   // each term on its spoken word
eq.ring(tl, 3, at('theta', 0.5));                                   // ring the result, 0.4 s
```

- Reveal a term only when the figure shows that part.
- Keep the figure moving under the equation (golden: a slower third turn of the trace).
- Golden scene: `tests/reference-derived/explain-equation-trace/`.

### `trace-pair`: `Studio.comp.tracePair`

```js
var trace = C.tracePair('#trace', { cycles: 3, period: 2.6, label: 'A point on a circle traces a sine wave' });
trace.enter(tl, at('spin', -0.4));
trace.run(tl, at('spin'), { cycles: 2 });                   // ends on the word that names the result
trace.run(tl, at('wave'), { cycles: 1, period: 5.8 });      // slower, so the figure never freezes
```

Give `#trace` a width and height. Golden scene: `explain-equation-trace/`.

### `slider`: `Studio.comp.slider`

```js
var slider = C.slider('#slider', { min: 0, max: 500, value: 50, step: 10, map: function (v) { return v * 155.282; },
  input: { label: 'Each month', prefix: '$' }, output: { label: 'After 10 years', prefix: '$' }, caveat: 'Assumes 5% a year' });
slider.enter(tl, at('save'));
slider.drag(tl, at('more'), { to: 300 });     // 1.7 s, then the output settles in two small steps
slider.caveat(tl, at('assume'));               // hold the end value at least 1 s before this
```

- The output must be real arithmetic. Put the formula in a comment, and state the assumption in the caveat.
- Golden scene: `explain-slider-ui/`.

### `simulation`: `Studio.comp.simulation` and `Studio.comp.simulationScript`

```js
var events = C.simulationScript(11, [
  { from: 2.0, to: 3.9, rate: 8, kind: 'take' },
  { from: 2.25, to: 10.5, rate: 2, kind: 'refill', jitter: 0 },
  { from: 5.0, to: 10.5, rate: 1, kind: 'take' }]);
var sim = C.simulation('#sim', { capacity: 8, events: events, duration: 11,
  regimes: [{ t: 0, text: 'Full: 8 tokens to spend' }, { t: 2.0, text: 'A burst spends them fast' }] });
sim.enter(tl, 0.4);
sim.run(tl, 0.6);              // sim clock runs 1:1 from 0.6 s; give each regime caption at least 1.6 s
```

- Give `#sim` a height.
- Name every regime in a caption.
- Keep the event rate at or below about 10 a second.
- Golden scene: `explain-simulation-race/`.

### `bar-race`: `Studio.comp.barRace`

```js
var race = C.barRace('#race', { names: [...], frames: [{ label: 'Jan', values: [...] }, ...], format: { suffix: 'k' } }, { rows: 5 });
race.play(tl, at('who'), { step: 0.7 });
```

- Use 0.25-0.7 s per step.
- Label data "Illustrative numbers" unless it is sourced.
- Golden scene: `explain-simulation-race/`.

### `progression`: `Studio.comp.progression`

```js
var prog = C.progression('#ui', { items: ['#c0', '#c1', '#c2'], steps: [
  { focus: [0, 1, 2], caption: 'Three moves, for every job' },     // step 0: the overview
  { focus: 0, caption: 'Read the job from the queue' }, ...] });
prog.to(tl, 1, at('read')); prog.to(tl, 2, at('check')); prog.to(tl, 3, at('write'));
```

- Lay out the items yourself; the device only moves the focus.
- Change one thing per step, and name it in the caption.
- Golden scene: `explain-tour-progression/`.

### `canvas-tour`: `Studio.space.tour`

```js
Studio.space.tour(tl, '#canvas', [
  { target: '#pClient', at: at('client', -0.4) }, { target: '#pQueue', at: at('queue', -0.4) }, ...
], { pullBack: at('whole'), start: 'first' });
```

- Make `#canvas` 2-3 times the frame, positioned at the top left.
- Hold each stop at least 2 s, and keep each panel's text to 6 words or fewer.
- Move anything that travels between panels in canvas space, so the camera follows it.
- Golden scene: `explain-tour-progression/`.

### `empty-stage-dip`: `Studio.fx.dip`

```js
tl.fromTo('#bg', { x: 0 }, { x: -36, duration: f.duration, ease: 'none', immediateRender: true }, 0);  // keeps moving
Studio.fx.dip(tl, '#sceneA', '#sceneB', at('inside'));   // 'inside' = first word of the next phrase
```

- Keep a persistent kicker or a moving background through the 0.25 s hold.
- Use it at section turns only.
- Golden scene: `explain-tour-progression/`.

### `copy-slot`: `Studio.comp.copySlot`

```js
var copy = C.copySlot('#copy', ['Two minutes is enough to begin.', 'After coffee, before the phone.']);
copy.enter(tl, 0, at('step1', -0.3));
copy.swap(tl, 1, at('step2'), { words: WORDS });   // WORDS from audio/words.json; check copy.warnings
```

- Leave at least 1.7 s between swaps of a six-word line.
- Golden scene: `explain-headline-copy/`.

### `ui-demo`: `Studio.comp.ui`

```js
var input = C.ui.input('#bar', { placeholder: 'Amount', text: '$300 every month' });
var btn = C.ui.button('#bar', { label: 'Save rule' });
var cursor = C.ui.cursor('#layer');                // a full-frame layer
input.type(tl, at('type'), { cps: 16 });
cursor.enter(tl, at('type', 0.4), { x: f.width * 0.42, y: f.height * 0.78 });
cursor.moveTo(tl, btn.el, at('press', -0.7), { duration: 0.6 });
cursor.click(tl, at('press')); btn.press(tl, at('press'));
```

- Scale the panel (`transform: scale(1.45)`) for a close demo shot.
- Do one action per spoken step.
- Golden scene: `explain-slider-ui/`.

### `container-transform` and `strike-correct` (runtime 1.17.0)

- `container-transform`: `Studio.fx.containerTransform(tl, '#tile', '#card', at, {outTarget, inTarget})`. A tile grows
  into the card it stands for.
- `strike-correct`: `Studio.type.strikeCorrect(tl, '#claim', '#fix', at)`. It types the claim, strikes it, demotes it
  and types the correction.
- Golden scenes: `tests/reference-derived/flash-and-container/` and `scramble-strike-caption/`.

## Checklist before you hand a film on

1. Every scene in `storyboard.json` has a `device` with a `job`, an `id` and a `why`.
2. `studio.py validate <slug>` shows no "devices:" warning.
3. Every device call is snapped to a spoken word, with no hard-coded seconds except offsets from a cue.
4. Something moves during every second of narration: drift, a device running, or a background.
5. Frame review shows 0 errors. Every `text_below_floor` and `line_unread` warning is fixed or explained.
6. You opened the contact sheets and looked at them. Automated checks do not replace looking.

## What is verified and what is not

- **Verified on Windows (2026-11-28):**
  - 63 runtime checks in `tests/studio-runtime/explain-devices.html`, including seek-order independence.
  - Frame review of the five golden scenes, with 0 errors and 0 warnings, and each contact sheet inspected.
  - `tests/test-explanation-devices.py` (the table and the validate checks).
- **Not verified:**
  - No HyperFrames render on the M2. The devices stay `experimental` until a render on the Mac.
  - No film uses them yet.
