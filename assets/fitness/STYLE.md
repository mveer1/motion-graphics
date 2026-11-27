# Sinew style guide (fitness asset library)

One system for every Sinew film. If a film needs something this guide does not cover, extend the guide and the kit first, then the film. Companion files: `.claude/skills/fitness/references/brand-guidelines.md` (logo, voice, sound), `character-guidelines.md` (Tibi), `.claude/skills/fitness-anatomy/SKILL.md` (anatomy), `src/studio/styles/sinew-lab.css` (the tokens).

## Identity
**"See what your body is doing."** Tibi is one athletic body in the Cobalt Sculpt identity: cobalt skin, a marigold spark on the head, white shoes, no face detail, dark shorts with a marigold waistband (a dark crop top on the female body). The silhouette is the brand: broad shoulders tapering to the waist, a spark, shoes. It must read as Tibi in silhouette alone. The old two-dimensional Tibi stays for static poses, running, brand cards and storytelling; the 3D Tibi is the same character with a free camera. Decision (ADR-2, `docs/fitness-studio.md`): refine, do not replace; the failure was the anatomy, not the character. Yellow Dude is studied for character-led explanation and clear hierarchy, not a look or script to copy. Its production article was retrieved in the 2026-11-20 study: publisher process statements are attributed, not independently verified, and provocative hooks are not automatically adopted.

## Character modes (one body, never two competing characters)
| Mode | What it shows | Use |
|---|---|---|
| Normal | the continuous body, no highlight | default for every demonstration |
| Activation | effort as a gradient on the skin by role | what works, by how much (illustrative) |
| Anatomy | cutaway window, isolated muscle, layers, skeleton | what is under the skin, when the lesson needs it |
| Storytelling | the 2D Tibi (expressive poses, cards) | hooks, brand, explanations that need acting |

## Colour (tokens in sinew-lab.css; canvas `#F6F3EC` paper, ink `#1B1D29`)
cobalt skin `#2A4FD8` (muscle tone `#4468EA`) · coral prime `#F2553D` · marigold helper/spark `#FFB224` · pale cobalt stabiliser `#8CAEFA` · emerald for "same/ok" `#17A673` · rosewood `#C98A82` / `#A8645F` for muscle under the skin, ivory `#F3E7CF` tendon, bone `#E3D5B6`, cream `#F6EFE0` cut edge. **One meaning per colour**: cobalt = the outside, coral/marigold gradient on skin = effort, rosewood/ivory = inside, ghost pale = transparent skin, a card with discs and a trace = a measurement.

Inside-the-body plates (`anatomy.js`: vascular tree, alveolus, joint sections; tokens in `Studio.kit.fitness.anatomy.inside`, 2026-11-23) stay in that inside language: deep rosewood `#A8645F` for oxygen-rich blood and vessel walls, a dusk tone `#6F5B70` (light `#9B879A`) for oxygen-poor blood, ivory `#F3E7CF` for cartilage, ligaments, tendons and valves, bone `#E3D5B6` with a `#B39C72` edge, a pale rosewood `#EFD9D2` for synovial fluid and bursae, `#FBF8F1` for air. Never the effort colours or the cobalt skin inside, and every plate carries an ILLUSTRATIVE tag in JetBrains Mono. The older plates (heart, lungs, muscle) still use the earlier red/blue and coral tissue colours; move them to this language when they are next touched. Dark themes only when a brief asks.

The current 2D master uses body `#2F56E0`, not the 3D skin token above. The effort
colours match, but the base fills and shading are not identical. Keep the
approved 2D palette fixed until the owner selects a cross-medium direction;
do not call the existing four-band 3D treatment a verified crescent-shading match.

Runtime 1.10.0's default `distance` body incorporates the requested anatomical
correction: broad lat/pec fans, an integrated shoulder cap, continuous abdominal
bands, embedded limb forms and a torso-owned top. Explicit `legacy` is kept
for compatibility comparisons. Palette tokens, spark, shoes and approved 2D
art remain fixed; this is not a photoreal body or an exact attachment atlas.
The owner's subsequent shoulder rejection is addressed in 1.11.0: the
shoulder roof must slope into a rounded, downward-tapering deltoid, never
an exposed joint sphere or a flat-ended arm tube. The neutral stance gives
the arms/waist visible separation; compare the old pose separately so a
posture change cannot masquerade as a geometry fix. `fig.defaultPose` is
the current neutral stance, not the authored-motion `T3.DEFAULT_POSE`.
Hands retain their stylised grip language; no articulated-finger claim.
Current behavior and limits: `docs/fitness-studio.md` sections 9-10.

## Type
Outfit (display, 700-800) for titles, cues and labels; Inter (600) for sentences; JetBrains Mono (500-600) for kickers, sources, "illustrative" tags. Caption presets by style (`specs/caption-presets.json`): phrases, never single orphan words. Minimum on-screen size on 720 px: 22 px for labels, 14 px for source lines.

## Backgrounds, light, shadow
Paper canvas with a faint floor grid in 3D; no environment noise behind the lift. Key light rides the camera. The current skin uses softened toon sampling so shallow anatomical form stays readable, with 10% crease darkening rather than painted-on outlines. Legacy retains the old four-band/24% treatment. Soft blob shadow only under feet. Clay is a diagnostic material, not a new brand colour.

## Camera language
One move or one cut per spoken cue, never both. Front names the muscle, three-quarter is the default lift shot, side shows range and bar path, back shows lats, glutes, calves, above shows bar path and elbow flare. Orbit slowly (30-60 degrees over a set); cut on a cue. A cutaway opens on the side the camera sees. Standing figure framing for portrait: top >= y 330, floor <= y 895 (`motion-3d.md` rule 13).

## Annotation and overlay vocabulary (`film3d.js`, `scenes3d.js`)
Pins ride the skin and take the role colour; joint-angle arc with a number marked "illustrative"; dashed trail for the load's path; rep HUD (REP n / N, phase pill coloured by shortening, lengthening or holding, a tempo bar to scale); one cue card per phase; electrode + trace card for sEMG; a chip ("Under the skin") whenever the picture changes level. One idea per frame; the character and the movement stay the focus.

## Reference-informed composition and packaging

See the [Yellow Dude study](../../.claude/skills/fitness/references/yellow-dude-study.md)
for observations, source limits and adoption decisions. Adopt hierarchy and
anatomical flow, not its character, branded palette, typography or compositions.

- First read: Tibi's action or the mechanism; second: one explanatory cue;
  third: supporting context/source. The character is the explanation, not decoration.
- Use viewpoint to answer a question. Match camera/scale/phase in comparisons.
- Plan original cover concepts before final illustration; verify the pose,
  promise and short title at intended phone size. No unsupported numerical bait.
- A held pose still needs a developing annotation/path/window during narration.
- Keep palette/type and colour meanings consistent; no new runtime look,
  voice, 4K requirement or third-party software is adopted by this study.

## Motion principles
Eccentric slower than concentric, short holds at the ends, every rep the same tempo; no art swaps and no visibility switches (continuous parameters only; the 2D Tibi's arm drawings blend across their thresholds since sculpt kit 2.2.0, a mitigation, so a raise, press or curl that is the subject of the shot still goes to 3D); moves are continuous, never sampled into short linear pieces; contacts planted by IK, never hand-posed; ramps never shorter than 0.35 s (activation colour) or 1.0 s into dark cloth; frame 0 already carries the hook and the start pose; something moves in every 2-3 seconds.

## Sound
Original, synthesised (`sinew_sound.py`): a warm bed, a soft tick where a lift starts, a low thud at the end range, a spark chime only on the logo. Narration: brand voice `am_michael` at 1.05 unless a scene overrides; no whooshes on educational cross-dissolves; -16 LUFS +/- 2.
