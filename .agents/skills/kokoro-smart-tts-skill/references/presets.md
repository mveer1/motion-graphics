# Kokoro Smart TTS Presets Reference

The `kokoro-smart-tts-skill` ships with 5 calibrated prosody presets designed for different genres and explainer contexts. Each preset configures pacing, sentence pause duration, clause pause duration, default multi-voice blend, and punctuation handling.

---

## 1. Preset Comparison Matrix

| Preset Name | Target Genre | Voice Recipe | Default Speed | Sentence Pause | Clause Pause | Pacing (wps) | Character |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`conversational`** | Tutorials, intros, human interest | `af_bella:0.75,af_sarah:0.25` | `1.03x` | `0.28s` | `0.16s` | ~2.6–2.8 | Warm, expressive, empathetic |
| **`documentary`** | Economics, crises, thrillers, history | `am_michael:0.70,am_adam:0.30` | `0.96x` | `0.38s` | `0.20s` | ~2.2–2.5 | Resonant, cinematic, deliberate |
| **`storytelling`** | Lore, narrative arcs, fiction | `bm_fable:0.65,bm_george:0.35` | `0.98x` | `0.42s` | `0.22s` | ~2.3–2.5 | Dramatic, theatrical British, suspenseful |
| **`energetic`** | TikTok, Instagram Reels, YouTube Shorts | `am_adam:0.65,am_echo:0.35` | `1.15x` | `0.20s` | `0.12s` | ~3.0–3.3 | Punchy, high-momentum, crisp attack |
| **`technical-explainer`** | Systems, code walkthroughs, math | `am_adam:0.80,am_michael:0.20` | `1.12x` | `0.30s` | `0.18s` | ~2.8–3.0 | Grounded, neutral, authoritative |

---

## 2. Detailed Preset Profiles

### `conversational`
* **Best for:** Video tutorials, product overviews, educational explainers where approachable warmth is required.
* **Acoustic Profile:** Blends Bella's warm, expressive conversational tone (75%) with Sarah's didactic articulation (25%).
* **Prosody Rules:** Inserts gentle breath pauses (~280ms) between thoughts; slightly lifts terminal pitch on questions to maintain conversational rapport.

### `documentary`
* **Best for:** Financial collapse explainers, historical retrospectives, investigative journalism.
* **Acoustic Profile:** Michael's baritone depth (70%) provides cinematic authority, tempered by Adam's crisp precision (30%).
* **Prosody Rules:** Deliberate pacing (`0.96x`), generous pause buffers (`0.38s`), and dramatic ellipsis support. Words have room to breathe so viewer focus remains on on-screen data.

### `storytelling`
* **Best for:** Historical tales, audio dramas, deep narrative arcs.
* **Acoustic Profile:** Fable's rich, theatrical British storytelling tone (65%) complemented by George's scholarly enunciation (35%).
* **Prosody Rules:** Converts contrast conjunctions (*"but"*, *"yet"*, *"then"*) into dramatic ellipsis holds (`…`); extended inter-paragraph silence (`0.75s`).

### `energetic`
* **Best for:** 9:16 vertical reels, fast-paced shorts, viral hooks.
* **Acoustic Profile:** Adam (65%) + Echo (35%) creates modern, high-retention energy without sounding frantic.
* **Prosody Rules:** Tight silence buffers (`0.20s` between sentences), high speech speed (`1.15x`), and punchy phrase breaks.

### `technical-explainer`
* **Best for:** Deep-dive motion graphics explainers (compiler design, distributed systems, financial mechanics).
* **Acoustic Profile:** Adam (80%) + Michael (20%) enhances speech body while preserving neutral technical objectivity.
* **Prosody Rules:** Measured `1.12x` pacing, optimized for synchronizing with GSAP visual keyframes.

---

## 3. CLI Invocation Examples

```bash
# Conversational Tutorial
python3.12 smart_synth.py --text "Hey there! Let's build a neural network." --out audio.wav --preset conversational

# Dramatic Documentary
python3.12 smart_synth.py --text "In twenty twenty-six, the illusion broke." --out audio.wav --preset documentary

# Punchy Vertical Reel
python3.12 smart_synth.py --text "Stop losing money on triple leverage." --out audio.wav --preset energetic

# Custom Overrides on Preset
python3.12 smart_synth.py --text "System check complete." --out audio.wav --preset technical-explainer --speed 1.05 --sentence-pause 0.25
```
