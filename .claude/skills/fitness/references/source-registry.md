# Source registry: external resources evaluated (2026-11-08)

Policy: prefer public domain, then CC0, then explicit commercial permission, then attribution licences whose terms we can meet. A resource with unclear or non-commercial terms is **excluded** from the production library and noted here. Licences were read on the date shown; re-check before any new use. Machine-readable licence and provenance per asset: `assets/fitness/manifest.json`.

## Decision summary

The production library is **original vector art and code** drawn for the 2D HyperFrames pipeline: Tibi, 19 muscle shapes, 16 bone shapes, anatomy plates, equipment and environments. External resources supply **facts** (anatomy, study results) and one **public-domain dataset** used for cross-checks. No third-party image, model or animation is in the library.

## Evaluated resources

| Resource | What it offers | Licence / terms (checked) | Formats | Commercial use | Decision |
|---|---|---|---|---|---|
| **Z-Anatomy** (z-anatomy.com, GitHub Z-Anatomy) | Full 3D atlas (muscles, bones, organs) as a Blender template | CC BY-SA 4.0; meshes derived from BodyParts3D (CC BY-SA 2.1 JP); some third-party add-ons are CC BY-NC or CC BY-NC-SA with no per-mesh licence map | .blend | Allowed for the BY-SA parts, but **share-alike** may extend to a derived video; the NC add-ons are not allowed; no per-mesh map | **Excluded** from the production library. Reference viewing only. Revisit with legal advice if a 3D pipeline is added; then use only the BodyParts3D-derived meshes and publish the derivatives under BY-SA. |
| **BodyParts3D / Anatomography** (DBCLS) | Segmented 3D human anatomy | CC BY-SA 2.1 Japan | OBJ | Yes, with attribution and share-alike | **Not used now** (no 3D pipeline). The first candidate for a future Blender path, with share-alike handled. |
| **NIH 3D** (3d.nih.gov) | Many anatomy and molecule models | The uploader chooses each model's licence; NIH does not enforce terms; many are PD or CC BY, some restrictive | STL, OBJ, GLB, WRL | Per model | **Not used.** Allowed case by case: record the model's own licence page in the manifest before use. |
| **Ana3D** (ana3d.app) | Interactive 3D anatomy app | Commercial app; no open asset licence found | App | No | **Excluded** (reference viewing only). |
| **OpenStax Anatomy & Physiology 2e** (openstax.org, Betts et al.) | Textbook text and figures | **CC BY-NC-SA 4.0** (the section pages state it; not CC BY) | Web, PDF | **No** (non-commercial) | **Facts only.** Used to check anatomy and sizes (§10.2: fibre up to 100 µm and 30 cm, myofibril about 1.2 µm, sarcomere about 2 µm). No figures or text copied. |
| **Gray's Anatomy 1918** (Wikimedia Commons scans) | Classic anatomy plates | Public domain (US, pre-1929) | PNG, JPG | Yes | **Reference** for shape checks. Not imported (the style does not match; old terminology). |
| **Servier Medical Art** (smart.servier.com) | Medical and cellular illustrations | CC BY 4.0, attribution "Servier Medical Art" with a link | SVG, PPT, PNG | Yes, with attribution | **Approved source, not used yet.** Our cell plates are original; use SMART for complex organs when needed, with attribution in the description and the manifest. |
| **free-exercise-db** (github.com/yuhonas/free-exercise-db) | 800+ exercises: muscles, instructions, levels | **Unlicense** (public domain) for the data; the **images** have no stated licence or origin | JSON, JPG | Data yes; images unknown | **Data imported** (13-record extract in `assets/fitness/sources/free-exercise-db/` with its LICENSE) as a cross-check of muscle lists. **Images excluded.** |
| **RepDB free edition** (github.com/RepDB/exercise-dataset) | 701 exercises, multilingual, illustrations | Free for in-app commercial use **with a visible attribution link**; no redistribution as a dataset; images may not be used for generative AI | JSON, WebP | Restricted (in-app, attribution, no redistribution) | **Excluded.** The terms target apps, not videos, and the redistribution and AI clauses conflict with a reusable library. |
| **ExerciseDB / AscendAPI** (oss.exercisedb.dev) | 1,500+ exercises with GIFs via an API | Code AGPL-3.0; GIF licence not stated; GIF origin unclear | REST, GIF | Unclear | **Excluded** (commercial rights to the media cannot be confirmed). |
| **wger** (github.com/wger-project/wger) | Exercise DB and API | Code AGPL-3.0; exercise data "Creative Commons, see individual entries" | REST, JSON | Per entry | **Not used.** Allowed only per entry with that entry's licence recorded. |
| **PubMed / Europe PMC** | Citations, abstracts | Abstracts are publisher copyright; citing and quoting short findings is fine | Web, REST | Citing yes | **Research source.** Europe PMC REST is the verified fetch path. |
| **Cochrane Library, ACSM, NSCA** | Reviews and position stands | Publisher copyright | Web, PDF | Citing yes | **Research source.** |
| **Blender** (blender.org) | 3D modelling, rigging, rendering | GPL-2.0+ (outputs are yours) | App | Yes | **Evaluated, not installed** (see `production.md`): not on the render host; 8 GB RAM and the one-heavy-job rule; the pipeline is 2D. |
| **Google Fonts copies of Outfit, Inter, JetBrains Mono** | Web fonts for sheet previews in plain Chrome | OFL-1.1 | CSS/WOFF2 | Yes | **Preview only** (`assets/fitness/sheets/`); renders use the HyperFrames-bundled copies. |

## Scientific sources used by the demo film

Wackerhage 2019 (J Appl Physiol, review); Damas 2016 (J Physiol, 10 men, 10 weeks); MacDougall 1995 (Can J Appl Physiol, 6 men); Phillips 1997 (Am J Physiol, 8 adults); Biolo 1997 (Am J Physiol, 6 men); Drummond 2009 (J Physiol); Schoenfeld 2017 (JSCR, 21-study meta-analysis); Morton 2018 (BJSM, 49 RCTs, 1,863 participants); Jorgenson 2020 (Cells, scoping review); OpenStax A&P 2e §10.2. Full citations, DOIs and verification: `projects/how-muscles-grow/research/dossier.json`.

## Adding a source

### Communication reference: Yellow Dude (2026-11-20 UTC)

[Source ledger and adoption guide](yellow-dude-study.md): nine official web
pages, two inspected public layouts and the supplied character still.
The current production article is accessible; its process descriptions are
publisher-reported, not independently audited. Full videos/audio were not inspected.
Use communication principles only. Licence for asset reuse is unestablished:
exclude character, branding, art, voice, scripts, footage, product UI and exact
compositions. No source artwork was imported. Article science still requires
independent primary-source verification; expert involvement is not blanket validation.

### Asset intake procedure

1. Read the licence page yourself and record the URL and date.
2. Commercial use, modification and redistribution must all be allowed (or the use must be facts only).
3. Add a row here, then the asset with `source` and `license` fields in the manifest, and the upstream LICENSE file beside any downloaded file (`assets/fitness/sources/<name>/`).
4. Downloads go into their own new folder; open them only as data (never run their scripts).
