# Kokoro Voice Catalog & Styling Guide

Kokoro 0.9.4 includes 54 voice models across 9 languages. Each voice has an acoustic fingerprint, and voice vectors can be linearly blended ($\sum w_i \mathbf{v}_i$) to create custom timbres that eliminate single-voice artificiality.

---

## 1. Signature Multi-Voice Blends

| Recipe Name | Blend Formula | Speed | Best For | Timbre Description |
| :--- | :--- | :---: | :--- | :--- |
| **`documentary-thriller`** | `am_michael:0.70,am_adam:0.30` | `0.96x` | Finance collapses, crises, drama | Deep cinematic baritone with crisp technical precision. |
| **`warm-conversational`** | `af_bella:0.75,af_sarah:0.25` | `1.03x` | Tutorials, lifestyle, UX demos | Warm and empathetic with analytical clarity. |
| **`epic-storyteller`** | `bm_fable:0.65,bm_george:0.35` | `0.98x` | Lore, history, philosophical arcs | Rich theatrical British narration with gravitas. |
| **`energetic-reel`** | `am_adam:0.65,am_echo:0.35` | `1.15x` | Short-form mobile reels / TikTok | Punchy attack and fast modern retention. |
| **`energetic-female`** | `af_nova:0.70,af_sky:0.30` | `1.14x` | Short-form mobile reels / TikTok | High-momentum modern female delivery. |
| **`technical-systems`** | `am_adam:0.80,am_michael:0.20` | `1.12x` | Motion graphics system diagrams | Grounded neutral technical narration with extra chest body. |

---

## 2. Base Personas Catalog

### American English (`lang="a"`)
- **`am_adam` (Default Technical Male):** Grounded, neutral, authoritative. Best for systems architecture, compiler design, algorithms.
- **`am_michael` (Documentary Male):** Resonant, deliberate, cinematic baritone. Best for economics, crises, deep dives.
- **`am_echo` (Modern Energetic Male):** Confident, brisk, contemporary. Best for short-form reels and product launches.
- **`af_bella` (Conversational Female):** Warm, friendly, expressive. Best for tutorials and educational intros.
- **`af_sarah` (Academic Female):** Crisp, precise, didactic. Best for mathematics, proofs, data structures.
- **`af_nova` (Dynamic Female):** Sharp consonant punch, high energy. Best for fast mobile hooks.

### British English (`lang="b"`)
- **`bm_george` (Scholarly British Male):** Classic British lecture, refined enunciation. Best for physics and formal logic.
- **`bm_fable` (Theatrical Narrator Male):** Resonant, dramatic storytelling. Best for history, audiobooks, and lore.
- **`bf_emma` (Sophisticated British Female):** Calm, measured, poised. Best for scientific documentaries.

---

## 3. Pacing & Word Budget Calibration Table (10-Second Scene Target)

To prevent rushed speech or visual disconnects, budget narration words to the measured cadence of each persona:

| Preset / Voice | Tone Persona | Recommended Speed | Cadence (words/sec) | Max Words (10s Scene) | Max Words (40s Short) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `am_adam` / `technical` | Neutral Technical | `1.12x–1.15x` | ~3.0 wps | 30–33 words | 120–130 words |
| `am_michael` / `documentary` | Deliberate Documentary | `0.96x–1.05x` | ~2.2–2.5 wps | 22–25 words | 90–100 words |
| `af_bella` / `conversational` | Conversational / Warm | `1.03x` | ~2.6 wps | 25–27 words | 100–110 words |
| `af_sarah` / `academic` | Academic Analytical | `1.05x` | ~2.7 wps | 26–28 words | 105–115 words |
| `bm_fable` / `storytelling` | Theatrical British | `0.98x` | ~2.3 wps | 22–25 words | 90–100 words |
| `energetic` | High-Retention Reel | `1.15x` | ~3.1 wps | 31–34 words | 125–135 words |

> [!TIP]
> Always budget **$\le 22$–$25$ words per 10-second scene** when using deliberate narrative blends (`documentary` or `storytelling`) to allow natural breathing pauses, kinetic visual transitions, and foley micro-accents.
