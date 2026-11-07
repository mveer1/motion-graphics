---
name: caption-designer
description: Style, font and place the burned-in captions of a Motion Lab film. Use when a film has captions on, when choosing or changing a caption preset, when a scene's lower third is busy and the captions need another lane, when captions look wrong in frame review, or when asked where captions go in the hook, body or outro. Guide docs/caption-design.md, numbers specs/caption-presets.json.
version: 0.1.0
---

# Caption designer

Captions are an overlay on the full frame, never a reserved band. Every film gets one preset (font, size, plate, highlight, entrance) chosen from its style system, and every cue gets a lane by section: hook mid, body lower, outro lower, upper when a scene's lower third is busy. Read [docs/caption-design.md](../../../docs/caption-design.md) for the tables; the machine-readable source is [specs/caption-presets.json](../../../specs/caption-presets.json).

## Do this

1. **New film.** `studio.py new` turns captions on and writes the style's preset into `src/captions.js`. Nothing to author in `src/index.html`: the template calls `Studio.comp.captions`.
2. **Story phase.** If a scene puts its key visual, a source line or a call to action in the lower third, add `"caption_lane": "upper"` to that scene in `storyboard.json`. Portrait has lanes `lower`, `mid`, `upper`; landscape and square have `lower` and `upper`.
3. **After narration is measured.** `python scripts/studio.py captions <slug> --timing words` (heavy: it takes the analysis lock; run it, never in parallel with a render). Grouping follows the video type: phrase cues for a reel (3 words) and long reel (4), sentence cues for YouTube. `--preset <id>` or `project.json` `audio.caption_preset` overrides the style's choice.
4. **Gate.** `python scripts/studio.py validate <slug>` warns on a stale or missing preset, cues too long for two lines, more than two lanes and a late first caption. Then `frame-review.py` for clipping, safe area and contrast. Read the cue text once for names, numbers and units.
5. **Changing the look.** Fix it in `specs/caption-presets.json` and `src/studio/studio-base.css` together (`tests/test-short-form.py` fails when they drift), bump `Studio.version`, run `studio.py upgrade --all`. Never hand-edit `_studio/`, and never style one film's captions with one-off CSS: that is a template problem (refine, do not patch one video).

## Rules that are easy to break

- One preset per film; at most two lanes; a lane changes only between cues (once after the hook, then at scene boundaries).
- Plate or outline, never neither. Do not use `bold-pop` caps for long sentences.
- Only numbers are emphasised automatically. Do not add a highlight or motion to every word.
- Fonts must be literal `font-family` names in CSS or HyperFrames will not inject them; they are already in `studio-base.css` for the five presets.
- A film that draws its own caption band is skipped by the checks; do not re-run `captions` over hand-keyed cues.
- Status is experimental: only snapshot-checked, never in a full build or on a phone. Say so when reporting.
