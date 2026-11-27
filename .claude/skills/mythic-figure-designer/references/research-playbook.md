# Research playbook: finding what a figure looks like

Goal: an identity block that is faithful where it must be and heroic everywhere else, with every claim linked.

## 1. Source ranking (use the highest available; say which you used)
1. **Primary text of the film's telling**, in a public-domain or scholarly translation, cited by book, chapter and verse:
   - Ramayana: ramayana.com (Gita Press) or valmikiramayan.net.
   - Mahabharata: Ganguli on sacred-texts.com.
   - Puranas and Upanishads: wisdomlib.org, vedabase.
   - Homer, Hesiod, Ovid, Pausanias: Perseus, theoi.com, Loeb.
   - Eddas: Bellows on sacred-texts.com, voluspa.org.
   - Jain and Buddhist: SuttaCentral, JAINpedia.
2. **Museum records of the tradition's own images** (Met, V&A, Cleveland, British Museum, National Museum India, Government Museum Chennai, Acropolis Museum).
   - Search them with `python scripts/myth-sources.py search "<figure> <attribute>" --source cma,met,commons --culture "..."`.
   - Read the record's description: it names the attributes and the hands that hold them.
3. **Iconographic manuals and scholarship**: Shilpa texts (Manasara on wisdomlib), Brihat Samhita, the Met's Heilbrunn essays, Britannica, Theoi.
4. **Secondary and devotional pages**: mark them **[blog]** and never use them alone for a sacred attribute.
5. **Modern heroic art and animation**, for **technique only**: proportion, pose, light, aura, silhouette. Write down the technique, never the character.

## 2. Query templates (run several in parallel; research subagents work well)
- Text: `"<figure>" description <text name> <book> verse translation`, `"<epithet>" meaning`, `<figure> physical appearance <text> chapter`.
- Image tradition: `<figure> bronze museum attributes left hand right hand`, `<figure> iconography dhyana sloka`, `<figure> Chola | Pala | Gupta | Pahari | Attic red-figure | Gotland picture stone`.
- Weapons and props: `<weapon> shape museum`, `<weapon> iconography <tradition>`, `<figure> holds <weapon> which hand`.
- Heroic technique: `<figure> modern illustration character design`, `<film> character design interview`, `heroic proportions head count shoulder width`.
- Errors and sensitivities: `<figure> controversy depiction`, `<figure> portrayal backlash`, `Hindu American Foundation <topic>`.
- AI landscape (to learn what audiences reject): `AI generated <figure> video criticism`, `AI mythology series review faces`.

## 3. What to record for each figure
| Field | Examples |
|---|---|
| Telling | Valmiki / Tulsidas / Kamban; Homer / Ovid; Poetic or Prose Edda |
| Text says | quotations with citations: complexion, build, face, eyes, hair, beard, dress, ornaments, attributes |
| Image tradition adds | museum-sourced attributes, hand positions, pose (tribhanga, Promachos, dhyana) |
| Varies | by telling, region, period, sect |
| Modern errors | neon skin, Western armour, comic animal, wrong hand, mixed tellings |
| Heroic choices | preset, proportions, aura, pose, expression (calm power or fury), wind |
| Check items | anything not sourced that a reviewer must confirm |

## 4. Identity block template (append to `figure-design.md` section 4)
```markdown
### <Name> (`<id>-human`)
- **Telling**: <text and version>; <which episode or state: exile, royal, battle>.
- **Text**: <quote> (<book chapter.verse>, [source](url)); <quote> (...).
- **Drawn (heroic)**:
  - <preset>, <aura kind>, <pose>;
  - skin <colour and source>; face <eyes, brows, expression>;
  - hair <how dressed>; facial hair <none or which>;
  - dress <garments and colours>; ornaments <list>;
  - <right hand: object>; <left hand: object>; mount or companion <...>.
- **Options**: `<opt>: '<a>' | '<b>'`.
- **Check**:
  - <what is not sourced or is disputed>;
  - <artistic licence taken for heroism: aura, musculature>.
```

## 5. Heroic design rules (summary of the 2026-11-24 research; details in `figure-design.md` section 7)
- **Proportions:** 8-8.5 heads for heroes and gods, about 7 for a titan (Hanuman), 6.5 for Ganesha. Shoulders 2.2 (goddess) to 3.0 (titan) head-widths. Elbows at the waist.
- **Stance:** a wide A-stance, chest out, weapons held clear of the body so the silhouette reads.
- **Muscle as cel shapes:**
  - pec crescent shadow;
  - deltoid cap;
  - biceps lens;
  - abs implied 2 x 3, shadow on the lower edge only;
  - serratus fingers on the shadow side;
  - oblique wedge and Apollo's belt;
  - quad teardrop;
  - calf bean.
- **Light:**
  - one lamp at the upper left;
  - the aura behind adds a warm rim light on both edges;
  - the outer contour is the heaviest line.
- **Divinity by code:**
  - **Prabhavali or prabhamandala:** 13 flame tongues on the Chola Nataraja.
  - **Sun disc and 12-24 rays:** radiant figures.
  - **Calm or fierce face:** match the episode.
  - Greek gods have no halo; use radiance. The Norse sources give no aura convention; use storm light and props.
- **Expression:**
  - Calm power: level brows, steady gaze, closed or slightly smiling mouth (Rama, Shiva, Athena).
  - Fury: brows angled to the nose (Hanuman in battle, Odin).
- **One wind direction** for hair, cloth and cloak.
- **Kitsch traps:**
  - calendar-art gloss;
  - neon skin;
  - bodybuilder excess on a meditative figure;
  - Western or Marvel armour;
  - a cartoon animal;
  - drifting attributes (AI's typical failure).

## 6. Lessons from AI mythology video (why code-drawn figures)
- *Mahabharat: Ek Dharmayudh* (JioHotstar, 2025) was praised for colour and criticised for uncanny faces, anachronisms and continuity breaks ([IWMBuzz](https://www.iwmbuzz.com/television/editorial/mahabharat-ek-dharmayudh-review-shines-as-tech-powered-epic-for-new-generation/2025/10/25), [New Indian Express](https://www.newindianexpress.com/web-only/2025/Nov/27/mahabharat-ek-dharmayudh-is-proof-that-ai-does-not-replace-the-need-for-filmmaking-craft-it-amplifies-it)).
- Independent AI Ramayana series admit faces vary between shots.
- AI prompt guides converge on a fixed "identity block" per deity, because attributes drift: a conch becomes a cup, a trident a spear ([Orelon](https://orelon.ai/blog/hindu-gods-ai-art-prompts-guide) [blog]).
- Our figures are consistent by construction. Keep them that way: one identity block, one drawing, posed, never regenerated per shot.
