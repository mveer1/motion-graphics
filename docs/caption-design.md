# Caption design: style, font and placement

Burned-in, word-timed captions for every film. This guide is the short version; the numbers live in
[specs/caption-presets.json](../specs/caption-presets.json) and are applied by `studio.py captions` and
`Studio.comp.captions`. Pick the preset from the film's style, put the caption in the right lane for the section,
and let the tooling do the rest.

## In the flow

| Phase | What happens | Who |
|---|---|---|
| 1 brief | `studio.py new` turns captions on and pre-selects the preset from the style (written to `src/captions.js`) | automatic |
| 2 story | Mark a scene `caption_lane: "upper"` in `storyboard.json` when its lower third is busy (diagram label, source line, call to action) | `story-writer` |
| 3 audio | `studio.py captions <slug> --timing words` writes the cues, a role per cue (hook, body, outro), emphasised numbers and the preset. Grouping follows the video type | `voice-director` |
| 3 visuals | The template already calls `Studio.comp.captions`; nothing to author. Keep scene content out of the caption lane's plate | author |
| 3 gate | `studio.py validate` (preset, cue length, lane count) then `frame-review.py` (clipping, safe area, contrast) | author |
| 4 render | `studio.py build`. Captions are part of the visuals render, not a mux step | automatic |

To pin a preset instead of taking the style's: `project.json` `audio.caption_preset`, or `studio.py captions <slug> --preset <id>`. One preset per film.

## 1. Style picks the preset and the font

All fonts are bundled with HyperFrames, so they render offline. Sizes are in `--u` (1 % of the short side); pixels are at the default 720p delivery.

| Preset | Style systems | Feel | Font | Portrait | Landscape | Plate | Entrance |
|---|---|---|---|---|---|---|---|
| `clean-plate` | editorial-light, swiss-minimal, data-journalism, abstract-geometric, sci-viz | calm, factual: finance, news, science, maths, tech | Inter 700, sentence case | 6.6u (48 px) | 4.4u (32 px) | style plate | fade |
| `bold-pop` | mixed-media (or pin it for a punchy reel) | high energy, youth, culture | Montserrat 800, caps | 7.4u (53 px) | 4.6u (33 px) | none, outline and shadow | pop; spoken word grows 8 % |
| `serif-quiet` | archival, cinematic-dark | documentary, history, reflective | EB Garamond 600 | 7.2u (52 px) | 4.8u (35 px) | style plate, 94 % | fade |
| `paper-label` | paper-cut | playful, handmade, storybook | Nunito 800 | 6.8u (49 px) | 4.5u (32 px) | style plate, round | rise |
| `mono-type` | dark-tech | technical, terminal | JetBrains Mono 600 | 5.8u (42 px) | 3.9u (28 px) | style plate, 94 % | fade |

Why these choices:
- A sans-serif with a clear bold (Inter, Montserrat, Nunito) is the dependable default for captions over moving picture; thin or light weights vanish on busy backgrounds. Serifs and monospace are used only where the film's tone is the point, and run at a different size to hold the same apparent size.
- Match the caption tone to the content. A hype style on a calm explainer fights the film.
- The spoken word turns `--c-caption-hl` (the style's third accent). A number or amount keeps that colour for the whole cue. Nothing else is highlighted: a highlight on every word is no highlight.
- Plate or outline, never neither. Plate-less light text vanished on a light canvas in testing, so only `bold-pop` runs without a plate and it carries an eight-way outline.

## 2. Lanes: where the plate sits

A lane is a vertical position, as a fraction of the frame height. Captions are an overlay on the full composition, never a reserved band: do not move scene content up to make room.

| Format | Lane | Edge | Position | Use |
|---|---|---|---|---|
| portrait 720x1280 | `lower` | bottom edge | 76.6 % (y 980) | Default for body. Just above the platform caption and action bar |
| portrait | `mid` | bottom edge | 64 % (y 819) | Hook window |
| portrait | `upper` | top edge | 14 % (y 179) | A scene whose lower third is occupied |
| landscape 1280x720 | `lower` | bottom edge | 92 % (y 662) | Always |
| landscape | `upper` | top edge | 8 % (y 58) | Only when the lower band holds a lower third or source line |
| square 1080x1080 | `lower` / `upper` | 91 % / 10 % | | as landscape |

Plates are centred on the frame, at most two lines, and never wider than the safe area. In portrait keep the right 12 % clear below 52 % of the height (button rail).

## 3. Section by section

| Section | When | Lane (portrait / landscape) | Size | Behaviour |
|---|---|---|---|---|
| First caption | on screen by about 0.3 to 1 s | mid / lower | x1.15 | A silent opening is a hook with no words: `validate` warns when the first cue is later than 1.5 s |
| Hook | 0 to 3 s | mid / lower | x1.15 | Larger and nearer the eye line, so it reads before the thumb moves |
| Body | rest of the film | lower / lower | x1 | One stable home for the voice. 1 to 3 words per cue in a reel, 4 in a long reel, a sentence of two lines at most on YouTube |
| Number or key term | any | same lane | same | Highlight colour for the number for the whole cue. No extra motion except in `bold-pop` |
| Busy lower third | per scene | upper / upper | same | Set `caption_lane: "upper"` on that scene in `storyboard.json`. Return to lower at the next scene boundary |
| Silence | gaps over about 0.6 s | | | The cue ends with its last word plus a short hold. No plate lingers over silence |
| Outro | last scene | lower / lower | x1 | The end card owns the rest of the frame. If the card carries a call to action low in the frame, mark the scene `upper` |

Lane changes happen only between cues: once when the hook ends, then only at a scene boundary. At most two lanes per film (`validate` warns on a third).

## 4. Text rules

- Cue length: portrait phrase cues are 18 characters or fewer; portrait sentence cues stay under 44 characters; landscape under 90 (two lines of about 45).
- Never end a phrase on a weak word ("the", "to", "had"); the grouping code already avoids it.
- Text at least 2.6 % of the short side and contrast at least 4.5 to 1 against the plate: `frame-review.py` and `motion-qa.py` check both.
- Show the display spelling, not the phonetic respelling used for the voice. Read the cues once for names, numbers and units before render.
- Never place a caption over a face or the hero object. Use the upper lane instead.
- A film that draws its own caption band (cloud-physical-infrastructure-india) is skipped by the design checks; do not re-run `studio.py captions` over hand-keyed cues.

## 5. Where this comes from, and what is unproven

- **HyperFrames** (Apache-2.0), `captions-overlay` skill and caption catalogue: captions are an overlay, most text rides the verbatim rail and a promoted word is scarce, match tone to content, do not stack an effect on every word.
- **josiahsiegel/claude-plugin-marketplace**, `viral-video-animated-captions` (MIT): preset vocabulary (pop, sweep, fill), word appear time about 80 to 250 ms, large high-contrast sans with a thick outline.
- **reap.video** short-form safe-zone article: cross-platform working margins. These are third-party and not published by any platform; the sources disagree, so the workspace keeps its own numbers in `specs/format-presets.json`. Nothing was copied from any of them. No code was adopted.
- Sizes, lane positions, the 3 s hook window and the four-word long-reel phrase are workspace judgement.
- **Checked:** the five presets in portrait and `clean-plate` in landscape, as HyperFrames snapshots of a scratch project on 2026-11-07 (fonts load, lanes land where the spec says, emphasis and spoken-word highlight work). **Not checked:** a full `studio.py build` with captions, `frame-review.py` on a captioned film (Playwright is not installed on this host), a phone's interface overlay, and whether Montserrat 800 and Nunito 800 are real bundled weights. Status stays `experimental` until one film ships with them.
