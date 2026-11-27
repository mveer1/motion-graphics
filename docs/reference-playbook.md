# Reference playbook: transitions, sound and pace learned from reference videos

What the reference corpus teaches, grouped so a skill or agent can pick a technique by what a scene needs. The top half is
written by the reference analyst after each batch; the bottom half is generated from the catalogue records by
`python scripts/reference-corpus.py playbook` and lists every technique with how to rebuild it, its runtime support and
the reference moments it was learned from.

Learn techniques, never assets: no frames, footage, marks, copy or shot sequences from these videos go into a project
(`ARCHITECTURE.md` section 0.8). A film that is recognisably one reference re-cut is a failure.

## How to use it

- **Pick by relationship, then by family.** Decide what the change between two scenes means (next step, go deeper,
  turn, contrast, chapter close), take the family from the table below, then read that family's entries in the
  generated index.
- **Search and recommend.** `python scripts/motion-catalogue.py search "<intent>" --type technique`, or
  `python scripts/motion-catalogue.py recommend --brief projects/<slug>/brief.json`. Cite what you used in the brief's
  `references[].technique_ids`; `studio.py validate` checks the ids.
- **Look at the evidence.** Each source record (`catalogue/data/reference-sources/<ref-id>.json`) has scenes, moments
  with timestamps and the `automated.listen` numbers. On a machine that ran the analysis, the contact sheets are in
  `reference/analysis/<ref-id>/` (`transitions.jpg`, `motion.jpg`, `audio.png`, `listen/listen.jpg`; untracked).
- **Pin the numbers before building** with the motion-spec method below, then check your own build with
  `frame-review.py` at the same moments.

## What the corpus teaches (64 inspected references, 2026-11-27)

Inspected: batch-0 (the 14 earlier references, `listen` backfilled 2026-11-26, transitions re-read 2026-11-27 as
batch-7/8), batches 1-6 and the two new films of batch-7 (batch-5 merged 2026-11-27). 96 technique records in 11
families. Every reference now has a `transitions` aspect; for the 14 re-read ones each boundary carries a time and a
family (cut, grow, cover, continuous).

### Transitions: choose by what the change means

| The change means | Family | Techniques (references) | Numbers from the corpus |
| --- | --- | --- | --- |
| Same idea, next step | transition-continuous | `single-stage-progression` (16), `empty-stage-dip` (16), `continuous-line-spine` (4), `canvas-camera-tour` (2), `background-palette-lift` (2) | One stage for 14-57 s (a light SaaS launch runs 47.6 s with no boundary at all) with 0-3 soft boundaries; a dip holds the empty background 0.05-0.4 s (on black: exit 0.06-0.3 s, empty 0.03-0.13 s; through a white page in a 98 s 3D explainer: out 0.2 s, empty 0.05 s, up 0.25 s with the title typing); a camera tours one canvas with 0.6-1.0 s moves and 2-5 s holds; an empty background changes colour in 0.6-0.8 s, or a held stage's sky cycles day to night once per second (0.3 s each) as a time-lapse |
| Go deeper, open a detail | transition-grow | `element-bloom-transition` (24), `zoom-through-transition` (10), `implode-burst-reveal` (10), `container-transform` (8) | Blooms take 0.10-0.33 s from first pixel to full cover in batches 2, 4, 5 and 6 (0.10-0.27 s in product films and showreels; 0.17 s from a dot and from a ball in batch-5; the re-read of batch-0 measured 0.13 s from an eye, 0.14 s from a clicked button, 0.17 s from a full stop, about 0.1 s for a white disc with echo rings from a ball that then stays as the full stop, 0.27 s for rings and for a heart that already holds the next scene, 0.3 s for a rectangle); the bloom shape can be a story symbol (a heart), not only a circle; 0.25-0.8 s in batch-1's slower pieces; a collapse to a dot (0.17-0.33 s), or a screen flash to black, before the burst marks an act hinge |
| A turn, a reveal, energy | transition-cut | `flash-frame-cut` (15), `chromatic-punch-word` (2), `light-swell-climax` (1) | Flash 1-2 frames, decays 0.15-0.35 s, at most one per film in batch-3 (at the climax); the hit lands 0-250 ms after it (+40 and +50-60 ms in batch-4); a story climax swells light for 3.4 s and cuts 1.4 s after the peak |
| Feeling rises in a character story | transition-cut | `reaction-shot-cutting` (1) | Setup shots of 8.4 and 10.4 s, five reaction shots of 0.7-2.6 s (median 2.0 s) cut on a look at the emotional middle, one 14.2 s take into the end card; 7 of batch-5's 9 cuts are in this one film |
| Rhythm, a list, a montage | transition-cut, kinetic-typography | `cut-on-beat` (11), `word-per-beat-sequence` (10), `palette-cycle-card` (3) | Word sections cut every 0.23-1.00 s; montages accelerate to 0.10-0.27 s cards; an agency showreel's median shot is 0.67 s; recolouring a held word every 0.23-0.27 s (0.1 s fails the photosensitivity cap) |
| Contrast, before and after | transition-cut, kinetic-typography | `film-match-cut` (6), `strike-and-correct` (4) | Held element, figure and ground swap on the cut; strike 0.2 s, demote 0.3 s |
| Chapter change | transition-cover, transition-continuous | `diagonal-band-wipe` (8), `section-push-slide` (7), `random-bar-wipe` (3), `act-break-fade-black` (2), `aperture-iris-transition` (1), `curtain-bookends` (1), `stacked-panel-wipe` (1), `dither-edge-wipe` (1) | Push 0.35-0.6 s with content 0.25 s after it lands (a vertical push of 0.1 s in a Swiss reel; 0.1-0.25 s panel pushes in batch-0's reels, one dark reel pushing a flat panel every 2.50 s whose colour is the next card's background); diagonal band 0.2-0.27 s (single-edge wipes 0.05-0.13 s; one band used as a metronome every 2.00 s, solid cover centred on the whole second); random or pixel bars 0.3 s; two stacked colour panels 0.13 s + 0.15 s hold + 0.22 s, the second becoming the next background; a dithered-grain edge 0.35 s from dark to light; bladed iris close 0.1-0.3 s; act break 0.5-0.8 s out, 0.7-0.9 s black, 0.6-0.7 s up |
| Chapter close, story beat | transition-cover | `crt-collapse-to-line` (4), `diegetic-object-wipe` (1), `liquid-pour-transition` (1), `foreground-occluder-pass` (1) | Cover 0.3-0.6 s; the covering object belongs to the scene; a blurred foreground object crosses the lens in 0.2-0.3 s while the subject changes behind it |

Patterns across the corpus:

- **Motivated transitions win.** The strongest changes start from something already on screen: a full stop, a dot, a
  pupil, a letter's counter, the middle of a word, the gap between pills, a clicked toggle, a lens.
  `element-bloom-transition` is linked from 23 of 64 inspected references, more than any other transition. In batch-6, 4 of
  10 films start a section change from an accent-coloured full stop or letter O; in batch-5 a bloom opens from a dot and
  one from a ball.
- **Blooms are fast.** Batch-1 measured 0.25-0.8 s; the 19 blooms of batches 2, 4, 5 and 6 take 0.10-0.33 s (median
  about 0.2 s; 0.10-0.23 s in batch-5's and batch-6's product films and showreels). Use 0.1-0.3 s in product and promo
  films, slower only in calm pieces.
- **A dot is the hinge between acts.** Six films (batches 2, 3, 4 and 6) collapse the outgoing element into a point
  (0.17-0.5 s; 1.7 s in a slow silent film), hold it (0.3-2.7 s), then release the next act (`implode-burst-reveal`);
  a seventh (batch-5) flashes the screen to black for 0.08 s instead and bursts a particle ring from its centre. The
  batch-0 re-read adds three short ones (collapse 0.06-0.2 s, no hold, burst 0.15-0.2 s), two with one inverted or grey
  frame between implosion and burst.
- **One object can carry a whole film.** A 29 s photo-print film never cuts: one container morphs through 8 shapes,
  0.13-0.33 s each; a 14 s square film runs twelve UI states as box and corner-radius tweens of 0.2-0.33 s
  (`container-transform`, 8 references).
- **Light canvases rarely hard-cut.** 0 cuts in 123 s on three batch-2 light films; batch-4's founder page, photo print
  and music app, both batch-3 light films, batch-7's 47.6 s light SaaS launch and batch-5's narrated 60 s reading-app
  explainer and referral promo have none either (cameras tour one canvas, containers morph, headlines swap in place,
  dissolves of 0.15-0.7 s). Dips go to the film's own background (ivory), never black. Cuts are kept for entering a dark section, for
  Swiss-style films (payments: cuts on whole seconds, one header-only frame, then the line rises), for dark word-card
  films (20 cuts in 24 s), for showreels (28 cuts in 35 s) and for the emotional middle of a character story.
- **Big transitions are rationed.** Films with flashes or blooms use 2-4 of them in 15-30 s, at the section turns; the
  rest of the changes are quiet (in-place builds, dips, plain cuts). Logo implosions appear once or twice per film.
- **Shot length.** Median shots of 0.67 s in a showreel of finished work, 1.8-2.8 s in 15-20 s reels, 3.2 s in a 54 s
  silent milestone film, 4.7 s in a 44 s portrait promo; one card per 1.00 s in word-card films; 6-13 s sections in
  photo-led explainers; about 6 s per step in a 40 s demo. Without the one showreel, batch-3 has 3 cuts in 187 s;
  batch-6 and the two batch-7 films have 14 cuts and 22 soft boundaries in 221 s, three films none at all; batch-5 has
  9 cuts in 221 s (7 of them in one character story), 40 soft boundaries and 28 in-place copy swaps the detector does
  not mark (11 headline swaps in the narrated film, about 11 move titles in a silent kata).
- **Detector blind spot.** On paper-on-paper films the boundary detector can find 0 boundaries where there are 9
  redraws; use a caption change or a strip to find them.
- **Cut or soft is not a family.** Re-reading batch-0's 108 boundaries frame by frame: 12 (11%) are another family
  than the detector's label suggests. 10 'cuts' are 5 grows (a bloom or burst, some with one flash or grey frame),
  2 fast covers (a 0.1 s wipe, strips of type sliding in) and 3 dips or fades through white or black; 2 'soft'
  boundaries are real cuts (one white flash frame; a clean change on paper). Even the sheet can mislead: a bloom
  from a ball read as a disc sweeping in from the left until a 30 fps strip showed its centre. Read `transitions.jpg` (and a 30 fps strip) before naming a family; never copy the detector label.
- **Family census of the re-read (14 films, 424 s, 108 boundaries).** 31 cut (29%), 16 grow (15%), 21 cover (19%),
  40 continuous (37%). Cuts cluster in word lists (5 cuts 0.23-0.47 s apart in one reel) and camera-stop jumps (5 in a
  98 s 3D explainer, each followed by a typed title); a 20 s life story and a 57 s paper theatre have no cut at all;
  light explainers (a 53 s sticker diagram, a 30 s recipe on one stage) change in place and cover only at their 1-2
  big turns. Per-film rows are in each source record's `transitions` aspect.

### Sound design: sound marks information, not edits

- **Accent on arrival** (`beat-grid-element-arrivals`, 26 references). The strongest accents fall on a grid and each
  coincides with an element arriving: 1.00 s grids in at least 10 films (accents at x.05, x.36-x.41 or x.53-x.70 s past
  each second), 2.00 s (cursor presses), 0.93-0.95 s, 0.88-0.91 s, 0.755 s (about 79.5 bpm), 0.47-0.5 s (one shape
  morph per beat at 129 bpm), 0.28 s and 0.25 s (a headline 0.17 s after each wipe).
- **Accents avoid cuts unless the cut is the event.** In 39 of 50 inspected films with audio and boundaries, accents on
  cuts are at or within 0.01 of chance, or only one cut carries one (batch-5 pooled: 3 of 35 boundaries, 0.09 against a
  weighted chance of 0.18). Of the other 11, 10 are films where the cut is the information (word cards, flash or
  glitch cuts, object transformations, a montage climax, a split-screen sting cutting both panes at once, a lyric
  video: 6 of 12 cuts accented, chance 0.14; a referral promo whose three transitions are themselves events, a bloom,
  a dissolve and a sweep, each with an accent 60-103 ms before the picture); the eleventh is a busy music loop (124
  accents a minute) whose accents are the music itself.
- **"Synced to music" means phrase-level.** A product intro titled as synced changes section every 2.40-2.55 s (about
  one bar at 95.7 bpm) and its headline changes land within 50 ms of an onset 6 of 10 times (chance 0.35), but list rows
  0 of 5 (chance 0.35) and accents on transitions 0 of 3 (chance 0.23). Sync the sections to the bar, not every element
  to a hit.
- **Cut, then prove.** Cut on the downbeat (x.97 s, or whole seconds) and put the accent 0.55-0.56 s later, on the new
  line or the card's UI action (`ref-b4e79aa0a4`, `ref-32fea7dae3`).
- **Sound on the action** (`action-synced-foley`, 11 references): steps 0.42 s apart on a stair, keystrokes, cursor
  presses, a ball's floor contacts, heartbeat blips, each change of a hero object's shape, letter tiles landing on a
  board (0 of 11 cuts accented). The cuts in those films carry none.
- **Silence as structure.** After the densest montage of a 153 s film the music stops for 3.7 s and, before the
  sign-off, for 5.3 s, while the picture keeps moving (`quiet-after-overload`; loudness range 12.5 LU against 1.1-8.2 LU
  in the promos). Relief can also be thinning, not silence: after a race is won the arrangement drops from 33 onsets
  per 4 s to 2. Shorter: 0.28-0.93 s of silence or a 19-28 dB dip right before a reveal, a lockup, a list landing or an
  end card, or right after an opening sting before the first section (`pre-hit-dropout`, 7 references); a 1 s gap
  between the two halves of a comparison reel. None in batch-4.
- **Under a voice the bed steps aside.** In the one narrated reference the bed sits about 25 dB under the voice
  (pauses about -40 dBFS against voice blocks about -15 dBFS, short-term), its 24 dips of 0.28-0.83 s are the speech
  pauses, and the two boundaries and 11 headline swaps carry no accent.
- **The arrangement is structure.** A launch tells its problem over a sparse bed and the full beat enters +7.3 dB as the
  product fills the frame (`beat-drop-product-reveal`); two promos end the music 0.7-1.7 s before the end card and
  build the card in its 2.5-6 s decay (`end-card-in-the-tail`).
- **Loudness follows importance.** In the sonified ball film a bounce is a note, a ring break is louder, the escape is
  the loudest (`sonified-motion`).
- **Levels.** 53 inspected films have an audible track: integrated -8.9 to -38.2 LUFS, median -14.2 (most promos -11.4
  to -16.6; the narrated explainer -16.1); loudness range 0.6-12.9 LU, widest in story films and showreels; four files
  peak above 0 dBTP (up to +0.8). 11 more are silent (one digital-silence track, 10 with no audio stream). All but one
  are music-only films: compare with our narrated-mix targets in the QA gates, not directly.
- **Limits of the evidence.** Measured from the signal (onsets, levels) and Windows dictation; nobody listened, and
  earshot's tagging models were not available on the analysis host. Accents may be part of the music rather than
  separate effects. Accents at x.53-x.70 s of a 1.00 s grid in 8 films may mean several films share one tool's
  defaults; batch-5's and batch-6's grids sit on other phases and add no evidence either way.

### Narration and pace: 1 narrated reference of 64

**The corpus has one measurable narrated reference.** Of 64 inspected references, `listen` (Windows en-US desktop
dictation) calls 1 narrated, 9 sparse, 44 none (one with a digitally silent track) and 10 have no audio stream. All 9
"sparse" films were checked on the phrase frames: 1-2 word "phrases" over title cards, a dot or music with nobody
speaking (in three title-voiced or "synced" films most confident "words" are one repeated letter). Two of them could
still hide a voice the recogniser cannot measure: a likely French voice-over (`ref-85d3a83400`; en-US dictation cannot
measure French pace) and a quiet poem film where a reading voice is unlikely but not ruled out (`ref-910d9fc567`). The
"likely narrated by title" list hit once in 9: batch-5's `reading-app-explainer` (`ref-31ce9d6332`) is voiced; the
other 8 (batch-2: 4; batch-3: `one-million-visitors`, which has no audio stream, and `an-emotional-app-promo`; batch-6
and 7: `self-intro-for-a-recruiter` and `voice-agent-saas-launch`) are music-only or silent. The syllabic-modulation
feature is no voice detector: its corpus high (0.51) belongs to a music-only film; the narrated film scores 0.39.

**The narrated reference** (`ref-31ce9d6332`, 60 s, light canvas, a headline lane on the left and a phone demo on the
right, one voice over a quiet bed). Speech is confirmed by dictated words that follow the on-screen copy in 8 or more
places and by harmonic speech blocks on the spectrogram; nobody listened. Dictation keeps only 61 of 170 words, so the
film is measured two ways:

| measure | energy voice activity (batch-5 `narration_31ce.py`) | dictation (`listen`) |
| --- | --- | --- |
| talk | 33 blocks, 41.4 s = 0.69 of the film, block median 1.23 s | 21 phrases; 61 confident of 170 raw words; coverage 0.38 |
| words per second while speaking | a band: 1.35 (confident words in blocks) to 3.65 (raw words in blocks) | 2.65 |
| words per minute over the speech span | 58-158 | 65 |
| pauses (count, median, max) | 32, 0.50 s, 1.12 s | 20, 1.37 s, 6.24 s (counts a 6.2 s in-app read-aloud in French, which the recogniser skips, as a pause) |
| pace over thirds, trend | talk share 0.73 / 0.68 / 0.74 and raw words/s 3.49 / 3.97 / 3.52: **steady** | "accelerates" (0.91 / 0.86 / 1.50): recognisability, not pace |
| picture changes in pauses | 11 of 11 headline swaps and 2 of 2 boundaries, chance 0.28 (the pause share) | boundaries 2 of 2, tool chance 0.59 |
| change to the next phrase | boundaries 0.41 and 0.56 s; headline swaps median 0.60 s (0.01-0.94) | 1617 ms |
| engine | 20 ms RMS, threshold midway between the 10th and 90th percentile | Windows System.Speech en-US desktop dictation (rough) |

Words per second is a band, not a number: the true rate lies between the confident-word floor and the raw-word
ceiling, and the band is too wide to test our 1.15x default against. A whisper or Parakeet `listen` on the Mac would
settle it. The pauses are firmer (they come from the signal, not the recogniser): a median of 0.50 s and nothing over
1.12 s, so our 0.5 s pause between scenes matches this voice's typical breath.

**Copy against a voice** (`pause-locked-copy-swap`): every copy change waits for a breath. The new headline is first
visible 0.27 s and 0.58 s before its phrase (30 fps strips) and list lines 0.21 s before; a swap is a fade out of
0.17-0.20 s, 0.07-0.10 s empty and a fade in of 0.13-0.15 s (about 0.35 s in all). The film has no captions: the
headline lane is the caption. It is calmer than our 2-3 s change rule: copy holds 1.6-10 s per step and the analyser
finds 15 static holds of 0.7-3.5 s over speech while the phone keeps only small motion (recorded for the owner, not
acted on).

Batch-2's proof table (the first batch expected to be narrated; none of its 8 films is). Engine: Windows desktop
dictation; "confident" means confidence 0.2 or more.

| film | s | audio | confident words | phrases | wps speaking | verdict | phrase-frame evidence |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| `ref-58ff9f39df` | 153.4 | music | 4 | 4 | 0.9 | none | 1-word "phrases" over a glitch frame, a bar chart, a noise field and the end card |
| `ref-5a2816d4db` | 39.1 | music | 0 | 0 | - | none | no phrases |
| `ref-3abcbedd20` | 30.0 | music | 0 | 0 | - | none | no phrases |
| `ref-216f4eaeef` | 58.0 | **none** | - | - | - | none (no audio stream) | the caption carries the script |
| `ref-c6d0aa55f6` | 54.0 | **none** | - | - | - | none (no audio stream) | copy in headlines |
| `ref-b4e79aa0a4` | 23.8 | music | 0 | 0 | - | none | no phrases |
| `ref-70c57c2adf` | 15.0 | music | 0 | 0 | - | none | no phrases |
| `ref-1e22836116` | 45.6 | music, possibly foley | 3 | 3 | 0.94 | none | 1-word "phrases" over a walking silhouette, a dark room and an exterior |

The two speech-like rates come from 3-4 isolated words; they are not a pace. Batch-3 adds no narration (0 words in 6
films, 1 noise word in one, one film without audio), batch-4 none either (one likely French voice, one sung track on
which dictation fails), batch-6 and the two batch-7 films none (8 music-only, 2 without audio), batch-5 one (above; of
the other 7, 5 are music-only and 2 have no audio track), and the 14 earlier references are un-narrated too.

What the corpus measures besides the one voice:

- **Reading pace when the caption is the voice** (`ref-216f4eaeef`, silent, `caption-voice-strip`): 10 cues, 192 words
  in 58 s = **199 words a minute on screen**, typed in at **7.8 words/s** (6.3-8.3) and then held complete **3.5 s**
  (1.4-4.9); 17.5 words per cue (8-32). The reveal runs at about twice speaking speed; the holds set the pace the viewer
  feels.
- **Text against a voice, sung** (`ref-e8125c24ca`, `lyric-word-onset-sync`): each word starts to show 0-120 ms before
  its vocal onset (median about 15 ms early), never more than about 40 ms after; lines of median 3 words held about
  2.3 s; a line clears with a 0.1-0.3 s dissolve that starts on the next phrase's onset. On speech (the one narrated
  reference) headlines lead by more, 0.27-0.58 s, because they change only in the pause before their phrase.
- **Text against a music bed** (batch-6, 3 films, 29 headline words at 30 fps): words arrive on their own fixed stagger
  (median 0.10, 0.13 and 0.20 s) and land within 50 ms of an onset only at chance (for example 10 of 21 against 0.51);
  only the accent payoff word sits on an onset (2 of 3 lines, within 10 ms). A voice pulls on-screen words to it; a
  music bed does not.
- **Text-led pace:** one idea per 1-2 s of on-screen copy in promos; one card per 1.00 s in word-card films; about 6 s
  per step in a demo; a 0.07-0.4 s empty breath before a new section (`empty-stage-dip`), which in the narrated film
  (0.17 s) sits in a pause between phrases; a 153 s first-person monologue told only in type, 1-6 words per card held 1-4 s;
  a silent 54 s milestone film that keeps its rhythm with dips and 1-2 s holds alone.

Consequence: the `voice-director` 1.15x default and the story-writer's pace map stay as they are: one narrated
reference measured with rough dictation gives a words-per-second band (1.35-3.65), not a pace. What it does support,
and the skills now carry as advisory lines: change copy in the pauses, show it 0.2-0.6 s before its phrase, put no
hits on copy swaps (this film's bed sits about 25 dB under the voice, deeper than our 15-20 dB target; one film does
not move the target), and keep pauses near 0.5 s. The owner's options are in
`prompts/state/decisions-needed.md` (a narrated reference set, our own narrated films as references, or the Mac
re-run with whisper or Parakeet, which would turn the band into a number).

### Captions and on-screen copy

- **Caption lanes measured:**
  - a lower-third caption strip that is the film's only voice (82-96% of the height, 1-3 lines, typed word by word,
    no highlight, swapped on the scene redraw at whole seconds; `caption-voice-strip`);
  - a subtitle plate bottom-centre at about 90% of the height, 6-12 words, one accent word echoing the headline's
    accent word, hard one-frame swaps every 2-3 s (`ref-85d3a83400`);
  - a diegetic plaque in the top band (3-12% of a portrait frame) carrying a poem line by line (`ref-910d9fc567`);
  - lyric lanes that move every phrase, anchored to the picture (8 placements in 30 s; `lyric-word-onset-sync`);
  - a step pill for a wordless demo: bottom centre at about 90%, one line of 4-8 words, held 3.5-5 s, changed only on
    the next step (`step-caption-pill`, 5 cues in 30 s);
  - in a portrait promo, one line under the hero number at 60-65% of the height and a status pill at the bottom updated
    every 0.75 s;
  - a one-line regime caption (5-9 words) at the top-left of a live simulation, swapped in place 4 times in 18 s
    (`live-simulation-trace`);
  - in the narrated reference, no caption at all: a headline lane top-left (about 25-46% of the height, 2-30% of the
    width; 2-7 words in 1-2 lines) is the caption, swapped only in the voice's pauses and readable 0.27-0.58 s before
    its phrase (`pause-locked-copy-swap`);
  - a corner move title in a silent kata: 2-4 characters set vertically at the top right (85-95% of the width), swapped
    in place with each move (0.7-2.2 s), the same job as a step pill without the pill (`step-caption-pill`);
  - a portrait end card stacked in bands: headline 6-15% of the height, diegetic content 16-80%, wordmark 81-87%,
    tagline 88-91%, address 92-94%; its top and bottom lines sit at 77 px, outside our portrait safe zones (top 80-128
    px, bottom 120-256 px).
- **Copy as the picture** (most films): centred single words; a centred middle-third stack under a persistent header bar
  in portrait; top-left or left-column two-line headlines beside a proof card; a left-aligned stack from about 30% of a
  portrait frame in which earlier lines dim as each new one lands (`dim-previous-line-stack`); a lower-left chapter
  block over a progress bar in a captured web explainer; hand-written labels with arrows beside the object they name.
- **Emphasis:** a two-tone headline pair, line 2 in the accent colour or grey arriving a beat later, the payoff word
  last (`two-tone-headline-pair`, 10 references); one italic serif word in the accent colour per headline; one accent-coloured key word per headline; red strike-through for a wrong
  belief; the phrase-final word set larger in lyrics; small handwritten notes beside the moving subject.
- **Builds:** per-word fades about 0.1 s apart; per-character blur to sharp at 0.07 s stagger for a quiet closing line
  (`per-character-blur-reveal`); letters dropping in with a bounce and toppling out (`gravity-letter-drop`); monospace
  typing at about 10 characters/s re-set into a display serif (`markup-renders-to-type`); typing with a block caret; a
  typed prompt pushed to macro scale (`macro-typing-push`).
- Word-highlight captions placed directly under the illustration they narrate (`word-highlight-caption`). Our caption
  overlay highlights the spoken word and, since runtime 1.17.0, can sit beside the subject (`subject` lane with a
  `caption_anchor`); a caption lead option, a pause-aware copy swap and a reading-pace timing mode for muted films are
  not built.

## Rebuilding a technique: the motion-spec method

Before building a technique seen in a reference, write a small spec from the strips (the method is adapted from the
MIT-licensed `reanimate` skill, NiazMorshed2007/reanimate; the skill itself is not installed):

1. Run `python scripts/reference-corpus.py strip <ref-id> --from <a> --to <b> --fps 30 --root <folder>` around the moment.
2. Per element and property, note the first frame it moves and the last frame it rests: start = first / fps,
   duration = (last - first + 1) / fps.
3. Read the easing from where the midpoint lands: more than half the distance covered at a third of the duration is an
   ease-out; less than a quarter is an ease-in; symmetric is ease-in-out; passing the end and coming back is back or
   spring (note the overshoot and settle time).
4. Staggers are the gaps between siblings' start frames: constant, growing, or per character or word.
5. Write the rows (element | property | from -> to | start | duration | easing | stagger | evidence) into the technique
   record's `mechanics` and `parameters`. Use the spec to pin the technique's numbers, never to copy a shot sequence.
6. After building, check timing in `frame-review.py` sheets; within about 80 ms of the intended rhythm is a match.

## Batches

The corpus is analysed in batches of 8 (`tags` on each source record carry `batch-N`); all 64 files resolve from one
folder (`--root ~/Downloads/motion-references`, outside the repository). Process per batch: `analyze` -> `listen` ->
look at every sheet -> source records -> `check` -> technique records (new or provenance) ->
`motion-catalogue.py validate` -> `reference-corpus.py playbook` -> update the synthesis above.

| Batch | References (download-folder order) | State |
| --- | --- | --- |
| batch-0 | the 14 earlier references (`ref-0bf0254a3d`, `ref-1cbe55c987`, `ref-37644838b5`, `ref-392ee4d0f9`, `ref-49459ad8c1`, `ref-5924215625`, `ref-736d4ef2c2`, `ref-910d9fc567`, `ref-92c22222a2`, `ref-95c96d5c47`, `ref-b97f9168c6`, `ref-c3bc609841`, `ref-c93524ef20`, `ref-ce769bc33e`) | inspected 2026-10-30; `listen` and the sound, narration and caption aspects backfilled 2026-11-26 (0 narrated; 1 without audio, 1 silent track) |
| batch-1 | `ref-6f68999b60`, `ref-81650adf49`, `ref-a2496929ca`, `ref-0b13aa7f02`, `ref-a3031376e7`, `ref-a339360a56`, `ref-fe7fb0ded2`, `ref-aff23e662b` | inspected 2026-11-26 |
| batch-2 | `ref-58ff9f39df`, `ref-5a2816d4db`, `ref-3abcbedd20`, `ref-216f4eaeef`, `ref-c6d0aa55f6`, `ref-b4e79aa0a4`, `ref-70c57c2adf`, `ref-1e22836116` | inspected 2026-11-26 (0 narrated; 2 without audio) |
| batch-3 | `ref-99713f6e72`, `ref-cfaf668ebf`, `ref-e40080c790`, `ref-2860712d4e`, `ref-a943607659`, `ref-ad023ce9dc`, `ref-57fd2ce3b4`, `ref-19cee08f9c` | inspected 2026-11-26 (0 narrated; 1 without audio) |
| batch-4 | `ref-ee70618e88`, `ref-d386e5f0ae`, `ref-85d3a83400`, `ref-e8125c24ca`, `ref-0fe1abc90a`, `ref-c2addc76df`, `ref-32fea7dae3`, `ref-7a185cb08d` | inspected 2026-11-26 (0 measurable narration: 1 likely French voice, 1 sung; 1 without audio) |
| batch-5 | `ref-dc626241e6`, `ref-2a6c654bfe`, `ref-31ce9d6332`, `ref-9ed4034cad`, `ref-05acc490f6`, `ref-debf607232`, `ref-0a270a1575`, `ref-c324a3d516` | inspected 2026-11-27 (1 narrated: `ref-31ce9d6332`, the corpus's first; 2 without audio) |
| batch-6 | `ref-b34f751c59`, `ref-c87967b288`, `ref-9459c8097f`, `ref-fb375e07e2`, `ref-fd749e7ebc`, `ref-04d81a6a3e`, `ref-a1c9ef89a3`, `ref-05c4222dae` | inspected 2026-11-26 (0 narrated; 2 without audio) |
| batch-7 | `ref-0b2552b64e`, `ref-b8cf9a12b0` (new; inspected with batch-6) + transition re-read of `ref-0bf0254a3d`, `ref-1cbe55c987`, `ref-37644838b5`, `ref-392ee4d0f9`, `ref-49459ad8c1`, `ref-5924215625` (their `listen` backfill is done as batch-0) | new films inspected 2026-11-26 (0 narrated); re-read done 2026-11-27: 44 boundaries, each with a time and a family (14 cut, 9 grow, 5 cover, 16 continuous), 7 strips; first `transitions` aspect for `ref-37644838b5` |
| batch-8 | transition re-read of `ref-736d4ef2c2`, `ref-910d9fc567`, `ref-92c22222a2`, `ref-95c96d5c47`, `ref-b97f9168c6`, `ref-c3bc609841`, `ref-c93524ef20`, `ref-ce769bc33e` (their `listen` backfill is done as batch-0) | re-read done 2026-11-27: 64 boundaries, each with a time and a family (17 cut, 7 grow, 16 cover, 24 continuous); first `transitions` aspect for `ref-c93524ef20` and `ref-ce769bc33e` |

<!-- BEGIN GENERATED: python scripts/reference-corpus.py playbook (do not edit between these markers) -->

## Corpus at a glance

- 64 reference videos registered; 64 inspected; 64 with a `listen` block (speech, loudness, accents).
- Inspected by batch: batch-0: 14, batch-1: 8, batch-2: 8, batch-3: 8, batch-4: 8, batch-5: 8, batch-6: 8, batch-7: 2.
- 96 technique records in 11 families. Records: `catalogue/data/references/`; sources: `catalogue/data/reference-sources/`; local evidence sheets: `reference/analysis/<ref-id>/` (untracked).

| family | techniques | most used (references) |
| --- | --- | --- |
| [Transitions: the cut carries the change](#transition-cut) | 5 | `flash-frame-cut` (15), `cut-on-beat` (11), `film-match-cut` (6) |
| [Transitions: an element grows into the next scene](#transition-grow) | 4 | `element-bloom-transition` (24), `implode-burst-reveal` (10), `zoom-through-transition` (10) |
| [Transitions: something covers or wipes the frame](#transition-cover) | 13 | `diagonal-band-wipe` (8), `section-push-slide` (7), `grid-wave-propagation` (6) |
| [Transitions without a cut](#transition-continuous) | 7 | `empty-stage-dip` (16), `single-stage-progression` (16), `morph-ready-shape-sequence` (7) |
| [Kinetic typography](#kinetic-typography) | 21 | `word-slot-roll` (16), `accent-punctuation-motif` (15), `two-tone-headline-pair` (10) |
| [Motion character](#motion-character) | 7 | `directional-smear` (10), `particle-assemble-glyph` (10), `pen-led-stroke` (8) |
| [Staging and depth](#staging-depth) | 7 | `hud-frame-overlay` (16), `css-3d-staging` (13), `rendered-3d-objects` (12) |
| [Explanation devices](#explanation-device) | 15 | `ui-demo-micro-interactions` (25), `diagram-connectors` (8), `annotation-callouts` (5) |
| [Style and texture systems](#style-texture) | 5 | `cut-paper-title-sequence` (2), `archival-mono-collage` (1), `pencil-sketch-paper-style` (1) |
| [Sound design against the picture](#sound-design) | 7 | `beat-grid-element-arrivals` (26), `action-synced-foley` (11), `pre-hit-dropout` (7) |
| [Narration and captions](#narration-captions) | 5 | `step-caption-pill` (2), `word-highlight-caption` (2), `caption-voice-strip` (1) |

<a id="transition-cut"></a>
## Transitions: the cut carries the change

Hard cuts made meaningful: on the beat, on a matching shape, through a flash.

### `flash-frame-cut`: Flash frame cut (light-burst cut)
- **Lifecycle** tested (preview); support native; seen in 15 reference(s). Record: [`flash-frame-cut.json`](../catalogue/data/references/flash-frame-cut.json)
- **What:** At the cut, the frame flashes to white (or to a radial burst of the accent colour) for one or two frames, and the incoming shot starts overexposed and settles to normal exposure. The flash hides the edit and reads as an impact, an exposure or a release of energy.
- **Recreate:** Full-frame overlay at the cut: opacity 1 for 1-2 frames, then to 0 over 0.15-0.35 s with power2.out. White overlay for a camera-flash read; radial-gradient (accent core, transparent edge) centred on the incoming subject for a light-burst read. Optional pre-dim of the outgoing scene (brightness 1 -> 0.6 over 0.2 s). The scene swap happens under the opaque frame. Sound: the impact hit or bass drop lands 0-250 ms after the flash (ref-6f68999b60: flash 10.00 s, accent 10.24 s).
- **Timing:** Flash 1-2 frames (33-67 ms at 30 fps); decay 0.15-0.35 s; at most 2-3 per film.
- **Runtime:** Studio.fx.flash
- **Precedents:** `ref-04d81a6a3e` at 14.39 s; `ref-0fe1abc90a` at 8 s; `ref-19cee08f9c` at 5.62 s; `ref-3abcbedd20` at 7.51 s; `ref-58ff9f39df` at 0.71 s; `ref-6f68999b60` at 10 s; `ref-70c57c2adf` at 13.09 s; `ref-81650adf49` at 0.9 s
- **Watch out:** Photosensitivity: more than three flashes in any one second, or large saturated-red flashes, fail WCAG 2.3.1 and broadcast flash guidelines; keep to isolated flashes / On the light default canvas a white flash is invisible; use the accent burst or a brief inversion instead

### `cut-on-beat`: Cuts locked to the music
- **Lifecycle** tested (preview); support native; seen in 11 reference(s). Record: [`cut-on-beat.json`](../catalogue/data/references/cut-on-beat.json)
- **What:** Scene cuts and word changes land on the soundtrack's beats or hits, so picture and sound feel like one gesture and the edit's rhythm is felt rather than noticed.
- **Recreate:** Beat grid from the track's tempo and phase; cue times snapped to the grid (or to detected onsets) within about one frame.
- **Timing:** Measured: Measured at analyzer 1.2: ref-92c22222a2 60% of boundaries within 60 ms of the estimated 129 bpm grid (chance 26%), 80% within 50 ms of an onset (chance 41%); ref-392ee4d0f9 80% near an onset (chance 31%); ref-736d4ef2c2 40% near the 129 bpm grid (chance 26%, weak).
- **Runtime:** Studio.rhythm.grid, Studio.rhythm.snap, Studio.comp.wordBeats
- **Precedents:** `ref-0fe1abc90a` at 8 s; `ref-19cee08f9c` at 5.65 s; `ref-32fea7dae3` at 2 s; `ref-392ee4d0f9` at 2.1 s; `ref-57fd2ce3b4` at 1.1 s; `ref-70c57c2adf` at 3.77 s; `ref-736d4ef2c2` at 3.82 s; `ref-92c22222a2` at 11.25 s
- **Watch out:** Snapping cuts that need reading time onto a fast grid / Using an estimated tempo without checking the phase by ear

### `film-match-cut`: Shape match cut (film editing)
- **Lifecycle** implemented; support -; seen in 6 reference(s). Record: [`film-match-cut.json`](../catalogue/data/references/film-match-cut.json)
- **What:** The incoming element starts at the outgoing element's position and scale, then settles. Variant seen in the corpus: hold the shape exactly in place and swap figure and ground colours on the cut.
- **Timing:** Hard cut plus 0.6-1.0 s settle
- **Runtime:** match-cut
- **Precedents:** `ref-2860712d4e` at 5 s; `ref-49459ad8c1` at 2 s; `ref-57fd2ce3b4` at 3.6 s; `ref-92c22222a2` at 5.63 s; `ref-aff23e662b` at 3.35 s; `ref-b8cf9a12b0` at 13.18 s

### `light-swell-climax`: Light swell climax, released by a cut
- **Lifecycle** specified; support approximation; seen in 1 reference(s). Record: [`light-swell-climax.json`](../catalogue/data/references/light-swell-climax.json)
- **What:** The climax is a light source growing until the whole dark frame flares, then a cut to a wide shot releases it. Brightness, not motion or sound, carries the peak.
- **Recreate:** Lamp lit at 29.7 s; its glow radius and intensity rise steadily for 3.4 s; a frame-wide exposure lift peaks at 33.1-33.3 s; it settles over about 0.5 s; hard cut to the exterior at 34.60 s, 1.4 s after the peak (ref-1e22836116). No accent at the cut.
- **Timing:** Swell 3-3.5 s; settle 0.5 s; cut 1-1.5 s after the peak.
- **Runtime:** not built yet
- **Precedents:** `ref-1e22836116` at 29.7 s
- **Watch out:** On a light canvas there is no headroom: use a dark section / Cutting before the peak deflates the climax

### `reaction-shot-cutting`: Reaction-shot cutting at the emotional peak
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`reaction-shot-cutting.json`](../catalogue/data/references/reaction-shot-cutting.json)
- **What:** In a wordless character story the setup and the resolution are long takes and the emotional middle is cut fast between the character's close-up and the others' reactions (shot-reverse-shot). The cutting speed shows the feeling rising; the long final take lets it settle.
- **Recreate:** Two long setup shots (8.4 and 10.4 s), then five shots of 0.7-2.6 s (median 2.0 s), each cut on a look or a hop, then one 14.2 s take that rises over the result and holds into the end card. No transition effects; fades from and to black only at the ends.
- **Timing:** Middle act 8.6 s in 5 shots; outer shots 8.4-14.2 s.
- **Runtime:** Studio.cut
- **Precedents:** `ref-0a270a1575` at 18.97 s
- **Watch out:** Fast cutting everywhere removes the peak / Cutting away during an action instead of on a look loses the thread

<a id="transition-grow"></a>
## Transitions: an element grows into the next scene

A dot, a letter, a mark or a card expands until it becomes the next frame.

### `element-bloom-transition`: Element bloom transition
- **Lifecycle** tested (preview); support native; seen in 24 reference(s). Record: [`element-bloom-transition.json`](../catalogue/data/references/element-bloom-transition.json)
- **What:** Instead of cutting or wiping, a small element of the current frame expands until its colour fills the frame, and that colour is the background of the next scene. The viewer's eye is already on the element, so the change feels caused rather than imposed.
- **Recreate:** Scale of a circle from the source's size to the distance to the farthest corner; ease-in (accelerating) growth; the scene swap happens under full cover, so no frame shows both scenes; optional ring leads the fill by 15-20% of the duration.
- **Timing:** About 0.25-0.4 s in fast reels (ref-92c22222a2 1.88 s, ref-49459ad8c1 7.82 s); about 0.5-0.8 s in slower pieces (ref-5924215625 1.57 s).
- **Runtime:** Studio.fx.bloom, Studio.boxAt
- **Precedents:** `ref-05c4222dae` at 4.57 s; `ref-0b13aa7f02` at 2.13 s; `ref-0bf0254a3d` at 2.48 s; `ref-1cbe55c987` at 12.5 s; `ref-392ee4d0f9` at 13.17 s; `ref-3abcbedd20` at 21.9 s; `ref-49459ad8c1` at 7.82 s; `ref-5924215625` at 1.57 s
- **Watch out:** Incoming scene background differs from the bloom colour: visible pop / Source near a frame corner makes the growth read as a wipe

### `implode-burst-reveal`: Implode to a point, then a ring burst reveal
- **Lifecycle** specified; support native; seen in 10 reference(s). Record: [`implode-burst-reveal.json`](../catalogue/data/references/implode-burst-reveal.json)
- **What:** Everything on screen collapses into one point, the frame holds its breath (a slight dim), then one bright frame and an expanding ring release the next scene while its mark assembles from the debris. The collapse makes the reveal feel caused and loaded.
- **Recreate:** Converge: elements travel to one point along straight dashed rays over 0.3-0.5 s, power2.in (ref-3abcbedd20 7.00-7.30 s). Pre-dim: background brightness to about 85% over 0.15-0.2 s (7.30-7.47 s). Release: one bright frame (7.50-7.53 s), then a 1-2 px ring scales from radius 0 to about 40% of the frame width over 0.27 s, power2.out, opacity fading (7.53-7.80 s); the mark assembles from scattered particles over 0.3-1.0 s. Hit on the first ring frame (accent 7.55 s). Dark variant: a dark circle closes, then particles burst outward from a point over 0.15 s (ref-70c57c2adf 9.19-9.53 s). Also (batch-4): ref-85d3a83400: the UI window blanks, blurs, recolours orange and shrinks to a dot in about 0.33 s (8.41-8.74 s, power-in); the dot holds about 2.7 s while particles gather around it (9.9-10.9 s); release: the dot grows into a full-frame orange disc and a cream disc opens inside it, about 0.27 s in all (11.41-11.68 s). No bright frame; accent within 100 ms of the release boundary: none (1 of 3 boundaries overall).
- **Timing:** Converge 0.3-0.5 s; dim 0.15-0.2 s; ring 0.25-0.3 s; assembly 0.3-1.0 s; once or twice per film.
- **Runtime:** Studio.space.assemble, Studio.fx.bloom
- **Precedents:** `ref-19cee08f9c` at 7.72 s; `ref-1cbe55c987` at 1.47 s; `ref-2a6c654bfe` at 12.5 s; `ref-3abcbedd20` at 7 s; `ref-70c57c2adf` at 9.36 s; `ref-85d3a83400` at 8.57 s; `ref-92c22222a2` at 1.82 s; `ref-99713f6e72` at 11.87 s
- **Watch out:** No dim before the release: it reads as a plain bloom / Used more than twice it stops being an event

### `zoom-through-transition`: Zoom-through transition
- **Lifecycle** specified; support native; seen in 10 reference(s). Record: [`zoom-through-transition.json`](../catalogue/data/references/zoom-through-transition.json)
- **What:** The camera flies into an element (a letter counter, a window, a dot) until it passes the lens, and the next scene is found inside it.
- **Recreate:** Scale to 8-20x about an interior point with power3/expo.in; next scene from scale 1.15 to 1 with ease-out; brief overlap.
- **Timing:** About 0.5-0.8 s.
- **Runtime:** Studio.fx.zoomThrough
- **Precedents:** `ref-05c4222dae` at 10.2 s; `ref-0b13aa7f02` at 6.98 s; `ref-0bf0254a3d` at 7.7 s; `ref-19cee08f9c` at 2.18 s; `ref-736d4ef2c2` at 10.7 s; `ref-7a185cb08d` at 25.56 s; `ref-a2496929ca` at 9.97 s; `ref-b4e79aa0a4` at 3.62 s
- **Watch out:** Scaling text to 20x blurs or costs raster time; switch at about 6x / Transform origin not on a hole or dark interior shows a flash

### `container-transform`: Container transform (shared element)
- **Lifecycle** tested (preview); support native; seen in 8 reference(s). Record: [`container-transform.json`](../catalogue/data/references/container-transform.json)
- **What:** One container carries the viewer between two states: its position, size and corner radius tween from the source element's box to the target's box, the old content fades out early and the new content fades in late, so there is never a cut.
- **Recreate:** Measure source and target rects (Studio.boxAt). Tween x, y, width, height and border-radius together over 0.5-0.8 s with power3.inOut; source content opacity 1 -> 0 in the first 30%; target content 0 -> 1 in the last 40% with a 4-8 px rise; shadow grows with size. No crossfade of two full frames.
- **Timing:** 0.5-0.8 s; content swap in the middle third.
- **Runtime:** Studio.fx.containerTransform
- **Precedents:** `ref-5a2816d4db` at 31.27 s; `ref-7a185cb08d` at 1.17 s; `ref-ad023ce9dc` at 17.9 s; `ref-b4e79aa0a4` at 1.53 s; `ref-b8cf9a12b0` at 9.72 s; `ref-e40080c790` at 1.82 s; `ref-ee70618e88` at 0.56 s; `ref-fe7fb0ded2` at 0.37 s
- **Watch out:** Aspect ratio changes without corner-radius interpolation look like a stretch / Fading both contents at the same time shows a muddy mid-state

<a id="transition-cover"></a>
## Transitions: something covers or wipes the frame

Liquid, curtains, an eyelid, a collapse to a line, a ripple across a grid.

### `diagonal-band-wipe`: Diagonal colour band wipe with echo edges
- **Lifecycle** specified; support native; seen in 8 reference(s). Record: [`diagonal-band-wipe.json`](../catalogue/data/references/diagonal-band-wipe.json)
- **What:** A solid band in the accent colour, tilted slightly, sweeps across the frame and the scene changes while it covers everything. Stepped lighter stripes on both edges suggest speed without motion blur.
- **Recreate:** Band rotated about 15 degrees from vertical, wide enough to cover the frame at mid-travel; 3-4 echo stripes of decreasing opacity (about 80, 60, 40%) on the leading and trailing edges; travels from off-left to off-right in 0.23 s (7 frames at 30 fps), near-linear; full cover for 1-2 frames at the midpoint (ref-3abcbedd20 20.62 s); scene swap under full cover; the next headline starts typing 0.1 s after the band leaves (20.72 s).
- **Timing:** 0.2-0.3 s total; 1-2 frames of full cover.
- **Runtime:** Studio.fx.shapeCover
- **Precedents:** `ref-0bf0254a3d` at 10.45 s; `ref-3abcbedd20` at 20.52 s; `ref-5924215625` at 3.92 s; `ref-92c22222a2` at 3.5 s; `ref-9ed4034cad` at 12.3 s; `ref-b8cf9a12b0` at 7.47 s; `ref-dc626241e6` at 3 s; `ref-fb375e07e2` at 5.41 s
- **Watch out:** A band colour outside the palette reads as a glitch / Slower than about 0.5 s it reads as a slide, not a wipe

### `section-push-slide`: Section push (page turn between sections)
- **Lifecycle** implemented; support native; seen in 7 reference(s). Record: [`section-push-slide.json`](../catalogue/data/references/section-push-slide.json)
- **What:** The next section arrives as a panel from one side and pushes the current page off the other side, like turning a catalogue page. Alternating light and dark sections make each push read as a new chapter.
- **Recreate:** Incoming panel enters from the right edge while the outgoing page translates left at the same speed; 0.4-0.6 s with a fast start and soft landing (power3.out); incoming content fades in 0.2-0.3 s after the panel lands (ref-c6d0aa55f6 12.05-12.45, 28.05-28.45, 47.05-47.40 s). Vertical variant: a coloured section slides up off the frame while the next card rises from below (ref-5a2816d4db 6.95-7.35 s).
- **Timing:** 0.35-0.6 s per push.
- **Runtime:** Studio.fx.push, Studio.transition
- **Precedents:** `ref-392ee4d0f9` at 8.47 s; `ref-5a2816d4db` at 6.95 s; `ref-736d4ef2c2` at 5.97 s; `ref-95c96d5c47` at 6.27 s; `ref-b97f9168c6` at 19.25 s; `ref-c324a3d516` at 3.55 s; `ref-c6d0aa55f6` at 12.05 s
- **Watch out:** Pushing every scene turns the film into a slideshow / Different speeds for the two panels open a gap

### `grid-wave-propagation`: Grid wave propagation
- **Lifecycle** tested (preview); support native; seen in 6 reference(s). Record: [`grid-wave-propagation.json`](../catalogue/data/references/grid-wave-propagation.json)
- **What:** Every cell of a grid changes state with a delay proportional to its distance from an origin, so a pattern change becomes a visible ripple and a transition gains a source and direction.
- **Recreate:** Grid stagger with an 'amount' for the whole wave; per-cell tween 0.3-0.5 s; flips rotate quarter turns so Truchet arcs reconnect.
- **Timing:** Observed waves cross the frame in about 1-2 s (ref-92c22222a2 7.58-9.58 s).
- **Runtime:** Studio.fx.gridWave, Studio.draw.grid
- **Precedents:** `ref-0bf0254a3d` at 2.85 s; `ref-1cbe55c987` at 10.52 s; `ref-70c57c2adf` at 5.3 s; `ref-92c22222a2` at 7.58 s; `ref-b97f9168c6` at 8.4 s; `ref-c324a3d516` at 6.38 s
- **Watch out:** Too many cells (DOM cost, moire at 720p) / Uniform waves with no origin read as a fade

### `crt-collapse-to-line`: CRT collapse to line
- **Lifecycle** specified; support native; seen in 4 reference(s). Record: [`crt-collapse-to-line.json`](../catalogue/data/references/crt-collapse-to-line.json)
- **What:** The frame or a word collapses vertically into a thin bright line (scaleY to almost zero, slight horizontal stretch, brightness up); the line holds or extends and becomes a rule, a connector or the next element. Reversed, the line opens into a new frame.
- **Recreate:** scaleY 1 -> 0.02 with power3.in over 0.12 s, scaleX 1 -> 1.08, filter brightness 1 -> 1.6 and a 2-4 px vertical blur during the squash; the remaining line is a separate 1-2 px rule that takes over (extend scaleX or fade). transform-origin at the vertical centre.
- **Timing:** Squash 0.10-0.15 s; line hold 0.1-0.3 s.
- **Runtime:** not built yet
- **Precedents:** `ref-70c57c2adf` at 1.62 s; `ref-aff23e662b` at 3.35 s; `ref-b97f9168c6` at 4.57 s; `ref-c87967b288` at 3.7 s
- **Watch out:** Too slow reads as a squash-and-stretch gag, not a power-off / Without the brightness lift it looks like a scale bug

### `random-bar-wipe`: Random bar wipe
- **Lifecycle** specified; support native; seen in 3 reference(s). Record: [`random-bar-wipe.json`](../catalogue/data/references/random-bar-wipe.json)
- **What:** Horizontal bars of random length and position appear across the frame, merge into full cover and clear to reveal the next scene. It reads as a quick digital redraw, faster and less formal than a straight wipe.
- **Recreate:** 10-14 horizontal bars of 1/16-1/10 of the frame height with seeded x offsets and lengths; bars in the incoming scene's colour grow in from random x over about 0.12 s until full cover at about 0.15 s; the scene swaps under cover; bars clear in the same pattern over 0.15 s (ref-2860712d4e 11.21-11.51 s, 0.3 s in all, 30 fps sheet).
- **Timing:** About 0.3 s.
- **Runtime:** Studio.transition
- **Precedents:** `ref-2860712d4e` at 11.21 s; `ref-fb375e07e2` at 12.85 s; `ref-fd749e7ebc` at 3.42 s
- **Watch out:** An unseeded pattern changes between renders / Too slow reads as a broken screen

### `strip-slice-offset`: Strip-slice offset
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`strip-slice-offset.json`](../catalogue/data/references/strip-slice-offset.json)
- **What:** An image or word is divided into strips that shift independently and then realign, suggesting analysis, fragmentation or a reveal.
- **Recreate:** N clones each clipped to one strip (clip-path inset), staggered y offsets with power3 ease.
- **Timing:** About 0.6-1 s.
- **Runtime:** not built yet
- **Precedents:** `ref-b97f9168c6` at 8.4 s; `ref-c93524ef20` at 7.5 s
- **Watch out:** Many strips on large images multiply paint cost

### `aperture-iris-transition`: Aperture iris (bladed) transition
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`aperture-iris-transition.json`](../catalogue/data/references/aperture-iris-transition.json)
- **What:** A camera-aperture shape (six blades, a hexagon at the centre) closes over the frame to a point on black, or opens from a point onto the next scene. For a photography or camera subject the transition is the subject's own mechanism, so it reads as motivated.
- **Recreate:** clip-path polygon (6-8 vertices) centred on the subject; radius from the half-diagonal to 0 over 0.1-0.3 s with power2.in to close, 0 to full with power2.out to open; rotate the polygon 30-60 deg during the move to suggest blades; a dark rim with faint blade lines.
- **Timing:** Close 0.1-0.3 s (reference 26.46-26.56 s); the opening at 2.6 s shows the blade pattern as a still before it opens.
- **Runtime:** Studio.fx.iris
- **Precedents:** `ref-7a185cb08d` at 2.6 s
- **Watch out:** Outside a camera context it is a gimmick / A plain circle reads as a generic iris; the blades make it an aperture

### `curtain-bookends`: Theatre curtain bookends
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`curtain-bookends.json`](../catalogue/data/references/curtain-bookends.json)
- **What:** Curtains part to open the story and close at the end, framing the piece as a performance and giving it a clear beginning and end.
- **Recreate:** Two panels translating outward with ease-in-out; optional skew sway; fold texture.
- **Timing:** About 2 s open (ref-910d9fc567 0-2.1 s), about 1-2 s close at the end.
- **Runtime:** not built yet
- **Precedents:** `ref-910d9fc567` at 1 s
- **Watch out:** Kitsch when the story is not theatrical

### `diegetic-object-wipe`: Diegetic object wipe
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`diegetic-object-wipe.json`](../catalogue/data/references/diegetic-object-wipe.json)
- **What:** Something that belongs to the scene (an eyelid, a page, a door, a card, a hand) moves across the frame and becomes the matte for the cut, so the transition is part of the story instead of an effect laid on top.
- **Recreate:** Draw the object as an SVG shape in the overlay layer (two lids, a page, a panel); animate its path or transform to full cover with power2.in; swap scenes under full cover; reopen with power2.out or cut to the next scene on the object's colour. Eyelid: two curved paths meeting at the horizon line, lashes as strokes.
- **Timing:** Close 0.3-0.6 s; hold 0-0.3 s; open 0.3-0.5 s.
- **Runtime:** not built yet
- **Precedents:** `ref-81650adf49` at 17.63 s
- **Watch out:** An object that does not belong to the scene reads as a generic wipe / Lid or page edges with hard straight lines look mechanical; curve and soften them

### `dither-edge-wipe`: Dithered-edge wipe
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`dither-edge-wipe.json`](../catalogue/data/references/dither-edge-wipe.json)
- **What:** A wipe from a dark scene to a light one whose leading edge is a soft band of dithered grain, so the change reads as print or particles turning over rather than a hard line. It suits films built from dots or print texture.
- **Recreate:** A vertical edge crosses left to right in about 0.35 s; the edge is a band about 15-20% of the width of light dots thinning into the dark; the incoming headline is already in place under it.
- **Timing:** 7.50-7.85 s, one use in 15 s.
- **Runtime:** Studio.fx.wipe
- **Precedents:** `ref-2a6c654bfe` at 7.55 s
- **Watch out:** Unseeded noise flickers between renders / A wide band turns muddy

### `foreground-occluder-pass`: Foreground occluder pass
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`foreground-occluder-pass.json`](../catalogue/data/references/foreground-occluder-pass.json)
- **What:** A large, heavily blurred object sweeps across the lens for a few frames while the subject changes form behind it. The occluder hides the change and adds depth, like a camera passing a foreground object.
- **Recreate:** Foreground element 1.5-3x the frame height, blur 20-40 px, opacity 0.6-0.9, crossing the frame in 0.2-0.3 s (ref-19cee08f9c 4.12-4.35 s, 30 fps strip); swap or morph the subject while it is covered; move the occluder against the camera's direction.
- **Timing:** A 0.2-0.3 s pass.
- **Runtime:** Studio.fx.smear
- **Precedents:** `ref-19cee08f9c` at 4.12 s
- **Watch out:** A sharp occluder reads as an object in the scene, not a lens pass / Large blur filters cost raster time

### `liquid-pour-transition`: Liquid pour transition
- **Lifecycle** implemented; support -; seen in 1 reference(s). Record: [`liquid-pour-transition.json`](../catalogue/data/references/liquid-pour-transition.json)
- **What:** A wavy liquid surface rises to cover the frame, then either drains away or becomes the next scene's background.
- **Timing:** 1.0-1.6 s; ease in on the rise
- **Runtime:** liquid-transition
- **Precedents:** `ref-0b13aa7f02` at 13.65 s

### `stacked-panel-wipe`: Stacked colour-panel wipe
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`stacked-panel-wipe.json`](../catalogue/data/references/stacked-panel-wipe.json)
- **What:** Two flat colour panels slide across from the same side one after the other: the first covers the outgoing scene, the second follows over it and stays as the next scene's background. The double pass reads as a deliberate brand gesture and hands over the next section's colour.
- **Recreate:** Panel 1 (accent colour) enters from the left with a fast ease-out to full cover in about 0.13 s, holds about 0.15 s, panel 2 (the next background colour) enters from the same side in about 0.22 s; new content starts after panel 2 lands. Single-panel variant: one panel crosses in about 0.25 s.
- **Timing:** Whole gesture about 0.5 s (8.95-9.47 s); single panel about 0.25 s (36.45-36.70 s); used twice in 40 s.
- **Runtime:** Studio.fx.shapeCover, Studio.fx.push
- **Precedents:** `ref-05acc490f6` at 9.03 s
- **Watch out:** Panel colours not used elsewhere read as a glitch / Slower than about 0.6 s it feels like a curtain

<a id="transition-continuous"></a>
## Transitions without a cut

One stage that evolves, a breath on the empty stage, a line or shape that persists.

### `empty-stage-dip`: Empty stage dip (a breath between sections)
- **Lifecycle** tested (preview); support native; seen in 16 reference(s). Record: [`empty-stage-dip.json`](../catalogue/data/references/empty-stage-dip.json)
- **What:** Instead of crossfading scene into scene, the outgoing content leaves and the bare background holds for 0.15-0.4 s, then the next section's headline enters. The empty frame is a full stop: the viewer resets before the new idea.
- **Recreate:** Outgoing group opacity 1 -> 0 and y +8..16 px over 0.3 s (power2.in); hold the empty stage 0.15-0.4 s while background drift and texture keep moving (never a frozen frame); next title enters (typewriter or line-mask rise). Snap the next title to the first word of the next narration phrase, so the dip sits inside the narration pause.
- **Timing:** Exit 0.25-0.4 s; empty hold 0.15-0.4 s; entrance 0.4-0.8 s.
- **Runtime:** Studio.fx.dip
- **Precedents:** `ref-05acc490f6` at 13.48 s; `ref-0b2552b64e` at 44.17 s; `ref-31ce9d6332` at 53.5 s; `ref-37644838b5` at 22.35 s; `ref-58ff9f39df` at 4.02 s; `ref-5a2816d4db` at 13.15 s; `ref-6f68999b60` at 17.68 s; `ref-9459c8097f` at 7.9 s
- **Watch out:** Holds longer than about 0.5 s with narration running break the no-static-frame rule / A dip to pure black on a light film reads as a glitch; dip to the film's own background

### `single-stage-progression`: Single-stage progression
- **Lifecycle** tested (preview); support native; seen in 16 reference(s). Record: [`single-stage-progression.json`](../catalogue/data/references/single-stage-progression.json)
- **What:** One persistent layout (a diagram, a recipe stage, a theatre set, a 3D scene) evolves: elements are added, re-labelled, stamped, connected or lit, while a caption or step header names the change. The viewer never re-orients, so attention goes to what changed.
- **Recreate:** Persistent DOM; per-step tweens on existing elements; state changes chained from the previous state for seek safety; optional progress tracker and changing caption.
- **Timing:** A state change every 2-8 s (ref-95c96d5c47 sections of about 6 s; ref-c3bc609841 about 5 s per step); no hard cuts in two references.
- **Runtime:** Studio.comp.progression
- **Precedents:** `ref-0b2552b64e` at 0.38 s; `ref-216f4eaeef` at 3 s; `ref-31ce9d6332` at 15.57 s; `ref-37644838b5` at 10 s; `ref-910d9fc567` at 10 s; `ref-95c96d5c47` at 12.31 s; `ref-99713f6e72` at 2.62 s; `ref-a2496929ca` at 0.37 s
- **Watch out:** Too many simultaneous changes per step / No caption naming the change

### `morph-ready-shape-sequence`: Geometric shape morph sequence
- **Lifecycle** tested (preview); support native; seen in 7 reference(s). Record: [`morph-ready-shape-sequence.json`](../catalogue/data/references/morph-ready-shape-sequence.json)
- **What:** A single shape changes identity in place (circle to triangle to square to star), so an idea transforms continuously instead of being replaced. Matching point structure keeps the morph clean and untwisted.
- **Recreate:** Same point count, same start point (top) and winding (clockwise) for every shape; power3.inOut string interpolation of path data.
- **Timing:** About 0.6 s per morph with 0.3-0.5 s holds (ref-92c22222a2 5.71-7.42 s).
- **Runtime:** Studio.draw.shape, Studio.draw.morphChain, Studio.draw.morph
- **Precedents:** `ref-05c4222dae` at 5.67 s; `ref-0bf0254a3d` at 1.5 s; `ref-57fd2ce3b4` at 0.19 s; `ref-736d4ef2c2` at 17.5 s; `ref-92c22222a2` at 5.71 s; `ref-c324a3d516` at 3.81 s; `ref-fd749e7ebc` at 4.12 s
- **Watch out:** Different point counts or start points cause twisting / Morphing to detailed letterforms needs many more points or MorphSVG

### `continuous-line-spine`: Continuous line as narrative spine
- **Lifecycle** tested (preview); support native; seen in 4 reference(s). Record: [`continuous-line-spine.json`](../catalogue/data/references/continuous-line-spine.json)
- **What:** One line persists or is redrawn across scene changes and changes role (heartbeat, horizon, path, underline), so a story of many scenes reads as one continuous thought.
- **Recreate:** Line on a layer above the scenes (or at the same position in each scene) drawn with a pen-led stroke; scene cuts never cross the line's position.
- **Timing:** Whole piece; bookend draws of 1-2 s.
- **Runtime:** Studio.draw.pen, Studio.draw.layer
- **Precedents:** `ref-0bf0254a3d` at 13.1 s; `ref-19cee08f9c` at 0.5 s; `ref-49459ad8c1` at 2.5 s; `ref-5924215625` at 0.5 s
- **Watch out:** The line competes with scene content if it is too heavy / Breaking position continuity at a cut loses the effect

### `act-break-fade-black`: Act break through black
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`act-break-fade-black.json`](../catalogue/data/references/act-break-fade-black.json)
- **What:** In a wordless story, acts are separated by a fade to black, a short black hold and a fade up on the next location; the black reads as time passing. Location changes inside an act are plain cuts.
- **Recreate:** Fade out 0.8 s (ref-1e22836116 23.6-24.4 s), black hold 0.8 s (24.4-25.2 s), fade up 0.6 s (25.3-25.9 s); opening fade in 0.5 s (3.4-3.9 s); closing fade 0.5 s (43.2-43.7 s); cuts inside acts at 9.90 and 34.60 s.
- **Timing:** About 2.2 s per act break.
- **Runtime:** Studio.transition
- **Precedents:** `ref-1e22836116` at 23.6 s; `ref-a943607659` at 22.25 s
- **Watch out:** On a light-canvas film fade to the film's own background (see empty-stage-dip) / With narration running, a 0.8 s black hold breaks the no-static-frame rule unless it sits in a narration pause

### `background-palette-lift`: Empty background changes palette
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`background-palette-lift.json`](../catalogue/data/references/background-palette-lift.json)
- **What:** With nothing on screen, the background itself slowly changes colour (dark to light), so a new emotional register begins without a cut or a wipe; the reverse move closes it.
- **Recreate:** Previous content fades out first (ref-58ff9f39df 120.77-120.93 s); the empty background tweens black to warm cream with a vignette over 0.6 s, ease-in-out (120.97-121.6 s); the persistent header stays; the first line of the new section enters after the lift. Close: cream to black over 0.8 s with an empty frame (137.5-138.3 s).
- **Timing:** 0.6-0.8 s per lift; frame empty during the lift.
- **Runtime:** not built yet
- **Precedents:** `ref-58ff9f39df` at 120.97 s; `ref-910d9fc567` at 34.08 s
- **Watch out:** Content still on screen during the lift looks like a fade bug / A lift under about 0.3 s reads as a flash

### `canvas-camera-tour`: Camera tour over one canvas
- **Lifecycle** tested (preview); support native; seen in 2 reference(s). Record: [`canvas-camera-tour.json`](../catalogue/data/references/canvas-camera-tour.json)
- **What:** All the screens of a demo live on one large canvas, and a virtual camera pans, pushes in and pulls back to frame each step. There is never a cut, so the viewer always knows where each panel sits relative to the others.
- **Recreate:** Lay panels out on a canvas 2-3x the frame. Animate one camera transform (translate and scale) per step: a push-in or pan of 0.6-1.0 s with power2.inOut, then a 2-5 s hold with a slow drift (scale +2-3%). Elements that move between panels travel in canvas space while the camera follows them (ref-ad023ce9dc 17.9-18.7 s). End with a pull-back that shows the whole canvas (25.19-25.9 s).
- **Timing:** Moves 0.6-1.0 s; holds 2-5 s; 4 moves in 30 s in the reference.
- **Runtime:** Studio.space.tour
- **Precedents:** `ref-ad023ce9dc` at 18.31 s; `ref-c87967b288` at 11.56 s
- **Watch out:** Moving the camera and the content at the same time with no focus point confuses the eye / Fast pans over dense text are unreadable; ease in and out and hold

<a id="kinetic-typography"></a>
## Kinetic typography

Words as the picture: per-beat words, builds, rolls, strikes, scrambles, structures.

### `word-slot-roll`: Word or number slot roll
- **Lifecycle** tested (preview); support native; seen in 16 reference(s). Record: [`word-slot-roll.json`](../catalogue/data/references/word-slot-roll.json)
- **What:** One slot of a sentence or figure rolls vertically to its next value while everything around it holds still, so the change itself is the message (what varies, what stays).
- **Recreate:** yPercent step of a masked column with back.out(1.5) over about 0.5 s; optional width tween so centred lines re-flow smoothly.
- **Timing:** One roll per beat; each entry held at least about 0.6 s.
- **Runtime:** Studio.type.roll
- **Precedents:** `ref-0b13aa7f02` at 14.49 s; `ref-1cbe55c987` at 2.5 s; `ref-31ce9d6332` at 3.78 s; `ref-32fea7dae3` at 4.08 s; `ref-49459ad8c1` at 6 s; `ref-9ed4034cad` at 9.46 s; `ref-a943607659` at 5.59 s; `ref-b34f751c59` at 2.66 s
- **Watch out:** Entries changing faster than reading speed / Different word widths jumping without fit

### `accent-punctuation-motif`: Accent punctuation motif
- **Lifecycle** tested (preview); support native; seen in 15 reference(s). Record: [`accent-punctuation-motif.json`](../catalogue/data/references/accent-punctuation-motif.json)
- **What:** A punctuation mark in the accent colour becomes the piece's signature: it ends statements with conviction, travels between scenes (i-dot, decimal point, full stop) and blooms or draws the next element.
- **Recreate:** Separate span for the mark; the mark is the measured source for bloom or pen effects.
- **Timing:** Appears with the word; holds 0.3-1 s before it acts.
- **Runtime:** Studio.comp.wordBeats, Studio.fx.bloom
- **Precedents:** `ref-05c4222dae` at 1.13 s; `ref-0bf0254a3d` at 10.52 s; `ref-19cee08f9c` at 1.4 s; `ref-2860712d4e` at 7.88 s; `ref-49459ad8c1` at 2.5 s; `ref-7a185cb08d` at 0.77 s; `ref-92c22222a2` at 11.48 s; `ref-b4e79aa0a4` at 1.53 s
- **Watch out:** Reusing a specific brand's accent colour and serif with the dot reproduces that brand's identity: use the project's own style tokens / Every sentence ending in a coloured dot dilutes it

### `two-tone-headline-pair`: Two-tone headline pair (statement, then counterpoint)
- **Lifecycle** tested (preview); support native; seen in 10 reference(s). Record: [`two-tone-headline-pair.json`](../catalogue/data/references/two-tone-headline-pair.json)
- **What:** A two-line headline in which the first line states and the second answers or turns, set in the accent colour (or a lighter grey) and arriving a beat later. The colour split shows where the payoff is without a highlight effect, and repeated per section it becomes the film's headline grammar.
- **Recreate:** Line 1 in the body colour, line 2 in the accent (or about 50% grey for a quieter contrast), same size and weight; words fade or rise in about 0.07-0.1 s apart; line 2 starts 0.15-0.5 s after line 1, or on the next accent. Left-aligned beside a proof card, or centred.
- **Timing:** Headline complete in about 0.3-0.6 s; one pair per section of about 2-3 s.
- **Runtime:** Studio.comp.headline
- **Precedents:** `ref-0b2552b64e` at 2.4 s; `ref-32fea7dae3` at 3.35 s; `ref-5a2816d4db` at 1.13 s; `ref-9459c8097f` at 1.12 s; `ref-9ed4034cad` at 3.38 s; `ref-b8cf9a12b0` at 3.38 s; `ref-c2addc76df` at 0.88 s; `ref-c6d0aa55f6` at 1.27 s
- **Watch out:** Using the accent on every line 2 and elsewhere too dilutes it / A line 2 longer than line 1 loses the punch

### `word-per-beat-sequence`: Word-per-beat typographic sequence
- **Lifecycle** tested (preview); support native; seen in 10 reference(s). Record: [`word-per-beat-sequence.json`](../catalogue/data/references/word-per-beat-sequence.json)
- **What:** A line of copy is split across hard cuts, one word (or short phrase) per card, each card with its own background, colour or treatment. The rhythm of the cuts carries the sentence; contrast between cards keeps every cut legible.
- **Recreate:** Hard cuts on a beat grid; per-word entrance (mask rise, smear, character drop, stretch) of 0.2-0.5 s with expo or power ease-out; no exits (the cut replaces the card).
- **Timing:** Measured cut spacing 0.23-0.47 s (ref-92c22222a2 11.25-12.65 s; ref-1cbe55c987 10.52-12.00 s), about 0.33-0.5 s (ref-0bf0254a3d), about 0.4-2.5 s (ref-b97f9168c6). Readable minimum is about 0.25 s for one short word.
- **Runtime:** Studio.comp.wordBeats, Studio.rhythm.grid
- **Precedents:** `ref-05acc490f6` at 0.38 s; `ref-0bf0254a3d` at 10.52 s; `ref-1cbe55c987` at 10.52 s; `ref-58ff9f39df` at 106.4 s; `ref-70c57c2adf` at 2.29 s; `ref-81650adf49` at 8.56 s; `ref-92c22222a2` at 11.25 s; `ref-b4e79aa0a4` at 0.98 s
- **Watch out:** Cards under 0.25 s for words longer than one syllable become unreadable / Too many different treatments read as a sampler, not a sentence

### `self-describing-kinetic-words`: Self-describing kinetic words
- **Lifecycle** tested (preview); support native; seen in 8 reference(s). Record: [`self-describing-kinetic-words.json`](../catalogue/data/references/self-describing-kinetic-words.json)
- **What:** Each word performs its own meaning, so the motion is the definition. It works because the viewer reads and sees the same idea at once (dual coding) and the treatment never feels arbitrary.
- **Recreate:** Short single-property tweens (scaleX, rotation, per-character y with seeded rotation, letter-spacing) of 0.3-0.6 s with expressive eases (expo.out, back.out); outlined echo copies for repetition words.
- **Timing:** One word per 0.5-1.5 s in the references; each treatment resolves within about 60% of its card.
- **Runtime:** Studio.comp.wordBeats, Studio.fx.smear, Studio.type.cascade, Studio.type.track
- **Precedents:** `ref-392ee4d0f9` at 3.9 s; `ref-57fd2ce3b4` at 16.2 s; `ref-58ff9f39df` at 27.57 s; `ref-92c22222a2` at 11.72 s; `ref-a2496929ca` at 0.37 s; `ref-b4e79aa0a4` at 2.53 s; `ref-b97f9168c6` at 27 s; `ref-fb375e07e2` at 2.8 s
- **Watch out:** Treatment that contradicts the word (a slow 'snap') / Using it for words that have no motion meaning

### `typographic-repetition`: Typographic repetition walls
- **Lifecycle** specified; support native; seen in 6 reference(s). Record: [`typographic-repetition.json`](../catalogue/data/references/typographic-repetition.json)
- **What:** A single word repeated into a pattern (tiled grid or rows scrolling in opposite directions) becomes texture and insistence: the word turns into wallpaper.
- **Recreate:** Finite linear x tweens per row (alternating sign), outline/solid alternation; grid stagger for tiling.
- **Timing:** Rows drift 1-3 s; tiling in under 0.5 s.
- **Runtime:** not built yet
- **Precedents:** `ref-05acc490f6` at 28.3 s; `ref-05c4222dae` at 2.86 s; `ref-70c57c2adf` at 12.93 s; `ref-92c22222a2` at 12.5 s; `ref-b97f9168c6` at 10.5 s; `ref-c324a3d516` at 10.12 s
- **Watch out:** Infinite loops are banned: compute finite tween lengths / Moire with thin outline type at 720p

### `centred-word-build`: Centred word-by-word headline build
- **Lifecycle** tested (preview); support native; seen in 5 reference(s). Record: [`centred-word-build.json`](../catalogue/data/references/centred-word-build.json)
- **What:** Words arrive one by one and the existing words slide aside so the growing line stays centred, letting the viewer read at speaking pace and ending on an accent word.
- **Recreate:** Measure each prefix width; animate the line's x so the visible prefix is centred; new words rise or fade in with a short stagger.
- **Timing:** About 0.3-0.6 s per word.
- **Runtime:** Studio.comp.headline
- **Precedents:** `ref-6f68999b60` at 0.38 s; `ref-85d3a83400` at 0.38 s; `ref-9459c8097f` at 0.38 s; `ref-9ed4034cad` at 0.38 s; `ref-ce769bc33e` at 0.5 s
- **Watch out:** Re-centring jumps if widths are measured before fonts load (Studio.build waits for fonts)

### `glitch-type`: Glitch type
- **Lifecycle** observed; support approximation; seen in 4 reference(s). Record: [`glitch-type.json`](../catalogue/data/references/glitch-type.json)
- **What:** A word flickers with colour-channel offsets and horizontal slice shifts for a few frames, signalling code, error or digital noise.
- **Recreate:** Two tinted copies with mix-blend-mode screen/multiply and stepped x offsets; clip-path bands of a clone with stepped x; seeded so it repeats identically.
- **Timing:** Bursts of 0.1-0.3 s.
- **Runtime:** not built yet
- **Precedents:** `ref-58ff9f39df` at 3.62 s; `ref-70c57c2adf` at 12.16 s; `ref-aff23e662b` at 11.97 s; `ref-b97f9168c6` at 3.9 s
- **Watch out:** Overuse is cliche / Flashing above safe photosensitivity limits

### `strike-and-correct`: Strike and correct
- **Lifecycle** tested (preview); support native; seen in 4 reference(s). Record: [`strike-and-correct.json`](../catalogue/data/references/strike-and-correct.json)
- **What:** A claim types in, a red line strikes it, the struck claim shrinks and steps back (smaller, greyer, higher), and the correction types in below in the accent colour. The viewer sees the old belief and the new fact in one frame.
- **Recreate:** Typewriter the claim (Studio.type.typewriter, about 25-35 cps); strike: a 2-4 px accent-red line scaleX 0 -> 1 from the left over 0.15-0.25 s (power2.out), slightly overshooting the text box; demote: scale 1 -> 0.55, y up, opacity 1 -> 0.5 over 0.3 s; correction: typewriter in the accent colour 0.1 s later. Sound: a soft scratch or tick on the strike, a pop on the correction's last character.
- **Timing:** Claim 0.4-0.8 s; strike 0.2 s; demote 0.3 s; correction 0.5-0.9 s.
- **Runtime:** Studio.type.strike, Studio.type.strikeCorrect
- **Precedents:** `ref-6f68999b60` at 7.92 s; `ref-99713f6e72` at 5.05 s; `ref-9ed4034cad` at 1.62 s; `ref-a339360a56` at 22.26 s
- **Watch out:** Struck text removed too fast: the viewer never reads what was wrong / Red strike on a red-accent film disappears; use the film's 'wrong' colour consistently

### `dim-previous-line-stack`: Dim the previous lines as each new one lands
- **Lifecycle** specified; support native; seen in 3 reference(s). Record: [`dim-previous-line-stack.json`](../catalogue/data/references/dim-previous-line-stack.json)
- **What:** A list or argument builds line by line in one block; as each new line lands, the earlier lines drop to grey, so only the newest has full contrast. It shows progress and keeps the eye on the new item without colour or arrows; a larger closing line sums the list up.
- **Recreate:** Lines stacked at one line of spacing, left-aligned. On each beat: earlier lines go from full contrast to about 40% (grey) in 1 frame (up to 0.1 s), then 1-2 frames later the new line rises from a mask (yPercent 100 -> 0 over 0.07-0.15 s, power3.out). The summary line enters at 1.5-2x size after the last item while all items stay grey.
- **Timing:** One line per 0.5-1.0 s on the beat; the dim leads the new line by about 0.07 s (8.50 s vs 8.57 s).
- **Runtime:** Studio.type.rise, Studio.comp.itemList
- **Precedents:** `ref-19cee08f9c` at 11.55 s; `ref-32fea7dae3` at 8.5 s; `ref-49459ad8c1` at 6.04 s
- **Watch out:** Dimming too far makes earlier lines unreadable: keep them legible for re-reading / More than about six lines crowd a portrait frame

### `palette-cycle-card`: Palette cycle on a held word
- **Lifecycle** specified; support native; seen in 3 reference(s). Record: [`palette-cycle-card.json`](../catalogue/data/references/palette-cycle-card.json)
- **What:** One word holds its place while its background and type colours swap on hard cuts several times a second, so the word reads as one thing shown in many themes, or, faster, as mounting agitation.
- **Recreate:** Word position, size and font fixed; on each cut swap the background and text colour pair: 4 pairs every 0.23-0.27 s (7-8 frames at 30 fps) in ref-b4e79aa0a4 6.24-6.98 s; every 0.1 s (3 frames) on repeated words at the end of a montage in ref-58ff9f39df 113.9-115.8 s. Contrast-safe pairs only.
- **Timing:** 0.1-0.27 s per colour; 3-6 swaps.
- **Runtime:** Studio.comp.wordBeats
- **Precedents:** `ref-58ff9f39df` at 113.9 s; `ref-b4e79aa0a4` at 6.24 s; `ref-cfaf668ebf` at 16.67 s
- **Watch out:** Changing the word at the same time makes it unreadable / Photosensitivity cap (WCAG 2.3.1, three-flashes rule; not measured on the reference): no more than 3 flashes, that is 6 opposing large luminance changes, in any 1 s over a large area. Alternating dark and light full-frame backgrounds every 0.1 s gives about 5 flashes a second; keep swaps at 0.2 s or longer when consecutive backgrounds differ strongly in lightness, or change hue at similar lightness.

### `chromatic-punch-word`: Chromatic punch word
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`chromatic-punch-word.json`](../catalogue/data/references/chromatic-punch-word.json)
- **What:** A single word enters about 20% oversized with red and cyan copies offset sideways, and in 2-4 frames scales to size while the copies collapse into one clean word. The split reads as impact and speed without a camera shake.
- **Recreate:** Three stacked copies (or text-shadow): red at -dx, cyan at +dx, white on top with mix-blend-mode screen on dark; dx 8-14 px -> 0 and scale 1.2 -> 1.0 over 0.10-0.15 s with power4.out, placed on the beat. Optional 1-frame opacity flicker on the fringes.
- **Timing:** Settle 0.10-0.15 s; one word per beat (0.5-1.0 s).
- **Runtime:** not built yet
- **Precedents:** `ref-81650adf49` at 10.52 s; `ref-dc626241e6` at 1.55 s
- **Watch out:** Red/cyan fringes on a light canvas look like misregistration; use on dark sections or swap to the accent pair / A split that never settles hurts legibility

### `letter-shatter`: Letter shatter
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`letter-shatter.json`](../catalogue/data/references/letter-shatter.json)
- **What:** A solid glyph fractures into shards that fly apart with rotation, turning a letter into debris for emphasis or a transition.
- **Recreate:** Clones of the glyph clipped to seeded polygon shards; per-shard x, y, rotation with power2.in; optional reverse to assemble.
- **Timing:** About 0.5-0.8 s.
- **Runtime:** not built yet
- **Precedents:** `ref-736d4ef2c2` at 20.8 s; `ref-99713f6e72` at 7.55 s
- **Watch out:** Too few shards look like a cut, too many cost paint time

### `swiss-kinetic-grid`: Swiss kinetic grid typography
- **Lifecycle** implemented; support -; seen in 2 reference(s). Record: [`swiss-kinetic-grid.json`](../catalogue/data/references/swiss-kinetic-grid.json)
- **What:** Words land on a visible grid with hard cuts, mask rises and character cascades; colour marks the key word.
- **Timing:** Hard cuts on beats; 0.3-0.5 s entrances
- **Runtime:** text-mask-rise, char-cascade, push-transition, marker-highlight
- **Precedents:** `ref-32fea7dae3` at 3.08 s; `ref-c324a3d516` at 2.62 s

### `text-scramble-decode`: Text scramble decode
- **Lifecycle** tested (preview); support native; seen in 2 reference(s). Record: [`text-scramble-decode.json`](../catalogue/data/references/text-scramble-decode.json)
- **What:** Each character slot cycles through random glyphs and locks to its final letter, slot by slot (usually left to right), so the word 'decodes' into place.
- **Recreate:** Split the word into character slots of fixed width (monospace avoids reflow); for each frame before a slot's lock time, pick a glyph from a charset with a seeded PRNG keyed by (slot, frame index), so any seek shows the same glyph; lock times staggered 30-60 ms per slot; colour accent -> body on lock.
- **Timing:** 0.3-0.6 s total; 30-60 ms stagger per character; glyph change every 1-2 frames.
- **Runtime:** Studio.type.scramble
- **Precedents:** `ref-99713f6e72` at 5.2 s; `ref-aff23e662b` at 1.89 s
- **Watch out:** Math.random or time-based glyph picks break deterministic renders / Proportional fonts make the word jitter in width

### `fluid-type-resolve`: Fluid type dissolve and resolve
- **Lifecycle** specified; support additional-dependencies; seen in 1 reference(s). Record: [`fluid-type-resolve.json`](../catalogue/data/references/fluid-type-resolve.json)
- **What:** Turbulent ink pulls a word apart into streaks and then settles back into the word, so the type seems made of the same matter as the scene. A word's arrival or departure becomes a material event.
- **Recreate:** Pre-rendered fluid simulation (yellow and grey ink on black) with the word as a collider or initial density, about 2.5 s of billowing (ref-19cee08f9c 8.0-10.4 s); the clean word sharpens over the ink at 9.3-9.5 s, distorts into streaks 10.40-10.90 s and re-forms 10.96-11.29 s. Composite the plate under a clean HyperFrames word for the settled frames.
- **Timing:** Dissolve about 0.5 s; re-form about 0.35 s; ink section about 3 s.
- **Runtime:** not built yet
- **Precedents:** `ref-19cee08f9c` at 8.4 s
- **Watch out:** The word is unreadable for too long / Simulations are heavy and not deterministic in a browser; use a plate

### `gravity-letter-drop`: Gravity letter drop and topple
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`gravity-letter-drop.json`](../catalogue/data/references/gravity-letter-drop.json)
- **What:** The letters of a headline fall into place one by one from above with a small bounce, and later lose their footing and topple out of frame with rotation. Gravity makes the words feel like physical objects, and the exit undoes the entrance.
- **Recreate:** Entrance: each letter falls from y = -120% of the line height to 0 (power2.in), then a 6-10% bounce (back.out), with rotation from a seeded 10-20 degrees to 0; stagger about 0.03 s; a two-line headline lands in 0.3 s (ref-2860712d4e 6.78-7.06 s, 30 fps sheet). Exit: each letter takes a seeded rotation of 30-90 degrees and falls to y = +150% (power2.in), stagger 0.02 s, about 0.33 s (8.81-9.14 s).
- **Timing:** In 0.3 s; out 0.33 s; held about 1.7 s between.
- **Runtime:** Studio.type.split, Studio.type.cascade
- **Precedents:** `ref-2860712d4e` at 6.78 s
- **Watch out:** Unseeded rotations break determinism / Letters colliding at landing look messy; keep fall paths vertical

### `macro-typing-push`: Macro typing push
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`macro-typing-push.json`](../catalogue/data/references/macro-typing-push.json)
- **What:** After text is typed in a UI, the camera pushes into it at macro scale and glides along the line with motion blur while a soft gradient caret leads the next letters, so a few typed words become a full-frame headline without a scene change.
- **Recreate:** Scale the input text 1 -> about 8x about the caret (0.2-0.3 s, power3.in); translate x along the line at constant speed with a directional smear of 6-12 px while letters type at 15-25 characters per second; caret = a 60-120 px gradient block (accent to transparent) with a solid 4 px edge; exit with a 3D tilt (rotateY 20-30 deg) and fade over 0.2-0.3 s.
- **Timing:** Push 0.2-0.3 s; glide 0.7-1.0 s; exit 0.3 s (reference 2.12-3.15 s).
- **Runtime:** Studio.type.typewriter, Studio.fx.smear
- **Precedents:** `ref-ee70618e88` at 2.12 s
- **Watch out:** A fast glide makes the blurred letters unreadable / Pixelated type if the text is rasterised before scaling

### `markup-renders-to-type`: Raw markup renders into styled type
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`markup-renders-to-type.json`](../catalogue/data/references/markup-renders-to-type.json)
- **What:** Raw source text with its markup symbols types in monospace, then the symbols drop away and the word re-sets in the display face: the viewer sees input become output. Works for markdown, code and formulas.
- **Recreate:** Monospace typing with a block caret at about 10 characters/s (ref-3abcbedd20: the heading marker and first letter at 0.39 s, the whole word at 0.87 s); the swap to the serif passes through a scrambled mix (1.12 s) and lands by 1.88 s; the second line types with an emphasis marker and re-sets as the italic accent line (2.04-4.12 s). Accents on keystrokes. Swap mechanics not pinned (no 30 fps strip of 0.8-1.9 s).
- **Timing:** Type 0.5-1.0 s; swap about 0.3-1.0 s (estimated).
- **Runtime:** Studio.type.typewriter
- **Precedents:** `ref-3abcbedd20` at 0.39 s
- **Watch out:** A slow swap looks like a font-loading bug / Markup too small to read

### `per-character-blur-reveal`: Per-character blur reveal
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`per-character-blur-reveal.json`](../catalogue/data/references/per-character-blur-reveal.json)
- **What:** Each letter of a short line appears in turn, from heavy blur and low opacity to sharp, so a quiet or grateful line arrives softly instead of popping. The left-to-right stagger reads like the line being breathed out.
- **Recreate:** Split into characters; per character, filter blur 12-16 px -> 0 and opacity 0 -> 1 over about 0.3 s (power2.out), stagger 0.07 s; a 10-character line completes in about 1.1 s (ref-cfaf668ebf 42.47-43.53 s, 15 fps strip). Optional colour gradient across the line. Final glyph positions stay fixed (no tracking change).
- **Timing:** 0.07 s stagger, about 0.3 s per character, about 1 s per short line; hold at least 1.5 s.
- **Runtime:** Studio.type.split
- **Precedents:** `ref-cfaf668ebf` at 42.47 s
- **Watch out:** Blur on many large letters costs filter time every frame; cap at about 20 characters / A long stagger on a long line drags; switch to per-word

### `typographic-architecture`: Typographic architecture
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`typographic-architecture.json`](../catalogue/data/references/typographic-architecture.json)
- **What:** Words become structural members of a building that the sentence constructs: a heavy word rests on a thin beam that bends under its weight, a word hangs from the beam on hangers, a word rotated 90 degrees becomes a pillar, and the last line sets the floor or roof. The structure is the argument.
- **Recreate:** Lay out on a grid: beam as an SVG path whose sag (quadratic control point) scales with the weight of the word placed on it, settling with a damped oscillation (elastic.out) when the word lands; hangers as 1 px lines drawn top-down; pillar words rotated -90/90 degrees with transform-origin at their base and dropped into place; small serif connectors type in between. Camera: Studio.space.panTo to the newest member. Transitions inside the piece: push the view up off a word; zoom through a letter counter.
- **Timing:** One member every 1.5-3 s; beam settle 0.4-0.6 s.
- **Runtime:** not built yet
- **Precedents:** `ref-a2496929ca` at 0.37 s
- **Watch out:** Structure that does not match the meaning becomes decoration / Rotated words become hard to read; keep them short and large

<a id="motion-character"></a>
## Motion character

How things move: squash, smear, stamps, trails, pens, particles.

### `directional-smear`: Directional smear (motion-blur approximation)
- **Lifecycle** tested (preview); support approximation; seen in 10 reference(s). Record: [`directional-smear.json`](../catalogue/data/references/directional-smear.json)
- **What:** Fast entrances and exits are drawn smeared: the shape is stretched and blurred along its direction of travel on the fast frames and snaps crisp at rest. It reads as speed and impact, the way camera motion blur or hand-drawn smear frames do.
- **Recreate:** Expo-out travel; stretch anchored at the leading edge, decaying with speed; one-axis Gaussian blur decaying with the same ease; filter removed at rest.
- **Timing:** Observed smears last about 2-5 frames at 60 fps (ref-92c22222a2 11.25 s, 13.07 s); implemented default 0.45 s total with the blur mostly in the first 0.1 s.
- **Runtime:** Studio.fx.smear
- **Precedents:** `ref-0bf0254a3d` at 10.52 s; `ref-19cee08f9c` at 7.7 s; `ref-392ee4d0f9` at 3.77 s; `ref-70c57c2adf` at 3.32 s; `ref-7a185cb08d` at 0.77 s; `ref-92c22222a2` at 11.25 s; `ref-b4e79aa0a4` at 1 s; `ref-b8cf9a12b0` at 2.74 s
- **Watch out:** Too long a blur reads as out-of-focus, not speed / Blur on large areas costs CPU in the SVG filter path

### `particle-assemble-glyph`: Particles assemble a glyph (and break apart)
- **Lifecycle** specified; support native; seen in 10 reference(s). Record: [`particle-assemble-glyph.json`](../catalogue/data/references/particle-assemble-glyph.json)
- **What:** A field of small particles drifts, then each particle travels to a point sampled from a target glyph or mark, so the shape forms out of dust; reversed, a shape breaks into particles that drift away.
- **Recreate:** Rasterise the target glyph once to an offscreen canvas and sample filled pixels on a jittered grid (seeded) to get N targets; assign each particle a seeded start position; tween progress p 0 -> 1 with staggered power3.out (stagger by distance), draw on Canvas 2D each frame from p (no simulation state); swap to real text at p = 1. Disperse: reverse with outward velocity and fade.
- **Timing:** Converge 0.6-1.2 s; disperse 0.4-0.8 s.
- **Runtime:** not built yet
- **Precedents:** `ref-04d81a6a3e` at 2.62 s; `ref-05c4222dae` at 11.68 s; `ref-0b13aa7f02` at 24.89 s; `ref-19cee08f9c` at 5.66 s; `ref-2a6c654bfe` at 3.43 s; `ref-3abcbedd20` at 7.6 s; `ref-70c57c2adf` at 9.43 s; `ref-99713f6e72` at 10.24 s
- **Watch out:** Font not loaded before sampling gives the fallback glyph's shape / Too few particles leave the glyph unreadable; switch to real text at the end

### `pen-led-stroke`: Pen-led stroke
- **Lifecycle** tested (preview); support native; seen in 8 reference(s). Record: [`pen-led-stroke.json`](../catalogue/data/references/pen-led-stroke.json)
- **What:** A line is drawn by a visible point that travels ahead of it, so the line reads as the trace of an action (a pen, a pulse, a flight) rather than as a mask reveal. The point usually survives the stroke and becomes the next focal element.
- **Recreate:** Dash-offset reveal and dot position share one eased progress (ease-in-out or sine), so the dot stays on the tip; speeds of about 400-900 px/s.
- **Timing:** Observed strokes of 0.6-2 s (ref-49459ad8c1 question-mark stroke about 1 s; ref-5924215625 heartbeat line about 1.5 s).
- **Runtime:** Studio.draw.pen
- **Precedents:** `ref-0bf0254a3d` at 13.1 s; `ref-0fe1abc90a` at 4.55 s; `ref-19cee08f9c` at 0.3 s; `ref-2860712d4e` at 10.05 s; `ref-49459ad8c1` at 0.5 s; `ref-5924215625` at 0.5 s; `ref-a943607659` at 27.97 s; `ref-c93524ef20` at 5 s
- **Watch out:** Dot drawn with a different ease from the line drifts off the tip / Very fast pens (>1200 px/s) make the dot invisible

### `squash-stretch-bounce`: Squash-and-stretch bounce
- **Lifecycle** tested (preview); support native; seen in 5 reference(s). Record: [`squash-stretch-bounce.json`](../catalogue/data/references/squash-stretch-bounce.json)
- **What:** Objects fall with gravity-like acceleration, stretch while fast, squash on contact and rebound lower and quicker each time, which gives flat graphics weight and material.
- **Recreate:** power2.in falls and power2.out rises; rebound height x decay and duration x sqrt(decay); 50 ms squash, 100 ms recovery; scale about the base.
- **Timing:** First fall about 0.4-0.45 s; each rebound about 60% shorter in time.
- **Runtime:** Studio.space.bounce
- **Precedents:** `ref-2860712d4e` at 0.56 s; `ref-392ee4d0f9` at 0.8 s; `ref-c324a3d516` at 0.38 s; `ref-c3bc609841` at 3 s; `ref-fd749e7ebc` at 0.5 s
- **Watch out:** Squash on rigid objects (glass, metal) looks wrong; set squash to 0 / Bouncing everything makes the piece toy-like

### `stamp-state-change`: Stamp impact for state changes
- **Lifecycle** tested (preview); support native; seen in 5 reference(s). Record: [`stamp-state-change.json`](../catalogue/data/references/stamp-state-change.json)
- **What:** A short uppercase state label lands from large scale with a tilt and a tiny squash, sometimes jolting the card it hits. The physical metaphor (an official stamp) makes a state change feel final.
- **Recreate:** power4.in scale-down, 50 ms squash, back.out recovery, four-step x shake of the target.
- **Timing:** About 0.4 s total.
- **Runtime:** Studio.fx.stamp
- **Precedents:** `ref-58ff9f39df` at 46.75 s; `ref-6f68999b60` at 7.92 s; `ref-95c96d5c47` at 3.42 s; `ref-9ed4034cad` at 1.72 s; `ref-b8cf9a12b0` at 6.8 s
- **Watch out:** Overuse turns punctuation into noise / Stamps over important text hide it

### `onion-skin-trail`: Onion-skin motion trail
- **Lifecycle** tested (preview); support native; seen in 3 reference(s). Record: [`onion-skin-trail.json`](../catalogue/data/references/onion-skin-trail.json)
- **What:** Ghost copies of a moving object, each a few frames behind, show the arc, spacing and easing of the move at once, the way an animator's onion skin does. Spacing between ghosts makes acceleration visible.
- **Recreate:** Clones replay the same motion function with a time lag (about 2 frames) and decreasing opacity; ghosts hidden after the move.
- **Timing:** Ghost lag 1-3 frames; trail lifetime = the move plus 0.3 s.
- **Runtime:** Studio.space.trail
- **Precedents:** `ref-392ee4d0f9` at 0.8 s; `ref-92c22222a2` at 3.58 s; `ref-debf607232` at 3.35 s
- **Watch out:** Too many ghosts read as smear and cost DOM / Ghosts left on screen after the move

### `orbit-constellation`: Orbit constellation
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`orbit-constellation.json`](../catalogue/data/references/orbit-constellation.json)
- **What:** Satellites circling a centre express an ecosystem, a network or attraction, and keep a hold lively without new information.
- **Recreate:** Positions sampled from ellipses into keyframes (finite, deterministic) or a rotating ring with counter-rotated children; depth scale and opacity by angle.
- **Timing:** One orbit per 4-10 s.
- **Runtime:** not built yet
- **Precedents:** `ref-1cbe55c987` at 8.5 s; `ref-92c22222a2` at 5.71 s
- **Watch out:** Infinite rotation loops are banned: compute a finite duration / Too many satellites crowd the centre

<a id="staging-depth"></a>
## Staging and depth

Space and framing: CSS 3D, layered stages, exploded views, HUD frames.

### `hud-frame-overlay`: HUD frame overlay
- **Lifecycle** tested (preview); support native; seen in 16 reference(s). Record: [`hud-frame-overlay.json`](../catalogue/data/references/hud-frame-overlay.json)
- **What:** A thin, persistent frame (corner marks, tiny labels, a counter, a progress rule) sits above every scene and survives every cut. It turns a sequence of disparate shots into one designed object and gives the viewer a sense of place and progress.
- **Recreate:** Static layer above transitions; label swaps of 0.15-0.3 s; progress linear with time.
- **Timing:** Constant for the whole piece; counter swaps on cuts.
- **Runtime:** Studio.comp.frameHud
- **Precedents:** `ref-05c4222dae` at 1.13 s; `ref-0bf0254a3d` at 1 s; `ref-0fe1abc90a` at 0.37 s; `ref-19cee08f9c` at 0.38 s; `ref-37644838b5` at 10 s; `ref-58ff9f39df` at 1.2 s; `ref-5924215625` at 4.5 s; `ref-70c57c2adf` at 0.37 s
- **Watch out:** Labels below the text floor are unreadable on phones / HUD colour that does not adapt to dark and light scenes disappears

### `css-3d-staging`: CSS 3D staging (tilted cards, carousels, perspective floors)
- **Lifecycle** specified; support native; seen in 13 reference(s). Record: [`css-3d-staging.json`](../catalogue/data/references/css-3d-staging.json)
- **What:** Flat elements are arranged and moved in a CSS perspective space (rotateX/rotateY/translateZ) so they gain depth, scale and occlusion without a 3D renderer.
- **Recreate:** preserve-3d containers, perspective on the stage, rotationY of a ring with cards at translateZ radius; motion blur at speed (see directional-smear).
- **Timing:** Carousel turns of 1-2 s; tilts of 0.6-1 s.
- **Runtime:** not built yet
- **Precedents:** `ref-05c4222dae` at 0.25 s; `ref-0bf0254a3d` at 6 s; `ref-1cbe55c987` at 6 s; `ref-3abcbedd20` at 14.62 s; `ref-5a2816d4db` at 7.14 s; `ref-6f68999b60` at 0.38 s; `ref-736d4ef2c2` at 7.5 s; `ref-85d3a83400` at 3.69 s
- **Watch out:** GPU compositing differences between preview Chromium and HyperFrames / Text on tilted planes below the readability floor

### `rendered-3d-objects`: Rendered 3D objects and scenes
- **Lifecycle** prototyped; support additional-dependencies; seen in 12 reference(s). Record: [`rendered-3d-objects.json`](../catalogue/data/references/rendered-3d-objects.json)
- **What:** Lit, shaded 3D geometry (materials, reflections, soft shadows, camera moves through space) gives products and systems physical presence that flat vector work cannot.
- **Recreate:** Perspective camera paths, physically based or matcap materials, per-frame lighting; point clouds as projected 3D samples.
- **Timing:** Camera moves of 2-6 s; object turns of 1-3 s.
- **Runtime:** not built yet
- **Precedents:** `ref-05c4222dae` at 7.91 s; `ref-0a270a1575` at 0.38 s; `ref-0bf0254a3d` at 8.5 s; `ref-19cee08f9c` at 2.62 s; `ref-1cbe55c987` at 3 s; `ref-37644838b5` at 5 s; `ref-57fd2ce3b4` at 8.08 s; `ref-70c57c2adf` at 6.35 s
- **Watch out:** Real-time WebGL in headless capture may stall or exceed the 1.5 GB render budget / Non-deterministic render loops break frame-accurate seeking

### `layered-silhouette-stage`: Layered silhouette stage with palette clock
- **Lifecycle** tested (preview); support native; seen in 4 reference(s). Record: [`layered-silhouette-stage.json`](../catalogue/data/references/layered-silhouette-stage.json)
- **What:** Flat silhouette layers at different depths form a paper-theatre stage; a slow camera move gives parallax, and the palette (sky gradient, lights coming on) marks the passage of time, so time is told by colour rather than by text.
- **Recreate:** Depth-factored camera transforms; tweened CSS colour variables over several seconds; staggered light-ups; arc motion from two axes with different eases.
- **Timing:** Palette shifts over 4-10 s; lights stagger 0.2-0.4 s; ref-910d9fc567 runs 57 s without a hard cut.
- **Runtime:** Studio.space.camera, Studio.draw.particles
- **Precedents:** `ref-1e22836116` at 5.61 s; `ref-5924215625` at 5.5 s; `ref-910d9fc567` at 10 s; `ref-a943607659` at 27.22 s
- **Watch out:** Too many layers with detailed silhouettes slow the stage and clutter / Colour shift without a narrative reason

### `isometric-exploded-view`: Isometric exploded view (2.5D)
- **Lifecycle** specified; support approximation; seen in 1 reference(s). Record: [`isometric-exploded-view.json`](../catalogue/data/references/isometric-exploded-view.json)
- **What:** An object's layers slide apart along a vertical axis with leader-line labels, turning an opaque device into a readable stack; then collapse back together.
- **Recreate:** Per-layer translateY with stagger from the top; leader lines with stroke-draw; optional slight camera tilt.
- **Timing:** Separation about 0.8-1.2 s, labels 0.3 s each.
- **Runtime:** not built yet
- **Precedents:** `ref-37644838b5` at 44 s
- **Watch out:** Isometric projection drawn inconsistently between layers / Too many layers for portrait

### `rim-light-sweep-reveal`: Rim-light sweep reveal
- **Lifecycle** specified; support approximation; seen in 1 reference(s). Record: [`rim-light-sweep-reveal.json`](../catalogue/data/references/rim-light-sweep-reveal.json)
- **What:** In darkness, a thin highlight travels along the edges of a large shape, so its silhouette is read from the rim light before the shape is ever fully lit. The viewer assembles the shape from glints, which builds suspense.
- **Recreate:** Dark shape a few percent brighter than the background; a narrow gradient (accent to transparent) masked to the shape's edge stroke travels along it at about 300-500 px/s with a soft glow, 2.0-2.6 s for a frame-filling shape (ref-99713f6e72 0-2.6 s, 10 fps strip); a second glint starts on another edge at about 1.4 s; the full shape fades up only after the sweep (2.4-2.7 s).
- **Timing:** Sweep 2-2.6 s; reveal fade about 0.3 s.
- **Runtime:** not built yet
- **Precedents:** `ref-99713f6e72` at 0.5 s
- **Watch out:** On a light canvas it disappears; dark sections only / A fast sweep loses the suspense

### `product-hero-turntable`: Product hero turntable
- **Lifecycle** specified; support -; seen in 0 reference(s). Record: [`product-hero-turntable.json`](../catalogue/data/references/product-hero-turntable.json)
- **What:** Needs real 3D or footage: use hybrid-video-underlay with supplied product footage, or three.js after it leaves 'proposed'.
- **Timing:** Slow 4-8 s rotation
- **Runtime:** not built yet

<a id="explanation-device"></a>
## Explanation devices

Diagrams, UI demos, trackers, callouts, fills.

### `ui-demo-micro-interactions`: Product UI micro-interactions (generic)
- **Lifecycle** tested (preview); support native; seen in 25 reference(s). Record: [`ui-demo-micro-interactions.json`](../catalogue/data/references/ui-demo-micro-interactions.json)
- **What:** Simplified, generic UI fragments perform one interaction each (type, click, toggle, notify, compress) in close-up, so a product's value is shown as action rather than as a screenshot tour.
- **Recreate:** Typewriter, FLIP width morphs, cursor paths with ease-in-out and a press scale, staggered card entrances, counters.
- **Timing:** One interaction per 0.8-2 s.
- **Runtime:** Studio.comp.ui
- **Precedents:** `ref-05acc490f6` at 33.59 s; `ref-0b13aa7f02` at 12.26 s; `ref-0b2552b64e` at 0.38 s; `ref-1cbe55c987` at 0.5 s; `ref-2a6c654bfe` at 5.69 s; `ref-31ce9d6332` at 24.86 s; `ref-32fea7dae3` at 12.98 s; `ref-3abcbedd20` at 11.62 s
- **Watch out:** Recreating a real product's proprietary UI (forbidden without authorisation) / Too much UI detail to read at 720p or on phones

### `diagram-connectors`: Drawn diagram connectors
- **Lifecycle** tested (preview); support native; seen in 8 reference(s). Record: [`diagram-connectors.json`](../catalogue/data/references/diagram-connectors.json)
- **What:** Relationships are introduced by drawing the line between two elements at the moment the narration or caption names the relationship, so structure is built in front of the viewer instead of shown complete.
- **Recreate:** Facing-edge anchors, cubic curve with symmetric handles, ease-in-out draw of 0.35-1.2 s, arrowhead after the shaft.
- **Timing:** 0.35-1.2 s per connector, one at a time.
- **Runtime:** Studio.draw.connect, Studio.draw.layer
- **Precedents:** `ref-05acc490f6` at 5.66 s; `ref-0b13aa7f02` at 21.17 s; `ref-216f4eaeef` at 4.98 s; `ref-37644838b5` at 44 s; `ref-5a2816d4db` at 14.65 s; `ref-6f68999b60` at 19.94 s; `ref-95c96d5c47` at 14.99 s; `ref-b8cf9a12b0` at 10.14 s
- **Watch out:** Connectors drawn before both ends exist / Elements moving after the connector is drawn (measure at the cue; keep them still)

### `annotation-callouts`: Hand-drawn annotation callouts
- **Lifecycle** tested (preview); support native; seen in 5 reference(s). Record: [`annotation-callouts.json`](../catalogue/data/references/annotation-callouts.json)
- **What:** A note in a handwritten or italic voice, a loop around the subject and a curved arrow between them name the thing the viewer should notice, like a teacher marking up a page. The hand-made marks contrast with clean geometry, so they read as commentary rather than content.
- **Recreate:** Stroke-draw of an overshooting hand loop (0.5 s), arrow shaft (0.35 s) and head (0.15 s); note pop with back ease; positions from the target's rendered box.
- **Timing:** About 0.6-0.9 s to complete; held 1.5-4 s.
- **Runtime:** Studio.comp.callout, Studio.draw.loop
- **Precedents:** `ref-216f4eaeef` at 7 s; `ref-2860712d4e` at 1.81 s; `ref-392ee4d0f9` at 0.6 s; `ref-49459ad8c1` at 5.5 s; `ref-95c96d5c47` at 12.15 s
- **Watch out:** Notes over moving targets drift off (measure once; keep the target still) / More than two notes at once clutters

### `step-progress-tracker`: Step progress tracker
- **Lifecycle** tested (preview); support native; seen in 5 reference(s). Record: [`step-progress-tracker.json`](../catalogue/data/references/step-progress-tracker.json)
- **What:** A row of numbered nodes on a rule fills as the process advances, giving a how-to or explainer a constant answer to 'where are we and how much is left'.
- **Recreate:** Colour and scale tweens per node (chained from the previous state), rule scaleX to index / (n - 1).
- **Timing:** 0.5-0.8 s per advance, aligned with the step's first action.
- **Runtime:** Studio.comp.stepper
- **Precedents:** `ref-37644838b5` at 10 s; `ref-95c96d5c47` at 18.75 s; `ref-a339360a56` at 4.15 s; `ref-a943607659` at 27.22 s; `ref-c3bc609841` at 6 s
- **Watch out:** More than 7 steps crowd portrait / Advancing the tracker before the step is shown

### `bar-chart-race`: Bar chart race
- **Lifecycle** tested (preview); support native; seen in 2 reference(s). Record: [`bar-chart-race.json`](../catalogue/data/references/bar-chart-race.json)
- **What:** Horizontal bars grow and swap places by value as a date label advances, so a ranking over time is felt as a race; the change of leader is the story.
- **Recreate:** Per data step: bar width tween to value / max (linear, 0.08-0.3 s per step); rank by value and tween each bar's y to rank x row height (power2.inOut, same duration); value labels count with the bar; a large faint date label in a corner advances each step.
- **Timing:** About 30 steps in 2.5 s in the reference (Sep 1 to Sep 30, 11.4-13.7 s).
- **Runtime:** Studio.comp.barRace
- **Precedents:** `ref-a943607659` at 10.81 s; `ref-d386e5f0ae` at 11.39 s
- **Watch out:** Too many fast steps become noise: keep rank swaps readable / Bars without labels are unreadable at 720p

### `placeholder-image-resolve`: Placeholder image resolve
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`placeholder-image-resolve.json`](../catalogue/data/references/placeholder-image-resolve.json)
- **What:** A grey placeholder box appears where an image will be, a faint sheen passes over it, then scattered patches of the final image show through and spread until the image resolves. Generation or loading is shown as a process, so the result feels earned.
- **Recreate:** Placeholder: a rounded rectangle in the canvas tone with a diagonal sheen sweeping across over about 1.0 s (ref-ad023ce9dc 10.88-12.0 s). Resolve: mask the final image with a seeded set of blobs whose radii grow from 0 to full cover over 1.0-1.2 s (power1.in), starting at 12.0 s and complete at about 13.1 s. Blob centres from a seeded PRNG so every render matches.
- **Timing:** Sheen about 1 s; resolve 1.0-1.2 s; about 2.2 s in all.
- **Runtime:** not built yet
- **Precedents:** `ref-ad023ce9dc` at 10.88 s; `ref-b8cf9a12b0` at 8.01 s
- **Watch out:** Unseeded random patches break deterministic renders / Too fast and it reads as a glitch, not a process

### `radar-sweep-reveal`: Radar sweep reveal
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`radar-sweep-reveal.json`](../catalogue/data/references/radar-sweep-reveal.json)
- **What:** A wedge rotates over concentric rings and each labelled point appears as the wedge passes it, so discovery is shown as scanning: the viewer watches the system find things instead of a list appearing.
- **Recreate:** Wedge as a conic gradient or SVG path rotating 0 -> 360 deg linearly over 2-4 s; each point's reveal time = its angle / 360 x period; point pop (scale 0 -> 1, back.out) plus a label slide; rings static; optional pulse ring on each hit; point angles from a seeded PRNG.
- **Timing:** One sweep in 2-4 s; points about 0.2-0.4 s apart (reference 12-17.6 s).
- **Runtime:** Studio.space.pop
- **Precedents:** `ref-85d3a83400` at 12.38 s; `ref-9459c8097f` at 4.11 s
- **Watch out:** Points that appear before the wedge reaches them / Too many labels to read at 720p

### `equation-term-build`: Equation built term by term beside its figure
- **Lifecycle** tested (preview); support native; seen in 1 reference(s). Record: [`equation-term-build.json`](../catalogue/data/references/equation-term-build.json)
- **What:** An equation appears one term at a time next to the figure it describes, each term arriving when the figure shows it, and the closing term is ringed. The equation is read against the geometry instead of before it, the core move of a proof-led explainer.
- **Recreate:** Lay out the full equation first, then reveal term spans: opacity 0 -> 1 with a 4-8 px rise over 0.2-0.3 s at the moment the figure shows that part (a radius turning through pi, a point landing on -1); the final term gets a stroke-drawn ring (0.3-0.5 s) in an accent; the figure keeps moving under it.
- **Timing:** About 0.5-0.8 s between terms; whole statement in 1.5-2.5 s (reference 16.7-18.1 s).
- **Runtime:** Studio.comp.equation
- **Precedents:** `ref-0fe1abc90a` at 16.67 s
- **Watch out:** Terms arriving before the figure shows them read as a caption, not a proof / Typesetting that reflows as terms are added: lay out the whole equation, then reveal spans

### `index-card-bookend`: Index card bookend (the film opens and closes on its contents)
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`index-card-bookend.json`](../catalogue/data/references/index-card-bookend.json)
- **What:** The film opens on a card that lists its chapters, plays each chapter as a short self-contained piece, and returns to the same card at the end, now completed with an icon per chapter. The card states the promise; the return proves it was kept.
- **Recreate:** Card on a contrasting surround with corner marks; enters with a perspective flip (0.10-0.45 s); four chapter rows; holds about 1.5 s; the first chapter starts from a detail of the card (its accent full stop grows at 1.82 s, cut at 1.87 s). End: cut back to the card (13.13 s); the title's letters reassemble over 0.35 s (13.15-13.48 s); each row now carries an icon; hold about 1.5 s.
- **Timing:** Card about 1.9 s at each end; chapters of 2.7-4.6 s.
- **Runtime:** Studio.comp.heroStage
- **Precedents:** `ref-05c4222dae` at 0.25 s
- **Watch out:** More than about five rows will not read in 1.5 s / Returning to an unchanged card wastes the bookend

### `linked-trace-projection`: Linked trace projection (one motion, two representations)
- **Lifecycle** tested (preview); support native; seen in 1 reference(s). Record: [`linked-trace-projection.json`](../catalogue/data/references/linked-trace-projection.json)
- **What:** A point moves on one figure (a circle, a rotating arm) while a guide line carries one of its coordinates across to an adjacent axis, where it draws a curve over time. The viewer sees that the circle and the wave are one motion, which a static diagram cannot show.
- **Recreate:** Point angle = 2*pi*t/T with linear ease; guide line from the point to x = x0 + k*t on the graph at the same height; the curve is a path drawn by stroke-dashoffset (or a growing polyline) up to the guide line's end; a radius line and an angle arc on the circle; T = 1.5-3 s per cycle; both driven from the same timeline variable.
- **Timing:** One cycle in 1.5-3 s; 1-2 cycles per explanation beat (reference 2-4 s).
- **Runtime:** Studio.comp.tracePair
- **Precedents:** `ref-0fe1abc90a` at 2.59 s
- **Watch out:** Point and curve drifting apart: compute both from one time variable / Several guide lines at once

### `live-simulation-trace`: Live simulation trace (gauge, log and chart on one clock)
- **Lifecycle** tested (preview); support native; seen in 1 reference(s). Record: [`live-simulation-trace.json`](../catalogue/data/references/live-simulation-trace.json)
- **What:** A system is explained by running it. One deterministic event script drives a state gauge (a big count and a bar stack), a scrolling event log and a time-series chart, all advanced by one clock, so the three views always agree. A one-line caption at the top names the current regime and swaps in place when the regime changes; there are no transitions.
- **Recreate:** One timeline clock; an event list [{t, kind}] from a seeded script. Each event updates the gauge (count and bar stack; the count turns red at 0), appends a log row (time, id, outcome in green or red, remainder) and adds a tick on the chart axis while the chart line steps to the new value. Measured: a burst drains 9 -> 0 between 2.50 and 3.36 s (one event per 0.07-0.1 s); single refills flicker 0 -> 1 -> 0 at the refill period (4.31-5.41 s); recovery 2 -> 10 over about 4.5 s. Regime caption: one line of 5-9 words swapped in place 4 times in 18 s; the closing rule in an accent colour; hold the final state 3-6 s.
- **Timing:** Regimes of 0.8-5.9 s; the burst is the shortest, the closing rule the longest.
- **Runtime:** Studio.comp.simulation, Studio.comp.simulationScript
- **Precedents:** `ref-b34f751c59` at 2.5 s
- **Watch out:** Views that disagree by one event destroy trust: drive all three from one event list / More than about 10 events per second become unreadable: aggregate or slow the clock

### `slider-driven-counter`: Slider-driven counter (cause and effect)
- **Lifecycle** tested (preview); support native; seen in 1 reference(s). Record: [`slider-driven-counter.json`](../catalogue/data/references/slider-driven-counter.json)
- **What:** An input control is dragged and the figure it drives rolls with it in real time, so the effect of one parameter is shown in one move. The viewer sees the rule (more of X, more of Y) without a chart.
- **Recreate:** The handle travels with an ease-in-out over about 1.7 s; the input readout steps (50 -> 500) and the output rolls ($500 -> $5,000) with it, settling by a few units ($4,997 -> $4,999 -> $5,000); small accents on some steps; a caveat sticker lands after the stop.
- **Timing:** Drag 9.3-11.0 s; caveat 0.2 s after the stop (11.18 s).
- **Runtime:** Studio.comp.slider
- **Precedents:** `ref-9ed4034cad` at 9.36 s
- **Watch out:** Output not rounded to the readout's precision looks fake / Too fast to read the end value

### `split-screen-parallel`: Split-screen parallel demo (both panes on the same beat)
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`split-screen-parallel.json`](../catalogue/data/references/split-screen-parallel.json)
- **What:** Two subjects (products, methods, before and after) run the same sequence of steps in two equal panes. Each step starts on the same frame in both panes and every cut happens in both at once, so the viewer compares by glancing left and right at the same moment, without narration.
- **Recreate:** Two equal panes (50% of the width each, a 1-2 px gutter) under a thin label bar naming each side; one shared list of steps; each step's entrance starts on the same frame in both panes (4 cuts checked at 2-frame steps: 3.38, 5.31, 8.17, 10.04 s); steps of 1.9-3.2 s; close on both names side by side, blurred large and scaling to sharp in 0.17 s (10.05-10.22 s).
- **Timing:** Steps of 1.9-3.2 s; five steps in a 12 s sting.
- **Runtime:** Studio.comp.splitStage
- **Precedents:** `ref-a1c9ef89a3` at 0.38 s
- **Watch out:** Unequal step timing breaks the comparison / Each pane is near-square at 16:9, so text halves in size; in portrait stack the panes top and bottom

### `vessel-fill-pour`: Vessel fill and pour
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`vessel-fill-pour.json`](../catalogue/data/references/vessel-fill-pour.json)
- **What:** A container fills as a pour stream connects bottle and liquid; the level rises against measurement ticks and the colour mixes with each ingredient, so quantities become visible.
- **Recreate:** Liquid as a wave path clipped by the vessel interior; level tween with ease-out; fill colour tween per ingredient; stream as a stroked path drawn then erased.
- **Timing:** About 1.5-2.5 s per pour.
- **Runtime:** not built yet
- **Precedents:** `ref-c3bc609841` at 8 s
- **Watch out:** Level overshooting the vessel / Stream not touching the surface

### `recipe-flatlay-steps`: Overhead recipe step sequence
- **Lifecycle** implemented; support -; seen in 0 reference(s). Record: [`recipe-flatlay-steps.json`](../catalogue/data/references/recipe-flatlay-steps.json)
- **What:** Ingredient list assembles, numbered steps replace each other around a constant vessel, final serve shot holds.
- **Timing:** Step holds sized to reading time
- **Runtime:** item-list, step-header, object-assembly, line-art-reveal

<a id="style-texture"></a>
## Style and texture systems

Whole-look systems: collage, stickers, cut paper, line boil.

### `cut-paper-title-sequence`: Mid-century cut-paper title sequence
- **Lifecycle** implemented; support -; seen in 2 reference(s). Record: [`cut-paper-title-sequence.json`](../catalogue/data/references/cut-paper-title-sequence.json)
- **What:** Flat geometric cut-outs pop and slide on beat; a shape grows to wipe the frame; type appears inside shapes.
- **Timing:** Cut and pop on beats; 2-4 beats per card
- **Runtime:** paper-pop, shape-cover-transition, beat-pulse
- **Precedents:** `ref-0bf0254a3d` at 2.85 s; `ref-736d4ef2c2` at 22 s

### `archival-mono-collage`: Monochrome archive collage with one accent
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`archival-mono-collage.json`](../catalogue/data/references/archival-mono-collage.json)
- **What:** Public-domain monochrome imagery on white, overlaid with analytic line drawings and one accent mark, gives a thoughtful, museum-like tone; fast cuts between images on the beat keep it lively.
- **Recreate:** Hard cuts about every 0.75 s; line overlays drawn with a pen-led stroke; images cut out with clean edges.
- **Timing:** Image cuts about 0.5-1 s; type holds about 1-2 s.
- **Runtime:** not built yet
- **Precedents:** `ref-c93524ef20` at 3 s
- **Watch out:** Reproducing a specific brand's combination of archive imagery, serif and accent colour reproduces its identity / Using images without public-domain or licence verification

### `pencil-sketch-paper-style`: Pencil sketch on paper with one coloured protagonist
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`pencil-sketch-paper-style.json`](../catalogue/data/references/pencil-sketch-paper-style.json)
- **What:** Pencil line drawings with visible hatching on warm paper, hand-written notes with arrows and one saturated object as the protagonist. The sketchbook feel makes a business subject feel considered and human, and the single colour leads the eye. Not the same as cut-paper-title-sequence (flat cut shapes popping on beats).
- **Recreate:** Off-white paper texture with a soft vignette; line art in 1-1.5 px graphite grey with hatching; annotations in a hand-written script with curved arrows; one accent colour reserved for the protagonist (teal in ref-2860712d4e); documents as slightly rotated paper cards with soft shadows that settle in 0.3-0.5 s; a negative variant (dark chalkboard, light lines) for the payoff section (5.0-11.4 s).
- **Timing:** A style system; card entrances 0.3-0.5 s.
- **Runtime:** not built yet
- **Precedents:** `ref-2860712d4e` at 1.12 s
- **Watch out:** Tracing a reference's drawings instead of drawing original art / More than one saturated colour breaks the single-protagonist read

### `sticker-brutalist-style`: Sticker neo-brutalist explainer style
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`sticker-brutalist-style.json`](../catalogue/data/references/sticker-brutalist-style.json)
- **What:** Cards and labels drawn like stickers (heavy outline, flat pastel fill, hard offset shadow) with monospace labels and hatched 'disabled' states make dense technical diagrams friendly and very legible.
- **Recreate:** Style tokens (outline width, shadow offset, pastel set) plus pop and stamp entrances.
- **Timing:** Pop entrances 0.3-0.5 s; state stamps 0.4 s.
- **Runtime:** not built yet
- **Precedents:** `ref-95c96d5c47` at 3.42 s
- **Watch out:** Too many colours break the system / Outlines too thin at 720p portrait

### `hand-drawn-line-boil`: Hand-drawn line boil
- **Lifecycle** specified; support -; seen in 0 reference(s). Record: [`hand-drawn-line-boil.json`](../catalogue/data/references/hand-drawn-line-boil.json)
- **What:** Swap between 3 seeded variants of each outline at 8-12 fps.
- **Timing:** 8-12 fps stepped
- **Runtime:** not built yet

<a id="sound-design"></a>
## Sound design against the picture

Where effects, music and silence land relative to what the viewer sees.

### `beat-grid-element-arrivals`: Beat-grid element arrivals (sound marks information, not edits)
- **Lifecycle** specified; support native; seen in 26 reference(s). Record: [`beat-grid-element-arrivals.json`](../catalogue/data/references/beat-grid-element-arrivals.json)
- **What:** Pick a tempo, put every element entrance on the beat grid, and give each arrival a short soft accent (pop, tick, knock) on the frame where it lands. Scene changes sit on other beats and are carried by picture (or a swell), not by a hit. The sound tracks the information the viewer should notice.
- **Recreate:** beat = 60 / bpm (120 bpm -> 0.5 s). Arrival (end of the ease-out, or the overshoot peak) snaps to the grid with Studio.rhythm.snap; the entrance starts 0.2-0.4 s earlier. Accent SFX: onset on the arrival frame (earshot kit roles pop or knock, onset aligned), 3-10 dB over the bed. Cuts and section changes on whole bars without a hit; an impact or swell only at the 2-3 biggest turns. In the references the accents sit at x.55-x.60 s on a 1.00 s grid while hard cuts sit on whole seconds.
- **Timing:** 120 bpm: arrivals every 0.5 or 1.0 s; sections every 4-8 s; accents 25-55 per minute in the references.
- **Runtime:** Studio.rhythm.grid, Studio.rhythm.snap
- **Precedents:** `ref-04d81a6a3e` at 4.44 s; `ref-05c4222dae` at 2.39 s; `ref-0b13aa7f02` at 4.55 s; `ref-0b2552b64e` at 6.27 s; `ref-0bf0254a3d` at 0.53 s; `ref-1cbe55c987` at 2.6 s; `ref-2860712d4e` at 7.06 s; `ref-32fea7dae3` at 4.55 s
- **Watch out:** With narration, the voice is the grid: snap arrivals to the spoken noun (studio.py words), not to the music, and keep accents quieter than the voice / An accent on every cut as well as every arrival makes everything equally loud

### `action-synced-foley`: Sound on the action, not on the edit
- **Lifecycle** specified; support native; seen in 11 reference(s). Record: [`action-synced-foley.json`](../catalogue/data/references/action-synced-foley.json)
- **What:** Short sounds follow what a character or element does (each step, keystroke or click on its own contact frame) while cuts carry none. In a wordless film they are the only accents, so the sound tells you where to look.
- **Recreate:** Accent onset on the contact frame of each action. ref-1e22836116: accents every 0.42 s on the stair climb (17.86, 18.27, 18.69, 19.11 s) and 14.05-15.39 s across the room; 0 of 6 cuts carry an accent (chance 6%); 18.4 accents per minute. ref-3abcbedd20: accents on typed characters at 0.07, 0.39, 0.77 and 2.04 s. Build: take contact frames from the animation (real-sfx from_hyperframes.py) and place earshot kit sounds (knock, tick) on them. Also (batch-4): ref-7a185cb08d: accents at the wordmark collapsing into its full stop (0.86 s), the dot stretching into a pill (1.60-1.74 s), the button press (2.00-2.11 s), the circle becoming a tile (3.11 s) and the tile splitting into a grid (3.85-4.11 s); spacing 0.11-1.0 s, irregular; 2 of 10 boundaries carry an accent within 100 ms (0.20, chance 0.19).
- **Timing:** One sound per action; spacing follows the walk cycle (0.4-0.5 s) or typing speed.
- **Runtime:** not built yet
- **Precedents:** `ref-04d81a6a3e` at 16.76 s; `ref-0a270a1575` at 5.69 s; `ref-1e22836116` at 14.05 s; `ref-2860712d4e` at 0.56 s; `ref-392ee4d0f9` at 0.51 s; `ref-3abcbedd20` at 0.07 s; `ref-5924215625` at 0.3 s; `ref-7a185cb08d` at 0.86 s
- **Watch out:** Every action at the same level becomes noise / Sounds more than about 40 ms off the contact frame read as late

### `pre-hit-dropout`: Pre-hit dropout (silence before the reveal)
- **Lifecycle** specified; support native; seen in 7 reference(s). Record: [`pre-hit-dropout.json`](../catalogue/data/references/pre-hit-dropout.json)
- **What:** Just before the single most important reveal, take the music (and effects) out for 0.3-0.6 s, hold the picture in near-stillness, then land the reveal and its hit on the returning sound. Contrast, not loudness, makes it the biggest moment.
- **Recreate:** Mix: bed gain -inf (or -12 dB) from hit - 0.5 s to hit, restore on the hit with a 10-30 ms fade; the hit's onset on the reveal frame. Picture: the approach eases in (slow) during the gap; no new elements enter in the gap.
- **Timing:** Gap 0.3-0.6 s; once (at most twice) per film.
- **Runtime:** not built yet
- **Precedents:** `ref-04d81a6a3e` at 13.89 s; `ref-2a6c654bfe` at 1.8 s; `ref-49459ad8c1` at 5.13 s; `ref-99713f6e72` at 12 s; `ref-b8cf9a12b0` at 1.44 s; `ref-fb375e07e2` at 1.07 s; `ref-fe7fb0ded2` at 5.5 s
- **Watch out:** Used more than once or twice it stops being a surprise / Never drop out under a spoken word: in narrated films place it in a narration pause

### `end-card-in-the-tail`: End card built in the music's decay
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`end-card-in-the-tail.json`](../catalogue/data/references/end-card-in-the-tail.json)
- **What:** The music's last event comes before the end card, and the logo, line and call to action build while that sound decays. The close lands calm instead of shouted, and small sounds (keystrokes, a button) are heard clearly.
- **Recreate:** Last music onset 0.7-1.7 s before the card starts; the level decays 15-45 dB over the card (12.12 s last onset, -18 dB at 12.9 s, -26 at 13.2 s, -35 at 14.3 s, -65 at 15.0 s; or a hit at 14.42 s decaying -13 -> -20 dB over 14.4-19.8 s and fading by 20.7 s). Card elements arrive 0.2 s apart (12.84, 13.04, 13.24, 13.44 s) or type in at 0.14-0.17 s per letter with a keystroke each (16.1-18.4 s).
- **Timing:** Tail of 2.5-6 s.
- **Runtime:** Studio.comp.endCard, Studio.type.typewriter
- **Precedents:** `ref-04d81a6a3e` at 14.42 s; `ref-9459c8097f` at 12.12 s
- **Watch out:** Dead silence with no tail reads as an export error / A tail much longer than the card loses the viewer

### `quiet-after-overload`: Silence after the overload
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`quiet-after-overload.json`](../catalogue/data/references/quiet-after-overload.json)
- **What:** The densest, loudest stretch of the film ends on a hard cut to one small line, and the music stops (or thins to almost nothing) for several seconds while the picture slows and the palette softens. The relief is felt and makes the next words intimate. Unlike a pre-hit dropout it leads into quiet, not into a hit.
- **Recreate:** Build: word cards every 0.2-0.3 s accelerating to colour swaps every 0.1 s (ref-58ff9f39df 108.4-115.8 s). Stop: hard cut to one small monospace line at 115.9 s; music out 117.93-121.63 s (3.7 s); during it the empty background lifts from black to cream over 0.6 s (120.97-121.6 s); music back under the new section. Second use before the sign-off: 140.29-145.57 s (5.3 s). The film's loudness range is 12.5 LU, against 1.1-8.2 LU in this batch's music-only promos.
- **Timing:** Silence 3-5 s; at most twice per film; right after the loudest stretch.
- **Runtime:** Studio.space.drift
- **Precedents:** `ref-58ff9f39df` at 115.9 s; `ref-a943607659` at 20.2 s
- **Watch out:** Silence over a frozen frame reads as a broken render: keep drift or a slow background change / Too early, before the viewer cares

### `beat-drop-product-reveal`: Beat drop on the product reveal
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`beat-drop-product-reveal.json`](../catalogue/data/references/beat-drop-product-reveal.json)
- **What:** The problem is told over a sparse, quiet intro; the full beat enters, louder and denser, at the moment the product's main interface fills the frame. The arrangement marks the turn from problem to solution without a cut or an added sound effect.
- **Recreate:** Intro bed about 7 dB below the body (median -24.6 dB against -17.3 dB) with onsets 0.2-1.0 s apart; at the turn the level steps up 7.3 dB within about 0.2 s (13.33 -> 13.51 s) and onsets go to every 0.11-0.23 s; the picture grows the main window to fill the frame across the step (11.0-13.97 s).
- **Timing:** Intro about 13 s of a 47.6 s film (28%); one step, no return.
- **Runtime:** not built yet
- **Precedents:** `ref-0b2552b64e` at 13.42 s
- **Watch out:** A step on a non-event reads as a mix error / Under narration the step must be ducked so the voice stays on top

### `sonified-motion`: Sonified motion (the motion plays the score)
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`sonified-motion.json`](../catalogue/data/references/sonified-motion.json)
- **What:** Every physical event in the animation (a bounce, a collision, an arrival) triggers the next note of a pre-written melody, with bigger events getting bigger sounds. There is no separate music bed: the motion writes the soundtrack.
- **Recreate:** Run a deterministic (seeded) simulation and log event frames with a kind (contact, break, finish). Map contact k to note k of a melody (pentatonic avoids clashes; pitch may step up with progress). Render notes with earshot sfx mallet or pluck (--pitch), place onsets on the event frames; a heavier sound for breaks; a release (swell plus hit) for the finish. Visual hierarchy matches: palette steps per stage, particles on breaks.
- **Timing:** Event-driven; in the reference 64 onsets in 32 s, strongest 13-14 on ring breaks.
- **Runtime:** not built yet
- **Precedents:** `ref-a3031376e7` at 0.21 s
- **Watch out:** A non-deterministic simulation gives different notes per render / Notes too dense (> 8/s) turn into noise; thin the events or only sonify one kind

<a id="narration-captions"></a>
## Narration and captions

Voice pace and the on-screen words that carry speech.

### `step-caption-pill`: Step caption pill for a wordless demo
- **Lifecycle** specified; support native; seen in 2 reference(s). Record: [`step-caption-pill.json`](../catalogue/data/references/step-caption-pill.json)
- **What:** In a product demo without a voice, a dark rounded pill at bottom centre carries one short line naming the current step and changes only when the step changes. It narrates without competing with the interface.
- **Recreate:** Pill: near-black fill, full corner radius, 12-16 px white sentence-case text, one line of 4-8 words, about 90% down the frame, centred. It enters with a 0.2-0.3 s fade and a 4-6 px rise, holds 3.5-5 s, and swaps on the step's first action (ref-ad023ce9dc cues at about 4.9, 11.6, 15.4, 20.6 and 25.9 s). No word highlight.
- **Timing:** One cue per step; 3.5-5 s each; 5 cues in 30 s in the reference.
- **Runtime:** Studio.comp.captions
- **Precedents:** `ref-ad023ce9dc` at 4.88 s; `ref-debf607232` at 1.86 s
- **Watch out:** A caption that repeats the UI text adds nothing / Cues that change faster than about 2.5 s cannot be read alongside the UI

### `word-highlight-caption`: Word-highlight caption anchored to the subject
- **Lifecycle** tested (preview); support native; seen in 2 reference(s). Record: [`word-highlight-caption.json`](../catalogue/data/references/word-highlight-caption.json)
- **What:** Captions show a short phrase (one or two lines) and colour the word being spoken. Placed directly under the thing being explained rather than in a fixed lower third, they keep the eye on the subject while reading.
- **Recreate:** Word-timed cues (studio.py captions --timing words) grouped into phrases of 3-7 words; highlight the current word (colour or weight) at its measured start; lane = below the subject's box (Studio.boxAt(subject).bottom + gap) instead of the frame's lower third, clamped inside the safe area; phrase swap on a 0.1-0.15 s fade.
- **Timing:** Highlight per word at its spoken start; phrases 1-3 s.
- **Runtime:** Studio.comp.captions
- **Precedents:** `ref-31ce9d6332` at 30.49 s; `ref-a339360a56` at 16.23 s
- **Watch out:** Subject-anchored captions that jump with every scene's layout; keep the lane stable inside a scene / Highlight lagging the voice by more than about 100 ms reads as broken; use measured word times

### `caption-voice-strip`: Typed caption as the voice of a silent film
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`caption-voice-strip.json`](../catalogue/data/references/caption-voice-strip.json)
- **What:** In a film without sound, a caption strip in the lower third is the narrator: each cue types in word by word at about twice speaking speed, then holds complete so the viewer can finish reading, and cues change only when the picture is redrawn. Reading replaces listening, so the film works muted.
- **Recreate:** Plate: a paper-like strip across about 83% of the width at 82-96% of the height over a dark bar; centred text, 1-3 lines. Reveal word by word at 6.3-8.3 words/s (median 7.8, about 0.13 s per word, linear, no highlight). Hold complete 1.4-4.9 s (median 3.5 s). The new cue starts on the frame of the scene redraw, at a whole second. 8-32 words per cue (median 17.5); 192 words in 58 s (199 words a minute on screen). Measured by counting word blobs in the caption band at the source 12 fps (calibrated: 19 of 19 words on one frame).
- **Timing:** Cue = scene, 3-9 s; reveal 1.0-4.9 s; hold at least 1.4 s, median 3.5 s.
- **Runtime:** Studio.comp.captions, Studio.type.typewriter
- **Precedents:** `ref-216f4eaeef` at 3 s
- **Watch out:** Holds under about 1.5 s for 20 or more words: the reader cannot finish / A type-on slower than reading speed makes the viewer wait

### `lyric-word-onset-sync`: Lyric words on the sung onset, a new lane per phrase
- **Lifecycle** specified; support native; seen in 1 reference(s). Record: [`lyric-word-onset-sync.json`](../catalogue/data/references/lyric-word-onset-sync.json)
- **What:** Words of a sung or spoken line appear one at a time, each starting to fade in on its own vocal onset, so reading and hearing coincide. Each phrase gets its own placement anchored to the picture (a horizon, an arc around the subject, a corner, the centre), and the scene change follows the phrase's first word instead of preceding it. Emphasis comes from size, weight and letter-spacing, not a colour sweep.
- **Recreate:** Per word: opacity 0 -> 1 (optional blur 4 px -> 0) over 2-6 frames (0.07-0.2 s); start = vocal onset minus 0-0.12 s (measured median about 15 ms early; never more than about 40 ms late). Line exit: a 0.1-0.3 s dissolve that starts on the next phrase's onset, then 0.07-0.15 s of empty frame; or let the next phrase's first word fade in over the outgoing picture and cut the background about 0.2 s later. Phrase-final word 1.5-3x larger. A held word starts at about 0.6 em letter-spacing and tightens to normal over the held note (about 1 s). Optional accent marks on strong onsets: a ring ripple or a light-line flash of 2-4 frames.
- **Timing:** Lines of 1-8 words (median 3) held 0.6-4.6 s (median about 2.3 s); a new lane per phrase (8 placements in 30 s).
- **Runtime:** Studio.comp.captions, Studio.cues.fromWords
- **Precedents:** `ref-e8125c24ca` at 0.07 s
- **Watch out:** A word that shows more than about 40 ms after the voice reads as lagging / A new lane every phrase in an explainer body is restless: keep it for hooks, quotes and lyrics

### `pause-locked-copy-swap`: Copy swaps in the narrator's pauses
- **Lifecycle** tested (preview); support native; seen in 1 reference(s). Record: [`pause-locked-copy-swap.json`](../catalogue/data/references/pause-locked-copy-swap.json)
- **What:** In a narrated film every change of on-screen copy (headline, list line, card) happens inside a pause of the voice, never over a word, and the new copy is readable a beat before the phrase that says it. The viewer reads the line, then hears it confirmed, and nothing changes while they listen.
- **Recreate:** Take phrase times from the measured narration (word times or voice activity). For each copy change pick the pause before the phrase that names the new copy: old copy fades out 0.17-0.20 s, the slot stays empty 0.07-0.10 s, new copy fades in over 0.13-0.15 s, timed so it is first visible 0.2-0.6 s before the phrase starts (list lines about 0.2 s). Keep the demo beside it moving so the pause is not a frozen frame.
- **Timing:** Swap about 0.35 s in all. Observed: 11 of 11 swaps in pauses (chance 0.28); swap starts a median 0.60 s (0.01-0.94) before the phrase; first visible 0.27 and 0.58 s before it (strips); list lines 0.21 s before. This voice's pauses: median 0.50 s, max 1.12 s.
- **Runtime:** Studio.comp.copySlot
- **Precedents:** `ref-31ce9d6332` at 9.23 s
- **Watch out:** A pause shorter than the swap: start it in the previous pause or shorten the fades / Copy that appears after its phrase reads as a lagging caption

## Sound, narration and pace by reference

From `automated.listen` (signal features and local speech recognition; nobody listened). Accents = strongest sound onsets; 'on cuts' = share of picture boundaries with an accent within 100 ms, chance level in brackets.

| reference | s | LUFS | LRA | TP dBTP | accents/min | accents on cuts | narration | words/s speaking |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| `ref-04d81a6a3e` Slow-build logo reveal: facets fly in on the bea | 21 | -14.0 | 4.6 | -1.2 | 62.9 | 0.0 (0.19) | none | - |
| `ref-05acc490f6` Silent blue-and-yellow course launch: stacked co | 40 | - | - | - | - | - | no audio | - |
| `ref-05c4222dae` Type, form, space, time: a designer's index card | 15 | -12.5 | 0.8 | 0.5 | 39.8 | 0.0 (0.12) | none | - |
| `ref-0a270a1575` Portrait 3D letter-tile story: a left-out tile t | 42 | -14.5 | 5.2 | -1.0 | 25.7 | 0.0 (0.08) | none | - |
| `ref-0b13aa7f02` Cream-and-green app launch with sound placed on  | 30 | -14.1 | 3.7 | -1.1 | 30.3 | 0.17 (0.1) | none | - |
| `ref-0b2552b64e` Light-canvas voice-agent launch (music only): tw | 48 | -15.9 | 5.6 | -4.9 | 61.8 | - | sparse | - |
| `ref-0bf0254a3d` Motion reel: Bauhaus grid, chrome 3D and one-wor | 15 | -23.9 | 3.9 | -7.5 | 100.0 | 0.5 (0.28) | none | - |
| `ref-0fe1abc90a` Mathematics reel on a dark instrument frame: cir | 20 | -14.1 | 1.3 | -3.6 | 51.0 | 0.4 (0.16) | none | - |
| `ref-19cee08f9c` Dark transformation reel: a dot draws the line,  | 15 | -16.0 | 3.9 | -2.3 | 40.0 | 0.33 (0.12) | none | - |
| `ref-1cbe55c987` SaaS launch promo: UI fragments, orbit hub and w | 15 | -13.6 | 1.7 | -0.3 | 47.8 | 0.25 (0.15) | none | - |
| `ref-1e22836116` Wordless lighthouse short: silhouette layers in  | 46 | -14.2 | 6.4 | -1.0 | 18.4 | 0.0 (0.06) | none | - |
| `ref-216f4eaeef` Silent hand-drawn explainer told in a typed capt | 58 | - | - | - | - | - | no audio | - |
| `ref-2860712d4e` Pencil-on-paper launch film: a ball protagonist, | 15 | -14.2 | 1.7 | -2.4 | 52.0 | 0.0 (0.16) | none | - |
| `ref-2a6c654bfe` Particle-built newsletter-reader intro: dot sphe | 15 | -14.5 | 5.0 | -1.3 | 80.0 | 0.0 (0.23) | sparse | - |
| `ref-31ce9d6332` Narrated light-canvas reading-app explainer: hea | 60 | -16.1 | 1.9 | -1.5 | 55.0 | 0.0 (0.17) | narrated | 2.65 |
| `ref-32fea7dae3` Swiss-type payments cut: hard cuts on whole seco | 23 | -14.2 | 3.1 | -5.2 | 39.1 | 0.0 (0.12) | none | - |
| `ref-37644838b5` 3D isometric infrastructure explainer (screen ca | 98 | -38.2 | 4.3 | -24.3 | 12.3 | 0.0 (0.04) | none | - |
| `ref-392ee4d0f9` Animator's notes reel: bounce, verbs and easing  | 15 | -11.7 | 4.6 | -0.1 | 36.0 | 0.0 (0.11) | sparse | - |
| `ref-3abcbedd20` Cream-and-terracotta editor launch: raw text ren | 30 | -14.1 | 8.2 | -0.9 | 48.0 | 0.25 (0.15) | none | - |
| `ref-49459ad8c1` Dot-led announcement: one dot draws, punctuates  | 10 | -13.6 | 2.4 | -0.8 | 24.0 | 0.25 (0.08) | none | - |
| `ref-57fd2ce3b4` Branding-agency showreel: 28 sub-second cuts acr | 35 | -9.6 | 12.9 | 0.4 | 55.9 | 0.18 (0.17) | none | - |
| `ref-58ff9f39df` First-person AI monologue in kinetic type (portr | 153 | -14.3 | 12.5 | -1.3 | 41.5 | 0.12 (0.13) | none | - |
| `ref-5924215625` Life story along a heartbeat line | 20 | -14.2 | 3.3 | -0.6 | 54.0 | 0.14 (0.16) | none | - |
| `ref-5a2816d4db` Light-canvas connector-tracker promo: three colo | 39 | -16.1 | 1.1 | -3.3 | 67.6 | 0.17 (0.2) | none | - |
| `ref-6f68999b60` Dark SaaS launch: tilted card wall, light-burst  | 30 | -17.4 | 4.6 | -3.1 | 51.8 | 0.0 (0.16) | none | - |
| `ref-70c57c2adf` Motion-designer reel: a line opens the frame, bl | 15 | -15.8 | 1.2 | -2.8 | 148.5 | 0.38 (0.39) | none | - |
| `ref-736d4ef2c2` Constructivist type poster in motion | 30 | -15.7 | 6.3 | -2.1 | 36.0 | 0.1 (0.11) | none | - |
| `ref-7a185cb08d` Photo-print app film: one container morphs from  | 29 | -14.1 | 2.0 | -0.3 | 64.1 | 0.2 (0.19) | none | - |
| `ref-81650adf49` A photon's journey in single words: flash cuts,  | 20 | -12.2 | 6.3 | 0.7 | 44.8 | 0.44 (0.14) | none | - |
| `ref-85d3a83400` French SaaS launch: serif word build, a UI that  | 30 | -14.4 | 2.9 | -1.4 | 60.0 | 0.33 (0.18) | sparse | - |
| `ref-910d9fc567` Paper-theatre silhouette poem (portrait) | 57 | -23.2 | 1.8 | -8.6 | 26.3 | 0.08 (0.08) | sparse | - |
| `ref-92c22222a2` Dark kinetic reel: easing studies, shape morphs  | 15 | -13.1 | 2.9 | -1.2 | 64.0 | 0.4 (0.19) | none | - |
| `ref-9459c8097f` Dark red-glow transcript product ad: headline pa | 15 | -11.7 | 4.1 | -1.0 | 68.0 | - | none | - |
| `ref-95c96d5c47` Neo-brutalist sticker explainer of a distributed | 53 | -70.0 | 0.0 | None | - | - | none | - |
| `ref-99713f6e72` Dark teaser: rim-lit mark, struck statement, car | 15 | -14.3 | 8.7 | -1.3 | 20.0 | - | none | - |
| `ref-9ed4034cad` Light referral promo: struck headline and sticke | 15 | -21.0 | 2.2 | -1.8 | 68.0 | 0.67 (0.2) | none | - |
| `ref-a1c9ef89a3` Split-screen product sting: two products run the | 12 | -14.2 | 1.0 | -2.2 | 84.8 | 0.5 (0.25) | none | - |
| `ref-a2496929ca` A sentence built as a structure (square, silent) | 20 | - | - | - | - | - | no audio | - |
| `ref-a3031376e7` Ball escaping twelve rings: a sonified physics l | 32 | -8.9 | 3.9 | -0.4 | 26.5 | 1.0 (0.08) | sparse | - |
| `ref-a339360a56` Light-canvas product demo: step tracker, word-hi | 40 | -12.3 | 3.8 | -0.7 | 55.5 | 0.5 (0.17) | sparse | - |
| `ref-a943607659` Portrait step-race promo: rolling counters, a co | 44 | -15.9 | 7.9 | -0.2 | 40.9 | 0.0 (0.13) | none | - |
| `ref-ad023ce9dc` Light-canvas AI demo: one camera over a UI canva | 30 | -13.5 | 5.3 | 0.8 | 124.0 | 0.5 (0.34) | none | - |
| `ref-aff23e662b` Monochrome lab reel: eight transition types in f | 15 | -12.7 | 1.9 | -1.6 | 68.0 | 0.38 (0.2) | none | - |
| `ref-b34f751c59` Silent square terminal explainer: a token bucket | 18 | - | - | - | - | - | no audio | - |
| `ref-b4e79aa0a4` One verb per card: word cards with a living full | 24 | -15.3 | 1.5 | -3.1 | 83.2 | 0.09 (0.24) | none | - |
| `ref-b8cf9a12b0` Dark-navy wholesale pitch: a full stop blooms, a | 15 | -13.9 | 4.9 | -1.0 | 40.0 | 0.0 (0.12) | none | - |
| `ref-b97f9168c6` Two-part reel comparison labelled with AI model  | 32 | -14.3 | 3.4 | -0.0 | 56.5 | 0.12 (0.17) | sparse | - |
| `ref-c2addc76df` Music-app film in a dark rounded window: two-ton | 18 | -14.0 | 1.6 | -4.7 | 46.7 | 0.0 (0.14) | none | - |
| `ref-c324a3d516` Swiss-style motion showreel: easing ball, bloom, | 15 | -12.6 | 1.6 | -0.7 | 60.0 | 0.0 (0.18) | none | - |
| `ref-c3bc609841` Hand-drawn cocktail recipe on one stage (square, | 30 | - | - | - | - | - | no audio | - |
| `ref-c6d0aa55f6` Silent textile brand explainer: serif headlines, | 54 | - | - | - | - | - | no audio | - |
| `ref-c87967b288` Silent dark trading-terminal reveal: power-on fr | 47 | - | - | - | - | - | no audio | - |
| `ref-c93524ef20` Monochrome archive collage brand film (portrait) | 14 | -14.3 | 1.8 | -0.9 | 87.1 | 0.33 (0.25) | none | - |
| `ref-ce769bc33e` Ad-tool promo: headline build, card carousel, st | 20 | -13.6 | 1.6 | -1.0 | 65.9 | 0.0 (0.2) | none | - |
| `ref-cfaf668ebf` Silent milestone film: dips to black between sec | 54 | - | - | - | - | - | no audio | - |
| `ref-d386e5f0ae` Silent light-canvas page launch: two-tone headli | 20 | - | - | - | - | - | no audio | - |
| `ref-dc626241e6` Dark market-news app reel: violet diagonal band  | 15 | -11.4 | 0.7 | -0.5 | 96.0 | 0.11 (0.27) | none | - |
| `ref-debf607232` Silent samurai kata on one fixed stage: a sun di | 19 | - | - | - | - | - | no audio | - |
| `ref-e40080c790` One container, twelve UI states: cursor-driven s | 14 | -14.1 | 0.9 | -1.0 | 72.9 | 0.0 (0.22) | none | - |
| `ref-e8125c24ca` Lyric video: each sung word lands on its onset,  | 30 | -12.4 | 3.9 | -1.4 | 46.6 | 0.5 (0.14) | none | - |
| `ref-ee70618e88` Light-canvas AI food-ordering film: a typed crav | 16 | -16.6 | 2.2 | -0.4 | 62.6 | 0.0 (0.19) | none | - |
| `ref-fb375e07e2` Self-introduction reel on black and orange: a le | 15 | -14.6 | 5.2 | -1.6 | 43.8 | 0.14 (0.14) | sparse | - |
| `ref-fd749e7ebc` Motion showreel built from scratch: a bouncing k | 15 | -13.2 | 0.6 | -0.9 | 52.0 | 0.29 (0.16) | none | - |
| `ref-fe7fb0ded2` One-take 3D camera through a dark bookkeeping da | 14 | -17.1 | 11.3 | -3.5 | 34.2 | 0.0 (0.11) | none | - |

## Transition census by reference

| reference | cuts | soft | transition families used |
| --- | ---: | ---: | --- |
| `ref-04d81a6a3e` Slow-build logo reveal: facets fly in on the beat, a sil | 1 | 1 | transition-cut |
| `ref-05acc490f6` Silent blue-and-yellow course launch: stacked colour-pan | 0 | 8 | transition-continuous, transition-cover |
| `ref-05c4222dae` Type, form, space, time: a designer's index card opens f | 2 | 3 | transition-continuous, transition-grow |
| `ref-0a270a1575` Portrait 3D letter-tile story: a left-out tile told in r | 7 | 4 | transition-cut |
| `ref-0b13aa7f02` Cream-and-green app launch with sound placed on every ar | 3 | 3 | transition-cover, transition-grow |
| `ref-0b2552b64e` Light-canvas voice-agent launch (music only): two-tone h | 0 | 0 | transition-continuous |
| `ref-0bf0254a3d` Motion reel: Bauhaus grid, chrome 3D and one-word cards | 3 | 3 | transition-continuous, transition-cover, transition-grow |
| `ref-0fe1abc90a` Mathematics reel on a dark instrument frame: circle to s | 3 | 2 | transition-cut |
| `ref-19cee08f9c` Dark transformation reel: a dot draws the line, rings to | 1 | 5 | transition-continuous, transition-cover, transition-cut, transition-grow |
| `ref-1cbe55c987` SaaS launch promo: UI fragments, orbit hub and word card | 4 | 0 | transition-cover, transition-grow |
| `ref-1e22836116` Wordless lighthouse short: silhouette layers in fog, act | 2 | 4 | transition-continuous, transition-cut |
| `ref-216f4eaeef` Silent hand-drawn explainer told in a typed caption stri | 0 | 0 | transition-continuous |
| `ref-2860712d4e` Pencil-on-paper launch film: a ball protagonist, a figur | 1 | 3 | transition-cover, transition-cut |
| `ref-2a6c654bfe` Particle-built newsletter-reader intro: dot sphere, part | 1 | 2 | transition-cover, transition-grow |
| `ref-31ce9d6332` Narrated light-canvas reading-app explainer: headline le | 0 | 2 | transition-continuous |
| `ref-32fea7dae3` Swiss-type payments cut: hard cuts on whole seconds, lin | 6 | 1 | transition-cut |
| `ref-37644838b5` 3D isometric infrastructure explainer (screen capture) | 7 | 11 | transition-continuous |
| `ref-392ee4d0f9` Animator's notes reel: bounce, verbs and easing curve | 3 | 2 | transition-cover, transition-cut, transition-grow |
| `ref-3abcbedd20` Cream-and-terracotta editor launch: raw text renders, an | 0 | 4 | transition-cover, transition-cut, transition-grow |
| `ref-49459ad8c1` Dot-led announcement: one dot draws, punctuates and open | 3 | 1 | transition-continuous, transition-cut, transition-grow |
| `ref-57fd2ce3b4` Branding-agency showreel: 28 sub-second cuts across iden | 28 | 0 | transition-continuous, transition-cut |
| `ref-58ff9f39df` First-person AI monologue in kinetic type (portrait, 153 | 7 | 18 | transition-continuous, transition-cut |
| `ref-5924215625` Life story along a heartbeat line | 0 | 7 | transition-continuous, transition-cover, transition-grow |
| `ref-5a2816d4db` Light-canvas connector-tracker promo: three colour bloom | 0 | 6 | transition-continuous, transition-cover, transition-grow |
| `ref-6f68999b60` Dark SaaS launch: tilted card wall, light-burst cuts and | 2 | 1 | transition-continuous, transition-cut |
| `ref-70c57c2adf` Motion-designer reel: a line opens the frame, blooms, a  | 2 | 6 | transition-cover, transition-cut, transition-grow |
| `ref-736d4ef2c2` Constructivist type poster in motion | 4 | 6 | transition-continuous, transition-cover, transition-cut, transition-grow |
| `ref-7a185cb08d` Photo-print app film: one container morphs from wordmark | 0 | 10 | transition-cover, transition-grow |
| `ref-81650adf49` A photon's journey in single words: flash cuts, chromati | 2 | 7 | transition-cover, transition-cut, transition-grow |
| `ref-85d3a83400` French SaaS launch: serif word build, a UI that collapse | 0 | 3 | transition-grow |
| `ref-910d9fc567` Paper-theatre silhouette poem (portrait) | 0 | 12 | transition-continuous, transition-cover |
| `ref-92c22222a2` Dark kinetic reel: easing studies, shape morphs and word | 7 | 3 | transition-continuous, transition-cover, transition-cut, transition-grow |
| `ref-9459c8097f` Dark red-glow transcript product ad: headline pairs with | 0 | 0 | transition-continuous |
| `ref-95c96d5c47` Neo-brutalist sticker explainer of a distributed timer | 0 | 9 | transition-continuous, transition-cover |
| `ref-99713f6e72` Dark teaser: rim-lit mark, struck statement, card wall t | 0 | 0 | transition-continuous, transition-grow |
| `ref-9ed4034cad` Light referral promo: struck headline and sticker, a dot | 0 | 3 | transition-cover, transition-grow |
| `ref-a1c9ef89a3` Split-screen product sting: two products run the same be | 4 | 2 | - |
| `ref-a2496929ca` A sentence built as a structure (square, silent) | 0 | 3 | transition-continuous, transition-grow |
| `ref-a3031376e7` Ball escaping twelve rings: a sonified physics loop (por | 1 | 0 | transition-continuous, transition-cut |
| `ref-a339360a56` Light-canvas product demo: step tracker, word-highlight  | 0 | 2 | transition-continuous |
| `ref-a943607659` Portrait step-race promo: rolling counters, a countdown  | 1 | 7 | transition-continuous, transition-cut |
| `ref-ad023ce9dc` Light-canvas AI demo: one camera over a UI canvas, an im | 0 | 4 | transition-continuous, transition-grow |
| `ref-aff23e662b` Monochrome lab reel: eight transition types in fifteen s | 5 | 3 | transition-cover, transition-cut, transition-grow |
| `ref-b34f751c59` Silent square terminal explainer: a token bucket simulat | 0 | 0 | transition-continuous |
| `ref-b4e79aa0a4` One verb per card: word cards with a living full stop fo | 20 | 3 | transition-grow |
| `ref-b8cf9a12b0` Dark-navy wholesale pitch: a full stop blooms, a counter | 2 | 3 | transition-cover, transition-cut, transition-grow |
| `ref-b97f9168c6` Two-part reel comparison labelled with AI model names | 7 | 9 | transition-continuous, transition-cover, transition-cut |
| `ref-c2addc76df` Music-app film in a dark rounded window: two-tone headli | 0 | 3 | transition-continuous |
| `ref-c324a3d516` Swiss-style motion showreel: easing ball, bloom, shape m | 1 | 6 | transition-continuous, transition-cover, transition-grow |
| `ref-c3bc609841` Hand-drawn cocktail recipe on one stage (square, silent) | 0 | 0 | transition-continuous |
| `ref-c6d0aa55f6` Silent textile brand explainer: serif headlines, photo g | 0 | 8 | transition-continuous, transition-cover |
| `ref-c87967b288` Silent dark trading-terminal reveal: power-on from a dot | 0 | 4 | transition-continuous, transition-cover, transition-grow |
| `ref-c93524ef20` Monochrome archive collage brand film (portrait) | 1 | 2 | transition-cover, transition-grow |
| `ref-ce769bc33e` Ad-tool promo: headline build, card carousel, stat cards | 0 | 4 | transition-grow |
| `ref-cfaf668ebf` Silent milestone film: dips to black between sections, a | 0 | 11 | transition-continuous |
| `ref-d386e5f0ae` Silent light-canvas page launch: two-tone headlines, liv | 0 | 0 | transition-continuous |
| `ref-dc626241e6` Dark market-news app reel: violet diagonal band wipes ev | 5 | 4 | transition-cover |
| `ref-debf607232` Silent samurai kata on one fixed stage: a sun disc, embe | 3 | 3 | transition-continuous |
| `ref-e40080c790` One container, twelve UI states: cursor-driven shape cha | 0 | 3 | transition-continuous, transition-grow |
| `ref-e8125c24ca` Lyric video: each sung word lands on its onset, the lane | 5 | 7 | transition-cut, transition-grow |
| `ref-ee70618e88` Light-canvas AI food-ordering film: a typed craving, a l | 2 | 5 | transition-grow |
| `ref-fb375e07e2` Self-introduction reel on black and orange: a letter blo | 1 | 6 | transition-cover, transition-grow |
| `ref-fd749e7ebc` Motion showreel built from scratch: a bouncing keyframe  | 4 | 3 | transition-continuous, transition-cover, transition-cut, transition-grow |
| `ref-fe7fb0ded2` One-take 3D camera through a dark bookkeeping dashboard | 0 | 2 | transition-grow |

<!-- END GENERATED -->
