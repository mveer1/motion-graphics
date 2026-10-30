#!/usr/bin/env python3
"""
scripts/workspace-governance.py
Lightweight CLI for workspace component governance, registration verification,
and drift detection.

Audits (7 gates):
1. Schema conformity, ID uniqueness and cross-references across all catalogue layers
   (delegated to motion-catalogue.py validate).
2. Broken workspace paths: registered component files, style sheets, project templates,
   primitive and composition implementations must exist on disk.
3. Unregistered active workspace components (skills, scripts, shared specs, studio style
   systems, project templates on disk without catalogue records).
4. Dependency constraints (no active component depends on a blocked one).
5. Architecture references: every architecture_ref must resolve to an existing document and
   anchor (explicit <a id> or a heading slug).
6. Secret/credential leak audit in catalogue records.
7. Studio project integrity: vendored runtime matches its lock, generated format entry files
   (src/index.<format>.html) are up to date with index.html + project.json.

Usage:
    python3 scripts/workspace-governance.py
    python3 scripts/workspace-governance.py --json
    python3 scripts/workspace-governance.py --strict
"""

import sys
import os
import re
import shutil
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

# Auto-delegate to Python 3.12 if current python lacks jsonschema
if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import jsonschema
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_DIR = REPO_ROOT / "catalogue"
SCHEMAS_DIR = CATALOGUE_DIR / "schemas"
DATA_DIR = CATALOGUE_DIR / "data"
AGENTS_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TEMPLATES_DIR = REPO_ROOT / "templates"
SPECS_DIR = REPO_ROOT / "specs"
ARCHITECTURE_MD = REPO_ROOT / "ARCHITECTURE.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
STUDIO_STYLES_DIR = REPO_ROOT / "src" / "studio" / "styles"
PROJECT_TEMPLATES_DIR = TEMPLATES_DIR / "projects"
PROJECTS_DIR = REPO_ROOT / "projects"

# Locations that are not workspace files.
VIRTUAL_PREFIXES = ("http://", "https://", "role:", "system_prompt:", "unresolved:", "pending:")
# Host-level binaries (checked on the production Mac only).
HOST_PREFIXES = ("/usr/", "/opt/")
# Machine-local, untracked environments: missing on a fresh checkout is a warning, not drift.
MACHINE_LOCAL_PREFIXES = (".venv/",)
# Shared specifications and assets that must carry a catalogue record.
SHARED_ASSETS = [
    "templates/research-template.json",
    "specs/research-spec.json",
    "specs/video-spec.json",
    "specs/brief-spec.json",
    "specs/storyboard-spec.json",
    "specs/format-presets.json",
    "src/studio",
]

sys.path.insert(0, str(SCRIPTS_DIR))
import importlib
motion_catalogue = importlib.import_module("motion-catalogue")
studio = importlib.import_module("studio")


def heading_slug(text: str) -> str:
    """GitHub-style heading anchor: lower-case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def document_anchors(path: Path) -> Set[str]:
    anchors: Set[str] = set()
    if not path.exists():
        return anchors
    for line in path.read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(r"<a\s+(?:id|name)=\"([^\"]+)\"", line))
        m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            anchors.add(heading_slug(m.group(1)))
    return anchors


class GovernanceAuditor:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.records = motion_catalogue.load_all_records()

    def audit_catalogue_schemas_and_integrity(self) -> None:
        """Gate 1: Schema validation, ID uniqueness, and valid statuses."""
        valid = motion_catalogue.validate_catalogue(verbose=False)
        if not valid:
            self.errors.append("Catalogue schema validation or internal cross-reference check failed.")
        else:
            self.checks_passed += 1

    def audit_workspace_file_existence(self) -> None:
        """Gate 2: Ensure registered workspace-owned files actually exist on disk."""
        missing_paths = []
        for coll in ["skills", "tools", "agents", "integrations", "shared"]:
            for comp_id, comp_data in self.records[coll].items():
                loc = comp_data.get("location", "")
                # Skip virtual locations or external URLs
                if loc.startswith(VIRTUAL_PREFIXES):
                    continue
                # Machine-level host tools
                if loc.startswith(HOST_PREFIXES):
                    # Checked leniently without failing CI if on a different machine
                    continue
                if loc.startswith(MACHINE_LOCAL_PREFIXES):
                    if not (REPO_ROOT / loc).exists():
                        self.warnings.append(
                            f"{comp_id}: machine-local location '{loc}' is not present on this host (untracked environment)."
                        )
                    continue

                target_path = REPO_ROOT / loc
                if not target_path.exists():
                    missing_paths.append(f"{comp_id} -> missing '{loc}'")

        # Capability layers that point at workspace files.
        layer_locations = []
        for coll in ["styles", "project-templates"]:
            for rec_id, rec in self.records.get(coll, {}).items():
                layer_locations.append((coll, rec_id, rec.get("status"), rec.get("location", "")))
        for coll in ["primitives", "compositions"]:
            for rec_id, rec in self.records.get(coll, {}).items():
                layer_locations.append((coll, rec_id, rec.get("status"), rec.get("implementation", {}).get("location", "")))
        for coll, rec_id, status, loc in layer_locations:
            if not loc or loc == "native":
                continue
            if loc.startswith("pending:"):
                if status in ("experimental", "approved"):
                    missing_paths.append(f"{rec_id} ({coll}) is {status} but has only a pending location '{loc}'")
                continue
            if not (REPO_ROOT / loc).exists():
                missing_paths.append(f"{rec_id} ({coll}) -> missing '{loc}'")

        if missing_paths:
            for m in missing_paths:
                self.errors.append(f"Registered component file missing on disk: {m}")
        else:
            self.checks_passed += 1

    def audit_unregistered_workspace_components(self) -> None:
        """Gate 3: Detect active workspace skills, tools, and templates that lack catalogue records."""
        errors_before = len(self.errors)
        # 1. Check all skills in .agents/skills/
        registered_skill_locs = {
            comp_data.get("location", "").rstrip("/")
            for comp_data in self.records["skills"].values()
        }
        
        if AGENTS_SKILLS_DIR.exists():
            for skill_path in AGENTS_SKILLS_DIR.iterdir():
                if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                    rel_loc = skill_path.relative_to(REPO_ROOT).as_posix()
                    if rel_loc not in registered_skill_locs:
                        self.errors.append(
                            f"Active skill folder '{rel_loc}' on disk is not registered in catalogue/data/skills/."
                        )

        # 2. Check key scripts in scripts/
        registered_tool_locs = {
            comp_data.get("location", "").lstrip("./")
            for comp_data in self.records["tools"].values()
        }
        for script_file in sorted(SCRIPTS_DIR.glob("*.*")):
            if script_file.suffix in [".py", ".sh"] and not script_file.name.startswith("."):
                rel_loc = f"scripts/{script_file.name}"
                if rel_loc not in registered_tool_locs:
                    self.warnings.append(
                        f"Script '{rel_loc}' on disk is not registered in catalogue/data/tools/."
                    )

        # 3. Check shared specifications, templates and the studio runtime
        registered_shared_locs = {
            comp_data.get("location", "").rstrip("/")
            for comp_data in self.records["shared"].values()
        }
        for tmpl in SHARED_ASSETS:
            if (REPO_ROOT / tmpl).exists() and tmpl not in registered_shared_locs:
                self.warnings.append(f"Shared specification/template '{tmpl}' is not registered in catalogue/data/shared/.")

        # 4. Studio style systems and project templates are selectable components: they must be registered.
        style_locs = {rec.get("location", "") for rec in self.records.get("styles", {}).values()}
        if STUDIO_STYLES_DIR.exists():
            for css in sorted(STUDIO_STYLES_DIR.glob("*.css")):
                rel = css.relative_to(REPO_ROOT).as_posix()
                if rel not in style_locs:
                    self.errors.append(f"Style system '{rel}' on disk is not registered in catalogue/data/styles/.")
        template_locs = {rec.get("location", "").rstrip("/") for rec in self.records.get("project-templates", {}).values()}
        if PROJECT_TEMPLATES_DIR.exists():
            for tdir in sorted(p for p in PROJECT_TEMPLATES_DIR.iterdir() if p.is_dir()):
                rel = tdir.relative_to(REPO_ROOT).as_posix()
                if rel not in template_locs:
                    self.errors.append(f"Project template '{rel}' on disk is not registered in catalogue/data/project-templates/.")

        if len(self.errors) == errors_before:
            self.checks_passed += 1

    def audit_dependency_constraints(self) -> None:
        """Gate 4: Ensure no active component depends on a blocked or deprecated dependency."""
        blocked_ids = set()
        for coll, items in self.records.items():
            for rec_id, data in items.items():
                if data.get("status") == "blocked":
                    blocked_ids.add(rec_id)

        for coll in ["effects", "recipes", "skills", "tools", "agents", "integrations", "shared"]:
            for comp_id, comp_data in self.records[coll].items():
                deps = comp_data.get("dependencies", comp_data.get("library_dependencies", []))
                for dep in deps:
                    if dep in blocked_ids:
                        self.errors.append(
                            f"Component '{comp_id}' violates constraint: depends on BLOCKED component '{dep}'."
                        )
        self.checks_passed += 1

    def audit_architecture_references(self) -> None:
        """Gate 5: Verify architecture documentation references resolve to a document and anchor."""
        if not ARCHITECTURE_MD.exists():
            self.errors.append(f"ARCHITECTURE.md not found at {ARCHITECTURE_MD}")
            return

        errors_before = len(self.errors)
        anchor_cache: Dict[str, Set[str]] = {}
        for coll in ["skills", "tools", "agents", "integrations", "shared"]:
            for comp_id, comp_data in self.records[coll].items():
                arch_ref = comp_data.get("architecture_ref", "")
                if not arch_ref:
                    if coll in ("skills", "tools", "integrations"):
                        self.warnings.append(f"Component '{comp_id}' has no architecture_ref.")
                    continue
                doc, _, anchor = arch_ref.partition("#")
                doc_path = REPO_ROOT / doc
                if not doc_path.exists():
                    self.errors.append(f"Component '{comp_id}' architecture_ref '{arch_ref}' points at a missing document.")
                    continue
                if anchor:
                    anchors = anchor_cache.setdefault(doc, document_anchors(doc_path))
                    if anchor not in anchors:
                        self.errors.append(f"Component '{comp_id}' architecture_ref '{arch_ref}': anchor '#{anchor}' not found in {doc}.")

        if len(self.errors) == errors_before:
            self.checks_passed += 1

    def audit_secret_and_security_exposure(self) -> None:
        """Gate 6: Scan catalogue records for hardcoded secrets, tokens, or credential leaks."""
        sensitive_patterns = ["bearer ", "eyj", "ghp_", "sk-", "password", "private_key"]
        
        for coll, items in self.records.items():
            for rec_id, data in items.items():
                rec_str = json.dumps(data).lower()
                for pat in sensitive_patterns:
                    if f'"{pat}' in rec_str or f": {pat}" in rec_str:
                        self.errors.append(f"Potential secret exposure in record '{rec_id}' (matches pattern '{pat}').")

                sec = data.get("security", {})
                if sec.get("sensitive_data_exposure") is True:
                    self.errors.append(f"Record '{rec_id}' explicitly flags sensitive_data_exposure = true.")

        self.checks_passed += 1

    def audit_studio_project_integrity(self) -> None:
        """Gate 7: Studio projects keep an unedited vendored runtime and up-to-date format entry files."""
        errors_before = len(self.errors)
        if PROJECTS_DIR.exists():
            for pdir in sorted(p for p in PROJECTS_DIR.iterdir() if (p / "project.json").exists()):
                integ = studio.runtime_integrity(pdir)
                self.errors.extend(integ.errors)
                self.warnings.extend(integ.warnings)
                try:
                    project = studio.load_json(pdir / "project.json")
                    expected = studio.expected_variants(pdir, project)
                except (OSError, ValueError, KeyError) as exc:
                    self.errors.append(f"{pdir.name}: cannot derive format entry files ({exc}).")
                    continue
                for name, content in expected.items():
                    path = pdir / "src" / name
                    current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
                    if current != content.replace("\r\n", "\n"):
                        self.errors.append(
                            f"{pdir.name}: src/{name} is missing or out of date; run `python scripts/studio.py formats {pdir.name}`."
                        )
        if len(self.errors) == errors_before:
            self.checks_passed += 1

    def run_all_audits(self) -> Tuple[bool, Dict[str, Any]]:
        self.audit_catalogue_schemas_and_integrity()
        self.audit_workspace_file_existence()
        self.audit_unregistered_workspace_components()
        self.audit_dependency_constraints()
        self.audit_architecture_references()
        self.audit_secret_and_security_exposure()
        self.audit_studio_project_integrity()

        if self.strict and self.warnings:
            for w in self.warnings:
                self.errors.append(f"[STRICT MODE] {w}")

        success = len(self.errors) == 0
        summary = {
            "success": success,
            "checks_passed": self.checks_passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "counts": {coll: len(self.records[coll]) for coll in motion_catalogue.COLLECTIONS}
        }
        return success, summary


def main():
    parser = argparse.ArgumentParser(description="Workspace Governance & Drift Detection CLI")
    parser.add_argument("--json", action="store_true", help="Output audit report as JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    auditor = GovernanceAuditor(strict=args.strict)
    success, summary = auditor.run_all_audits()

    if args.json:
        print(json.dumps(summary, indent=2))
        sys.exit(0 if success else 1)

    print("=" * 70)
    print("WORKSPACE GOVERNANCE & COMPONENT STEWARDSHIP AUDIT")
    print("=" * 70)
    print(f"Verified Entity Counts:")
    for coll, count in summary["counts"].items():
        print(f"  • {coll.capitalize().ljust(15)}: {count}")
    print("-" * 70)

    if summary["warnings"]:
        print("GOVERNANCE WARNINGS:")
        for w in summary["warnings"]:
            print(f"  [WARN] {w}")
        print("-" * 70)

    if not success:
        print("GOVERNANCE VIOLATIONS DETECTED:")
        for e in summary["errors"]:
            print(f"  [FAIL] {e}")
        print("=" * 70)
        sys.exit(1)
    else:
        print(f"[PASS] All {summary['checks_passed']} governance gates passed. No drift or violations detected.")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
