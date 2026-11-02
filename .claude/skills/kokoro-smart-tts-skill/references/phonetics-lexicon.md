# Kokoro Phonetics & IPA Lexicon Guide

Misaki G2P (Kokoro's English phoneme frontend) natively supports Markdown custom IPA phonetic annotations:
`[Word](/IPA_PHONEMES/)`

When Kokoro encounters this syntax, it bypasses its dictionary lookup and directly injects your custom phonetic tokens into the model.

---

## 1. Syntax Rules

1. **Format:** `[SpokenText](/phoneme_symbols/)`
2. **Stress Markers:**
   * Primary stress: `ˈ` (Unicode `\u02c8`, placed before the stressed syllable)
   * Secondary stress: `ˌ` (Unicode `\u02cc`)
3. **Pitch & Intonation Markers:**
   * `↗` : Rising inflection (for questions / anticipation)
   * `↘` / `↓` : Falling inflection (for definitive statements)
   * `→` : Sustained level tone

---

## 2. Common Domain Dictionary

### Machine Learning & Tech
| Term | Raw Text | Smart Phonetic Syntax | Spoken Equivalent |
| :--- | :--- | :--- | :--- |
| **ReLU** | `ReLU` | `[ReLU](/ˈɹɛluː/)` | "ray-loo" |
| **Epoch** | `epoch` | `[epoch](/ˈɛpək/)` | "eh-puck" |
| **LaTeX** | `LaTeX` | `[LaTeX](/ˈlɑːtɛk/)` | "lah-tek" |
| **SQL** | `SQL` | `[SQL](/ˈsiːkwəl/)` | "sequel" |
| **Nvidia** | `Nvidia` | `[Nvidia](/ɛnˈvɪdiə/)` | "en-vid-ee-uh" |
| **Kokoro** | `Kokoro` | `[Kokoro](/kəˈkɔːɹoʊ/)` | "kuh-kor-oh" |
| **PyTorch** | `PyTorch` | `[PyTorch](/ˈpaɪtɔːɹtʃ/)` | "pie-torch" |
| **GSAP** | `GSAP` | `[GSAP](/ˈdʒiːsæp/)` | "gee-sap" |

### Finance & Economics
| Term | Raw Text | Smart Phonetic Syntax | Spoken Equivalent |
| :--- | :--- | :--- | :--- |
| **1/L** | `1/L` | `[1/L](/wˈʌn ˈoʊvəɹ ˈɛl/)` | "one over L" |
| **ETF** | `ETF` | `[ETF](/ˌiːtiːˈɛf/)` | "E.T.F." |
| **Deleveraging** | `deleveraging` | `[deleveraging](/diːˈlɛvəɹɪdʒɪŋ/)` | "dee-leveraging" |
| **FOMO** | `FOMO` | `[FOMO](/ˈfoʊmoʊ/)` | "fo-mo" |
| **HODL** | `HODL` | `[HODL](/ˈhɑːdəl/)` | "hod-ul" |

---

## 3. How to Pass Custom Dictionaries

You can pass a custom JSON dictionary to `smart_synth.py`:

```json
{
  "ReLU": "ˈɹɛluː",
  "Kokoro": "kəˈkɔːɹoʊ",
  "GSAP": "ˈdʒiːsæp"
}
```

Command:
```bash
python3.12 smart_synth.py --text "We built GSAP animations with ReLU activations." --out out.wav --phonetics-json custom_lexicon.json
```
