---
name: caption-designer
description: Style, font and place the burned-in captions of a Motion Lab film. Use when a film has captions on, when choosing or changing a caption preset, when a scene's lower third is busy and the captions need another lane, when captions look wrong in frame review, or when asked where captions go in the hook, body or outro. Guide docs/caption-design.md, numbers specs/caption-presets.json.
version: 0.1.0
---

# Caption designer

Captions are an overlay on the full frame, never a reserved band. Every film gets one preset (font, size, plate, highlight, entrance) chosen from its style system, and every cue gets a lane by section: hook mid, body lower, outro lower, upper when a scene's lower third is busy. Read [docs/caption-design.md](../../../docs/caption-design.md) for the tables; the machine-readable source is [specs/caption-presets.json](../../../specs/caption-presets.json).

## Do this

1. **New film.** `studio.py new` turns captions on and writes the style's preset into `src/captions.js`. Nothing to author in `src/index.html`: the template calls `Studio.comp.captions`.
2. **Story phase.** If a scene puts its key visual, a source line or a call to action in the lower third, add `"caption_lane": "upper"` to that scene in `storyboard.json`. Portrait has lanes `lower`, `mid`, `upper`; landscape and square have `lower` and `upper`. Every format also has `subject`: when the voice names one thing on screen, add `"caption_lane": "subject"` and `"caption_anchor": "#element-id"` (optional `"caption_side": "above"`) and the caption sits beside that element.
3. **After narration is measured.** `python scripts/studio.py captions <slug> --timing words` (heavy: it takes the analysis lock; run it, never in parallel with a render). Grouping follows the form: phrase cues for short-form (3 words) and portrait mid-form (4), sentence cues for landscape mid-form and long-form. `--preset <id>` or `project.json` `audio.caption_preset` overrides the style's choice.
4. **Gate.** `python scripts/studio.py validate <slug>` warns on a stale or missing preset, cues too long for two lines, more than two lanes and a late first caption. Then `frame-review.py` for clipping, safe area and contrast. Read the cue text once for names, numbers and units.
5. **Changing the look.** Fix it in `specs/caption-presets.json` and `src/studio/studio-base.css` together (`tests/test-short-form.py` fails when they drift), bump `Studio.version`, run `studio.py upgrade --all`. Never hand-edit `_studio/`, and never style one film's captions with one-off CSS: that is a template problem (refine, do not patch one video).

## Rules that are easy to break

- One preset per film; at most two lanes; a lane changes only between cues (once after the hook, then at scene boundaries).
- Plate or outline, never neither. Do not use `bold-pop` caps for long sentences.
- Only numbers are emphasised automatically. Do not add a highlight or motion to every word.
- Fonts must be literal `font-family` names in CSS or HyperFrames will not inject them; they are already in `studio-base.css` for the five presets.
- A film that draws its own caption band is skipped by the checks; do not re-run `captions` over hand-keyed cues.
- Status is experimental: only snapshot-checked, never in a full build or on a phone. Say so when reporting.

## Learned from reference videos

From `docs/reference-playbook.md` ("Captions and on-screen copy"; techniques `word-highlight-caption`, `caption-voice-strip`, `lyric-word-onset-sync`, `two-tone-headline-pair`, `dim-previous-line-stack`, `step-caption-pill`, `pause-locked-copy-swap`), 64 inspected references (2026-11-27):

- The one captioned narration seen (a product's own sample explainer) puts two short lines directly under the illustration being narrated and colours the spoken word. That keeps the eye on the subject; use the `subject` lane with a `caption_anchor` on the illustration (runtime 1.17.0).
- Text-led promos carry their copy in headlines, not captions: one accent-coloured key word per sentence-case headline, or a two-line pair whose second line answers in the accent colour (5 references), a hook fixed in the top band for a whole portrait film, giant centred single words in kinetic reels. Do not stack captions over a headline that already says the line.
- **Caption as the only voice (muted films).** A silent explainer carries its whole script in a lower-third strip (82-96% of the height, 1-3 lines, no highlight): each cue types in at about 7-8 words/s, then holds complete at least 1.5 s (median 3.5 s), one cue per scene, swapped on the scene change at a whole second: 199 words a minute on screen (`ref-216f4eaeef`, 10 cues, 192 words in 58 s). Our captions are timed from measured speech only; a reading-pace timing mode is not built (open question in `prompts/state/decisions-needed.md`).
- **Timing against a voice (measured on singing only).** A word starts to show 0-120 ms before its vocal onset (median about 15 ms early) and never more than about 40 ms after; a line's exit dissolve (0.1-0.3 s) starts on the next phrase's first word (`ref-e8125c24ca`, 14 word arrivals at 30 fps). Check that `Studio.comp.captions` applies the spoken-word highlight at or slightly before the word start, never after.
- **Subtitle plate variant.** One line of 6-12 words on a dark rounded plate at about 90% of the height, one accent word per cue echoing the headline's accent word, hard one-frame swaps every 2-3 s (`ref-85d3a83400`).
- **Step pill for a wordless demo.** One line of 4-8 words in a near-black rounded pill at bottom centre (about 90% down), held 3.5-5 s and changed only when the next step starts; no word highlight (`step-caption-pill`; `ref-ad023ce9dc`, 5 cues in 30 s). Cues faster than about 2.5 s cannot be read beside a UI.
- **Text against a music bed does not lock.** Headline words arrive on their own fixed stagger (median 0.10-0.20 s) and land on music onsets only at chance (10 of 21 within 50 ms against 0.51 in `ref-0b2552b64e`); only the accent payoff word sits on an onset (2 of 3 lines, within 10 ms). A voice pulls words to it (the sung case above); a bed does not, so snap caption words to speech and headline payoffs to the beat, nothing else.
- One narrated reference has been measured (1 of 64 inspected, `ref-31ce9d6332`), and it has no captions: its headline lane top-left is the caption. Each headline changes only in a pause of the voice (11 of 11, chance 0.28) and is readable 0.27-0.58 s before its phrase; list lines 0.21 s before; a swap is about 0.35 s (fade out 0.17-0.20 s, 0.07-0.10 s empty, fade in 0.13-0.15 s) (`pause-locked-copy-swap`). For a headline lane in a narrated film, change copy in the pause and lead the phrase by 0.2-0.6 s. One film measured with rough dictation is not enough to change a preset's speech timing; the word-highlight caption's timing stays as it is.
- A portrait end card in the corpus puts its top line and its address at 77 px from the frame edges, outside our portrait safe zones; keep caption and card lanes inside `--safe-*`.
