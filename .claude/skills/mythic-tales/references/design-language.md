# Design language for mythic films

Distilled from web research on 2026-11-23. Every source is linked; **[blog]** marks a secondary source to cross-check, and every hex value is an estimate from a pigment name (no source gives hex codes). Learn techniques, never assets: no frames, characters or compositions are copied from any film below.

## 1. Choose the look

| Style system | Picture | Best for | Kit emphasis |
|---|---|---|---|
| `mythic-paper` (default) | Rag paper diorama under a lamp; deckle-edged sheets; duotoned museum plates; gold leaf | Any tradition; first choice for a short | `stage`, `sheet`, `plate`, `halo`, `place`, `rise`, `flicker` |
| `shadow-lantern` | Lamp-lit screen; jointed silhouettes or translucent dyed leather with punched holes | Battles, journeys, chases; a narrator-puppet frame; Tholu Bommalata, Karagiozis | `puppet` (`look: 'leather'` or `'silhouette'`), `pose`, `sway`, `lampTo` |
| `painted-folio` | Ivory folio, ornament border, register strips, scrolls and folding panels | Traditions with a painted manuscript or scroll form: Pattachitra, Kalpasutra, Phad, kaavad, vase friezes | `border`, `scroll`/`unroll`, `doors`/`open`, `cartouche` |
| `carved-relief` | Museum light on stone, bronze, terracotta; cut-out photographs in 2.5D; spaced inscriptional capitals | Stories told through surviving artefacts: temple sculpture, Greek vases, Roman reliefs, Gotland picture stones | `plate` (`frame: 'cutout'`), `stage` parallax, `credit` |
| `cinematic-dark` | Night and dread | Only when the brief asks (Ragnarok, Kali's battle) | lamp as the only light |

One film may borrow a dialect per narrative layer, as *Sita Sings the Blues* did (myth in miniature flats, narrators as shadow puppets, the present in a different line) ([Wikipedia](https://en.wikipedia.org/wiki/Sita_Sings_the_Blues)). Keep it to two dialects and give each a job.

## 2. Signature moves and how the kit does them

| Move | Source of the idea | Kit |
|---|---|---|
| Backlit tint with dark jointed silhouettes | Lotte Reiniger, *Prince Achmed* (cut-outs, tinted backlit grounds, an early multiplane) ([Wikipedia](https://en.wikipedia.org/wiki/The_Adventures_of_Prince_Achmed), [multiplane](https://en.wikipedia.org/wiki/Multiplane_camera)) | `puppet({look: 'silhouette'})` on `shadow-lantern`, `sway`, `pose` |
| Three canonical angles only (side, front, three-quarter) | Michel Ocelot ([Wikipedia](https://en.wikipedia.org/wiki/Michel_Ocelot)) | Draw figures in profile; never rotate a puppet in 3D |
| Parallax planes that overlap | Multiplane camera; 3+ textured layers, far slower ([ProVideo Coalition](https://www.provideocoalition.com/animating-parallax-images-in-after-effects-and-apple-motion/)) | `stage.layer(0..5)` + `Studio.space.camera` |
| Danger palette swap | Cartoon Saloon, *The Secret of Kells*: the world turns red, black and white only for danger ([Wikipedia](https://en.wikipedia.org/wiki/The_Secret_of_Kells)) | `tint(tl, world, from, to, {color: '--c-accent'})` |
| Lamp carried across a scroll | Phad: at night the Bhopi lifts a lamp to each scene while the Bhopa sings ([Wikipedia](https://en.wikipedia.org/wiki/Phad_painting), [Artshaili](https://artshaili.com/phad-painting-of-rajasthan/) [blog]) | `lamp` + `lampTo` |
| Hinged panels opening to nested story tiers | Kaavad: doors open to Vishnu, flaps to the Ramayana and Bhagavata, inner doors to Sita ([V&A](https://collections.vam.ac.uk/item/O169083)); red ground, mineral colours ([Google Arts & Culture](https://artsandculture.google.com/story/kavad-art/uwVh5jCFtXslLg)) | `doors` + `open` |
| Translucent punched-hole figures | Tholu Bommalata: thinned, painted, perforated hide; perforations sparkle as jewellery ([Wikipedia](https://en.wikipedia.org/wiki/Tholu_Bommalata), [Bhaktilipi](https://bhaktilipi.in/indian-shadow-puppetry-tholu-bommalata-guide/) [blog]); the same idea in Karagiozis ([SearchCulture.gr](https://www.searchculture.gr/aggregator/portal/thematicCollections/karagiozis?language=en)) | `puppet({look: 'leather'})` |
| Colour by temperament, not naturalism | Kerala murals: green for serene figures, red for kings and warriors, black and white for fierce forms ([Varnaalaya](https://varnaalayaarts.com/blog/kerala-mural-art-painting) [blog]) | choose part fills per character |
| Gold leaf catching light | Tanjore: gesso relief, gold foil on crowns and thrones ([Curio](https://designbycurio.com/learn/tanjore-gold-leaf-tamil) [blog]) | `gold()` fills + `glint` |
| Frieze told in a strip | Greek black- and red-figure painting ([Met essay](https://www.metmuseum.org/essays/athenian-vase-painting-black-and-red-figure-techniques)); Oseberg procession tapestry ([Museum of the Viking Age](https://www.vikingtidsmuseet.no/english/viking-age/design-and-craft/the-oseberg-textiles.html)) | `scroll` with a row of `sheet`/`puppet` pieces inside |
| Picture-stone fields read in order | Gotland picture stones, divided into fields (ship, battle, rider, Valhalla) ([Wikipedia](https://en.wikipedia.org/wiki/Picture_stone), [Tängelgårda](https://www.wikiwand.com/en/T%C3%A4ngelg%C3%A5rda_stones)) | stacked `plate`s or `sheet` panels revealed bottom to top |
| Storyteller's proscenium and board changes | Kamishibai's wooden butai; toy theatre ([Kamishibai](https://en.wikipedia.org/wiki/Kamishibai), [Toy theatre](https://en.wikipedia.org/wiki/Toy_theatre)) | `doors` as the box, `place`/`lift` as the board change |
| Slow zoom and pan over stills | Ken Burns effect ([Wikipedia](https://en.wikipedia.org/wiki/Ken_Burns_effect)) | `plate` in a layer + `Studio.space.camera` push |
| Hand-made paper edges and fibre | Deckle edge ([Wikipedia](https://en.wikipedia.org/wiki/Deckle_edge)); SVG `feTurbulence` ([MDN](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/feTurbulence)) | `sheet` (geometric deckle), `#mx-fibre`, `stage` fibre ground |

## 3. Grammar of the tradition's own art

Use these as rules for layout, border and colour when a film follows one tradition.

**Indian**
- **Pattachitra** (Odisha): flat colour, bold black contour, patterned border band; conch-shell white, hingula red, haritala yellow, lamp-black, indigo ([Wikipedia](https://en.wikipedia.org/wiki/Pattachitra), [Odiapedia](https://odiapedia.com/culture/pattachitra) [blog]). Estimates: white #F4EFE4, red #D8352A, yellow #E8B923, black #1E1B18. Border band about 6% of the short side (estimate).
- **Phad** (Rajasthan): long cloth scroll; the deity at the centre, episodes around; faces in profile ([Wikipedia](https://en.wikipedia.org/wiki/Phad_painting)).
- **Kaavad** (Rajasthan): portable painted shrine, hinged panels, red ground (#B3261E estimate) ([V&A](https://collections.vam.ac.uk/item/O169083)).
- **Rajput and Pahari miniatures**: stacked flat colour planes, high horizon, a ruled border red then yellow then black at about 1.5% of the short side each ([MayaLucIA](https://mayalucia.dev/surveys/high-asia-art/pahari-miniatures/) [blog]).
- **Madhubani**: double outlines, hatching and dots, no empty space ([Anantam IAS](https://anantamias.com/madhubani-painting/) [blog]).
- **Kerala murals**: panchavarna five colours (yellow, red, green, black, white) ([Wikipedia](https://en.wikipedia.org/wiki/Kerala_mural_painting)).
- **Amar Chitra Katha** conventions for Indian audiences: flat bright colour, hard black keylines, a caption band ([Wikipedia](https://en.wikipedia.org/wiki/Amar_Chitra_Katha)). Do not imitate its characters.

**Jain and Buddhist**
- **Kalpasutra manuscripts**: long narrow folio, fine angular line, the far eye projecting past the profile, lapis, gold, black, white ([Wikipedia](https://en.wikipedia.org/wiki/Kalpasutra), [Museums of India](https://museumsofindia.gov.in/repository/record/im_kol-15021-10397)). Lapis #26429A and gold #C9A24B (estimates). A red ground is often claimed but was not confirmed.
- **Ajanta murals**: red-ochre underdrawing, colour fill, dark contour; ochres, glauconite green, lamp-black, lapis; Jataka subjects ([IASPOINT](https://iaspoint.com/ajanta-paintings/) [blog]).
- **Thangka**: central figure, smaller figures in compartments; black-ground nak thang for wrathful figures ([Wikipedia](https://en.wikipedia.org/wiki/Thangka)).

**Greek and Roman**
- **Black-figure / red-figure**: terracotta ground (#C8663A estimate) with near-black figures; incised detail; a frieze that loops ([Met essay](https://www.metmuseum.org/essays/athenian-vase-painting-black-and-red-figure-techniques)).
- **Roman mosaic**: black-and-white geometric borders, a polychrome central emblem ([Getty](https://www.getty.edu/publications/romanmosaics/introduction/index.html)). The kit's `meander` border is the Greek key.

**Norse**
- **Picture stones**: stacked narrative fields ([Wikipedia](https://en.wikipedia.org/wiki/Picture_stone)).
- **Runestones** were usually painted ([Wikipedia](https://en.wikipedia.org/wiki/Runestone)); colours not verified.
- **Animal styles** (Mammen, Ringerike, Urnes): ribbon-like beasts with tapering lines ([Glanz & Gravur](https://www.glanzundgravur.de/en/blog-tierstil-zeichnen.html) [blog]); the kit's `knot` border is a simplified interlace.

## 4. Handmade feel, as rules
- One light: a single warm lamp with a slow flicker (`flicker` 5-7 steps a second, amount 0.12-0.2). Shadows fall the same way in every plane.
- Paper is placed, never flown in: `place` (lift and settle, tilt under 1.5°), `lift` to exit.
- Edges are cut, not vector-perfect: `deckle` 0.25-0.5u on sheets, 0 only for ornament.
- Photographs are objects: duotone, paper margin or sticker edge, a soft contact shadow.
- Stepped motion ("on twos") only for puppet limbs if wanted; keep camera moves smooth ([Animating on twos](https://zuhuri.com/learn/stories/frame-by-frame-animation/) [blog]).

## 5. Not verified
Kalamkari palette and sequencing; Mysore painting; Gotland, runestone and Oseberg colours; the Jain red ground; every hex value. Measure palettes from a museum photograph (`design-dna.py measure`) before treating them as fact.
