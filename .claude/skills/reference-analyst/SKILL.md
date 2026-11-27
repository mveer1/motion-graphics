---
name: reference-analyst
description: Analyse reference videos into reusable motion-design knowledge. Use when the user supplies reference videos or asks what can be learned from them, to ingest and measure them with scripts/reference-corpus.py, inspect the evidence, write reference-source and technique records (observation separate from interpretation, capability class, provenance, rights), find gaps and keep the knowledge base consistent.
---

# Reference Analyst Skill

Turns a folder of reference videos into reviewed knowledge that projects can search and reuse: one source record per video and one technique record per reusable technique. It learns techniques and principles, never assets.

## Non-negotiables

- **Videos stay outside the repository.** Pass their folder with `--root` or `MOTION_REFERENCE_ROOTS`. Never copy them, their frames or the analysis cache (`reference/analysis/`, ignored by git) into tracked folders, assets or projects. Transcripts from `listen` stay in that cache (`listen/words.json`); records carry speech numbers, never the words.
- **No brand identity.** Record logos, wordmarks, mascots, characters, product UI, branded palettes combined with their marks, and exact shot sequences as `rights.brand_assets` with policy `exclude`. Do not trace, recreate or "almost" recreate them. Sources default to `inspiration-only` with unknown licence.
- **Observed is not interpreted.** Every note has `observed` (what is visibly or audibly there, with times), `interpreted` (why it works, what it is for) and `confidence`. Say what the evidence could not establish in `uncertainties`.
- **No claims without evidence.** Do not mark a source `inspected` without having looked at its sheets. Do not set technique `validation` without a test, frame review, demo or render path. Nothing is `approved` without a HyperFrames render on the render host.

## Workflow

```bash
python scripts/reference-corpus.py doctor                                  # needs Edge/Chrome with H.264, or FFmpeg
python scripts/reference-corpus.py ingest "<folder or files>"               # hash, probe, record (renamed copies become aliases)
python scripts/reference-corpus.py analyze --pending --root "<folder>"      # automated evidence, about 0.5x real time
python scripts/reference-corpus.py listen --pending --root "<folder>"       # speech word times, loudness, accents vs cuts and speech
python scripts/reference-corpus.py strip <ref-id> --from 3.2 --to 4.4 --root "<folder>"   # fine strip for a fast move
python scripts/reference-corpus.py status                                  # 'lsn' column = listen block present
```

The user's corpus lives in one folder outside the repository (`~/Downloads/motion-references`, all 64 files); pass it with `--root`. Work in batches of 8 (the batch table is in `docs/reference-playbook.md`; tag each finished source `batch-N`).

1. **Inspect** `reference/analysis/<id>/`: `overview.jpg` (whole piece), `scenes.jpg` (start, middle, end per scene), `transitions.jpg` (+-10 frames around each boundary), `motion.jpg` (most active windows), `audio.png` (envelope, onsets, spectrogram, boundaries), `listen/listen.jpg` (frames while each phrase is spoken, then on the strongest sound onsets; a grid for portrait) and `frames/`. Cross-check the `automated` block: cut versus soft classification, holds, palette, tempo and `boundary_onset_alignment` (compare `near_onset`/`near_beat` with their chance levels before calling anything beat-synced). Read `automated.listen`: `speech.narration` (narrated, sparse or none: sparse is often recogniser noise over music, so check the phrase frames), words per second, pauses, `boundaries_vs_speech`, accents per minute and `boundaries_with_accent` against its chance level, silences, loudness. Audio is analysed as signal plus local speech recognition only; say so.
2. **Write the source record** (`catalogue/data/reference-sources/<id>.json`), keeping `media` and `automated` untouched: `name`, `analysis` (state `inspected`, `inspected_on`, `method`, `coverage`, `concept`, `communication_style`, the aspects that matter (always `transitions`, `sound_design`, `narration` and `captions` when there is audio or on-screen copy), `scenes`, `moments`, `difficult`, `uncertainties`), `rights.brand_assets`, `categories` (controlled list in the schema), `tags` (include `batch-N`), `confidence`, `related`. Protocol and checklists: [`references/analysis-protocol.md`](./references/analysis-protocol.md).
3. **Extract techniques.** For each reusable technique run `python scripts/reference-corpus.py check --name "<candidate>" --text "<one line>"`. Score 0.5 or more means extend that record (add provenance) instead of creating a near-duplicate. New records go in `catalogue/data/references/<id>.json` (`reference.schema.json`) with a `family` (the playbook's groups), purpose, visual behaviour, mechanics (pin the numbers with the motion-spec method in the playbook), parameters, use cases, failure modes, implementation, capability, provenance and related items. Technique IDs must not collide with effect, recipe or composition IDs.
4. **Classify capability** with the decision table in the protocol: `native`, `approximation` (state what is lost), `additional-dependencies` (name the tool and the hand-off path), `resource-constrained` (give the measurement or estimate) or `research-required`. Set `priority.creative_value` and `priority.cost` (1-5) so the backlog sorts.
5. **Link both ways.** The source lists `techniques[{id, timestamps}]`; the technique lists `provenance[{source_id, timestamps, observed}]`. Timestamps must be inside the video.
6. **Validate and report.**

```bash
python scripts/motion-catalogue.py validate          # honesty and link rules for techniques and sources
python scripts/reference-corpus.py report --backlog  # what cannot be done yet, by value and frequency
python scripts/reference-corpus.py playbook          # regenerate the grouped index in docs/reference-playbook.md
python scripts/motion-catalogue.py export
```

   Then update the hand-written synthesis at the top of `docs/reference-playbook.md` (what the batch changed about transitions, sound, narration pace and captions, with numbers) and the batch table.

7. **Hand off implementation** to development (runtime APIs in `src/studio/`, effect/recipe/composition records, a test page or `tests/reference-derived/<name>/`, `frame-review.py`, `tests/reference-derived/benchmark.py`). After a passing test or review, add the evidence path to the technique's `validation` and move `implementation_state` forward; the derived lifecycle then reads tested.

## Using the knowledge base

- Start from `docs/reference-playbook.md`: techniques grouped by family (four transition families, typography, motion, staging, explanation devices, style, sound design, narration and captions) with how to rebuild each, its runtime API, the reference moments, and per-reference sound, pace and transition tables.
- Search: `python scripts/motion-catalogue.py search "<intent>" --type technique [--support native] ` and `--type source --category kinetic-typography`.
- Recommend for a brief: `python scripts/motion-catalogue.py recommend --brief projects/<slug>/brief.json [--implemented-only]`. It returns techniques (with lifecycle and support class), the components that implement them, precedents with timestamps, and matching styles.
- In a project brief, cite what was used in `references[].technique_ids`; `studio.py validate` checks the IDs and warns about techniques that are only observed or specified.
- Combine principles from several references into an original direction. A demo or project that is recognisably one reference re-cut is a failure, whatever the validator says.

## Handoffs

- `workspace-steward`: placement, rights questions, registration of new tools or skills, governance.
- `motion-library-guide`: component search and approval states once techniques map to effects, recipes and compositions.
- `motion-graphics-designer`: briefs and compositions that apply the techniques.
