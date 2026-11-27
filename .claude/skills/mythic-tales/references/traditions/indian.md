# Tradition pack: Hindu epics and Puranas

## Tellings and translations
Name one per film; record variants in `research.json`.
- **Ramayana**: Valmiki (Sanskrit; Rama a god-man within human limits), Kamban's *Ramavataram* (Tamil; plainly divine), Tulsidas's *Ramcharitmanas* (Awadhi; devotional), Krittivasi (Bengali), the Jain *Paumachariya* (Vimalasuri; Lakshmana, not Rama, kills Ravana) and the Buddhist *Dasaratha Jataka*. A. K. Ramanujan called them "tellings", not versions of one original ([summary](https://wagtail.ruralindiaonline.org/en/library/resource/three-hundred-ramayanas-five-examples-and-three-thoughts-on-translation/)).
- **Mahabharata**: attributed to Vyasa; cite the critical edition when a detail is contested.
- **Puranas**: Bhagavata (Krishna's childhood, Govardhan), Vishnu, Shiva, Markandeya (the *Devi Mahatmya*: Durga and Mahishasura).
- Public-domain English translations safe to quote: R. T. H. Griffith's Ramayan (1870-74), K. M. Ganguli's Mahabharata (1883-96). Cite book and chapter.

## Iconography checklist
**Verified** marks a museum source ([Met, Hinduism and Hindu art](https://www.metmuseum.org/essays/hinduism-and-hindu-art), [Met, Recognizing the gods](https://www.metmuseum.org/toah/hd/gods/hd_gods.htm)). **Check** marks items from secondary sources or general knowledge that a reviewer confirms before release (HAF, a museum page, a scholar).

| Figure | Attributes | Mount / companion | Common errors |
|---|---|---|---|
| Vishnu | Discus (chakra) and conch (shankha), tall crown, rich jewellery (**verified**); mace and lotus in four hands, dark or blue skin, yellow garment (**check**) | Garuda (**verified**); reclines on the serpent Shesha; consort Lakshmi | Merged with Krishna; Shiva's attributes |
| Shiva | Trident, serpent at the neck, crescent moon and matted locks, third eye; Nataraja the dancer (**verified**); damaru drum, Ganga in the hair (**check**); body ash-pale "like a silver mountain" (Shiva Purana 1.20.52) with only the throat blue (Bhagavata 8.7.43) | Nandi the bull (**verified**) | Durga's lion given to Shiva; dance in the wrong pose; an all-blue body (calendar art) |
| Parvati / Devi | Multiple arms show power (**verified**) | Lion (**verified**) | |
| Krishna | Dark or blue-toned skin, yellow pitambara, peacock feather, flute, tribhanga pose (**check**; "dark" not strictly blue) | Cows, Radha, the gopis | Always blue; adult Krishna in a childhood episode |
| Rama | Bow and quiver, dark skin, crown (**check**); Valmiki: arms to the knees, conch neck, lotus-petal eyes, "dark-brown" (*shyama*) skin (Sundara 35, Bala 1); in exile bark cloth (Ayodhya 37) and hair matted into a rounded knot (Ayodhya 52.67-70), no crown | Sita, Lakshmana, Hanuman | Tulsidas's fully divine Rama in a Valmiki film; a crown worn with bark cloth; neon-blue skin; short arms |
| Hanuman | Mace, monkey face, carrying the mountain in the Lanka war (**check**); Valmiki: "like the rising sun" (Sundara 31.19), the jaw struck by Indra (Kishkindha 66.23-24), fights with trees, rocks and an iron bar (Sundara 42); the mace is later tradition; Chola bronzes: a man's body, only the face and tail simian (Met 38945) | Rama | Comic monkey; mace dropped or mocked; a human beard; leather armour |
| Ganesha | Elephant head, one broken tusk, sweets (modak) (**check**); Atharvashirsha: red, pot-bellied, winnowing-fan ears, clad in red, noose, goad, tusk and boon gesture | The mouse (**check**) | One cause for the broken tusk given as the only one; both tusks whole |
| Durga | Many arms, weapons given by the gods, slaying Mahishasura (**check**) | Lion or tiger (**check**) | Gore; sexualised |
| Kali | Dark skin, tongue out, garland of heads, standing on Shiva (**check**) | | Horror treatment; use only with a reviewer |

Every human figure has no vahana: a mount marks a god ([Met, Recognizing the gods](https://www.metmuseum.org/toah/hd/gods/hd_gods.htm)).

## Art forms and palettes
Pattachitra (flat colour, black contour, patterned border), Phad (scroll, lamp reveal), kaavad (hinged panels, red ground), Rajput and Pahari miniatures (stacked colour planes, red-yellow-black ruled border), Kerala murals (five colours, colour by temperament), Tanjore (gold leaf). Details and sources: `../design-language.md` section 3. Style: `mythic-paper` or `painted-folio`; `shadow-lantern` with leather puppets for battles (Tholu Bommalata performs the epics).

## Sensitivities
The Hindu American Foundation's guidance on commercial use of Hindu images lists as offensive anything placed to be stepped on or likely to be destroyed, items with alcohol or meat, and significant modification of a deity, while noting that intent matters ([HAF](https://www.hinduamerican.org/projects/commercial-use-hindu-images-guide)). For animation that means:
- deity images high in the frame, never on the ground plane, never walked over, dropped, shattered, glitched or wiped;
- no comic props or edits in a deity's hands; no deity cast as a demon or a joke;
- no sexualisation (inference from the same guidance; no Tier 1 source found);
- living worship: many viewers pray to these figures. Tell, do not perform worship; no aarti or mantra used as a music bed.

## Framing
"In the Valmiki Ramayana, ...", "Hindus regard Krishna as an avatar of Vishnu", "the Bhagavata Purana tells it this way". Avoid "myth" as a synonym for false; "epic", "Purana" and "sacred story" are fine.

## Episodes by form and search queries
- short: Hanuman's leap to Lanka; Ganesha's broken tusk; Krishna lifting Govardhan; the Ganga caught in Shiva's hair.
- mid: the churning of the ocean (Samudra manthan); Narasimha and Hiranyakashipu (`boon-and-curse`); Savitri and Yama.
- long: Rama's exile to his return; the dice game to Kurukshetra.
- `myth-sources.py` queries: "Krishna Govardhan", "Shiva Nataraja", "Vishnu Garuda", "Ramayana folio", "churning of the ocean", "Durga Mahishasura", with `--culture "India|Nepal|Rajasthan|Pahari|Odisha"`.

## Figures in the kit
kits/mythic/figures.js: `rama`, `hanuman`, `shiva` (standing, profile), `ganesha` (seated, frontal); border `M.border({tradition: 'indian'})` (lotus, pattachitra, ruled); halo `prabhavali`. kits/mythic/figures-human.js: `rama-human` (forest or royal, blue or brown), `hanuman-human` (veera or dasa), `shiva-human`, `ganesha-human` (red or gold), human-like front views from the identity blocks in `../figure-design.md` (heroic since 2026-11-24: Rama leaning on the Kodanda with a tejas-lit arrow raised, Hanuman with the gada on his right shoulder, Shiva with the planted trishula and the raised right hand, Ganesha with muscled shoulders over the belly). 3D: `python scripts/mythic3d.py render --figures rama,hanuman,shiva,ganesha` (`../figure-design.md` section 9; options `rama:tone=brown;attire=royal`, `hanuman:form=dasa`, `ganesha:tone=gold`). Not drawn yet: Krishna, Vishnu, Devi/Durga, Sita, Lakshmana. The style samples tell Hanuman's leap (Valmiki, Sundara Kanda) in all four looks.
