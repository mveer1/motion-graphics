# Imagery: public-domain plates, generated stills, credits

Order of preference: **(1) the tradition's own art in public domain** from a museum, **(2) code-drawn paper** (the kit), **(3) generated stills**, flagged and iconography-checked. Never stock photographs of people at worship, never film, game or comic portrayals.

## 1. Search and fetch

```bash
python scripts/myth-sources.py search "Krishna Govardhan" --source cma,met,commons --limit 8 \
    --culture "India|Rajasthan|Pahari" --out projects/<slug>/research/plates.json
python .claude/skills/collage-design/scripts/fetch.py --json projects/<slug>/research/plates.json \
    --out projects/<slug>/src/assets/plates --attributions projects/<slug>/research/plate-credits.md
python scripts/assets.py import <slug> projects/<slug>/src/assets/plates/<file> --license-status verified
```

Plates must live under `src/` (HyperFrames serves only the project's `src/`); reference them as `assets/plates/<file>` in `M.plate({src: ...})`.

| Source | Status (checked 2026-11-23) | Licence signal kept | Notes |
|---|---|---|---|
| Cleveland Museum of Art (`cma`) | Live, no key | `share_license_status == "CC0"` | Best metadata: culture and creators; `images.web` 672x900 |
| The Met (`met`) | Live, no key; v1 search retired 2026-10-01, the tool uses v1.1 | `isPublicDomain == true` and an image | Search returns ids only and matches any field: expect noise ("Hawks for Cranes" for "Shiva") |
| Wikimedia Commons (`commons`) | Live; descriptive User-Agent required | `LicenseShortName` public domain or CC0; CC BY-SA dropped | Broad but noisy ("Odin" finds a battleship): add the tradition and medium ("Odin Sleipnir manuscript") |
| Art Institute of Chicago | Blocked to scripts by Cloudflare | `is_public_domain` | Use the weekly data dump if needed; not wired |
| Smithsonian Open Access | Needs a free api.data.gov key | `usage.access == "CC0"` | Freer/Sackler is strong for Asian art; not wired (no keys in the workspace) |
| Openverse | 200 anonymous requests a day | `license` cc0/pdm | Last resort |

Sources: [Met API](https://metmuseum.github.io/), [CMA API](https://openaccess-api.clevelandart.org/), [Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy), [AIC api-data issue 9](https://github.com/art-institute-of-chicago/api-data/issues/9), [Smithsonian Open Access](https://github.com/Smithsonian/OpenAccess).

**Check every image by eye** before it goes in: is it the figure the record says (the tradition pack's checklist)? Is the object itself respectful to show this way (no deity image placed low or cut through)? Open the museum page and confirm the licence there; the API flag is a filter, not proof. Set `MOTIONLAB_CONTACT` to your e-mail or URL so archives can reach you.

## 2. Preparing plates
- Duotone everything to the style's ink and paper (`M.plate` does it by default) so plates from different museums sit together; pass `duotone: false` only for a deliberate full-colour reveal (gold leaf, a painted folio).
- Keep the long side at 1600 px or less (render memory).
- Cut-outs: knock the subject out to a PNG with alpha (collage-design `scripts/knockout.py` or `cut.py`), then `M.plate({frame: 'cutout'})` draws the sticker edge and contact shadow.
- Windows for the sacred: `frame: 'niche'` (temple niche), `'disc'` (medallion), `'rect'` (folio page).

## 3. Generated stills (allowed, flagged)
Use only when no public-domain image shows what the scene needs (a composition, an angle, a moment the tradition never painted).
1. Generate through the asset engine so the request is logged: `python scripts/assets.py generate <slug> --task text-to-image --provider kie --prompt "..."` (needs `KIE_API_KEY` in the environment; never in a file).
2. The prompt states the iconography explicitly from the tradition pack (attributes, number of arms, mount, emblem, colour, clothing) and the art form to follow ("flat Pattachitra style, black contour, conch-white ground"), and asks for **no text, no watermark, no modern objects**.
3. Walk the tradition pack's checklist on the output. Typical failures: wrong number of arms, wrong weapon in the wrong hand, a missing or wrong lanchhana, a Western halo on an Indian figure, Marvel armour on Thor, a winged helmet.
4. Record it as generated: asset record `source: generated`, and in `research.json` images. The end card says "Some images generated and checked against [source]".
5. Reject rather than retouch an image that gets a sacred attribute wrong.

## 4. Credits
- Every plate's `attribution` (written by `myth-sources.py`) goes into `research/plate-credits.md` and the end card; a plate on screen for longer than about 3 s gets a `M.credit` line ("The Met, 38158 · Public domain").
- The source cartouche names the text; credits name the images; a generated image is labelled as generated.
