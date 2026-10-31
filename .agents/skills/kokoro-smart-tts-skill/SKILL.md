---
name: kokoro-smart-tts-skill
description: Makes Kokoro TTS speech sound human, expressive, and natural via intelligent text preprocessing, calibrated prosody, breath pauses, and multi-voice tensor blending.
---

# Kokoro Smart TTS Skill

The `kokoro-smart-tts-skill` transforms raw script text into natural, expressive, human-sounding speech using Kokoro TTS (v0.9.4). It eliminates the common symptoms of robotic AI voices: breathless run-on sentences, mangled numbers and currencies, flat monotone delivery, and synthetic single-voice artifacts.

---

## Quick References & Tools

- **Core Synthesizer CLI:** [`scripts/smart_synth.py`](./scripts/smart_synth.py) (full end-to-end smart synthesis with presets).
- **Text Preprocessor:** [`scripts/preprocessor.py`](./scripts/preprocessor.py) (currencies, multipliers, initialisms, smart breath grouping).
- **Voice Advisor & Blender:** [`scripts/voice_advisor.py`](./scripts/voice_advisor.py) (persona selection & multi-voice tensor blending).
- **Benchmark & Evaluation Suite:** [`scripts/evaluate_benchmark.py`](./scripts/evaluate_benchmark.py) (before/after evaluation report).
- **Capabilities Ground Truth:** [`references/kokoro-capabilities.md`](./references/kokoro-capabilities.md) (verified Kokoro 0.9.4 parameters vs limitations).
- **Presets Guide:** [`references/presets.md`](./references/presets.md) (conversational, documentary, storytelling, energetic, technical).
- **Voice Catalog & Recipes:** [`references/voice-catalog-guide.md`](./references/voice-catalog-guide.md) (all 54 voices + blending formulas).
- **Phonetics Lexicon:** [`references/phonetics-lexicon.md`](./references/phonetics-lexicon.md) (Markdown IPA syntax and technical pronunciations).

---

## 1. Why Kokoro Sounds Like AI (And How We Fix It)

| Problem in Naive Kokoro | Root Cause | Smart Skill Solution |
| :--- | :--- | :--- |
| **Breathless delivery** | Concatenating sentence audio with 0ms gap | Injects calibrated acoustic silence buffers (`0.20s`–`0.45s`) between sentences and clauses. |
| **Mangled symbols** | `$2.4T`, `3x`, `1/L`, `90%` get misread or dropped | Normalizes currencies, multipliers, and fractions to clean spoken English (`"two point four trillion dollars"`, `"three times"`, `"one over L"`). |
| **Monotone flat timbre** | Using a single voice profile across all themes | Multi-voice style vector blending: $\sum w_i \mathbf{v}_i$ (e.g. `am_michael:0.7,am_adam:0.3` for cinematic baritone + crisp articulation). |
| **Cadence drops / clipping** | Long unbroken token runs (> 40 words or 510 tokens) | Splits long run-ons into natural semantic breath groups (15–18 words max) at conjunctions and em-dashes. |
| **Dropped dashes** | Misaki G2P completely deletes ascii double hyphens (`--`) | Normalizes `--` to Unicode em-dash `—` (token ID 9) and `...` to Unicode ellipsis `…` (token ID 10) for true dramatic pauses. |
| **Mispronounced jargon** | Complex acronyms or names (ReLU, LaTeX, SQL) | Injects Misaki Markdown phonetic syntax: `[ReLU](/ˈɹɛluː/)`. |

---

## 2. Pacing & Prosody Presets

The skill provides 5 pre-calibrated presets:

| Preset | Ideal For | Voice Recipe | Speed | Pause | Pacing |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`conversational`** | Tutorials, walkthroughs, warm educational content | `af_bella:0.75,af_sarah:0.25` | `1.03x` | `0.28s` | ~2.6 wps |
| **`documentary`** | Finance crashes, crises, high-stakes investigations | `am_michael:0.70,am_adam:0.30` | `0.96x` | `0.38s` | ~2.2 wps |
| **`storytelling`** | Narrative lore, history, audiobooks, drama | `bm_fable:0.65,bm_george:0.35` | `0.98x` | `0.42s` | ~2.3 wps |
| **`energetic`** | TikTok, 9:16 vertical reels, YouTube shorts | `am_adam:0.65,am_echo:0.35` | `1.15x` | `0.20s` | ~3.1 wps |
| **`technical-explainer`** | Motion graphics diagrams, compiler/system architecture | `am_adam:0.80,am_michael:0.20` | `1.12x` | `0.30s` | ~2.8 wps |

---

## 3. How to Use

### A. Command-Line Usage

```bash
# 1. Basic synthesis with preset
python3.12 .agents/skills/kokoro-smart-tts-skill/scripts/smart_synth.py \
  --text "In 2026, retail traders watched $2.4T vanish after an ordinary 2% dip." \
  --out audio/s1.wav \
  --preset documentary

# 2. Custom multi-voice blend with custom speed
python3.12 .agents/skills/kokoro-smart-tts-skill/scripts/smart_synth.py \
  --text "When leverage bursts, you cannot print confidence." \
  --out audio/s2.wav \
  --voice "am_michael:0.75,am_adam:0.25" \
  --speed 1.05 \
  --sentence-pause 0.35

# 3. Export timeline markers for GSAP sync
python3.12 .agents/skills/kokoro-smart-tts-skill/scripts/smart_synth.py \
  --text-file narration.txt \
  --out audio/narration-full.wav \
  --preset technical-explainer \
  --json-meta audio/timeline-markers.json
```

### B. Python API Integration

```python
from pathlib import Path
import sys

skill_scripts = Path(".agents/skills/kokoro-smart-tts-skill/scripts")
if str(skill_scripts) not in sys.path:
    sys.path.insert(0, str(skill_scripts))

from smart_synth import synthesize_smart

result = synthesize_smart(
    text="In early 2026, retail traders watched $2.4T vanish.",
    out_path="renders/voice.wav",
    preset="documentary",
    voice="am_michael:0.7,am_adam:0.3",
    custom_phonetics={"ReLU": "ˈɹɛluː"}
)

print(f"Synthesized {result['word_count']} words in {result['duration_sec']}s at {result['cadence_wps']} wps.")
```

---

## 4. Empirical Evaluation Benchmark

The benchmark suite (`evaluate_benchmark.py`) compared naive baseline Kokoro against Smart Kokoro across 3 genres:

1. **Financial Crisis Explainer:**
   - *Baseline:* 19.68s, 24% pause ratio, currency `$2.4T` and `1/L` mangled.
   - *Smart:* 28.70s, 38.2% pause ratio, all currencies, percentages, and multipliers verbalized clearly with Michael+Adam depth.
2. **Conversational Deep Learning Tutorial:**
   - *Baseline:* 12.08s, 25.6% pause ratio, flat pace.
   - *Smart:* 16.87s, 44.8% pause ratio, warm Bella+Sarah blend with exact `[ReLU](/ˈɹɛluː/)` phonemes.
3. **Cinematic Storytelling:**
   - *Baseline:* 13.08s, rushed through ellipses.
   - *Smart:* 15.64s, theatrical British Fable+George blend with dramatic pause holds.

Samples are stored in [`examples/before_after_samples/`](./examples/before_after_samples/).

---

## 5. Non-Interference Guarantee

This skill does NOT replace or break `src/pipeline/tts.py` or existing explainer projects. It runs independently as a modular workspace skill and can be called directly or used by `voice-director` to produce superior speech.
