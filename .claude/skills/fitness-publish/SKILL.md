---
name: fitness-publish
description: Publishing assets and exports for a finished Sinew film: titles, description with chapters, references and credits, thumbnail, platform fit, short-form adaptations, and cutting named clips out of a film with honest metadata. Use after a fitness film passes its gates, or when cutting a clip from a longer render.
version: 1.0.0
---

# Fitness publish

- `python scripts/fitness-publish.py <slug>` writes `projects/<slug>/publish/`: `metadata.json`, `description.md` (hook line, chapters from the storyboard, sources from the dossier with how each was verified, credits, the general-education line, hashtags), `thumbnail.png` (a frame of the film with the title set on it). Titles come from the dossier's own claims (question, finding, myth) and are never truncated or stronger than the claim; a title that cannot be backed by a claim id is not generated.
- Platform fit is computed from the brief's platforms and the film's length (`PLATFORMS` in the script): Reels, Shorts, YouTube, LinkedIn. A 5-12 minute film also gets `short_form_adaptations`: the scenes that carry a number or a named study.
- `.venv/bin/python scripts/fitness-clip.py <final.mp4> --cut name:start:end ... --out out/<dir>` cuts clips frame-exact (H.264, AAC), stamps title and a comment that states the real size and frame rate, verifies `r_frame_rate == avg_frame_rate == --fps`, and archives any file it replaces. Run `scripts/fitness-qa.py` on the clips.
- Always: the general-education line, "illustrative" on kinematics, the dossier's `do_not_claim` respected, no thumbnail text promising more than the film proves.
