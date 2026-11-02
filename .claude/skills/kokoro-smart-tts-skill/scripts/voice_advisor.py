#!/usr/bin/env python3
"""
voice_advisor.py — Intelligent Voice Recommender & Multi-Voice Blender for Kokoro TTS.

Handles:
1. Recommending the best voice persona or blend based on project genre, tone, and platform.
2. Parsing weighted voice formulas (e.g. 'am_michael:0.75,am_adam:0.25').
3. Blending voice embedding tensors mathematically: v_blend = sum(w_i * v_i).
4. Providing detailed catalog metadata for all 54 Kokoro voices.
"""

from typing import Dict, List, Tuple, Optional, Union, Any
import torch

# Curated Signature Blends tested for high acoustic naturalness and reduced AI artifacts
SIGNATURE_RECIPES = {
    "documentary-thriller": {
        "voice": "am_michael:0.70,am_adam:0.30",
        "speed": 0.96,
        "sentence_pause": 0.38,
        "paragraph_pause": 0.65,
        "lang": "a",
        "description": "Deep resonant cinematic gravitas with crisp technical articulation. Ideal for finance crises, economics, and documentaries."
    },
    "warm-conversational": {
        "voice": "af_bella:0.75,af_sarah:0.25",
        "speed": 1.03,
        "sentence_pause": 0.28,
        "paragraph_pause": 0.50,
        "lang": "a",
        "description": "Engaging, approachable, and warm with analytical clarity. Ideal for product intros, tutorials, and lifestyle explainers."
    },
    "epic-storyteller": {
        "voice": "bm_fable:0.65,bm_george:0.35",
        "speed": 0.98,
        "sentence_pause": 0.42,
        "paragraph_pause": 0.75,
        "lang": "b",
        "description": "Theatrical British narration with scholarly enunciation and deep presence. Perfect for history, philosophy, and lore."
    },
    "energetic-reel": {
        "voice": "am_adam:0.65,am_echo:0.35",
        "speed": 1.15,
        "sentence_pause": 0.22,
        "paragraph_pause": 0.42,
        "lang": "a",
        "description": "Punchy, fast-paced modern delivery designed to maintain viewer retention on TikTok, Reels, and YouTube Shorts."
    },
    "energetic-reel-female": {
        "voice": "af_nova:0.70,af_sky:0.30",
        "speed": 1.14,
        "sentence_pause": 0.22,
        "paragraph_pause": 0.42,
        "lang": "a",
        "description": "Bright, high-energy modern female delivery with punchy consonants for short-form mobile."
    },
    "academic-explainer": {
        "voice": "af_sarah:0.70,bf_emma:0.30",
        "speed": 1.05,
        "sentence_pause": 0.32,
        "paragraph_pause": 0.55,
        "lang": "a",
        "description": "Meticulous, authoritative, and didactic tone suited for deep science, mathematics, and algorithms."
    },
    "technical-systems": {
        "voice": "am_adam:0.80,am_michael:0.20",
        "speed": 1.12,
        "sentence_pause": 0.30,
        "paragraph_pause": 0.50,
        "lang": "a",
        "description": "Clear neutral technical narration with extra vocal body. Default for motion graphics systems explainers."
    }
}

VOICE_PROFILES = {
    # American English (lang='a')
    "am_adam": {"lang": "a", "gender": "male", "timbre": "Neutral, grounded, technical", "pace": "Fast/Neutral"},
    "am_michael": {"lang": "a", "gender": "male", "timbre": "Deep, resonant, cinematic", "pace": "Deliberate"},
    "am_echo": {"lang": "a", "gender": "male", "timbre": "Modern, energetic, confident", "pace": "Brisk"},
    "am_eric": {"lang": "a", "gender": "male", "timbre": "Conversational, friendly", "pace": "Moderate"},
    "am_fenrir": {"lang": "a", "gender": "male", "timbre": "Gritty, intense, dramatic", "pace": "Moderate"},
    "am_liam": {"lang": "a", "gender": "male", "timbre": "Youthful, bright, modern", "pace": "Moderate"},
    "am_onyx": {"lang": "a", "gender": "male", "timbre": "Deep baritone, solemn", "pace": "Slow/Deliberate"},
    "am_puck": {"lang": "a", "gender": "male", "timbre": "Playful, animated, crisp", "pace": "Fast"},
    "af_bella": {"lang": "a", "gender": "female", "timbre": "Warm, engaging, expressive", "pace": "Moderate"},
    "af_sarah": {"lang": "a", "gender": "female", "timbre": "Analytical, precise, didactic", "pace": "Moderate"},
    "af_alloy": {"lang": "a", "gender": "female", "timbre": "Corporate, clear, steady", "pace": "Moderate"},
    "af_aoede": {"lang": "a", "gender": "female", "timbre": "Melodic, gentle, artistic", "pace": "Moderate"},
    "af_heart": {"lang": "a", "gender": "female", "timbre": "Soft, empathetic, intimate", "pace": "Slow"},
    "af_jessica": {"lang": "a", "gender": "female", "timbre": "Casual, upbeat, friendly", "pace": "Moderate"},
    "af_kore": {"lang": "a", "gender": "female", "timbre": "Poised, measured, articulate", "pace": "Moderate"},
    "af_nicole": {"lang": "a", "gender": "female", "timbre": "Broadcaster, polished, confident", "pace": "Moderate"},
    "af_nova": {"lang": "a", "gender": "female", "timbre": "Punchy, dynamic, sharp", "pace": "Fast"},
    "af_river": {"lang": "a", "gender": "female", "timbre": "Nuanced, atmospheric, storyteller", "pace": "Deliberate"},
    "af_sky": {"lang": "a", "gender": "female", "timbre": "Breezy, natural, light", "pace": "Moderate"},
    # British English (lang='b')
    "bm_george": {"lang": "b", "gender": "male", "timbre": "Scholarly, refined, articulate", "pace": "Deliberate"},
    "bm_fable": {"lang": "b", "gender": "male", "timbre": "Theatrical, rich, storytelling", "pace": "Deliberate"},
    "bm_daniel": {"lang": "b", "gender": "male", "timbre": "Calm, clean RP British", "pace": "Moderate"},
    "bm_lewis": {"lang": "b", "gender": "male", "timbre": "Down-to-earth, sincere British", "pace": "Moderate"},
    "bf_emma": {"lang": "b", "gender": "female", "timbre": "Sophisticated, poised, calm", "pace": "Deliberate"},
    "bf_alice": {"lang": "b", "gender": "female", "timbre": "Direct, lively, clear", "pace": "Moderate"},
    "bf_isabella": {"lang": "b", "gender": "female", "timbre": "Formal, aristocratic, elegant", "pace": "Moderate"},
    "bf_lily": {"lang": "b", "gender": "female", "timbre": "Gentle, soothing, soft", "pace": "Slow"}
}

def parse_voice_weights(voice_spec: str) -> Dict[str, float]:
    """
    Parse a voice specification string into a normalized dictionary of weights.
    Examples:
      'am_adam' -> {'am_adam': 1.0}
      'am_adam,am_michael' -> {'am_adam': 0.5, 'am_michael': 0.5}
      'am_michael:0.75,am_adam:0.25' -> {'am_michael': 0.75, 'am_adam': 0.25}
    """
    parts = [p.strip() for p in voice_spec.split(',') if p.strip()]
    weights = {}
    
    has_explicit_weights = any(':' in p for p in parts)
    
    if not has_explicit_weights:
        # Equal weights
        equal_w = 1.0 / len(parts)
        for p in parts:
            weights[p] = equal_w
    else:
        for p in parts:
            if ':' in p:
                name, w_str = p.split(':', 1)
                weights[name.strip()] = float(w_str.strip())
            else:
                weights[p] = 1.0
        # Normalize weights so sum == 1.0
        total = sum(weights.values())
        if total > 0:
            for k in weights:
                weights[k] /= total

    return weights

def blend_voice_tensors(pipe, voice_weights: Dict[str, float]) -> torch.FloatTensor:
    """
    Load individual voice tensors and compute their normalized weighted combination.
    Each voice tensor has shape [510, 1, 256].
    """
    if len(voice_weights) == 1:
        voice_name = next(iter(voice_weights))
        return pipe.load_single_voice(voice_name)

    blended = None
    for name, weight in voice_weights.items():
        pack = pipe.load_single_voice(name)
        if blended is None:
            blended = pack.clone().float() * weight
        else:
            blended += pack.float() * weight

    return blended

def recommend_voice(
    genre: str,
    tone: Optional[str] = None,
    gender: Optional[str] = None,
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recommends a recipe or voice based on creative requirements.
    """
    genre_lower = genre.lower() if genre else ""
    tone_lower = tone.lower() if tone else ""
    platform_lower = platform.lower() if platform else ""

    # Short-form reels / TikTok / Shorts
    if "reel" in platform_lower or "tiktok" in platform_lower or "short" in platform_lower or "fast" in tone_lower:
        if gender == "female":
            return SIGNATURE_RECIPES["energetic-reel-female"]
        return SIGNATURE_RECIPES["energetic-reel"]

    # Documentary, crisis, tension, finance crash
    if any(k in genre_lower or k in tone_lower for k in ["crash", "crisis", "documentary", "thriller", "drama", "tension"]):
        return SIGNATURE_RECIPES["documentary-thriller"]

    # Storytelling, fiction, lore
    if any(k in genre_lower or k in tone_lower for k in ["story", "fable", "history", "lore", "narrative"]):
        return SIGNATURE_RECIPES["epic-storyteller"]

    # Warm educational or tutorial
    if any(k in genre_lower or k in tone_lower for k in ["tutorial", "product", "warm", "conversational", "lifestyle"]):
        return SIGNATURE_RECIPES["warm-conversational"]

    # Science / academic
    if any(k in genre_lower or k in tone_lower for k in ["academic", "proof", "math", "lecture", "research"]):
        return SIGNATURE_RECIPES["academic-explainer"]

    # Default technical systems explainer
    return SIGNATURE_RECIPES["technical-systems"]


if __name__ == "__main__":
    import json
    print("--- SIGNATURE BLENDS ---")
    for name, rec in SIGNATURE_RECIPES.items():
        print(f"[{name.upper()}] Voice: {rec['voice']} | Speed: {rec['speed']}x")
        print(f"   -> {rec['description']}\n")

    test_spec = "am_michael:0.7,am_adam:0.3"
    print("Parsed weights for", test_spec, ":", parse_voice_weights(test_spec))
