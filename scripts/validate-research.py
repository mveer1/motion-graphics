#!/usr/bin/env python3
"""
validate-research.py
Validates a project's research.json dossier against specs/research-spec.json.

Usage:
    python3 scripts/validate-research.py projects/benchmark-neural-network/research.json
    python3 scripts/validate-research.py projects/benchmark-neural-network
"""

import sys
import os
import shutil
import json
from pathlib import Path

# Auto-delegate to Python 3.12 on Apple Silicon macOS if current python lacks jsonschema
if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import jsonschema
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

try:
    import jsonschema
except ImportError:
    print("Error: 'jsonschema' package is required. Install via: pip install jsonschema")
    sys.exit(1)


def find_files(target_arg: str):
    root = Path(__file__).resolve().parent.parent
    schema_path = root / "specs" / "research-spec.json"
    
    target = Path(target_arg).resolve()
    if target.is_dir():
        research_path = target / "research.json"
    else:
        research_path = target
        
    return schema_path, research_path


def validate_research(schema_path: Path, research_path: Path) -> bool:
    if not schema_path.exists():
        print(f"Schema file not found at: {schema_path}")
        return False
        
    if not research_path.exists():
        print(f"Research dossier not found at: {research_path}")
        return False

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Failed to read schema JSON: {e}")
        return False

    try:
        with open(research_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read research JSON: {e}")
        return False

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

    if errors:
        print(f"Validation FAILED for: {research_path.name} ({len(errors)} error(s) found)")
        print("-" * 60)
        for i, err in enumerate(errors, 1):
            path_str = " -> ".join([str(p) for p in err.path]) if err.path else "root"
            print(f"  {i}. [{path_str}] {err.message}")
        print("-" * 60)
        return False

    # Summary report
    meta = data.get("metadata", {})
    pedagogy = data.get("pedagogy", {})
    truth = data.get("ground_truth", {})
    metaphors = data.get("visual_metaphors", [])
    acoustic = data.get("acoustic_guidance", {})
    scenes = data.get("scene_blueprint", [])

    print("=" * 60)
    print(f"RESEARCH DOSSIER VALIDATION PASSED: {meta.get('title')}")
    print("=" * 60)
    print(f"  • Topic ID:          {meta.get('topic_id')}")
    print(f"  • Domain:            {meta.get('domain')} ({meta.get('difficulty')})")
    print(f"  • Target Runtime:    {meta.get('target_duration_sec', {}).get('target')}s (range: {meta.get('target_duration_sec', {}).get('min')}-{meta.get('target_duration_sec', {}).get('max')}s)")
    print(f"  • Verified Claims:   {len(pedagogy.get('verified_claims', []))}")
    print(f"  • Math Entities:     {len(truth.get('entities', []))}")
    print(f"  • Equations:         {len(truth.get('equations', []))}")
    print(f"  • Visual Metaphors:  {len(metaphors)}")
    print(f"  • Voice / Speed:     {acoustic.get('recommended_voice')} @ {acoustic.get('speech_rate')}x")
    print(f"  • Phonetic Terms:    {len(acoustic.get('phonetic_lexicon', []))}")
    print(f"  • Scene Blueprints:  {len(scenes)} scenes")
    print("=" * 60)
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate-research.py <path_to_research.json | project_dir>")
        sys.exit(1)
        
    schema_p, research_p = find_files(sys.argv[1])
    success = validate_research(schema_p, research_p)
    sys.exit(0 if success else 1)

