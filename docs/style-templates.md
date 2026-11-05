# Style templates

A style template is the unit you pick when you ask "what should this video look like", and the unit you refine when a video turns out wrong. Fix the template once and every video that follows it inherits the fix, instead of repairing each film by hand.

Records live in `catalogue/data/style-templates/`, schema in `catalogue/schemas/style-template.schema.json`, logic in `src/pipeline/style_templates.py`, CLI under `python scripts/studio.py style`.

## Why this layer exists

The workspace already had two layers that describe a look, and neither answers "which one for this film?":

| Layer | Owns | Does not own |
|---|---|---|
| **Style system** (`catalogue/data/styles/`, `src/studio/styles/*.css`) | Paint: colours, fonts, texture, easing defaults | When to use it; any rule about pacing |
| **Design profile** (`catalogue/data/design-profiles/`) | Design DNA: identity, camera, transitions, audio direction, each fact tagged measured or prescribed | A decision; anything a check can fail |
| **Style template** (this) | The decision and the contract: when to pick it, the scene grammar, measurable rules, anti-patterns, revision log | Colours, fonts, easing. It binds a style system and a profile and never repeats them |
| **Creative direction** (`brief.json`) | One film's own interpretation, up to three alternatives | Anything reusable |

A template therefore answers the open question in `TODO.md`: a visual style is look **and** motion language **and** pacing rules, but those live in three records that a template ties together. A brief's creative direction is a per-film choice made inside the template's limits.

## The seven templates

They are split by **what the picture has to do**, not by subject. Subject is a hint (`selection.categories`); the visual job decides. A finance story about a collapse can need `data-ledger` (the point is a number) or `chronicle` (the point is the order of events).

| Template | Visual job | The viewer leaves able to | Default style |
|---|---|---|---|
| `systems-blueprint` | mechanism | trace input to output and name the part that fails | editorial-light |
| `proof-canvas` | proof | restate the claim and say why it must be true | abstract-geometric |
| `data-ledger` | quantity | state how big it is, how it changed, against what | data-journalism |
| `chronicle` | sequence | place events in order, in place and time | archival |
| `storybook` | narrative | remember the people and the stakes | paper-cut |
| `news-brief` | evidence | say what is confirmed, what is not, what next | data-journalism |
| `science-atlas` | natural-world | picture the structure at its real scale | editorial-light |

Defaults are light. A dark style appears only under `look.alternates` with a stated condition, matching the workspace rule that dark themes need a brief that asks for them. The schema check rejects a dark default.

### Samples

Each template has a 22-second silent portrait sample in `projects/style-sample-<template>/`, rendered to `out/style-sample-<template>-portrait.mp4`. Each one walks through its template's scene grammar on a subject that fits the visual job. Each storyboard carries beats in film time, so `style check` measures the sample against its own rules. The samples are for judging the look; they are not releases.

| Sample | Subject | Pinned |
|---|---|---|
| `style-sample-systems-blueprint` | How a pin-tumbler lock opens | v1 |
| `style-sample-proof-canvas` | Why a triangle's angles add to 180° | v1 |
| `style-sample-data-ledger` | World population, one billion at a time (UN) | v2 |
| `style-sample-chronicle` | Apollo 11, launch to splashdown (NASA) | v1 |
| `style-sample-storybook` | Grace Darling's 1838 rescue | v2 |
| `style-sample-news-brief` | The 2025 NIRS data center fire (reuses the Korea dossier) | v2 |
| `style-sample-science-atlas` | Earth's layers at true scale | v1 |

When a template changes, `style check` marks its sample as behind. Re-render the sample and look at it before re-pinning: it is the cheapest way to see what a rule change does.

## Picking one

```bash
python scripts/studio.py style recommend <slug>                       # uses the brief's categories, title, objective, message, tone
python scripts/studio.py style recommend --category finance --text "how inflation hit pensions"
python scripts/studio.py style show data-ledger
python scripts/studio.py style adopt <slug> data-ledger              # pins id and version in project.json
python scripts/studio.py new <slug> --template illustrated-explainer --style-template data-ledger --category finance
```

`recommend` scores categories (primary 3, others 1.5) plus up to 6 keyword hits, and prints its reasons. It is a heuristic. When the top two are within 1.5 points it says so; settle those by reading each template's `avoid_when` and its "viewer leaves able to" line. On the current projects it picks sensibly for seven of nine and treats cloud-physical-infrastructure-india as a close call between `systems-blueprint` and `news-brief`, which is accurate: it is a mechanism film told as news.

## The refinement loop

1. A review, a render or a measured QA result shows a problem.
2. Decide whether it is one film's problem or the kind's. If the kind's, edit the template record: change a rule, add an anti-pattern, adjust the scene grammar.
3. Bump `version` and append to `revisions` with the change **and the evidence**. The validator requires `version` to equal the newest revision.
4. `python scripts/studio.py style check` lists every project with the version it was built against. Projects behind the template are marked.
5. `style check <slug>` prints what changed since its version plus the current rule findings. Revise the project, then `style adopt <slug> <template>` to re-pin. Re-pinning records that you reviewed the change; it does not apply it.

`studio.py validate` runs the same project check and prints it as warnings, so a build never fails on a template rule. Rules guide; errors are reserved for broken references.

Promotion from `experimental` to `approved` needs `validation.evidence` and at least one reference project. The intended bar, not yet automated: two films made to the template, rendered on the render host, passing `qa/creative-review.json`. None of the seven has met it.

## What is checked, and by what

Checked before any render by `style check` and `validate` (storyboard, narration, `audio/timeline.json`):

| Rule | Check |
|---|---|
| `words_per_10s_max` | Words per scene divided by the measured clip length, per scene. Falls back to the storyboard span when narration is not yet measured |
| `max_beat_gap_sec` | Longest stretch between storyboard beats in a scene, including the lead-in and the tail |
| `hook_within_sec` | First beat of the first scene |
| `max_scene_sec` | Scenes over the limit that carry no beats |
| discouraged capabilities | Storyboard capabilities the template discourages |
| style | Project style is the default or a listed alternate |
| version | Pinned version behind the template |

Not checked by this layer: `rules.ending` (reviewed by a person), label size and collisions (`motion-qa`, `frame-review`, then your eyes), and whether a scene's visual events really happen (only the storyboard's plan is read).

Calibration: run against the three newest films, the check reproduces the numbers measured by hand on 2026-11-03: cloud s1 and s6 at 36 and 35 words per 10 s, fridge s2 at 33, and Korea inside budget. Every scene of all three also fails the 2.0 s beat gap, because their storyboards plan one event every 3 to 7 seconds. That matches what `motion-qa` found after rendering (41, 44 and 79 s of static or low-energy stretches).

## Honest limits

- The rule values are **prescribed**, taken from the voice-director budgets, CLAUDE.md and the 2026-11-03 review. No film has been made to a template yet, so none is calibrated. `proof-canvas` at 27 words per 10 s is the clearest guess: `polya-recurrence` (29 to 39) exceeds it in every scene, and it is not known whether the film was too fast or the number too tight.
- The beat gap needs storyboard beats. Most storyboards have none (polya, none of its six scenes); the check then says it cannot check, and states which scenes.
- `at_sec` in beats is film time in Korea and cloud and scene time in fridge. The checker reads both and says when it shifted a scene.
- Two templates (`data-ledger`, `news-brief`) bind the same style system and profile. They differ in scene grammar and rules, not in paint. If that proves too fine a split, merge them.
- Light default for `science-atlas` is `editorial-light` because both scientific styles are dark. A light plate style is the missing piece (recorded as an open question on the template).
- `catalogue/index.json` was not regenerated; it is a derived file (`motion-catalogue.py export`) and carries other sessions' uncommitted changes.

## Adding or changing a template

Copy an existing record, keep `id` equal to the file name, and run:

```bash
python scripts/motion-catalogue.py validate
python tests/test-style-templates.py
```

The tests require every category in `specs/categories.json` to be served by at least one template and every visual job to be distinct, so a new subject category forces a decision about which template covers it.
