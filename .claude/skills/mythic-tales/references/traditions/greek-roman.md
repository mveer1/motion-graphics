# Tradition pack: Greek and Roman

## Tellings and translations
- Homer (*Iliad*, *Odyssey*), Hesiod (*Theogony*, *Works and Days*), the Homeric Hymns, the tragedians; Ovid (*Metamorphoses*) and Virgil (*Aeneid*) for Roman tellings. Say which: Ovid's Arachne is not Homer's world.
- Public-domain English translations safe to quote: Samuel Butler (Homer, 1898-1900), H. G. Evelyn-White (Hesiod and the Homeric Hymns, Loeb 1914), Brookes More (Ovid, 1922). Cite book and line.
- Hellenic polytheism is practised today: "the Greeks told", "in Hesiod's telling" is courteous and accurate.

## Names: one system per film
Greek for Homer, Hesiod and Attic vases; Latin for Ovid, Virgil and Roman art ([name chart](https://thegreekandromangods.com/greek-roman-gods-names/) [Tier 2]).

| Greek | Roman | Attributes (check against a museum object) |
|---|---|---|
| Zeus | Jupiter | Thunderbolt, eagle, sceptre |
| Hera | Juno | Diadem, peacock |
| Poseidon | Neptune | Trident, horses |
| Athena | Minerva | Helmet, spear, aegis with the gorgon head, owl |
| Apollo | Apollo | Lyre, bow, laurel |
| Artemis | Diana | Bow, hound or deer, crescent |
| Hermes | Mercury | Winged sandals and cap, caduceus |
| Demeter | Ceres | Wheat, torch |
| Heracles | Hercules | Club, lion skin |
| Hades | Pluto | Helm, Cerberus |

Attributes in this table are general reference knowledge, not checked against a museum in this research; confirm on the object you show (the Cleveland Athena lekythos, CMA 2022.42, is a good Athena source).

## Art forms
Black-figure and red-figure vases: terracotta ground, near-black figures, incised detail, friezes that loop ([Met essay](https://www.metmuseum.org/essays/athenian-vase-painting-black-and-red-figure-techniques)); Roman mosaics: black-and-white geometric borders, a polychrome centre ([Getty](https://www.getty.edu/publications/romanmosaics/introduction/index.html)); Karagiozis shadow theatre ([SearchCulture.gr](https://www.searchculture.gr/aggregator/portal/thematicCollections/karagiozis?language=en)). Style: `carved-relief` for vases and reliefs, `painted-folio` with the `meander` border for a frieze, `shadow-lantern` for a Karagiozis-style action episode.

## Sensitivities and errors
- No film or game portrayal as source (Disney's Hercules, Percy Jackson, God of War).
- Do not mix Greek and Roman names, or a Roman telling's details into a Greek one.
- Assault and violence are frequent in the sources: imply by cut and silhouette, never depict sexual violence; say "abducted" when the source says so, without euphemism or spectacle.

## Episodes and queries
- short: Arachne and Athena; Prometheus steals fire; Icarus.
- mid: Persephone and the seasons (`origin-myth`); Midas (`boon-and-curse`); Orpheus and Eurydice.
- long: the twelve labours; the Odyssey's homecoming.
- Queries: "Athena lekythos", "Heracles amphora", "Prometheus", "Persephone", `--culture "Greek|Roman|Attic"`.

## Figures in the kit
kits/mythic/figures.js: `athena` (crested helmet, spear, shield, aegis; no owl drawn). kits/mythic/figures-human.js: `athena-human` (after the Parthenos and the Varvakeion copy: ivory flesh, grey-blue eyes, Attic helmet with three crests, peplos and overfold, snake belt, aegis with the gorgoneion; heroic Promachos pose since 2026-11-24: the spear raised level overhead in the right hand, the round aspis on the left arm, a `radiant` aura with no ring; `../figure-design.md`). 3D: `python scripts/mythic3d.py render --figures athena` (`../figure-design.md` section 9). Borders `{tradition: 'greek'}` (meander, egg-and-dart, wave) or `'roman'`. No haloes on Greek or Roman gods. Not drawn yet: Zeus, Heracles.
