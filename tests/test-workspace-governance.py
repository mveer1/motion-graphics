#!/usr/bin/env python3
"""
tests/test-workspace-governance.py
Automated test suite verifying workspace governance, component registration,
and drift detection.

Covers:
1. Complete schema validation across all component types (component.schema.json).
2. Global ID uniqueness across all collections.
3. Version consistency for libraries, tools, skills, agents, integrations, shared assets.
4. Active workspace skills on disk are registered.
5. Active workspace scripts in scripts/ are registered.
6. Registered workspace files exist on disk (no broken paths).
7. Dependency constraints: No active component depends on a blocked component.
8. Architecture reference validity.
9. Secret exposure audit.
10. scripts/workspace-governance.py CLI execution.
"""

import sys
import os
import re
import shutil
import json
import subprocess
import unittest
from pathlib import Path

# Auto-delegate to Python 3.12 if current python lacks jsonschema
if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import jsonschema
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
CATALOGUE_DIR = REPO_ROOT / "catalogue"
SCHEMAS_DIR = CATALOGUE_DIR / "schemas"
DATA_DIR = CATALOGUE_DIR / "data"
GOVERNANCE_CLI = SCRIPTS_DIR / "workspace-governance.py"

sys.path.insert(0, str(SCRIPTS_DIR))
import importlib
workspace_governance = importlib.import_module("workspace-governance")
motion_catalogue = importlib.import_module("motion-catalogue")


class TestWorkspaceGovernance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.records = motion_catalogue.load_all_records()
        cls.component_schema = motion_catalogue.load_json(SCHEMAS_DIR / "component.schema.json")
        cls.library_schema = motion_catalogue.load_json(SCHEMAS_DIR / "library.schema.json")
        cls.effect_schema = motion_catalogue.load_json(SCHEMAS_DIR / "effect.schema.json")
        cls.recipe_schema = motion_catalogue.load_json(SCHEMAS_DIR / "recipe.schema.json")

    def test_component_schema_validation(self):
        for coll in ["skills", "tools", "agents", "integrations", "shared"]:
            self.assertGreaterEqual(len(self.records[coll]), 1, f"Collection {coll} should have records")
            for comp_id, data in self.records[coll].items():
                try:
                    jsonschema.validate(instance=data, schema=self.component_schema)
                except jsonschema.ValidationError as e:
                    self.fail(f"Component '{comp_id}' in '{coll}' failed schema validation: {e.message}")

    def test_global_id_uniqueness(self):
        all_ids = {}
        for coll, items in self.records.items():
            for rec_id in items:
                self.assertNotIn(
                    rec_id,
                    all_ids,
                    f"Duplicate ID '{rec_id}' in '{coll}', already in '{all_ids.get(rec_id)}'"
                )
                all_ids[rec_id] = coll

    def test_version_consistency(self):
        for coll in ["libraries", "skills", "tools", "agents", "integrations", "shared"]:
            for comp_id, data in self.records[coll].items():
                ver = data.get("version")
                self.assertTrue(ver, f"Component '{comp_id}' in '{coll}' must have a valid version string")

    def test_registered_workspace_files_exist_on_disk(self):
        for coll in ["skills", "tools", "shared"]:
            for comp_id, data in self.records[coll].items():
                loc = data.get("location", "")
                if loc.startswith(workspace_governance.VIRTUAL_PREFIXES + workspace_governance.HOST_PREFIXES):
                    continue
                if loc.startswith(workspace_governance.MACHINE_LOCAL_PREFIXES):
                    # Untracked per-machine environments (.venv) may be absent on a fresh checkout.
                    continue
                path = REPO_ROOT / loc
                self.assertTrue(path.exists(), f"Registered component '{comp_id}' location does not exist: {path}")

    def test_all_active_skills_are_registered(self):
        skills_dir = REPO_ROOT / ".agents" / "skills"
        registered_locations = {
            data.get("location", "").rstrip("/") for data in self.records["skills"].values()
        }
        for item in skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                rel_loc = item.relative_to(REPO_ROOT).as_posix()
                self.assertIn(
                    rel_loc,
                    registered_locations,
                    f"Skill folder '{rel_loc}' on disk is not registered in catalogue/data/skills/"
                )

    def test_style_systems_and_templates_are_registered(self):
        style_locs = {r["location"] for r in self.records["styles"].values()}
        for css in (REPO_ROOT / "src" / "studio" / "styles").glob("*.css"):
            self.assertIn(css.relative_to(REPO_ROOT).as_posix(), style_locs)
        tpl_locs = {r["location"].rstrip("/") for r in self.records["project-templates"].values()}
        for tdir in (REPO_ROOT / "templates" / "projects").iterdir():
            if tdir.is_dir():
                self.assertIn(tdir.relative_to(REPO_ROOT).as_posix(), tpl_locs)

    def test_architecture_refs_resolve(self):
        auditor = workspace_governance.GovernanceAuditor()
        auditor.audit_architecture_references()
        self.assertEqual(auditor.errors, [], "\n".join(auditor.errors))

    def test_anchor_check_catches_missing_anchor(self):
        auditor = workspace_governance.GovernanceAuditor()
        auditor.records["tools"]["tool-motion-catalogue"] = dict(
            auditor.records["tools"]["tool-motion-catalogue"], architecture_ref="ARCHITECTURE.md#no-such-anchor-xyz")
        auditor.audit_architecture_references()
        self.assertTrue(any("no-such-anchor-xyz" in e for e in auditor.errors))

    def test_heading_slug_matches_github_style(self):
        self.assertEqual(workspace_governance.heading_slug("7. Workspace Governance & Drift"), "7-workspace-governance--drift")
        self.assertEqual(workspace_governance.heading_slug("Stage 4B: Sound `design`"), "stage-4b-sound-design")

    def test_studio_project_integrity_gate(self):
        auditor = workspace_governance.GovernanceAuditor()
        auditor.audit_studio_project_integrity()
        self.assertEqual(auditor.errors, [], "\n".join(auditor.errors))

    def test_no_blocked_dependency_usage(self):
        blocked_ids = {
            rec_id
            for coll in self.records.values()
            for rec_id, data in coll.items()
            if data.get("status") == "blocked"
        }
        self.assertIn("animejs", blocked_ids)

        for coll in ["effects", "recipes", "skills", "tools", "agents", "integrations", "shared"]:
            for comp_id, data in self.records[coll].items():
                deps = data.get("dependencies", data.get("library_dependencies", []))
                for dep in deps:
                    self.assertNotIn(
                        dep,
                        blocked_ids,
                        f"Component '{comp_id}' depends on blocked component '{dep}'"
                    )

    def test_secret_exposure_audit(self):
        # Token-shaped patterns: a bare "sk-" substring would match ids such as "text-mask-rise".
        sensitive_patterns = [
            r"\bbearer\s+[a-z0-9._-]{16,}",
            r"\beyj[a-z0-9_-]{10,}\.",
            r"\bghp_[a-z0-9]{20,}",
            r"(?<![a-z0-9])sk-[a-z0-9]{16,}",
        ]
        self.assertTrue(re.search(sensitive_patterns[3], '"api_key": "sk-' + "a1" * 12 + '"'))
        self.assertFalse(re.search(sensitive_patterns[3], '"id": "text-mask-rise"'))
        for coll, items in self.records.items():
            for rec_id, data in items.items():
                rec_str = json.dumps(data).lower()
                for pat in sensitive_patterns:
                    self.assertIsNone(
                        re.search(pat, rec_str),
                        f"Secret pattern '{pat}' detected in record '{rec_id}'"
                    )
                sec = data.get("security", {})
                self.assertFalse(
                    sec.get("sensitive_data_exposure", False),
                    f"Component '{rec_id}' marked sensitive_data_exposure = True"
                )

    def test_governance_cli_execution(self):
        res = subprocess.run([sys.executable, str(GOVERNANCE_CLI)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Governance CLI failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("[PASS]", res.stdout)
        self.assertIn("All 7 governance gates passed", res.stdout)

    def test_drift_detector_catches_missing_file(self):
        # Test auditor directly with simulated missing file
        auditor = workspace_governance.GovernanceAuditor()
        auditor.records["tools"]["fake-tool"] = {
            "id": "fake-tool",
            "name": "Fake Tool",
            "component_type": "tool",
            "purpose": "Test",
            "location": "scripts/non_existent_file_xyz.py",
            "version": "1.0.0",
            "status": "approved",
            "owner": "test",
            "licensing": {"spdx_identifier": "MIT", "status": "verified", "commercial_use": True},
            "security": {
                "requires_filesystem_write": False,
                "requires_network": False,
                "requires_execution": False,
                "sensitive_data_exposure": False,
                "notes": "Test"
            },
            "last_verified": "2026-10-30"
        }
        auditor.audit_workspace_file_existence()
        self.assertTrue(
            any("non_existent_file_xyz.py" in err for err in auditor.errors),
            "Drift detector should flag non-existent workspace file"
        )

    def test_drift_detector_catches_pending_location_on_active_template(self):
        auditor = workspace_governance.GovernanceAuditor()
        tpl = dict(next(iter(auditor.records["project-templates"].values())))
        tpl.update(id="fake-template", status="experimental", location="pending:not-built")
        auditor.records["project-templates"]["fake-template"] = tpl
        auditor.audit_workspace_file_existence()
        self.assertTrue(any("fake-template" in err for err in auditor.errors))


if __name__ == "__main__":
    unittest.main()
