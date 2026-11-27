---
name: mythic-tales
description: Entry point for films that retell myths, legends and sacred stories (gods, heroes, epics, origin stories) in the Indian, Jain, Buddhist, Greek, Roman and Norse traditions, in the mythic-tale style template (lamp-lit paper, layered public-domain museum photos, shadow puppets, painted folios, carved relief). Use when the user asks for a myth, legend, deity, epic episode, Jataka or Tirthankara story as a short, mid or long film, or asks about the mythic styles, the mythic kit, sourcing images of gods, or depicting a deity respectfully. Routes to only the references the task needs and runs the normal studio pipeline with a storyteller stance and an iconography gate on top.
version: 1.1.0
---

# Mythic tales: the storyteller's paper theatre

A mythic film is a **storyteller's performance**: a lamp, a box that opens, a world laid out in paper, a god or hero who rises into a halo, the tradition's own art held up as evidence of how it has been told. The stance is **storyteller**: "as told in the Valmiki Ramayana", "the tradition reads this as". Never devotional preaching, never debunking. This skill specialises the studio pipeline (`AGENTS.md` section 1); it is not a second pipeline.

## What exists (all registered in `catalogue/data/`)
| Piece | Where |
|---|---|
| Category `mythology` | `specs/categories.json` |
| Style template `mythic-tale` (job `myth`, scene grammar, rules, anti-patterns) | `catalogue/data/style-templates/mythic-tale.json` |
| Style systems, all light: `mythic-paper` (default), `shadow-lantern`, `painted-folio`, `carved-relief` | `src/studio/styles/*.css`, `catalogue/data/styles/` |
| Design profile `mythic-storyteller` | `catalogue/data/design-profiles/` |
| Runtime kit `Studio.kit.mythic` 0.5.0 (stage, sheets, plates, haloes, borders with tradition presets, doors, scrolls, friezes, registers, puppets, lamp, tint, shower, stepped "on twos" motion) | `src/studio/kits/mythic/mythic.js` |
| Figure library: Rama, Hanuman, Shiva, Ganesha, Athena, Odin, a seated Tirthankara (lanchhana options), the Buddha, in classic and heroic (muscular) builds and silhouette, leather, paper and painted looks | `src/studio/kits/mythic/figures.js` (review sheets: `tests/mythic-kit/render-figures.py`) |
| Human build of the same eight: believable people on one proportion grid, faces, hair, dress and ornament from the texts, `look: 'illustrated'`; ids `rama-human` ... `buddha-human` | `src/studio/kits/mythic/figures-human.js` (review sheet: `tests/mythic-kit/figures-human.html`; research and identity blocks: `references/figure-design.md`); since 2026-11-24 the heroic build (muscular, auras, iconic poses) for all but the Jina and the Buddha |
| Armoury: 20 weapons and attributes (kodanda, gada, trishula, gungnir, dory, aspis, chakra, vajra, mjolnir, keraunos...) drawn once at the grip and placed in a hand; 7 auras (tejas, agni, cosmic, lotus, radiant, storm, calm) | `src/studio/kits/mythic/armoury.js` (review sheet: `tests/mythic-kit/armoury.html`) |
| 3D figures of all eight (Blender, procedural from the identity blocks): hero shot, five-view turnaround, head close-up; looks `painted` and `bronze`; review renders and drawing reference, not film plates | `src/blender/mythic3d/`, `python scripts/mythic3d.py render` (sheets in `projects/_mythic-figures/3d/`; `references/figure-design.md` section 9; test `tests/test-mythic3d.py`) |
| Style samples: Hanuman's leap in all four looks, 22 s portrait, frame-reviewed | `projects/style-sample-mythic-{paper,shadow,folio,relief}` (local; `projects/` is untracked) |
| Project template `mythic-film` (45 s scaffold, cues scale with the duration) | `templates/projects/mythic-film/` |
| Arcs `sacred-tale`, `boon-and-curse`, `origin-myth` | `specs/narrative-arcs.json` |
| Hook formulas `impossible-feat`, `boon-loophole` | `specs/hook-formulas.json` |
| Image search `scripts/myth-sources.py` (Cleveland, Met, Commons; public domain only) | `catalogue/data/tools/myth-sources.json` |

## Route the task, load only what it needs
| The task involves | Load |
|---|---|
| any mythic film (always) | this file + the form skill (`short-form`, `mid-form`, `long-form`) + the tradition pack |
| Hindu epics, Puranas, Shiva, Vishnu, Krishna, Rama, Devi, Ganesha, Hanuman | `references/traditions/indian.md` |
| Tirthankaras, Jain Ramayana, Jataka, the Buddha | `references/traditions/jain-buddhist.md` |
| Olympians, heroes, Homer, Hesiod, Ovid | `references/traditions/greek-roman.md` |
| Aesir, Vanir, the Eddas, Ragnarok | `references/traditions/norse.md` |
| story, script, hook, arc, voice, music | `references/storytelling.md` (+ `story-writer`, `voice-director`) |
| choosing among the four looks, palettes, why a move exists | `references/design-language.md` |
| writing `src/index.html`, kit calls, a scene recipe | `references/scene-recipes.md` |
| drawing or changing a figure, a figure's look, body, face, dress or attributes, a new view or angle, an AI still of a figure | `references/figure-design.md` |
| a 3D render, turnaround or bronze of a figure | `references/figure-design.md` section 9 (`scripts/mythic3d.py`) |
| the plot needs a figure, weapon, prop or aura the kit does not have | the `mythic-figure-designer` skill (research, identity block, code, review, tests) |
| museum images, AI stills, credits, rights | `references/imagery-sourcing.md` |
| review, "is it done", the iconography gate | `references/quality-rubric.md` |

## Invocation: a myth as a `short | mid | long` film
1. **Pick the episode and the telling.** One episode, one turn. Name the text and version you follow (Valmiki or Tulsidas, Homer or Ovid, Snorri's Prose Edda or the Poetic Edda). Say which and why.
2. **Scaffold.** `python scripts/studio.py new <slug> --template mythic-film --style-template mythic-tale --type <short|mid|long> [--formats landscape] --category mythology`. Choose the look with `studio.py style show mythic-tale` (alternates and their conditions). Fill `brief.json` (1-3 directions; the scaffold seeds three). Then set `research.required` to `true`.
3. **Research (always).** `technical-researcher` writes `research.json`/`research.md` holding: the telling followed and its variants, the episode's events in order, every figure's iconography checklist (from the tradition pack), the tradition's own reading of the episode (attributed), image sources with licences, and `do_not_claim` items. Gate: `python scripts/validate-research.py projects/<slug>`. Never invent a verse, a quotation or an attribute.
4. **Story.** `story-writer` with arc `sacred-tale` (or `boon-and-curse`, `origin-myth`): `python scripts/beatmap.py init <slug> --arc sacred-tale`. Hooks from `impossible-feat` / `boon-loophole` (`studio.py hook formulas`); the hook names the telling. Sign-off `qa/story-review.json`.
5. **Images.** `python scripts/myth-sources.py search "<figure> <episode>" --out projects/<slug>/research/plates.json`, fetch with the collage fetcher, check each image by eye against the tradition pack, import with `scripts/assets.py import ... --license-status verified`. AI stills only where no public-domain image exists, logged and iconography-checked (`references/imagery-sourcing.md`).
6. **Audio.** `voice-director` (storyteller voice, respellings for Sanskrit, Greek and Old Norse names in `src/narration.json`), `build-audio.py`, `studio.py captions <slug> --timing words`, then `beatmap.py storyboard <slug>`.
7. **Visuals.** `src/index.html` on the kit (`references/scene-recipes.md`): start the figure from the library (`figure: 'hanuman'`) or a museum plate, the border from the tradition preset (`border({tradition: 'indian'})`), and copy the closest style sample's structure. Replace the scaffold's cue map with measured times and snap each beat to its word (`studio.py words <slug> "<phrase>"`). The scaffold is paced for a 45 s short; a mid or long film re-plans its beats per scene, or frame review flags dead stretches.
8. **Pre-render gate.** `studio.py validate <slug>`, `studio.py style check <slug>`, `python scripts/frame-review.py <slug> --fonts google`; look at every contact sheet; walk the iconography gate in `references/quality-rubric.md`.
9. **Render and review.** `studio.py build <slug>` on the render host (one heavy job at a time), `studio.py review <slug> --init`, story-writer `retro`. A rule that will recur goes into `mythic-tale.json` with a version bump and evidence.

## Forms
- **short** (20-60 s, portrait): one moment of one episode (Hanuman's leap, Odin at Mimir's well); invocation in the first 1.5 s, one emblem, one turn, the lamp returns as the loop.
- **mid** (60-180 s): one complete episode with `sacred-tale` stages; re-hook at the trial and the turn; one plate of the tradition's own art as evidence.
- **long** (5-12 min, landscape, chapters): an arc of episodes (the churning of the ocean, the twelve labours, Ragnarok); each chapter one turn, a chapter card in the folio border, the telling named once per chapter.

## Rules that never bend
- **Storyteller stance.** Attribute belief and meaning ("Hindus regard...", "Snorri says..."); never assert, preach or debunk. Do not use the `myth-flip` hook formula: it is for myth-busting.
- **Name the telling** on screen (source cartouche) and in narration; never mix tellings in one film without saying so.
- **Sacred images stay high and whole.** No deity at foot level, stepped over, dropped, shattered, glitched or wiped; no comic props in a deity's hands; no bounce or whoosh on sacred figures.
- **Iconography is checked**, especially on generated images, against the tradition pack, and every figure is identified by an emblem on first appearance.
- **Every image is public domain or licensed and credited.** No pop-culture portrayals as source (Marvel, Disney, games).
- **No hate-appropriated symbols as decoration** (valknut, Othala rune, sonnenrad).
- **Pipeline:** light canvas by default (`cinematic-dark` only when the brief asks); one heavy job at a time; `src/_studio/` is never edited.
