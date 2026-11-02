# Creative Intelligence Layer: Implementation Report

Written 2026-11-02 on the M2 render host. Companion files: `creative-intelligence-architecture.md` (audit and design decisions, written before implementation) and `creative-intelligence-guide.md` (how to operate it). Nothing here claims a result that was not produced on this host. Where something is specified but not exercised, it says so.

## 1. What was already present

A studio with brief, research, storyboard, runtime, QA and a catalogue; five styles; 14 reference sources and 42 technique records; Kokoro narration, SFX sourcing and a three-track mux; `frame-review.py`; a creative-review rubric; session locks; a manual Veo import path. Full inventory and gap analysis: architecture doc sections 1.3-1.5. Two premises of the brief did not match the repository: **Revideo is installed but unused** (a prior report rejected it; HyperFrames + GSAP is the renderer), and **OpenClaw lives outside the repo** (`~/.openclaw`; its "Builder" is the generic `forge` agent). I kept HyperFrames, made no change to `~/.openclaw`, and encoded orchestration as skills, CLIs and JSON files any agent can run.

## 2. What was adopted from each repository

| Repository | Adopted (reimplemented, nothing copied) |
| --- | --- |
| **Open-Higgsfield-AI** | The *shape* of per-model capability fields (aspect ratios, resolutions, durations, reference-image limits) as our provider `capabilities`; asynchronous submit / poll / download lifecycle. |
| **design-dna** | The deterministic measure -> record -> verify loop (stratified sampling, farthest-point k-means, perceptual merging, coverage, pass thresholds), ported to Python on Pillow/NumPy; CIEDE2000 added and checked against published test vectors. |
| **Vox generator** | The arc library (6 arcs adapted among our 12), beat + shot decomposition, hook/cadence guidance as conventions, the provider interface shape, the idea of a style bake-off. |
| **Motionmaxxing** | Gate-as-question-with-numbers design, frozen-stretch / flat-frame / end-hold ideas, "describe the frame before judging", mandatory evidence, handoff and cut-on-motion as *options* in the motion vocabulary, a QA report that never self-certifies. |

## 3. What was deliberately not adopted

- **Open-Higgsfield UI, its "200+ models" as a promise, localStorage keys, substring model routing.** Its poller also has two bugs (a lower-cased state compared to `'FAILED'`; a thrown failure swallowed so polling continues to timeout). Its "cinema" controls are prompt-text substitutions, not model parameters.
- **Vox's bake-off.** It re-skins one prompt template for one model: the failure mode the brief describes. Replaced by structurally different archetypes with a measured re-skin control. Its job runner never resets its stall clock on progress and so re-submits slow jobs (double billing); ours polls an existing remote id and never re-submits it.
- **design-dna's "every field populated, no empty strings" rule** (it forces fabrication) and its web-UI schema. Ours tags every value measured / inferred / subjective / prescribed / unknown.
- **Motionmaxxing's "never ship" list as law** (kickers, counters, labels, stillness, end cards are legitimate in explainers), "almost nothing fades", and its numeric curves, which come from a private corpus I could not reproduce. They appear in the motion vocabulary labelled `adopted-unverified`.
- **MuAPI adapter.** Its docs host does not resolve and no primary source was found, so no adapter was written (brief: verify first).
- **Revideo, OpenClaw changes, local generative inference, new agents.**

## 4. What was implemented (and what exists only on paper)

Implemented and exercised: design-profile schema, nine registry profiles on ten styles (five new style systems), 14 extracted reference profiles with analyst-note bridging, faceted knowledge-base retrieval; beat-map schema, 12-arc library, planner and storyboard derivation; structural bake-off (9 archetypes, distinctness with control, decision record, derived project profile); asset engine (interface, secrets redaction, library, jobs with bounded retry / timeout / resume / fallback / reuse, providers `procedural` (7 recipes), `import`, `mock`, `kie`); motion vocabulary (28 entries); motion QA (video, composition via a DOM probe, critique pack) with a unified report schema; scene-level revision; `studio.py validate/status` integration; three skills; ten catalogue records; 54 tests.

Specified or partial, **not** exercised: the bake-off `--motion` samples (written, never run); `audio-cut-alignment` (reported as skipped); live `kie` generation (stub only); image-edit, upscaling, video-extend and lip-sync *tasks* exist in the schema enum but no adapter implements them; provider-based music generation (the demos use an original synthesized bed); portrait/square demo formats (landscape only); the Veo path remains manual import.

## 5. What was tested, and 6. actual results

| Suite | Result |
| --- | --- |
| `tests/test-creative-intelligence.py` (new, `.venv/bin/python`) | **54 tests OK** in 13.5 s: CIEDE2000 vs published vectors, palette recovery, profile provenance rules (5 negative cases), beat-map planning checks, engine retry/timeout/resume/fallback/isolation/reuse, kie against a stub (documented in-body error codes, key not sent to the CDN, redaction), QA on synthetic media with known ground truth (true black, designed darkness, frozen vs drifting, repeated layouts, waivers), DOM-probe text findings and false-positive guards, `studio.py validate` hook with a deliberately broken beat map and profile |
| `test-motion-catalogue` / `test-workspace-governance` / `test-motion-primitives` / `test-studio` | 16 / 15 / 8 / 21 OK |
| `test-reference-corpus` | 24 OK, 1 skipped with `.venv/bin/python`. With `python3.12` it errors on a missing Pillow (environmental; present before this work) |
| `test-studio-runtime` | exit 0, 2 skipped (no Playwright on this host) |
| `test-audio-stack` | **exit 1** in the real-SFX step ("Extracted 0 animation moments"). Not run before my changes; the file is being edited by the concurrent `.agents` -> `.claude` skills migration. Not investigated further; unresolved |
| `motion-catalogue.py validate`, `workspace-governance.py` | PASS (all 7 gates) after registering the new components |
| `studio.py validate` on every non-archived project | all PASS |
| Legacy path | `studio.py build <legacy> --dry-run` still delegates to `build-project.sh`; `bash -n` clean on all shell scripts |

**Validation against real evidence (non-circular).** Run on the archived `china-market-crash/v3` composition, the DOM check reproduced the font sizes that a prior report measured by hand (7.9, 8.6, 10.8, 11.5, 13.0, 15.8 px), found the repeated dashboard-card layout and a caption sitting over HUD labels (confirmed by looking at the frame), and the video check quantified its "near freezes" as holds of 8.5, 4.8 and 4.9 s. **The baseline/directed comparison below is circular by construction** (I built the baseline to show the patterns); it shows what the tool detects, not that it measures quality.

## 7. Demonstration projects

| Project | Direction | Output | Final QA | Creative review (agent) |
| --- | --- | --- | --- | --- |
| `projects/great-fire-london-collage` (44.6 s) | editorial paper collage; five beats; four distinct transitions incl. a match-cut | `out/great-fire-london-collage-landscape.mp4` | 0 objective, 0 measured, 2 waivers (`intent: minimal`); loudness -16.4 LUFS | 11 criteria at 4, colour_and_style 3: mean 3.92 |
| `projects/ocean-descent-documentary` (49.5 s) | cinematic documentary descent; depth gauge, pressure lines, 100-dot pictogram where 76 dots ignite on 76 synchronised bells | `out/ocean-descent-documentary-landscape.mp4` | 0 objective, 4 measured (low content coverage, accepted and not waived), 3 waivers (`minimal`, `dark`); loudness -17.8 LUFS (inside the +/-2 LU tolerance, at its edge) | 10 at 4, readability 3, composition 3: mean 3.83 |
| `projects/motion-quality-v1-baseline` / `v2-directed` (14 s, silent) | the same binary-search content as a template baseline and as a directed piece | `out/motion-quality-*-landscape.mp4` | baseline **39 measured findings** (sub-floor type, HUD corners, step counters, card pile, repeated layout and composition, low occupancy, contrast); directed **0 live, 1 waiver** | not scored |

All three were built with `studio.py build` (validate, lint, render, three-track mux, five QA gates), each defect found by looking at frames, then fixed and re-rendered. The review files state that **the films were not listened to or watched end to end by a person**: sound design (a bed per depth zone; foley; bells exactly on the dots) was verified by measurement only. Both reviews are an agent's critique, not user acceptance.

**Content provenance.** Facts trace to `research.json` per project. Great Fire: houses 13,200-13,500, churches 86 or 87, death toll presented as disputed (traditional figure six), Act of 1666, Monument 202 ft, all from Wikipedia (citing Tinniswood, Porter, Field, Hanson) and themonument.org.uk; Britannica returned 403; the cited books were not read. Ocean: NOAA pages for zones, colour and pressure; the 76% figure verified from the Europe PMC record of Martini & Haddock 2017 (the nature.com page needed a login and the Smithsonian copy returned 403, so the full text was not read). Claims I could not verify (the Monument's height equalling its distance from the bakery; a depth at which red disappears; a share of the City destroyed) are explicitly not made. **No generated imagery exists in these films**: plates are procedural and stylised, and the generated-asset path was verified only through procedural/import/mock providers and the kie stub.

## 8. Performance observations (single jobs, this host, `/usr/bin/time -l`)

| Task | Wall | Peak RSS |
| --- | --- | --- |
| design-dna extract, 15 s 720p60 video | 9.6 s | 128 MB |
| bake-off, 4 candidates (+ control) | 12 s | 300 MB |
| DOM probe, 2 samples | 2.4 s | 107 MB |
| motion QA, finished 45 s film | 10 s | 170 MB |
| Kokoro, 43 s of speech | 18 s | 1.44 GB |
| full studio build, 44.6 s / 49.5 s landscape 720p30 | 86 s / 79 s | 619 MB / 833 MB |
| scene revision (43% of a 14 s film) | 19 s | 403 MB |

The whole build (validate, lint, render, mux, QA) took about 1.6-1.9 s of wall time per second of film. Nothing was run concurrently with a render. `build-audio.py` takes speech rate from `research.json`; if the dossier does not exist yet it silently uses 1.15x (this cost one wrong 38 s synthesis before I noticed). Installing nothing new: `jsonschema` (declared in `pyproject.toml`) was added to `.venv`.

## 9. Defects the process found in its own tools (all fixed, all with tests)

The structure metric first measured palette (a re-skin scored 0.10): replaced by a palette-invariant ink map with a border-median background. Full-frame texture images saturated the occupancy grid. Contrast was "estimated" against the page behind an image (now declines). Line-box overlaps were reported as collisions (now ink boxes). A deliberately dark plate was an *objective* failure (now true black only; designed darkness is a measured lead with an `intent: dark` waiver). Slow drift was called a hold (now frozen vs alive by 0.5 s change). Unknown narration downgraded an 8.5 s hold to a note. The same discipline caught my own compositions: missing assets (HyperFrames serves only `src/`), stamps over text, clipped labels, an empty match-cut, a depth gauge contradicting its label.

## 10. Remaining limitations

1. No live provider has been exercised; `kie` create path and per-model inputs are unverified; no prices are claimed; MuAPI has no adapter.
2. Procedural plates are not photographs; the "cinematic" and "archival" profiles cannot reach their full intent without real or generated imagery.
3. Audio was never auditioned; `audio-cut-alignment` does not exist; Earshot reported -13.4 LUFS on demo A while ffmpeg's EBU R128 reported -16.4 (different methods; not reconciled).
4. QA thresholds are starting values calibrated on a handful of stretches (3 frozen, 4 drifting, 3 re-skin controls); contrast over images is unmeasured; occupancy flagged four Ocean scenes that I judged to be the style's negative space and left visible.
5. Bake-off stills cannot show motion; a bake-off judged on a still favours poster-like looks.
6. `frame-review.py` cannot run here (no Playwright); the DOM probe and `hyperframes snapshot` stood in. The research-spec's `spatial_anchor` and `color_token` enums remain tied to the old dark-tech palette (I only extended the archetype list).
7. Extracted profiles' qualitative facts are the reference analyst's notes re-labelled, from one pass on 14 clips; they are descriptive, not statistical. Keyword-derived KB facets over-match.
8. The agent critique scored its own work; its value is the list of defects, not the numbers.
9. `test-audio-stack` fails (section 6) and is unresolved.

## 11. Recommended next improvements

Run the demos past a person with sound on. Give `kie` one supervised live job after verifying the create docs, or write a verified adapter for whichever provider you will pay for. Add an onset detector (`hyperframes audio`) for cut/sound alignment. Source real period or photographic plates for the archival and cinematic profiles. Exercise `bakeoff --motion`. Install Playwright (or point `frame-review.py` at the cached Chrome) so the existing frame review runs. Calibrate QA thresholds on more finished films, and promote components to `approved` only after a repeat render-host trail. Reconcile the two loudness meters. Make portrait and square versions of the demos.

## 12. Inventory and rollback

Added: `scripts/{design-dna,beatmap,bakeoff,assets,motion-qa,scene-revise}.py`, `scripts/dom-probe.mjs`; `src/pipeline/{colorscience,profiles,videoscan,archetypes}.py`, `src/pipeline/assets/` (base, secrets, store, engine, 4 providers); `catalogue/schemas/design-profile.schema.json`; `catalogue/data/design-profiles/` (9 registry, 14 extracted, 14 measurement files); 5 style records and stylesheets; 6 tool, 3 skill and 1 integration record; `specs/{beatmap-spec,asset-spec,qa-report-spec,bakeoff-spec,narrative-arcs,motion-vocabulary}.json`; three docs in `specs/`; `.claude/skills/{creative-director,asset-engine,motion-director}/`; `tests/test-creative-intelligence.py`; four projects; `assets/library/` index and jobs. Modified (small, additive): `scripts/motion-catalogue.py` (one collection plus a semantic hook), `scripts/studio.py` (optional-artefact checks, status rows), `specs/storyboard-spec.json` (optional scene fields), `specs/research-spec.json` (six extra archetypes), `.gitignore`. To roll back: delete the added paths and revert those five files; no existing behaviour depends on them.
