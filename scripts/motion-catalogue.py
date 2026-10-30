#!/usr/bin/env python3
"""
scripts/motion-catalogue.py
Lightweight CLI to manage, validate, and search the Motion Graphics Capability Catalogue.

Features:
- Search by capability, visual intent, tags, compatibility, and approval status.
- Inspect full record definitions, parameters, and code snippets.
- Validate records against JSON schemas, detect broken cross-references, and check duplicate IDs.
- Compile aggregated catalogue index.

Usage:
    python3 scripts/motion-catalogue.py search --query "crossfade"
    python3 scripts/motion-catalogue.py search --type effect --tag data-flow
    python3 scripts/motion-catalogue.py search --status approved --compat low-memory
    python3 scripts/motion-catalogue.py get zero-dip-scene-transition
    python3 scripts/motion-catalogue.py list
    python3 scripts/motion-catalogue.py validate
    python3 scripts/motion-catalogue.py export
"""

import sys
import os
import re
import shutil
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Auto-delegate to Python 3.12 if current python lacks jsonschema
if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import jsonschema
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_DIR = REPO_ROOT / "catalogue"
SCHEMAS_DIR = CATALOGUE_DIR / "schemas"
DATA_DIR = CATALOGUE_DIR / "data"

COLLECTIONS = [
    "libraries",
    "effects",
    "recipes",
    "skills",
    "tools",
    "agents",
    "integrations",
    "shared",
    "primitives",
    "compositions",
    "project-templates",
    "styles",
    "references",
    "reference-sources"
]

# Collection -> schema file. Component collections share component.schema.json.
SCHEMA_FILES = {
    "libraries": "library.schema.json",
    "effects": "effect.schema.json",
    "recipes": "recipe.schema.json",
    "primitives": "primitive.schema.json",
    "compositions": "composition.schema.json",
    "project-templates": "project-template.schema.json",
    "styles": "style.schema.json",
    "references": "reference.schema.json",
    "reference-sources": "reference-source.schema.json",
    "skills": "component.schema.json",
    "tools": "component.schema.json",
    "agents": "component.schema.json",
    "integrations": "component.schema.json",
    "shared": "component.schema.json",
}

SINGULAR = {
    "libraries": "library", "effects": "effect", "recipes": "recipe", "skills": "skill", "tools": "tool",
    "agents": "agent", "integrations": "integration", "shared": "shared", "primitives": "primitive",
    "compositions": "composition", "project-templates": "template", "styles": "style", "references": "reference",
    "reference-sources": "source",
}

# Searchable capability layers (CLI --type values map onto these collections). Technique records
# live in references/ (type reference or technique); supplied reference videos in reference-sources/.
CAPABILITY_TYPES = {
    "library": "libraries", "effect": "effects", "recipe": "recipes", "primitive": "primitives",
    "composition": "compositions", "template": "project-templates", "style": "styles", "reference": "references",
    "technique": "references", "source": "reference-sources",
}

STATUS_RANK = {"blocked": 0, "deprecated": 0, "proposed": 1, "experimental": 2, "approved": 3}


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_records() -> Dict[str, Dict[str, Any]]:
    records = {c: {} for c in COLLECTIONS}
    for coll in COLLECTIONS:
        coll_dir = DATA_DIR / coll
        if coll_dir.exists():
            for p in sorted(coll_dir.glob("*.json")):
                data = load_json(p)
                records[coll][data["id"]] = data
    return records


def format_table(rows: List[List[str]], headers: List[str]) -> str:
    if not rows:
        return "No matching records found."
    
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
            
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * widths[i] for i in range(len(headers)))
    
    body_lines = []
    for row in rows:
        body_lines.append(" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)))
        
    return f"{header_line}\n{sep_line}\n" + "\n".join(body_lines)


def technique_lifecycle(ref: Dict[str, Any]) -> str:
    """observed -> specified -> prototyped -> tested -> approved, derived from stored fields."""
    if ref.get("status") == "approved":
        return "approved"
    state = ref.get("implementation_state")
    vstate = ref.get("validation", {}).get("state", "none")
    if state in ("prototyped", "implemented") and vstate in ("preview", "render"):
        return f"tested ({vstate})"
    return {"observed": "observed", "documented": "specified", "prototyped": "prototyped",
            "implemented": "implemented (untested)"}.get(state, str(state))


def validate_knowledge_base(records: Dict[str, Dict[str, Any]], all_ids: Dict[str, str],
                            errors: List[str], warnings: List[str]) -> None:
    """Technique records (references/) and reference sources (reference-sources/): links and honesty rules."""
    techniques = records.get("references", {})
    sources = records.get("reference-sources", {})
    related_colls = {"techniques": "references", "effects": "effects", "compositions": "compositions",
                     "templates": "project-templates", "styles": "styles"}
    for ref_id, ref in techniques.items():
        state = ref.get("implementation_state")
        val = ref.get("validation", {})
        vstate = val.get("state", "none")
        evidence = val.get("evidence", [])
        if vstate != "none" and not evidence:
            errors.append(f"Technique '{ref_id}' claims {vstate} validation without evidence")
        if vstate != "none" and state in ("observed", "documented"):
            errors.append(f"Technique '{ref_id}' has validation evidence but is only {state}; set prototyped or implemented")
        if ref.get("status") == "approved" and vstate != "render":
            errors.append(f"Technique '{ref_id}' cannot be approved without render-host validation (validation.state 'render')")
        for ev in evidence:
            if not ev["path"].startswith(("http://", "https://")) and not (REPO_ROOT / ev["path"]).exists():
                warnings.append(f"Technique '{ref_id}' evidence path '{ev['path']}' does not exist in this checkout")
        prov = ref.get("provenance", [])
        if prov and not ref.get("source", {}).get("inspected"):
            errors.append(f"Technique '{ref_id}' cites reference provenance but source.inspected is false")
        for p in prov:
            src = sources.get(p["source_id"])
            if src is None:
                errors.append(f"Technique '{ref_id}' provenance cites unknown reference source '{p['source_id']}'")
                continue
            if src.get("analysis", {}).get("state") not in ("inspected", "reviewed"):
                errors.append(f"Technique '{ref_id}' cites '{p['source_id']}', which has not been inspected")
            dur = src.get("media", {}).get("duration_sec", 0)
            if any(t > dur + 0.5 for t in p["timestamps"]):
                errors.append(f"Technique '{ref_id}' cites a timestamp beyond the end of '{p['source_id']}' ({dur}s)")
            if ref_id not in {t["id"] for t in src.get("techniques", [])}:
                warnings.append(f"Reference source '{p['source_id']}' does not list technique '{ref_id}' that cites it")
        for key, coll in related_colls.items():
            for rid in ref.get("related", {}).get(key, []):
                if rid not in records.get(coll, {}):
                    errors.append(f"Technique '{ref_id}' related.{key} lists unknown id '{rid}'")
        for c in ref.get("combines_with", []):
            if c["id"] not in techniques:
                errors.append(f"Technique '{ref_id}' combines_with unknown technique '{c['id']}'")
        cap = ref.get("capability", {})
        for cid in cap.get("compatible_components", []):
            if cid not in all_ids:
                errors.append(f"Technique '{ref_id}' capability lists unknown component '{cid}'")
        res = cap.get("resources", {})
        if res.get("basis") == "measured" and not res.get("measurements"):
            errors.append(f"Technique '{ref_id}' claims measured resources without measurements")
        if state == "implemented" and cap.get("support") in ("additional-dependencies", "research-required"):
            warnings.append(f"Technique '{ref_id}' is implemented but marked '{cap['support']}'; use 'approximation' if the code approximates it")
    for src_id, src in sources.items():
        a = src.get("analysis", {})
        st = a.get("state")
        if not src_id.endswith(src.get("source", {}).get("sha256", "")[:10]):
            errors.append(f"Reference source '{src_id}' id does not match its content hash")
        if st in ("automated", "inspected", "reviewed") and not src.get("automated"):
            errors.append(f"Reference source '{src_id}' is '{st}' but has no automated evidence block")
        if st in ("inspected", "reviewed") and not (a.get("inspected_on") and a.get("method") and a.get("concept")):
            errors.append(f"Reference source '{src_id}' is '{st}' without inspected_on, method and concept")
        if src.get("status") in ("experimental", "approved") and st not in ("inspected", "reviewed"):
            errors.append(f"Reference source '{src_id}' is {src['status']} but its analysis is only '{st}'")
        if src.get("status") == "approved" and st != "reviewed":
            errors.append(f"Reference source '{src_id}' cannot be approved before a person reviews the analysis")
        rights = src.get("rights", {})
        if rights.get("usage") == "inspiration-only" and any(b.get("policy") == "authorised" for b in rights.get("brand_assets", [])):
            errors.append(f"Reference source '{src_id}' authorises brand assets while usage is inspiration-only")
        dur = src.get("media", {}).get("duration_sec", 0)
        for t in src.get("techniques", []):
            tech = techniques.get(t["id"])
            if tech is None:
                errors.append(f"Reference source '{src_id}' lists unknown technique '{t['id']}'")
                continue
            if any(x > dur + 0.5 for x in t["timestamps"]):
                errors.append(f"Reference source '{src_id}' technique '{t['id']}' has a timestamp beyond {dur}s")
            if src_id not in {p["source_id"] for p in tech.get("provenance", [])}:
                warnings.append(f"Technique '{t['id']}' does not cite reference source '{src_id}' that lists it")
        for key, coll in (("effects", "effects"), ("compositions", "compositions"), ("templates", "project-templates"), ("styles", "styles")):
            for rid in src.get("related", {}).get(key, []):
                if rid not in records.get(coll, {}):
                    errors.append(f"Reference source '{src_id}' related.{key} lists unknown id '{rid}'")


_SUFFIXES = ("ations", "ation", "ings", "ing", "ed", "es", "s")


def stem(word: str) -> str:
    for suf in _SUFFIXES:
        if len(word) > len(suf) + 3 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def query_tokens(text: str) -> List[str]:
    """Stemmed query terms; hyphenated terms (light-theme, 2.5d-depth) stay phrases."""
    stop = {"a", "an", "and", "the", "of", "to", "in", "on", "for", "with", "by", "from", "that", "find", "show",
            "me", "is", "are", "which", "what", "use", "uses", "using", "work", "well", "between", "examples",
            "references", "reference", "videos", "video", "techniques", "technique", "interesting", "appropriate"}
    out = []
    for raw in re.findall(r"[a-z0-9.]+(?:-[a-z0-9.]+)*", (text or "").lower()):
        raw = raw.strip(".")
        if "-" in raw:
            parts = [p for p in raw.split("-") if p]
            out.append(" ".join(parts[:-1] + [stem(parts[-1])]))
        elif raw and raw not in stop and len(raw) > 1:
            out.append(stem(raw))
    return out


def has_term(term: str, text: str) -> bool:
    """Term matches at the start of a word (plurals and suffixes allowed, 'light' not in 'highlight')."""
    return re.search(r"(?<![a-z0-9])" + re.escape(term), text) is not None


def searchable_text(coll: str, rec_id: str, rec: Dict[str, Any]) -> str:
    parts = [rec_id, rec.get("name", ""), rec.get("category", "") or rec.get("kind", "") or rec.get("deliverable_type", "") or rec.get("mode", ""),
             rec.get("visual_intent") or rec.get("justification") or rec.get("description") or rec.get("purpose") or rec.get("technique") or "",
             rec.get("implementation_summary", ""), " ".join(rec.get("suitable_for", [])), " ".join(str(t) for t in rec.get("tags", []))]
    if coll == "libraries":
        parts.append(" ".join(str(t) for t in rec.get("metadata", {}).get("tags", [])))
    if coll == "compositions":
        parts += [rec.get("layout_notes", ""), rec.get("implementation", {}).get("api", "")]
    if coll == "effects":
        parts.append(rec.get("runtime_api", ""))
    if coll == "references":
        cap = rec.get("capability", {})
        parts += [rec.get("technique", ""), rec.get("visual_behaviour", ""), rec.get("mechanics", ""),
                  " ".join(rec.get("use_cases", [])), cap.get("support", ""), rec.get("decomposition", {}).get("timing", ""),
                  " ".join(rec.get("implemented_by", [])), " ".join(p["observed"] for p in rec.get("provenance", []))]
    if coll == "reference-sources":
        a = rec.get("analysis", {})
        parts += [" ".join(rec.get("categories", [])), " ".join(t["id"] for t in rec.get("techniques", []))]
        for key in ("concept", "communication_style"):
            parts += [a.get(key, {}).get("observed", ""), a.get(key, {}).get("interpreted", "")]
        parts += [n.get("observed", "") for n in a.get("aspects", {}).values()]
        for ids in rec.get("related", {}).values():
            parts.append(" ".join(ids))
    return " ".join(p for p in parts if p).lower().replace("-", " ")


def matches(tokens: List[str], text: str) -> bool:
    return all(has_term(t, text) for t in tokens)


def validate_catalogue(verbose: bool = True) -> bool:
    records = load_all_records()
    errors = []
    warnings = []

    allowed_statuses = {"proposed", "experimental", "approved", "deprecated", "blocked"}

    # 1. Schema Validation (every collection that has a schema)
    if HAS_JSONSCHEMA:
        schema_cache = {}
        for coll, schema_file in SCHEMA_FILES.items():
            path = SCHEMAS_DIR / schema_file
            if not path.exists():
                warnings.append(f"Schema {schema_file} missing; skipped validation of '{coll}'.")
                continue
            schema = schema_cache.setdefault(schema_file, load_json(path))
            for rec_id, rec_data in records[coll].items():
                try:
                    jsonschema.validate(instance=rec_data, schema=schema)
                except jsonschema.ValidationError as e:
                    errors.append(f"{SINGULAR[coll].capitalize()} '{rec_id}' schema error: {e.message}")
    else:
        warnings.append("jsonschema package not installed; skipped formal JSON Schema draft-07 check.")

    # 2. Check Valid Statuses
    for rtype, collection in records.items():
        for rec_id, rec_data in collection.items():
            st = rec_data.get("status")
            if st not in allowed_statuses:
                errors.append(f"{SINGULAR[rtype].capitalize()} '{rec_id}' has invalid status '{st}'. Must be one of {allowed_statuses}")

    # 3. Check Duplicate IDs across types (strict uniqueness)
    all_ids = {}
    for rtype, collection in records.items():
        for rec_id in collection:
            if rec_id in all_ids:
                errors.append(f"Duplicate ID '{rec_id}' found in '{rtype}' (previously registered in '{all_ids[rec_id]}')")
            else:
                all_ids[rec_id] = rtype

    # 4. Cross-Reference Validation
    # Effect -> Libraries
    for eff_id, eff_data in records["effects"].items():
        for dep in eff_data.get("library_dependencies", []):
            if dep not in records["libraries"]:
                errors.append(f"Effect '{eff_id}' references non-existent library dependency '{dep}'")
        for rec in eff_data.get("recipes", []):
            if rec not in records["recipes"]:
                errors.append(f"Effect '{eff_id}' references non-existent recipe '{rec}'")

    # Recipe -> Effect
    for rec_id, rec_data in records["recipes"].items():
        parent_eff = rec_data.get("effect_id")
        if parent_eff not in records["effects"]:
            errors.append(f"Recipe '{rec_id}' references non-existent parent effect '{parent_eff}'")
        else:
            # Check bidirectional link: parent effect should list this recipe
            if rec_id not in records["effects"][parent_eff].get("recipes", []):
                warnings.append(f"Effect '{parent_eff}' does not list child recipe '{rec_id}' in its 'recipes' array.")

    # Library -> Effects provided
    for lib_id, lib_data in records["libraries"].items():
        for eff in lib_data.get("effects_provided", []):
            if eff not in records["effects"]:
                errors.append(f"Library '{lib_id}' references non-existent provided effect '{eff}'")

    # Effect -> Primitives
    for eff_id, eff_data in records["effects"].items():
        for prim in eff_data.get("primitives", []):
            if prim not in records["primitives"]:
                errors.append(f"Effect '{eff_id}' references non-existent primitive '{prim}'")

    # Primitive -> Libraries
    for prim_id, prim in records["primitives"].items():
        for dep in prim.get("library_dependencies", []):
            if dep not in records["libraries"]:
                errors.append(f"Primitive '{prim_id}' references non-existent library '{dep}'")

    # Approval constraint: a component may not depend on anything less mature than itself
    # (approved -> approved only; experimental -> experimental/approved; nothing active -> blocked/deprecated).
    def check_dep(kind: str, rec_id: str, status: str, dep_coll: str, dep_id: str) -> None:
        dep = records[dep_coll].get(dep_id)
        if dep is None:
            errors.append(f"{kind} '{rec_id}' references non-existent {SINGULAR[dep_coll]} '{dep_id}'")
            return
        if status in {"approved", "experimental"} and STATUS_RANK[dep["status"]] < STATUS_RANK[status]:
            errors.append(f"{kind} '{rec_id}' ({status}) depends on {SINGULAR[dep_coll]} '{dep_id}' ({dep['status']})")

    for comp_id, comp in records["compositions"].items():
        uses = comp.get("uses", {})
        for p in uses.get("primitives", []):
            check_dep("Composition", comp_id, comp["status"], "primitives", p)
        for e in uses.get("effects", []):
            check_dep("Composition", comp_id, comp["status"], "effects", e)
        for r in uses.get("recipes", []):
            check_dep("Composition", comp_id, comp["status"], "recipes", r)
        for s in comp.get("styles_tested", []):
            if s not in records["styles"]:
                errors.append(f"Composition '{comp_id}' lists unknown style '{s}'")

    for tpl_id, tpl in records["project-templates"].items():
        if tpl["status"] == "proposed":
            continue
        check_dep("Template", tpl_id, tpl["status"], "styles", tpl["default_style"])
        for c in tpl.get("compositions", []):
            check_dep("Template", tpl_id, tpl["status"], "compositions", c)
        for e in tpl.get("effects", []):
            check_dep("Template", tpl_id, tpl["status"], "effects", e)

    defaults = [s for s, rec in records["styles"].items() if rec.get("default")]
    if records["styles"] and len(defaults) != 1:
        errors.append(f"Exactly one style system must be marked default (found {defaults or 'none'})")

    implementers = {}
    for coll in ("effects", "recipes", "compositions", "primitives"):
        implementers.update({k: coll for k in records[coll]})
    for ref_id, ref in records["references"].items():
        state = ref.get("implementation_state")
        impl = ref.get("implemented_by", [])
        for target in impl:
            if target not in implementers:
                errors.append(f"Reference '{ref_id}' implemented_by unknown component '{target}'")
        if state == "implemented" and not impl:
            errors.append(f"Reference '{ref_id}' is 'implemented' but lists no implementing component")
        if state in ("documented", "observed") and impl:
            warnings.append(f"Reference '{ref_id}' is '{state}' yet lists implementers; set implementation_state.")
        if ref.get("status") == "approved" and state != "implemented":
            errors.append(f"Reference '{ref_id}' cannot be approved while only {state}")
        if ref.get("source", {}).get("inspected") and not ref.get("source", {}).get("inspected_on"):
            errors.append(f"Reference '{ref_id}' claims inspection without an inspected_on date")
    validate_knowledge_base(records, all_ids, errors, warnings)

    # 5. Licensing Check
    for lib_id, lib_data in records["libraries"].items():
        lic = lib_data.get("licensing", {})
        if lic.get("status") not in {"verified", "unverified"}:
            errors.append(f"Library '{lib_id}' licensing.status must be 'verified' or 'unverified'")
        if lic.get("status") == "unverified" and lib_data.get("status") == "approved":
            errors.append(f"Library '{lib_id}' cannot be 'approved' with unverified licensing.")

    # Reporting
    if verbose:
        print("=" * 65)
        print("MOTION GRAPHICS CAPABILITY CATALOGUE AUDIT")
        print("=" * 65)
        print(f"Libraries: {len(records['libraries'])}")
        print(f"Effects:   {len(records['effects'])}")
        print(f"Recipes:   {len(records['recipes'])}")
        print(f"Primitives: {len(records['primitives'])} | Compositions: {len(records['compositions'])} | "
              f"Templates: {len(records['project-templates'])} | Styles: {len(records['styles'])} | "
              f"References: {len(records['references'])} | Sources: {len(records['reference-sources'])}")
        print("-" * 65)
        
        if warnings:
            print("WARNINGS:")
            for w in warnings:
                print(f"  [WARN] {w}")
            print("-" * 65)

        if errors:
            print("VALIDATION FAILED:")
            for e in errors:
                print(f"  [FAIL] {e}")
            print("=" * 65)
            return False
        else:
            print("[PASS] All records, schemas, and cross-references are valid.")
            print("=" * 65)
            return True

    return len(errors) == 0


def search_catalogue(
    query: Optional[str] = None,
    rec_type: str = "all",
    status: Optional[str] = None,
    tag: Optional[str] = None,
    compat: Optional[str] = None,
    output_format: str = "table",
    support: Optional[str] = None,
    category: Optional[str] = None,
) -> None:
    records = load_all_records()
    matched = []

    types_to_search = list(dict.fromkeys(CAPABILITY_TYPES.values())) if rec_type == "all" else [CAPABILITY_TYPES.get(rec_type, rec_type)]

    tokens = query_tokens(query) if query else []
    tag_lower = tag.lower() if tag else None
    status_lower = status.lower() if status else None
    compat_lower = compat.lower() if compat else None

    for t in types_to_search:
        if t not in records:
            continue
        for rec_id, rec in records[t].items():
            # Filter by status
            if status_lower and rec.get("status", "").lower() != status_lower:
                continue

            # Filter by tag
            rec_tags = [str(x).lower() for x in rec.get("tags", [])]
            if t == "libraries":
                rec_tags.extend([str(x).lower() for x in rec.get("metadata", {}).get("tags", [])])
            if tag_lower and tag_lower not in rec_tags:
                continue

            # Filter by compatibility
            if compat_lower:
                compat_match = False
                if t == "libraries":
                    c = rec.get("compatibility", {})
                    if compat_lower in ["apple-silicon", "m2", "arm64"] and c.get("apple_silicon_tested"):
                        compat_match = True
                    elif compat_lower in ["hyperframes", "hf"] and c.get("hyperframes_compatible"):
                        compat_match = True
                    elif compat_lower in ["low-memory", "low-mem"] and c.get("low_memory_mode_compatible"):
                        compat_match = True
                elif t != "libraries":
                    # Inherit compatibility through library dependencies
                    compat_match = True
                if not compat_match:
                    continue

            intent = (rec.get("visual_intent") or rec.get("justification") or rec.get("description")
                      or rec.get("purpose") or rec.get("technique") or "")
            if t == "reference-sources":
                intent = rec.get("analysis", {}).get("concept", {}).get("observed", "") or rec.get("name", "")

            if support and rec.get("capability", {}).get("support") != support:
                continue
            if category and category not in rec.get("categories", []):
                continue

            # Filter by query: every query term must appear (hyphens and plurals normalised).
            if tokens and not matches(tokens, searchable_text(t, rec_id, rec)):
                continue

            note = intent
            if t == "references":
                note = f"[{technique_lifecycle(rec)}; {rec.get('capability', {}).get('support', 'support ?')}] {intent}"
            elif t == "reference-sources":
                note = f"[{rec.get('analysis', {}).get('state')}; {', '.join(rec.get('categories', [])[:3])}] {intent}"
            matched.append({
                "type": SINGULAR.get(t, t),
                "id": rec_id,
                "name": rec.get("name", ""),
                "status": rec.get("status", ""),
                "category": rec.get("category", "") or rec.get("kind", "") or rec.get("deliverable_type", "") or rec.get("mode", ""),
                "visual_intent": note[:90],
                "tags": ", ".join(rec.get("tags", rec.get("metadata", {}).get("tags", [])))
            })

    if output_format == "json":
        print(json.dumps(matched, indent=2))
        return

    if output_format == "markdown":
        headers = ["Type", "ID", "Name", "Status", "Intent / Notes"]
        rows = [[m["type"], f"`{m['id']}`", m["name"], m["status"], m["visual_intent"]] for m in matched]
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in rows:
            print("| " + " | ".join(r) + " |")
        return

    # Default table
    headers = ["Type", "ID", "Name", "Status", "Visual Intent / Notes"]
    rows = [[m["type"], m["id"], m["name"][:28], m["status"], m["visual_intent"]] for m in matched]
    print(format_table(rows, headers))
    print(f"\nTotal matches: {len(matched)}")


def get_record(record_id: str) -> None:
    records = load_all_records()
    found = None
    rec_type = None

    for t in ["libraries", "effects", "recipes"]:
        if record_id in records[t]:
            found = records[t][record_id]
            rec_type = SINGULAR[t]
            break

    if not found:
        for t in ["primitives", "compositions", "project-templates", "styles", "references", "reference-sources"]:
            if record_id in records[t]:
                rec = records[t][record_id]
                print("=" * 70)
                print(f"{SINGULAR[t].upper()}: {rec.get('name')} ({record_id})")
                print("=" * 70)
                print(f"Status:       {rec.get('status', '').upper()}")
                if t == "references":
                    print(f"Lifecycle:    {technique_lifecycle(rec)} | support: {rec.get('capability', {}).get('support', 'not assessed')}")
                if t == "reference-sources":
                    print(f"Analysis:     {rec.get('analysis', {}).get('state')} | rights: {rec.get('rights', {}).get('usage')} (licence {rec.get('rights', {}).get('licence')})")
                summary = rec.get("description") or rec.get("purpose") or rec.get("technique")
                if summary:
                    print(f"\nSummary:\n  {summary}")
                skip = {"id", "name", "status", "description", "purpose", "technique"}
                for key, value in rec.items():
                    if key in skip:
                        continue
                    rendered = json.dumps(value, indent=2, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                    print(f"\n{key}:\n  " + rendered.replace("\n", "\n  "))
                print("=" * 70)
                return
        print(f"Error: Record '{record_id}' not found in any capability layer.")
        sys.exit(1)

    print("=" * 70)
    print(f"{rec_type.upper()}: {found.get('name')} ({found.get('id')})")
    print("=" * 70)
    print(f"Status:       {found.get('status').upper()}")
    print(f"Category:     {found.get('category')}")
    
    if rec_type == "library":
        print(f"Version:      {found.get('version')}")
        lic = found.get("licensing", {})
        print(f"Licensing:    {lic.get('spdx_identifier')} [{lic.get('status').upper()}] (Commercial: {lic.get('commercial_use')})")
        print(f"Docs:         {', '.join(found.get('documentation_urls', []))}")
        env = found.get("runtime_environment", {})
        print(f"Runtime:      {env.get('type')} (CDN: {env.get('cdn_url', 'N/A')})")
        rc = found.get("rendering_constraints", {})
        print(f"Constraints:  Max RAM: {rc.get('max_memory_mb')}MB | Target FPS: {rc.get('target_fps')} | Headless: {rc.get('headless_chromium_compatible')}")
        print(f"\nJustification:\n  {found.get('justification')}")
        print(f"\nEffects Provided:\n  {', '.join(found.get('effects_provided', []))}")

    elif rec_type == "effect":
        print(f"Dependencies: {', '.join(found.get('library_dependencies', []))}")
        print(f"Engine:       {found.get('rendering_engine')}")
        print(f"Tags:         {', '.join(found.get('tags', []))}")
        print(f"\nVisual Intent:\n  {found.get('visual_intent')}")
        print(f"\nImplementation Summary:\n  {found.get('implementation_summary')}")
        print(f"\nRecipes:\n  {', '.join(found.get('recipes', []))}")

    elif rec_type == "recipe":
        parent_eff = found.get("effect_id", "")
        parent_cat = records["effects"].get(parent_eff, {}).get("category", "N/A")
        print(f"Parent Effect:{parent_eff} (category: {parent_cat})")
        print(f"Tags:         {', '.join(found.get('tags', []))}")
        print(f"\nVisual Intent:\n  {found.get('visual_intent')}")
        
        print("\nParameters:")
        for p in found.get("parameters", []):
            dft = f" [default: {p.get('default')}]" if "default" in p else ""
            print(f"  • {p['name']} ({p['type']}){dft}: {p['description']}")

        tr = found.get("timeline_requirements", {})
        print(f"\nTimeline Requirements:")
        print(f"  • GSAP Instance:   {tr.get('gsap_instance')}")
        print(f"  • Timing Anchors:  {tr.get('timing_anchors')}")
        print(f"  • Easing Standard: {tr.get('easing_standard')}")
        print(f"  • PRNG Required:   {tr.get('prng_required')}")

        snip = found.get("code_snippet", {})
        if snip.get("html"):
            print(f"\nHTML / SVG Snippet:\n{snip['html']}")
        if snip.get("css"):
            print(f"\nCSS Snippet:\n{snip['css']}")
        if snip.get("javascript"):
            print(f"\nJavaScript / Timeline Snippet:\n{snip['javascript']}")

        print(f"\nFallbacks:\n  {found.get('fallbacks')}")
        print(f"\nValidation Steps:")
        for idx, step in enumerate(found.get("validation_steps", []), 1):
            print(f"  {idx}. {step}")

    print("=" * 70)


def list_records() -> None:
    records = load_all_records()
    print("=" * 70)
    print("MOTION GRAPHICS CAPABILITY CATALOGUE REGISTRY")
    print("=" * 70)

    for rtype in ["libraries", "effects", "recipes", "primitives", "compositions", "project-templates", "styles", "references", "reference-sources"]:
        items = records[rtype]
        print(f"\n[{rtype.upper()}] ({len(items)} records)")
        rows = []
        for rec_id, rec in items.items():
            if rtype == "recipes":
                cat = f"effect: {rec.get('effect_id', '')}"
            elif rtype == "references":
                cat = f"{technique_lifecycle(rec)}; {rec.get('capability', {}).get('support', '-')}"
            elif rtype == "reference-sources":
                cat = f"{rec.get('analysis', {}).get('state')}; {', '.join(rec.get('categories', [])[:2])}"
            else:
                cat = rec.get("category", "") or rec.get("kind", "") or rec.get("deliverable_type", "") or rec.get("mode", "")
            if rtype == "styles" and rec.get("default"):
                cat += " (default)"
            rows.append([rec_id, rec.get("name", "")[:30], rec.get("status", "").upper(), cat])
        print(format_table(rows, ["ID", "Name", "Status", "Category / Effect"]))
    print("=" * 70)


def export_index(output_path: Optional[Path] = None) -> None:
    records = load_all_records()
    dest = output_path or (CATALOGUE_DIR / "index.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Catalogue compiled and exported to: {dest}")


def brief_text(path: Path) -> str:
    """The parts of a brief.json that describe intent (objective, message, tone, directions)."""
    b = load_json(path)
    parts = [b.get("title", ""), b.get("objective", ""), b.get("audience", ""), " ".join(b.get("platforms", [])),
             b.get("message", {}).get("core_message", ""), " ".join(b.get("message", {}).get("key_points", [])),
             " ".join(b.get("tone", {}).get("emotional_response", [])), " ".join(b.get("tone", {}).get("keywords", [])),
             " ".join(b.get("deliverables", {}).get("other", []))]
    chosen = b.get("selected_direction")
    for d in b.get("creative_directions", []):
        if chosen and d.get("id") != chosen:
            continue
        ml = d.get("motion_language", {})
        parts += [d.get("concept", ""), d.get("pacing", ""), ml.get("personality", "") if isinstance(ml.get("personality"), str) else "",
                  " ".join(ml.get("signature_moves", []) if isinstance(ml.get("signature_moves"), list) else []),
                  " ".join(ml.get("transitions", []) if isinstance(ml.get("transitions"), list) else [])]
    return " ".join(p for p in parts if p)


def recommend(text: str, limit: int = 8, include_unimplemented: bool = True) -> Dict[str, Any]:
    """Rank technique records against a brief by weighted term overlap; implementation and precedent break ties."""
    records = load_all_records()
    terms = list(dict.fromkeys(query_tokens(text)))
    techniques = records["references"]
    sources = records["reference-sources"]
    ranked = []
    for tid, t in techniques.items():
        strong = " ".join([tid, t.get("name", ""), " ".join(t.get("tags", [])), " ".join(t.get("use_cases", []))]).lower().replace("-", " ")
        medium = " ".join([t.get("purpose", ""), t.get("technique", "")]).lower().replace("-", " ")
        weak = searchable_text("references", tid, t)
        hits = [w for w in terms if has_term(w, weak)]
        if not hits:
            continue
        score = sum(3 if has_term(w, strong) else 2 if has_term(w, medium) else 1 for w in hits)
        life = technique_lifecycle(t)
        support = t.get("capability", {}).get("support", "")
        score += {"approved": 2.0}.get(life, 1.0 if life.startswith("tested") else 0.5 if life.startswith("implemented") else -0.5 if life in ("observed", "specified") else 0)
        score += {"native": 0.5, "approximation": 0.25, "research-required": -1.0}.get(support, 0)
        score += 0.2 * len(t.get("provenance", []))
        if not include_unimplemented and life in ("observed", "specified"):
            continue
        ranked.append({
            "id": tid, "name": t.get("name", ""), "score": round(score, 2), "lifecycle": life, "support": support or "not assessed",
            "implemented_by": t.get("implemented_by", []), "runtime_api": t.get("implementation", {}).get("runtime_api", []),
            "precedents": [{"source": p["source_id"], "at": p["timestamps"][0]} for p in t.get("provenance", [])][:4],
            "matched": hits,
        })
    ranked.sort(key=lambda r: (-r["score"], r["id"]))
    top = ranked[:limit]
    picked = {r["id"] for r in top}
    src_rank = []
    for sid, s in sources.items():
        overlap = picked & {x["id"] for x in s.get("techniques", [])}
        text_hits = [w for w in terms if has_term(w, searchable_text("reference-sources", sid, s))]
        if overlap or len(text_hits) >= 2:
            src_rank.append({"id": sid, "name": s.get("name", ""), "score": 2 * len(overlap) + len(text_hits),
                             "shares": sorted(overlap), "usage": s.get("rights", {}).get("usage")})
    src_rank.sort(key=lambda r: (-r["score"], r["id"]))
    styles = []
    for sid, s in records["styles"].items():
        hits = [w for w in terms if has_term(w, searchable_text("styles", sid, s))]
        if hits:
            styles.append({"id": sid, "matched": hits, "status": s.get("status")})
    styles.sort(key=lambda r: -len(r["matched"]))
    return {"terms": terms, "techniques": top, "references": src_rank[:6], "styles": styles[:3],
            "note": "Precedents are study material (inspiration-only): combine principles into an original direction; never copy a reference's assets, brand or shot sequence."}


def print_recommendation(rec: Dict[str, Any]) -> None:
    print("=" * 78)
    print("CAPABILITY RECOMMENDATION")
    print("=" * 78)
    print(f"Brief terms: {', '.join(rec['terms']) or '(none)'}")
    print("\nTechniques (best first):")
    if not rec["techniques"]:
        print("  none matched; search the catalogue directly or broaden the brief terms.")
    for r in rec["techniques"]:
        impl = ", ".join(r["implemented_by"]) or "no implementation yet"
        prec = ", ".join(f"{p['source']}@{p['at']}s" for p in r["precedents"]) or "genre convention"
        print(f"  {r['score']:5.1f}  {r['id']}  [{r['lifecycle']}; {r['support']}]")
        print(f"         use: {impl}")
        print(f"         precedent: {prec}   matched: {', '.join(r['matched'])}")
    if rec["references"]:
        print("\nReference precedents to study (not to copy):")
        for s in rec["references"]:
            print(f"  {s['id']}  {s['name'][:52]}  shares: {', '.join(s['shares']) or '-'}")
    if rec["styles"]:
        print("\nStyle systems that match the tone: " + ", ".join(f"{s['id']} ({s['status']})" for s in rec["styles"]))
    print(f"\n{rec['note']}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(
        description="Motion Graphics Capability Catalogue CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/motion-catalogue.py search --query "crossfade"
  python3 scripts/motion-catalogue.py search --type effect --tag data-flow
  python3 scripts/motion-catalogue.py search --status approved --compat low-memory
  python3 scripts/motion-catalogue.py get zero-dip-scene-transition
  python3 scripts/motion-catalogue.py search -q "kinetic typography" -t source
  python3 scripts/motion-catalogue.py search -t technique --support approximation
  python3 scripts/motion-catalogue.py recommend --brief projects/<slug>/brief.json
  python3 scripts/motion-catalogue.py list
  python3 scripts/motion-catalogue.py validate
  python3 scripts/motion-catalogue.py export
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # search
    search_parser = subparsers.add_parser("search", help="Search the catalogue")
    search_parser.add_argument("-q", "--query", type=str, help="Search query (matches name, description, intent, tags)")
    search_parser.add_argument("-t", "--type", type=str, default="all", choices=["all"] + list(CAPABILITY_TYPES.keys()), help="Record type filter")
    search_parser.add_argument("-s", "--status", type=str, choices=["proposed", "experimental", "approved", "deprecated", "blocked"], help="Approval status filter")
    search_parser.add_argument("--tag", type=str, help="Filter by exact tag")
    search_parser.add_argument("--compat", type=str, choices=["apple-silicon", "hyperframes", "low-memory"], help="Hardware/platform compatibility filter")
    search_parser.add_argument("--support", type=str, choices=["native", "approximation", "additional-dependencies", "resource-constrained", "research-required"],
                               help="Technique capability class filter")
    search_parser.add_argument("--category", type=str, help="Reference source category (e.g. kinetic-typography)")
    search_parser.add_argument("-f", "--format", type=str, default="table", choices=["table", "json", "markdown"], help="Output format")

    # recommend
    rec_parser = subparsers.add_parser("recommend", help="Rank techniques, components and precedents for a brief")
    rec_parser.add_argument("--brief", type=Path, help="projects/<slug>/brief.json")
    rec_parser.add_argument("--text", type=str, help="Free-text brief")
    rec_parser.add_argument("--limit", type=int, default=8)
    rec_parser.add_argument("--implemented-only", action="store_true", help="Hide observed/specified techniques")
    rec_parser.add_argument("-f", "--format", type=str, default="table", choices=["table", "json"])

    # get
    get_parser = subparsers.add_parser("get", help="Get complete record details")
    get_parser.add_argument("id", type=str, help="Record ID")

    # list
    subparsers.add_parser("list", help="List all records in catalogue")

    # validate
    subparsers.add_parser("validate", help="Validate catalogue schemas, references, and statuses")

    # export
    export_parser = subparsers.add_parser("export", help="Export aggregated index.json")
    export_parser.add_argument("-o", "--output", type=Path, help="Output destination path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "search":
        search_catalogue(
            query=args.query,
            rec_type=args.type,
            status=args.status,
            tag=args.tag,
            compat=args.compat,
            output_format=args.format,
            support=args.support,
            category=args.category,
        )
    elif args.command == "recommend":
        if not args.brief and not args.text:
            print("Give --brief <brief.json> and/or --text \"...\".")
            sys.exit(2)
        text = " ".join(filter(None, [brief_text(args.brief) if args.brief else "", args.text or ""]))
        result = recommend(text, limit=args.limit, include_unimplemented=not args.implemented_only)
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print_recommendation(result)
    elif args.command == "get":
        get_record(args.id)
    elif args.command == "list":
        list_records()
    elif args.command == "validate":
        valid = validate_catalogue(verbose=True)
        sys.exit(0 if valid else 1)
    elif args.command == "export":
        export_index(args.output)


if __name__ == "__main__":
    main()