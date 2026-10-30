# Motion Lab: Technical Motion Graphics Production Pipeline

An end-to-end, reproducible, low-memory video production pipeline built for engineering, scientific, and technical explainers on Apple Silicon macOS (optimized for 8 GB RAM).

Motion Lab automates the complete lifecycle: from technical research dossier validation, studio-grade speech synthesis, and frame-accurate GSAP 3 / SVG animation to intelligent sound design, multi-track audio multiplexing, and automated QA gates.

---

## Table of Contents

- [Key Capabilities](#key-capabilities)
- [Open Source Tools & Attributions](#open-source-tools--attributions)
- [Production Lifecycle (Stages 0–9)](#production-lifecycle-stages-09)
- [Directory Layout](#directory-layout)
- [Workspace Governance & Stewardship](#workspace-governance--stewardship)
- [Quickstart & Commands](#quickstart--commands)
- [Hardware & Memory Management](#hardware--memory-management)
- [Showcase Portfolio](#showcase-portfolio)
- [Credits & Licensing](#credits--licensing)

---

## Key Capabilities

- **Natural Narration:** Kokoro TTS v0.9.4 generating 24 kHz WAV narration with accurate G2P phonemisation and configurable speech pacing (default: 1.15x).
- **Procedural Motion Graphics:** HyperFrames CLI + GSAP 3 + SVG compositions rendered via headless Chrome with ANGLE Metal GPU acceleration.
- **Audio-Driven Timeline Synchronization:** Visual animations are strictly driven by actual measured audio waveforms (sub-millisecond ffprobe timing), with 0.5s inter-scene padding buffers.
- **Acoustic Intelligence & Real SFX:** Visual cue detection from code, CC0 sound effect retrieval from Openverse, code-synthesized micro-SFX via Earshot, and multi-track audio ducking.
- **Decoupled Stream Assembly:** Sub-second FFmpeg stream multiplexing (`-c:v copy -c:a aac`) eliminating costly video re-encoding.
- **Automated QA Verification:** 5-gate automated validation suite (`run-qa-gates.sh`) ensuring stream integrity, EBU R128 loudness compliance, zero black gaps, bitrate targets, and spectral acoustic health.
- **Single-Command Orchestration:** Automated project builder executing the entire pipeline from Stage 0 to Stage 9 (`./scripts/build-project.sh <project-slug>`).

---

## Open Source Tools & Attributions

This project stands on the shoulders of remarkable open-source software, models, tools, and datasets. We gratefully credit the original authors and maintainers:

### 1. Voice Synthesis & Phonetics

- **[Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M)** by [hexgrad](https://github.com/hexgrad) (Apache-2.0 License)
  - An open-weight 82-million parameter text-to-speech model that punches well above its weight class. Kokoro delivers natural, expressive prosody with ultra-fast inference on CPU and Apple Silicon.
  - *Usage:* Powers `src/pipeline/tts.py` and `scripts/build-audio.py`, generating 24 kHz mono PCM WAV narration across male and female personas (`am_adam`, `af_bella`, `am_michael`, `af_sarah`, `bm_george`, `bf_emma`).
- **[Misaki](https://github.com/hexgrad/misaki)** by [hexgrad](https://github.com/hexgrad) (Apache-2.0 License)
  - G2P (Grapheme-to-Phoneme) conversion engine providing accurate phonemic transcription for English pronunciation.
- **[eSpeak NG](https://github.com/espeak-ng/espeak-ng)** (GPLv3 License)
  - Universal text-to-speech phoneme engine used by Kokoro for phonetic segmentation and fallback synthesis.

### 2. Motion Graphics & Visual Rendering

- **[HyperFrames](https://hyperframes.dev)** by the HyperFrames Team
  - A code-first motion graphics framework and CLI that renders HTML5, CSS, SVG, Canvas, and JavaScript animations into frame-accurate MP4 video using headless Chromium with ANGLE Metal hardware acceleration.
  - *Usage:* Primary visual rendering engine (`hyperframes render --low-memory-mode`, `hyperframes snapshot`, `hyperframes lint`).
- **[GSAP 3 (GreenSock Animation Platform)](https://gsap.com)** by [GreenSock / Webflow](https://greensock.com) (Standard 'No-Charge' GreenSock License)
  - The industry-standard JavaScript animation library. Provides rock-solid timeline sequencing, easing curves, and deterministic frame stepping.
  - *Usage:* All scene animations are orchestrated with GSAP 3 timelines attached to `window.__timelines['root']`, synchronized to millisecond audio timeline maps.
- **[Three.js](https://threejs.org)** by [Ricardo Cabello (Mr.doob)](https://github.com/mrdoob/three.js) and contributors (MIT License)
  - WebGL/WebGPU 3D graphics library registered in the capability catalogue (`catalogue/data/libraries/threejs.json`) for spatial data visualizations and 3D scenes.
- **[Anime.js](https://animejs.com)** by [Julian Garnier](https://github.com/juliangarnier/anime) (MIT License)
  - Lightweight, flexible JavaScript animation engine registered in the capability catalogue (`catalogue/data/libraries/animejs.json`) for micro-interactions and SVG path morphing.

### 3. Sound Design, Foley & Acoustic Intelligence

- **[Earshot](https://github.com/Leonxlnx/earshot)** by [Leon (@Leonxlnx)](https://github.com/Leonxlnx) (MIT License)
  - An acoustic intelligence CLI and procedural sound synthesis engine built as "Ears for Coding Agents".
  - *Usage:* Vendored under `tools/earshot`. Provides procedural micro-SFX rendering (`earshot sfx render <id>`), objective loudness measurement (EBU R128), spectral bandwidth verification, sync checking, and automated acoustic QA gates.
- **[Real SFX & Clipwing Skills](https://github.com/Clipwing/skills)** by [Clipwing Team](https://github.com/Clipwing) (MIT License)
  - Sound design automation suite for motion graphics.
  - *Usage:* Vendored under `tools/clipwing-skills` and `.agents/skills/real-sfx/`. Extracts animation moments from HyperFrames compositions (`from_hyperframes.py`), maps visual events to real foley recordings (`suggest_cues.py`), and renders balanced multi-track SFX audio tracks (`mix.py`).
- **[Openverse](https://openverse.org)** by the [WordPress Foundation](https://wordpress.org) & Openverse Community (Open Source / CC-licensed metadata)
  - Search engine and index for over 700 million openly licensed and public domain creative works.
  - *Usage:* Directly queried via `scripts/sfx-openverse.py` to search and download high-quality CC0 and CC BY sound effects (whooshes, UI pops, mechanical clicks, ambient beds) with zero API keys required.

### 4. Audio-Video Multiplexing & Signal Processing

- **[FFmpeg & FFprobe](https://ffmpeg.org)** by Fabrice Bellard, Michael Niedermayer, and the FFmpeg Development Team (LGPLv2.1+ / GPLv2+)
  - The universal multimedia processing framework.
  - *Usage:* Sub-millisecond audio duration probing, EBU R128 loudness scanning (`-filter:a ebur128`), audio ducking via `amix` filter, and lightning-fast stream multiplexing (`-c:v copy -c:a aac -shortest`).
- **[SoundFile](https://github.com/bastibe/python-soundfile)** by Bastian Bechtold and Erik de Castro Lopo (BSD 3-Clause License)
  - Python interface to libsndfile for reading, writing, and transforming uncompressed PCM audio files.
- **[SciPy](https://scipy.org)** & **[NumPy](https://numpy.org)** by the SciPy and NumPy Developers (BSD 3-Clause License)
  - High-performance scientific computing and digital signal processing used across acoustic measurement and audio manipulation.
- **[jsonschema](https://github.com/python-jsonschema/jsonschema)** by Julian Berman (MIT License)
  - Strict JSON Schema Draft-07 implementation used for validating Stage 0 research dossiers (`scripts/validate-research.py`) and catalogue component metadata (`scripts/workspace-governance.py`).

---

## Production Lifecycle (Stages 0–9)

Every explainer video produced in this repository follows a strictly staged, quality-gated lifecycle:

```
[ Stage 0: Technical Research ]
  ├── research.json (Draft-07 schema validation via validate-research.py)
  └── research.md (Mathematical truth & visual metaphor archetypes)
        │
        ▼
[ Stage 1 & 2: Storyboarding & Narration Script ]
  └── narration.json (Scene definitions, phonetic respellings, pacing)
        │
        ▼
[ Stage 3: Speech Synthesis & Waveform Measurement ]
  ├── Kokoro TTS generates 24 kHz WAV clips via src/pipeline/tts.py
  ├── FFprobe measures exact millisecond durations
  └── audio/timeline.json generated with 0.5s inter-scene padding buffers
        │
        ▼
[ Stage 4: Motion Graphics Composition ]
  ├── Query capability catalogue (scripts/motion-catalogue.py)
  └── Author src/index.html with GSAP 3 timelines locked to timeline.json
        │
        ▼
[ Stage 4B: Foley Choreography & Sound Design ]
  ├── Visual moments extracted from index.html (from_hyperframes.py)
  ├── Openverse CC0 assets sourced (scripts/sfx-openverse.py)
  ├── Micro-sounds synthesized via Earshot (earshot sfx render)
  └── Multitrack SFX bed rendered (real-sfx mix.py -> audio/sfx-track.wav)
        │
        ▼
[ Stage 5 & 6: Linting & Headless Chrome Rendering ]
  ├── hyperframes lint index.html
  └── hyperframes render --low-memory-mode (Pinned 1 worker, ANGLE Metal)
        │
        ▼
[ Stage 8: Multi-Track Stream Multiplexing ]
  └── FFmpeg amix ducks SFX bed under narration (-c:v copy -c:a aac)
        │
        ▼
[ Stage 9: Automated QA Gates (run-qa-gates.sh) ]
  ├── Gate 1: Stream Integrity & Zero Silent Tracks
  ├── Gate 2: EBU R128 Loudness Verification (-16 to -14 LUFS)
  ├── Gate 3: Black Gap & Visual Dip Detection
  ├── Gate 4: Video Bitrate Compliance (1.0 to 4.5 Mbps)
  └── Gate 5: Earshot Acoustic Health & Spectral Bandwidth
```

---

## Directory Layout

```text
.
├── AGENTS.md                          # Operational instructions for AI agents
├── ARCHITECTURE.md                    # Complete system architecture & specifications
├── README.md                          # Pipeline documentation, open source credits & quickstart
├── .gitignore                         # Placement-policy-enforced gitignore
├── .gitmodules                        # Upstream git submodules for tools
├── specs/
│   ├── research-spec.json             # Stage 0: Research dossier JSON Schema (Draft-07)
│   ├── video-spec.json                # Declarative video specification schema
│   └── veo-integration.md             # Ingestion strategy for cinematic / Veo video
├── templates/
│   ├── research-template.json         # Reusable research data model instance
│   └── research-template.md           # Reusable Markdown dossier template
├── projects/                          # Production explainer workspaces
│   ├── benchmark-neural-network/      # Explainer 1: Deep Learning & Gradient Descent
│   ├── distributed-consensus-raft/    # Explainer 2: Raft Consensus & Log Replication
│   └── btree-database-indexing/       # Explainer 3: B-Trees & Storage Engine Geometry
├── out/                               # Portfolio delivery showcase
│   ├── index.html                     # HTML5 interactive video portfolio gallery
│   └── posters/                       # Video preview poster thumbnails
├── scripts/
│   ├── build-project.sh               # Full-lifecycle production orchestrator (0 -> 9)
│   ├── build-all.sh                   # Sequential batch portfolio builder & QA verifier
│   ├── build-audio.py                 # Kokoro TTS & timeline map generator
│   ├── sfx-openverse.py               # Openverse CC audio search and asset downloader
│   ├── motion-catalogue.py            # Capability catalogue CLI search & inspect
│   ├── workspace-governance.py        # 6-gate governance audit & drift detector
│   ├── new-project.sh                 # Scaffolds new projects from schema & templates
│   ├── render.sh                      # Single-command render and mux builder
│   ├── validate-research.py           # Research schema validator (Draft-07)
│   └── ingest-asset.sh                # Normalizer for external stock/AI video
├── catalogue/                         # Workspace component capability registry
│   ├── schemas/                       # JSON schemas for tools, libraries, recipes, effects
│   ├── data/                          # Registered component definitions
│   └── index.json                     # Precomputed lookup index
├── .agents/skills/                    # Workspace agent skills
│   ├── workspace-steward/             # Governance, placement policy & audit
│   ├── technical-researcher/          # Stage 0 research dossiers & schema validation
│   ├── motion-library-guide/          # Capability catalogue search & recipe curation
│   ├── motion-graphics-designer/      # SVG/GSAP 3 motion graphics design system
│   ├── voice-director/                # Kokoro voice synthesis & phonetics
│   ├── real-sfx/                      # Sound design & frame-accurate cue mixing
│   ├── earshot/                       # Acoustic listening, critique & procedural SFX
│   └── video-assembler/               # Low-memory rendering, multiplexing & QA
├── tools/                             # Local vendored toolsets (git submodules)
│   ├── earshot/                       # Leonxlnx/earshot (v0.4.0)
│   └── clipwing-skills/               # Clipwing/skills
├── assets/
│   ├── audio/sfx/                     # Openverse / CC0 downloaded sound library
│   ├── images/                        # Vector and raster graphic assets
│   └── generated/                     # Normalized external video clips
├── logs/                              # Pipeline execution logs (ephemeral)
└── tests/                             # Independent test suite & smoke tests
```

---

## Workspace Governance & Stewardship

This workspace enforces the **7-Domain Placement Policy** documented in `.agents/skills/workspace-steward/references/component-placement-policy.md`. Every component in active use is registered under `catalogue/data/` conforming to strict schemas:

```bash
# Validate workspace governance & verify all 6 gates:
python3 scripts/workspace-governance.py

# Search the capability catalogue for approved animation recipes:
python3 scripts/motion-catalogue.py search "glow"
python3 scripts/motion-catalogue.py inspect recipe-backpropagation-flow
```

### Zero Secrets Rule
No API keys, access tokens, private keys, or machine-specific credentials are ever committed to source code or catalogue files. All authenticated external services read credentials dynamically from local environment variables or the macOS Keychain.

---

## Quickstart & Commands

### 1. Initialize Submodules & Virtual Environment
```bash
# Initialize vendored tool submodules:
git submodule update --init --recursive

# Activate Python 3.12 virtual environment:
source .venv/bin/activate
pip install -e tools/earshot
```

### 2. Scaffold a New Project
```bash
./scripts/new-project.sh <project-slug> ["Canonical Title"]

# Example:
./scripts/new-project.sh quantum-computing-qubits "How Do Qubits Compute in Superposition?"
```

### 3. Validate Research Dossier
```bash
python3 scripts/validate-research.py projects/<project-slug>
```

### 4. Synthesize Narration Audio & Timeline
```bash
# Default pacing (1.15x speed, voice: am_adam):
python3 scripts/build-audio.py <project-slug>

# Custom override:
python3 scripts/build-audio.py <project-slug> --voice af_bella --speed 1.20
```

### 5. Sourcing Sound Effects with Openverse
```bash
# Search and download CC0/CC BY sound effects with attribution:
python3 scripts/sfx-openverse.py "whoosh fast" --limit 5 --download --out-dir assets/audio/sfx
```

### 6. Synthesizing Procedural Micro-SFX with Earshot
```bash
.venv/bin/earshot sfx render click/thock -o assets/audio/sfx/thock.wav
```

### 7. Full-Lifecycle Build (Stages 0 → 9)
```bash
./scripts/build-project.sh <project-slug>
```
Renders visuals with HyperFrames, extracts visual foley cues, mixes multi-track audio, multiplexes streams via FFmpeg, and verifies all 5 Stage 9 QA gates. Output is placed in `out/<project-slug>.mp4`.

### 8. Batch Portfolio Build & QA Audit
```bash
./scripts/build-all.sh
```

---

## Hardware & Memory Management

This pipeline is specifically engineered for Apple Silicon (macOS, Apple M2, 8 GB RAM):
- **Single-Worker Rendering:** `hyperframes render` is pinned to `--low-memory-mode` to prevent Chrome worker explosions.
- **Decoupled Assembly:** Video rendering is strictly decoupled from audio synthesis. Stream multiplexing uses FFmpeg copy mode (`-c:v copy`), completing in under one second.
- **Hardware Acceleration:** Chromium uses `--use-angle=metal` and `--enable-gpu-rasterization` for smooth SVG rendering without CPU bottlenecking.
- **Deterministic Math:** Compositions strictly use seeded PRNGs (`mulberry32`) instead of non-deterministic `Math.random()`.

---

## Showcase Portfolio

The repository includes three production explainers demonstrating diverse technical domains:

1. **Benchmark: Neural Network Learning & Gradient Descent** (`projects/benchmark-neural-network`)
   - Visualizes multi-layer forward propagation, loss surface computation, and backpropagation weight adjustments.
2. **Distributed Consensus: The Raft Algorithm** (`projects/distributed-consensus-raft`)
   - Visualizes leader election, heartbeat broadcasts, RPC request handling, and split-brain resolution.
3. **Storage Engine Geometry: B-Tree Database Indexing** (`projects/btree-database-indexing`)
   - Visualizes balanced search trees, branch factor traversal, page splits, and logarithmic query bounds.

To view the portfolio gallery with poster thumbnails and research briefs, open `out/index.html` in your browser.

---

## Credits & Licensing

### Upstream Open Source Acknowledgments

| Tool / Component | Creator / Maintainer | Upstream Repository | License |
|---|---|---|---|
| **Kokoro TTS** | hexgrad | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache-2.0 |
| **Misaki G2P** | hexgrad | [hexgrad/misaki](https://github.com/hexgrad/misaki) | Apache-2.0 |
| **eSpeak NG** | eSpeak NG Team | [espeak-ng/espeak-ng](https://github.com/espeak-ng/espeak-ng) | GPLv3 |
| **HyperFrames** | HyperFrames Team | [hyperframes.dev](https://hyperframes.dev) | MIT / CLI |
| **GSAP 3** | GreenSock / Webflow | [greensock.com](https://gsap.com) | GreenSock Standard |
| **Earshot** | Leon (@Leonxlnx) | [Leonxlnx/earshot](https://github.com/Leonxlnx/earshot) | MIT |
| **Clipwing Skills** | Clipwing Team | [Clipwing/skills](https://github.com/Clipwing/skills) | MIT |
| **Openverse** | WordPress Foundation | [openverse.org](https://openverse.org) | Open Source / CC |
| **FFmpeg** | FFmpeg Developers | [ffmpeg.org](https://ffmpeg.org) | LGPLv2.1+ / GPLv2+ |
| **Three.js** | Mr.doob & Contributors | [mrdoob/three.js](https://github.com/mrdoob/three.js) | MIT |
| **Anime.js** | Julian Garnier | [juliangarnier/anime](https://github.com/juliangarnier/anime) | MIT |
| **SoundFile** | Bastian Bechtold | [bastibe/python-soundfile](https://github.com/bastibe/python-soundfile) | BSD 3-Clause |
| **SciPy** | SciPy Developers | [scipy.org](https://scipy.org) | BSD 3-Clause |
| **NumPy** | NumPy Developers | [numpy.org](https://numpy.org) | BSD 3-Clause |
| **jsonschema** | Julian Berman | [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) | MIT |

### Project License
Motion Lab pipeline source code, scripts, agent skills, and architecture documentation are distributed under the **MIT License**.
