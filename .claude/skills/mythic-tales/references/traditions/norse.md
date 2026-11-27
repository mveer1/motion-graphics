# Tradition pack: Norse

## Tellings and translations
- The **Poetic Edda** (Codex Regius) and Snorri Sturluson's **Prose Edda** (Iceland, around 1220, written in a Christian setting with a euhemerising prologue) ([Wikipedia](https://en.wikipedia.org/wiki/Prose_Edda)). Say "Snorri says...", "in the Völuspá...", not "the Vikings believed".
- Public-domain English translations safe to quote: Henry Adams Bellows, *The Poetic Edda* (1923); Arthur Gilchrist Brodeur, *The Prose Edda* (1916). Cite poem and stanza or chapter.
- Heathenry is practised today, including universalist groups: the same "tradition says" phrasing applies; do not equate Norse imagery with extremism.

## Iconography checklist (check on the source and the object shown)
| Figure | Attributes | Common errors |
|---|---|---|
| Odin | One eye (given at Mimir's well), spear Gungnir, ravens Huginn and Muninn, wolves, the eight-legged horse Sleipnir, wide hat and cloak | Marvel's Odin; two eyes |
| Thor | Hammer Mjölnir, red beard, iron gloves and belt of strength, goat-drawn chariot; wife Sif (golden hair) | Blond Marvel Thor; Loki as his brother |
| Loki | Son of the giant Fárbauti; Odin's blood-brother; a shape-changer | Thor's brother (that is Marvel) |
| Freyja | Cats drawing her chariot, the necklace Brísingamen, a falcon cloak | |
| Frigg | Odin's wife, foreknowledge, spinning | |
| Yggdrasil | The world-tree with the well, the eagle, Ratatoskr, Níðhöggr at the roots | |

Thor's mother is Jörð; the winged helmet comes from Carl Emil Doepler's 1876 costumes for Wagner, not from the Viking age ([Glanz & Gravur](https://www.glanzundgravur.de/en/blog-marvel-thor-faktencheck.html), [TheCollector](https://www.thecollector.com/real-thor-vs-marvel-thor/) [Tier 2]).

## Symbols to keep out of decoration
The ADL lists the **valknot** ([ADL](https://dc.adl.org/resources/hate-symbol/valknot)) and the **Othala rune** ([ADL](https://dc.adl.org/resources/hate-symbol/othala-rune)) as appropriated by white supremacists; the **sonnenrad** ("black sun") is a neo-Nazi symbol ([The Conversation](https://theconversation.com/the-sonnenrad-used-in-shooters-manifestos-a-spiritual-symbol-of-hate-183319)). Never use them as background texture or borders. If a historical artefact shows one, say in narration what it is and what it meant then. Prefer neutral Viking-age art: Gotland picture stones, the Oseberg textiles, runestones. The kit's `knot` border is a neutral interlace.

## Art forms
Gotland picture stones read in stacked fields ([Wikipedia](https://en.wikipedia.org/wiki/Picture_stone)); runestones were painted when raised ([Wikipedia](https://en.wikipedia.org/wiki/Runestone)); Mammen, Ringerike and Urnes animal ribbons; the Oseberg procession strip ([Museum of the Viking Age](https://www.vikingtidsmuseet.no/english/viking-age/design-and-craft/the-oseberg-textiles.html)). Colours were not verified: measure from museum photographs. Style: `carved-relief` for stones and manuscripts (the 17th-18th century Icelandic manuscript illustrations on Commons, e.g. "NKS 1867 4to, Odin on Sleipnir", are public domain), `shadow-lantern` for the action, `cinematic-dark` only if the brief asks for Ragnarok at night.

## Runic and Old Norse text
No bundled font has runes; add a project font with `@font-face` (an OFL runic font, registered in `assets/`) before showing runes, and never show the three symbols above. Keep Old Norse spellings consistent (Mjölnir or Mjollnir, not both).

## Episodes and queries
- short: Odin's eye at Mimir's well; Thor's fishing for the world-serpent; how Sleipnir was born.
- mid: Baldr's death (`sacred-tale`); the binding of Fenrir; Idun's apples.
- long: the road to Ragnarok, from the Völuspá's creation to the world's renewal (`origin-myth` opening, chapters per sign).
- Queries: "Odin Sleipnir manuscript", "Thor Mjolnir manuscript", "picture stone Gotland", "Yggdrasil Edda" on `--source commons` (topical words avoid the battleship *Odin*).

## Figures in the kit
kits/mythic/figures.js: `odin` (one eye, wide hat, cloak, spear, two ravens). kits/mythic/figures-human.js: `odin-human` (heroic elder: the right eye given and scarred, the left burning ice-blue, long grey beard, broad hat, dark-blue mantle spread in a storm wind, Gungnir planted in the right hand, Draupnir on the left arm, Huginn on the right shoulder and Muninn flying to the raised left hand, a `storm` aura as artistic licence with no ring; `../figure-design.md`). 3D: `python scripts/mythic3d.py render --figures odin` (turnaround and hero, painted or bronze; `../figure-design.md` section 9). Border `{tradition: 'norse'}` (knot, urnes ribbon, chevron); never valknut, Othala or sonnenrad. No haloes. Not drawn yet: Thor, Loki, Freyja.
