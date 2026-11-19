# 07 · Create AI skills for the work we keep repeating

> Read `prompts/00-shared-context.md` and `.claude/skills/workspace-steward/SKILL.md` (it owns placement and registration of every new component). Track G in `prompts/03-pending-work-plan.md`. Best done after a first pass of `01`, `02` and `04`, so the skills encode repetition you have actually lived through rather than guessed at.

## The goal

Every time an agent re-derives the same procedure (which commands, in which order, with which traps), the owner pays for it in tokens, time and mistakes. Find the procedures that recur in this workspace and turn the worthwhile ones into **skills**: short, accurate instructions (plus small deterministic scripts where it helps) that any capable model can load and follow. Also decide when a skill is the wrong answer, and a script, a check or a doc fix is better.

## How to find the repetition (evidence, not guesses)

Look at what was actually done, in all of these:

- `prompts/state/log.md` from the Windows sessions, and `logs/build-timings.jsonl`
- `docs/fitness-studio.md`, `motion-3d.md` and every `qa/production-report.md` that exists
- the git history (`git log --stat`, the messages of fitness and runtime commits)
- `TODO.md` and `docs/*-lessons.md`
- the existing skills, so you don't duplicate them. Already present in `.claude/skills/`: `fitness` (orchestrator), `fitness-anatomy`, `fitness-animation`, `fitness-qa`, `fitness-publish`, `short-form`, `mid-form`, `long-form`, `story-writer` (also an agent), `creative-director`, `caption-designer`, `voice-director`, `video-assembler`, `motion-*`, `parallel-session`, `workspace-steward`, `agy`, `earshot`, `real-sfx`, `asset-engine`, `reference-analyst`, `technical-researcher`, the `gsap-*` set, and more. **Extending an existing skill is usually better than adding a new one.**

A procedure deserves a skill when it recurs (three or more times, or certainly will), has an order or traps that agents get wrong, and isn't already fully automated by one command. If one command would do it, write the command instead (and maybe a one-line pointer in an existing skill).

## Candidates seen so far (validate each one; drop or merge freely)

| Candidate | What it would encode | Notes |
|---|---|---|
| **kit-release** | the runtime-change ritual: bump `Studio.version` with a changelog line, `studio.py upgrade --all`, node checks, the fitness/anatomy/rig tests, governance, catalogue validate, docs touched, render queue updated | done by hand in every session that touched the kit; easy to forget a step |
| **tibi-look-loop** | the closed loop for character work: matrix slice → change → numeric checks → before/after sheet → look and describe → decide | the core of `01`/`02`; the "look at the frames" discipline written down |
| **3d-exercise-port** | the 9-point standard in `04` as a checklist with commands | may belong inside `fitness-animation` instead |
| **host-probe** | which tools exist on this machine, what can run here and what must be queued; Windows vs Mac differences; portability gotchas | lets any session start honest in one step |
| **render-handoff** | writing and draining `prompts/state/render-queue.md`: exact commands, branch, what to look at; on the Mac, the verify → render → QA → report loop | links `00` §6 and `08` |
| **owner-decision-pack** | turning an open question into options, sheets, cost, recommendation; where it is recorded; never deciding it | recurs in every track |
| **motion-only-qa** | building the temporary `qa-motion.html`, rendering a draft to scratch, running `motion-continuity.py`, deleting the file so the render fingerprint is untouched | a known trap (a file left in `src/` changes the fingerprint) |
| **progress-recording** | where each kind of outcome goes (`TODO.md`, docs, `catalogue/project-progress.md`, `prompts/state/`), checking all worktrees before a status report | an owner rule that agents keep missing |

## Standards for every skill

- Follow the format of the existing skills: a folder in `.claude/skills/<name>/` with `SKILL.md` (frontmatter `name`, `description` that says **when to use it** in the words a user would type, and `version`), optional `references/` and `scripts/`.
- Register each one as a catalogue record in `catalogue/data/skills/<name>.json` with status `experimental`, matching the schema in `catalogue/schemas/` and the style of neighbouring records. Run `python scripts/motion-catalogue.py validate` and `python scripts/workspace-governance.py`.
- **Short and true.** A skill is read every time it's loaded, so every line costs tokens. Prefer a table and the exact commands over prose. Point to the docs that hold the detail instead of copying them. Every command in it must have been run by you, on this machine or with the host noted.
- Scripts in a skill are deterministic, have `--help`, work on macOS and Windows (or say which), and never take the heavy-job lock implicitly unless they're documented as self-locking.
- Wire it in: the `fitness` orchestrator's routing table, `CLAUDE.md` (only if it's a top-level workflow), and the parallel-session or steward docs where relevant.
- **Test it like a user would**: start a fresh session (or a fresh subagent if the owner allows), give it a realistic task that should trigger the skill, and check that it loads the skill and follows it correctly. Record the trial in the log. Revise until it does.
- Delegation: if the `agy` skill works on this host, note where a skill should hand bulk reading or drafting to it (per `CLAUDE.md`'s delegation rules: never renders, QA verdicts, creative judgment or secrets).

## Deliverables

- an evidence table in `prompts/state/skills-analysis.md`: each recurring procedure, how often it was seen and where, and the decision (new skill, extend skill X, script, doc fix, or nothing)
- the skills themselves, registered, wired in and trialled
- a short note to the owner listing what was created, what was merged into existing skills, and what you deliberately didn't make a skill and why
