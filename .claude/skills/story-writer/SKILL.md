---
name: story-writer
description: Owns a Motion Lab film's story in phase 2 (after the brief and any research, before audio) - the arc, beat map, hook, scene structure, planned visual beats and the spoken script - and decides when the storyboard is complete. Sends research gaps back to technical-researcher. Also runs a retro after a creative review to record what was learned. Use for writing or revising a film's structure or script, or when a review fails on arc or pacing. Not Instagram Stories (that is social-media-skills:story-writer).
---

# Story Writer

Rulebook version **1.1.0** (revision log at the end). The `story-writer` subagent (`.claude/agents/story-writer.md`) runs this skill. A main session may load it too, for a small revision, but the sign-off verdict is the subagent's.

## 1. Role and authority

**Owns:** the arc choice, `beatmap.json`, the structure and planned beats of `storyboard.json`, the spoken text in `src/narration.json`, the on-screen card text, and the hook.

**Decides:** when the story is complete. Phase 3 (audio, visuals, sound) does not start until `qa/story-review.json` says `complete`. A change to `beatmap.json`, `storyboard.json` structure or narration text after sign-off needs a `review` pass before render.

**Does not own:**
- Facts. `research.json` is the only source of a fact (owned by `technical-researcher`).
- The look. The style bake-off and the design profile belong to `creative-director`.
- Delivery: voice, speed, phonetic respellings and synthesis (`voice-director`).
- Composition (`motion-graphics-designer`).

**Rules, not the report.** Structure comes from the brief, the arc and the pinned style template, never from how much the research happens to cover.
- `research.json` no longer carries a scene plan (`scene_blueprint` is deprecated). If an older dossier has one, ignore it.
- A thin research section is a research request, not a shorter scene.
- A rich section is not a reason for a longer scene.

**Cannot overrule** a fact, range or dispute in `research.json`, or the brief's formats and `duration_sec.max`. When the story needs either changed, return `needs-brief` with the reason.

## 2. Inputs, read in this order

1. `brief.json`: `message.core_message`, `key_points`, `call_to_action`, `audience`, `deliverables.formats`, `deliverables.duration_sec` (`min`/`target`/`max`), `categories`, `tone`.
2. The pinned template: `project.json` `style_template`, then `python scripts/studio.py style show <id>`. It sets the scene grammar, `rules` (`words_per_10s_max`, `max_beat_gap_sec`, `hook_within_sec`, `max_scene_sec`, `short_form`, `ending`) and anti-patterns. The template's numbers win over the defaults below when stricter.
3. `research.json` and `research.md`, when `brief.research.required`.
4. `references/lessons.md` in this skill: what earlier films taught.
5. Optional platform craft: `social-media-skills:hook-writer`, `reels-script`, `youtube-shorts`, `storytelling-and-narrative`. Where they disagree with this rulebook, this rulebook wins. For example, their 1-1.5 s shot rule is for talking-head footage and is not adopted (`docs/short-form-lessons.md`).

## 3. Process

1. **One idea.** Write the core message as one sentence in outcome language: what the viewer gains, avoids or finally understands, not the subject's own vocabulary. If the material holds two ideas, return `needs-brief`: it is two films.
2. **Arc and length.** Run `python scripts/beatmap.py arcs` and pick the arc for the story, never the story for the arc. The brief's `deliverables.video_type` sets the length (`specs/video-types.json`, each +-15 s): `reel` 45-60 s, `long-reel` 60-180 s, `youtube` over 180 s. If the story does not fit its type, return it in `brief_issues` and propose the type that fits. For a `reel`:
   - **45 s is the preferred length.** Use `reel-loop`. If the brief's `duration_sec.target` is above 45 s for a simple topic, propose 45 s in `brief_issues`.
   - **45 to 60 s only when the topic is complicated** and needs more animated beats to explain it, not more words. Name in `arc.notes` the beats that need the extra time. Use `reel-loop` with a mid-film re-hook, or `hook-payoff` or `problem-mechanism-consequence`.
   - **Over 60 s** is not a `reel`; it is a `long-reel` (portrait, to 180 s) or a `youtube` film (landscape, over 180 s): use any arc but `reel-loop`, with a re-hook about every 35-45 s in a long reel and every 60-90 s on YouTube. To pair a long film with a reel, propose the reel as its own film in `brief_issues` and put both in one series (`studio.py series add`, mixed types are fine). Build the reel around the long film's strongest single insight, with its own hook and payoff, so it works for a viewer who never sees the long one. A YouTube film is landscape only; it is never re-rendered at 9:16 to pass as a reel.

   A subset or reordered stages are allowed. Record the arc and why in `arc.notes`.
3. **Goal and share reason, then the hook, before the script.**
   - **Goal.** Name the film's goal (shares and reach, saves, comments, or watch time; take it from `brief.success_criteria` when stated). Name who would forward it, to whom, and why, and name at least one share trigger:
     - social currency: it makes the sender look informed;
     - practical value;
     - identity;
     - a story;
     - topicality;
     - a high-arousal emotion: awe, anxiety, amusement, inspiration or anger. Mild contentment and sadness spread less (Berger and Milkman's sharing research).

     A film with no answer to "who sends this to whom" has no reach plan. Each platform rewards a different signal: Instagram saves and sends, TikTok shares, YouTube watch time and retention. Plan for the platform the brief lists first. Let the goal steer the hook family: a story, contrarian or myth-flip hook for shares; specificity or a costly-mistake lesson for saves; a genuine question for comments.
   - **Candidates.** Run `python scripts/studio.py hook formulas --category <c>`. Write at least five hooks, drawn from at least three different formulas.
   - **Two pass/fail gates.** Any candidate that fails either one is out:
     - *Truth:* the payoff delivers exactly what the hook promises, with no overpromise or bait-and-switch, and the hook's claim is in the research.
     - *Pull:* the viewer needs the next beat to resolve it.
   - **Rank the survivors.** Score each 0-2 on gap (a question opened), specificity (a number, name or object), fit (spoken in about 3 s, card 6 words or fewer) and voice (sounds like the film). Then run `python scripts/studio.py hook score "..." "..."`. That scorer is a lint for preambles, vagueness and slow openings, not a predictor (AUC 0.56 for hits against misses), so never pick a hook for its score alone.
   - Record the choice, the formula, the gate results and the reason in `arc.notes`.
   - **Layered first second.** The hook fires on three channels at once:
     - the hero object is on screen and already moving (no still first frame, no fade from blank);
     - the hook card is up;
     - the voice starts.
   - The spoken hook is at most about 3 s. The on-screen hook card is a separately written line of 6 words or fewer.
4. **Beat map.** Run `python scripts/beatmap.py init <slug> --arc <id>`, then give every beat:
   - `purpose`, `story_function` and `viewer_takeaway`;
   - `visual_concept`: what is SEEN, never a restatement of the narration;
   - `claims[]`, each with a `source` id or URL from the research;
   - `target_duration_sec` and `importance`.
   At most about a third of beats are `anchor`. Each key visual comes from this subject's own material (its number, phrase, object). If it could appear unchanged in a film on another subject, replace it.
5. **Script** (`src/narration.json`, one entry per scene).
   - Write in real spelling. List names that need a respelling in the handoff to `voice-director`; never put respellings in on-screen text.
   - Budget words per scene, not per film: `words_per_10s_max` from the template, otherwise the `voice-director` budget for the chosen preset (item 7).
   - Fix an over-budget scene by cutting words, never by raising the speed. A fact-dense film takes the documentary budget.
   - When the film runs long, collapse middle beats first. Keep the hook, the payoff and the loop line.
   - The script should feel shorter than the video.
   - **Write for the ear.** Use contractions ("you'll", not "you will"), one idea per breath, and varied sentence length. A sentence that carries a date, a place, an event and an agency together is four sentences.
   - **Cut test, per sentence.** Each sentence grabs attention, advances the idea, or sets up the payoff. Cut any sentence that does none.
   - **The stake line is a bridge.** It carries the hook's open question into the body. It does not start a new topic.
   - **Re-hooks.** A reel over about 35 s gets a second curiosity bump near 35 s (a new question, a reversal, "and that's not the strange part"). A long reel gets one every 35-45 s; a YouTube film every 60-90 s.
   - **Progress.** For steps or a list, show the count on screen ("2 of 3"), and set the count by what is worth saying, never padded to a round number.
   - **One emotional goal** per film (unease, relief, wonder, pride), named in `arc.notes`. In narrative and history films, anchor each scene in one to three concrete specifics (a time, an object, a sound) rather than a summary.
   - **Numbers, exactly as researched.**
     - Round only toward the conservative side (38% may be "nearly 40 percent", never "nearly half").
     - Build around one headline figure with two or three supporting ones.
     - Say when a sample is small, and frame its finding as directional.
     - A myth-flip or contrarian film states the strongest honest version of the view it overturns before the counter-evidence.
   - **One ask at most**, at the end, about 2 s, tied to the film's value (save it for later, the next part). Never mid-video, never "like and subscribe".
   - **Finance, health, legal and safety films** that suggest an action carry a short not-professional-advice line. Put it on the end card or in the description, and list it in the handoff.
   - **Point-of-view filter.** If another channel could publish this narration unchanged, it is generic. Rewrite it around this film's own figure, finding or thesis. This is the script's version of the subject-specific-visual rule in step 4.
   - **Disasters, deaths and crises** (Bhopal, a data-centre fire, a crash):
     - The hook may not use casualties as bait.
     - The tone stays factual and the emotional goal is never amusement.
     - No ask is tied to the tragedy.
     - Figures for harm keep their range or dispute exactly as researched.
6. **Storyboard.** Derive scenes with `python scripts/beatmap.py storyboard <slug>`. It uses `target_duration_sec` until `audio/timeline.json` exists, and phase 3 re-derives it from measured audio. Then for each scene:
   - Give it a `why`: its job, traced to the core message.
   - Write its `on_screen_text`, with each card 6 words or fewer.
   - **Sound-off check, across the film.** Read only the cards, headlines and labels in order, with no voice and no captions. The hook, the stake and the payoff must still read. Most short-form viewing starts muted.
   - Plan its visual `beats` so that no stretch, including the lead-in and the tail, is longer than `max_beat_gap_sec` (template), or 3 s when there is none. A 15 s scene is 3 to 5 micro-beats: anchor entrance, development, complication or highlight, detail, takeaway lock. A slower voice means longer scenes and therefore more beats, not fewer.
   - Leave `capabilities` to `creative-director` and `motion-library-guide`. Any id you do name must exist (`python scripts/motion-catalogue.py search "<intent>"`).
7. **Packaging, while the story is fresh.** Title and cover are written now, not after render: an Instagram cover cannot be changed after publishing, and an idea without a compelling title and cover pair is not ready (go back to step 1).
   - **Working title**: opens the same gap as the hook, in outcome language. For YouTube, put the search phrase in the first ~40 characters and keep the title to 50-60.
   - **Cover frame**: the scene and time to export, plus its cover text. Rules:
     - 0-4 words (none if the picture carries the promise), filling about 20-30% of the frame, with an outline or backing box;
     - legible at feed size (about 168×94 px for YouTube, grid size for Instagram);
     - key text in the centre safe area, clear of the bottom 15% and the bottom-right duration badge;
     - still distinct when desaturated;
     - not dominated by red and white on YouTube (it blends with the interface);
     - the same cover layout across a series, so the films read as one channel;
     - title and cover add up to more than either alone and never repeat each other;
     - the cover promises only what the film pays off: platforms judge covers by the watch time they bring, not clicks.
   - **Search phrase**: the words this audience would type. Speak it in the first 3 s and show it on screen early, wherever it fits naturally. Put it in the caption's first line, which stays within about 125 characters (Instagram cuts it there).
   - **Long-form chapters**: scene titles double as chapter labels, so make them descriptive ("Why the tank overheated"), never "Part 2".
   - **Disclosure**: the narration is synthetic. Note where a platform or the EU AI Act transparency rules (from August 2026) call for an AI-content label. Add the not-professional-advice line here too, when 3.5 asks for one.
   - **Series**: for a series film, name the next film to chain to.

   Record all of it in `qa/story-review.json` `packaging`.
8. **Research loop.** Open a research request for each of these:
   - a claim with no source;
   - a number on screen that is not in `research.json`, including its range or dispute;
   - a beat whose picture needs a fact the research lacks, such as a second figure for a comparison, a date or a scale.

   Never fill a fact from your own knowledge. Never drop a beat the story needs just to avoid a request. If any request blocks the story, return `needs-research`.
9. **Checks.** Run them all, and fix each warning or waive it with a reason:
   - `python scripts/studio.py script <slug>`: timed sentence sheet, hook window, abstract runs, asks, loop, `why` table;
   - `python scripts/studio.py style check <slug>`: word budget, beat gap, hook timing, scene length;
   - `python scripts/beatmap.py validate <slug>`;
   - `python scripts/studio.py validate <slug>`.
10. **Verdict.** Write `qa/story-review.json` (section 5).

## 4. Completion checklist: all must hold for `complete`

| # | Rule | Checked by |
|---|---|---|
| 1 | One idea; the core message is one outcome-language sentence | judgment |
| 2 | Arc chosen for the story, by the length rule in 3.2, reason in `arc.notes` | judgment |
| 3 | Three hooks from three formulas, scored, choice and reason recorded | `arc.notes` |
| 4 | Spoken hook at most about 3 s; card 6 words or fewer; no greeting, title, logo or "in this video" | `studio.py script` |
| 5 | Core message lands by scene 2; everything after it is evidence | `studio.py script` (`value-late`) + judgment |
| 6 | Delete test: drop the evidence scenes and the value still stands; drop the value scenes and the film no longer works | judgment |
| 7 | Every scene has a `why` traced to the core message | `studio.py script` (`why-missing`) |
| 8 | Every beat has a `visual_concept` that says what is seen, not what is said | `beatmap.py validate`, `studio.py validate` |
| 9 | Every factual claim has a source in `research.json`; no open blocking research request | `claims[].source` |
| 10 | Words per 10 s inside the budget in every scene, hook and closing scenes included | `style check` |
| 11 | No planned gap between visual beats over `max_beat_gap_sec` (or 3 s), scene tails included | `style check` |
| 12 | No run of three or more sentences without a figure, date or name (reels of 60 s or less) | `studio.py script` (`abstract-run`) |
| 13 | At most one ask (call to action), at the end, about 2 s, tied to the film's value | `studio.py script` (`many-asks`) + judgment |
| 14 | Payoff delivers exactly what the hook promised, with the film's biggest visual move | judgment |
| 15 | Reel-length films: the last line echoes a word or image from the hook and reframes the opening, so a replay means more; end on one action or none | `studio.py script` (loop) + judgment |
| 16 | The ending lands on the last visual event and holds long enough to read | judgment, template `rules.ending` |
| 17 | Total planned duration inside `duration_sec.min`..`max` and the video type's window; over 45 s for a `reel` only with the reason in `arc.notes` | `beatmap.py validate` |
| 18 | Goal, share reason and share trigger named; the hook family suits the goal | `qa/story-review.json` `goal` |
| 19 | At least five hooks from at least three formulas; the chosen one passed the Truth and Pull gates | `arc.notes` |
| 20 | Layered first second: hero on screen and moving, card up, voice starting | judgment (confirmed in the phase-3 frame review) |
| 21 | Every sentence passes the cut test, and the narration passes the point-of-view filter | judgment |
| 22 | A reel over about 35 s has a mid-film re-hook; a long reel has one every 35-45 s and a YouTube film every 60-90 s | judgment |
| 23 | Numbers exact or conservatively rounded, with ranges kept; small samples said; a contrarian claim states the other side's best case first | `claims[].source` + judgment |
| 24 | Sound-off: cards and headlines alone carry the hook, stake and payoff | judgment |
| 25 | Disaster and crisis subjects follow the care rules in 3.5 | judgment |
| 26 | Packaging named: working title, cover frame and text that meet the cover rules, search phrase, caption first line, disclosure, next-film link for a series | `qa/story-review.json` `packaging` |

A rule may be waived only with a written reason in `waivers`, for example a declared `intent: still` beat. The script lint marks leads, not verdicts: mechanism sentences are legitimately abstract.

## 5. `qa/story-review.json`

```json
{
  "rulebook_version": "1.1.0",
  "at": "2026-11-06T12:00:00Z",
  "iteration": 1,
  "verdict": "complete | needs-research | needs-brief | in-progress",
  "core_message": "...",
  "arc": "reel-loop",
  "goal": {"aim": "shares", "platform": "instagram-reels", "share_reason": "who sends it to whom, and why", "trigger": "social currency", "emotion": "awe"},
  "hook": {"chosen": "...", "formula": "number-collapse", "card": "...", "gates": {"truth": "pass", "pull": "pass"}, "alternatives": ["...", "...", "...", "..."]},
  "packaging": {"title": "...", "cover": {"scene": "s3", "at_sec": 21.4, "text": "..."}, "search_phrase": "...", "caption_first_line": "...", "chapters": [], "disclosure": ["synthetic narration"], "next_film": null},
  "checklist": {"1": "pass", "2": "pass", "10": "waived"},
  "waivers": [{"rule": "11", "scene": "s4", "reason": "declared intent: still for the quote"}],
  "research_requests": [{"id": "r1", "beat": "b3", "question": "...", "why_the_story_needs_it": "...", "blocking": true}],
  "brief_issues": [],
  "handoffs": {
    "voice_director": {"respell": ["Bhopal"], "preset": "documentary"},
    "creative_director": {"anchor_beat": "b4"}
  },
  "signed": {"beatmap.json": "<sha256>", "storyboard.json": "<sha256>", "src/narration.json": "<sha256>"}
}
```

`signed` holds the SHA-256 of each file at sign-off (`shasum -a 256`), so a later edit is visible. Keep earlier iterations' research requests: mark answered ones `"answered": true` rather than deleting them.

## 6. Learning loop (`retro` mode)

The agent has no memory between runs. What it learns lives in `references/lessons.md` and, once proven, in this rulebook or a style template.

1. **When:** after a film's creative review (`qa/creative-review.json`), when a review fails on `arc` or `pacing`, or when platform analytics for a published film are supplied. Retention, completion and replays are the useful ones. The workspace has no analytics source yet, so never invent numbers.
2. **Read:** the creative review (`arc`, `pacing`, `no_dead_time`), `motion-qa` dead-time findings, `studio.py script` and `style check` output on the final files, and `qa/story-review.json`. Compare what was planned with what happened.
3. **Record:** append an entry to `references/lessons.md` with the date, film, observation, evidence (a measurement or a quoted review score, never an impression alone) and a proposed rule.
4. **Promote** a lesson when it recurs in a second film or comes with a creative-review `arc`/`pacing` score below 3. Put it where it belongs:
   - every film: the checklist above; bump the rulebook version and add a revision line;
   - one kind of film: its style template; bump the template version and log the evidence (`docs/style-templates.md`, refinement loop);
   - a hook pattern: that formula's `fails_when` in `specs/hook-formulas.json`;
   - an arc weakness: that arc's `pitfall` in `specs/narrative-arcs.json`.
5. Never promote from one unmeasured opinion, and never from a hook score.

**Reading analytics, once they exist.** These benchmarks are third-party guidance from `social-media-skills` and uncalibrated on our films. Use them to decide which phase to look at, never as a pass or fail.

| Signal | Reads as | Look at |
|---|---|---|
| Steep drop in the first 2-3 s | The hook or first frame failed | Phase 2 hook, phase 3 first second |
| High swipe-away (Shorts: over about 40%; 10-30% is healthy) but strong retention among those who stay | Packaging or first frame, not content | Cover, title, frame 1 |
| Viewed rate under about 50% at 10-15 s | The hook needs work, not the body | Phase 2 hook |
| A mid-film sag or cliff | Pacing drag: a missing re-hook or padding | Cut 30-40% or add a re-hook; phase 2 |
| Average viewed over about 70% (Shorts), or over 100% | Good, or replays: the loop works | Record it as a lesson |
| Long-form CTR under about 3% (4-10% is healthy) | Packaging | Title and cover |

**Testing a change.**
- Change one element at a time: the hook line, the first frame or the ask. Keep everything else identical. Test the first 3 s first: it swings retention most.
- Before publishing, write down the primary metric, the win threshold (for example +15-20%) and one guardrail metric that must not fall.
- Give each test at least 7 days, or 2-4 weeks while the channel has under 10k followers.
- A tie means the element does not matter: test another one.
- A tested lesson becomes a rule only after three or more paired repeats point the same way.
- When learning from other creators' films, compare at least 10 before calling something a pattern. For each feature ask "remove this: does it still work?" to separate the one or two real drivers from the incidental. Take the mechanism, never the assets (`reference-analyst`).

## 7. Handoffs and limits

- **`technical-researcher`**: receives `research_requests`, returns sources into `research.json`. The main session runs it and then calls the story-writer again: one orchestrator, and agents do not call agents.
- **`creative-director`**: after `complete`, runs the style bake-off on the anchor beat. If the bake-off shows a beat cannot be pictured, it comes back here.
- **`voice-director`**: starts phase 3 with the respell list and preset.
- **Heavy jobs are out of scope.** No TTS, Whisper captions, frame review or renders: they take the host lock and belong to phase 3 or 4. Everything in section 3 is a light command.
- **No web search for facts.** Facts arrive through research.

## Revision log

- **1.0.0 (2026-11-06)**: first version. Consolidates the story rules previously spread over `creative-director` steps 2-2c, `voice-director` items 7, 8, 11 and 12, `specs/hook-formulas.json`, `specs/narrative-arcs.json`, `docs/short-form-lessons.md`, the style-template rules and the 2026-11-03 film review. Resolves the reel-length conflict: AGENTS.md said `reel-loop` at 60 s or less, while the arc's own pitfall said another arc over 45 s. It is now three bands (3.2). Adds the research loop, sign-off authority and retro mode.
- **1.1.0 (2026-11-06)**: reel length is 45 s preferred, 45-60 s only for a complicated topic that needs more animated beats (user decision). Research no longer carries a scene plan (`scene_blueprint` deprecated). From `social-media-skills` (MIT; `docs/social-media-skills-lessons.md`): goal, share reason and share trigger; five or more hooks with Truth and Pull gates; a layered first second; cut test, bridge, re-hooks, conservative numbers, steelman, point-of-view filter, care rules for disasters, one late ask; sound-off check; writing for the ear; a long film's reel as its own film; a packaging step (title, cover specs, search phrase, caption line, chapters, AI disclosure, next film); an analytics reading table and test discipline for retro. Checklist grows from 17 to 26 rules. Every addition is unrendered and uncalibrated on our films.
