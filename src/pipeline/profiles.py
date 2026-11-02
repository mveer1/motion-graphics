"""Design profile helpers shared by scripts/design-dna.py, scripts/bakeoff.py and the catalogue.

Schema validity is necessary but not sufficient: the rules that keep measurement honest
(`measured` needs evidence, an extracted profile cannot claim `prescribed`, cross-references
resolve) are semantic and live here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "catalogue" / "schemas" / "design-profile.schema.json"
PROFILE_DIR = ROOT / "catalogue" / "data" / "design-profiles"
VOCAB_PATH = ROOT / "specs" / "motion-vocabulary.json"

FACT_SECTIONS = ("identity", "design_system", "motion", "audio_direction")
BASES = {"measured", "inferred", "subjective", "prescribed", "unknown"}


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iter_facts(node: Any, path: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield (dotted path, fact) for every leaf fact (string, or dict carrying 'basis')."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        if "basis" in node and ("value" in node or "hex" in node):
            yield path, node
            return
        for k, v in node.items():
            if k in ("measurement", "measured"):  # reproducibility blocks, not facts
                continue
            yield from iter_facts(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, (dict, str)) and not (isinstance(v, str) and path.endswith(("moves", "avoid", "vocabulary_ids"))):
                yield from iter_facts(v, f"{path}[{i}]")


def fact_basis(fact: Any, kind: str) -> str:
    if isinstance(fact, dict):
        return fact.get("basis", "unknown")
    return "prescribed"  # bare string: only legal on registry profiles


def schema_errors(profile: Dict[str, Any]) -> List[str]:
    import jsonschema

    v = jsonschema.Draft7Validator(load_json(SCHEMA_PATH))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message[:200]}" for e in sorted(v.iter_errors(profile), key=lambda e: list(e.absolute_path))]


def check_profile(profile: Dict[str, Any], styles: Dict[str, Any] | None = None, techniques: Dict[str, Any] | None = None,
                  sources: Dict[str, Any] | None = None, profiles: Dict[str, Any] | None = None) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings). Cross-reference dicts are optional; a check is skipped when absent."""
    errors: List[str] = []
    warns: List[str] = []
    kind = profile.get("kind")
    pid = profile.get("id", "?")

    n_facts = 0
    for section in FACT_SECTIONS:
        for path, fact in iter_facts(profile.get(section, {}), section):
            n_facts += 1
            if isinstance(fact, str):
                if kind != "registry":
                    errors.append(f"{pid}: {path}: bare string on a {kind} profile; use {{value, basis}} so the basis is stated")
                continue
            basis = fact.get("basis")
            if basis not in BASES:
                errors.append(f"{pid}: {path}: unknown basis {basis!r}")
            if basis == "measured" and not fact.get("evidence"):
                errors.append(f"{pid}: {path}: basis 'measured' requires an evidence pointer")
            if basis == "prescribed" and kind == "extracted":
                errors.append(f"{pid}: {path}: an extracted profile cannot use 'prescribed'")
            if basis == "unknown" and isinstance(fact.get("value"), (int, float)) and fact["value"] is not None:
                errors.append(f"{pid}: {path}: basis 'unknown' must not carry a number")
            if basis in ("inferred", "subjective") and "confidence" not in fact and kind == "extracted":
                warns.append(f"{pid}: {path}: {basis} fact without a confidence")
    for i, c in enumerate(profile.get("design_system", {}).get("palette", {}).get("colors", [])):
        if c.get("basis") == "measured" and not c.get("evidence"):
            errors.append(f"{pid}: design_system.palette.colors[{i}] {c.get('hex')}: measured colour needs evidence")
        if c.get("basis") == "prescribed" and kind == "extracted":
            errors.append(f"{pid}: palette colour {c.get('hex')}: an extracted profile cannot use 'prescribed'")
    if kind == "extracted":
        prov = profile.get("provenance", {})
        if not prov.get("reference_sources") and "image" not in prov.get("method", "") and "video" not in prov.get("method", ""):
            warns.append(f"{pid}: extracted profile names no reference source")
    if kind == "project" and not profile.get("extends"):
        warns.append(f"{pid}: project profile without 'extends' (stands alone)")

    if kind in ("registry", "project") and not profile.get("style"):
        errors.append(f"{pid}: a {kind} profile must name a style system")
    if styles is not None and profile.get("style") and profile.get("style") not in styles:
        errors.append(f"{pid}: style {profile.get('style')!r} is not a registered style")
    if techniques is not None:
        for t in profile.get("techniques", []):
            if t not in techniques:
                errors.append(f"{pid}: technique {t!r} not found in the catalogue")
    if sources is not None:
        for s in profile.get("provenance", {}).get("reference_sources", []):
            if s not in sources:
                errors.append(f"{pid}: reference source {s!r} not found")
    if profiles is not None and profile.get("extends") and profile["extends"] not in profiles:
        errors.append(f"{pid}: extends {profile['extends']!r} which is not a registered profile")
    if VOCAB_PATH.exists():
        vocab = {v["id"] for v in load_json(VOCAB_PATH)["vocabulary"]}
        for vid in profile.get("motion", {}).get("easing", {}).get("vocabulary_ids", []):
            if vid not in vocab:
                errors.append(f"{pid}: motion vocabulary id {vid!r} not in specs/motion-vocabulary.json")
    ids = [v["id"] for v in profile.get("scene_variants", [])]
    if len(ids) != len(set(ids)):
        errors.append(f"{pid}: duplicate scene_variants ids")
    if n_facts == 0:
        errors.append(f"{pid}: profile has no facts")
    return errors, warns


def load_registry(only_ids: bool = False) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if PROFILE_DIR.exists():
        for f in sorted(PROFILE_DIR.glob("*.json")):
            d = load_json(f)
            out[d["id"]] = d
    return out


def resolve(profile: Dict[str, Any], registry: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Apply a project profile's overrides on top of the registry profile it extends.

    Overrides are top-level sections merged key by key (dict) or replaced (everything else);
    the result keeps the project profile's id/kind so provenance is not lost.
    """
    base_id = profile.get("extends")
    if not base_id or base_id not in registry:
        return profile
    base = json.loads(json.dumps(registry[base_id]))

    def merge(a: Any, b: Any) -> Any:
        if isinstance(a, dict) and isinstance(b, dict) and not ("basis" in b and "value" in b):
            for k, v in b.items():
                a[k] = merge(a.get(k), v) if k in a else v
            return a
        return b

    for k, v in profile.items():
        if k in ("extends",):
            continue
        base[k] = merge(base.get(k), v) if k in base else v
    base["id"], base["kind"], base["extends"] = profile["id"], profile["kind"], base_id
    return base


PLAIN_LISTS = ("moves", "avoid", "vocabulary_ids", "preferred_asset_types", "runtime_capabilities", "formats")


def lift_strings(node: Any, evidence: str, key: str = "") -> Any:
    """Turn bare registry strings into explicit `prescribed` facts that point at the registry profile.

    A project profile may inherit a registry look, but it must say HOW each inherited value is known;
    this keeps 'authored rule' distinct from anything measured or judged for the project."""
    if isinstance(node, str):
        return {"value": node, "basis": "prescribed", "evidence": evidence}
    if isinstance(node, dict):
        if "basis" in node or "hex" in node:
            return node
        return {k: (v if k in ("measurement", "measured") else lift_strings(v, evidence, k)) for k, v in node.items()}
    if isinstance(node, list):
        return node if key in PLAIN_LISTS else [lift_strings(v, evidence, key) for v in node]
    return node
