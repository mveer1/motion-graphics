# Lessons from `social-media-skills` (adopted 2026-11-06)

`social-media-skills` 1.0.1 (106 skills, MIT, by Frank Heijdenrijk; not an Anthropic plugin) is installed as a Claude Code plugin. This note records what was learned from it for a studio that makes narrated motion-graphics explainers and reels, where each lesson now lives, and what was left out. Nothing was copied: the rules were restated in our own words, and only short phrases were quoted while checking them.

## How it was read

- **Scope.** 28 of the 106 skills are relevant to making, structuring, packaging or improving narrated motion-graphics films, about 80k words. The rest cover publishing tools, community management, DMs, ads, live-action and other surfaces.
- **Extraction.** The 28 were read in four themed bundles: script and hook; story and long-form; learning and analytics; packaging and audio. Gemini (`agy`, `gemini-3.8-flash-high`) extracted every concrete rule that is new to us, sharper than ours or in conflict with ours, each with a verbatim quote. That gave 156 rules. The bundles sit in the untracked `reference/analysis/social-media-skills/`.
- **Checking.** Every quote was matched against its source file: 150 of 156 verbatim, and the other six checked by hand (formatting differences only). Five rules that need a person on camera were dropped.
- **Selection.** Done by Claude, not Gemini, against this studio's constraints: no live action, Kokoro voice, local render, no analytics source yet.

## What it taught, in one paragraph

Our rules were strong on the inside of a film: hook formulas, value by scene 2, word budgets, beat spacing. They were thin on everything around it. Nothing named *why a viewer would send the film to someone*. There was no packaging step at all: title, cover frame and search phrase were missing everywhere in the specs and the pipeline. The learning loop had no way to read audience data or test a change. And because one composition renders in every format, a long explainer's portrait version would simply be the long film at 9:16, where the plugin's repurposing skills say a reel must be its own film with its own hook and payoff. The plugin's most useful content is exactly there.

## Adopted

| Lesson | Source skill | Where it lives now |
|---|---|---|
| Name the goal, who forwards the film to whom and why, and a share trigger (social currency, practical value, identity, story, topicality, high-arousal emotion; Berger and Milkman) | `reels-script`, `viral-reverse-engineering`, `hook-writer` | story-writer 3.3, checklist 18 |
| Hook family follows the goal (story or contrarian for shares, specificity for saves, question for comments); each platform rewards a different signal | `hook-writer`, `analytics-and-reporting` | story-writer 3.3 |
| Five or more hook candidates from three or more formulas; Truth and Pull as pass/fail gates; a 0-2 rubric before the lint score | `hook-writer` | story-writer 3.3, checklist 19 |
| Layered first second: hero moving, card up, voice starting, all at once | `short-form-video-script`, `tiktok-script` | story-writer 3.3, checklist 20 |
| Cut test per sentence (grab, advance, or set up the payoff) | `short-form-video-script` | story-writer 3.5, checklist 21 |
| Stake line as a bridge; a re-hook near 35 s in reels and every 60-90 s in long-form | `short-form-video-script`, `reels-script`, `youtube-long-form` | story-writer 3.5, checklist 22 |
| Callback that reframes the opening, so a replay means more | `youtube-shorts` | checklist 15 |
| Trim by collapsing middle beats; keep hook, payoff and loop | `scripting-and-storyboarding` | story-writer 3.5 |
| Visible progress for steps and lists ("2 of 3"), never padded to a round number | `short-form-video-script`, `listicle-and-roundup` | story-writer 3.5 |
| One emotional goal per film; one to three concrete specifics per narrative scene | `storytelling-and-narrative` | story-writer 3.5 |
| Numbers exactly as researched: conservative rounding only, one headline figure plus two or three supporting, small samples disclosed, steelman before a contrarian claim | `data-and-original-research`, `contrarian-and-opinion` | story-writer 3.5, checklist 23 |
| One ask, at the end, about 2 s, tied to value; never mid-video or "like and subscribe" | `short-form-video-script`, `youtube-long-form` | checklist 13 |
| Not-professional-advice line for finance, health, legal and safety films that suggest an action | `educational-content-and-how-to` | story-writer 3.5 |
| Point-of-view filter: if another channel could publish the narration unchanged, rewrite it | `idea-generation-and-ideation` | story-writer 3.5, checklist 21 |
| Care rules for disaster and crisis subjects (no casualties as bait, no amusement, no ask tied to the tragedy) | `trend-jacking` (its safety gate) | story-writer 3.5, checklist 25 |
| Sound-off check: the cards alone carry hook, stake and payoff | `reels-script` | story-writer 3.6, checklist 24 |
| Packaging named in phase 2: working title, cover frame, search phrase, next-film link | `hook-writer`, `reels-script`, `youtube-long-form`, `youtube-shorts` | story-writer 3.7, checklist 26 |
| Cover rules: 0-4 words over 20-30% of the frame, legible at about 168×94, clear of the bottom 15% and the duration badge, desaturation check, no red-and-white dominance on YouTube, one layout per series, promise only what the film pays off | `thumbnail-design` | story-writer 3.7 |
| Title with the search phrase in the first ~40 characters (50-60 total); caption first line within ~125 characters; descriptive chapter names for long-form | `youtube-publishing-and-metadata`, `cross-platform-repurposing` | story-writer 3.7 |
| AI-content disclosure where a platform or the EU AI Act transparency rules (from August 2026) call for it | `captions-and-clipping` | story-writer 3.7; decision in `TODO.md` |
| A long film's reel is its own film around one insight, with its own hook and payoff, not the long film at 9:16 | `cross-platform-repurposing`, `captions-and-clipping` | story-writer 3.2 |
| Write for the ear: contractions, one idea per breath, varied sentence length | `ai-voiceover` | story-writer 3.5 |
| Proofread caption cues for names, numbers, units and respellings before render | `captions-and-clipping` | `voice-director` item 13 |
| Chart titles state the takeaway; bar baselines at zero; a stat card, not a chart, for one or two numbers; never colour alone | `infographic-and-data-viz` | `data-ledger` v3 anti-patterns |
| Reading analytics: which curve shape points to which phase, plus benchmark ranges | `youtube-shorts`, `short-form-video-script`, `youtube-long-form`, `analytics-and-reporting` | story-writer section 6 table |
| Test discipline: one variable, a pre-committed metric, threshold and guardrail, at least 7 days (2-4 weeks under 10k followers), three or more repeats before a rule | `experimentation-and-ab-testing` | story-writer section 6 |
| Learning from others' films: ten or more examples before a pattern; separate drivers from incidentals; take the mechanism, never the assets | `viral-reverse-engineering` | story-writer section 6 (matches `reference-analyst`) |

## Open experiments (conflicts with our rules)

Recorded as story-writer lessons L9-L11, each with a proposed test:
- **Reel length.** Under 30 s or 50-60 s claimed best, against our preferred 45 s.
- **Caption chunk size.** 4-7 words, or two lines of 32-42 characters, against our 1-3 words.
- **Beat spacing.** 1-2 s in Shorts, against our 2-3 s.

## Not adopted

- **Trending audio and syncing the edit to it** (`trend-jacking`, `reels-script`): against the dim-bed audio rule, and a licensing risk.
- **A soft mid-video ask in educational films** (`educational-content-and-how-to`): we keep one ask at the end.
- **Up to 5-6 lines on a trend chart** (`infographic-and-data-viz`): a moving chart has seconds to be read, so `data-ledger` keeps three metrics at most.
- **Hook cards of 8-10 words** for educational content: we keep 6 or fewer until a test says otherwise.
- **Live-action and AI-video craft:** camera framing, character bibles, previz for generated video. A non-goal.
- **ElevenLabs settings, voice cloning and emotion tags** (`ai-voiceover`): Kokoro has none of these controls. Smart prosody and punctuation do the job here.
- **Sound accents on structure** (`ai-music-and-sound`: whooshes on hard cuts, a riser into the payoff, a stinger on the takeaway): whooshes conflict with our no-whoosh rule on educational dissolves. The riser and the final accent agree with what made Korea's ending launch-grade, so they are left to `real-sfx` as a suggestion rather than a rule.
- **Title power words** ("surprising", "complete"; a claimed +8.3% CTR): unverified and close to clickbait. The Truth gate covers titles too.
- **Publishing mechanics:** description layout, tag order, `madeForKids`, cross-posting validation, recycling intervals (90-120 days; never re-post an identical file). They belong to a publishing step that does not exist yet (`TODO.md`).
- **Business-side planning** (KPIs per quarter, pillar inventories of 100 ideas, probe ladders through polls and carousels, attribution windows): useful once publishing starts, but outside the production pipeline. The pillar and series rules are worth revisiting when a series is planned (`series/`).

## Limits that matter

- Most numbers in the plugin are platform claims or vendor studies (OpusClip, Zebracat, YouTube creator benchmarks, "2026 analyses") that it cites but we did not verify. They are used here to point at a phase, never as pass or fail lines. Berger and Milkman's sharing research is the one peer-reviewed source among those used.
- Every adopted rule is unrendered and uncalibrated on our films. They are rules, so they are judged by the next films' creative reviews and retros, like the style templates.
- Platform facts in the plugin go stale quickly: Shorts deprioritised after about 28-30 days, and Shorts and long-form recommendations separated in late 2025. Re-check them before any publishing decision rests on them.

## Attribution

`social-media-skills` 1.0.1, copyright 2026 Frank Heijdenrijk, MIT License. Ideas adopted from the skills named in the tables above. No text, code or data files were copied into this repository.
