---
name: creative-director
description: Decide what a film should look and feel like before building it. Use at the start of any studio project and whenever the direction is unclear: turn a brief into a narrative arc and beat map, pick a design profile from the knowledge base, run a structural style bake-off on one representative beat, record the decision and derive the production profile and storyboard.
---

# Creative Director

Creative judgment comes before tooling. This skill runs the planning half of the pipeline; `motion-director` reviews the result and `asset-engine` supplies assets. Builder (or Claude Code) stays the single orchestrator: this skill produces files, not new agents.

## Order of work

1. **Brief and research** (existing stages). Facts need `research.json` (`scripts/validate-research.py`). Numbers on screen must match it, including its ranges and disputes.
2. **Story: owned by `story-writer`** (subagent `.claude/agents/story-writer.md`, rulebook `.claude/skills/story-writer/SKILL.md`). The arc, beat map, hook, value-first structure, `why` per scene, planned visual beats and the narration script are written there, and it signs off in `qa/story-review.json`. Do not start the bake-off until that verdict is `complete`. This skill adds to the beat map only what is the look's job: shots, transitions (with a motivation), audio intent and asset needs, where relevant. If a beat cannot be pictured, send it back to the story-writer rather than rewriting it here.
3. **Pick candidates from the knowledge base**: `python scripts/design-dna.py kb for-beat projects/<slug>/beatmap.json <beat>` and `kb query --facet camera=push --support native`. Facets are keyword-derived: use them to retrieve, not as truth.
3b. **Pick the style template** before the bake-off: `python scripts/studio.py style recommend <slug>`, read the top pick's `avoid_when` and "viewer leaves able to" line, then `style adopt <slug> <template>`. The template fixes the scene grammar and pacing rules (`docs/style-templates.md`) and its `design_profile` and alternates are the natural bake-off shortlist. Choose by the visual job, not the subject; if the film needs something the template forbids, say so in the rationale and consider whether the template should change instead.
4. **Style bake-off** on ONE anchor beat: write a beat JSON (headline, message, key figure, supporting lines, optional real `series`), then `python scripts/bakeoff.py run <slug> --beat beat.json --profiles a,b,c --reason "<why these>"`. Shortlist 3-4 profiles that suit the content; never all nine. The candidates are different composition archetypes. The run measures structure against a re-skin control; if it prints NOT DISTINCT, the candidates were re-skins: redo with different profiles.
5. **Look at `bakeoff/sheet.png`.** Stills undersell motion-led directions; say so in the rationale. Score candidates 1-5 per criterion in a scores file, then `bakeoff.py decide --chosen <id> --by user|creative-director-agent|user-approved-agent-proposal --rationale "..."`. The user may override; record their words with `--overrides`.
6. **Derive**: `decide` writes `design-profile.json` (kind `project`, extends the registry profile, inherited values lifted to explicit `prescribed` facts). `beatmap.py storyboard <slug>` derives the timed storyboard from the measured audio timeline when it exists; fill `capabilities` with catalogue ids.
7. `python scripts/studio.py validate <slug>` checks all of it.

## Rules that do not bend

- **Measured, inferred, subjective, prescribed, unknown** are different things (`design-profile.schema.json`). Never fill an unmeasured value with a number. Extracted profiles keep qualitative facts `unknown` until an analyst has looked at frames.
- **Right medium for the job.** Charts, counters, diagrams, exact typography and anything with numbers: code. Atmosphere, texture, environments: procedural or generated plates. Say which in each beat's `assets[].strategy`; a `generate` need must name a fallback.
- **Stillness and darkness are legitimate** when declared (`intent: still|minimal|dark` on the beat). Declaring is not optional: it is what turns a QA finding into a visible waiver.
- **Do not copy** references: learn techniques from `catalogue/data/references/`, never assets, brands or exact sequences. Registry profiles carry a `weaknesses` list; read it before choosing.
- **No credentials, no live generation** here: asset acquisition goes through `asset-engine`.

## Handoffs

`story-writer`: story and script, with sign-off (step 2). Research agent: fact verification only, returns sources into `research.json`. `asset-engine`: acquires what the beat map names. `motion-director`: critique and polish after a render. One owner per project folder at a time (`scripts/session-guard.py`).
