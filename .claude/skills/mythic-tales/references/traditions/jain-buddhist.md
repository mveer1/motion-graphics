# Tradition pack: Jain and Buddhist stories

## Jain

### Tellings and translations
- The **Kalpa Sutra** (lives of the Tirthankaras, read at Paryushana; illustrated from the mid-15th century) ([Wikipedia](https://en.wikipedia.org/wiki/Kalpasutra)). Public-domain translation: Hermann Jacobi, *Jaina Sutras* part I (Sacred Books of the East 22, 1884).
- The Jain Ramayana, *Paumachariya* of Vimalasuri: Rama does not kill; Lakshmana kills Ravana.
- Say which sect's tradition the film follows: **Digambara** or **Shvetambara**.

### Iconography checklist
The 24 Tirthankaras (Jinas) share near-identical bodies and faces on purpose; the **emblem (lanchhana)** on the pedestal identifies them ([Nidarshana Vedh](https://jain.nidarshanavedh.com/symbols/lanchhana/) [Tier 2]; check every emblem against one named source and cite it).

| Tirthankara | Emblem | Notes |
|---|---|---|
| Rishabhanatha (1st) | Bull | Locks of hair on the shoulders |
| Shantinatha (16th) | Deer | |
| Neminatha (22nd) | Conch | |
| Parshvanatha (23rd) | Snake | Canopy of seven or more serpent hoods |
| Mahavira (24th) | Lion | |

- The two sects differ on some emblems (Anantanatha, Shitalanatha): use one named source per film.
- **Digambara** images: unclothed, eyes downcast, no ornaments or crown, shrivatsa on the chest. **Shvetambara** images: a lower garment marked, open eyes, often adorned. Mallinatha is female in Shvetambara tradition, male in Digambara ([Tier 2 summary of JAINpedia and Britannica](https://jain.nidarshanavedh.com/symbols/lanchhana/)).
- The Ahimsa hand: a raised palm with a wheel.
- The earliest images (Kushana Mathura) carry no emblem; a film set then should not invent one.

### Sensitivities
- A Tirthankara has destroyed attachment and aversion: never show one fighting, granting boons or protecting someone. Say "Tirthankara (ford-maker)", not "god".
- Ahimsa: no gore, no animal harm shown, no violence by a Jina.
- Monks and nuns are living people: no caricature.
- No Tier 1 source on specific offence cases was found: a Jain scholar or JAINA reviews before release.

### Episodes
- short: Mahavira's lion emblem and why; the snake canopy of Parshvanatha.
- mid: Neminatha's wedding procession turned renunciation; Mahavira's birth dreams (Kalpa Sutra).
- long: Mahavira from renunciation to kevala jnana.
- Look: `painted-folio` after Kalpasutra folios (lapis, gold, angular line, projecting eye). Queries: "Kalpasutra", "Jina Parshvanatha", "Tirthankara", `--culture "India|Gujarat"`.

## Buddhist

### Tellings and translations
- **Jataka** tales: stories of the Buddha's previous lives as the Bodhisatta, teaching stories, not the historical biography. Public-domain translation: E. B. Cowell (ed.), *The Jataka* (1895-1907).
- Life of the Buddha: the Pali canon, the *Buddhacarita* (Ashvaghosha); say which.

### Iconography checklist
- Mudras ([Smarthistory](https://smarthistory.org/mudras-in-buddhist-art/)): earth-touching (bhumisparsha, enlightenment), meditation (dhyana), fearlessness (abhaya), giving (varada), teaching wheel (dharmachakra, first sermon).
- **Aniconic period**: early art shows the Buddha by an empty throne, the Bodhi tree, footprints, the wheel or a stupa ([Wikipedia](https://en.wikipedia.org/wiki/Aniconism_in_Buddhism)); Bharhut and Sanchi show Jatakas this way. Gandhara images carry Greek-influenced drapery; Mathura images an Indian style.
- Jataka art: Ajanta murals (Shibi, Mahajanaka, Chhaddanta) ([IASPOINT](https://iaspoint.com/ajanta-paintings/) [blog]).

### Sensitivities
- Buddha images are not decoration: never as wallpaper, never at foot level or on the floor, never with your back turned in a composition, no comic reuse, no sound-effect gags ([Lanka Lens](https://lankalens.com/articles/buddha-images-rules/) [Tier 2]). Sri Lanka and Myanmar enforce this by law. Keep the image high and whole.
- Do not draw a human Buddha in a scene set in the aniconic period.

### Episodes
- short: the hare in the moon (Sasa Jataka); the monkey king's bridge.
- mid: Prince Vessantara; the Chhaddanta elephant.
- long: from the four sights to the first sermon.
- Look: `mythic-paper` with Ajanta earth tones, or `carved-relief` with Gandhara and Sanchi reliefs. Queries: "Jataka relief", "Gandhara Buddha", "Life of the Buddha shrine" (the Met's object 38224 is a Gandhara shrine section with scenes from his life).

## Figures in the kit
kits/mythic/figures.js: `tirthankara` (seated in meditation; `figureOptions: {emblem: 'lion'}` for Mahavira, `'bull'` Rishabhanatha, `'deer'` Shantinatha, `'conch'` Neminatha, `'snake'` Parshvanatha's hoods) and `buddha` (earth-touching gesture). kits/mythic/figures-human.js: `tirthankara-human` (same emblems; `sect: 'digambara'` or `'svetambara'`; Brihat Samhita 57.45: arms to the knees, shrivatsa, placid, young; tiny curls, no ushnisha) and `buddha-human` (DN 30: golden, ushnisha, urna; robe over the left shoulder; bhumisparsha); see `../figure-design.md`. 3D: `python scripts/mythic3d.py render --figures tirthankara,buddha` (`../figure-design.md` section 9; the 3D lanchhana exists for the lion (Mahavira) and the serpent hoods (Parshvanatha) only, and any other emblem is refused rather than drawn as the lion). Pose them only gently (head, a breath); never posed fighting or granting boons. Borders `{tradition: 'jain'}` (ruled, beads) and `{tradition: 'buddhist'}` (lotus, beads).
