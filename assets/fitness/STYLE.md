# Sinew style guide (fitness asset library)

One system for every Sinew film. If a film needs something this guide does not cover, extend the guide and the kit first, then the film. Companion files: `.claude/skills/fitness/references/brand-guidelines.md` (logo, voice, sound), `character-guidelines.md` (Tibi), `.claude/skills/fitness-anatomy/SKILL.md` (anatomy), `src/studio/styles/sinew-lab.css` (the tokens).

## Identity
**"See what your body is doing."** Tibi is one athletic body in the Cobalt Sculpt identity: cobalt skin, a marigold spark on the head, white shoes, no face detail, dark shorts with a marigold waistband (a dark crop top on the female body). The silhouette is the brand: broad shoulders tapering to the waist, a spark, shoes. It must read as Tibi in silhouette alone. The old two-dimensional Tibi stays for static poses, running, brand cards and storytelling; the 3D Tibi is the same character with a free camera. Decision (ADR-2, `docs/fitness-studio.md`): refine, do not replace; the failure was the anatomy, not the character. Studied for communication, never copied: Yellow Dude's playful, low-ego tone ("start ugly", one idea per video) is a discipline to match, not a look to borrow; its production page was not retrievable (HTTP 404) so no process claims are made from it.

## Character modes (one body, never two competing characters)
| Mode | What it shows | Use |
|---|---|---|
| Normal | the continuous body, no highlight | default for every demonstration |
| Activation | effort as a gradient on the skin by role | what works, by how much (illustrative) |
| Anatomy | cutaway window, isolated muscle, layers, skeleton | what is under the skin, when the lesson needs it |
| Storytelling | the 2D Tibi (expressive poses, cards) | hooks, brand, explanations that need acting |

## Colour (tokens in sinew-lab.css; canvas `#F6F3EC` paper, ink `#1B1D29`)
cobalt skin `#2A4FD8` (muscle tone `#4468EA`) · coral prime `#F2553D` · marigold helper/spark `#FFB224` · pale cobalt stabiliser `#8CAEFA` · emerald for "same/ok" `#17A673` · rosewood `#C98A82` / `#A8645F` for muscle under the skin, ivory `#F3E7CF` tendon, bone `#E3D5B6`, cream `#F6EFE0` cut edge. **One meaning per colour**: cobalt = the outside, coral/marigold gradient on skin = effort, rosewood/ivory = inside, ghost pale = transparent skin, a card with discs and a trace = a measurement. Dark themes only when a brief asks.

## Type
Outfit (display, 700-800) for titles, cues and labels; Inter (600) for sentences; JetBrains Mono (500-600) for kickers, sources, "illustrative" tags. Caption presets by style (`specs/caption-presets.json`): phrases, never single orphan words. Minimum on-screen size on 720 px: 22 px for labels, 14 px for source lines.

## Backgrounds, light, shadow
Paper canvas with a faint floor grid in 3D; no environment noise behind the lift. Key light rides the camera (cobalt light and shade planes read the same from any angle). Toon shading in four bands; soft blob shadow only under feet; creases between muscles are a 24% darkening, never an outline.

## Camera language
One move or one cut per spoken cue, never both. Front names the muscle, three-quarter is the default lift shot, side shows range and bar path, back shows lats, glutes, calves, above shows bar path and elbow flare. Orbit slowly (30-60 degrees over a set); cut on a cue. A cutaway opens on the side the camera sees. Standing figure framing for portrait: top >= y 330, floor <= y 895 (`motion-3d.md` rule 13).

## Annotation and overlay vocabulary (`film3d.js`, `scenes3d.js`)
Pins ride the skin and take the role colour; joint-angle arc with a number marked "illustrative"; dashed trail for the load's path; rep HUD (REP n / N, phase pill coloured by shortening, lengthening or holding, a tempo bar to scale); one cue card per phase; electrode + trace card for sEMG; a chip ("Under the skin") whenever the picture changes level. One idea per frame; the character and the movement stay the focus.

## Motion principles
Eccentric slower than concentric, short holds at the ends, every rep the same tempo; no art swaps and no visibility switches (continuous parameters only); contacts planted by IK, never hand-posed; ramps never shorter than 0.35 s (activation colour) or 1.0 s into dark cloth; frame 0 already carries the hook and the start pose; something moves in every 2-3 seconds.

## Sound
Original, synthesised (`sinew_sound.py`): a warm bed, a soft tick where a lift starts, a low thud at the end range, a spark chime only on the logo. Narration: brand voice `am_michael` at 1.05 unless a scene overrides; no whooshes on educational cross-dissolves; -16 LUFS +/- 2.
