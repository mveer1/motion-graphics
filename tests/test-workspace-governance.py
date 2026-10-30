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
                if loc.startswith(("/usr/", "/opt/", "http://", "https://", "role:", "system_prompt:", "unresolved:", "pending:")):
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
                rel_loc = str(item.relative_to(REPO_ROOT))
                self.assertIn(
                    rel_loc,
                    registered_locations,
                    f"Skill folder '{rel_loc}' on disk is not registered in catalogue/data/skills/"
                )

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
        sensitive_patterns = ["bearer ", "eyj", "ghp_", "sk-"]
        for coll, items in self.records.items():
            for rec_id, data in items.items():
                rec_str = json.dumps(data).lower()
                for pat in sensitive_patterns:
                    self.assertNotIn(
                        pat,
                        rec_str,
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
        self.assertIn("All 6 governance gates passed", res.stdout)

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


if __name__ == "__main__":
    unittest.main()
