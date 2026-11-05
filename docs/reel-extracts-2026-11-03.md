# Instagram reel extracts, 2026-11-03

Eight reels extracted and analysed as reference material. Nothing in them was acted on: no comments sent, no links followed, nothing installed.

## Method and limits

- **Download:** `yt-dlp` (bundled in OpenWhispr.app), no login. Caption, uploader, like and comment counts came from the yt-dlp metadata.
- **Speech:** FFmpeg to 16 kHz mono, then local Whisper `base.en` (`~/.openclaw/whisper-models/ggml-base.en.bin`) through OpenWhispr's `whisper-server`. Transcripts below are paraphrased summaries, with short quotes only.
- **Visuals:** one contact sheet per reel (8 frames across the runtime). **Viewed for 4 reels** (DfPOHlfIVsM, DfM7YzLgbj9, DbRGB9QsGtb, De1xXtICvqs). The other 4 have no visual notes.
- **Whisper errors:** `base.en` mishears product names. In De1xXtICvqs it wrote "cloth" and "clock" for Claude and "TUNO" for Suno. Where the caption or on-screen text gives the correct word, the caption wins.
- **Claims are unverified.** Star counts, benchmarks, token savings and "best database" statements are the creators' own. None were checked against a source.
- Working files (mp4, wav, transcript JSON, contact sheets) are in the session scratchpad under `reels/<shortcode>/`. They are not in the repo.

## Overview

| # | Shortcode | Creator | Length | Topic | Speech | Comment-for-link CTA |
|---|---|---|---|---|---|---|
| 1 | DfPOHlfIVsM | Julia, product designer | 9.1 s | Website mouse-interaction inspiration list | None (music) | Yes: "INSPO" |
| 2 | DbRGB9QsGtb | Marc Kaz | 16.0 s | Pinchtab, browser control for AI agents | One sentence | No (GitHub URL on screen) |
| 3 | DfO_RLTE8dZ | Prince Gupta | 43.1 s | Google's AX, "Kubernetes for AI agents" | Yes | Yes: "LINK" |
| 4 | De1xXtICvqs | softgirlnocode | 30.1 s | 3 ways to make Claude-made videos look different | Yes | Yes: "LINK" |
| 5 | De5Q9YKhSis | Antonio | 45.4 s | "Atticus", voice control for a Mac | Yes | Yes: "ATTICUS" |
| 6 | DfPXiP0RhNl | Kallaway | 33.2 s | Short-form video reference database | Yes | Yes: "Collections" |
| 7 | DfM7YzLgbj9 | Keeran Jagadesan | 10.9 s | Top 5 Claude skills for SEO | None (music) | Yes: "SKILLS" |
| 8 | DeEALxWikNH | The Token Ai | 29.7 s | Cactus Compute "Whistle" speech-to-text model | Yes | Yes: "WHISTLE" |

Engagement from metadata, in post order of the table:

| Shortcode | Likes | Comments | Posted |
|---|---|---|---|
| DfPOHlfIVsM | 1,687 | 192 | 2026-11-02 |
| DbRGB9QsGtb | 3,808 | 66 | 2026-07-26 |
| DfO_RLTE8dZ | 177 | 45 | 2026-11-02 |
| De1xXtICvqs | 2,921 | 1,304 | 2026-10-23 |
| De5Q9YKhSis | 897 | 795 | 2026-10-24 |
| DfPXiP0RhNl | 3,029 | 8,275 | 2026-11-02 |
| DfM7YzLgbj9 | 1,547 | 2,177 | 2026-11-01 |
| DeEALxWikNH | 2,039 | 297 | 2026-10-04 |

---

## 1. DfPOHlfIVsM: website mouse-interaction inspiration

**Creator / caption.** Julia (product designer). "New curated website inspo alert", themed on mouse interactions. Says designers' creativity in something as simple as moving the mouse makes sites feel playful. CTA: comment "INSPO" for the full list.

**Spoken content.** None. Music only.

**On-screen content.**
- Opens on the creator sitting on the floor with a laptop. Overlay text: "i love when designers refuse to make just another website".
- Then a monitor on a dark, orange-glow desk, with the site name as a label above each shot: igloo.inc, found.runable.site, laxspace.co, wix.com/transparentvideo, newmixcoffee.com, thibaut.cool, rohithmanikkoth.framer.website.
- End card text: comment "INSPO" and "I'll send you all the links".

**Analysis.**
- Format is a human hook, then fast screen-recording cuts, about 1 s per site, then a CTA.
- The site name is the only text during the demo, so the screen recordings carry the piece.
- Sites shown lean on playful 3D, cursor-reactive objects, physical-feeling interactions and bold type.
- 9 s total, the shortest in the set.

## 2. DbRGB9QsGtb: Pinchtab

**Creator / caption.** Marc Kaz, posted 2026-07-26 (oldest in the set). Describes Pinchtab as giving an agent full browser control through a plain HTTP API. Claimed features: single Go binary with no dependencies, accessibility-DOM snapshots with stable element refs, stealth mode and persistent sessions, page snapshots of about 800 tokens ("13x cheaper than screenshots"), and a diff mode so agents read only what changed.

**Spoken content.** One line: a greeting, then "a high performance browser automation bridge and multi-instance orchestrator with advanced stealth injection and a real-time dashboard". The speech is shorter than the caption and adds nothing to it.

**On-screen content.**
- Top text: "A 12MB binary just solved the biggest bottleneck in AI agents".
- Background is a GitHub README screenshot (benchmark table of cost and request savings against another tool).
- The presenter is cut out in the lower right, pointing at the text, with the URL `github.com/pinchtab/pinchtab` pinned across the bottom.
- Word-by-word captions, with the current word highlighted yellow.

**Analysis.**
- Claim-first headline ("12MB binary", "biggest bottleneck") is the hook, not the greeting.
- The URL stays on screen for the whole 16 s, so no comment-for-link step is needed.
- Highest likes-to-comments ratio in the set (3,808 to 66), consistent with no comment trigger.

## 3. DfO_RLTE8dZ: Google AX ("Kubernetes for AI agents")

**Creator / caption.** Prince Gupta. Says Google open-sourced AX (Agent Executor) with 14k+ GitHub stars. Two claimed fixes for agents in production: per-agent sandboxes with CPU and memory limits (pre-wired with repos, MCP servers and skills), and suspend and resume from a checkpoint. Apache-2.0, driven by `ax apply`, `ax suspend`, `ax resume`. Logo credit: Nan Hockin, CC BY 4.0. CTA: comment "LINK".

**Spoken content.** Follows the caption closely. Adds the failure framing: agents "crashing mid-task or burning money stuck in a loop". Calls suspend and resume "the best part". Ends with the comment-for-link CTA.

**Analysis.**
- Structure is hook (big-company name plus star count), problem, feature 1, feature 2 ("the best part"), CTA.
- Lowest engagement of the set (177 likes, 45 comments) despite a strong topic. The channel is smaller.
- Visuals not reviewed.

## 4. De1xXtICvqs: 3 ways to make Claude videos look different

**Creator / caption.** softgirlnocode. Three tips: (1) open-source projects, pasting a GitHub link into Claude so it pulls in real code (thinking orbs, 3D line art, a free mascot library); (2) a workspace instead of one-off chats, so Claude knows past projects, brand and templates; (3) AI-generated music (Suno) that fits the pace and mood. CTA: comment "LINK" for her favourite GitHub projects.

**Spoken content.** Reads as the caption, in order. Whisper garbled the product names, so the caption is the better source for those.

**On-screen content.** Talking head against a red wall with a handheld mic, on a cut rhythm of about 3 to 4 s. Overlays visible:
- Title card "Claude Motion Graphics".
- A grid of example effects: a green halftone tunnel, a bold "FRIDAY" typographic card, a prompt box with a GitHub URL, a mascot icon grid.
- A "workspace" folder icon, then a mock file tree: `CLAUDE.md`, `references/brand.md`, `voice.md`, `.claude/skills/` (several named skills), `projects/`, next to a thumbnail grid of past reels.
- A music-player chip ("Pixel Bloom", Suno), and two cards contrasting "Airy / flowing" and "Punchy / percussive" with waveform shapes.
- Lower-third captions on a grey pill.

**Analysis.**
- Closest to this repo's own approach: a workspace with a `CLAUDE.md`, brand and voice files, and per-project skills is the same pattern as Motion Lab.
- Two ideas worth noting for Motion Lab (not acted on): pulling reusable effect code from public GitHub libraries, and choosing music by pace and mood. Any such use would need the licence check and the "learn techniques, never assets" rule from CLAUDE.md.
- The alternation of face and illustrated overlay avoids long static stretches.
- High comment count (1,304 on 2,921 likes) from the "LINK" trigger.

## 5. De5Q9YKhSis: "Atticus", voice control for a Mac

**Creator / caption.** Antonio. "Open sourced Jarvis for your Mac. You talk, it clicks." CTA: comment "ATTICUS" for the install guide, after following first so a DM can reach you.

**Spoken content.** Free, open-source app called Atticus; press a shortcut and speak. It opens apps, moves windows and finds files. It can read what is on screen (for example reply to an open email). It learns shortcuts, with a "focus mode" example that opens a to-do list and blocks distractions. The catch, announced as "one thing it needs first" and delayed until near the end: the app is free but needs a paid Claude plan (Pro or Max, Whisper wrote "cloud") or a local model, plus macOS 26.

**Analysis.**
- Retention hook: promises a catch early ("I'll tell you before the end") and delays it.
- The install guide goes only to commenters, so the funnel is comment, DM, link.
- 897 likes against 795 comments, near parity, so the CTA drives most of the interaction.
- Visuals not reviewed. The product name and the "needs macOS 26 and a paid plan" claim come from this one creator and were not checked.

## 6. DfPXiP0RhNl: short-form video reference database

**Creator / caption.** Kallaway. Describes a hand-curated reference library of short-form video: 100+ collections across formats, visual hooks, editing styles and signature series. Each video links to a full transcript and an analysis of topic, format and hook. CTA: comment "Collections". A follow plug for @kallawaymarketing.

**Spoken content.** Same as the caption, nearly word for word. It has no link and no name for the database.

**Analysis.**
- Most comments of the set (8,275) against 3,029 likes. Comments are mostly the trigger word. The first ten visible were all "Collection" or "collections".
- Short, one-claim reel: superlative hook, features, CTA. No new information on the audio over the caption.
- The reference-library idea overlaps with this repo's `reference-corpus.py` workflow (transcripts plus hook and format analysis per video).
- Visuals not reviewed.

## 7. DfM7YzLgbj9: top 5 Claude skills for SEO

**Creator / caption.** Keeran Jagadesan. "Follow me then comment SKILLS." All of the skills use the OpenSEO connector with Claude to get keyword data.

**Spoken content.** None. Music only.

**On-screen content.**
- Fixed headline: "Top 5 Claude skills to make your website show up on Google".
- A countdown from No. 5 to No. 1, each a coloured card showing an install count on SEO.party and a one-line description:
  - No. 5 Local SEO (pink): audits a Google Business Profile against local competitors.
  - No. 4 Competitor Analysis (green): ranking keywords, backlinks and gaps.
  - No. 3 Keyword Gap (purple): keywords competitors rank for that you don't.
  - No. 2 Keyword Research (yellow): keywords worth going after.
  - No. 1 AI Visibility Audit (orange): what gets you cited in Google AI answers.
- The install number on each card counts up while it is on screen.
- A five-step progress bar at the bottom, filled progressively toward No. 1.
- Background is first-person footage riding a scooter down a tree-lined road (the same clip throughout).
- End text: "Comment SKILLS for the full list".

**Analysis.**
- Strong motion-graphics pattern for list content: one colour per rank, a counting number, and a progress bar showing position. It stays in motion for the full 11 s.
- Live footage behind clean flat cards keeps the background changing, so no frame is static.
- Second most comments (2,177) at 11 s, on 1,547 likes.
- The skill names and install counts were read from frames and not checked on the site.

## 8. DeEALxWikNH: Cactus Compute "Whistle"

**Creator / caption.** The Token Ai. Whistle is a speech-to-text model of 16.9 MB that runs on a device CPU. Caption claims: released 2 October, open weights under Apache-2.0, seven languages, per-word timestamps, audio stays on the device, roughly Whisper base quality at about a ninth of the size, first token in 11 ms against 73 ms on an M4 Pro. The caption itself notes the benchmarks are the company's own and Whisper base still leads on three of them. It adds that, with Cactus's Needle model, it can turn a voice clip into tool calls. Footage credit: Cactus Compute. Music credit: "Cornfield Chase" (Hans Zimmer).

**Spoken content.** A compressed version of the caption. The narration drops the caveat that Whisper base still leads on three benchmarks, and says "9 times smaller and 6 times faster".

**Analysis.**
- The caption is more careful than the voice-over: the narration keeps the claims and leaves out the qualification.
- Uses licensed music from a film score, which would be a rights problem for any reuse here. Noted only as an observation.
- Direct relevance to this repo: Motion Lab uses Whisper base for transcription in this extraction, and Whistle would be a possible lighter local alternative, but its claims are unverified. Not tried.
- Visuals not reviewed.

---

## Cross-cutting findings

1. **Comment-to-DM funnels dominate.** 7 of 8 reels end with "comment WORD and I'll send you the link". Only DbRGB9QsGtb puts the URL on screen. The reels with the trigger have far higher comment counts, and Kallaway's has more than twice as many comments as likes. Comment counts here measure the trigger, not interest.
2. **The hook is a claim or a number in the first seconds**: "12MB binary", "Google open-sourced", "best database in the world", "Top 5". None opens with a greeting as the main hook, apart from DbRGB9QsGtb's brief one.
3. **Speech usually repeats the caption.** In 5 of the 6 reels with speech, the voice-over is the caption read aloud, so the caption carries the information and the audio is redundant. DfPOHlfIVsM and DfM7YzLgbj9 carry no speech at all.
4. **Visual formats seen:** talking head with overlays (De1xXtICvqs, DbRGB9QsGtb, DfPOHlfIVsM intro), screen recording with labels (DfPOHlfIVsM), and flat cards over live footage (DfM7YzLgbj9). The cards-over-footage format is the most reusable motion-graphics pattern here.
5. **Short length.** Reels run 9 to 45 s, the median about 30 s. The two shortest (9 s and 11 s) have no speech.
6. **Topic cluster.** Six of the eight are about AI tooling, mostly Claude-adjacent. This is the creator-economy niche, not Motion Lab's subject set (technology, finance, science, history, mathematics, news).

## Open follow-ups (none started)

- View contact sheets for the 4 reels not yet looked at (DfO_RLTE8dZ, De5Q9YKhSis, DfPXiP0RhNl, DeEALxWikNH) to complete the visual analysis.
- If any of this should become reference records, route it through `reference-analyst` and `scripts/reference-corpus.py` (technique records only, no assets).
- Verify any factual claim (AX, Pinchtab, Whistle, Atticus) before it is used in narration or on-screen text.
