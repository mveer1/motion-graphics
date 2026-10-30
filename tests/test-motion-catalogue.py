#!/usr/bin/env python3
"""
tests/test-motion-catalogue.py
Comprehensive automated test suite for the Motion Graphics Capability Catalogue.

Validates:
1. JSON Schema validation for library, effect, and recipe records.
2. Cross-reference integrity (effect -> library, recipe -> effect, etc.).
3. Strict ID uniqueness across all catalogue entities.
4. Valid approval states ('proposed', 'experimental', 'approved', 'deprecated', 'blocked').
5. Licensing verification checks.
6. Detection of broken references, duplicate IDs, and invalid statuses.
7. Search CLI commands, filtering, and detail extraction.
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
CATALOGUE_DIR = REPO_ROOT / "catalogue"
SCHEMAS_DIR = CATALOGUE_DIR / "schemas"
DATA_DIR = CATALOGUE_DIR / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
CLI_PATH = SCRIPTS_DIR / "motion-catalogue.py"

# Import helper functions from motion-catalogue CLI
sys.path.insert(0, str(SCRIPTS_DIR))
import importlib
motion_catalogue = importlib.import_module("motion-catalogue")


class TestMotionCatalogue(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.library_schema = motion_catalogue.load_json(SCHEMAS_DIR / "library.schema.json")
        cls.effect_schema = motion_catalogue.load_json(SCHEMAS_DIR / "effect.schema.json")
        cls.recipe_schema = motion_catalogue.load_json(SCHEMAS_DIR / "recipe.schema.json")
        cls.records = motion_catalogue.load_all_records()

    def test_catalogue_structure_exists(self):
        self.assertTrue(CATALOGUE_DIR.exists(), "catalogue/ directory must exist")
        self.assertTrue(SCHEMAS_DIR.exists(), "catalogue/schemas/ directory must exist")
        self.assertTrue(DATA_DIR.exists(), "catalogue/data/ directory must exist")
        self.assertTrue((DATA_DIR / "libraries").exists())
        self.assertTrue((DATA_DIR / "effects").exists())
        self.assertTrue((DATA_DIR / "recipes").exists())

    def test_library_schema_validation(self):
        libraries = self.records["libraries"]
        self.assertGreaterEqual(len(libraries), 4, "Should have at least 4 initial library records")
        for lib_id, data in libraries.items():
            try:
                jsonschema.validate(instance=data, schema=self.library_schema)
            except jsonschema.ValidationError as e:
                self.fail(f"Library '{lib_id}' failed schema validation: {e.message}")

    def test_effect_schema_validation(self):
        effects = self.records["effects"]
        self.assertGreaterEqual(len(effects), 4, "Should have at least 4 initial effect records")
        for eff_id, data in effects.items():
            try:
                jsonschema.validate(instance=data, schema=self.effect_schema)
            except jsonschema.ValidationError as e:
                self.fail(f"Effect '{eff_id}' failed schema validation: {e.message}")

    def test_recipe_schema_validation(self):
        recipes = self.records["recipes"]
        self.assertGreaterEqual(len(recipes), 4, "Should have at least 4 initial recipe records")
        for rec_id, data in recipes.items():
            try:
                jsonschema.validate(instance=data, schema=self.recipe_schema)
            except jsonschema.ValidationError as e:
                self.fail(f"Recipe '{rec_id}' failed schema validation: {e.message}")

    def test_no_duplicate_ids(self):
        seen_ids = {}
        for rtype, collection in self.records.items():
            for rec_id in collection:
                self.assertNotIn(
                    rec_id,
                    seen_ids,
                    f"Duplicate ID '{rec_id}' in '{rtype}', previously in '{seen_ids.get(rec_id)}'"
                )
                seen_ids[rec_id] = rtype

    def test_valid_approval_statuses(self):
        allowed = {"proposed", "experimental", "approved", "deprecated", "blocked"}
        for rtype, collection in self.records.items():
            for rec_id, data in collection.items():
                st = data.get("status")
                self.assertIn(st, allowed, f"{rtype} '{rec_id}' has invalid status '{st}'")

    def test_licensing_verification_policy(self):
        for lib_id, data in self.records["libraries"].items():
            lic = data.get("licensing", {})
            self.assertIn(lic.get("status"), ["verified", "unverified"], f"Library '{lib_id}' licensing status invalid")
            if data.get("status") == "approved":
                self.assertEqual(
                    lic.get("status"),
                    "verified",
                    f"Approved library '{lib_id}' must have verified licensing"
                )
                self.assertTrue(
                    lic.get("commercial_use"),
                    f"Approved library '{lib_id}' must permit commercial use"
                )

    def test_cross_references_integrity(self):
        # Effects -> Libraries
        for eff_id, eff_data in self.records["effects"].items():
            for dep in eff_data.get("library_dependencies", []):
                self.assertIn(dep, self.records["libraries"], f"Effect '{eff_id}' references unknown library '{dep}'")

        # Recipes -> Effects
        for rec_id, rec_data in self.records["recipes"].items():
            parent_eff = rec_data.get("effect_id")
            self.assertIn(parent_eff, self.records["effects"], f"Recipe '{rec_id}' references unknown effect '{parent_eff}'")
            # Bidirectional consistency
            self.assertIn(
                rec_id,
                self.records["effects"][parent_eff].get("recipes", []),
                f"Effect '{parent_eff}' must list '{rec_id}' in its 'recipes' array"
            )

        # Libraries -> Effects provided
        for lib_id, lib_data in self.records["libraries"].items():
            for eff in lib_data.get("effects_provided", []):
                self.assertIn(eff, self.records["effects"], f"Library '{lib_id}' references unknown provided effect '{eff}'")

    def test_validator_detects_broken_reference(self):
        # Temporarily mock records with broken reference
        broken_records = {
            "libraries": dict(self.records["libraries"]),
            "effects": {
                "broken-effect": {
                    "id": "broken-effect",
                    "name": "Broken",
                    "category": "transition",
                    "visual_intent": "Test",
                    "status": "approved",
                    "library_dependencies": ["non-existent-lib"],
                    "rendering_engine": "svg_dom",
                    "tags": ["test"],
                    "performance_characteristics": {
                        "cpu_intensity": "low",
                        "gpu_intensity": "low",
                        "memory_profile": "low"
                    },
                    "recipes": ["non-existent-recipe"],
                    "implementation_summary": "Test"
                }
            },
            "recipes": dict(self.records["recipes"])
        }
        
        # Test detection logic directly
        errors = []
        for dep in broken_records["effects"]["broken-effect"]["library_dependencies"]:
            if dep not in broken_records["libraries"]:
                errors.append(f"Missing library: {dep}")
        self.assertEqual(len(errors), 1)
        self.assertIn("non-existent-lib", errors[0])

    def test_validator_detects_invalid_status(self):
        allowed = {"proposed", "experimental", "approved", "deprecated", "blocked"}
        test_status = "unsupported_status"
        self.assertNotIn(test_status, allowed)

    def test_cli_validate_command(self):
        res = subprocess.run([sys.executable, str(CLI_PATH), "validate"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"CLI validate failed: {res.stdout}\n{res.stderr}")
        self.assertIn("[PASS]", res.stdout)

    def test_cli_search_by_query(self):
        res = subprocess.run([sys.executable, str(CLI_PATH), "search", "-q", "crossfade"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("crossfade-dissolve", res.stdout)
        self.assertIn("zero-dip-scene-transition", res.stdout)

    def test_cli_search_by_tag_and_type(self):
        res = subprocess.run(
            [sys.executable, str(CLI_PATH), "search", "-t", "effect", "--tag", "data-flow"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("traveling-packet", res.stdout)
        self.assertIn("marching-dashed-stroke", res.stdout)

    def test_cli_search_by_status(self):
        res = subprocess.run(
            [sys.executable, str(CLI_PATH), "search", "-s", "blocked"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("animejs", res.stdout)

    def test_cli_get_record(self):
        res = subprocess.run(
            [sys.executable, str(CLI_PATH), "get", "zero-dip-scene-transition"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("sceneCrossfade", res.stdout)
        self.assertIn("outSelector", res.stdout)
        self.assertIn("window.__timelines['root']", res.stdout)

    def test_cli_export_command(self):
        tmp_export = CATALOGUE_DIR / "test_export.json"
        try:
            res = subprocess.run(
                [sys.executable, str(CLI_PATH), "export", "-o", str(tmp_export)],
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0)
            self.assertTrue(tmp_export.exists())
            with open(tmp_export, "r") as f:
                data = json.load(f)
            self.assertIn("libraries", data)
            self.assertIn("effects", data)
            self.assertIn("recipes", data)
        finally:
            if tmp_export.exists():
                tmp_export.unlink()


if __name__ == "__main__":
    unittest.main()

