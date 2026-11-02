# Kokoro Voice Catalog & Blending Guide

Kokoro 0.9.4 provides **54 voice models** across 9 languages. In this workspace, each voice is represented as a style embedding tensor $\mathbf{v} \in \mathbb{R}^{510 \times 1 \times 256}$.

---

## 1. Complete Voice Catalog

### A. American English (`lang="a"`) — 20 Voices

| Voice ID | Gender | Timbre Profile | Natural Cadence | Ideal Genre / Use Case |
| :--- | :---: | :--- | :---: | :--- |
| **`am_adam`** | Male | Grounded, neutral, authoritative | ~3.0 wps | Technical systems, code, compiler explainers *(workspace baseline)* |
| **`am_michael`** | Male | Deep resonant baritone, cinematic | ~2.5 wps | Financial collapses, crisis explainers, documentaries |
| **`am_echo`** | Male | Modern, energetic, confident | ~3.1 wps | High-retention reels, startup launches, product demos |
| **`am_eric`** | Male | Conversational, warm, approachable | ~2.7 wps | Friendly tutorials, onboarding guides |
| **`am_fenrir`** | Male | Gritty, intense, dramatic | ~2.6 wps | High-stakes drama, game lore, trailers |
| **`am_liam`** | Male | Youthful, bright, articulate | ~2.9 wps | Tech explainers, consumer apps |
| **`am_onyx`** | Male | Solemn, heavy baritone, steady | ~2.3 wps | Philosophical retrospectives, memorials |
| **`am_puck`** | Male | Playful, fast-paced, animated | ~3.2 wps | Entertainment, comedy sketches |
| **`am_santa`** | Male | Cheerful, jovial, boisterous | ~2.4 wps | Holiday specials, stylized narration |
| **`af_bella`** | Female | Warm, conversational, expressive | ~2.7 wps | Lifestyle, UX walkthroughs, educational overviews |
| **`af_sarah`** | Female | Crisp, analytical, didactic | ~2.8 wps | Mathematics, algorithmic proofs, data structures |
| **`af_alloy`** | Female | Polished corporate, measured | ~2.8 wps | Enterprise B2B, pitch decks |
| **`af_aoede`** | Female | Melodic, gentle, artistic | ~2.5 wps | Art history, generative art essays, design philosophy |
| **`af_heart`** | Female | Intimate, soft, empathetic | ~2.3 wps | Personal stories, mindfulness, meditation |
| **`af_jessica`** | Female | Casual, upbeat, friendly | ~2.9 wps | Social media promos, vlog voiceovers |
| **`af_kore`** | Female | Poised, articulate, classical | ~2.7 wps | Literature, museum audio guides |
| **`af_nicole`** | Female | Broadcast journalist, steady | ~2.8 wps | News summaries, factual debriefs |
| **`af_nova`** | Female | Punchy, dynamic, sharp attack | ~3.2 wps | Fast mobile reels, TikTok hooks |
| **`af_river`** | Female | Atmospheric, nuanced storyteller | ~2.5 wps | Mystery, audiobooks, investigative arcs |
| **`af_sky`** | Female | Light, breezy, natural | ~2.9 wps | Consumer lifestyle, productivity |

---

### B. British English (`lang="b"`) — 8 Voices

| Voice ID | Gender | Timbre Profile | Natural Cadence | Ideal Genre / Use Case |
| :--- | :---: | :--- | :---: | :--- |
| **`bm_george`** | Male | Scholarly, classical British lecture | ~2.6 wps | Physics, logic, formal academia |
| **`bm_fable`** | Male | Theatrical, rich, resonant storyteller | ~2.4 wps | Epic narrative, myth, lore, history |
| **`bm_daniel`** | Male | Modern RP British, crisp, clean | ~2.8 wps | Contemporary tech documentaries |
| **`bm_lewis`** | Male | Warm, down-to-earth British | ~2.7 wps | Casual commentary, essays |
| **`bf_emma`** | Female | Sophisticated, calm, poised | ~2.6 wps | High-end scientific documentaries, nature |
| **`bf_alice`** | Female | Lively, direct, clear | ~2.8 wps | British educational series |
| **`bf_isabella`** | Female | Aristocratic, formal, elegant | ~2.5 wps | Period pieces, luxury showcases |
| **`bf_lily`** | Female | Gentle, soft, soothing | ~2.3 wps | Bedtime stories, relaxation |

---

### C. Other Supported Languages
* **Mandarin Chinese (`lang="z"`):** `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`
* **Japanese (`lang="j"`):** `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`
* **Hindi (`lang="h"`):** `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi`
* **Spanish (`lang="e"`):** `ef_dora`, `em_alex`, `em_santa`
* **Brazilian Portuguese (`lang="p"`):** `pf_dora`, `pm_alex`, `pm_santa`
* **Italian (`lang="i"`):** `if_sara`, `im_nicola`
* **French (`lang="f"`):** `ff_siwis`

---

## 2. Voice Blending Recipes & Best Practices

### How Blending Works
Kokoro synthesizes audio by multiplying phoneme tokens with style vector embeddings. Because all voice tensors share the exact dimension `[510, 1, 256]`, we can compute linear combinations:
$$\mathbf{v}_{\text{blend}} = w_1 \mathbf{v}_1 + w_2 \mathbf{v}_2 + \dots + w_n \mathbf{v}_n \quad \text{where} \quad \sum w_i = 1.0$$

### Curated High-Naturalness Blends
1. **The Financial Thriller / Crisis Voice:**
   `am_michael:0.70,am_adam:0.30`
   *Why it works:* Michael brings low-end chest resonance and emotional weight; Adam provides crisp consonant attacks so fast financial numbers remain completely legible.
2. **The Warm Educational Voice:**
   `af_bella:0.75,af_sarah:0.25`
   *Why it works:* Bella eliminates the clinical chill of pure didactic TTS; Sarah prevents Bella from sounding overly casual.
3. **The Epic Narrator:**
   `bm_fable:0.65,bm_george:0.35`
   *Why it works:* Fable gives theatrical gravitas; George adds scholarly British precision.
4. **The Mobile Retention Hook:**
   `am_adam:0.65,am_echo:0.35` (Male) or `af_nova:0.70,af_sky:0.30` (Female)
   *Why it works:* Sharp transients, high energy, and forward momentum tuned for short-form mobile attention spans.

### Blending Rules & Cautionary Guardrails
* **Always stay within the same language family** when blending (e.g. blend `lang="a"` with `lang="a"`, or `lang="b"` with `lang="b"`). Blending across languages can blur the G2P phoneme accents.
* **Dominant Voice Rule:** Keep one primary voice at 60–80% weight and secondary modifiers at 20–40%. Blending 50/50 across drastically different vocal tracts (e.g. deep male + high female) can occasionally yield uncanny phase interference.
