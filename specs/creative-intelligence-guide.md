# Creative Intelligence Layer: Operator's Guide

How to use what was added on top of the studio. The design rationale and audit are in `creative-intelligence-architecture.md`; what was built, tested and measured is in `creative-intelligence-report.md`. Everything here is optional: a project without these files behaves exactly as before.

## 1. Production workflow

```
brief.json -> [research.json] -> beatmap.json -> (kb retrieval) -> bake-off -> design-profile.json
   -> storyboard.json -> audio (Kokoro) -> assets -> src/index.html -> validate -> render -> motion QA -> critique -> revise -> final
```

| Step | Command | Writes |
| --- | --- | --- |
| scaffold | `python scripts/studio.py new <slug> --template illustrated-explainer --style <style> --formats landscape` | project folder |
| arc and beats | `python scripts/beatmap.py arcs` / `init <slug> --arc <id>` / `validate <slug>` | `beatmap.json` |
| retrieve | `python scripts/design-dna.py kb for-beat <beatmap> <beat>`; `kb query --facet camera=push --support native` | stdout (index in untracked `reference/design-kb/`) |
| bake-off | `python scripts/bakeoff.py run <slug> --beat beat.json --profiles a,b,c --reason "..."` then `decide` | `bakeoff/` (record, stills, sheet), `design-profile.json` |
| timing | `python scripts/beatmap.py storyboard <slug>` (after `build-audio.py`) | `storyboard.json` |
| assets | `python scripts/assets.py procedural|import|generate ...`, `approve`, `export <slug> <ids>` | `assets/library/`, `<slug>/src/assets/` |
| check | `python scripts/studio.py validate <slug>` | checks every file above |
| QA | `python scripts/motion-qa.py composition <slug>`, then after a build `... project <slug>` | `qa/motion/` |
| revise | `python scripts/scene-revise.py <slug> --scene s3` | spliced `renders/<format>/visuals.mp4` |

Heavy commands (render, browser, TTS) take the `session-guard.py` lock themselves or must be run under it: `python scripts/session-guard.py run --slug <slug> render -- <command>`. Use `.venv/bin/python` for anything touching images, `python3.12` for `studio.py` and `build-audio.py`. Narration speed is read from `research.json` `acoustic_guidance.speech_rate`, and falls back to 1.15x if the dossier does not exist yet: write the dossier first.

## 2. Data contracts

| File | Spec | Notes |
| --- | --- | --- |
| design profile | `catalogue/schemas/design-profile.schema.json` | three dimensions plus camera, transitions, audio, rendering, provenance, scene variants. Every leaf is a **fact** `{value, basis, confidence, evidence}`; `basis` is `measured` (needs `evidence`), `inferred`, `subjective`, `prescribed` (registry rules only) or `unknown` (no numbers allowed) |
| beat map | `specs/beatmap-spec.json` | concept, arc, beats with optional shots, transitions (with motivation), audio intent, asset needs and strategy, claims with sources, declared `intent` |
| narrative arcs | `specs/narrative-arcs.json` | 12 arcs; add one by appending an entry |
| motion vocabulary | `specs/motion-vocabulary.json` | 28 entries with GSAP ease, duration range, use/avoid, evidence class |
| asset, job, capabilities | `specs/asset-spec.json` | no credential ever appears; only the env-var name |
| QA report | `specs/qa-report-spec.json` | objective / measured / judgment, waivers, skipped checks with reasons |
| bake-off | `specs/bakeoff-spec.json` | candidates, measured distinctness with a re-skin control, scores, decision |

## 3. Style registry

A style is a **style record** (`catalogue/data/styles/<id>.json`, tokens) plus its stylesheet (`src/studio/styles/<id>.css`), plus a **design profile** (`catalogue/data/design-profiles/<id>.json`, the DNA). Nine registry profiles exist (paper collage, cinematic documentary, Swiss, 2D illustrated, 3D scientific, archival, abstract geometric, data journalism, experimental mixed media) on ten styles. Fourteen *extracted* profiles describe the reference videos, with measured palettes and rhythm and the reference analyst's notes bridged as `inferred`/`subjective`. **Adding a style needs no engine change:** write the CSS, the style record and the profile; `python scripts/motion-catalogue.py validate` checks schema, provenance rules and cross-references. A profile's `archetype` names a composition archetype (`src/pipeline/archetypes.py`); adding an archetype is one function plus a registry entry. Each profile lists its `weaknesses`.

## 4. Reference ingestion

Unchanged: `reference-analyst` and `scripts/reference-corpus.py` write source and technique records. New: `python scripts/design-dna.py extract <video|image> --id x-ref-<hash> --register` measures the file and writes an extracted profile and its measurement file; if the file hash matches a source record, the analyst's observed/interpreted notes are bridged into facts. Qualitative fields stay `unknown` without an analyst note. Never commit frames or contact sheets (`reference/design-dna/` is ignored).

## 5. Style bake-off

Compare structure, not colour. Candidates are rendered from the same beat through different archetypes; the tool re-renders the first archetype in another style as a control and reports the layout distance between every pair against 1.5x the control. If any pair is below that, the candidates were re-skins and the run exits non-zero. Metrics are evidence; the decision (with scores, rationale and who decided) is yours. Stills undersell camera-led directions; use `--motion` for short samples (implemented, not exercised in this work).

## 6. Provider integration and secrets

Providers declare capabilities (tasks, aspect ratios, resolutions, durations, reference-image limits, auth, rate limits, verification level) from documented facts only. Default providers: `procedural` and `import` (no credential), `kie` (partial verification, needs `KIE_API_KEY`). To add one: subclass `base.Provider`, register it in `providers/__init__.py`, add a stub-server contract test. Credentials: **environment variables only** (`export KIE_API_KEY=...` in your shell or your OpenClaw secret mechanism). They are never written to files, prompts, logs or browser storage; `secrets.redact` runs on every job and asset record; keys are sent only to the API host, never to result CDNs. Do not run a live job without a key you chose to supply and a look at the provider's current pricing.

## 7. QA and critique

`motion-qa.py` separates **objective** failures (the file is wrong), **measured** leads (numbers with thresholds) and **judgment** questions (for a critic). It never writes a creative pass. Declare intent (`still`, `minimal`, `dark`) or capability (`frame-hud`, `progress-stepper`, `caption-band`) to turn a finding into a visible waiver. `technical_pass` only means no objective failure and every required check ran. The critique pack (`scene-sheet.jpg`, `seams.jpg`, `critique.template.json`) is for a human or model to fill after looking and listening. Score `qa/creative-review.json` with evidence and reasons; see `.claude/skills/motion-director/SKILL.md`.

## 8. Dependencies and install

Added: nothing new to the project. `jsonschema` (already declared in `pyproject.toml`) was installed into `.venv`. Browser probing reuses `puppeteer-core` and the cached Chrome that ship with the global `hyperframes` install (no Playwright was installed; `scripts/frame-review.py` therefore still cannot run on this host). Pillow, NumPy, SciPy are already in `.venv`. Rollback: delete the files listed in the report's section 12 and revert the small edits to `scripts/motion-catalogue.py`, `scripts/studio.py`, `specs/storyboard-spec.json`, `specs/research-spec.json`, `.gitignore`.

## 9. Resource notes (Apple M2, 8 GB; one job at a time)

Typical peaks measured here: colour/motion extraction of a 15 s video 128 MB; four-candidate bake-off 300 MB; DOM probe 107 MB; motion QA on a finished film 170 MB; scene revision 403 MB; a full 45-50 s 720p30 build 620-830 MB at about 1.6-1.9 s of wall time per second of film; Kokoro 1.4 GB. Nothing runs local generative inference.

## 10. Known limitations

No live generation provider has been exercised; procedural plates are stylised, not photographic; audio was measured, not listened to; contrast over images is not estimated; several QA thresholds are calibrated on a handful of stretches and are starting values; the bake-off cannot show motion in stills; `audio-cut-alignment` is not implemented. See the report for the full list.
