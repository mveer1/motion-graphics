# Creative Intelligence Layer: Audit, Architecture and Roadmap

**Phase 0 deliverable.** Written before any implementation, on the Mac render host (M2, 8 GB), 2026-11-02. Sections 1-3 are findings; sections 4-7 are decisions. Implementation status and test results live in `specs/creative-intelligence-report.md`, not here: this file never claims something is built.

## 1. Audit of the existing workspace

### 1.1 Corrections to the brief's assumptions

| Brief says | What the host shows | Decision |
| --- | --- | --- |
| Production stack is Revideo / Motion Canvas | Revideo CLI 0.11.0 is installed globally but wired into nothing. The whole studio is HyperFrames + GSAP + the `src/studio/` runtime. `specs/motion-graphics-evolution-report.md` section 5.2 already evaluated and rejected adopting it. | Keep HyperFrames as the renderer. Revideo stays out. The "programmatic" asset class means HyperFrames/GSAP/SVG/Canvas compositions. |
| OpenClaw agents orchestrate; "Builder" is the production orchestrator | OpenClaw 2026.10.9 is installed (`~/.openclaw`). "Builder" is the identity of the generic `forge` software-engineering agent and has no motion-graphics configuration. This repo's `AGENTS.md` declares Claude Code the owner. | No change to `~/.openclaw`. The orchestration contract is encoded in repo-local skills, CLIs and JSON artifacts that any agent (Claude Code or Builder) can execute. No new agents. |
| "Existing 14 visual references" | 14 source records + 42 technique records are in the catalogue; the 14 videos are `~/Downloads/play_720p*.mp4`, outside the repo. | Build the knowledge layer on those records. |
| Playwright-based frame review is the preview QA | Neither Python environment has `playwright`; `python3.12` also lacks Pillow. `tests/test-reference-corpus.py` fails on `python3.12` (no PIL). | Environmental, not a regression. Use `.venv/bin/python` for anything needing Pillow/SciPy. Playwright is an explicit decision in section 6. |

### 1.2 Current pipeline

```
brief.json (Stage 0)  ->  [research.json, Stage 0R, only if factual]
   -> storyboard.json (Stage 1, timed scenes)  ->  narration.json (Stage 2)
   -> Kokoro audio + timeline.json (Stage 3)   ->  src/index.html on src/_studio runtime (Stage 4)
   -> SFX / bed (4B)  ->  studio.py validate + frame-review.py (Stage 5)
   -> hyperframes render per format (Stage 6)  ->  ffmpeg amix (Stage 8)
   -> run-qa-gates.sh + creative-review.json (Stage 9)
```

Two tracks share it: studio projects (`project.json`) and legacy explainers (`build-project.sh`). Both delegate to each other and must keep working.

### 1.3 Feature inventory (what exists)

| Area | Exists | Where |
| --- | --- | --- |
| Creative brief with up to 3 directions + a recorded choice | yes | `specs/brief-spec.json` |
| Scene-level storyboard (purpose, layout per format, capabilities, transitions, audio cues) | yes | `specs/storyboard-spec.json` |
| Research dossier + validator | yes | `specs/research-spec.json`, `validate-research.py` |
| Style registry (record + CSS tokens) | 5 styles | `catalogue/data/styles/`, `src/studio/styles/` |
| Capability catalogue with maturity gates | 14 collections | `catalogue/`, `motion-catalogue.py` (`search`, `recommend`) |
| Reference ingestion, measurement, technique records | 14 sources, 42 techniques | `reference-corpus.py`, `catalogue/data/reference*/` |
| Motion runtime (camera, wipes, match-cut, kinetic type, drawing) | yes | `src/studio/studio-*.js` |
| Multi-format layout | yes | `format-presets.json`, `studio.py formats` |
| TTS, SFX sourcing, ducked mix, loudness gates | yes | `src/pipeline/tts.py`, `sfx-openverse.py`, `video-assembler` |
| Preview QA (clipped text, safe area, contrast, dead stretches) | yes (needs Playwright) | `frame-review.py` |
| Creative review rubric (12 criteria) | yes | `studio.py review` |
| External-footage ingest (manual Veo/Flow download) | yes | `ingest-asset.sh`, `specs/veo-integration.md` |
| Concurrency locks | yes | `session-guard.py`, `.locks/` |

### 1.4 Host capabilities discovered (reuse before building)

HyperFrames 0.8.226 ships tools that overlap with planned work, so they are wrapped, not rebuilt: `compare` (labelled variant sheet: the bake-off sheet), `snapshot` (stills, `--review`), `inspect`/`check` (layout overflow), `measure` (cuts, events, motion energy, ink, look, eases), `audio` (onsets, loudness, silence), `beats`, `grade-compare`. FFmpeg 9 and ffprobe are present.

### 1.5 Duplication and gaps

**Would-be duplicates (do not build):** a second style registry (extend `styles/`); a second planner (extend `brief`/`storyboard`); a second reference store (extend `references/`); a second QA entry point for text/safe-area checks (consume `frame-review` output); a second comparison-sheet renderer (use `hyperframes compare`).

**Real gaps:**

| # | Gap |
| --- | --- |
| G1 | No pre-timing narrative layer: arc, beat purpose, viewer takeaway, emotional progression. `storyboard.json` is already timed and visual-first. |
| G2 | No structured visual-intelligence profile. Styles hold tokens only; no motion grammar, camera/transition language, audio direction, known weaknesses, or measured-vs-inferred provenance. |
| G3 | Bake-off exists only as "1-3 directions in brief.json" (prose). No rendered, comparable treatments of the same beat. |
| G4 | No generated-asset management: no provider abstraction, job lifecycle, asset library, reuse or provenance. Veo is manual import with no record. |
| G5 | No anti-template/repetition detection, no cross-scene composition-repetition check, no objective/measurable/subjective separation in QA output. The prior evolution report found exactly these defects (dashboard cards, hard cuts, undersized type) by manual measurement. |
| G6 | No motion vocabulary with evidence labels. |
| G7 | No per-scene revision path (a full re-render is the only option). |
| G8 | Narration lacks a pronunciation lexicon and explicit pause markup (to be confirmed in section 5). |

## 2. What the four reference repositories actually contain

Read from shallow clones. No third-party code was executed (the harness declined an attempt to import a cloned module, which was correct and unnecessary).

| Repo | Licence on disk | Real content | Verdict |
| --- | --- | --- | --- |
| **Open-Higgsfield-AI** | No LICENSE file; `packages/studio/package.json` says MIT, README says MIT | A browser UI over **one** aggregator (MuAPI) plus a kie.ai client. ~21 curated models in the app registry and ~221 entries in the studio package, with per-model aspect/resolution/duration/max-reference-image fields. "Cinema Studio" camera/lens/aperture are **prompt-text substitutions** (`CAMERA_MAP`), not model parameters. API key lives in `localStorage` (the brief forbids this). Poller bugs: state is lower-cased then compared with `'FAILED'`; a failure thrown inside `try` is swallowed and polling continues to the timeout. Model routing by substring `includes()`. | Adopt: per-model capability *fields* (aspects, resolutions, durations, max reference images) as the shape of our capability record; async submit/poll/download as a lifecycle. Reject: UI, localStorage keys, substring routing, hard-coded model lists, "200+ models" as a guarantee. |
| **design-dna** | MIT (file present) | A skill plus three small scripts. `measure-colors.mjs`: deterministic stratified pixel sampling, farthest-point k-means, CIE76 merge, coverage. `verify.mjs`: re-measure the output and compare (mean dE <= 5, max <= 20, drift <= 0.35). Schema is UI/web oriented. Its rule "every field populated, no empty strings" **forces fabrication**. | Adopt: the measure -> record -> verify loop. Reimplement in Python (Pillow + NumPy already installed; avoids `sharp`). Use dE2000 beside dE76. Reject: web-UI schema and the no-empty-fields rule; ours tags every value measured / inferred / subjective / unknown. |
| **Vox AI Motion Graphics Generator** | README + `package.json` say MIT; **no LICENSE file** | Six narrative arcs, a beat/shot JSON (shot size, camera move from a flat-safe set, element motion), a provider ABC, a submit/poll/retry runner, and `style_bakeoff.py`. The bake-off only swaps a text idiom/palette into the **same prompt template** for the same model: a re-skin, which is exactly what the brief says a bake-off must not be. `run_jobs` never resets its stall clock on progress, so slow jobs are re-submitted (duplicate cost). Hard-wired to MuAPI and Flux/Runway. | Adopt: arc library, hook-in-3s and cut-cadence guidance (as conventions, not laws), beat+shot decomposition, the provider ABC shape. Reject: the bake-off mechanism (replaced by structurally different composition archetypes), the stall/resubmit logic, MuAPI coupling. |
| **Motionmaxxing** | Apache-2.0 (file present); bundles GSAP and Three.js under their own licences | The most substantive. `look.py` (stdlib + ffmpeg: contact sheet, cut detection, frozen stretches, end hold, LUFS, onsets), `lint.mjs` (DOM lint for HUD/deck/vibe-UI rules), 12 craft laws and a 12-item "never ship" list, a motion reference with a measured duration/ease table (50 moments, 4,288 moves) and a 716-row precedent library. The corpus behind the numbers is private. Its own docs say several limits are starting values and that "slop is right when" tables exist. | Adopt: gates as *questions with numbers*, the freeze/end-hold/flat-frame ideas, cut-on-motion and handoff as options, "describe the frame before judging", mandatory evidence note. Reject as hard rules: every "never ship" item (kickers, counters, labels, stillness and end cards are legitimate in explainers), "almost nothing fades", the continuous-motion band as a target. Its numeric curves are **unreproduced here**; we label them `adopted-unverified` until measured on our corpus. |

Licence handling: no third-party source is copied. Patterns are reimplemented from scratch, and `tools/` is untouched. Open-Higgsfield and Vox are treated as idea sources only because their licences are inconsistent on disk.

## 3. Capability matrix

`Native` = exists in this repo; `Wrap` = host tool covers it; `Build` = new work; `External` = needs a paid provider.

| Capability | Status | Plan |
| --- | --- | --- |
| Research, citations | Native | unchanged |
| Narrative arc + beat map | Build | `specs/beatmap-spec.json`, `specs/narrative-arcs.json`, `scripts/beatmap.py` |
| Shot plan | Build (inside beat map) | optional per-beat `shots[]` |
| Design DNA profile + measurement + verify | Build | `catalogue/data/design-profiles/`, `scripts/design-dna.py`, `src/pipeline/colorscience.py` |
| Reference-to-profile bridge | Build on Native | consumes `reference-sources/*` evidence + fresh measurement |
| Style registry | Native, extend | 5 new style records + CSS, 9 profiles |
| Style bake-off | Build + Wrap | `scripts/bakeoff.py` + archetype treatments + `hyperframes compare` |
| Provider abstraction, jobs, library | Build | `src/pipeline/assets/`, `scripts/assets.py` |
| Live image/video generation | External | KIE adapter only (verified in part, section 4.3); no MuAPI adapter |
| Programmatic animation | Native | HyperFrames/GSAP |
| Motion vocabulary | Build (data) | `specs/motion-vocabulary.json` |
| Anti-template lint, repetition, motion QA, evidence report | Build + Wrap | `scripts/motion-qa.py` over `frame-review`, ffmpeg, `hyperframes measure/audio` |
| Narration | Native | Kokoro via `tts.py`; lexicon/pause gaps checked in 5 |
| Per-scene re-render | Build | segment render + splice (G7) |
| Local image/video generation | Not pursued | 8 GB, no GPU |

## 4. Target architecture

### 4.1 Layers and their artefacts

```
brief.json ─► [research] ─► beatmap.json ─────────────┐   narrative concept, arc, beats (+shots)
                  │                                    │
reference KB ─► design-profile.json ◄── bakeoff.json   │   chosen direction + rationale + evidence
 (techniques,        │  (extends a registry profile)   │
  sources)           ▼                                 ▼
              storyboard.json (timed, derived from beats; gains optional beat_id / asset_refs)
                     │
        assets/library (index + media)  ◄── assets.py jobs ◄── providers (procedural, import, kie, mock)
                     │
              src/index.html (HyperFrames/GSAP)  ─► render ─► mux ─► run-qa-gates.sh
                                                         └──► motion-qa.py ─► qa/motion-qa.json ─► critique pack
```

Every new file is optional. A project without `beatmap.json` behaves exactly as today.

### 4.2 Decisions

1. **Style = existing style record (tokens + CSS) + a design profile (DNA).** Profiles are a new catalogue collection `design-profiles`, validated by `motion-catalogue.py validate` and cross-referenced to a style and to technique IDs. Adding a style is a JSON file (and a CSS file); no engine code changes.
2. **Provenance on every non-trivial value.** Profile fields are objects `{value, basis, confidence, evidence}` with `basis` in `measured | inferred | subjective | unknown`. The validator rejects `measured` without an `evidence` pointer and rejects invented precision on `unknown`.
3. **Bake-off compares structure.** Each candidate is a different composition *archetype* (collage stack, Swiss grid, cinematic depth, chart-hero, geometric field) built from the same beat content, rendered as a HyperFrames composition and compared with `hyperframes compare`. Distinctness is measured (layout-map distance, palette distance, text-block count), not asserted. The choice and rationale are written by the director, with the metrics as evidence.
4. **Asset engine is provider-independent and offline-first.** `procedural` (Pillow/NumPy textures, paper, halftone, gradient, geometric fields) and `import` (manual Veo/Flow/stock files) need no credentials. `mock` exercises the lifecycle and failure paths in tests. `kie` is the one live adapter, labelled `verified: partial`. Credentials come from environment variables only and are redacted from logs and job files.
5. **QA separates three classes** in one schema: `objective` (decode failure, wrong size, black frames), `measured` (numbers with thresholds, severity capped at warn unless a hard spec is violated), `judgment` (never pass/fail; emitted as questions for the critic). Findings can be waived only by a declared `intent` (for example `still`, `minimal`) that is itself recorded.
6. **No auto-pass.** `motion-qa.py` exits non-zero only on objective failures; it never writes a "passed creative review".

### 4.3 Provider verification status (2026-11-02)

| Provider | Verified from primary docs | Not verified | Decision |
| --- | --- | --- | --- |
| kie.ai | Bearer auth; errors returned as HTTP 200 with `code`; `GET /api/v1/jobs/recordInfo?taskId=`; states `waiting|queuing|generating|success|fail`; `resultJson` is a JSON **string**; `failCode`, `failMsg`, `costTime`, `creditsConsumed`; 20 creates / 10 s per account; callback optional | Create path and body (`POST /api/v1/jobs/createTask`, `{model, input, callBackUrl?}`) corroborated by Open-Higgsfield's client and a third-party mirror only; per-model input schemas; prices | Adapter written, labelled `partial`. Never run live without a key and explicit approval; contract-tested against a local stub. |
| MuAPI | nothing: `docs.muapi.ai` does not resolve; search found no primary source | everything | **No adapter.** Revisit when its docs can be read. |

### 4.4 Resource policy

All new analysis is streaming (ffmpeg pipes at 96x54 or sampled frames), one process at a time, taken under the existing `session-guard.py` locks when it launches a browser or render. No local inference. Benchmarks record wall time and peak RSS (`/usr/bin/time -l`).

## 5. Dependency inventory (decided up front)

| Item | Needed for | Existing alternative | Decision |
| --- | --- | --- | --- |
| Pillow, NumPy, SciPy | colour measurement, image metrics | present in `.venv` | use, no change |
| `jsonschema` | schema validation | present in `python3.12`, absent in `.venv` | run schema-aware scripts with `python3.12`; image scripts with `.venv/bin/python`. Scripts needing both degrade gracefully or re-exec. |
| Playwright (Python) | `frame-review.py`, DOM probes | none installed here | install into `.venv` only after the rest is built and only if the browser can reuse the cached Chrome; otherwise `hyperframes inspect/snapshot` are the fallback. Recorded in the report either way. |
| Any model SDK / `requests` | KIE adapter | `urllib` stdlib | stdlib only |
| `sharp`, Three.js, any vendored third-party | n/a | n/a | not added |

Rollback for everything: new files are additive; remove the listed paths and the three small edits to `motion-catalogue.py`, `studio.py`, `storyboard-spec.json`.

## 6. Roadmap and migration

| Phase | Output | Backward-compat check |
| --- | --- | --- |
| 1 Contracts | schemas for design profile, beat map, asset, job, QA report, bake-off; provider interface; validators | catalogue + governance + existing tests unchanged |
| 2 Creative intelligence | colour science, `design-dna.py`, arcs, `beatmap.py`, bake-off, 9 profiles, 5 styles | `studio.py validate` on existing projects |
| 3 Asset engine | adapters, jobs, library, reuse, failure isolation, secret redaction | no credentials required anywhere |
| 4 Motion quality | vocabulary, `motion-qa.py`, anti-template lint, critique pack, scene re-render | `frame-review` untouched |
| 5 Integration | `studio.py validate/status` aware of new artefacts; skills; docs; catalogue registration | legacy `build-project.sh` path run |
| 6 Demonstrations | Demo A (paper collage), Demo B (cinematic documentary), motion-quality before/after | existing benchmark projects untouched |

Open risks: no live provider key (generation is verified against a stub and local providers only; this is stated wherever it matters); reference measurements come from 14 clips and are descriptive, not statistical; Kokoro and HyperFrames render timings are measured on this host only.
