# TODO

Open decisions and follow-ups. Delete an item when it is done; record the outcome in the relevant spec or doc.

## Decide

- [ ] **Define what a "visual style" is.** Today a style is a catalogue record (`catalogue/data/styles/*.json`) with colour tokens, typography, texture, motion personality and a stylesheet in `src/studio/styles/`. Open questions: is a style only look (tokens), or also motion language and layout rules? How does it relate to a design profile and to a creative direction in `brief.json`? Who may create one and what evidence promotes it from `experimental`?
- [ ] **Review the initial category tags on styles.** They are a first guess from each style's `suitable_for` text. Revisit once the style definition above is settled. Current tags:
  - abstract-geometric: mathematics, technology
  - archival: history, news
  - cinematic-dark: storytelling
  - dark-tech: technology
  - data-journalism: finance, news
  - mixed-media: storytelling
  - paper-cut: storytelling
  - sci-viz: science, technology
  - editorial-light, swiss-minimal: untagged (general-purpose, fit any category)

## Follow up

- [ ] Backfill `categories` in the `brief.json` of existing projects (`studio.py validate` warns for each one without).
- [ ] Decide whether categories should drive defaults (suggested narrative arc, suggested style) or stay tags only.
- [ ] Decide how a series is rendered or published as a unit (shared intro/outro, cross-part recap, naming of `out/` files). Today `series.json` only records membership and checks consistency.
