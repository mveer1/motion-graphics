---
name: reference-analyst
description: Analyse reference videos into reusable motion-design knowledge. Use when the user supplies reference videos or asks what can be learned from them, to ingest and measure them with scripts/reference-corpus.py, inspect the evidence, write reference-source and technique records (observation separate from interpretation, capability class, provenance, rights), find gaps and keep the knowledge base consistent.
---

# Reference Analyst Skill

Turns a folder of reference videos into reviewed knowledge that projects can search and reuse: one source record per video and one technique record per reusable technique. It learns techniques and principles, never assets.

## Non-negotiables

- **Videos stay outside the repository.** Pass their folder with `--root` or `MOTION_REFERENCE_ROOTS`. Never copy them, their frames or the analysis cache (`out/reference-analysis/`, ignored by git) into tracked folders, assets or projects.
- **No brand identity.** Record logos, wordmarks, mascots, characters, product UI, branded palettes combined with their marks, and exact shot sequences as `rights.brand_assets` with policy `exclude`. Do not trace, recreate or "almost" recreate them. Sources default to `inspiration-only` with unknown licence.
- **Observed is not interpreted.** Every note has `observed` (what is visibly or audibly there, with times), `interpreted` (why it works, what it is for) and `confidence`. Say what the evidence could not establish in `uncertainties`.
- **No claims without evidence.** Do not mark a source `inspected` without having looked at its sheets. Do not set technique `validation` without a test, frame review, demo or render path. Nothing is `approved` without a HyperFrames render on the render host.

## Workflow

```bash
python scripts/reference-corpus.py doctor                                  # needs Edge/Chrome with H.264, or FFmpeg
python scripts/reference-corpus.py ingest "<folder or files>"               # hash, probe, record (renamed copies become aliases)
python scripts/reference-corpus.py analyze --pending --root "<folder>"      # automated evidence, about 0.5x real time
python scripts/reference-corpus.py strip <ref-id> --from 3.2 --to 4.4 --root "<folder>"   # fine strip for a fast move
python scripts/reference-corpus.py status
```

1. **Inspect** `out/reference-analysis/<id>/`: `overview.jpg` (whole piece), `scenes.jpg` (start, middle, end per scene), `transitions.jpg` (+-10 frames around each boundary), `motion.jpg` (most active windows), `audio.png` (envelope, onsets, spectrogram, boundaries) and `frames/`. Cross-check the `automated` block: cut versus soft classification, holds, palette, tempo and `boundary_onset_alignment` (compare `near_onset`/`near_beat` with their chance levels before calling anything beat-synced). Audio is analysed as signal only; say so.
2. **Write the source record** (`catalogue/data/reference-sources/<id>.json`), keeping `media` and `automated` untouched: `name`, `analysis` (state `inspected`, `inspected_on`, `method`, `coverage`, `concept`, `communication_style`, the aspects that matter, `scenes`, `moments`, `difficult`, `uncertainties`), `rights.brand_assets`, `categories` (controlled list in the schema), `tags`, `confidence`, `related`. Protocol and checklists: [`references/analysis-protocol.md`](./references/analysis-protocol.md).
3. **Extract techniques.** For each reusable technique run `python scripts/reference-corpus.py check --name "<candidate>" --text "<one line>"`. Score 0.5 or more means extend that record (add provenance) instead of creating a near-duplicate. New records go in `catalogue/data/references/<id>.json` (`reference.schema.json`) with purpose, visual behaviour, mechanics, parameters, use cases, failure modes, implementation, capability, provenance and related items. Technique IDs must not collide with effect, recipe or composition IDs.
4. **Classify capability** with the decision table in the protocol: `native`, `approximation` (state what is lost), `additional-dependencies` (name the tool and the hand-off path), `resource-constrained` (give the measurement or estimate) or `research-required`. Set `priority.creative_value` and `priority.cost` (1-5) so the backlog sorts.
5. **Link both ways.** The source lists `techniques[{id, timestamps}]`; the technique lists `provenance[{source_id, timestamps, observed}]`. Timestamps must be inside the video.
6. **Validate and report.**

```bash
python scripts/motion-catalogue.py validate          # honesty and link rules for techniques and sources
python scripts/reference-corpus.py report --backlog  # what cannot be done yet, by value and frequency
python scripts/motion-catalogue.py export
```

7. **Hand off implementation** to development (runtime APIs in `src/studio/`, effect/recipe/composition records, a test page or `tests/reference-derived/<name>/`, `frame-review.py`, `tests/reference-derived/benchmark.py`). After a passing test or review, add the evidence path to the technique's `validation` and move `implementation_state` forward; the derived lifecycle then reads tested.

## Using the knowledge base

- Search: `python scripts/motion-catalogue.py search "<intent>" --type technique [--support native] ` and `--type source --category kinetic-typography`.
- Recommend for a brief: `python scripts/motion-catalogue.py recommend --brief projects/<slug>/brief.json [--implemented-only]`. It returns techniques (with lifecycle and support class), the components that implement them, precedents with timestamps, and matching styles.
- In a project brief, cite what was used in `references[].technique_ids`; `studio.py validate` checks the IDs and warns about techniques that are only observed or specified.
- Combine principles from several references into an original direction. A demo or project that is recognisably one reference re-cut is a failure, whatever the validator says.

## Handoffs

- `workspace-steward`: placement, rights questions, registration of new tools or skills, governance.
- `motion-library-guide`: component search and approval states once techniques map to effects, recipes and compositions.
- `motion-graphics-designer`: briefs and compositions that apply the techniques.
