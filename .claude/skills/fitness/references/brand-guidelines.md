# Sinew brand guidelines (v1.0, 2026-11-08)

Sources of truth: tokens in `src/studio/styles/sinew-lab.css` and `Studio.kit.fitness.palette` (`src/studio/kits/fitness/tibi.js`); logo and graphics in `src/studio/kits/fitness/graphics.js`; rendered boards in `assets/fitness/previews/` (`brand.png`, `tibi-sculpt-model.png`, `tibi-sculpt-activation.png`, `expressions.png`, `thumbnail.png`); SVG exports in `assets/fitness/brand/`. Why this direction: `brand-concepts.md`.

## 1. Identity

| | |
|---|---|
| Brand | **Sinew** (lowercase wordmark `sinew`) |
| Mascot | **Tibi** (from *tibia*): a male and a female athlete in the Cobalt Sculpt style (flat cobalt muscle planes, no outlines, marigold spark); the earlier glass-body cartoon is classic Tibi (legacy) |
| Promise / tagline | **See what your body is doing.** |
| Positioning | Character-led exercise science: the movement first, then the mechanism inside the same body, with the evidence grade on screen. |
| Personality | Curious, warm, precise, a little cheeky; never hype, never shame. Tibi reacts; the narrator explains. |
| Voice | "Sinew narrator": Kokoro `am_michael` at 1.05 (slow scenes 0.94). Second person, contractions, one idea per breath. No "bro", no fear-selling, no miracle words ("hack", "secret"). |
| Audience | Gym-goers, runners and curious beginners, 16+; no biology assumed. |

**Trademark note.** "Sinew" and "Tibi" were chosen for meaning and sound, not cleared legally. Before publishing commercially, run a trademark search (USPTO, EUIPO, UKIPO) in classes 41 (education, entertainment) and 9 (downloadable video). Several gyms and products use "Sinew" in their names; the character name and lockup carry most of the distinctiveness.

## 2. Colour

| Token | Hex | Use |
|---|---|---|
| paper | `#F6F3EC` | canvas (light by default, the workspace rule) |
| paper-2 | `#ECE5D8` | panels, alternate rows |
| ink | `#1B1D29` | text, outlines (15.1:1 on paper) |
| ink-2 | `#4A4E60` | secondary text, sources (7.4:1) |
| **cobalt** | `#2F56E0` | Tibi's body, brand colour, kicker pills, "building" data (5.4:1, text OK) |
| cobalt-light | `#4F75EC` | Tibi's light planes (muscles, Cobalt Sculpt) |
| cobalt-shade | `#2244B8` | Tibi's shade planes and crescents (Cobalt Sculpt) |
| navy | `#18286F` | Tibi's eyes, far-limb overlay, rig markers, ink on shoes |
| stabiliser | `#8CAEFA` | activation level 1 on Tibi (pale cobalt) |
| **spark** | `#FFB224` | the spark, markers, emphasis bars, signal (shapes only, 1.6:1; ink on spark 9.3:1) |
| **muscle** | `#F2553D` | anatomy only: muscle tissue, never decoration (3.1:1, shapes and large text) |
| muscle-deep | `#C2381F` | myth stamps, "breakdown", strike-throughs (4.9:1) |
| emerald | `#12A36E` | evidence (badges, net gain areas); text in `#0B7A52` |
| violet | `#7B5CE0` | nuclei, myosin, hypotheses |
| bone | `#F4EAD5` | skeleton layer |

Rules: coral means muscle, nothing else. One accent per beat besides cobalt. Dark themes only when a brief asks.

## 3. Typography

| Role | Family / weight | Size (landscape 1280x720) |
|---|---|---|
| Display, titles, cards | **Outfit** 800 (900 for thumbnails) | 44-64 px; tracking -0.02em |
| Labels, body | **Inter** 500-700 | 15-24 px |
| Sources, data, kickers | **JetBrains Mono** 500-700 | 13-18 px; kickers uppercase, +0.08em |

All three are HyperFrames-bundled (OFL). Name them literally in compositions (`font-family: 'Outfit'`); a variable from a linked sheet is not injected.

## 4. Logo

- **Lockup:** icon + wordmark (`G.logo(g, {variant: 'lockup'})`). Clear space = the height of the spark on all sides. Minimum width 120 px.
- **Icon:** Tibi's head (face patch, eyes, smile) on a cobalt rounded square with the spark on top (`variant: 'icon'`). Use as avatar and favicon.
- **Wordmark:** lowercase `sinew` in Outfit 800; the dotless i takes the spark as its dot (`variant: 'wordmark'`). On cobalt, ink becomes paper.
- Never: recolour the spark, outline the wordmark, put the icon on a photo, stretch, or add a tagline under the icon alone.

## 5. Graphic system (all in `graphics.js`)

| Element | API | Rule |
|---|---|---|
| Title card (short and mid) | `G.titleCard` | kicker pill (`Sinew · topic`), max 2 lines, last line cobalt, spark bar |
| Lower third | `G.lowerThird` | cobalt tab with spark, Outfit title, mono definition line: one per term |
| Chapter card (long) | `G.chapterCard` | "CHAPTER n", descriptive title, one-line mechanism |
| Evidence badge | `G.evidenceBadge` | six fixed grades and colours (research protocol); always with a claim |
| Source line | `G.citation` | `Author et al. year · journal · design/n`; with every number |
| Myth stamp | `G.mythStamp` | over the myth's own words, once per film |
| Callout | `G.callout` | dot on the structure, drawn leader, Outfit label plus a function line |
| Opening and closing | `G.sting`, `G.endCard` | sting (spark flare, lockup, tagline) about 2.2 s; end card rows plus the general-education line |
| Environments | `G.env.gym/track/outdoor/plate` | backgrounds stay desaturated behind Tibi; diagrams sit on the dot-grid plate inside a white panel |

**Long-form opening:** cold-open hook (Tibi moving) for 5-15 s, then `G.sting` (2.2 s), then chapter 1's card. **Long-form close:** the takeaway end card, sources slate, then the sting with the tagline. **Short-form:** no sting at the start (the hook owns the first second); the icon may sit at the end card.

## 6. Thumbnails

`assets/fitness/sheets/thumbnail.html` is the template: paper ground, a pale cobalt disc behind Tibi at large scale doing the exercise with the subject muscle in coral, 1-3 words in Outfit 900 (ink plus one coral or cobalt word), a spark bar, and the small lockup bottom-left. The words must pass the story-writer's Clear gate and never repeat the title. Check at 168x94 px and in greyscale. Keep the same layout across a series.

## 7. Motion principles

- Tibi never freezes: reps, breathing, weight shifts, activation changes on meaning words (snap to `studio.py words`). Tibi has no face rig: the body carries the acting.
- Springy character acting (`back.out`, anticipation on big poses); calm, precise diagram builds (`power2`, drawn lines, one change every 2-3 s).
- Mechanism scenes open from Tibi's body (x-ray, lens line, zoom ladder), not from a hard cut to a diagram.
- Science stays still enough to read: no shake, no whip pans; scale labels on every zoom.
- No whoosh on cross-dissolves (workspace rule).

## 8. Camera and lighting conventions

2D: flat light from top-left (a light plane and a crescent shade on every muscle, no outlines), one soft floor shadow ellipse, no gradients on the character. Default framing: side view for exercises (sagittal biomechanics), front view for talking and explaining, back view for back muscles, from above for prone and lying work. Tibi's feet on the floor line; keep the caption band clear (landscape floor about y 560).

## 9. Sound identity (`scripts/sinew_sound.py`)

- **Bed:** warm Dmaj7 pad over a soft 96 bpm pulse; IV (Gmaj7) in mechanism scenes, ii (Em7) for complications, home on the logo. About 17 dB under the voice after the mux.
- **Sonic logo ("spark"):** two marimba notes a fifth apart (A5 to E6) with a shimmer: logo only.
- **Foley:** rubber thud on each lifted rep, dry ticks for chart points, rounded pops for badges and cards, low thump plus paper burst for the myth stamp, a filtered swell into a scale dive, a double pulse for signals.

## 10. Do and don't

Do: show the mechanism on Tibi's own body; state the evidence grade; keep coral for muscle; let the narrator be precise and Tibi be funny.
Don't: shame bodies, sell supplements, use before/after physique imagery, show blood or injury gore, use real athletes' likenesses, or give individual prescriptions.
