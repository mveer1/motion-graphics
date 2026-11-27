# 09: Learn from the reference videos, batch by batch

For any host (Windows or Mac). Read `00-shared-context.md` first, then this file, then `prompts/state/` (newest
`handoff-*.md` naming the reference corpus, and the tail of `log.md`).

## Mission

To run batches in parallel sessions instead (3 at a time, then 3 more), follow `10-reference-parallel-protocol.md`:
lanes, file ownership, the `staging.json` hand-in and the integrator role.

The owner supplied motion-graphics reference videos to learn from. Analyse them **8 at a time**. For each batch, learn:

- **Transitions:** how scenes change, and how to rebuild each change in our runtime.
- **Animation techniques.**
- **Sound design:** how effects, music and silence land against the picture.
- **Narration:** how its pace changes.
- **Captions:** where captions and on-screen copy sit.

Catalogue it all in the reference knowledge base so the story, visual, caption and sound skills (and the `story-writer`
and `visual-director` agents) use it. Pause after each batch, report, and update the state files.

Owner's words (2026-11-26): "analyse the type of transitions ... catalouge and group them and understand how to recreate
them ... learn from how the sound effects come together in the visuals and how the pace of the narration changes, with
the sound effects and caption placement if applicable ... make our skill files and agents learn from these files and
they should have direct access to our reference material".

## Read first

1. `.claude/skills/reference-analyst/SKILL.md` and `references/analysis-protocol.md`: the workflow, honesty rules, rights.
2. `docs/reference-playbook.md`: the synthesis so far, the **batch table** (which ids are in which batch), the
   motion-spec method, and the generated index (technique families, sound and pace table, transition census).
3. `.claude/skills/earshot/SKILL.md` "Limits" before saying anything about how audio sounds.

## Where things are

- **Videos:** `~/Downloads/motion-references/`, one flat folder with all 64 files: 58 from `~/Downloads/1 (1)/{1..5}/`
  plus 6 earlier originals from `~/Downloads/New folder/`. They stay outside the repository; never copy them, their
  frames or the cache into tracked folders.
- **Records:** sources in `catalogue/data/reference-sources/ref-*.json` (64, ingested), techniques in
  `catalogue/data/references/*.json` (each with a `family`).
- **Evidence (untracked):** `reference/analysis/<ref-id>/` holds `overview.jpg`, `scenes.jpg`, `transitions.jpg`,
  `motion.jpg`, `audio.png`, `listen/listen.jpg`, `listen/words.json` and `strips/`.

## Per batch (PowerShell; the heavy steps take the host lock themselves, so run one at a time)

```powershell
$root = "$env:USERPROFILE\Downloads\motion-references"
$ids = 'ref-...','ref-...'                                   # the batch row in docs/reference-playbook.md
python scripts/reference-corpus.py analyze @ids --root $root  # ~0.5x real time
python scripts/reference-corpus.py listen @ids --root $root   # speech, loudness, accents; ~30 s per film on Windows
python scripts/reference-corpus.py status                     # 'lsn' column
```

1. **Look at every sheet** of every film: `overview.jpg`, `transitions.jpg`, `listen/listen.jpg`, plus `motion.jpg`
   and a 30 fps `strip` where a move is ambiguous. Say in `analysis.method` exactly what you looked at.
2. **Read the listen numbers critically.**
   - `narration: sparse` with 1-3 word phrases is usually dictation noise over music: check the phrase frames.
   - Accents may be part of the music rather than separate effects.
   - Compare every alignment figure with its chance level.
3. **Source record** per film (copy the shape of the batch-1 records, for example
   `catalogue/data/reference-sources/ref-0b13aa7f02.json`):
   - **Aspects:** `transitions`, `sound_design`, `narration` and `captions` always, plus those that matter.
   - **Content:** scenes, at least one moment, uncertainties, and `rights.brand_assets` (logos, mascots, product UI,
     model names: `exclude`).
   - **Metadata:** categories from the controlled list, tags including `batch-N`, and status `experimental`.
   - **Writing:** write the record through the corpus's own writer; never touch `media` or `automated`. The batch-1
     script `prompts/state/reference-corpus-helpers/write_sources_batch1.py` shows the pattern: `load_json`, set
     fields, `validate_source`, `save_json`.
4. **Techniques.**
   - **Check first:** run `python scripts/reference-corpus.py check --name "..." --tags a,b --text "..."` for each
     candidate.
   - **Score 0.5 or more:** add provenance to the existing record. Insert it as text so the hand formatting stays
     (pattern: `prompts/state/reference-corpus-helpers/add_provenance.py`), update `metadata.updated_at`, and set
     `source.inspected: true` if it was false.
   - **New record:** `reference.schema.json` with a `family`, mechanics pinned with the motion-spec method, honest
     capability and lifecycle (`documented` unless a test exists).
   - **Links:** both ways, and timestamps inside the film.
5. **Validate and regenerate.**
   - `python scripts/motion-catalogue.py validate`: PASS, and the warning count no higher than before (27 on
     2026-11-26, all about absent projects).
   - `python tests/test-reference-corpus.py` and `python tests/test-motion-catalogue.py`.
   - `python scripts/reference-corpus.py playbook`, then `playbook --check`.
6. **Update the synthesis** at the top of `docs/reference-playbook.md`.
   - Change the numbers and patterns this batch moved, and the batch table state.
   - When a learning changes how a skill should act, edit that skill's reference section, not its rules wholesale:
     `motion-graphics-designer` section H, `story-writer` input 6, `caption-designer` "Learned from reference videos",
     `real-sfx` taste rules, `voice-director` "Reference pace", `short-form`/`mid-form` pace lines, `motion-director`,
     `creative-director`, and the two agents.
7. **Pause and report** what the batch taught, with numbers. Then append the dated entries to `prompts/state/`
   (`log.md`, `tracker.md`, `decisions-needed.md` if needed, `host-windows.md` for host facts, and a
   `handoff-<date>.md`).

## Priorities for the next batches

- **Batch 2 is mostly long films with likely narration** (`chaotic-ai-point-of-view-reel` 153 s,
  `hand-drawn-stop-motion-explainer`, `handwoven-textiles-brand-explainer`, `connector-tracker-promo`). It is the first
  chance to measure narration pace: words per second while speaking, pause lengths, pace over thirds, cuts in pauses,
  and the gap between a cut and the next phrase. Write the first narration-pace synthesis and decide with evidence
  whether `voice-director`'s 1.15x default and the story-writer's pace map need a change (propose; do not change
  silently).
- **Batches 7-8** run `listen` on the 14 earlier references and re-read their transitions with the new aspects.
- **Development backlog** (hand to development, not this mission): `flash-frame-cut` (candidate `Studio.fx.flash`),
  `container-transform`, `text-scramble-decode` (seeded), `strike-and-correct`, a subject-anchored caption lane. Each
  needs a test page or `tests/reference-derived/<name>/` with `frame-review.py` evidence before its lifecycle moves.

## Host facts (2026-11-26, Windows; re-probe, they change)

- **FFmpeg and HyperFrames:** FFmpeg 9.0.2 (WinGet) and HyperFrames 0.8.226 are on PATH. From Python, call
  `hyperframes.cmd`.
- **No local speech model:** `hyperframes transcribe` reports `whisper_unavailable`. Hugging Face downloads fail on
  this network (TLS revocation check, `CRYPT_E_NO_REVOCATION_CHECK`), so no Parakeet and no earshot CLAP/AST models.
  Do not work around the security control.
- **Fallback recogniser:** `listen` falls back to Windows desktop dictation (System.Speech en-US). It is rough, so
  keep its numbers labelled as such.
- **On the Mac,** with whisper or Parakeet and earshot's models cached, `listen --all --root <folder>` replaces the
  numbers with better ones (queued as an optional Mac item).
- **Rules that still hold:** one heavy job at a time. Never commit or push without the owner. Learn techniques, never
  assets.
