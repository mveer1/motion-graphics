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
    "shared"
]


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


def validate_catalogue(verbose: bool = True) -> bool:
    records = load_all_records()
    errors = []
    warnings = []
    
    library_schema = load_json(SCHEMAS_DIR / "library.schema.json") if (SCHEMAS_DIR / "library.schema.json").exists() else None
    effect_schema = load_json(SCHEMAS_DIR / "effect.schema.json") if (SCHEMAS_DIR / "effect.schema.json").exists() else None
    recipe_schema = load_json(SCHEMAS_DIR / "recipe.schema.json") if (SCHEMAS_DIR / "recipe.schema.json").exists() else None
    
    allowed_statuses = {"proposed", "experimental", "approved", "deprecated", "blocked"}

    # 1. Schema Validation
    if HAS_JSONSCHEMA:
        for lib_id, lib_data in records["libraries"].items():
            try:
                jsonschema.validate(instance=lib_data, schema=library_schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Library '{lib_id}' schema error: {e.message}")
                
        for eff_id, eff_data in records["effects"].items():
            try:
                jsonschema.validate(instance=eff_data, schema=effect_schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Effect '{eff_id}' schema error: {e.message}")
                
        for rec_id, rec_data in records["recipes"].items():
            try:
                jsonschema.validate(instance=rec_data, schema=recipe_schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Recipe '{rec_id}' schema error: {e.message}")
    else:
        warnings.append("jsonschema package not installed; skipped formal JSON Schema draft-07 check.")

    # 2. Check Valid Statuses
    for rtype, collection in records.items():
        for rec_id, rec_data in collection.items():
            st = rec_data.get("status")
            if st not in allowed_statuses:
                errors.append(f"{rtype[:-1].capitalize()} '{rec_id}' has invalid status '{st}'. Must be one of {allowed_statuses}")

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
    output_format: str = "table"
) -> None:
    records = load_all_records()
    matched = []

    types_to_search = ["libraries", "effects", "recipes"] if rec_type == "all" else [f"{rec_type}s" if not rec_type.endswith("s") else rec_type]

    query_lower = query.lower() if query else None
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
                elif t in ["effects", "recipes"]:
                    # Inherit compatibility through library dependencies
                    compat_match = True
                if not compat_match:
                    continue

            # Filter by query
            if query_lower:
                searchable_text = " ".join([
                    rec_id,
                    rec.get("name", ""),
                    rec.get("category", ""),
                    rec.get("visual_intent", ""),
                    rec.get("justification", ""),
                    rec.get("implementation_summary", ""),
                    " ".join(rec_tags)
                ]).lower()
                if query_lower not in searchable_text:
                    continue

            matched.append({
                "type": t[:-1],
                "id": rec_id,
                "name": rec.get("name", ""),
                "status": rec.get("status", ""),
                "category": rec.get("category", ""),
                "visual_intent": rec.get("visual_intent", rec.get("justification", ""))[:70],
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
            rec_type = t[:-1]
            break

    if not found:
        print(f"Error: Record '{record_id}' not found in libraries, effects, or recipes.")
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

    for rtype in ["libraries", "effects", "recipes"]:
        items = records[rtype]
        print(f"\n[{rtype.upper()}] ({len(items)} records)")
        rows = []
        for rec_id, rec in items.items():
            if rtype == "recipes":
                cat = f"effect: {rec.get('effect_id', '')}"
            else:
                cat = rec.get("category", "")
            rows.append([rec_id, rec.get("name", "")[:30], rec.get("status", "").upper(), cat])
        print(format_table(rows, ["ID", "Name", "Status", "Category / Effect"]))
    print("=" * 70)


def export_index(output_path: Optional[Path] = None) -> None:
    records = load_all_records()
    dest = output_path or (CATALOGUE_DIR / "index.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Catalogue compiled and exported to: {dest}")


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
  python3 scripts/motion-catalogue.py list
  python3 scripts/motion-catalogue.py validate
  python3 scripts/motion-catalogue.py export
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # search
    search_parser = subparsers.add_parser("search", help="Search the catalogue")
    search_parser.add_argument("-q", "--query", type=str, help="Search query (matches name, description, intent, tags)")
    search_parser.add_argument("-t", "--type", type=str, default="all", choices=["all", "library", "effect", "recipe"], help="Record type filter")
    search_parser.add_argument("-s", "--status", type=str, choices=["proposed", "experimental", "approved", "deprecated", "blocked"], help="Approval status filter")
    search_parser.add_argument("--tag", type=str, help="Filter by exact tag")
    search_parser.add_argument("--compat", type=str, choices=["apple-silicon", "hyperframes", "low-memory"], help="Hardware/platform compatibility filter")
    search_parser.add_argument("-f", "--format", type=str, default="table", choices=["table", "json", "markdown"], help="Output format")

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
            output_format=args.format
        )
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