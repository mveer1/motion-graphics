#!/usr/bin/env python3
"""
tests/test-fitness.py
The Sinew fitness capability: kit determinism, manifest and data consistency, classification,
dossier and review rules. Pure Python (no browser); run with python3.12 so jsonschema is available.
"""

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fitness", ROOT / "scripts" / "fitness.py")
fitness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fitness)

KIT_FILES = [ROOT / "src" / "studio" / "studio-rig.js"] + sorted((ROOT / "src" / "studio" / "kits" / "fitness").glob("*.js"))
BANNED = [r"Math\.random\s*\(", r"Date\.now\s*\(", r"new\s+Date\s*\(", r"performance\.now\s*\(", r"requestAnimationFrame\s*\(",
          r"setInterval\s*\(", r"setTimeout\s*\(", r"repeat\s*:\s*-1", r"\.play\s*\("]


def has_jsonschema() -> bool:
    try:
        import jsonschema  # noqa: F401
        return True
    except ImportError:
        return False


class TestKitDeterminism(unittest.TestCase):
    def test_kit_files_exist(self):
        names = {p.name for p in KIT_FILES}
        for n in ("studio-rig.js", "brand.js", "exercises.js", "anatomy.js", "graphics.js", "library.js", "sculpt.js", "sculpt-data.js"):
            self.assertIn(n, names)
        self.assertNotIn("tibi.js", names, "the classic Tibi was retired on 2026-11-09; only the Cobalt Sculpt Tibi stays")

    def test_no_nondeterministic_calls(self):
        for p in KIT_FILES:
            text = p.read_text(encoding="utf-8")
            for pat in BANNED:
                self.assertIsNone(re.search(pat, text), f"{p.name} matches banned pattern {pat}")

    def test_tweens_are_fromto(self):
        # the kit only adds explicit fromTo tweens so random-order seeks are stable
        for p in KIT_FILES:
            text = p.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\btl\.(to|from)\(", text), f"{p.name} uses tl.to/tl.from")

    def test_runtime_version_bumped(self):
        core = (ROOT / "src" / "studio" / "studio-core.js").read_text(encoding="utf-8")
        major_minor = tuple(int(x) for x in re.search(r"Studio\.version = '(\d+)\.(\d+)\.\d+'", core).groups())
        self.assertGreaterEqual(major_minor, (1, 4), "the rig and fitness kit arrived in runtime 1.4.0")


class TestLibraryAndManifest(unittest.TestCase):
    def test_library_js_current(self):
        self.assertEqual(fitness.LIBRARY_JS.read_text(encoding="utf-8"), fitness.library_js(), "run fitness.py library")

    @unittest.skipUnless(has_jsonschema(), "needs jsonschema (python3.12)")
    def test_check_passes(self):
        self.assertEqual(fitness.check(), [])

    def test_every_exercise_has_kinematics_and_known_muscles(self):
        src = fitness.kit_source()
        md = json.loads((fitness.DATA / "muscles.json").read_text())
        muscles = {m["id"] for m in md["muscles"]} | {m["id"] for m in md.get("deep_not_drawn", [])}
        for e in json.loads((fitness.DATA / "exercises.json").read_text())["exercises"]:
            if e.get("engine") == "3d" and e.get("rig3d_status") == "pending":   # knowledge first; the 3D rig comes later
                self.assertNotIn("rig3d", e, f"{e['id']}: drop rig3d_status 'pending' once rig3d is set")
            elif e.get("engine") == "3d":                    # 3D-only lifts: they must name a rig in exercises3d.js instead
                self.assertIn(f"id: '{e['rig3d']}'", (fitness.KIT / "exercises3d.js").read_text(), e["id"])
            else:
                self.assertTrue(f"EX['{e['id']}']" in src or f"EX.{e['id']} " in src or e["id"] in ("walk", "jog", "sprint"), e["id"])
            for m in e["muscles"]["primary"] + e["muscles"]["secondary"] + e["muscles"].get("stabilizer", []):
                self.assertIn(m, muscles, f"{e['id']}: {m}")
            self.assertNotRegex(json.dumps(e), r"\d+\s*%", f"{e['id']} must carry no activation percentages")

    def test_manifest_licences_cleared(self):
        man = json.loads(fitness.MANIFEST.read_text())
        for a in man["assets"]:
            if a["status"] != "excluded":
                self.assertTrue(a["license"]["commercial_use"], a["id"])

    def test_routing_assets_exist(self):
        ids = {a["id"] for a in json.loads(fitness.MANIFEST.read_text())["assets"]}
        for r in fitness.spec()["routing"]:
            for a in r["assets"]:
                self.assertIn(a, ids)


class TestClassify(unittest.TestCase):
    def test_pillars(self):
        self.assertEqual(fitness.classify("Should runners do single-leg squats?")["pillar"], "strength-for-running")
        self.assertEqual(fitness.classify("Progressive overload explained")["pillar"], "gym-bodybuilding")
        self.assertEqual(fitness.classify("How your muscles actually grow")["pillar"], "performance")

    def test_unknown_topic_falls_back(self):
        c = fitness.classify("Why do we yawn")
        self.assertEqual(c["pillar"], "performance")
        self.assertTrue(c["visual_systems"])

    def test_form_override_and_routing(self):
        c = fitness.classify("Squat technique", "long")
        self.assertEqual(c["form"], "long")
        self.assertIn("exercise-library", c["assets"])
        self.assertIn("fitness", c["categories"])


class TestDossierAndReview(unittest.TestCase):
    def dossier(self):
        return {
            "topic": "t", "research_question": "q", "pillar": "performance",
            "sources": [{"id": "s1", "citation": "A. B. 2020", "year": 2020, "design": "rct", "url": "u", "verified_via": "Europe PMC 2026-11-08"}],
            "claims": [{"id": "c1", "claim": "x", "grade": "moderate", "sources": ["s1"], "where": ["s1"]}],
            "do_not_claim": ["y"], "medical_boundary": "general education", "reviewed": {"by": "me", "date": "d", "verdict": "complete"},
        }

    @unittest.skipUnless(has_jsonschema(), "needs jsonschema (python3.12)")
    def test_valid_dossier(self):
        self.assertEqual(fitness.dossier_errors(self.dossier()), [])

    @unittest.skipUnless(has_jsonschema(), "needs jsonschema (python3.12)")
    def test_dossier_rules(self):
        d = self.dossier()
        d["claims"][0]["sources"] = ["missing"]
        self.assertTrue(any("unknown source" in e for e in fitness.dossier_errors(d)))
        d = self.dossier()
        d["claims"][0]["grade"] = "strong"
        self.assertTrue(any("strong" in e for e in fitness.dossier_errors(d)), "strong needs a review or meta-analysis")
        d = self.dossier()
        d["sources"][0]["verified_via"] = "memory"
        self.assertTrue(any("verified_via" in e for e in fitness.dossier_errors(d)))

    def review(self, score=8):
        dims = [x["id"] for x in fitness.spec()["rubric"]["dimensions"]]
        return {"slug": "x", "render": "r", "reviewed_at": "d", "reviewer": "me",
                "scores": {k: {"score": score, "evidence": "e"} for k in dims}, "issues": [], "verdict": "pass"}

    @unittest.skipUnless(has_jsonschema(), "needs jsonschema (python3.12)")
    def test_review_pass_and_critical_rules(self):
        self.assertTrue(fitness.review_result(self.review())["passed"])
        r = self.review()
        r["scores"]["scientific_accuracy"]["score"] = 7
        self.assertFalse(fitness.review_result(r)["passed"], "critical dimension under 8 fails")
        r = self.review(10)
        r["issues"].append({"id": "i", "scene": "s1", "time": "1", "problem": "p", "severity": "critical", "dimension": "scientific_accuracy",
                            "fix": "f", "rerender": True, "status": "open"})
        self.assertFalse(fitness.review_result(r)["passed"], "an open critical issue fails whatever the scores")
        r2 = copy.deepcopy(r)
        r2["issues"][0]["status"] = "fixed"
        self.assertTrue(fitness.review_result(r2)["passed"])


class TestTemplateAndStyle(unittest.TestCase):
    def test_template_loads_kit(self):
        html = (ROOT / "templates" / "projects" / "fitness-explainer" / "src" / "index.html").read_text()
        order = ["studio-rig.js", "kits/fitness/brand.js", "kits/fitness/sculpt-data.js", "kits/fitness/sculpt.js", "kits/fitness/exercises.js",
                 "kits/fitness/anatomy.js", "kits/fitness/graphics.js", "kits/fitness/library.js"]
        for f in order:
            self.assertIn("_studio/" + f, html)
        idx = [html.index("_studio/" + f) for f in order]
        self.assertEqual(idx, sorted(idx), "kit scripts load in dependency order")
        self.assertNotIn("kits/fitness/tibi.js", html)
        # the generated data loads before the painter, and new films start on the Cobalt Sculpt Tibi: the template
        # builds its Tibis through the kit's stations (K.stations), which paint each one with K.sculpt
        self.assertLess(html.index("sculpt-data.js"), html.index("kits/fitness/sculpt.js"))
        self.assertIn("K.stations(", html)
        stations_js = (fitness.KIT / "stations.js").read_text(encoding="utf-8")
        self.assertIn("F.sculpt(", stations_js)
        # stations.js needs studio-film.js (after the compositions) and the whole 2D kit before it
        self.assertLess(html.index("_studio/studio-compositions.js"), html.index("_studio/studio-film.js"))
        self.assertLess(html.index("_studio/studio-film.js"), html.index("_studio/studio-rig.js"))
        self.assertLess(html.index("_studio/kits/fitness/library.js"), html.index("_studio/kits/fitness/stations.js"))
        # GSAP comes from the vendored copy, never a CDN
        self.assertIn('src="_studio/vendor/gsap.min.js"', html)
        self.assertNotRegex(html, r"<script[^>]+src=\"https?:")

    def test_style_template_and_caption_preset(self):
        tpl = json.loads((ROOT / "catalogue" / "data" / "style-templates" / "body-lab.json").read_text())
        self.assertEqual(tpl["look"]["style"], "sinew-lab")
        self.assertEqual(tpl["selection"]["categories"], ["fitness"])
        presets = json.loads((ROOT / "specs" / "caption-presets.json").read_text())
        self.assertIn("sinew-lab", presets["style_map"])
        cats = [c["id"] for c in json.loads((ROOT / "specs" / "categories.json").read_text())["categories"]]
        self.assertIn("fitness", cats)


class TestSculptTibi(unittest.TestCase):
    """The Cobalt Sculpt Tibi: generated runtime data matches its Python master, poses convert correctly."""

    @classmethod
    def setUpClass(cls):
        cls.exp = fitness.sculpt_exporter()
        cls.data = cls.exp.payload()
        import build2  # noqa: E402  (on sys.path through sculpt_exporter)
        cls.B = build2

    def test_sculpt_data_current(self):
        self.assertFalse(fitness.sculpt_stale(), "run `python scripts/fitness.py sculpt`")

    def test_every_painted_segment_has_art(self):
        segs, paths = self.data["segments"], self.data["paths"]
        for g in ("m", "f"):
            for view, keys in (("S", ["head", "neck", "pelvis", "thigh", "shin", "foot", "upperArm", "forearm", "hand"]),
                               ("F", ["head", "neck", "pelvis", "thigh", "shin", "foot", "upperArm", "upperArm_nd", "upperArm_flex", "forearm", "hand", "fist", "cap", "flare"]),
                               ("B", ["head", "neck", "pelvis", "thigh", "shin", "foot", "upperArm", "upperArm_nd", "upperArm_flex", "forearm", "hand", "fist", "cap", "flare"])):
                for k in keys:
                    sides = ["C"] if view == "S" or k in ("head", "neck", "pelvis") else ["L", "R"]
                    for sd in sides:
                        rec = segs.get(f"{g}{view}_{k}_{sd}")
                        self.assertIsNotNone(rec, f"{g}{view}_{k}_{sd}")
                        for pid in [rec["b"]] + [m[1] for m in rec["mus"]] + [c[1] for c in rec["cloth"]]:
                            self.assertIn(pid, paths)
            chest = ["chest"] if g == "m" else ["chest_sport", "chest_push"]
            for v in ("F", "S", "B"):
                for c in chest:
                    self.assertIn(f"{g}{v}_{c}_C", segs)
        self.assertIn("fF_pony_C", segs)
        self.assertIn("fB_pony_C", segs)

    def test_side_pose_conversion_reproduces_build2(self):
        # rebuild each segment's world angle from the exported joint values with the rig's signs
        signs = {"pelvis": 1, "spine": 1, "chest": 1, "neck": 1, "head": 1,
                 "shoulder": -1, "elbow": -1, "wrist": -1, "hip": -1, "knee": 1, "ankle": -1}
        parent = {"spine": "pelvis", "chest": "spine", "neck": "chest", "head": "neck",
                  "shoulder": "chest", "elbow": "shoulder", "wrist": "elbow", "hip": "pelvis", "knee": "hip", "ankle": "knee"}
        segkey = {"pelvis": "pelvis", "chest": "chest", "neck": "neck", "head": "head", "shoulder": "upperArm",
                  "elbow": "forearm", "wrist": "hand", "hip": "thigh", "knee": "shin", "ankle": "foot"}

        def world(j, jid):
            base = jid.rstrip("LR") if jid not in ("pelvis", "spine", "chest", "neck", "head") else jid
            side = jid[len(base):]
            a = signs[base] * j[jid]
            p = parent.get(base)
            return a + (world(j, p + (side if p in ("shoulder", "elbow", "hip", "knee") else "")) if p else 0)

        for g in ("m", "f"):
            for name in ("stand", "squat", "run_mid", "run_fly", "pushup"):
                pose = self.data["poses"][g]["side"][name.replace("_", "-")]
                spec = self.B.SIDE_POSES.get(name)
                segs, _, _ = self.B.side_pose(g, name)
                for P in segs:
                    for jid, key in segkey.items():
                        if key != P.key:
                            continue
                        sid = jid if jid in ("pelvis", "chest", "neck", "head") else jid + ("L" if P.far else "R")
                        self.assertAlmostEqual(world(pose["j"], sid), P.th, delta=0.05, msg=f"{g} {name} {P.key} far={P.far}")
                if spec:
                    self.assertEqual(pose["lift"], spec.get("lift", 0))

    def test_front_pose_conversion(self):
        for g in ("m", "f"):
            for kind, (a0, a1, a2) in self.exp.FRONT_ARMS.items():
                j = self.data["poses"][g]["front"][kind]["j"]
                self.assertEqual(j["shoulderR"], a0)
                self.assertEqual(j["shoulderR"] + j["elbowR"], a1)
                self.assertEqual(j["shoulderR"] + j["elbowR"] + j["wristR"], a2)

    def test_activation_tables_and_levels(self):
        self.assertEqual(set(self.data["acts"]), {k.replace("_", "-") for k in self.B.ACTS})
        self.assertEqual(self.data["levels"]["3"]["fill"], "#F2553D")
        self.assertEqual(self.data["levels"]["2"]["fill"], "#FFB224")
        self.assertEqual(self.data["levels"]["1"]["fill"], "#8CAEFA")

    def test_art_scales_mirror_what_build2_draws(self):
        for g in ("m", "f"):
            sk = self.data["skeleton"][g]
            self.assertEqual(sk["artLegScale"], 1.0)   # 0.965 rounds to 1 in build2.figure()
            self.assertEqual(sk["handScale"], 1.1)     # 1.15 rounds to 1.1

    def test_runtime_api_and_derive_hook(self):
        js = (ROOT / "src" / "studio" / "kits" / "fitness" / "sculpt.js").read_text(encoding="utf-8")
        for name in ("F.sculpt = function", "T.activate", "T.muscle", "T.markers", "T.spark", "T.soleFloor", "derive: function"):
            self.assertIn(name, js)
        rig = (ROOT / "src" / "studio" / "studio-rig.js").read_text(encoding="utf-8")
        self.assertIn("fig.spec.derive", rig)
        core = (ROOT / "src" / "studio" / "studio-core.js").read_text(encoding="utf-8")
        ver = tuple(int(x) for x in re.search(r"Studio\.version = '(\d+)\.(\d+)\.\d+'", core).groups())
        self.assertGreaterEqual(ver, (1, 6), "1.6.0: classic Tibi retired, foreshortening, back/top/above views, toes, grip hands")
        self.assertIn("function fore(", rig)

    def test_round7_data(self):
        segs, poses = self.data["segments"], self.data["poses"]
        for g in ("m", "f"):
            for k in ("S_toes_C", "S_grip_C", "S_hand_C", "F_fist_L", "B_fist_R"):
                self.assertIn(g + k, segs)
            self.assertEqual(self.data["skeleton"][g]["side"]["toe"][0] > 0, True)
            self.assertEqual(set(poses[g]["top"]), {"pushup", "pushup-bottom", "plank", "fly-low", "fly-high", "y-high"})
            self.assertEqual(set(poses[g]["above"]), {"fly-high", "fly-low"})
            self.assertTrue({"squat", "run-strike", "run-mid", "run-off", "run-fly"} <= set(poses[g]["back"]))
            self.assertEqual(poses[g]["side"]["calf"]["j"]["toeR"], 46)       # heel up, toes flat on the floor
        back = {nm for nm, _ in segs["mB_chest_C"]["mus"]}
        self.assertTrue({"trap", "midtrap", "lowtrap", "rhomb", "teres", "infra", "lat", "erector"} <= back)
        self.assertIn("rhomb", self.data["ghost"])

    def test_back3d_offsets_scale_with_foreshortening(self):
        # build2.rig_pose: a child's offset along its parent shrinks by the parent's f (the runtime's fore() rule)
        B = self.B
        segs, joints, W, A = B.rig_pose("m", B.BACK3D["back_squat"], "B")
        hip, knee = W["hipL"], W["kneeL"]
        L = ((knee[0] - hip[0]) ** 2 + (knee[1] - hip[1]) ** 2) ** 0.5
        self.assertAlmostEqual(L, 178.07 * B.BACK3D["back_squat"]["f"]["hipL"], delta=1.0)

    def test_library_matches_kit(self):
        js = (ROOT / "src" / "studio" / "kits" / "fitness" / "exercises.js").read_text(encoding="utf-8")
        ids = {e["id"] for e in json.loads((fitness.DATA / "exercises.json").read_text())["exercises"]}
        for i in ("push-up", "dumbbell-bench-press", "dumbbell-fly", "pull-up", "one-arm-row", "rear-delt-fly", "overhead-press",
                  "lateral-raise", "prone-y-raise", "incline-curl", "overhead-triceps-extension", "dip", "dumbbell-curl",
                  "back-squat", "deadlift", "barbell-bench-press", "leg-press", "lat-pulldown"):
            self.assertIn(i, ids)
            self.assertIn("EX['" + i + "']", js)

    def test_arm_blend_windows_leave_named_poses_unchanged(self):
        # sculpt kit 2.2.0 blends arm art inside per-view angle windows; a named pose inside a window would be
        # drawn half-blended, so every named pose must sit fully outside them (the exercise end poses are
        # audited in the browser: prompts/state/p05/2d-report.md)
        js = (ROOT / "src" / "studio" / "kits" / "fitness" / "sculpt.js").read_text(encoding="utf-8")
        raise_win = {v: (float(a), float(b)) for v, a, b in re.findall(r"(\w+): \[(\d+), (\d+)\]", re.search(r"var RAISE_WIN = \{([^}]*)\}", js).group(1))}
        bend = tuple(float(x) for x in re.search(r"BEND_WIN = \[(\d+), (\d+)\]", js).groups())
        self.assertEqual(set(raise_win), {"front", "back", "top", "above"})

        def ramp(v, w):
            x = min(1.0, max(0.0, (v - w[0]) / (w[1] - w[0])))
            return x * x * (3 - 2 * x)

        for g in ("m", "f"):
            for view, win in raise_win.items():
                for name, pose in self.data["poses"][g][view].items():
                    for x in "RL":
                        r = ramp(pose["j"].get("shoulder" + x, 0), win)
                        self.assertIn(r, (0.0, 1.0), f"{g} {view} {name}: shoulder{x} inside the blend window {win}")
                        if r == 1.0:
                            self.assertIn(ramp(pose["j"].get("elbow" + x, 0), bend), (0.0, 1.0), f"{g} {view} {name}: elbow{x} inside {bend}")

    def test_front_squat_pose(self):
        for g in ("m", "f"):
            sq = self.data["poses"][g]["front"]["squat"]
            self.assertLess(sq["f"]["hipR"], 0.5, "thighs point at the camera: foreshortened")
            self.assertTrue(sq["grip"])
        self.assertIn("front-squat", self.data["acts"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
