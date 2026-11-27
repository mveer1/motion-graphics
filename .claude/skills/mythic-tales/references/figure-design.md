# Figure design: human-like mythic figures

How the kit draws gods and heroes as believable people while keeping every mark the traditions give them. Research done 2026-11-24 (three web passes: AI mythology video, the Indian texts, the other traditions and figure craft). Code: `src/studio/kits/mythic/figures-human.js` (the `human` build). Review sheet: `tests/mythic-kit/figures-human.html` (rendered by `tests/mythic-kit/render-figures.py`). **[blog]** marks a secondary source to cross-check; **check** marks a choice a reviewer confirms before release.

## 1. What AI mythology video taught us

| Finding | Source | Rule for us |
|---|---|---|
| *Mahabharat: Ek Dharmayudh* (JioHotstar, Oct 2025, made with AI) won praise for lush colour and costume, and criticism for uncanny faces, mouths that do not match the line, a modern bedside table, arrow fletching that changes between cuts, and a king in armour inside his palace (armour kept the face consistent). | [IWMBuzz](https://www.iwmbuzz.com/television/editorial/mahabharat-ek-dharmayudh-review-shines-as-tech-powered-epic-for-new-generation/2025/10/25), [New Indian Express](https://www.newindianexpress.com/web-only/2025/Nov/27/mahabharat-ek-dharmayudh-is-proof-that-ai-does-not-replace-the-need-for-filmmaking-craft-it-amplifies-it) | Faces and continuity are where audiences notice failure. Code-drawn figures are consistent by construction; keep them so (one identity block per figure, below). |
| The studio "locked every character sketch, costume reference and lighting plan before any generation began"; "AI was never allowed to invent culture". | [Moneycontrol](https://www.moneycontrol.com/entertainment/exclusive-vijay-subramaniam-on-using-ai-to-bring-india-s-greatest-epic-into-the-digital-age-with-mahabharat-ek-dharmayudh-ai-was-never-allowed-to-invent-culture-article-13714525.html) | Design and sign off the model sheet before any scene uses a figure. |
| Independent AI Ramayana series admit characters "may appear with slight variations across shots". | [YouTube playlist](https://www.youtube.com/playlist?list=PLtz5boX1JA4bgYoUMStUPuobkVbvG9xSE) | Drift is the genre's norm; consistency is our advantage. |
| AI deity prompts work through iconography nouns, not adjectives; attributes drift (a conch becomes a cup, a trident a spear); name each hand and its object; anchor the palette (vermilion, turmeric, sandalwood, deep green, indigo, gold); "no Western fantasy armor". | [Orelon](https://orelon.ai/blog/hindu-gods-ai-art-prompts-guide) [blog] | Every hand's object is fixed in code and in the identity block; never swapped between shots. |
| Backlash cases: *Adipurush* (Hanuman in leather with a beard), AI videos rendering deities as "cartoon-like characters", AI that flattens skin tones and costume. | [Firstpost](https://www.firstpost.com/explainers/explained-a-ravana-looking-like-khilji-just-the-many-reasons-adipurush-is-facing-backlash-11400431.html), [New Indian Express](https://www.newindianexpress.com/india/2026/Jun/28/ai-generated-videos-depicting-jesus-as-father-of-hindu-deities-spark-protests-in-chhattisgarh) | No Western armour, no human beard on Hanuman, no cartoon gods, and skin colour from the text, not a default. |
| Character consistency in AI pipelines: one canonical reference image, a verbatim "identity block" reused in every prompt, turnaround sheets (front, side, back at the same scale, aligned feet). | [Midjourney Omni Reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference), [Luma](https://lumalabs.ai/news/make-character-sheet-with-ai) | The identity blocks below double as the prompt for any generated still (`imagery-sourcing.md` section 3). |

## 2. Lessons from the traditions' own art (technique only)

- **Raja Ravi Varma** gave the gods a human, three-dimensional face with European light and shade; his oleographs became the mass template ([Google Arts & Culture](https://artsandculture.google.com/story/0115/mAVxcZVst3JgLw)). Take the humanity; avoid the airbrushed calendar gloss it became.
- **Amar Chitra Katha**: firm even outline, hard solid shadow shapes, limited palette ([Curio](https://designbycurio.com/learn/amar-chitra-katha-comic-1967) [blog]). This is close to our `illustrated` look; do not imitate its characters.
- **Kerala murals**: colour by temperament, flat fields from light to dark, outline last ([Memeraki](https://www.memeraki.com/blogs/posts/panchavarnas-of-kerala-mural-paintings-the-five-colours-and-what-they-mean) [blog]). Our layer order is the same: base, shadow, light, features, outline.
- **Chola bronzes**: Hanuman "has assumed anthropomorphic form, with only his face and tail confirming his monkey identity" ([Met 38945](https://www.metmuseum.org/en/art/collection/search/38945)); Nataraja's *jata-makuta* with Ganga, cobra, crescent and skull, mismatched earrings ([National Museum](https://museumsofindia.gov.in/repository/record/nat_del-56-2-1-4919)).
- ***Ramayana: The Legend of Prince Rama* (1992)** reconciled Indian painting with anime simplification ([Wikipedia](https://en.wikipedia.org/wiki/Ramayana:_The_Legend_of_Prince_Rama)): simplify the drawing, never the iconography.
- **Divinity by code, not effects**: halo (prabhamandala) as a flat disc or ring, a lotus seat, a straight axis, a held gesture; calm faces read as reverent ([EnRoute](https://enrouteindianhistory.com/light-in-indian-art/) [blog]).

## 3. The drawing rules the code follows

1. **One grid.** Standing figures: viewBox 400 x 820, centre line x 200, 8 heads of 88-96 units (the heroic canon; Indian *talamana* measures in face-lengths, about 9.5 faces for *uttama dasatala* gods, [Manasara 65](https://www.wisdomlib.org/hinduism/book/manasara-english-translation/d/doc421113.html)). Landmarks: skull 84, brows 121, eyes 131, nose 151, chin 180, shoulders 212, nipples 262, navel 350, crotch 440, knees 596, ankles 752, soles 790. Seated figures (400 x 640) keep the same head and torso; the crossed legs and the lotus seat replace the legs. Later views must hit the same lines.
2. **Faces** on the Loomis thirds: eyes at half the head; the lotus-petal eye (almond, heavy upper lid, a kohl line lifting at the outer corner); bow brows rising to the outer third; a line-and-shadow nose; a full lower lip; corners lifted slightly. Lowered lids for meditative figures (Jina, Buddha, Shiva as yogi).
3. **Light** from the viewer's upper left (the storyteller's lamp): two-tone cel shadow on the right of every form, a soft light plane on the left, a thin rim light on the shadow edge, warm shadow tones (never grey).
4. **Anatomy** in few shapes: muscle stations along each limb (deltoid, biceps, forearm, quadriceps, calf), one contour per limb so no seams show at knee or ankle; abdominal detail soft (no bodybuilder grid); the Jina and the Buddha get the smooth "lion-like" torso; Ganesha keeps his belly (*Lambodara* is iconography); women are covered and athletic, never sexualised.
5. **Indian sculptural marks**: *kambu-griva* (three conch lines on the neck) on Rama, the Jina and the Buddha; *ajanubahu* (arms reaching the knees) where the text gives it.
6. **Ornament is data**: crown, kundala, haar, keyura, kankana, sacred thread, girdle are separate helpers, so a figure's jewellery is a list, not a drawing.
7. **Attributes stay in the same hand** in every shot and every view. Weapons and staffs: Rama's bow left, arrow right; Hanuman's gada in the right fist resting on his right shoulder, the left fist on his hip (the heroic Veera form of 2026-11-24, which replaced the first human build's mace in the left hand with the right raised); Shiva's trident left, right raised; Athena's spear right, shield left; Odin's spear right.
8. **Kitsch traps**: calendar gloss, neon-blue skin, Western or Marvel armour, a bearded human Hanuman, a cartoon monkey, bodybuilder bulk, winged helmets on Odin.

## 4. Identity blocks

Each block is the single source of truth for a figure: the code follows it, a later view (three-quarter, profile, back, 3D) must keep it, and a generated still's prompt copies it.

### Rama (`rama-human`)
- **Telling**: Valmiki. Forest years (default) or royal (`attire: 'royal'`).
- **Text**: broad shoulders, long arms "right up to his knees", conch-shaped neck, rounded chest, large eyes (Bala 1.9-11, [ramayana.com](https://ramayana.com/valmiki-ramayana/bala-kanda/sarga-1)); lotus-petal eyes, face like the full moon, coppery eye-rims, "dark-brown complexion" (*shyama*), square-built, three spirals in the hair (Sundara 35.8-19, [ramayana.com](https://ramayana.com/valmiki-ramayana/sundara-kanda/sarga-35)); bark garments (Ayodhya 37.7-14); hair matted with banyan sap into "a rounded mass of matted locks" (*jata-mandala*) (Ayodhya 52.67-70).
- **Drawn**: dark skin in two readings, `tone: 'blue'` (cloud-dark, the painting tradition, default) and `'brown'` (the text read literally); clean-shaven; hair parted at the centre and coiled into a bound jata knot, long locks behind the shoulders; bark-cloth dhoti and a twisted fibre girdle; no jewels in exile; Vaishnava tilak; sacred thread; quiver strap; Kodanda bow in the left hand grounded beside him, an arrow point-down in the right; a quiet smile. Royal: yellow silk, kirita crown, kundala, pearl haar, keyura, kankana, a red sash with a jewelled clasp.
- **Heroic (2026-11-24, default)**: `warrior` preset, about 8.5 heads; deep chest, heavy traps and knee-long arms (Bala 1.1.10: broad-chested, *ajanubahu*); the Chola bronze pose: he leans on the tall Kodanda with his left hand (Harvard, V&A), and his right hand raises an arrow glowing with tejas. The quiver is behind his left shoulder. The uttariya and long locks stream back in one wind; the brows are level, calm power. A `tejas` aura (sun disc, 24 rays, gold ring) puts a warm rim light on him. The bark dhoti is knee-length so the legs read.
- **Check**: the beard. No verse says he is shaved; Gita Press's footnote to Sundara 35.20 lists "the moustaches and the beard" among fine things, which looks like the commentators' list, not the root verse. Clean-shaven is the image convention, kept here. The tilak and sacred thread are image tradition (temple bronzes), not Valmiki.

### Hanuman (`hanuman-human`)
- **Text**: "like a mountain in size" (Sundara 1.29); "like the sun risen in the east" (Sundara 31.19); the name from his jaw, struck by Indra's thunderbolt "on the left side of your chin" (Kishkindha 66.23-24, [ramayana.com](https://ramayana.com/valmiki-ramayana/kishkindha-kanda/sarga-66)); fights with trees, rocks and an iron bar (Sundara 42.35-39). The Chalisa: golden hue, earrings, curly hair, a thread of munja grass.
- **Drawn**: a vanara head (bare face mask, heavy brow, flat broad nose, full upper lip, a strong jaw with a mark on his left side, round ears, a fur ruff framing the face) on a mighty human body (the Chola convention); golden-tawny fur with fur strokes and a paler chest; tail raised and arched over the head; curly hair under a kirita; hoop earrings; munja thread; gold necklace and *udarabandha* belly band; keyura and kankana; short red dhoti with a gold hem. First human build (superseded by the heroic block below): `form: 'veera'` with the ribbed gada in the left hand and the right hand raised (fear not). `form: 'dasa'`: hands joined in anjali, no mace.
- **Heroic (2026-11-24, default)**: `titan` preset, about 7 heads; shoulders 3 head-widths, thick neck, massive arms and legs with fur. The iconic Veera pose: the great gada rests on his right shoulder at about 22 degrees, his right fist across his body and his left fist on his hip; the tail rises in a counter-curve on his left. Fierce angled brows; an `agni` aura of three flame rings. `form: 'dasa'` keeps the anjali.
- **Check**: the mace is later tradition (Ananda Ramayana, devotional verse), not Valmiki; for a Valmiki film prefer `dasa` or empty hands. No Valmiki verse found for a red face (Britannica's "red-faced" describes later images); we give the bare face a warm red-pink and keep the fur golden. Never a human beard; never comic.

### Shiva (`shiva-human`)
- **Text**: "like a silver mountain... wears the moon... the hide of the tiger" (Shiva Purana 1.20.52, [wisdomlib](https://www.wisdomlib.org/hinduism/book/shiva-purana-sanskrit/d/doc1940266.html)); only the neck is blue, from the poison (Bhagavata 8.7.43, [vedabase](https://vedabase.cc/sb/8/7/)); Nataraja's jata with Ganga, cobra, crescent, makara-kundala in one ear and patra-kundala in the other (National Museum).
- **Drawn**: ash-pale grey-blue body (vibhuti), blue throat, three eyes (vertical third eye over the tripundra), lowered yogi's eyes; jata-makuta piled high and bound, crescent on his left, the Ganga running out of the knot; long matted locks behind the shoulders; cobra coiled at the neck with the hood beside his head; rudraksha mala and rudraksha bands; sacred thread; tiger-skin wrap with a paw at the front; trident with the damaru in the left hand; right hand raised (fear not); mismatched earrings. Lean ascetic build.
- **Heroic (2026-11-24, default)**: `ascetic` preset (lean, powerful). Eyes open in calm power. The matted locks fly out in waves on both sides like Nataraja's. The trishula (flame-curved side prongs, crescent, gold kalasha, red ribbons) is planted in his left hand, the damaru hangs beneath the prongs, and his right hand is raised (fear not). A `cosmic` aura: a night disc of stars ringed by 13 flame tongues, as on the Chola Nataraja prabhavali (Salar Jung Museum).
- **Check**: an all-blue body is calendar art, not the text; keep the body pale.

### Ganesha (`ganesha-human`)
- **Text**: Ganapati Atharvashirsha: one tusk, four hands bearing noose, goad, tusk and the boon gesture, the mouse on his banner, "red, pot-bellied, with winnowing-fan ears, clad in red" ([vedapath](https://vedapath.app/en/upanishads/ganapati/11)). Met Kalacuri Ganesha: a snake as sacred thread ([Met 74100](https://www.metmuseum.org/de/art/collection/search/74100)).
- **Drawn**: red skin (`tone: 'gold'` for the common later colour); twin-domed brow, small kind eyes, tripundra; winnowing-fan ears with a gold rim; trunk turning to his left to a modaka; right tusk broken (held in his lower right hand), left tusk whole; goad (upper right), noose (upper left), boon gesture (lower left); great belly with a serpent belt; pearl string and sacred thread; crimson dhoti; seated on a lotus, the mouse on the plinth; kirita.
- **Heroic (2026-11-24, default)**: broad, muscled shoulders and pecs with heroic arms. The belly is kept (*Lambodara* is iconography). The ornate armoury ankusha (upper right) and pasha (upper left). A `lotus` aura: a gold glow, a 16-petal mandala and rays.
- **Check**: which tusk is broken and which way the trunk turns vary by image and region; say which image the film follows.

### Athena (`athena-human`)
- **Text**: *glaukopis* (grey-blue or "glaring" eyes; Pausanias saw a statue with blue eyes, 1.14.6); the fringed aegis with the Gorgon's head and the golden crested helmet (Iliad 5); the Parthenos: a tunic to the feet, Medusa's head on the breast, a sphinx and griffins on the helmet, a spear, the shield at her feet with a serpent (Pausanias 1.24.5-7, [Uppsala](https://periegesis.abm.uu.se/en/reports.php?reportid=24)); the Varvakeion copy: belted peplos, snake belt, raised cheek guards, three crests ([Wikipedia](https://en.wikipedia.org/wiki/Varvakeion_Athena)).
- **Drawn**: ivory flesh, grey-blue eyes, a calm severe face; centre-parted waves at the temples and long locks over the shoulders; Attic helmet with raised cheek guards and three red crests; peplos to the feet with its overfold and meander borders; snake belt; scaled aegis with a fringe of snakes and the gorgoneion; spear in the right hand; the great shield on its rim at her left with the gorgoneion. Upright, covered, no armour cliches.
- **Heroic (2026-11-24, default)**: `goddess` preset, athletic. The Promachos pose (Acropolis Museum statuettes): her right arm raises the spear level overhead, the round aspis (meander rim, gorgoneion) is forward on her left arm, and the helmet's crest sweeps back. The peplos and a red himation stream in the wind; her gaze is level and fearless. A `radiant` aura (no ring: Greek gods have no halo); the radiance is artistic licence.
- **Check**: the Parthenos holds a Nike in her right hand; this figure gives the right hand the spear (closer to the Promachos). The owl is omitted until a primary source fixes its pose.

### Odin (`odin-human`)
- **Text**: his eye in Mimir's well (Voluspa 28); "he wore a dark-blue mantle and called himself Grimnir", the Hooded One; names *Sithhott* (broad hat), *Sithskegg* (long beard), *Harbarth* (greybeard) (Grimnismal, [sacred-texts](https://sacred-texts.com/book/the-poetic-edda/grimnismol)); "a slouched hat... huge, seeming-ancient, and one-eyed", linen breeches bound to the leg (Volsunga saga 3); ravens Huginn and Muninn (Grimnismal 20); Gungnir and Draupnir (Skaldskaparmal).
- **Drawn**: old, tall, weathered; his right eye closed and scarred (the Torslunda die lacks the right eye); long grey beard and moustache; broad slouched hat shading the brow; dark-blue mantle with the hood fallen back and a cloak to the ankles; wool tunic, belt, breeches bound with leg-wraps; Gungnir in the right hand; Draupnir on the left arm; a raven on each shoulder.
- **Heroic (2026-11-24, default)**: `elder` preset, broad and huge. His one eye burns ice-blue (*Baleyg*, "flaming-eyed") and the given eye is closed and scarred, under fierce brows. The great cloak spreads in a storm wind, with the beard and hair blown the same way. Gungnir is planted in his right hand, its blade lit cold; Draupnir is on his left arm. Huginn is perched on his right shoulder and Muninn flies to his raised left hand. A `storm` aura of cold light and wind arcs (the Norse sources give no halo; this is artistic licence).
- **Check**: which eye is not stated in the Eddas; keep it the same in every shot. No valknut or other hate-appropriated symbols as decoration.

### Tirthankara (`tirthankara-human`)
- **Text**: "hands hanging down to the knees, the Shrivatsa on his breast, a placid look, naked, young and beautiful" (Brihat Samhita 57.45, [siva.sh](https://www.siva.sh/brihat-samhita/58/45)); slight build, very wide shoulders, narrow waist, very long ears ([Jain art](https://www.wikiwand.com/en/articles/Jain_art)); the lanchhana on the pedestal is the only identifying mark ([JAINpedia](https://jainpedia.org/article/themes/principles/holy-symbols/emblems-of-the-24-jinas/)); Mahavira golden, with a lion ([Government Museum Chennai](https://govtmuseumchennai.org/museum-section/jain-sculptures/mahavira)).
- **Drawn**: padmasana and dhyana (right hand over left), smooth torso, shrivatsa, long ears, tiny tight curls with no ushnisha, lowered eyes and a calm half-smile; no ornament; rayed halo and triple umbrella; lion in the plinth window. `emblem` changes the lanchhana (bull, deer, conch, snake: serpent hoods); `sect: 'svetambara'` gives open, inlaid eyes, an applied gold tilaka and a lower garment.
- **Check**: the hair (small curls in museum pieces, smooth in some devotional accounts), the skin colour for Tirthankaras other than Mahavira, and the sect; never give a Jina the Buddha's ushnisha or robe.

### The Buddha (`buddha-human`)
- **Text**: golden skin, palms reaching the knees standing, "the crown of his head is like a turban" (ushnisha), the white tuft between the brows (urna) (DN 30, [SuttaCentral](https://suttacentral.net/dn30/en/sujato)); later lists add right-turning curls and long ears ([Wikipedia](https://en.wikipedia.org/wiki/Physical_characteristics_of_the_Buddha)); bhumisparsha: the right hand over the knee, fingers to the earth, the left in the lap ([imp-art](https://imp-art.org/articles/bhumisparsha-mudra/) [blog]).
- **Drawn**: golden skin; snail-shell curls in dark blue-black over the ushnisha; urna; long pierced earlobes; lowered eyes, faint smile; ochre robe over the left shoulder, right shoulder bare; right hand to the earth, left in the lap; plain halo; lotus seat.
- **Check**: not for a scene set in the aniconic period; robe arrangement by school (Gandhara covers both shoulders).

## 5. Next: more views

Planned order, after the front views are approved: three-quarter front, profile, three-quarter back, back (Ocelot draws "front, three-quarters front, profile, three-quarters back, back", [Film Education](https://filmeducation.org/princesquest/background.html)). Rules: the same landmark lines; one set of parts per view sharing pivots, swapped rather than rotated (the cut-out rig practice in Toon Boom and Moho); one-sided details stay on the correct side (Rama's quiver strap, Odin's closed eye, Ganesha's broken tusk, Shiva's crescent); every view passes a solid-black silhouette test with the figure's hook visible (Rama: jata and bow; Hanuman: tail; Shiva: jata and trident; Ganesha: ears and trunk; Athena: crest and spear; Odin: hat and ravens; Jina: ears and umbrella; Buddha: ushnisha and robe edge). The 3D figures (section 9) now give a five-view turnaround of every figure on the same identity block; use them as drawing reference for these 2D views (same lines, same sides), not as tracing sources.

## 6. Weapon iconography (the armoury, `src/studio/kits/mythic/armoury.js`)
Research 2026-11-24. Forms marked **[synthesis]** are drawn for heroic legibility where no source fixes the shape; review sheet `tests/mythic-kit/armoury.html`.
| Weapon | Held by | Sourced | Drawn |
|---|---|---|---|
| Kodanda (bow) | Rama | Rama leans on a tall bow with his left hand and holds an arrow in his right ([Harvard Chola bronze](https://harvardartmuseums.org/collections/object/206499), [V&A](https://collections.vam.ac.uk/item/O62774/sculpture-figure-unknown/)) | a tall lacquered recurve (about the figure's height), gold bands, a bound grip, gold curl tips, a taut string **[synthesis]** |
| Shara and tuna (arrow, quiver) | Rama | Agastya's gifts: a divine bow, arrows, two inexhaustible quivers [blog](https://mythlok.com/weapons/kodanda/) | a leaf-headed gold arrow with tejas glow, red and white vanes; a banded quiver of fletchings **[synthesis]** |
| Gada (mace) | Hanuman | "a spherical head mounted on a shaft, with a spike on the top" ([Wikipedia](https://en.wikipedia.org/wiki/Gada_(mace))); often raised or resting on the shoulder [blog](https://de.hdasianart.com/en/blogs/news/hanuman-symbolism) | a great fluted gold head (7 ribs), a jewelled equator band, a lotus collar, a crown finial and spike, a banded shaft with a red grip and pommel; on the shoulder at about 22 degrees **[synthesis for flutes and finial]** |
| Trishula, damaru | Shiva | three prongs on a long shaft, often planted upright ([Wikipedia](https://en.wikipedia.org/wiki/Trishula)); the damaru, an hourglass drum | a leaf-bladed centre prong, side prongs sweeping out and up like flames from a crescent, a gold kalasha, red ribbons; the damaru tied beneath **[synthesis for the prong curve]** |
| Ankusha, pasha, parashu | Ganesha | goad, noose and axe (Ganapati Atharvashirsha: noose and goad) | a spike and back-curving hook on a gold rod; a corded loop with a knot and tassel; a crescent axe |
| Dory, aspis | Athena | the hoplite spear with a sauroter butt-spike ([Wikipedia](https://en.wikipedia.org/wiki/Dory_(spear))); the Parthenos: a shield at her feet, Medusa's head on her breast (Pausanias 1.24.7) | a bronze leaf blade with a midrib, ash shaft, sauroter; a round bronze aspis with a meander rim and a gorgoneion boss (the boss is a common hoplite option, not the Parthenos) |
| Gungnir | Odin | forged by the sons of Ivaldi (Skaldskaparmal); runes cut on its point (Sigrdrifumal 17); a rider with spear and two ravens on Vendel helmet plates ([Wikipedia](https://en.wikipedia.org/wiki/Gungnir)) | a long pattern-welded leaf blade with a fuller and abstract incised marks (no real runes), a winged socket with gold bands, a dark ash shaft, a cold glow **[synthesis]** |
| Library for later figures | | Sudarshana chakra (serrated, flaming disc), shankha, vajra, khadga, venu, padma, Mjolnir (short handle: [Wikipedia](https://en.wikipedia.org/wiki/Mj%C3%B6lnir)), keraunos (a double-ended flaming bolt in Greek art [blog](https://mythoblog.com/en/mythologies/greek/objects/thunderbolt-zeus/)) | drawn at the grip, pointing up; see the armoury sheet |

## 7. The heroic build (owner's direction, 2026-11-24: heroic aesthetic, muscularity and aura over accuracy)
Applies to Rama, Hanuman, Shiva, Ganesha (body only; the belly stays), Athena and Odin. It does **not** apply to the Tirthankara and the Buddha: their calm, smooth "lion-like" torsos are the iconography.

- **Presets** (`HERO` in `figures-human.js`): `warrior` (Rama), `titan` (Hanuman), `ascetic` (Shiva), `goddess` (Athena), `elder` (Odin). Each sets the neck, traps, shoulder, lats, waist, hips, arm and leg bulk, the head scale and the stance; the measured results are in section 8.
- **Head scale** about the chin, 0.86-0.94: about 8.5 heads for heroes, about 7 for Hanuman, against 7.3 before ([blog](https://discover.oreateai.com/discover/mastering-the-heroic-silhouette-in-superhero-outline-drawing): heroes 7.5-8, gods 9; shoulders 2-3 head-widths).
- **Muscle as cel shapes**, from drawing guides ([clip-studio](https://tips.clip-studio.com/en-us/articles/10745) [blog], [egaco](https://en.egaco.com/guide/20413/) [blog]):
  - a pec crescent and the lit upper planes;
  - the deltoid cap and its separation;
  - the biceps lens and the triceps edge;
  - serratus fingers on the shadow side;
  - abs implied 2 x 3 with the shadow on each lower edge;
  - the obliques and Apollo's belt;
  - the quad teardrop and sweep;
  - the calf bean.
- **Stance and pose:**
  - A wide A-stance; weapons held clear of the body.
  - Each pose comes from the tradition's own iconic image: the Chola bronze, the Promachos, Nataraja's flying locks.
  - The silhouette test is a review sheet (`figures-human-silhouette.png`).
- **Aura:**
  - `M.auras.make(kind)`: a radial glow with rays and a ring as rotatable children, kept in every look.
  - The glow colour is passed to every builder as a rim light on both edges ([Salar Jung prabhavali](https://artsandculture.google.com/story/circle-of-flames-salar-jung-museum/jQUhLSrMxa3pWw) for the flames).
- **One wind** for hair, cloth, cloak and beard.
- **Expression:** `brow: 'level'` (calm power) or `'fierce'`; Odin's living eye glows.
- **Accuracy kept:** every emblem and attribute, the hand that holds it, the skin colours, the sacred marks.
- **Licence taken:** musculature beyond the texts; auras on Athena and Odin; the mace on Hanuman (later tradition); flame-curved trishula prongs; the gada's flutes and finial.

## 8. Proportion canon and measurements (2026-11-24, after review: "waist too high", too wide)
**Canon** (Andrew Loomis, *Figure Drawing for All It's Worth*, the ideal figure: [Wikisource p. 19](https://en.wikisource.org/wiki/Page:Andrew_Loomis,_Figure_Drawing_for_All_It%27s_Worth.pdf/19); [Proko summary](https://www.proko.com/course-lesson/human-proportions-idealistic-figures/downloads) [blog]). Vertical values are head units (H, skull top to chin) from the top of the head.
- **Vertical lines:** the nipples at 2 H, the navel at 3 H and the crotch at 4 H.
- **Arms:** elbows on the navel line; the wrist just below the crotch.
- **Height:** 8 H for the ideal figure. Heroes and gods are allowed 8-8.8 H, a titan 7.4-8.2 H.
- **Widths:** shoulders 2 1/3 H, the waist "a little wider than one head", hips 1.5 H.

**Allowed bands** (`tests/mythic-kit/measure.js`, `CANON`):

| Type | Heads | Crotch | Knee | Waist line | Shoulders | Waist width | Hips |
|---|---|---|---|---|---|---|---|
| male | 8-8.8 | 3.9-4.25 | 5.8-6.4 | 2.7-3.1 | 2.3-2.6 | 1.05-1.3 | 1.45-1.75 |
| titan | 7.4-8.2 | 3.7-4.15 | 5.4-6.1 | 2.65-3.05 | 2.45-3.0 | 1.25-1.55 | 1.6-1.95 |
| female | 7.8-8.6 | 3.9-4.25 | 5.8-6.4 | 2.65-3.05 | 1.9-2.2 | 0.95-1.2 | 1.45-1.75 |

Hanging arms are also checked: elbow 2.75-3.25 H, wrist 3.9-4.4 H.

**What the review found** (measured on the drawn geometry, first heroic build):

| Figure | Problem |
|---|---|
| All | Shoulders 3.1-3.3 H, about 35% too wide. |
| All | Hips 2.2-2.3 H. The thighs were too thick, so the pelvis read wide and short. |
| All | Elbows at 2.4-2.7 H and wrists at 3.2-3.9 H. Short upper arms put the elbows above the navel, which made the waist look high. |
| All | Belts as tall as cummerbunds (from y 330). |
| Hanuman | Only 6.7 H, crotch at 3.3 H, knee at 4.9 H: a long body on short legs. |
| Odin | A belt waist of 0.6 H. |

**What changed:**
- **Presets:** narrower shoulders and lats, and a hip half-width per preset.
- **Thighs:** thinner thigh stations.
- **Arms:** placed by length. `armJ` uses two-bone IK with an upper arm of 1.45 H and a forearm of 1.15 H, so a hanging arm puts the elbow on the navel and the wrist below the crotch.
- **Belt:** the girdle now sits on the navel (y 340-379).
- **Dhoti:** it falls from the navel and widens at the hips instead of flaring from the belt.
- **Hanuman:** head scale 0.78, which gives 7.9 H.

**Measured now:**

| Figure | Heads | Waist | Crotch | Knee | Shoulders | Waist width | Hips | Hanging arm (elbow / wrist) |
|---|---|---|---|---|---|---|---|---|
| Rama | 8.41 | 2.98 | 4.10 | 6.22 | 2.58 | 1.17 | 1.70 | 2.86 / 3.99 |
| Hanuman | 7.92 | 2.76 | 3.83 | 5.84 | 2.78 | 1.34 | 1.84 | (both arms bent) |
| Shiva | 8.41 | 2.98 | 4.10 | 6.15 | 2.54 | 1.10 | 1.65 | 2.86 / 3.99 |
| Athena | 8.22 | 2.91 | 4.03 | 6.07 | 1.93 | 0.98 | 1.57 | 2.82 / 3.93 |
| Odin | 8.00 | 2.85 | 3.93 | 5.88 | 2.53 | 1.25 | 1.68 | 2.85 / 3.98 |

**Enforced:**
- `tests/test-mythic.py` fails if any standing heroic figure or variant leaves its band.
- `python tests/mythic-kit/render-figures.py` writes `proportions.png`: each figure with the canon's head lines from its own skull and chin, its measured waist and knee rows, and its numbers.

## 9. 3D figures (Blender, 2026-11-25)

All eight figures also exist in 3D, built in code in Blender 5.2.4 from the identity blocks in section 4 (the blocks stay the single source of truth). Kit `src/blender/mythic3d/`, command `scripts/mythic3d.py`, test `tests/test-mythic3d.py`, output `projects/_mythic-figures/3d/` (gitignored). They are review renders and drawing reference (the five-view turnaround that section 5 plans), not film plates: a film that wants a 3D god goes through `scripts/visual-director.py` (a `mythic-figure` plate template is the open next step).

```bash
python scripts/mythic3d.py render                          # all eight, painted look, hero + five-view turnaround + head
python scripts/mythic3d.py render --figures shiva --look bronze
python scripts/mythic3d.py render --figures rama --opt "rama:tone=brown;attire=royal" --tag royal-brown
python scripts/mythic3d.py sheets                          # turnaround-<id>-<look>.png, gallery-<look>.png
python tests/test-mythic3d.py                              # builds all eight (no render) under the host lock
```

**How a figure is made** (the 2D layer order, in 3D):
1. **Skin:** one metaball surface per figure (bone capsules plus muscle masses as ellipsoids, given in visible half-extents), so the body is one continuous skin with no seam at the shoulder, hip, knee or neck. Presets mirror `HERO`: `warrior`, `titan`, `ascetic`, `goddess`, `elder`, `calm` (the Jina and the Buddha: smooth torso, lower trapezius), `ganesha` (the belly kept). Poses use two-bone IK; hands are built from per-finger curls (grip around a weapon's axis, open, varada, dhyana, earth-touching, anjali).
2. **Sculpt:** displacement along the normal: the pectoral underline, linea alba and the three tendinous lines, Apollo's belt, the deltoid edge, quad and calf separations, the spine; the face in head space (nose, almond eyes cut behind the eyeball so the lids wrap it, lid folds, lips and the mouth line, the chin); the *kambu-griva* on Rama, the Jina and the Buddha.
3. **Paint:** per-vertex colour from analytic regions: skin from the text, lips, bow brows, kohl, the hair cap, the tilak (Vaishnava U, tripundra, the Jina's gold mark, the urna), Shiva's blue throat and third eye, Hanuman's red face mask in golden fur, painted cloth (the peplos top and aegis, Odin's tunic and leg-wraps, the Buddha's robe, the dhotis over a seated lap).
4. **Dress, armoury, aura:** meshes fitted with ray casts: skirts whose sections drape over the body below them, pleated falls, rings that hug a limb or the torso (cast from inside, so a nearby hand never pulls them out), cords and straps on the skin, beads, crowns, jata coils and flying locks, curl caps and the ushnisha, the Attic helmet, the slouched hat, the cloak; the armoury in 3D (kodanda, shara, tuna, gada, trishula with damaru, ankusha, pasha, dory, aspis, gungnir, modaka); the auras as the plate of a temple image (tejas, agni, cosmic prabhavali, lotus mandala, radiant and storm with no ring, rayed and plain haloes); lotus seat, chhatra, mouse, lion, ravens, cobra, crescent, Ganga.

**Looks:** `painted` (default; a painted image: polychrome, a cavity term darkening folds) and `bronze` (one cast metal with patina, like a Chola or Greek bronze; glows not drawn).

**Studio:** the warm paper cyclorama, the storyteller's lamp as key light from the viewer's upper left, a rim light in the aura's colour, a long lens. The figure stands on a turntable so all five views share the same light and landmarks. The hero shot is a low, reverent three-quarter view (sacred images stay high; the camera never goes below the floor or looks down on a deity).

**Checked by `tests/test-mythic3d.py`:** every attribute in the hand its block gives (bow left, arrow right; gada on the right shoulder; trishula left, crescent on his left, makara earring right and patra left; goad upper right, noose upper left, broken tusk lower right and the shorter right tusk; aspis left; Gungnir right, Huginn on the right shoulder, Muninn at the left hand); Odin has one eyeball; no ring or halo on Athena; the ushnisha on the Buddha and not on the Jina; the mouse and the lion present; nothing below the floor; two builds give identical geometry (no randomness, no time).

**Check before release (a person):**
- The faces are a sculpted-statue stylisation, not portraits; judge them in the head close-ups.
- Garments are rigid drapes (no cloth simulation); the seated legs merge into a lap block, as in seated images.
- The 3D lanchhana exists for the lion (Mahavira) and the serpent hoods (Parshvanatha) only; other emblems are refused, never drawn as the lion.
- Everything marked **check** in section 4 applies to the 3D figures unchanged (Rama's beard, Hanuman's mace as later tradition, Athena's Nike, which eye Odin gave).
- Rendered on the Windows host only (Intel Iris Xe, EEVEE); not yet on the M2 render host.
