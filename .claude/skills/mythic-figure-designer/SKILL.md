---
name: mythic-figure-designer
description: Design and draw a NEW mythic figure (god, goddess, hero, sage, demon, animal mount) for a Motion Lab film whenever the plot needs one that the kit does not have, or redesign, re-pose or add a weapon, aura or view to an existing one. Researches the figure on the web (primary texts, museum images, the tradition's own art, modern heroic art for technique only), writes an identity block, builds it in code on the heroic human build (figures-human.js) with weapons and auras from the armoury (armoury.js), reviews the sheets and runs the tests. Use when a storyboard, script or brief names a figure missing from Studio.kit.mythic (Krishna, Sita, Lakshmana, Ravana, Durga, Vishnu, Arjuna, Zeus, Thor, Loki...), or when asked for a new figure, weapon, prop, aura, pose or angle.
version: 1.0.0
---

# Mythic figure designer: from plot to a drawn, heroic, faithful figure

The mythic kit draws figures in code, not as images. Every figure is SVG path data built from shared builders, posable on its joints, deterministic, and identical in every shot. This skill adds figures to it on demand. It works inside the `mythic-tales` pipeline (load that skill first for the film) and the studio rules in `AGENTS.md`. Nothing here replaces the iconography gate.

**Priority order** (set by the owner, 2026-11-24): heroic aesthetic, musculature and aura first, then accuracy. Accuracy still wins wherever it is sacred or carries identity:
- emblems and attributes, and which hand holds each one;
- skin colour from the text;
- the mount;
- a deity's form: Ganesha's belly, and the meditative calm of a Jina or the Buddha, which are never made heroic;
- dignity: nothing comic, nothing sexualised;
- the tradition's sensitivities in `mythic-tales/references/traditions/`.

## What exists (check before drawing anything)
| Need | Where | How to list |
|---|---|---|
| Human figures (front view). Heroic: `rama-human`, `hanuman-human`, `shiva-human`, `ganesha-human`, `athena-human`, `odin-human`. Calm: `tirthankara-human`, `buddha-human` | `src/studio/kits/mythic/figures-human.js` | `Studio.kit.mythic.human.ids` |
| Puppet figures (profile, jointed) | `src/studio/kits/mythic/figures.js` | `M.figureIds` |
| Weapons and held attributes: kodanda, shara, tuna, gada, trishula, damaru, ankusha, pasha, parashu, chakra, shankha, vajra, khadga, venu, padma, dory, aspis, gungnir, mjolnir, keraunos | `src/studio/kits/mythic/armoury.js` | `M.weapons.ids` |
| Auras: tejas, agni, cosmic, lotus, radiant, storm, calm | `armoury.js` | `M.auras.kinds` |
| Body presets (`HERO`: warrior, titan, ascetic, goddess, elder) and builders (`heroTorso`, `heroArms`, `heroLeg`, `headPart`, `vanaraHead`, `fistPart`, `palmPart`, `dhotiPart`, `girdlePart`, `kiritaPart`, `jataKnot`, `streamer`, `windLocks`...) | `figures-human.js` | `M.human.parts`, `M.human.geom` |
| Identity blocks of every figure, design rules, weapon research | `mythic-tales/references/figure-design.md` | sections 4, 6, 7 |
| 3D figures (Blender) of the same eight, built from the identity blocks: skin, sculpt, paint, dress, armoury, auras | `src/blender/mythic3d/` (`figures.py` per figure) | `python scripts/mythic3d.py list`; `figure-design.md` section 9 |

Review sheets: `tests/mythic-kit/armoury.html` (every weapon and aura) and `tests/mythic-kit/figures-human.html`. Code template and gotchas: `references/figure-template.md`. Research method: `references/research-playbook.md`. Evaluated libraries and tools: `references/tooling.md`.

## Workflow
1. **Collect the cast.**
   - From the film's `storyboard.json`, script or brief, list every figure on screen.
   - For each beat, note what the figure does: pose, prop, emotion.
   - Mark which figures already exist. Work on one new figure at a time.
2. **Research on the web (about 30-60 minutes per figure).** Follow `references/research-playbook.md`.
   - The primary text of the telling the film follows: quote it and cite chapter and verse.
   - The classical image tradition: museum records through `scripts/myth-sources.py`.
   - Variants and disputes.
   - Modern heroic art, **for technique only**.
   - Known modern errors and backlash cases.
   - Use research subagents in parallel for separate threads (text, museum iconography, heroic design).
   - Never copy a character from a film, comic, game or AI channel.
3. **Write the identity block** in `figure-design.md` section 4 (template in the playbook).
   - Record the telling and the text with citations.
   - Record what is drawn: skin, face, eyes, hair and how it is tied, facial hair, build preset, dress and colours, ornaments, attributes **and which hand holds each**, mount, aura kind, pose.
   - List the **check** items a reviewer confirms.
   - The block is the single source of truth. The code, every later view and any AI reference prompt follow it.
4. **Design.**
   - Pick the `HERO` preset, or define one: shoulders 2.2-3 head-widths, waist, stance.
   - Pick the aura and the weapons. Reuse the armoury; if a weapon is missing, add it there (`references/figure-template.md`).
   - Pick the iconic pose from a museum image of the tradition, not a modern poster.
   - Pick the palette: skin from the text, cloth by temperament (Kerala mural logic).
   - Pick one wind direction for hair, cloth and smoke.
   - Run the silhouette test in your head first: will the figure read in solid black from its weapon, headgear and aura alone?
5. **Build** `FIG['<id>-human']` in `figures-human.js` from the template in `references/figure-template.md`.
   - Add the id to `M.human.ids`.
   - Keep everything deterministic: no `Math.random`, no time.
6. **Review loop** (at least two passes).
   - Render: `python tests/mythic-kit/render-figures.py --ids <id>-human[,<id>-human:opt=value]`.
   - Look at `projects/_mythic-figures/figure-<id>-human.png`: the full figure and the 3x head close-up.
   - Add `--look silhouette` for the silhouette test, `--look paper` for the paper look.
   - Check the proportions: add the figure to `tests/mythic-kit/proportions.html` (`?ids=<id>-human`) and to the proportion check in `tests/mythic-kit/index.html` with its body type (`male`, `titan` or `female`; bands in `figure-design.md` section 8). Place arms with `armJ` (lengths from the head) rather than hand-picked elbows: hand-picked arms came out too short in the first build.
   - Fix what you see: overlaps, a weapon in the wrong hand, a limb seam, a face off the grid, clutter, an unreadable emblem.
7. **Test and register.**
   - Run `python tests/test-mythic.py`. It builds every human figure in every look and checks joints, layers, clips and auras.
   - Run `node --check` on the kit files.
   - Update `figure-design.md`, `mythic-tales/references/scene-recipes.md` (the human table), the tradition pack's "Figures in the kit" and `catalogue/data/primitives/mythic-figures.json`.
   - Run `python scripts/motion-catalogue.py validate` and `python scripts/workspace-governance.py`.
   - Re-sync projects that use the kit: `python scripts/studio.py upgrade <slug>`.
   - Optional, for a turnaround reference or a 3D render: add the figure to `src/blender/mythic3d/figures.py` from the same identity block (`BUILDERS`, `FIGURES`, and the CLI's `FIGURES` in `scripts/mythic3d.py`), add its hand checks to `tests/test-mythic3d.py`, render with `python scripts/mythic3d.py render --figures <id>` and look at the turnaround (`figure-design.md` section 9).
8. **Gate.**
   - Walk the iconography gate in `mythic-tales/references/quality-rubric.md` against the identity block.
   - Anything marked **check** goes to the human reviewer before release.

## AI reference stills (optional, reference only)
- **When:** no museum image shows the pose or costume. A generated still may then be used **as drawing reference, never shipped**.
- **Command:** `python scripts/assets.py generate <slug> --task text-to-image --provider kie --prompt "..."`. The key lives in the environment only.
- **Prompt:**
  - Build it from the identity block: subject, form, attributes per hand, ornaments, palette, art form.
  - Add "no text, no watermark, no Western fantasy armour, no modern objects".
- **Log it** in the film's `research.json`.
- Local image models are not set up (see `references/tooling.md`).

## Rules that never bend
- Sacred figures stay whole and dignified:
  - no comic props;
  - no weapon swapped into the wrong hand;
  - no deity drawn as a joke or a monster;
  - no sexualised anatomy (goddesses are athletic and covered).
- No hate-appropriated symbols as decoration (valknut, Othala rune, sonnenrad). Runes on Norse weapons are abstract marks.
- Learn techniques, never characters: no Marvel Thor, God of War Odin, Adipurush Hanuman, Amar Chitra Katha faces.
- `src/_studio/` copies are never edited. Edit `src/studio/` and run `studio.py upgrade`.
- New libraries or tools need the owner's approval first. `references/tooling.md` lists what was evaluated.
