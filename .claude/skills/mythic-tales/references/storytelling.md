# Storytelling for mythic films

Layered on the `story-writer` rulebook and the form skill; this file only adds what is particular to myth.

## 1. The storyteller stance, in words

The narrator is a storyteller holding a lamp, not a priest and not a debunker. Belief and meaning are always attributed.

| Do | Don't |
|---|---|
| "In the Valmiki Ramayana, ..." / "As the Bhagavata Purana tells it, ..." | "Long ago, Rama..." (no telling named) |
| "Hindus regard Krishna as an avatar of Vishnu." | "Krishna, the eighth avatar of Vishnu, ..." asserted as fact, or "according to legend (but really)..." |
| "Snorri says Odin gave an eye for a drink from Mimir's well." | "The Vikings believed..." (Snorri wrote in Christian Iceland around 1220) |
| "The tradition reads this as a lesson about ..." | "The lesson for us is ..." / "This teaches you to ..." |
| "Jain tradition holds that a Tirthankara ..." ; "Tirthankara (ford-maker)" | "the Jain god ..." |
| "the Jataka tells of a previous life of the Buddha" | Jataka events told as the historical Buddha's biography |
| "myth", "legend", "sacred story", "epic" as genre words | "myth" meaning "false" |

Every film names the telling **once on screen** (the source cartouche) and **once in narration**, in the first 10 seconds of a short and the first chapter of a long film.

## 2. Structure

Arcs (`python scripts/beatmap.py arcs`):
- `sacred-tale`: invocation, world, trial, divine turn, aftermath, teaching. The default for an episode.
- `boon-and-curse`: desire, boon, overreach, reckoning, lesson. Put the exact wording of the boon on screen; the loophole lives in it (Hiranyakashipu and Narasimha, Midas).
- `origin-myth`: before, first act, making, order, why it is so (the Nasadiya Sukta, Hesiod's Theogony, Ymir).

The style template's scene grammar maps onto these: invocation, world, revelation, trial, conflict, turn, aftermath, teaching, closing. A short uses four or five of them; a mid uses all; a long repeats trial-turn per chapter.

| Form | What fits | Shape |
|---|---|---|
| short (20-60 s) | One moment: Hanuman's leap, Ganesha's broken tusk, Odin at the well, Arachne's weaving | Invocation hook (1.5 s), one emblem, one turn, the lamp returns as the loop |
| mid (60-180 s) | One whole episode: the churning of the ocean, Prometheus, Baldr's death, the Jataka of the hare | `sacred-tale`; re-hook at the trial and the turn; one museum plate as evidence of the telling |
| long (5-12 min) | An arc: Sita's exile to return, the twelve labours, the road to Ragnarok, Mahavira's renunciation to kevala | Chapters (`storyboard.json` `chapters`), one turn per chapter, a folio chapter card, the telling restated per chapter, a variants beat ("in Kamban's telling...") |

## 3. Hooks

Write three from different formulas and score them (`python scripts/studio.py hook score "..." "..." "..."`):
- `impossible-feat`: "A mountain, held up on one finger for seven days. That is how the Bhagavata Purana tells it."
- `boon-loophole`: "He could not be killed by man or beast, by day or by night. So the god came at dusk, as neither."
- `witness` or `human-scale` work for heroes. Never `myth-flip` (myth-busting).

The hook names the telling or lands it in the next sentence. It passes the Clear gate: every name has its referent ("Hanuman, the monkey hero of the Ramayana").

## 4. What the research dossier holds

`research.json` / `research.md` (technical-researcher; validated by `scripts/validate-research.py`):
- **telling**: the text and version followed (with a citation to a translation or a museum or academic page), and why.
- **variants**: where other tellings differ in this episode (Valmiki, Kamban, Tulsidas, Jain Paumachariya; Homer vs Ovid; Poetic vs Prose Edda), and what the film will not mix.
- **events**: the episode beat by beat as the telling gives it.
- **figures**: for each, the iconography checklist from the tradition pack (attributes, mount, emblem, colour) and the source that confirms it.
- **reading**: what the tradition draws from the episode, attributed to whom.
- **images**: every plate with its institution, id, licence and page; every generated still marked as generated.
- **do_not_claim**: historicity claims, devotional claims, contested readings stated as settled.

## 5. Voice, pace, music

- **Voice:** `af_bella` (warm) or `bm_george` (British storyteller); `am_michael` for a long documentary. Speed 1.0-1.1, slower than the workspace 1.15: the template budget is 24 words per 10 s.
- **Names:** add respellings in `src/narration.json` for every Sanskrit, Prakrit, Greek and Old Norse name (voice-director); verify each against a pronunciation source, never guess. Keep diacritics on screen (Rāma, Mjǫllnir) only if the font has them.
- **Music bed:** a dim drone plus one timbre from the tradition (tanpura and bansuri, kithara or lyre, tagelharpa), -24 to -28 LUFS. Never a sacred chant, mantra or hymn used as a bed.
- **SFX:** paper rustle on `place`, a wick crackle under the lamp, a bell or conch only where the story has one; 12-18 dB under the voice. No whooshes.
- **Silence:** a breath before the sacred figure appears and after the teaching line.
