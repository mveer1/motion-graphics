# Quality rubric for mythic films

On top of the standard gates (`studio.py validate`, `frame-review.py`, `motion-qa.py`, `qa/creative-review.json`). A film is not done until every **gate** item below is true; record the walk-through in `qa/mythic-gate.md` (who checked, when, against which source).

## Pre-render: automated
```bash
python scripts/studio.py validate <slug>
python scripts/studio.py style check <slug>          # beat gaps <= 3 s, hook <= 1.5 s, 24 words per 10 s, 6-word cards
python scripts/frame-review.py <slug> --fonts google   # then LOOK at the contact sheet
python scripts/motion-qa.py composition <slug>
```
Frame review should report no contrast warnings on text over art (use `plate: true`) and no dead stretches while narration plays.

## Gate 1: telling and stance (story-writer signs)
- [ ] The text and version are named on screen (cartouche) and in narration.
- [ ] No detail from another telling is mixed in without saying so; variants live in `research.json`.
- [ ] Every belief and meaning is attributed; no preaching, no debunking, "myth" never means "false".
- [ ] Greek or Roman names, consistently; Norse from the Eddas, not Marvel.
- [ ] Every quotation is checked against a cited translation; no invented verse.

## Gate 2: iconography (a person who knows the tradition signs)
- [ ] Each god, hero or Tirthankara shows the attributes in the tradition pack's checklist, in the right hands and colours, with the right mount or emblem.
- [ ] Each figure is identified on first appearance by name plus one emblem.
- [ ] Jain: the lanchhana matches the Tirthankara and the sect of the image (Digambara or Shvetambara); no Tirthankara fights, grants boons or protects.
- [ ] Buddhist: no human Buddha in a scene set in the aniconic period; Jatakas framed as previous lives.
- [ ] Every generated still is marked generated and passed this gate; any wrong attribute means the image is replaced, not retouched.
- [ ] Release of a Jain or Buddhist film, or any film for an audience inside the tradition, has a named reviewer from or expert in that tradition.

## Gate 3: respect in the picture (anyone can check from the contact sheets)
- [ ] No sacred image at foot level, on the ground plane, walked over, dropped, shattered, glitched or wiped.
- [ ] No bounce, squash, overshoot or whoosh on a sacred figure; no comic props in a deity's hands.
- [ ] No sexualised depiction; no gore (violence by silhouette and cut).
- [ ] No valknut, Othala rune or sonnenrad as decoration.
- [ ] No sacred chant or mantra used as a music bed.

## Gate 4: sources and credits
- [ ] Every plate is public domain or licensed, confirmed on the museum page, credited on the end card (and on screen when held over about 3 s).
- [ ] `research/plate-credits.md` matches the images on screen.

## Creative review additions
Score these 1-5 alongside the 12 criteria in `qa/creative-review.json` (notes field), with evidence:
- **Handmade:** reads as paper, lamp and the tradition's art, not as vector software (consistent shadows, deckle, fibre, one light).
- **Recognition:** a viewer can name the figure from its emblem after the revelation scene.
- **Telling:** the viewer can say which text the story came from.
- **Wonder without preaching:** the turn lands as awe; the teaching line is attributed.
A score below 3 on any of these goes back to its owner: telling to the story-writer, look to phase 3; recurring problems become anti-patterns in `mythic-tale.json` with a version bump.
