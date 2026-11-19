# 06 · Clear the complex studio-tooling backlog

> Read `prompts/00-shared-context.md`, then `CLAUDE.md`, `AGENTS.md` and `TODO.md` in full. Track F in `prompts/03-pending-work-plan.md`. Almost all of this is pure Python, lint and runtime work, so it runs fine on Windows. Nothing here needs Kokoro. Anything that needs a render is queued for the Mac.

## The goal

The studio makes films faster and better when its tools catch problems **before** a render and stop each film from re-implementing the same helpers. These items have waited in `TODO.md` because each needs care and tests. Clear them one at a time, each with a test and a doc update, and remove the item from `TODO.md` with its outcome recorded where the behaviour now lives.

Verify each item is still open before you start. Some may have been done since 2026-11-19.

## The items (choose order by value; the first four have the most leverage)

1. **Promote repeated film helpers into the runtime** (`src/studio/`). Three films (cloud, Korea, fridge) each hand-code 620–730 lines for the same things: a typed kicker, a caption band, a stamp, a tile grid, a counter roll, per-scene drift. The fitness films repeat word-snapped cues (`build_cues.py`-style), the per-exercise card layout and the per-station Tibi pattern. Design small, deterministic, format-aware helpers (`--u`, `--safe-*`, `Studio.pick`), document them, and show one film's code shrink in a branch. Don't rewrite the films themselves without asking. Bump `Studio.version`, run `upgrade --all`, and queue re-renders.
2. **Pre-render film-time gap audit.** Visual event times (from the composition's own tweens; `tween-probe.mjs` already dumps them) against `audio/timeline.json`, flagging any narration stretch over 2 s with no visual change. Today a static hold is only caught after the render. Put it in `studio.py validate` or `studio.py script` as a warning. Test it on a synthetic composition with a known gap.
3. **`motion-qa` reads the project's style template**: waive the declared caption band, take the label floor and the static-hold limit from the template's `rules`, waive `low-contrast` and `text-echoes-narration` for a declared caption band, and make `static-hold` account for how much of the frame changes.
4. **Hook clarity lint** (`src/pipeline/hooks.py`, `studio.py hook score`, `scriptlint`): a note, not a score change, when a hook leans on a bare pronoun whose noun isn't in the same line, or a number word followed by a bare unit with no qualifier. The test case: "Nobody made a mistake. Both lost one year." scores 100/100 today and should get the note. Add it to `tests/test-short-form.py`.
5. **Pace budgets in `style check`** (`src/pipeline/style_templates.py`): read the storyboard `pace` (slow at most 0.9× `words_per_10s_max`, fast up to 1.1×).
6. **Speed-aware estimates** in the `scriptlint` sentence sheet and `beatmap.py storyboard`: scale words per second by each scene's `speed` in `src/narration.json`, and stop comparing new narration text against old clip lengths after a rewrite. Detect the mismatch and say "audio is stale" instead.
7. **A `named_things` check** in `studio.py script`: on-screen labels and narration nouns per scene beside the storyboard's `named_things`, so a name with no explanation shows up before render.
8. **Cover still export**: `studio.py build` exports the frame named in `qa/story-review.json` `packaging.cover` to `out/<slug>-<format>-cover.png`. You can write and unit-test it on Windows with a stub render. The real run is queued for the Mac.
9. **Fold the fitness lessons into the template and style**: the `fitness-explainer` template and `body-lab` style should carry the per-exercise card layout, the portrait safe-area bands for fitness (header to y 440, stage 440-850, captions below), and word-snapped cues as a runtime helper (overlaps with item 1).
10. **Proposals only** (write the options and a recommendation in `prompts/state/decisions-needed.md`; don't implement): where publishing metadata lives (`out/<slug>-publish.md` was proposed); a trimmed `tests/fixtures/` copy so `tests/test-studio.py` passes on a fresh clone (the owner forbids projects in git; a fixture that isn't a project may be acceptable, so ask); stereo vs mono mux; how a series is published as a unit; a cut-down path for a long film's reel; and whether categories drive defaults.

## Standards

- Every change has a test in the matching `tests/test-*.py` (each is a standalone script; run it directly). Keep it pure Python where possible, so it runs on any host.
- `ruff check` is clean on touched files (`line-length = 100`, rules E/F/W/I).
- Determinism rules hold for any runtime helper (`studio.py validate` lints them).
- Docs: `CLAUDE.md` command list, `docs/` guides and skill files that describe the behaviour, all updated in the same change. `TODO.md` items are removed with the outcome recorded.
- New lints start as **warnings**, never errors, until they're calibrated on real films. Say how they'll be calibrated.
- Keep both entry points working (`studio.py build` ↔ `build-project.sh`) if you touch the build.

## Deliverables

One branch per item or per small group, with tests passing, docs updated, `TODO.md` trimmed, render-queue entries for anything that needs a real render to prove, and a log entry per item: what changed, how it was verified, and what wasn't verified.
