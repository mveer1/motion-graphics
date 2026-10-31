# Kokoro TTS Capabilities & Architecture Reference

This reference documents the empirical, code-verified capabilities, supported parameters, and limitations of **Kokoro TTS (v0.9.4)** running on Python 3.12 with PyTorch on Apple Silicon.

---

## 1. Ground Truth Capability Matrix

| Feature | Supported? | Implementation Mechanism | Notes & Guardrails |
| :--- | :---: | :--- | :--- |
| **SSML Tags** (`<break>`, `<prosody>`) | ❌ **NO** | N/A | **DO NOT USE.** Kokoro does not parse XML/SSML; it literally reads tags aloud as spoken text. |
| **Emotion Prompt Tags** (`[whisper]`, `[happy]`) | ❌ **NO** | N/A | Ignored by tokenizer or pronounced literally. Strip them out before inference. |
| **Markdown IPA Phonemes** | ✅ **YES** | `[Word](/IPA/)` via Misaki G2P | Natively parsed by Misaki in English (`lang='a'/'b'`). Example: `[ReLU](/ˈɹɛluː/)`. |
| **Pitch Inflection Tokens** | ✅ **YES** | `↓` (169), `→` (171), `↗` (172), `↘` (173) | Kokoro vocab includes pitch direction tokens. Can be placed inside IPA syntax (e.g. `[what?](/wˈɑt↗/)`). |
| **Punctuation Prosody** | ✅ **YES** | Model token vocabulary | Periods, commas, colons, semicolons, em-dashes (`—`), and unicode ellipses (`…`) dictate duration and intonation. |
| **Weighted Voice Blending** | ✅ **YES** | Style vector interpolation: $\sum w_i \mathbf{v}_i$ | Kokoro's `load_voice` accepts raw `torch.FloatTensor` of shape `[510, 1, 256]`. Custom blends allow smooth timbre mixing. |
| **Dynamic Speed Scaling** | ✅ **YES** | Float or `Callable[[int], float]` | Linearly scales duration inside `KModel.forward_with_tokens`. Safe range: `0.90x` to `1.20x`. |
| **Inter-Sentence Silence Padding** | ✅ **YES** | Context-aware acoustic buffers | Concatenating raw chunks without padding leads to breathless, robotic audio. Padding $\approx 200–400\text{ms}$ is essential. |

---

## 2. Punctuation Timing & Acoustic Impact

In Kokoro, punctuation marks directly alter phoneme tokens, pause lengths, and acoustic contours:

* **Full Stop (`.`):**
  - Triggers a full clause termination and intonation contour reset (~250–300ms pause).
  - Essential for preventing runaway pitch escalation across sentences.
* **Comma (`,`):**
  - Inserts a light breathing pause (~150ms shorter than a period) while maintaining forward pitch momentum.
  - Adding commas after introductory transitions (*"In early 2026,"*, *"However,"*, *"Specifically,"*) drastically improves natural cadence.
* **Unicode Ellipsis (`…`):**
  - Triggers a lingering dramatic pause (~500–800ms) with a natural decaying pitch slope.
  - Note: Standard three ascii dots (`...`) are converted by Misaki, but using single unicode `…` (token ID 10) ensures deterministic behavior.
* **Em-Dash (`—`):**
  - Produces an abrupt parenthetical hold without a falling pitch drop.
  - **CRITICAL WARNING:** Misaki G2P completely *drops* ascii double hyphens (`--`). Always normalize `--` to unicode em-dash `—` before sending to Kokoro!
* **Colon (`:`) & Semicolon (`;`):**
  - Semicolons provide a medium-length pause with neutral pitch.
  - Colons generate an anticipatory pitch lift.
* **Question Mark (`?`):**
  - Triggers an authentic rising pitch contour (upward inflection) on questions.
* **Exclamation Mark (`!`):**
  - Heightens energy, consonant attack punch, and pitch ceiling.

---

## 3. Style Vectors & Multi-Voice Blending

Every Kokoro voice profile is a tensor of shape `[510, 1, 256]` (corresponding to style embedding vectors for phoneme sequences up to 510 tokens).

### Single Voice vs. Blended Voice
While single voices sound decent, combining two complementary voice vectors creates richer vocal textures and softens synthetic artifacts:
$$\mathbf{v}_{\text{blend}} = \sum_{i=1}^{k} w_i \cdot \mathbf{v}_i \quad \text{where} \quad \sum_{i=1}^{k} w_i = 1.0$$

* **Resonant Bass + Technical Clarity:** `am_michael:0.70,am_adam:0.30` blends the cinematic gravitas of Michael with the crisp diction of Adam.
* **Conversational Warmth + Precision:** `af_bella:0.75,af_sarah:0.25` softens didactic speech with engaging warmth.

---

## 4. Hardware & Memory Invariants

* **Process Isolation:** Never run parallel Kokoro TTS synthesis processes on 8 GB Apple Silicon M2.
* **Format:** Output is standardized to **24,000 Hz, 16-bit Mono PCM WAV**.
* **Audio Mastering:** Applying a micro 4ms edge fade and a -1.0 dBFS limiter prevents zero-crossing clicks and digital clipping.
