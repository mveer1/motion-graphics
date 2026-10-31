#!/usr/bin/env python3
"""
preprocessor.py — Intelligent text preprocessing engine for Kokoro TTS.

Transforms raw input text into speech-optimized phonetically sound input:
1. Normalizes numbers, currencies, multipliers, percentages, and units into natural words.
2. Expands common abbreviations and initialisms cleanly.
3. Enhances punctuation (converting '--' to em-dashes '—', '...' to '…', smart breath commas).
4. Splits overly long sentences into natural breath groups.
5. Injects Misaki-compliant Markdown IPA phonetic annotations: [Word](/phonemes/).
6. Strips unwanted stage directions ([laughs], *sigh*, etc.) or converts explicit pauses.
"""

import re
from typing import List, Tuple, Dict, Any, Optional

# Standard abbreviation mappings
ABBREVIATIONS = {
    r"\be\.g\.,?": "for example,",
    r"\bi\.e\.,?": "that is,",
    r"\bvs\.?": "versus",
    r"\betc\.?": "etcetera",
    r"\bapprox\.?": "approximately",
    r"\bdept\.?": "department",
    r"\bgovt\.?": "government",
    r"\bno\.?\s*(\d+)": r"number \1",
    r"\bdr\.?\s+": "doctor ",
    r"\bmr\.?\s+": "mister ",
    r"\bmrs\.?\s+": "missus ",
    r"\bms\.?\s+": "mizz ",
    r"\bprof\.?\s+": "professor ",
}

# Technical initialisms that should be spoken letter-by-letter with pauses
INITIALISMS = {
    r"\bAI\b": "A.I.",
    r"\bML\b": "M.L.",
    r"\bAPI\b": "A.P.I.",
    r"\bAPIs\b": "A.P.I.s",
    r"\bTTS\b": "T.T.S.",
    r"\bGPU\b": "G.P.U.",
    r"\bGPUs\b": "G.P.U.s",
    r"\bCPU\b": "C.P.U.",
    r"\bCPUs\b": "C.P.U.s",
    r"\bETF\b": "E.T.F.",
    r"\bETFs\b": "E.T.F.s",
    r"\bGDP\b": "G.D.P.",
    r"\bIPO\b": "I.P.O.",
    r"\bIPOs\b": "I.P.O.s",
    r"\bSEC\b": "S.E.C.",
    r"\bFOMO\b": "fo-mo",
    r"\bUI\b": "U.I.",
    r"\bUX\b": "U.X.",
    r"\bHTML\b": "H.T.M.L.",
    r"\bCSS\b": "C.S.S.",
    r"\bJSON\b": "J-son",
    r"\bSQL\b": "sequel",
}

# Currencies
CURRENCY_MAP = {
    "$": "dollars",
    "€": "euros",
    "£": "pounds",
    "¥": "yen",
    "₹": "rupees",
}

DIGIT_WORDS = {
    0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four',
    5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine',
    10: 'ten', 11: 'eleven', 12: 'twelve', 13: 'thirteen',
    14: 'fourteen', 15: 'fifteen', 16: 'sixteen', 17: 'seventeen',
    18: 'eighteen', 19: 'nineteen', 20: 'twenty', 30: 'thirty',
    40: 'forty', 50: 'fifty', 60: 'sixty', 70: 'seventy',
    80: 'eighty', 90: 'ninety'
}

def int_to_words(n: int) -> str:
    """Converts small to medium integers to clean English words."""
    if n < 0:
        return f"negative {int_to_words(abs(n))}"
    if n in DIGIT_WORDS:
        return DIGIT_WORDS[n]
    if n < 100:
        tens = (n // 10) * 10
        ones = n % 10
        return f"{DIGIT_WORDS[tens]}-{DIGIT_WORDS[ones]}"
    if n < 1000:
        hundreds = n // 100
        rem = n % 100
        if rem == 0:
            return f"{DIGIT_WORDS[hundreds]} hundred"
        return f"{DIGIT_WORDS[hundreds]} hundred {int_to_words(rem)}"
    return str(n)

def decimal_to_spoken_words(num_str: str) -> str:
    """Converts '2.4' -> 'two point four', '0.5' -> 'zero point five'."""
    if '.' in num_str:
        parts = num_str.split('.', 1)
        whole_str = parts[0] or "0"
        frac_str = parts[1]
        try:
            w_int = int(whole_str)
            w_spoken = int_to_words(w_int)
        except ValueError:
            w_spoken = whole_str
        frac_spoken = " ".join(DIGIT_WORDS.get(int(ch), ch) for ch in frac_str)
        return f"{w_spoken} point {frac_spoken}"
    try:
        n = int(num_str)
        if n < 100:
            return int_to_words(n)
        return num_str
    except ValueError:
        return num_str

def clean_stage_directions(text: str) -> str:
    """
    Remove non-spoken stage cues, e.g. [laughs], (chuckles), *sighs*.
    Preserves [pause:0.5s] or [break:0.3s] markers as explicit pause tokens.
    """
    # Normalize explicit pause markers
    text = re.sub(r'\[(pause|break)\s*:\s*([0-9.]+)s?\]', r'__PAUSE_\2__', text, flags=re.IGNORECASE)
    # Strip markdown emphasis asterisks
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    # Strip brackets containing stage cues (unless it's an IPA link [word](/ipa/))
    text = re.sub(r'\[(?!\w+\]\(/[^)]+/\))[^\]]+\]', '', text)
    # Strip parentheticals that are purely stage directions
    stage_words = r'(?:laughs?|sighs?|cough|gasp|clears throat|giggle|whispers?|pause|chuckle)'
    text = re.sub(rf'\(\s*{stage_words}\s*\)', '', text, flags=re.IGNORECASE)
    return text.strip()

def normalize_currencies_and_magnitudes(text: str) -> str:
    """
    Convert $2.4T -> two point four trillion dollars
    Convert $500M -> five hundred million dollars
    Convert $50B  -> fifty billion dollars
    Convert $100k -> one hundred thousand dollars
    Convert $25   -> twenty-five dollars
    """
    magnitude_map = {
        'T': 'trillion',
        'B': 'billion',
        'M': 'million',
        'k': 'thousand',
        'K': 'thousand',
    }

    def _replace_currency_mag(match):
        symbol = match.group(1)
        number_str = match.group(2)
        mag = match.group(3)
        currency_name = CURRENCY_MAP.get(symbol, "dollars")
        mag_name = magnitude_map.get(mag, "")
        spoken_num = decimal_to_spoken_words(number_str)
        return f"{spoken_num} {mag_name} {currency_name}".strip()

    pattern_mag = re.compile(r'([$€£¥₹])\s*([0-9]+(?:\.[0-9]+)?)\s*([TBMkK])\b')
    text = pattern_mag.sub(_replace_currency_mag, text)

    def _replace_currency_simple(match):
        symbol = match.group(1)
        number_str = match.group(2)
        currency_name = CURRENCY_MAP.get(symbol, "dollars")
        spoken_num = decimal_to_spoken_words(number_str)
        return f"{spoken_num} {currency_name}"

    pattern_simple = re.compile(r'([$€£¥₹])\s*([0-9]+(?:\.[0-9]+)?)\b')
    text = pattern_simple.sub(_replace_currency_simple, text)

    # Standalone magnitudes: 2.4T -> two point four trillion
    def _replace_mag_standalone(match):
        number_str = match.group(1)
        mag = match.group(2)
        mag_name = magnitude_map.get(mag, "")
        spoken_num = decimal_to_spoken_words(number_str)
        return f"{spoken_num} {mag_name}"

    pattern_standalone = re.compile(r'\b([0-9]+(?:\.[0-9]+)?)\s*([TBMkK])\b')
    text = pattern_standalone.sub(_replace_mag_standalone, text)

    return text

def normalize_numbers_symbols(text: str) -> str:
    """
    Convert numbers and technical symbols into natural spoken English.
    """
    # Years: 2026 -> twenty twenty-six, 1999 -> nineteen ninety-nine
    def _replace_year_2000(match):
        decade = int(match.group(1))
        return f"twenty {int_to_words(decade)}"
    text = re.sub(r'\b20([2-9][0-9])\b', _replace_year_2000, text)

    def _replace_year_1900(match):
        decade = int(match.group(1))
        return f"nineteen {int_to_words(decade)}"
    text = re.sub(r'\b19([5-9][0-9])\b', _replace_year_1900, text)
    text = re.sub(r'\b19([5-9][0-9])s\b', r'nineteen \1s', text)

    # Leverage multipliers: 3x -> three times, 2.5x -> two point five times
    def _replace_multiplier(match):
        num_str = match.group(1)
        spoken_num = decimal_to_spoken_words(num_str)
        return f"{spoken_num} times"
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*[xX]\b', _replace_multiplier, text)
    
    # Percentages: 90% -> ninety percent, 2% -> two percent
    def _replace_percentage(match):
        num_str = match.group(1)
        spoken_num = decimal_to_spoken_words(num_str)
        return f"{spoken_num} percent"
    text = re.sub(r'([0-9]+(?:\.[0-9]+)?)\s*%', _replace_percentage, text)

    # Convert standalone decimals: 0.5 -> zero point five
    def _replace_standalone_decimal(match):
        return decimal_to_spoken_words(match.group(0))
    text = re.sub(r'\b[0-9]+\.[0-9]+\b', _replace_standalone_decimal, text)

    # Ratios and fractions: 1/L -> one over L, 1/2 -> one half
    text = re.sub(r'\b1/L\b', 'one over L', text)
    text = re.sub(r'\b1/2\b', 'one half', text)
    text = re.sub(r'\b1/4\b', 'one quarter', text)
    text = re.sub(r'\b3/4\b', 'three quarters', text)
    text = re.sub(r'\b([0-9]+)/([0-9]+)\b', r'\1 over \2', text)

    # Minus signs in loss contexts: -2% -> negative two percent
    text = re.sub(r'-\s*([0-9])', r'negative \1', text)

    # Common technical units
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*ms\b', r'\1 milliseconds', text)
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*s\b(?!\w)', r'\1 seconds', text)
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*fps\b', r'\1 frames per second', text)
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*kHz\b', r'\1 kilohertz', text)
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*GB\b', r'\1 gigabytes', text)
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*MB\b', r'\1 megabytes', text)
    text = re.sub(r'\b([0-9]+(?:\.[0-9]+)?)\s*km/h\b', r'\1 kilometers per hour', text)

    # Symbols: & -> and, @ -> at, + -> plus
    text = re.sub(r'\s+&\s+', ' and ', text)
    text = re.sub(r'\s+@\s+', ' at ', text)
    text = re.sub(r'\s*\+\s*', ' plus ', text)

    return text

def expand_abbreviations_and_initialisms(text: str) -> str:
    """Expand abbreviations and format initialisms for natural cadence."""
    for pattern, repl in ABBREVIATIONS.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    for pattern, repl in INITIALISMS.items():
        text = re.sub(pattern, repl, text)
    return text

def enhance_punctuation_and_prosody(text: str, preset: str = "conversational") -> str:
    """
    Enhance punctuation for Kokoro's neural prosody:
    - Normalizes '--' and space-padded hyphens ' - ' to em-dash '—'. Preserves word-internal hyphens (e.g. 'twenty-six').
    - Normalizes '...' to '…' (Unicode ellipsis triggers long trailing pause).
    - Adds natural breath commas after introductory transition adverbs.
    - Adjusts cadence based on preset.
    """
    # Replace double hyphens and isolated hyphens with em-dash
    text = re.sub(r'\s*--\s*', '—', text)
    text = re.sub(r'\s+-\s+', '—', text)
    text = re.sub(r'—+', '—', text)

    # Normalize ellipsis to unicode
    text = re.sub(r'\.{3,}', '…', text)

    # Insert breath commas after common introductory transition words if missing
    intro_transitions = [
        r'\bHowever\b(?!,)',
        r'\bMeanwhile\b(?!,)',
        r'\bIn fact\b(?!,)',
        r'\bSuddenly\b(?!,)',
        r'\bConsequently\b(?!,)',
        r'\bFurthermore\b(?!,)',
        r'\bSpecifically\b(?!,)',
        r'\bInitially\b(?!,)',
        r'\bEventually\b(?!,)',
        r'\bNaturally\b(?!,)',
    ]
    for pattern in intro_transitions:
        text = re.sub(pattern, r'\g<0>,', text)

    # Clean whitespace around punctuation
    text = re.sub(r'\s+([,.:;?!…])', r'\1', text)
    text = re.sub(r'([,;?!…])([^\s"\'’”\)])', r'\1 \2', text)
    text = re.sub(r'(?<![A-Z0-9])\.([^\s"\'’”\)0-9])', r'. \1', text)
    text = re.sub(r'\s+', ' ', text)

    # Preset specific tweaks
    if preset == "storytelling":
        text = re.sub(r',\s+(but\b|yet\b|then\b)', r'… \1', text, flags=re.IGNORECASE)
    elif preset == "energetic":
        text = text.replace('…', '—')

    return text.strip()

def segment_into_breath_groups(text: str, max_words: int = 18) -> List[Dict[str, Any]]:
    """
    Splits long run-on sentences into natural breath groups.
    Kokoro's voice quality degrades on long unbroken token runs (> 40 words or 510 tokens).
    Splits at natural semantic boundaries (commas, em-dashes, conjunctions).
    """
    raw_sentences = re.split(r'([.!?…]+(?:\s+|\n+|$))', text)
    
    segments = []
    i = 0
    while i < len(raw_sentences):
        sent_body = raw_sentences[i].strip()
        sent_punct = raw_sentences[i+1].strip() if i+1 < len(raw_sentences) else ""
        i += 2

        if not sent_body:
            continue

        full_sentence = (sent_body + (sent_punct if sent_punct and not sent_body.endswith(sent_punct) else "")).strip()

        # Check for explicit pause token
        pause_match = re.search(r'__PAUSE_([0-9.]+)__', full_sentence)
        if pause_match:
            pause_val = float(pause_match.group(1))
            clean_s = re.sub(r'__PAUSE_[0-9.]+__', '', full_sentence).strip()
            if clean_s:
                segments.append({"text": clean_s, "pause_after": pause_val, "type": "custom_pause"})
            continue

        words = full_sentence.split()
        if len(words) <= max_words:
            pause_time = 0.35 if sent_punct.startswith('…') else 0.30
            segments.append({"text": full_sentence, "pause_after": pause_time, "type": "sentence"})
        else:
            clauses = re.split(r'([,—]|\s+(?:and|but|while|because|which|where)\s+)', full_sentence)
            buffer = ""
            for c_idx, part in enumerate(clauses):
                if not part:
                    continue
                if len((buffer + " " + part).split()) > max_words and buffer.strip():
                    clean_chunk = buffer.strip().rstrip(' ,—') + ","
                    segments.append({
                        "text": clean_chunk,
                        "pause_after": 0.18,
                        "type": "clause"
                    })
                    buffer = part
                else:
                    buffer = (buffer + " " + part).strip() if buffer else part

            if buffer.strip():
                clean_tail = buffer.strip().rstrip(' ,—')
                if sent_punct and not clean_tail.endswith(sent_punct):
                    clean_tail += sent_punct
                segments.append({
                    "text": clean_tail,
                    "pause_after": 0.30,
                    "type": "sentence"
                })

    return segments

def preprocess_for_kokoro(
    text: str,
    preset: str = "conversational",
    custom_phonetics: Optional[Dict[str, str]] = None,
    max_words_per_segment: int = 18
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Master pipeline:
    1. Clean stage cues.
    2. Normalize currencies, numbers, multipliers, units.
    3. Expand abbreviations & initialisms.
    4. Enhance punctuation for prosody.
    5. Inject custom phonetics.
    6. Segment into breath groups.
    """
    text = clean_stage_directions(text)
    text = normalize_currencies_and_magnitudes(text)
    text = normalize_numbers_symbols(text)
    text = expand_abbreviations_and_initialisms(text)
    text = enhance_punctuation_and_prosody(text, preset=preset)

    if custom_phonetics:
        for word, ipa in custom_phonetics.items():
            pattern = rf'\b{re.escape(word)}\b'
            text = re.sub(pattern, f'[{word}](/{ipa}/)', text)

    segments = segment_into_breath_groups(text, max_words=max_words_per_segment)
    return text, segments


if __name__ == "__main__":
    sample = (
        "In early 2026, retail traders watched $2.4T vanish after an ordinary 2% dip. "
        "Why? Because when you trade with 3x leverage, algorithms trigger automatic liquidation (1/L collateral loss)! "
        "e.g., automated margin calls hit 30M phones simultaneously... and panic went viral."
    )
    norm, segs = preprocess_for_kokoro(sample, preset="documentary")
    print("--- NORMALIZED TEXT ---")
    print(norm)
    print("\n--- SEGMENTS (BREATH GROUPS) ---")
    for s in segs:
        print(f"[{s['type'].upper()} | +{s['pause_after']}s] {s['text']}")
