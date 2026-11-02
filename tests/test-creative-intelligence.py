#!/usr/bin/env python3
"""Tests for the creative intelligence layer: colour science, design profiles, beat maps, asset engine,
KIE adapter (against a local stub), motion QA.

Run with the venv interpreter (Pillow, NumPy, jsonschema):  .venv/bin/python tests/test-creative-intelligence.py
Heavy tests that need HyperFrames/ffmpeg skip themselves when those tools are absent. Nothing here calls
a paid or remote service: the KIE adapter is exercised against an in-process HTTP stub.
"""
from __future__ import annotations

import copy
import http.server
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

import numpy as np  # noqa: E402

import colorscience as cs  # noqa: E402
import profiles as pf  # noqa: E402
from pipeline.assets import base  # noqa: E402
from pipeline.assets.engine import Engine  # noqa: E402
from pipeline.assets.providers.kie import KieProvider  # noqa: E402
from pipeline.assets.providers.mock import MockProvider  # noqa: E402
from pipeline.assets.providers.procedural import ProceduralProvider  # noqa: E402
from pipeline.assets.secrets import redact  # noqa: E402


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


# ------------------------------------------------------------------------------------------- colour
class TestColour(unittest.TestCase):
    def test_ciede2000_published_vectors(self):
        # Sharma, Wu, Dalal (2005) supplementary data
        vec = [((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425), ((50, 3.1571, -77.2803), (50, 0, -82.7485), 2.8615),
               ((50, 2.8361, -74.0200), (50, 0, -82.7485), 3.4412), ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
               ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082)]
        for a, b, exp in vec:
            self.assertAlmostEqual(float(cs.delta_e2000(np.array(a), np.array(b))), exp, places=3)

    def test_contrast_ratio(self):
        self.assertAlmostEqual(cs.contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=1)

    def test_palette_recovers_known_coverage_and_is_deterministic(self):
        img = np.zeros((360, 640, 3), np.uint8)
        img[:] = cs.hex_to_rgb("#FBFBFA")
        img[:, :160] = cs.hex_to_rgb("#D24A26")
        img[:36, 160:] = cs.hex_to_rgb("#2A2522")
        m1, m2 = cs.measure_palette(img, k=6), cs.measure_palette(img, k=6)
        self.assertEqual(m1, m2)
        cov = {p["hex"]: p["coverage"] for p in m1["palette"]}
        self.assertAlmostEqual(cov["#fbfbfa"], 0.675, delta=0.01)
        self.assertAlmostEqual(cov["#d24a26"], 0.25, delta=0.01)
        self.assertTrue(cs.verify_against(m1["palette"], m1)["pass"])

    def test_verify_fails_on_wrong_colours(self):
        a = np.zeros((90, 160, 3), np.uint8); a[:] = (240, 240, 235); a[:, :60] = (210, 74, 38)
        b = np.zeros((90, 160, 3), np.uint8); b[:] = (240, 240, 235); b[:, :60] = (30, 140, 200)
        res = cs.verify_against(cs.measure_palette(a)["palette"], cs.measure_palette(b))
        self.assertFalse(res["pass"])

    def test_structure_distance_ignores_palette_but_sees_layout(self):
        def comp(bg, fg, box):
            im = np.zeros((90, 160, 3), np.uint8); im[:] = bg
            y0, y1, x0, x1 = box; im[y0:y1, x0:x1] = fg
            return cs.ink_map(im)
        same_layout_a = comp((250, 248, 240), (200, 60, 30), (20, 60, 20, 100))
        same_layout_b = comp((12, 20, 30), (240, 200, 90), (20, 60, 20, 100))
        other_layout = comp((250, 248, 240), (200, 60, 30), (50, 85, 90, 150))
        self.assertLess(cs.structure_distance(same_layout_a, same_layout_b), 0.02)
        self.assertGreater(cs.structure_distance(same_layout_a, other_layout), 0.1)


# ------------------------------------------------------------------------------------------- profiles
class TestProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = pf.load_registry()
        import jsonschema  # noqa: F401
        cls.styles = {json.loads(p.read_text())["id"]: 1 for p in (ROOT / "catalogue/data/styles").glob("*.json")}
        cls.techs = {json.loads(p.read_text())["id"]: 1 for p in (ROOT / "catalogue/data/references").glob("*.json")}

    def test_registry_has_nine_styles_and_fourteen_extracted_references(self):
        kinds = [p["kind"] for p in self.reg.values()]
        self.assertEqual(kinds.count("registry"), 9)
        self.assertEqual(kinds.count("extracted"), 14)

    def test_every_profile_validates(self):
        for pid, p in self.reg.items():
            self.assertEqual(pf.schema_errors(p), [], pid)
            errs, _ = pf.check_profile(p, self.styles, self.techs, None, self.reg)
            self.assertEqual(errs, [], pid)

    def test_every_profile_declares_weaknesses(self):
        for pid, p in self.reg.items():
            self.assertTrue(p["weaknesses"], pid)

    def test_provenance_rules_reject_fabrication(self):
        base_p = copy.deepcopy(self.reg["x-ref-0bf0254a3d"])
        cases = {
            "measured without evidence": lambda p: p["design_system"]["palette"]["colors"][0].pop("evidence"),
            "prescribed on extracted": lambda p: p["identity"].__setitem__("mood", {"value": "warm", "basis": "prescribed"}),
            "bare string on extracted": lambda p: p["identity"].__setitem__("genre", "documentary"),
            "number on unknown": lambda p: p["motion"]["timing"].__setitem__("typical_move_sec", {"value": 0.4, "basis": "unknown"}),
            "unknown style": lambda p: (p.__setitem__("kind", "registry"), p.__setitem__("style", "nope")),
        }
        for name, mutate in cases.items():
            p = copy.deepcopy(base_p)
            mutate(p)
            errs = pf.schema_errors(p) + pf.check_profile(p, self.styles, self.techs, None, self.reg)[0]
            self.assertTrue(errs, name)

    def test_extracted_profiles_measure_not_invent(self):
        for pid, p in self.reg.items():
            if p["kind"] != "extracted":
                continue
            for c in p["design_system"]["palette"]["colors"]:
                self.assertEqual(c["basis"], "measured")
                self.assertTrue((ROOT / c["evidence"].split("#")[0]).exists(), c["evidence"])

    def test_project_profile_resolves_over_registry(self):
        proj = {"id": "demo-direction", "kind": "project", "extends": "editorial-paper-collage",
                "motion": {"timing": {"typical_move_sec": {"value": 0.6, "basis": "subjective"}}}}
        out = pf.resolve(proj, self.reg)
        self.assertEqual(out["style"], "paper-cut")
        self.assertEqual(out["motion"]["timing"]["typical_move_sec"]["value"], 0.6)
        self.assertIn("pace", out["motion"]["timing"])  # inherited


# ------------------------------------------------------------------------------------------- beat map
class TestBeatmap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bm = load_script("beatmap")

    def good(self):
        arc = self.bm.arcs()["problem-mechanism-consequence"]
        stages = [s["id"] for s in arc["stages"]]
        beats = [{"id": s, "stage": s, "purpose": f"Purpose of {s} in the story", "viewer_takeaway": f"takeaway {s}", "visual_concept": f"a distinct picture number {i} of crystals",
                  "target_duration_sec": 10, "narration": "totally different words spoken here"} for i, s in enumerate(stages)]
        return {"spec_version": 1, "slug": "t", "concept": {"logline": "a film about testing beat maps", "viewer_change": "knows tests"},
                "arc": {"id": arc["id"], "stages": stages}, "target_duration_sec": 40, "beats": beats,
                "global_direction": {"sound_design": "sparse"}}

    def test_valid_map_passes(self):
        errs, warns = self.bm.check(self.good(), None)
        self.assertEqual(errs, [], errs)
        self.assertEqual(warns, [])

    def test_arc_library_is_well_formed(self):
        lib = self.bm.arcs()
        self.assertGreaterEqual(len(lib), 8)
        for a in lib.values():
            self.assertGreaterEqual(len(a["stages"]), 3, a["id"])

    def test_todo_and_missing_fallback_are_errors(self):
        d = self.good()
        d["beats"][0]["purpose"] = "TODO: fill in later please"
        d["beats"][1]["assets"] = [{"role": "plate", "medium": "generated-image", "strategy": "generate"}]
        errs, _ = self.bm.check(d, None)
        self.assertTrue(any("TODO" in e for e in errs))
        self.assertTrue(any("fallback" in e for e in errs))

    def test_visual_restating_narration_is_flagged(self):
        d = self.good()
        d["beats"][0]["narration"] = "the machine moves the gears through the housing"
        d["beats"][0]["visual_concept"] = "the machine moves the gears through the housing"
        _, warns = self.bm.check(d, None)
        self.assertTrue(any("restates the narration" in w for w in warns))

    def test_repeated_composition_and_overspent_emphasis_are_flagged(self):
        d = self.good()
        for b in d["beats"]:
            b["importance"] = "anchor"
            b["shots"] = [{"id": "a", "composition": "left headline, right device", "camera_movement": "push-in"}]
        _, warns = self.bm.check(d, None)
        self.assertTrue(any("anchor" in w for w in warns))
        self.assertTrue(any("composition" in w and "planned" in w for w in warns) or len(d["beats"]) < 3)

    def test_storyboard_derivation_is_valid_against_existing_spec(self):
        import jsonschema
        d = self.good()
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "beatmap.json").write_text(json.dumps(d))
            a = type("A", (), {"target": str(tmp), "force": True})
            self.bm.cmd_storyboard(a)
            sb = json.loads((tmp / "storyboard.json").read_text())
            errs = list(jsonschema.Draft7Validator(json.loads((ROOT / "specs/storyboard-spec.json").read_text())).iter_errors(sb))
            self.assertEqual([e.message for e in errs], [])
            self.assertEqual(sb["scenes"][1]["start_sec"], 10.0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------------------------------- assets
class EngineCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.clock = FakeClock()
        self.mock = MockProvider(self.tmp / "mockstate")
        self.eng = Engine(self.tmp, {"mock": self.mock, "procedural": ProceduralProvider()}, sleep=self.clock.sleep, clock=self.clock.now)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def job(self, prompt, mock=None, providers=("mock",), **kw):
        res = self.eng.submit(project="t", task="text-to-image", request={"prompt": prompt, "_mock": mock or {}}, providers=list(providers), **kw)
        return res["job"] if "job" in res else res


class TestEngine(EngineCase):
    def test_async_job_completes_registers_and_is_reused(self):
        j = self.job("a harbour", {"polls": 3})
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.SUCCEEDED)
        self.assertGreaterEqual(j["poll_count"], 3)
        self.assertEqual(j["cost"]["credits"], 1.0)
        a = self.eng.lib.get(j["asset_ids"][0])
        self.assertEqual(a["provider"], "mock")
        self.assertEqual(a["request_key"], j["request_key"])
        again = self.eng.submit(project="t", task="text-to-image", request={"prompt": "a harbour", "_mock": {"polls": 3}}, providers=["mock"])
        self.assertTrue(again["reused"])
        self.assertEqual(again["asset"]["id"], a["id"])
        self.assertEqual(self.mock._load()["counters"]["submit:a harbour"], 1)  # provider was not called again

    def test_transient_failures_retry_up_to_a_bound_then_succeed(self):
        j = self.job("retry me", {"fail_submit": 2}, max_attempts=3)
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.SUCCEEDED)
        self.assertEqual(j["attempts"], 3)

    def test_retry_bound_is_enforced(self):
        j = self.job("never works", {"fail_submit": 99}, max_attempts=2)
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.FAILED)
        self.assertEqual(j["attempts"], 2)
        self.assertEqual(j["error"]["kind"], "network")

    def test_provider_failure_is_isolated_not_raised(self):
        bad = self.job("auth fails", {"fail_with": "auth"})
        good = self.job("fine")
        self.eng.run([bad, good], poll_sec=1)
        self.assertEqual(bad["state"], base.FAILED)
        self.assertEqual(bad["error"], {"kind": "auth", "retryable": False, "message": "mock refused (auth)"})
        self.assertEqual(good["state"], base.SUCCEEDED)
        self.assertEqual(bad["attempts"], 1)  # a non-retryable error is not retried

    def test_remote_failure_marks_failed_without_retry_when_not_retryable(self):
        j = self.job("remote bad", {"fail_job": True})
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.FAILED)
        self.assertEqual(j["attempts"], 1)

    def test_timeout_keeps_remote_id_and_does_not_hang(self):
        j = self.job("stuck", {"hang": True}, deadline_sec=20)
        self.eng.run([j], poll_sec=3)
        self.assertEqual(j["state"], base.TIMED_OUT)
        self.assertTrue(j["remote_id"])
        self.assertEqual(j["error"]["kind"], "timeout")

    def test_crash_and_resume_polls_instead_of_resubmitting(self):
        j = self.job("long job", {"polls": 5})
        self.eng.step(j)  # submit
        self.eng.step(j)  # one poll
        rid = j["remote_id"]
        self.assertEqual(j["state"], base.RUNNING)
        # "crash": new provider + engine objects over the same files
        mock2 = MockProvider(self.tmp / "mockstate")
        eng2 = Engine(self.tmp, {"mock": mock2}, sleep=self.clock.sleep, clock=self.clock.now)
        done = eng2.resume_all(poll_sec=1)
        self.assertEqual(len(done), 1)
        self.assertEqual(done[0]["state"], base.SUCCEEDED)
        self.assertEqual(done[0]["remote_id"], rid)
        self.assertEqual(mock2._load()["counters"]["submit:long job"], 1)  # never re-submitted (no double billing)
        # identical request while open resumes the same job
        j2 = self.eng.submit(project="t", task="text-to-image", request={"prompt": "pending one", "_mock": {"polls": 9}}, providers=["mock"])["job"]
        self.eng.step(j2)
        again = self.eng.submit(project="t", task="text-to-image", request={"prompt": "pending one", "_mock": {"polls": 9}}, providers=["mock"])
        self.assertTrue(again.get("resumed"))
        self.assertEqual(again["job"]["id"], j2["id"])

    def test_fallback_chain_moves_to_next_provider(self):
        mock_b = MockProvider(self.tmp / "mock-b")
        eng = Engine(self.tmp, {"mock": self.mock, "mockb": mock_b}, sleep=self.clock.sleep, clock=self.clock.now)
        j = eng.submit(project="t", task="text-to-image", request={"prompt": "fallback", "_mock": {}}, providers=["mock", "mockb"])["job"]
        # make the first provider refuse for this request only
        j["request"]["_mock"] = {"fail_with": "auth"}
        eng.run([j], poll_sec=1)
        # same mock settings reach mockb, which also refuses: chain exhausted -> failed, with the fallback recorded
        self.assertEqual(j["state"], base.FAILED)
        self.assertEqual(j["fallbacks"], ["mockb"])
        j2 = eng.submit(project="t", task="text-to-image", request={"prompt": "fallback two", "_mock": {}}, providers=["mock", "mockb"])["job"]
        j2["provider"] = "mock"
        mock_b2 = mock_b
        orig = self.mock.submit
        self.mock.submit = lambda task, req: (_ for _ in ()).throw(base.ProviderError("provider", "first provider down", False))
        eng.run([j2], poll_sec=1)
        self.mock.submit = orig
        self.assertEqual(j2["state"], base.SUCCEEDED)
        self.assertEqual(j2["provider"], "mockb")

    def test_unusable_task_is_not_planned_and_unavailable_is_reported(self):
        plan = self.eng.plan("text-to-video", aspect="16:9", duration=5)
        self.assertEqual([p["provider"] for p in plan], ["mock"])
        plan = self.eng.plan("text-to-image", aspect="3:2")
        self.assertFalse(plan[0]["fits"])

    def test_procedural_is_deterministic_and_credential_free(self):
        req = {"recipe": "paper-grain", "width": 128, "height": 72, "seed": 5, "colors": ["#f2e8d5"], "prompt": "paper"}
        a = self.eng.submit(project="t", task="procedural-image", request=req, providers=["procedural"], model="paper-grain")["job"]
        self.eng.run([a], poll_sec=0)
        self.assertEqual(a["state"], base.SUCCEEDED)
        rec = self.eng.lib.get(a["asset_ids"][0])
        req2 = {**req, "seed": 6}
        b = self.eng.submit(project="t", task="procedural-image", request=req2, providers=["procedural"], model="paper-grain")["job"]
        self.eng.run([b], poll_sec=0)
        self.assertNotEqual(rec["sha256"], self.eng.lib.get(b["asset_ids"][0])["sha256"])
        # same seed again from a clean library reproduces the identical bytes
        tmp2 = Path(tempfile.mkdtemp())
        try:
            eng2 = Engine(tmp2, {"procedural": ProceduralProvider()})
            c = eng2.submit(project="t", task="procedural-image", request=req, providers=["procedural"], model="paper-grain")["job"]
            eng2.run([c], poll_sec=0)
            self.assertEqual(eng2.lib.get(c["asset_ids"][0])["sha256"], rec["sha256"])
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_all_procedural_recipes_render(self):
        from pipeline.assets.providers.procedural import RECIPES, render
        for r in RECIPES:
            im = render(r, 96, 54, 1, ["#102030", "#304050", "#a0b0c0"], {})
            self.assertEqual(im.size, (96, 54), r)

    def test_asset_and_job_records_match_the_published_spec(self):
        import jsonschema
        spec = json.loads((ROOT / "specs/asset-spec.json").read_text())
        j = self.job("spec check")
        self.eng.run([j], poll_sec=1)
        job_rec = {k: v for k, v in self.eng.jobs.load(j["id"]).items() if not k.startswith("_")}
        job_rec.pop("fallbacks", None); job_rec.pop("last_poll_error", None); job_rec.pop("backoff_sec", None)
        for name, rec in (("job", job_rec), ("asset", self.eng.lib.get(j["asset_ids"][0])), ("capabilities", self.mock.capabilities())):
            v = jsonschema.Draft7Validator({**spec, "$ref": f"#/definitions/{name}"})
            self.assertEqual([e.message for e in v.iter_errors(rec)], [], name)
        for p in (ProceduralProvider(), KieProvider()):
            v = jsonschema.Draft7Validator({**spec, "$ref": "#/definitions/capabilities"})
            self.assertEqual([e.message for e in v.iter_errors(p.capabilities())], [], p.name)


# ------------------------------------------------------------------------------------------- kie stub
class Stub(http.server.BaseHTTPRequestHandler):
    log = []
    mode = {"tasks": {}}
    key_seen = []

    def log_message(self, *a):
        pass

    def _send(self, obj, status=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        Stub.log.append(("POST", self.path, self.headers.get("Authorization"), body)); Stub.key_seen.append(self.headers.get("Authorization"))
        if self.headers.get("Authorization") != "Bearer sk-test-key-123456789":
            return self._send({"code": 401, "msg": "You do not have access permissions"})  # documented style: HTTP 200 + code
        if body.get("model") == "rate/limited":
            return self._send({"code": 429, "msg": "rate limit, key sk-test-key-123456789 exceeded"})
        tid = f"task_{len(Stub.mode['tasks']) + 1}"
        Stub.mode["tasks"][tid] = {"polls": 0, "model": body["model"], "fail": body["model"] == "fails/always"}
        self._send({"code": 200, "msg": "success", "data": {"taskId": tid}})

    def do_GET(self):
        Stub.log.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path.startswith("/file/"):
            Stub.key_seen.append(self.headers.get("Authorization"))
            from PIL import Image
            import io
            buf = io.BytesIO(); Image.new("RGB", (32, 18), (200, 30, 30)).save(buf, "PNG")
            return self._send(buf.getvalue(), ctype="image/png")
        if self.path.startswith("/api/v1/jobs/recordInfo"):
            tid = self.path.split("taskId=")[1]
            t = Stub.mode["tasks"][tid]; t["polls"] += 1
            host = f"http://127.0.0.1:{self.server.server_port}"
            if t["fail"]:
                d = {"taskId": tid, "state": "fail", "failCode": "500", "failMsg": "content policy", "resultJson": ""}
            elif t["polls"] == 1:
                d = {"taskId": tid, "state": "waiting"}
            elif t["polls"] == 2:
                d = {"taskId": tid, "state": "generating"}
            else:
                d = {"taskId": tid, "state": "success", "resultJson": json.dumps({"resultUrls": [host + "/file/out.png"]}), "creditsConsumed": 2.5, "costTime": 7}
            return self._send({"code": 200, "msg": "success", "data": d})
        self._send({"code": 404, "msg": "nope"}, 404)


class TestKie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        Stub.log.clear(); Stub.key_seen.clear(); Stub.mode["tasks"].clear()
        self.tmp = Path(tempfile.mkdtemp())
        self.clock = FakeClock()
        os.environ.pop("KIE_API_KEY", None)
        self.eng = Engine(self.tmp, {"kie": KieProvider(self.base, sleep=self.clock.sleep, clock=self.clock.now)}, sleep=self.clock.sleep, clock=self.clock.now)

    def tearDown(self):
        os.environ.pop("KIE_API_KEY", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def job(self, model, prompt="x", **kw):
        return self.eng.submit(project="t", task="text-to-image", request={"prompt": prompt, "aspect_ratio": "16:9"}, providers=["kie"], model=model, **kw)["job"]

    def test_missing_key_fails_typed_without_any_network_call(self):
        j = self.job("any/model")
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.FAILED)
        self.assertEqual(j["error"]["kind"], "auth")
        self.assertEqual(Stub.log, [])
        self.assertIn("KIE_API_KEY", j["error"]["message"])

    def test_documented_envelope_full_lifecycle_and_key_not_sent_to_cdn(self):
        os.environ["KIE_API_KEY"] = "sk-test-key-123456789"
        j = self.job("vendor/model-x")
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.SUCCEEDED, j.get("error"))
        post = next(l for l in Stub.log if l[0] == "POST")
        self.assertEqual(post[1], "/api/v1/jobs/createTask")
        self.assertEqual(post[3], {"model": "vendor/model-x", "input": {"prompt": "x", "aspect_ratio": "16:9"}})
        self.assertEqual(j["cost"], {"credits": 2.5, "reported_by": "kie"})
        file_get = next(l for l in Stub.log if l[1].startswith("/file/"))
        self.assertIsNone(file_get[2], "API key must not be sent when downloading results")
        self.assertEqual(self.eng.lib.get(j["asset_ids"][0])["provider"], "kie")

    def test_wrong_key_comes_back_as_http200_code401_and_maps_to_auth(self):
        os.environ["KIE_API_KEY"] = "sk-wrong-key-00000000"
        j = self.job("vendor/model-x")
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["error"]["kind"], "auth")
        self.assertEqual(j["attempts"], 1)

    def test_rate_limit_is_retryable_and_bounded_and_key_is_redacted(self):
        os.environ["KIE_API_KEY"] = "sk-test-key-123456789"
        j = self.job("rate/limited", max_attempts=2)
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.FAILED)
        self.assertEqual(j["attempts"], 2)
        self.assertEqual(j["error"]["kind"], "rate-limit")
        stored = (self.eng.jobs.path(j["id"])).read_text()
        self.assertNotIn("sk-test-key-123456789", stored)
        self.assertNotIn("sk-test-key-123456789", json.dumps(j))
        self.assertIn("[REDACTED]", stored)

    def test_remote_failure_reports_code_and_message(self):
        os.environ["KIE_API_KEY"] = "sk-test-key-123456789"
        j = self.job("fails/always")
        self.eng.run([j], poll_sec=1)
        self.assertEqual(j["state"], base.FAILED)
        self.assertIn("content policy", j["error"]["message"])

    def test_adapter_does_not_claim_more_than_it_verified(self):
        c = KieProvider().capabilities()
        self.assertEqual(c["verification"]["level"], "partial")
        self.assertTrue(c["verification"]["unverified"])
        for t in c["tasks"].values():
            self.assertEqual(t["models"], [], "no model list may be asserted")
        for t in c["tasks"].values():
            self.assertNotIn("pricing", t, "prices are never asserted without a source")


class TestSecrets(unittest.TestCase):
    def test_redaction_of_token_shapes(self):
        s = redact("Authorization: Bearer abcDEF1234567890xyz and api_key=sk-live-AAAAAAAAAAAAAAAAAAAA ok")
        self.assertNotIn("abcDEF1234567890xyz", s)
        self.assertNotIn("sk-live-AAAAAAAAAAAAAAAAAAAA", s)
        self.assertIn("ok", s)

    def test_no_provider_or_record_in_the_repo_contains_a_literal_key(self):
        import re
        pat = re.compile(r"sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|Bearer [A-Za-z0-9]{24,}")
        for p in list((ROOT / "src/pipeline").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")) + list((ROOT / "catalogue/data/design-profiles").glob("*.json")):
            self.assertIsNone(pat.search(p.read_text(errors="ignore")), str(p))


# ------------------------------------------------------------------------------------------- motion QA
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
HAVE_PROBE = bool(shutil.which("hyperframes") and shutil.which("npm"))


def make_video(path: Path, segments, size=(320, 180), fps=30, audio=True):
    """segments: [(seconds, (r,g,b), motion)] -> mp4. motion=True draws a moving box so frames change."""
    from PIL import Image, ImageDraw
    tmp = Path(tempfile.mkdtemp())
    try:
        n = 0
        for secs, rgb, motion in segments:
            for i in range(int(secs * fps)):
                im = Image.new("RGB", size, rgb)
                if motion:
                    x = (i * 7) % (size[0] - 60)
                    ImageDraw.Draw(im).rectangle((x, 60, x + 50, 120), fill=(255 - rgb[0], 255 - rgb[1], 255 - rgb[2]))
                im.save(tmp / f"f{n:05d}.png")
                n += 1
        cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(tmp / "f%05d.png")]
        if audio:
            cmd += ["-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000", "-shortest", "-c:a", "aac", "-b:a", "96k"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
        import subprocess
        subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not available")
class TestMotionQAVideo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mq = load_script("motion-qa")
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_video(self, path, ctx=None, **kw):
        a = type("A", (), dict(expect_size=kw.get("size"), expect_fps=kw.get("fps"), expect_duration=kw.get("duration"), expect_audio=kw.get("audio", False), lufs=None, format=None))()
        rep = self.mq.Report({"kind": "video", "path": str(path)})
        self.mq.video_checks(rep, ctx or self.mq.Context(None, None), path, a)
        return rep, rep.doc()

    def ids(self, doc, cls=None, sev=None):
        return [f["id"] for f in doc["findings"] if (cls is None or f["class"] == cls) and (sev is None or f["severity"] == sev) and "waived_by" not in f]

    def test_clean_moving_video_has_no_findings_and_passes(self):
        p = self.tmp / "clean.mp4"
        make_video(p, [(4, (240, 235, 220), True)])
        from pipeline import videoscan  # noqa: F401
        import videoscan as vs
        target = vs.loudness(str(p))["integrated_lufs"]  # the synthetic tone is not at -16 LUFS; the tool is right to say so
        a = type("A", (), dict(expect_size="320x180", expect_fps=30, expect_duration=4.0, expect_audio=True, lufs=target, format=None))()
        rep = self.mq.Report({"kind": "video", "path": str(p)})
        self.mq.video_checks(rep, self.mq.Context(None, None), p, a)
        d = rep.doc()
        self.assertEqual(self.ids(d, sev="fail"), [])
        self.assertEqual(self.ids(d, "measured", "warn"), [])
        self.assertTrue(d["summary"]["technical_pass"])

    def test_black_gap_is_an_objective_failure(self):
        p = self.tmp / "black.mp4"
        make_video(p, [(2, (240, 235, 220), True), (1, (0, 0, 0), False), (2, (240, 235, 220), True)])
        _, d = self.run_video(p)
        self.assertIn("black-gap", self.ids(d, "objective", "fail"))
        self.assertFalse(d["summary"]["technical_pass"])

    def test_designed_darkness_is_a_measured_lead_not_an_objective_failure(self):
        p = self.tmp / "dark.mp4"
        make_video(p, [(2, (200, 200, 200), True), (3, (3, 5, 8), False), (2, (200, 200, 200), True)])
        _, d = self.run_video(p)
        self.assertNotIn("black-gap", self.ids(d, "objective", "fail"))
        self.assertIn("very-dark", self.ids(d, "measured", "warn"))
        ctx = self.mq.Context(None, None)
        ctx.scenes = [{"id": "deep", "start_sec": 2.0, "end_sec": 5.0, "intent": "dark"}]
        ctx.intent = {"deep": "dark"}
        _, d2 = self.run_video(p, ctx)
        self.assertNotIn("very-dark", self.ids(d2, "measured", "warn"))
        self.assertTrue([f for f in d2["findings"] if f["id"] == "very-dark" and "waived_by" in f])

    def test_slow_drift_is_not_called_frozen_but_a_frozen_frame_is(self):
        from PIL import Image, ImageDraw
        import subprocess
        def build(name, drift):
            tmp = Path(tempfile.mkdtemp())
            try:
                rng = np.random.default_rng(3)
                base = (rng.random((180, 700)) * 60 + 120).astype(np.uint8)  # textured so a shift changes pixels
                for i in range(150):
                    off = int(i * 0.9) if drift else 0
                    arr = np.stack([base[:, off:off + 320]] * 3, axis=-1)
                    Image.fromarray(arr).save(tmp / f"f{i:05d}.png")
                out = self.tmp / name
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(tmp / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "12", str(out)], check=True, stdin=subprocess.DEVNULL)
                return out
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        drifting, frozen = build("drift.mp4", True), build("frozen.mp4", False)
        d1 = self.run_video(drifting)[1]
        d2 = self.run_video(frozen)[1]
        self.assertNotIn("static-hold", self.ids(d1, "measured"))
        self.assertIn("static-hold", self.ids(d2, "measured"))
        frozen_f = [f for f in d2["findings"] if f["id"] == "static-hold"][0]
        self.assertIn("frozen", frozen_f["message"])

    def test_wrong_size_and_duration_are_objective_failures(self):
        p = self.tmp / "size.mp4"
        make_video(p, [(3, (200, 200, 200), True)])
        _, d = self.run_video(p, size="1280x720", duration=10.0)
        got = self.ids(d, "objective", "fail")
        self.assertIn("size", got)
        self.assertIn("duration", got)

    def test_off_target_loudness_is_reported(self):
        p = self.tmp / "loud.mp4"
        make_video(p, [(3, (240, 235, 220), True)])
        self.assertIn("loudness", self.ids(self.run_video(p)[1], "measured", "warn"))

    def test_missing_audio_fails_only_when_required(self):
        p = self.tmp / "silent.mp4"
        make_video(p, [(3, (200, 200, 200), True)], audio=False)
        self.assertNotIn("audio-missing", self.ids(self.run_video(p)[1], "objective", "fail"))
        self.assertIn("audio-missing", self.ids(self.run_video(p, audio=True)[1], "objective", "fail"))

    def test_static_hold_flagged_then_waived_by_declared_intent(self):
        p = self.tmp / "hold.mp4"
        make_video(p, [(2, (240, 235, 220), True), (3.5, (240, 235, 220), False), (2, (240, 235, 220), True)])
        _, d = self.run_video(p)
        self.assertIn("static-hold", self.ids(d, "measured", "warn"))
        ctx = self.mq.Context(None, None)
        ctx.scenes = [{"id": "hold", "start_sec": 2.0, "end_sec": 5.5, "intent": "still"}]
        ctx.intent = {"hold": "still"}
        _, d2 = self.run_video(p, ctx)
        self.assertNotIn("static-hold", self.ids(d2, "measured", "warn"))
        waived = [f for f in d2["findings"] if f["id"] == "static-hold" and "waived_by" in f]
        self.assertTrue(waived)
        self.assertEqual(waived[0]["waived_by"]["intent"], "intent:still")
        self.assertEqual(d2["summary"]["waived"], len(waived))

    def test_repeated_composition_detected_and_varied_layout_not(self):
        from PIL import Image, ImageDraw
        def slide(i, same):
            im = Image.new("RGB", (320, 180), (245, 240, 230))
            d = ImageDraw.Draw(im)
            if same:
                d.rectangle((20, 20, 150, 60), fill=(30, 30, 30)); d.rectangle((180, 40, 300, 160), fill=(200, 60, 40))
            else:
                boxes = [(10, 100, 310, 170), (200, 10, 300, 90), (20, 20, 90, 150), (110, 60, 250, 120)]
                d.rectangle(boxes[i % 4], fill=(30, 30, 30))
            return im
        def build(name, flags):
            tmp = Path(tempfile.mkdtemp())
            try:
                n = 0
                for k, same in enumerate(flags):
                    for j in range(60):
                        im = slide(k, same); ImageDraw.Draw(im).ellipse((300 - j % 6, 4, 310, 14), fill=(0, 0, 0)); im.save(tmp / f"f{n:05d}.png"); n += 1
                import subprocess
                out = self.tmp / name
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(tmp / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True, stdin=subprocess.DEVNULL)
                return out
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        ctx = self.mq.Context(None, None)
        ctx.scenes = [{"id": f"s{i}", "start_sec": 2.0 * i, "end_sec": 2.0 * (i + 1), "transition_out": {"type": "crossfade"}} for i in range(6)]
        same = build("same.mp4", [True] * 6)
        varied = build("varied.mp4", [False] * 6)
        self.assertIn("repeat-composition", self.ids(self.run_video(same, ctx)[1], "measured"))
        self.assertNotIn("repeat-composition", self.ids(self.run_video(varied, ctx)[1], "measured"))
        self.assertIn("repeat-transition", self.ids(self.run_video(same, ctx)[1], "measured"))  # six identical crossfades

    def test_report_matches_its_spec_and_never_claims_a_creative_pass(self):
        import jsonschema
        p = self.tmp / "spec.mp4"
        make_video(p, [(3, (200, 200, 200), True)])
        rep, d = self.run_video(p)
        errs = list(jsonschema.Draft7Validator(json.loads((ROOT / "specs/qa-report-spec.json").read_text())).iter_errors(d))
        self.assertEqual([e.message for e in errs], [])
        self.assertNotIn("creative", json.dumps(d["summary"]))
        skipped = [c for c in d["checks_run"] if c["status"] != "ran"]
        self.assertTrue(any(c["id"] == "audio-cut-alignment" and c.get("reason") for c in skipped), "an unimplemented check must say so")


@unittest.skipUnless(HAVE_PROBE and (Path.home() / ".cache/puppeteer").exists(), "hyperframes browser tooling not available")
class TestMotionQAComposition(unittest.TestCase):
    HTML = """<!DOCTYPE html><html><head><meta charset=utf-8><style>
    html,body{margin:0}#root{position:relative;width:1280px;height:720px;background:#fbfbfa;color:#111;font-family:Arial}
    .t{position:absolute;white-space:nowrap}</style></head><body>
    <div id="root" data-composition-id="root" data-format="landscape" data-width="1280" data-height="720" data-fps="30" data-duration="3">%s</div>
    <script>window.__timelines={root:{pause(){},seek(){},duration(){return 3}}};</script></body></html>"""

    @classmethod
    def setUpClass(cls):
        cls.mq = load_script("motion-qa")
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def lint(self, body, name, ctx=None):
        p = self.tmp / f"{name}.html"
        p.write_text(self.HTML % body)
        ctx = ctx or self.mq.Context(None, "landscape")
        rep = self.mq.Report({"kind": "composition", "path": str(p)})
        self.mq.composition_checks(rep, ctx, p, "landscape", [], 3.0)
        return rep.doc()

    def ids(self, d):
        return {f["id"] for f in d["findings"] if "waived_by" not in f}

    def test_clean_composition_has_no_text_findings(self):
        d = self.lint('<div class="t" style="left:80px;top:80px;font-size:72px;font-weight:700">A clear headline</div>'
                      '<div class="t" style="left:80px;top:300px;font-size:34px">One short supporting sentence.</div>', "clean")
        self.assertTrue({"text-size-floor", "text-collision", "text-outside-frame", "low-contrast"}.isdisjoint(self.ids(d)), self.ids(d))

    def test_small_text_collision_and_low_contrast_are_found(self):
        d = self.lint('<div class="t" style="left:80px;top:80px;font-size:12px">tiny label</div>'
                      '<div class="t" style="left:80px;top:300px;font-size:60px">Overlapping words here</div>'
                      '<div class="t" style="left:100px;top:310px;font-size:60px">Another line on top</div>'
                      '<div class="t" style="left:80px;top:500px;font-size:40px;color:#d8d8d4">pale text on near white</div>', "bad")
        self.assertTrue({"text-size-floor", "text-collision", "low-contrast"} <= self.ids(d), self.ids(d))

    def test_tight_leading_numeral_over_a_caption_is_not_a_collision(self):
        body = ('<div class="t" style="left:100px;top:60px;font-size:300px;line-height:1;font-weight:800">20</div>'
                '<div class="t" style="left:100px;top:330px;font-size:36px">checks, at most</div>')
        self.assertNotIn("text-collision", self.ids(self.lint(body, "tight")))

    def test_text_on_an_image_gets_no_invented_contrast_ratio(self):
        from PIL import Image
        Image.new("RGB", (400, 200), (180, 60, 30)).save(self.tmp / "sheet.png")
        body = ('<img src="sheet.png" style="position:absolute;left:60px;top:60px;width:700px;height:300px">'
                '<div class="t" style="left:100px;top:120px;font-size:60px;color:#f4ecd8">Cream on an image</div>')
        self.assertNotIn("low-contrast", self.ids(self.lint(body, "onimg")))

    def test_hud_label_waived_by_declared_capability(self):
        body = '<div class="t" style="left:20px;top:18px;font-size:20px;letter-spacing:.2em">FRAME 01</div>'
        self.assertIn("hud-label", self.ids(self.lint(body, "hud1")))
        ctx = self.mq.Context(None, "landscape")
        ctx.scenes = [{"id": "s1", "start_sec": 0, "end_sec": 3, "capabilities": ["frame-hud"], "transition_out": {"type": "cut"}}]
        ctx.caps = {"s1": {"frame-hud"}}
        d = self.lint(body, "hud2", ctx)
        self.assertNotIn("hud-label", self.ids(d))
        self.assertTrue([f for f in d["findings"] if f["id"] == "hud-label" and "waived_by" in f])


# ------------------------------------------------------------------------------------------- studio.py integration
class TestStudioIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.studio = load_script("studio")
        cls.tmp = Path(tempfile.mkdtemp())
        cls.p = cls.tmp / "proj"
        shutil.copytree(ROOT / "projects" / "motion-quality-v2-directed", cls.p, ignore=shutil.ignore_patterns("renders", "qa", "audio"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def tearDown(self):
        for f in ("beatmap.json", "design-profile.json"):
            (self.p / f).unlink(missing_ok=True)

    def test_project_without_new_files_validates_as_before(self):
        rep = self.studio.validate_project(self.p)
        self.assertEqual([e for e in rep.errors if "beatmap" in e or "design-profile" in e], [])

    def test_broken_beatmap_and_profile_are_reported_by_validate(self):
        bm = {"spec_version": 1, "slug": "x", "concept": {"logline": "a long enough logline here", "viewer_change": "changes"}, "arc": {"id": "nope", "stages": ["a", "b"]},
              "beats": [{"id": "a", "stage": "zzz", "purpose": "TODO: later please", "viewer_takeaway": "what they take away", "visual_concept": "a concept that is long enough"}]}
        (self.p / "beatmap.json").write_text(json.dumps(bm))
        prof = json.loads((ROOT / "catalogue/data/design-profiles/x-ref-0bf0254a3d.json").read_text())
        prof["identity"]["mood"] = {"value": "warm", "basis": "measured"}  # measured without evidence
        (self.p / "design-profile.json").write_text(json.dumps(prof))
        rep = self.studio.validate_project(self.p)
        self.assertTrue(any("beatmap.json" in e and "TODO" in e for e in rep.errors), rep.errors)
        self.assertTrue(any("design-profile.json" in e and "evidence" in e for e in rep.errors), rep.errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
