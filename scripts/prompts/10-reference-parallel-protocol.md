# 10: Reference corpus in parallel: protocol for 3 + 3 sessions

Shared rules for the parallel run of the reference-corpus mission (`09-reference-corpus-batches.md`). Every session
reads `00-shared-context.md`, `09-reference-corpus-batches.md`, this file, then its own prompt or handoff. Written
2026-11-26 after batch 1.

## Topology

| Wave | Lane | Session | Work | Successor |
| --- | --- | --- | --- | --- |
| 1 | 1 | A | batch-2 (8 films; the first narrated batch, so A writes the narration notes others compare against) | D |
| 1 | 2 | B | batch-3 (8 films) | E |
| 1 | 3 | C | batch-4 (8 films) | F |
| 2 | 1 | D | **integrator**: merges wave-1 staging into the shared knowledge base; `listen` backfill and new aspects for the 14 earlier references; at the end merges E's and F's staging | final report (or a 7th session if E/F are late) |
| 2 | 2 | E | batch-5 (8 films) | D merges |
| 2 | 3 | F | batch-6 (8 films) + the 2 new films of batch-7 (`ref-0b2552b64e`, `ref-b8cf9a12b0`) | D merges |

Batch ids: the batch table in `docs/reference-playbook.md`. Wave 2 starts only when all three wave-1 `DONE` files
exist. Within a wave the three sessions run at the same time.

## Ground rules

1. **One checkout, no worktrees, no commits.**
   - All sessions work in the main checkout: the evidence cache `reference/analysis/` is untracked and lives only
     here, and the 2026-11-26 tooling is not committed.
   - Never `git commit`, `push`, `stash`, `checkout` or `reset` (the owner decides).
2. **Heavy jobs take turns by themselves.** `reference-corpus.py analyze|listen|strip` take the host lock and queue
   first-come-first-served; waiting is normal. Never run them by hand outside the script, and never two at once
   yourself.
3. **Explicit ids only.**
   - Run `analyze <ids>`, `listen <ids>` and `strip <id>` with **your** ids. Never `--pending` or `--all`: they would
     grab another session's films and could overwrite a record it is editing.
   - Finish `analyze` and `listen` on your ids before you write authored analysis into those records.
4. **Write only what you own** (table below). Anything shared goes into your staging file for D.
5. **Honesty.** Look at every sheet you cite; say what you looked at in `analysis.method`. Nothing was listened to:
   dictation and signal features only. A claim without evidence is not written.
6. **Learn techniques, never assets.**
   - Brand marks, mascots, product UI and model names go in `rights.brand_assets` with `exclude`.
   - Transcripts stay in the cache; records carry speech numbers, never the words.

## File ownership

| Path | Wave-1 sessions and E, F | D (integrator) |
| --- | --- | --- |
| `catalogue/data/reference-sources/<your ids>.json` | write (authored blocks only; never `media` or `automated` by hand) | write: adds technique links after merging; owns the 14 earlier records |
| `prompts/state/reference-parallel/batch-N/` (your batch) | write: `staging.json`, `notes.md`, `handoff.md`, `DONE`, `shared-hashes-start.csv` | read all; write `integration/` |
| `reference/analysis/<your ids>/` (untracked cache) | through the tools only | through the tools only |
| `catalogue/data/references/*.json` (techniques) | **read only** | write |
| `docs/reference-playbook.md`, `catalogue/schemas/`, `.claude/skills/`, `.claude/agents/`, `AGENTS.md`, `CLAUDE.md`, `scripts/`, `tests/`, `catalogue/data/tools/` | **read only** | write (playbook, synthesis, skills); scripts/tests only for a bug, with a test |
| `prompts/state/log.md`, `tracker.md`, `decisions-needed.md`, `host-windows.md`, `render-queue.md` | **read only** (concurrent appends clobber each other) | append |

## Writing templates (source record aspects)

Copy the shape of the batch-1 records (`ref-0b13aa7f02`, `ref-a339360a56`) and the writer pattern in
`prompts/state/reference-corpus-helpers/write_sources_batch1.py`.

- **`transitions`.** For each boundary: the time, the family and how it reads, from `transitions.jpg` and a 30 fps
  strip when unsure. Families: cut, grow, cover, continuous. Interpreted: why that transition at that point.
- **`sound_design`.** Write the following, and always state that accents may be part of the music:
  - integrated LUFS, LRA and true peak;
  - tempo and its confidence;
  - accents per minute;
  - accents on cuts against chance (`listen.sound.boundaries_with_accent`) and onsets on cuts against chance
    (`automated.audio.boundary_onset_alignment`);
  - silences, and head and tail levels;
  - what the strongest accents land on, read from the listen sheet.
- **`narration`.** It is one of three cases:
  - **Narrated:**
    - words, words per second while speaking, and words per minute over the speech span;
    - pause count, median and maximum;
    - pace over thirds and the trend;
    - share of cuts in pauses against chance, and the median delay from a cut to the next phrase;
    - the engine (`speech.engine`).
    Confirm on the phrase frames that it is speech.
  - **Sparse:** say whether the phrase frames show real speech or recogniser noise over music.
  - **None.**
- **`captions`.** Lane (top band, mid, lower third, under the subject), lines and words per cue, highlight style
  (colour, weight, box), plate or outline, and when the caption appears against its spoken words (from the phrase
  frames). Or "none; copy is in headlines".
- Also `concept`, `communication_style`, scenes, at least one moment, `difficult`, `uncertainties`, categories (from
  the controlled list), tags including `batch-N`, status `experimental`, and `confidence`.
- `techniques` in a source record lists **existing** technique ids only, with timestamps inside the film. New
  candidates go to staging. Until D merges, `motion-catalogue.py validate` warns "Technique X does not cite reference
  source Y" for your links. That is expected; list them in your handoff.

## `staging.json` (one per batch, UTF-8, valid JSON)

```json
{
  "batch": "batch-3",
  "session": "B",
  "finished_at": "2026-11-26T15:10+05:30",
  "sources": ["ref-..."],
  "provenance_for_existing": [
    {"technique_id": "element-bloom-transition", "source_id": "ref-...", "timestamps": [4.2], "observed": "One sentence of what is seen, with times."}
  ],
  "new_technique_candidates": [
    {
      "proposed_id": "kebab-case-id",
      "family": "transition-cut | transition-grow | transition-cover | transition-continuous | kinetic-typography | motion-character | staging-depth | explanation-device | style-texture | sound-design | narration-captions",
      "name": "Readable name",
      "check": {"top_id": "nearest-existing-id", "score": 0.31},
      "technique": "What it does and why it works (2-3 sentences, generic, no brand).",
      "mechanics": "How to rebuild it: numbers from strips (start, duration, easing, stagger).",
      "timing": "Durations and spacing.",
      "parameters": [{"name": "duration", "description": "...", "default": 0.4}],
      "use_cases": ["..."],
      "failure_modes": ["..."],
      "support": "native | approximation | additional-dependencies | resource-constrained | research-required",
      "runtime_hint": "Existing Studio API or effect id that would implement it, or 'not built'",
      "priority": {"creative_value": 4, "cost": 1},
      "provenance": [{"source_id": "ref-...", "timestamps": [1.2], "observed": "..."}]
    }
  ],
  "synthesis_notes": {"transitions": ["..."], "sound_design": ["..."], "narration": ["..."], "captions": ["..."], "pace": ["..."]},
  "skill_suggestions": [{"skill": "voice-director", "change": "...", "evidence": "ref-... numbers"}],
  "expected_validate_warnings": ["Technique 'x' does not cite reference source 'ref-...' that lists it"],
  "open_questions": ["..."]
}
```

- Run `python scripts/reference-corpus.py check --name ... --tags ... --text ...` for every candidate.
  - Score 0.5 or more: write it under `provenance_for_existing` instead.
  - Also search the other batches' `staging.json` for the same idea (`Select-String -Path
    prompts/state/reference-parallel/*/staging.json -Pattern <word>`). If another batch already proposed it, reuse its
    `proposed_id`.

## Worker acceptance criteria (A, B, C, E, F)

1. `python scripts/reference-corpus.py status` shows every one of your films with `automated` and `lsn yes` (a silent
   film: listen reports no audio track, which is fine).
2. Every film's `overview.jpg`, `transitions.jpg` and `listen/listen.jpg` was opened, plus a strip wherever a
   transition or a narration claim depended on it; `analysis.method` says so.
3. Every source record:
   - is `inspected`;
   - has all the fields above, at least 4 aspects including `transitions` and `sound_design`, and `narration` and
     `captions` whenever there is audio or on-screen copy;
   - lists brand assets or says "No marks seen" in `rights.notes`.
4. `staging.json` parses; every candidate has a `check` result, a family and provenance with in-range timestamps.
5. `python scripts/motion-catalogue.py validate` prints `[PASS]`. The only new warnings are the expected "does not
   cite" ones for your ids, listed in staging.
6. `python tests/test-reference-corpus.py` prints OK. If it fails while reading another batch's file, re-run once:
   a concurrent write may have been mid-flight.
7. **You did not write a shared file.** `git status` cannot show this, because many shared files are already
   modified. Compare SHA-256 snapshots taken at the start and at the end:

   ```powershell
   $shared = 'catalogue\data\references','catalogue\schemas','docs','scripts','tests','.claude','AGENTS.md','CLAUDE.md'
   function Snap { Get-ChildItem $shared -Recurse -File | Where-Object FullName -notmatch '__pycache__' | Get-FileHash | Select-Object Path, Hash }
   Snap | Export-Csv -NoTypeInformation "$dir\shared-hashes-start.csv"                                   # at the start
   Compare-Object (Import-Csv "$dir\shared-hashes-start.csv") (Snap) -Property Path, Hash                 # at the end
   ```

   - **Wave 1:** the comparison must be empty.
   - **Wave 2 (E, F):** D edits shared files at the same time, so changes there are expected. Every changed path must
     be one D owns (techniques, playbook, skills, the 14 earlier source records), and none may be yours.
   - Report anything else; never revert another session's work.
8. `notes.md` holds what the batch taught, with numbers (transitions, sound, narration pace, captions).
9. `handoff.md` holds a paste-ready prompt for your successor (format below), and you also print it in chat.
10. `DONE` exists; its content is one line: ISO time, your session letter, `ok` or `ok-with-issues: <short>`.

## Integrator procedure and acceptance (D)

1. **Wait** until `batch-2/DONE`, `batch-3/DONE` and `batch-4/DONE` exist. Read every staging file, `notes.md` and
   `handoff.md`.
2. **Merge provenance.** For each `provenance_for_existing` entry, append it as text so the hand formatting stays
   (pattern: `prompts/state/reference-corpus-helpers/add_provenance.py`).
3. **Merge new candidates.**
   - Group the same idea across batches (same `proposed_id`, or a mutual `check` score of 0.5 or more after creating
     the first). One record per idea; merge provenance.
   - Write `catalogue/data/references/<id>.json` with `family`, the `reference.schema.json` fields, `documented`
     unless a test exists, and `source.inspected` true.
   - Then add `{id, timestamps}` to each cited source record's `techniques`.
4. **Backfill the 14 earlier references.**
   - Run `python scripts/reference-corpus.py listen <14 ids> --root $root`.
   - Open each `listen/listen.jpg`.
   - Add the `sound_design`, `narration` and `captions` aspects, keeping the existing authored text. Add `batch-0`
     to their tags; leave `inspected_on` and update `metadata.updated_at`.
5. **Regenerate and update.**
   - Run `python scripts/reference-corpus.py playbook`.
   - Update the hand-written synthesis in `docs/reference-playbook.md`: transitions, sound, the **narration and pace**
     section with measured numbers from the narrated references, captions and the batch table.
   - Apply skill suggestions only with evidence, as advisory lines in the skills' reference sections (see `09` step
     6). Bump a rulebook version when its text changes.
6. **Merge wave 2.** When `batch-5/DONE` and `batch-6/DONE` exist, merge them the same way; check every 10 minutes
   for up to 60 minutes after your own work ends.
7. **Acceptance:**
   - `validate` `[PASS]` with warnings no higher than 27 (the 2026-11-26 baseline);
   - no technique record without `family`, provenance and links both ways;
   - `playbook --check` current;
   - `tests/test-reference-corpus.py` and `tests/test-motion-catalogue.py` OK;
   - `status` shows 64 references, all inspected and all `lsn yes` (or D's handoff names what is missing);
   - dated entries appended to `prompts/state/log.md`, `tracker.md`, `decisions-needed.md` (if any) and `host-windows.md`
     (if a host fact changed);
   - a final `prompts/state/handoff-<date>-reference-corpus-final.md`.
8. **If E or F is not done in time,** write `prompts/state/reference-parallel/integration/handoff.md`: a paste-ready
   prompt for one more integrator session with exactly what is left.

## Handoff format (every session)

`handoff.md` contains one fenced block a person can paste into a new session, and it must stand alone:

- **Read first:** `scripts/prompts/00`, `09`, `10`, this batch's `notes.md` and `staging.json`,
  `docs/reference-playbook.md`.
- **Assignment:** the successor's role, exact ids, and what not to touch (the ownership table).
- **What this session learned:** the five most useful findings with numbers, the techniques proposed and the open
  questions.
- **Requirements, numbered steps and acceptance criteria** for the successor (from this file, specialised).
- **State:** what is done, what is not, any warnings and anything surprising (lock waits, decoder errors, dictation
  noise).
- **The successor must end** with its own `handoff.md`, `DONE` and a chat copy of the prompt.

## Troubleshooting

- **Lock queue.** `python scripts/session-guard.py status` shows the holder and the queue. A dead holder frees itself;
  never `unlock --force` a live job of another session.
- **No local speech model.** No HyperFrames recogniser and Hugging Face is blocked here, so `listen` uses Windows
  dictation. It invents short words over music; judge by the phrase frames. Do not try to bypass the network control.
- **Decoder errors.** Re-run that one id; if Edge fails twice, `--backend ffmpeg`, and write it in the method.
- **Memory.** If the machine is tight (Task Manager), close browsers before a heavy job; sessions that only author cost
  little.
