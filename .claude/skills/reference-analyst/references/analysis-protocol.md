# Reference Analysis Protocol

How to turn the automated evidence for one reference video into a source record and technique records. Read with `catalogue/schemas/reference-source.schema.json` and `catalogue/schemas/reference.schema.json`.

## 1. Evidence to look at, in order

| Artefact | Look for | Typical pitfalls |
| --- | --- | --- |
| `overview.jpg` | concept, palette, recurring motifs, layout system, how the piece opens and closes | evenly spaced frames miss fast events; confirm with strips |
| `scenes.jpg` | what each scene does; whether "scenes" are real cuts or one stage changing in place | a long single-stage piece shows as one scene: that is a finding, not a failure |
| `transitions.jpg` | cut, dissolve, wipe, mask, bloom, match cut, morph; what carries continuity | a boundary marked `soft` may be a fast move; a `cut` between near-identical frames may be a held pose; the detector's cut/soft label is not a family (12 of 108 batch-0 boundaries read otherwise), so name the family (cut, grow, cover, continuous) from the sheet, and from a 30 fps `strip` when direction or origin is unclear (an every-2nd-frame sheet read a bloom from a ball as a disc sweeping in from the left) |
| `motion.jpg` | easing feel (overshoot, settle, anticipation), stagger, smear or blur, squash and stretch | 10 fps strips under-sample sub-100 ms events; run `strip` at 24-30 fps for those |
| `audio.png` + `automated.audio` | music bed, hits, silence, voice-like modulation, tempo; alignment of boundaries with onsets and beats | alignment near chance level is not sync; signal features cannot identify speech content or music licence; when provenance cites a measured fraction, cite the boundaries that carry it (nearest onset within `tolerance_ms`, or within 60 ms of the grid from `tempo_estimate.bpm` and `beat_phase_sec`), not simply the hard cuts: 5 of 11 `cut-on-beat` entries cited the wrong boundaries until recomputed |
| `listen/listen.jpg` + `automated.listen` | what is on screen while each phrase is spoken (captions, lanes, highlighted words); what the picture does on each strong accent (an element arriving, a cut, a flash); speech pace, pauses, cuts in pauses, accents on cuts vs chance, silences before hits, loudness | Windows desktop dictation hallucinates words over music: `narration: sparse` with 1-3 word phrases is usually noise, so confirm on the phrase frames; accents may belong to the music, not separate effects; earshot tagging (`earshot` block) runs only where its models are cached |
| `frames/` | typography (classification, weight, case, tracking), texture, line quality | compression blurs fine texture; say "appears" when unsure |

Record in `analysis.method` what was actually examined (for example "overview, scenes, 6 transition strips, 2 motion strips at 10 fps, audio panel, listen sheet; no listening").

## 2. Notes: observed, interpreted, confidence

- **Observed:** concrete and timestamped. "0.6-0.9 s: the word scales from 240 % to 100 % with one overshoot." Not "dynamic, energetic text".
- **Interpreted:** purpose and effect. "The overshoot sells the word as landing on the beat."
- **Confidence:** `high` when several frames or strips show it; `medium` when inferred from sparse frames; `low` for guesses (easing curve shapes, audio intent).
- Fill `difficult` with techniques that would be hard to reproduce and why (3D renders, liquid simulation, hand animation, footage). Fill `uncertainties` with what the evidence cannot settle.

Aspect checklist (write the ones that matter, not all): visual identity, palette, typography, composition, shapes and materials, motion, easing, timing and rhythm, transitions, depth and layering, texture and effects, camera, audio and sync, sound design (where accents, music and silence land against the picture), narration (presence, words per second, pauses, pace curve, cuts against phrases), captions (lane, grouping, highlight, timing against the voice), motifs.

For a technique's mechanics, pin the numbers with the motion-spec method in `docs/reference-playbook.md` (first and last moving frame per element and property, easing read from where the midpoint lands, staggers from sibling start frames), on a `strip` at 24-30 fps.

## 3. Rights and brand assets

- Default `rights.usage` is `inspiration-only`, `licence` unknown, creator unknown unless shown on screen (record a visible credit in `source.creator`).
- Add a `brand_assets` entry (`kind`, `description`, `timestamps`, `policy: "exclude"`) for every logo, wordmark, mascot, product UI, character or distinctive branded combination. `authorised` is only possible with a recorded licence and a usage other than `inspiration-only`; the validator rejects it otherwise.
- Techniques are written generically: "a dot blooms into the next scene's background", not "the X logo bursts".

## 4. Is it a technique?

A technique is reusable across subjects and styles and can be described by mechanics and parameters. Subject matter, a specific illustration, or a brand system is not. Before writing a record:

1. `python scripts/reference-corpus.py check --name "<candidate>" --tags a,b --text "<mechanics in one line>"`.
2. Score >= 0.5: extend the existing record (provenance, parameters, failure modes). 0.2-0.5: read the candidates; usually extend. Otherwise create.
3. IDs: kebab-case, descriptive of the technique (`pen-led-stroke`), never a brand or creator name, and unique across techniques, effects, recipes and compositions.

## 5. Capability classification

| Question | If yes |
| --- | --- |
| Can the current runtime (GSAP timeline, HTML/CSS/SVG, Canvas 2D, seeded randomness) produce it deterministically at preview and HyperFrames render quality? | `native` |
| Can a cheaper stand-in produce the read of it with stated losses (motion blur via directional blur plus stretch; 3D via CSS transforms and layered SVG)? | `approximation`: describe the approximation and its limits in `capability.approximation` and `limitations` |
| Does it need a tool outside the runtime (Blender, a simulation, AI video, footage, Lottie authoring) whose output can be pre-rendered and ingested? | `additional-dependencies`: name the tool, the hand-off (for example pre-render, then `scripts/ingest-asset.sh`, then the `hybrid-video-underlay` effect) and licences in `additional_tooling` |
| Is it feasible but too heavy for the 8 GB M2 render host as specified (many filtered layers, large canvases, WebGL)? | `resource-constrained`: give a measurement (`resources.basis: measured` with `measurements`) or an explicit estimate |
| Is there no credible approach yet? | `research-required`: say what would need to be learned |

Also record `complexity`, `resources` (`basis` measured, estimated or untested), `native_option` and `advanced_path` where they differ, and `priority` (`creative_value`, `cost`, 1-5).

## 6. Lifecycle and evidence

| Derived lifecycle | Stored fields |
| --- | --- |
| observed | `implementation_state: observed`, no validation |
| specified | `documented`: mechanics and parameters written, no code |
| prototyped | `prototyped`: a test page or demo composes it from existing APIs |
| tested (preview) | `prototyped` or `implemented` plus `validation.state: preview` and evidence (runtime test, frame review, demo, benchmark) |
| tested (render) | `validation.state: render`: HyperFrames render on the render host |
| approved | `status: approved`, render evidence, plus every component it depends on approved |

Evidence entries: `{kind: runtime-test|frame-review|demo|render|benchmark, path, result, date, notes}`. Paths must exist in the checkout.

## 7. Quality bar for a finished source record

- `analysis.state: inspected`, `inspected_on`, `method`, `coverage`, `concept`, at least four relevant aspects, scenes for multi-scene pieces, at least one moment, uncertainties.
- Brand assets listed or explicitly none ("no marks seen" in `rights.notes`).
- Every technique linked both ways with timestamps; categories from the controlled list.
- `motion-catalogue.py validate` passes with no new warnings.
