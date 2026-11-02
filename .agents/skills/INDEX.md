# Skill Index

This folder holds only the index. The skills themselves live in `.claude/skills/<name>/SKILL.md`, read by Claude Code. Their former location, `.agents/skills/`, came from the Antigravity-era setup.

Each skill is loaded by name through the Skill tool. The "Owner" column shows where the skill came from: **project** means written for this workspace; **vendored** means copied from upstream (see `skills-lock.json` for hashes and sources).

## Production pipeline

| Skill | Owner | Use it for |
|---|---|---|
| `motion-graphics-designer` | project | Creative direction, layout rules, palettes and GSAP 3 patterns for short motion pieces in 16:9, 9:16 and 1:1. |
| `video-assembler` | project | Render automation on Apple Silicon, FFmpeg multiplexing, low-memory render settings and the five QA gates (`scripts/run-qa-gates.sh`). |
| `parallel-session` | project | Coordinating concurrent production sessions through `scripts/session-guard.py` and the `.locks/` files. |
| `technical-researcher` | project | Stage 0 research dossiers (`research.json` / `research.md`), formula checks and visual metaphors. |
| `motion-library-guide` | project | Navigating the capability catalogue, approval states (approved / proposed / blocked) and animation recipes. |
| `reference-analyst` | project | Analysing reference videos into techniques, using `scripts/reference-corpus.py`. Learns techniques only, never assets. |

## Motion and animation

| Skill | Owner | Use it for |
|---|---|---|
| `motion-design` | vendored (LottieFiles) | Disney-style principles adapted for UI: timing, easing, choreography, 1/3 rules. |
| `kinetic-typography` | vendored (iart-ai) | Text choreography: overflow masks, variable-font weight shifts, SplitText, screen-reader safe text changes. |
| `epic-design` | vendored (alirezarezvani) | Cinematic 2.5D scroll staging, six depth layers, clip-path transitions, no WebGL. |
| `collage-design` | vendored (polgarp) | Mixed-media collage styling (torn edges, tape, halftone) rendered through headless Chromium. |
| `algorithmic-art` | vendored (Pardesco) | Generative art (flow fields, attractors, shaders) adapted for deterministic rendering. |
| `gsap-core` | vendored (GreenSock) | GSAP core API: `to`, `from`, `fromTo`, easing, stagger, `matchMedia`. |
| `gsap-timeline` | vendored (GreenSock) | Timeline sequencing, position parameters, nesting. |
| `gsap-plugins` | vendored (GreenSock) | Plugin registration and use: SplitText, Flip, SVG drawing, Draggable and others. |
| `gsap-utils` | vendored (GreenSock) | `gsap.utils`: clamp, mapRange, normalize, snap, wrap, toArray, random. |
| `gsap-scrolltrigger` | vendored (GreenSock) | Scroll-linked animation, pinning, scrub. |
| `gsap-performance` | vendored (GreenSock) | Transform-first animation, avoiding layout thrash, batching. |
| `gsap-react` | vendored (GreenSock) | `useGSAP`, refs, `gsap.context()`, cleanup in React / Next.js. |
| `gsap-frameworks` | vendored (GreenSock) | GSAP in Vue, Svelte and other non-React frameworks. |

## Audio

| Skill | Owner | Use it for |
|---|---|---|
| `voice-director` | project | Kokoro voice personas, narration pacing, silence buffers and phonetic respellings (`src/pipeline/tts.py`). |
| `kokoro-smart-tts-skill` | project | Prosody and text preprocessing that makes Kokoro speech sound more natural, including multi-voice blending. |
| `real-sfx` | vendored (Clipwing, under `tools/clipwing-skills`) | Foley and SFX placement from HyperFrames cues, mixed from the user's own sound library. |
| `earshot` | vendored (under `tools/earshot`) | Listening and measuring: loudness, sync, picking or trimming sounds, procedural micro-SFX. |

## Governance

| Skill | Owner | Use it for |
|---|---|---|
| `workspace-steward` | project | Placement policy, registration in `catalogue/data/`, licence audit and drift checks. **Consult before adding a library, tool, skill or integration.** |

## Not skills

- `kokoro-tts/` has `examples/`, `references/`, `scripts/` and `tests/`, but no `SKILL.md`, so Claude Code does not load it as a skill. It is also untracked by git. Decide whether to promote it to a skill with a `SKILL.md` or move it out.

## Maintenance

- Add a row here whenever a skill is added, renamed or removed.
- Registration in `catalogue/data/` and the governance audit are still required: run `python3 scripts/workspace-governance.py`.
- Add skills only under `.claude/skills/`. Do not create a second copy here.
