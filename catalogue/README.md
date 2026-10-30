# Motion Graphics Capability Catalogue

The **Motion Graphics Capability Catalogue** is a machine-readable, schema-validated registry of animation libraries, visual effects, and deterministic animation recipes optimized for Apple Silicon (M-series, 8 GB Unified Memory) and HyperFrames headless Chromium rendering.

It also registers the creative-studio layers: **primitives** (`data/primitives/`), reusable **compositions** (`data/compositions/`), **style systems** (`data/styles/`, exactly one `default`), **project templates** (`data/project-templates/`, `pending:` location until built), **techniques** (`data/references/`: mechanics, parameters, capability class, provenance, validation evidence and a derived lifecycle) and **reference sources** (`data/reference-sources/`: one record per user-supplied reference video, with rights, automated evidence and the analyst's notes; the videos themselves never enter the repository). Search them with `--type primitive|composition|style|template|technique|source`; filter techniques with `--support` and sources with `--category`. Approved still means verified on the M2 with HyperFrames; components validated only in Playwright on other hosts stay `experimental`.

---

## 1. Directory Structure

```text
catalogue/
├── README.md                          # Catalogue guide and contribution runbook (this file)
├── index.json                         # Aggregated machine-readable catalogue manifest
│
├── schemas/                           # Draft-07 JSON Schemas
│   ├── library.schema.json            # Library and runtime capabilities
│   ├── effect.schema.json             # Visual effect intents and performance profiles
│   └── recipe.schema.json             # Deterministic GSAP animation recipes
│
└── data/                              # Individual atomic JSON records
    ├── libraries/                     # Evaluated runtime engines & browser primitives
    │   ├── gsap.json                  # GSAP 3.12.5 (APPROVED)
    │   ├── svg-native.json            # Native W3C SVG 2.0 (APPROVED)
    │   ├── canvas2d-native.json       # HTML5 Canvas 2D (APPROVED)
    │   ├── html5-video.json           # HTML5 Video Layer (APPROVED)
    │   ├── threejs.json               # Three.js WebGL (PROPOSED)
    │   └── animejs.json               # Anime.js (BLOCKED)
    │
    ├── effects/                       # Visual effect archetypes
    │   ├── crossfade-dissolve.json    # Zero-dip scene crossfades
    │   ├── traveling-packet.json      # Signal/token travel between nodes
    │   ├── marching-dashed-stroke.json# Continuous backprop flow
    │   ├── clip-path-reveal.json      # Mathematical curve disclosure
    │   ├── glow-pulse.json            # Active entity breathing glow
    │   └── hybrid-video-underlay.json # Veo cinematic video underlay
    │
    └── recipes/                       # Production-tested GSAP implementations
        ├── zero-dip-scene-transition.json
        ├── node-network-signal-transfer.json
        ├── backpropagation-flow.json
        ├── metric-curve-draw.json
        ├── active-entity-glow.json
        └── cinematic-backdrop-blend.json
```

---

## 2. Approval States Lifecycle

Every record in the catalogue carries a strict approval state:

| Status | Definition | Production Permitted? |
|---|---|:---:|
| **`approved`** | Production-certified. Verified on Apple Silicon (M2 8GB) with HyperFrames 1280×720 @ 30fps. Verified commercial licensing. Zero DOM memory leaks. | **YES** |
| **`experimental`** | In active benchmarking. Passed initial code review; undergoing low-memory stress tests and headless Chromium capture verification. | **NO** (Scratch only) |
| **`proposed`** | Under architectural evaluation. Documented requirements, but lacks verified runtime tests or exhibits memory/timing risks (e.g. Three.js). | **NO** |
| **`deprecated`** | Formerly approved. Superseded by a safer or lighter alternative; scheduled for removal. Existing projects may run, but new projects must not adopt. | **NO** (Avoid) |
| **`blocked`** | Explicitly forbidden. Fails memory constraints, causes headless Chromium GPU stalls, introduces non-deterministic frame drift, or is redundant (e.g. Anime.js). | **NO** (Strictly forbidden) |

---

## 3. Verified Licensing Policy

1. **Explicit Verification:** Every library record has `licensing.status` set to either `"verified"` or `"unverified"`.
2. **Audit Rule:** No library can be marked `approved` while `licensing.status` remains `"unverified"`.
3. **Commercial Clearance:** Libraries must provide `licensing.commercial_use: true` without requiring paid per-seat or royalty terms for motion graphics video distribution.
4. **License Drift:** If an upstream library changes its licensing terms, its record must be reassessed immediately.

---

## 4. Hardware & Memory Guardrails (Apple Silicon M2, 8 GB RAM)

- **Target Profile:** 1280×720 @ 30fps H.264 video.
- **Memory Ceiling:** Total headless Chromium render memory must remain **$\le$ 1.5 GB**.
- **Worker Concurrency:** Single worker only (`--low-memory-mode`). Parallel headless browser instances are strictly forbidden.
- **Determinism:** `Math.random()` is banned. Any procedural effect must accept a seeded PRNG (`mulberry32`).
- **Timeline Binding:** All visual timelines must register under `window.__timelines['root']` with `{ paused: true }`.

---

## 5. Catalogue CLI Reference

The catalogue is queried and maintained via `scripts/motion-catalogue.py`:

```bash
# 1. Search by keyword across all types:
python3 scripts/motion-catalogue.py search --query "crossfade"

# 2. Search approved effects with specific visual tags:
python3 scripts/motion-catalogue.py search --type effect --tag data-flow --status approved

# 3. Search recipes verified for low-memory mode:
python3 scripts/motion-catalogue.py search --type recipe --compat low-memory

# 4. View complete recipe parameters, snippets, and validation steps:
python3 scripts/motion-catalogue.py get zero-dip-scene-transition

# 5. List entire registry overview:
python3 scripts/motion-catalogue.py list

# 6. Validate all schemas, cross-references, and approval rules:
python3 scripts/motion-catalogue.py validate

# 7. Recompile index.json:
python3 scripts/motion-catalogue.py export

# 8. Techniques learned from reference videos, by capability class:
python3 scripts/motion-catalogue.py search "transition" --type technique --support native

# 9. Reference videos by category; techniques, precedents and styles for a brief:
python3 scripts/motion-catalogue.py search --type source --category kinetic-typography
python3 scripts/motion-catalogue.py recommend --brief projects/<slug>/brief.json --implemented-only
```

Validation also enforces knowledge-base honesty: technique provenance may cite only inspected sources (timestamps inside the video, links in both directions), preview or render validation needs evidence and an implementation, `approved` needs render-host evidence, and `inspiration-only` sources cannot authorise brand assets. The workflow for adding a video is in `ARCHITECTURE.md` section 0.8 and the `reference-analyst` skill.

---

## 6. Contribution Workflow

To add a new capability or library, follow the 5-step contribution protocol:
1. **Need Assessment:** Verify no existing approved library or recipe satisfies the requirement. Redundant libraries are automatically `blocked`.
2. **Licensing Clearance:** Audit upstream license (MIT, Apache-2.0, BSD, W3C) and set `status: "verified"`.
3. **Sandbox Testing:** Build an isolated test case in `tests/` and run `hyperframes render . --low-memory-mode`. Verify RAM $\le$ 1.5 GB.
4. **Schema Authoring:** Add JSON records in `catalogue/data/` conforming to `catalogue/schemas/`.
5. **Validation & Promotion:** Run `python3 scripts/motion-catalogue.py validate`. New entries enter as `proposed` or `experimental` before production signoff.

