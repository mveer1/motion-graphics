---
name: voice-director
description: Voice synthesis, narration pacing, audio measurement, and acoustic tuning using Kokoro TTS with integrated Smart Prosody and multi-voice blending.
---

# Voice Director Skill

This skill governs speech generation, voice persona selection, audio timing, and loudness mastering for educational explainers. It is now powered by the **Smart Prosody Engine** (`kokoro-smart-tts-skill`), eliminating robotic run-on sentences, mangled symbols, and flat single-voice artificiality.

---

## Quick References & Tools

- **Single-Step Synthesis Tool:** Use [`scripts/synth-and-measure.py`](./scripts/synth-and-measure.py) to generate speech with smart preprocessing and return exact duration and cadence JSON.
- **Master Pipeline Wrapper:** [`src/pipeline/tts.py`](file:///Users/mahavir/Downloads/Repo/motion graphics/src/pipeline/tts.py) (automatically applies smart preprocessing by default).
- **Voice Catalog & Blending Guide:** Read [`references/voices.md`](./references/voices.md) to pick single personas or signature blends (`am_michael:0.7,am_adam:0.3`, `af_bella:0.75,af_sarah:0.25`).
- **Phonetics Dictionary & IPA:** Check [`references/phonetics.md`](./references/phonetics.md) for technical pronunciation respellings and Markdown IPA syntax `[Word](/phonemes/)`.
- **Narration Schema:** See [`examples/narration-sample.json`](./examples/narration-sample.json) for multi-scene script structure.

---

## 1. Operating Instructions

1. **Invoke Smart Synthesis Wrapper:**
   Synthesize narration using `synth-and-measure.py` or `src/pipeline/tts.py`. Smart preprocessing is enabled by default to expand numbers/currencies, enhance punctuation, and insert breath pauses.
2. **Audio Specifications:**
   - Sample rate: 24,000 Hz
   - Format: 16-bit PCM Mono WAV
   - Default pacing: `speed: 1.12x–1.15x` (technical), `0.96x` (documentary), `1.03x` (conversational).
3. **Calibrated Prosody Presets:**
   - **`documentary`**: For finance crashes, crises, and historical thrillers (`am_michael:0.70,am_adam:0.30`).
   - **`conversational`**: For tutorials and approachable educational overviews (`af_bella:0.75,af_sarah:0.25`).
   - **`storytelling`**: For lore, narrative arcs, and audiobooks (`bm_fable:0.65,bm_george:0.35`).
   - **`energetic`**: For TikTok, 9:16 vertical reels, and YouTube Shorts (`am_adam:0.65,am_echo:0.35`).
   - **`technical-explainer`** *(Default)*: For systems, diagrams, and compiler explainers (`am_adam:0.80,am_michael:0.20`).
4. **Pacing Buffer:**
   Always concatenate a `0.5s` silence buffer (`pause.wav`) between scenes to prevent speech clipping across visual scene transitions.
5. **Duration First (GSAP Invariant):**
   **Never** hardcode GSAP animation keyframes before synthesizing and measuring narration clip durations via `synth-and-measure.py`.
6. **Conversational Simplification Rule (Reels / Shorts):**
   When targeting mobile reels (9:16), ground technical abstractions into human scenarios (e.g., *"borrowing 3x cash and getting wiped out by a margin call"* instead of *"systemic multi-tiered deleveraging cascade"*).
7. **Word Budgeting:**
   Always budget word counts to match target scene durations:
   - Deliberate documentary (`am_michael` / `documentary`): $\le 24$–$27$ words per 10-second scene.
   - Neutral technical (`am_adam` / `technical-explainer`): $\le 30$–$33$ words per 10-second scene.
   - High-energy reel (`energetic`): $\le 32$–$35$ words per 10-second scene.
8. **Check the budget on the measured clips, per scene, before animating.** Words ÷ `audio/timeline.json` `duration_sec` × 10, for every scene, not the film average. Measured on the three newest films (Nov 2026):

   | Film | Voice × speed | Film wpm | Per-scene words / 10 s | Verdict |
   |---|---|---|---|---|
   | cloud-physical-infrastructure-india | `am_adam` 1.15 | 188 | 27–36 (s1 36, s6 35) | opening and closing scenes over the 33 budget; the film reads rushed |
   | fridge-hack-europe | `am_adam` 1.15 | 171 | 26–33 (s2 32.5) | at the limit |
   | south-korea-data-center-fire | `am_michael` 1.0 | 136 | 21–25 | inside the documentary budget; the calmest; the only one of the three with a launch-grade `earshot critique` |

   Fix an over-budget scene by cutting words, not by raising the speed. Hook and closing scenes are the usual offenders because they are written last. A fact-dense film (dates, figures, named places) should take the documentary budget even when its visuals are light.
9. **A slower voice needs more beats, not fewer.** `motion-qa` flagged 79 s of the 98 s Korea film (1.0×, 14 stretches, longest 12 s) as low-energy or frozen under speech, against 41–44 s in the two 1.15× films (15–20 stretches, longest 4.5–5.4 s). The count is similar; the stretches are much longer, because slower narration means longer scenes (13–20 s). Plan one visual event per 2–3 s from the measured onsets, not one per sentence. See `motion-graphics-designer` §2.4.
10. **Phonetic respellings stay out of on-screen text.** The three scripts use respellings for Kokoro (`Dell-ee`, `Chen-eye`, `Day-jun`, `DAN-foss`, `Gee Drive`). Captions and headlines were correctly written with the real spelling (Delhi, Chennai, Daejeon). Keep narration text and displayed text as separate fields, and have a person listen to place names once, because the measurement cannot confirm the pronunciation.
11. **Lint the script before it is spoken, and the timing after.** `python scripts/studio.py script <slug>` prints a timed sentence sheet (measured clip lengths once `audio/timeline.json` exists) and flags: a hook sentence over about 3 s, a greeting or "in this video" frame, three or more sentences in a row with no figure, date or name, more than one ask, no echo of a hook word in the last line (reel-length films), and storyboard scenes with no `why`. `studio.py validate` prints the warnings. On the Nov 2026 films it found that Korea's film opens on one 9.8 s sentence (date, place, event and agency together) and that cloud's hook scores 20/100. Treat each flag as a lead, not a verdict: mechanism sentences are legitimately abstract, which is why `abstract-run` is a warning only for films of 60 s or less. Natural speech is about 2.5 words per second; this voice runs 2.2 to 3.0 on the three films, and the script should feel shorter than the video.
12. **The words are the story-writer's; delivery is this skill's.** The hook, the script and the word budget per scene are written and signed off by `story-writer` (`.claude/skills/story-writer/SKILL.md`, verdict in `qa/story-review.json`). This skill picks up its handoff (respell list, preset), adds phonetic respellings, sets voice and speed, synthesizes and measures. If the measured clips break the budget (item 8), cut words in a small edit and send the film back for a story-writer `review` pass before render.
13. **Use measured word times, not sentence guesses, for captions and for beats.** After narration is measured: `python scripts/studio.py captions <slug> --timing words --grouping phrase` transcribes each clip with the local Whisper (under the analysis lock), aligns the script's own spelling to the measured times and writes 1 to 3 word caption cues plus `audio/words.json`. Each cue keeps its word times, so `Studio.comp.captions` highlights the spoken word; the command also gives each cue a role and lane and flags numbers for emphasis (the `caption-designer` skill; it prints the preset and any cue-length or lane warning). Without `--grouping` the video type decides: phrase cues for a reel or long reel, sentence cues for YouTube. `python scripts/studio.py words <slug> "four degrees"` prints the film time a phrase is spoken: put the storyboard beat for that picture on that frame (show the noun on the word it names). Check the per-scene match the command prints; under 80% means words were interpolated, so listen to that scene. Before render, read the caption cues once for proper names, numbers, units and respellings: a cue that shows `Bo-pahl` or "forty two" where the screen should say Bhopal or 42 is a caption bug, even when the timing is right. Phonetic respellings in the script (`DAN-foss`) are matched by letters only, so they still align.

14. **Pace is set per scene, not per film (2026-11-07, owner's review of game-theory-trust: "the system also needs to understand where to slow down and where to pick up the pace").** `src/narration.json` scenes may carry `"speed": 0.92`; it overrides the film speed (`project.json` `audio.speed`) for that scene only, is recorded per scene in `audio/timeline.json` and re-makes only that scene when changed (`src/pipeline/narration.py` `scene_speed`, tested in `tests/test-studio.py`). Take the pace from the story-writer's pace map (`pace: slow | normal | fast` per storyboard scene): **slow** (about 0.90 to 0.95x) for the turn, the proof, a new concept or the key number, with fewer words per 10 s and a beat of silence after the payoff; **normal** (the film speed) for context; **fast** (about 1.10 to 1.15x) for recap, transitions and the loop line. Never go above 1.15x or below 0.88x. Budget words per scene against that scene's own speed (item 8), and after measuring, check that the slow scenes are the slowest and the fast ones the quickest in words per second; if a hook or closing scene reads rushed, slow it before cutting words. Re-time cues in `src/` after any per-scene speed change.