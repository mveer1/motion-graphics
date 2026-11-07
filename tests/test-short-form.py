#!/usr/bin/env python3
"""
tests/test-short-form.py
The craft layer adopted from third-party reel and HyperFrames skills (docs/short-form-lessons.md):
hook scoring and formulas, word-timed captions, the pre-render script and story lint, and the motion
variety / tween conflict analysis. Pure Python: no browser, no ffmpeg, no TTS.

    python tests/test-short-form.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

import caption_style as cs  # noqa: E402
import captions as cap  # noqa: E402
import hooks  # noqa: E402
import scriptlint as sl  # noqa: E402
import tweens as tw  # noqa: E402

STUDIO = ROOT / "scripts" / "studio.py"


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# --------------------------------------------------------------------------- hooks
class TestHooks(unittest.TestCase):
    def test_formula_library_is_well_formed(self):
        data = json.loads((ROOT / "specs" / "hook-formulas.json").read_text())
        self.assertEqual(hooks.check_formulas(data), [])
        self.assertGreaterEqual(len(data["formulas"]), 10)

    def test_formulas_cover_every_subject_category(self):
        cats = {c["id"] for c in json.loads((ROOT / "specs" / "categories.json").read_text())["categories"]}
        covered = {c for f in hooks.load_formulas() for c in f.get("best_for", [])}
        self.assertEqual(cats - covered, set(), "a subject category has no hook formula")

    def test_greeting_is_capped_low(self):
        r = hooks.score_hook("Welcome back to the channel, today we are looking at 3 fridges in France.")
        self.assertLessEqual(r["score"], hooks.PREAMBLE_CAP)
        self.assertEqual(r["capped_by"], "greeting")

    def test_concrete_stake_and_tension_beats_vague(self):
        strong = hooks.score_hook("Nobody broke in. 700 French stores lost their food.")
        vague = hooks.score_hook("Fridges are interesting machines that keep food cold.")
        self.assertGreater(strong["score"], vague["score"] + 30)

    def test_long_hook_loses_length_points(self):
        long_hook = "On Friday night, September twenty-sixth, twenty twenty-five, a fire broke out in a government data centre in Daejeon."
        r = hooks.score_hook(long_hook)
        self.assertEqual(r["points"]["length"], 0)
        self.assertGreater(r["spoken_sec"], hooks.HOOK_WINDOW_SEC)

    def test_rank_is_sorted_and_classifies(self):
        ranked = hooks.rank(["Welcome to my video.", "Nobody broke in. The machines were told to warm up.", ""])
        self.assertEqual(len(ranked), 2)
        self.assertGreaterEqual(ranked[0]["score"], ranked[1]["score"])
        self.assertEqual(ranked[0]["formula"], "nobody-did")

    def test_figures_and_number_words_count_as_concrete(self):
        self.assertEqual(hooks.score_hook("Four degrees.")["points"]["specificity"], 15)
        self.assertEqual(hooks.score_hook("Seven hundred stores threw out $2.5 million of food.")["points"]["specificity"], 25)


# --------------------------------------------------------------------------- captions
def asr(words):
    """[(text, start, end)] -> recogniser words."""
    return [{"text": t, "start": a, "end": b} for t, a, b in words]


class TestCaptions(unittest.TestCase):
    TEXT = "Sunday night, October eleventh. Across France, fridges hummed at eighteen below."

    def timed(self):
        toks = cap.tokenize(self.TEXT)
        # the recogniser writes digits where the script has words, and mishears nothing else
        heard = asr([("Sunday", 0.2, 0.6), ("night,", 0.6, 1.0), ("October", 1.1, 1.5), ("11.", 1.5, 2.1),
                     ("Across", 2.4, 2.8), ("France,", 2.8, 3.3), ("fridges", 3.3, 3.8), ("hummed", 3.8, 4.2),
                     ("at", 4.2, 4.3), ("18", 4.3, 4.6), ("below.", 4.6, 5.0)])
        times, matched = cap.align(toks, heard, (0.0, 5.2))
        return toks, times, matched

    def test_script_spelling_wins_over_the_recogniser(self):
        toks, times, matched = self.timed()
        cues = cap.sentence_cues(toks, times)
        self.assertEqual(cues[0]["text"], "Sunday night, October eleventh.")
        self.assertIn("eighteen below.", cues[1]["text"])
        self.assertGreater(matched, 0.7)

    def test_differing_run_takes_the_recognisers_span(self):
        toks, times, _ = self.timed()
        i = [t["norm"] for t in toks].index("eleventh")
        self.assertAlmostEqual(times[i][0], 1.5, places=2)
        self.assertAlmostEqual(times[i][1], 2.1, places=2)

    def test_unheard_words_are_interpolated_in_order(self):
        toks = cap.tokenize("One two three four five.")
        heard = asr([("One", 0.0, 0.4), ("five.", 2.0, 2.4)])
        times, _ = cap.align(toks, heard, (0.0, 2.4))
        starts = [a for a, _ in times]
        self.assertEqual(starts, sorted(starts))
        self.assertTrue(0.4 <= times[1][0] and times[3][1] <= 2.0 + 1e-9)

    def test_no_recogniser_words_falls_back_to_the_scene_span(self):
        toks = cap.tokenize("Alpha beta gamma delta.")
        times, matched = cap.align(toks, [], (10.0, 14.0))
        self.assertEqual(matched, 0.0)
        self.assertAlmostEqual(times[0][0], 10.0)
        self.assertAlmostEqual(times[-1][1], 14.0)

    def test_phrases_are_short_ordered_and_never_overlap(self):
        toks, times, _ = self.timed()
        cues = cap.phrases(toks, times)
        self.assertEqual(cap.check_cues(cues), [])
        for c in cues:
            self.assertLessEqual(len(c["text"].split()), cap.MAX_WORDS)
        self.assertEqual(" ".join(c["text"] for c in cues), self.TEXT)

    def test_phrase_never_ends_on_a_weak_word(self):
        toks, times, _ = self.timed()
        for c in cap.phrases(toks, times):
            last = cap.norm(c["text"].split()[-1])
            sentence_end = c["text"].rstrip().endswith((".", "!", "?"))
            self.assertTrue(last not in cap.WEAK_ENDINGS or sentence_end, c["text"])

    def test_lone_closing_word_does_not_strand_a_weak_word(self):
        # found by captioning the fridge film end to end: "that's | a | short cycle." left "a" alone, then overlapped
        toks = cap.tokenize("Normally that's a short cycle.")
        times = [(6.11, 6.27), (6.34, 6.63), (6.75, 6.77), (6.77, 7.01), (7.39, 7.6)]
        cues = cap.phrases(toks, times)
        self.assertEqual(cap.check_cues(cues), [])
        self.assertEqual([c["text"] for c in cues], ["Normally that's", "a short cycle."])

    def test_a_cue_squeezed_by_the_next_one_never_overlaps(self):
        cues = [{"start": 1.0, "end": 1.05, "text": "a"}, {"start": 1.02, "end": 1.6, "text": "short cycle."}]
        merged = cap._resolve_overlaps(cues)
        self.assertEqual(cap.check_cues(merged), [])
        self.assertEqual(merged[0]["text"], "a short cycle.")

    def test_pause_breaks_a_phrase(self):
        toks = cap.tokenize("alpha beta gamma delta")
        times = [(0.0, 0.3), (0.3, 0.6), (1.5, 1.8), (1.8, 2.1)]
        texts = [c["text"] for c in cap.phrases(toks, times)]
        self.assertEqual(texts, ["alpha beta", "gamma delta"])

    def test_word_index_finds_a_phrase_in_film_time(self):
        scene_words = {"s1": [{"text": "Four", "start": 1.0, "end": 1.3}, {"text": "degrees,", "start": 1.3, "end": 1.9}],
                       "s2": [{"text": "four", "start": 20.0, "end": 20.2}, {"text": "degrees.", "start": 20.2, "end": 20.8}]}
        hits = cap.word_index(scene_words, "Four degrees")
        self.assertEqual([h["scene"] for h in hits], ["s1", "s2"])
        self.assertAlmostEqual(hits[1]["start"], 20.0)
        self.assertEqual(cap.word_index(scene_words, "absent phrase"), [])


# --------------------------------------------------------------------------- script and story lint
def project_fixture(root: Path, scenes, *, narration, duration=45, formats=None, extra_sb=None, brief=None, timeline=None):
    pdir = root / "p"
    write(pdir / "project.json", {"slug": "p", "duration_sec": duration, "formats": formats or [{"id": "portrait", "primary": True}]})
    write(pdir / "src" / "narration.json", {"scenes": [{"id": k, "text": v} for k, v in narration.items()]})
    write(pdir / "storyboard.json", {"scenes": scenes})
    if brief:
        write(pdir / "brief.json", brief)
    if timeline:
        write(pdir / "audio" / "timeline.json", timeline)
    return pdir


class TestScriptLint(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def report(self, narration, scenes=None, **kw):
        scenes = scenes or [{"id": k, "start_sec": i * 10, "end_sec": i * 10 + 10} for i, k in enumerate(narration)]
        return sl.script_report(project_fixture(self.tmp, scenes, narration=narration, **kw))

    def ids(self, rep):
        return {fid for _, fid, _ in rep["findings"]}

    def test_greeting_hook_is_flagged(self):
        rep = self.report({"s1": "Welcome to this video. Fridges keep food at 4 degrees."})
        self.assertIn("hook-preamble", self.ids(rep))

    def test_long_hook_sentence_is_flagged(self):
        rep = self.report({"s1": "On Friday night in late September a fire broke out in a government data centre in the city of Daejeon and spread to the batteries. It took 22 days."})
        self.assertIn("hook-long", self.ids(rep))

    def test_abstract_run_is_a_warning_for_reels_and_a_note_for_long_films(self):
        text = "Fridges hold 4 degrees. They work by moving heat. Heat goes outside the box. The coils get warm. Nobody notices."
        short = self.report({"s1": text}, duration=40)
        long_ = self.report({"s1": text}, duration=90)
        level = lambda rep: next(lv for lv, fid, _ in rep["findings"] if fid == "abstract-run")  # noqa: E731
        self.assertEqual(level(short), "warn")
        self.assertEqual(level(long_), "note")

    def test_many_asks_is_flagged(self):
        rep = self.report({"s1": "Four degrees. Seven hundred stores. Follow for more. Comment your fridge. Save this."})
        self.assertIn("many-asks", self.ids(rep))

    def test_filler_frame_is_flagged(self):
        rep = self.report({"s1": "Four degrees. In this video we look at 700 stores."})
        self.assertIn("filler-frame", self.ids(rep))

    def test_loop_is_checked_for_reel_length_films(self):
        no_echo = self.report({"s1": "Nobody broke in. Seven hundred stores lost food. The thermostats were online. Officials urged an update."}, duration=30)
        echo = self.report({"s1": "Nobody broke in. Seven hundred stores lost food. The thermostats were online. Still, nobody broke in."}, duration=30)
        self.assertIn("no-loop", self.ids(no_echo))
        self.assertNotIn("no-loop", self.ids(echo))

    def test_missing_why_is_flagged_and_present_why_passes(self):
        scenes = [{"id": "s1", "start_sec": 0, "end_sec": 10}, {"id": "s2", "start_sec": 10, "end_sec": 20}]
        rep = self.report({"s1": "Four degrees.", "s2": "Seven hundred stores."}, scenes=scenes)
        self.assertIn("why-missing", self.ids(rep))
        scenes[0]["why"] = "Lands the claim that nobody broke in"
        scenes[1]["why"] = "Evidence that hundreds of stores lost food"
        rep = self.report({"s1": "Four degrees.", "s2": "Seven hundred stores."}, scenes=scenes)
        self.assertNotIn("why-missing", self.ids(rep))

    def test_value_that_arrives_late_is_a_lead(self):
        brief = {"message": {"core_message": "Thermostats exposed to the internet can be reprogrammed remotely"}}
        narration = {"s1": "Four degrees.", "s2": "Seven hundred stores.", "s3": "Thermostats exposed to the internet can be reprogrammed remotely."}
        rep = self.report(narration, brief=brief)
        self.assertIn("value-late", self.ids(rep))

    def test_measured_clip_lengths_are_used_when_present(self):
        timeline = {"speed": 1.15, "scenes": [{"id": "s1", "start_time_sec": 0.0, "duration_sec": 6.0, "end_time_sec": 6.0}]}
        rep = self.report({"s1": "Four degrees. Seven hundred stores."}, timeline=timeline)
        self.assertIn("measured clip lengths", rep["timing_source"])
        self.assertAlmostEqual(rep["sentences"][-1]["end"], 6.0, places=1)

    def test_beat_counts_are_attached_to_sentences(self):
        scenes = [{"id": "s1", "start_sec": 0, "end_sec": 10, "beats": [{"at_sec": 1, "action": "a"}]}]
        rep = self.report({"s1": "Four degrees. Seven hundred stores threw out their food."}, scenes=scenes)
        counts = [r["beats"] for r in rep["sentences"]]
        self.assertIn(0, counts)
        self.assertIn(1, counts)

    def test_render_text_runs(self):
        rep = self.report({"s1": "Four degrees. Seven hundred stores."})
        text = sl.render_text(rep)
        self.assertIn("STORY PROPOSAL", text)
        self.assertIn("Judgment checks", text)


# --------------------------------------------------------------------------- tween analysis
def tween(t0, dur, ease="power2.out", kind="fromTo", props=None, frm=None, target=1, label="div.x", cover=False, repeat=0):
    return {"t0": t0, "dur": dur, "ease": ease, "kind": kind, "props": props or {"autoAlpha": 1, "y": 0},
            "from": frm if frm is not None else {"autoAlpha": 0, "y": 20}, "target": target, "label": label, "cover": cover,
            "stagger": None, "repeat": repeat, "yoyo": False}


SCENES = [{"id": f"s{i}", "start_sec": i * 10, "end_sec": i * 10 + 10} for i in range(4)]


class TestTweens(unittest.TestCase):
    def ids(self, tweens_, scenes=SCENES):
        return {f["id"]: f for f in tw.analyse(tweens_, scenes)}

    def test_same_property_overlap_is_a_conflict(self):
        a = tween(1.0, 1.0, target=7, props={"scale": 1}, frm={"scale": 0.5})
        b = tween(1.5, 0.5, target=7, props={"scale": 0.9}, frm={"scale": 1}, kind="fromTo")
        f = self.ids([a, b])
        self.assertIn("tween-conflict", f)
        self.assertEqual(f["tween-conflict"]["severity"], "warn")

    def test_a_brief_handoff_overlap_is_not_a_conflict(self):
        a = tween(1.0, 0.7, target=7, props={"autoAlpha": 1}, frm={"autoAlpha": 0})
        b = tween(1.65, 0.25, target=7, props={"autoAlpha": 0}, frm={"autoAlpha": 1})   # starts 0.05 s early
        self.assertNotIn("tween-conflict", self.ids([a, b]))

    def test_different_elements_or_properties_do_not_conflict(self):
        a = tween(1.0, 1.0, target=1, props={"scale": 1}, frm={"scale": 0.5})
        b = tween(1.2, 1.0, target=2, props={"scale": 1.1}, frm={"scale": 1})
        c = tween(1.2, 1.0, target=1, props={"x": 0}, frm={"x": 10})
        self.assertNotIn("tween-conflict", self.ids([a, b, c]))

    def test_sequential_tweens_on_one_element_do_not_conflict(self):
        a = tween(1.0, 0.5, target=3)
        b = tween(2.0, 0.5, target=3, props={"autoAlpha": 0}, frm={"autoAlpha": 1})
        self.assertNotIn("tween-conflict", self.ids([a, b]))

    def test_counter_and_colour_tweens_are_ignored(self):
        a = tween(1.0, 2.0, target=4, props={"__n": 10}, frm={"__n": 0}, ease="none")
        b = tween(1.5, 2.0, target=4, props={"__n": 12}, frm={"__n": 10}, ease="none")
        self.assertNotIn("tween-conflict", self.ids([a, b]))

    def test_entrance_with_ease_in_is_noted(self):
        f = self.ids([tween(1.0, 0.5, ease="power2.in", target=5)])
        self.assertIn("entrance-ease-in", f)

    def test_ease_out_exits_are_noted_when_repeated(self):
        exits = [tween(2.0 + i, 0.3, ease="power2.out", target=10 + i, props={"autoAlpha": 0}, frm={"autoAlpha": 1}) for i in range(4)]
        self.assertIn("exit-ease-out", self.ids(exits))

    def test_uniform_motion_is_flagged(self):
        # 30 entrances over four scenes: one ease, one duration, one direction
        flat = [tween(i * 1.2, 0.4, ease="power2.out", target=100 + i, frm={"autoAlpha": 0, "y": 20 + (i % 2)}) for i in range(30)]
        f = self.ids(flat)
        self.assertIn("ease-variety", f)
        self.assertIn("duration-uniformity", f)

    def test_varied_motion_passes(self):
        eases = ["power3.out", "back.out(1.7)", "expo.out", "sine.out", "power1.out", "circ.out"]
        durs = [0.2, 0.35, 0.5, 0.8, 1.2, 0.3]
        frms = [{"autoAlpha": 0, "y": 30}, {"autoAlpha": 0, "x": -40}, {"autoAlpha": 0, "scale": 0.7}, {"autoAlpha": 0},
                {"autoAlpha": 0, "x": 40}, {"autoAlpha": 0, "y": -30}]
        varied = [tween(i * 1.3, durs[i % 6], ease=eases[i % 6], target=200 + i, frm=frms[i % 6]) for i in range(30)]
        f = self.ids(varied)
        for fid in ("ease-variety", "duration-uniformity", "entrance-direction", "ease-monotony"):
            self.assertNotIn(fid, f)

    def test_scene_covers_are_transitions_not_entrances(self):
        cover = tween(9.6, 0.8, target=50, cover=True, ease="power2.in")
        self.assertIsNone(tw.role(cover))
        self.assertNotIn("entrance-ease-in", self.ids([cover]))

    def test_role_and_direction(self):
        self.assertEqual(tw.role(tween(1, 0.5)), "entrance")
        self.assertEqual(tw.role(tween(1, 0.5, props={"autoAlpha": 0}, frm={"autoAlpha": 1})), "exit")
        self.assertEqual(tw.role(tween(1, 0.5, kind="set")), None)
        self.assertEqual(tw.direction(tween(1, 0.5, frm={"autoAlpha": 0, "y": 20})), "from-below")
        self.assertEqual(tw.direction(tween(1, 0.5, frm={"autoAlpha": 0, "x": -30})), "from-left")
        self.assertEqual(tw.direction(tween(1, 0.5, frm={"autoAlpha": 0, "scale": 0.6})), "scale-up")
        self.assertEqual(tw.direction(tween(1, 0.5, frm={"autoAlpha": 0}, props={"autoAlpha": 1})), "fade")

    def test_gsap_value_parsing(self):
        self.assertEqual(tw.to_num("+=40"), 40.0)
        self.assertEqual(tw.to_num("-50%"), -50.0)
        self.assertEqual(tw.to_num("12px"), 12.0)
        self.assertIsNone(tw.to_num("fn"))
        self.assertEqual(tw.split_ease("power3.out"), ("power3", "out"))
        self.assertEqual(tw.split_ease("steps(24)"), ("steps(24)", None))


# --------------------------------------------------------------------------- caption design
class TestCaptionDesign(unittest.TestCase):
    """specs/caption-presets.json, src/pipeline/caption_style.py and the CSS in studio-base.css must agree."""

    @classmethod
    def setUpClass(cls):
        cls.spec = cs.load_spec()
        cls.css = (ROOT / "src" / "studio" / "studio-base.css").read_text(encoding="utf-8")
        cls.presets = json.loads((ROOT / "specs" / "format-presets.json").read_text())["formats"]

    def test_every_style_system_has_a_preset(self):
        styles = {p.stem for p in (ROOT / "src" / "studio" / "styles").glob("*.css")}
        self.assertEqual(styles - set(self.spec["style_map"]), set(), "a style system has no caption preset")
        self.assertEqual(set(self.spec["style_map"]) - styles, set(), "style_map names a style that does not exist")
        for style, pid in self.spec["style_map"].items():
            self.assertIn(pid, self.spec["presets"], style)
        self.assertIn(self.spec["fallback_preset"], self.spec["presets"])

    def test_fonts_are_bundled_with_hyperframes(self):
        src = (ROOT / "scripts" / "studio.py").read_text(encoding="utf-8")
        bundled = {f.lower() for f in __import__("re").findall(r'"([a-z ]+)"', src.split("HF_BUNDLED_FONTS = {", 1)[1].split("}", 1)[0])}
        for pid, pr in self.spec["presets"].items():
            self.assertIn(pr["font"]["family"].lower(), bundled, f"{pid}: font is not bundled")

    def test_css_carries_every_preset_size_and_font(self):
        import re
        for pid, pr in self.spec["presets"].items():
            for fmt, size in pr["size_u"].items():
                prefix = "" if fmt == "landscape" else f'#root\\[data-format="{fmt}"\\] '
                m = re.search(prefix + r'\.st-captions\[data-cap-preset="' + pid + r'"\]\s*\{[^}]*--cap-size:\s*([0-9.]+)', self.css)
                self.assertIsNotNone(m, f"{pid} {fmt}: no --cap-size rule in studio-base.css")
                self.assertAlmostEqual(float(m.group(1)), size, msg=f"{pid} {fmt} size drifted from the spec")
            f = pr["font"]
            self.assertRegex(self.css, r'data-cap-preset="' + pid + r'"\] \.st-caption \{[^}]*font-family: \'' + re.escape(f["family"]) + r"'", f"{pid}: font family not written literally")
            self.assertRegex(self.css, r'data-cap-preset="' + pid + r'"\] \.st-caption \{[^}]*font-weight: ' + str(f["weight"]), f"{pid}: weight drifted")

    def test_css_lanes_match_the_spec_and_the_safe_areas(self):
        lanes = self.spec["lanes"]
        # the lower lane is the format's safe-area bottom, so it must equal what format-presets.json says
        for fmt in ("portrait", "landscape", "square"):
            self.assertAlmostEqual(lanes[fmt]["lower"]["bottom_edge"], 1 - self.presets[fmt]["safe_area"]["bottom"], places=3, msg=fmt)
        self.assertIn('.st-caption[data-lane="lower"] { top: auto; bottom: var(--safe-bottom); }', self.css)
        self.assertIn(f'bottom: calc(var(--h) * {1 - lanes["portrait"]["mid"]["bottom_edge"]:.2f})', self.css)
        self.assertIn(f'.st-caption[data-lane="upper"] {{ top: calc(var(--h) * {lanes["portrait"]["upper"]["top_edge"]:.2f}); bottom: auto; }}', self.css)
        self.assertIn(f'[data-format="landscape"] .st-caption[data-lane="upper"] {{ top: calc(var(--h) * {lanes["landscape"]["upper"]["top_edge"]:.2f}); }}', self.css)
        self.assertIn(f'[data-format="square"] .st-caption[data-lane="upper"] {{ top: calc(var(--h) * {lanes["square"]["upper"]["top_edge"]:.2f}); }}', self.css)
        self.assertNotIn("mid", lanes["landscape"])

    def test_lanes_stay_in_the_platform_reference(self):
        ref = self.presets["portrait"]["platform_ui_reference"]
        lanes = self.spec["lanes"]["portrait"]
        self.assertLessEqual(lanes["lower"]["bottom_edge"], 1 - ref["bottom"] + 1e-9)
        self.assertLessEqual(lanes["mid"]["bottom_edge"], lanes["lower"]["bottom_edge"])
        self.assertGreaterEqual(lanes["upper"]["top_edge"], ref["top"])

    def test_resolve_picks_by_style_and_pin(self):
        self.assertEqual(cs.resolve("archival", "portrait")["id"], "serif-quiet")
        self.assertEqual(cs.resolve("dark-tech", "portrait")["id"], "mono-type")
        self.assertEqual(cs.resolve("not-a-style", "portrait")["id"], self.spec["fallback_preset"])
        self.assertEqual(cs.resolve("archival", "portrait", "bold-pop")["id"], "bold-pop")
        with self.assertRaises(ValueError):
            cs.resolve("archival", "portrait", "nope")

    def test_hook_sits_mid_in_portrait_and_lower_elsewhere(self):
        self.assertEqual(cs.resolve("editorial-light", "portrait")["roles"]["hook"], {"lane": "mid", "scale": 1.15})
        for fmt in ("landscape", "square"):
            self.assertEqual(cs.resolve("editorial-light", fmt)["roles"]["hook"]["lane"], "lower")
        self.assertEqual(cs.resolve("editorial-light", "portrait")["roles"]["body"]["lane"], "lower")

    def test_video_type_from_brief_then_length(self):
        self.assertEqual(cs.video_type_of({"deliverables": {"video_type": "long-reel"}}, 30, "portrait"), "long-reel")
        self.assertEqual(cs.video_type_of(None, 45, "portrait"), "reel")
        self.assertEqual(cs.video_type_of(None, 120, "portrait"), "long-reel")
        self.assertEqual(cs.video_type_of(None, 240, "landscape"), "youtube")
        self.assertEqual(cs.type_defaults("youtube")["grouping"], "sentence")
        self.assertEqual(cs.type_defaults("reel")["grouping"], "phrase")

    def cues(self):
        mk = lambda t, a, b, ws: {"start": a, "end": b, "text": t, "words": [{"text": w, "start": a, "end": b} for w in ws]}  # noqa: E731
        return [mk("It was 1947", 0.3, 1.2, ["It", "was", "1947"]), mk("then it fell", 1.3, 2.4, ["then", "it", "fell"]),
                mk("Prices rose 12%", 3.5, 4.6, ["Prices", "rose", "12%"]), mk("That is all", 9.0, 9.8, ["That", "is", "all"])]

    def test_annotate_roles_lanes_and_emphasis(self):
        cues = cs.annotate(self.cues(), fmt="portrait", scene_spans=[{"start": 0, "end": 5}, {"start": 8, "end": 10}],
                           storyboard_scenes=[{"id": "s1", "start_sec": 0, "end_sec": 5}, {"id": "s2", "start_sec": 8, "end_sec": 10, "caption_lane": "upper"}])
        self.assertEqual([c["role"] for c in cues], ["hook", "hook", "body", "outro"])
        self.assertNotIn("lane", cues[0])
        self.assertEqual(cues[3]["lane"], "upper", "a storyboard scene's caption_lane overrides the role's lane")
        self.assertEqual([w.get("em") for w in cues[0]["words"]], [None, None, True])
        self.assertTrue(cues[2]["words"][2].get("em"))
        self.assertFalse(any(w.get("em") for w in cues[3]["words"]), "only numbers are emphasised")

    def test_mid_lane_falls_back_to_lower_outside_portrait(self):
        cues = cs.annotate(self.cues(), fmt="landscape", scene_spans=[{"start": 0, "end": 10}],
                           storyboard_scenes=[{"id": "s1", "start_sec": 0, "end_sec": 10, "caption_lane": "mid"}])
        self.assertEqual({c["lane"] for c in cues}, {"lower"})

    def test_lint_flags_long_cues_and_lane_sprawl(self):
        long = [{"start": 0.4, "end": 5.0, "text": "x" * 60, "role": "hook"}]
        self.assertTrue(any("60" in w or "over 44" in w for w in cs.lint_cues(long, "portrait")))
        self.assertEqual(cs.lint_cues(long, "landscape"), [])
        three = [{"start": 0.4, "end": 1, "text": "a", "role": "hook"}, {"start": 4, "end": 5, "text": "b", "role": "body"},
                 {"start": 6, "end": 7, "text": "c", "role": "body", "lane": "upper"}]
        self.assertTrue(any("3 lanes" in w for w in cs.lint_cues(three, "portrait")))
        late = [{"start": 2.0, "end": 3, "text": "a", "role": "hook"}]
        self.assertTrue(any("hook runs without one" in w for w in cs.lint_cues(late, "portrait")))
        self.assertEqual(cs.lint_cues(cs.annotate(self.cues(), fmt="portrait", scene_spans=[{"start": 0, "end": 10}]), "portrait"), [])

    def test_schemas_accept_the_new_fields(self):
        sb = json.loads((ROOT / "specs" / "storyboard-spec.json").read_text())
        self.assertEqual(sb["definitions"]["scene"]["properties"]["caption_lane"]["enum"], ["lower", "mid", "upper"])
        vs = json.loads((ROOT / "specs" / "video-spec.json").read_text())
        self.assertIn("caption_preset", vs["properties"]["audio"]["properties"])


# --------------------------------------------------------------------------- wiring
class TestWiring(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(STUDIO), *args], capture_output=True, text=True, cwd=ROOT)

    def test_hook_score_cli(self):
        out = self.run_cli("hook", "score", "Welcome to my channel.", "Nobody broke in. 700 stores lost their food.")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("a lint, not a prediction", out.stdout.lower())
        self.assertLess(out.stdout.index("Nobody broke in"), out.stdout.index("Welcome to my channel"))

    def test_hook_formulas_cli(self):
        out = self.run_cli("hook", "formulas", "--category", "finance")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("human-scale", out.stdout)

    def test_captions_phrase_grouping_needs_measured_timing(self):
        out = self.run_cli("captions", "fridge-hack-europe", "--grouping", "phrase")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--timing words", out.stdout + out.stderr)

    def test_script_cli_on_a_real_project(self):
        slug = "fridge-hack-europe"
        if not (ROOT / "projects" / slug / "src" / "narration.json").exists():
            self.skipTest("fridge-hack-europe is not in this checkout")
        out = self.run_cli("script", slug, "--json")
        self.assertEqual(out.returncode, 0, out.stderr)
        rep = json.loads(out.stdout)
        self.assertTrue(rep["sentences"])
        self.assertIn("findings", rep)

    def test_portrait_safe_area_adopts_only_the_reference_bottom(self):
        presets = json.loads((ROOT / "specs" / "format-presets.json").read_text())
        ref = presets["formats"]["portrait"]["platform_ui_reference"]
        self.assertFalse(ref["certified"])
        safe = presets["formats"]["portrait"]["safe_area"]
        # the bottom margin follows the reel-interface reference; top and right, where the sources disagree, do not
        self.assertEqual(safe["bottom"], ref["bottom"])
        self.assertLess(safe["top"], ref["top"])
        self.assertLess(safe["right"], ref["right"])
        core = (ROOT / "src" / "studio" / "studio-core.js").read_text()
        self.assertIn(f"bottom: {safe['bottom']}", core.split("portrait:", 1)[1].split("}", 1)[0],
                      "studio-core.js SAFE_DEFAULTS must mirror the portrait preset")

    def test_new_arc_is_registered(self):
        arcs = {a["id"]: a for a in json.loads((ROOT / "specs" / "narrative-arcs.json").read_text())["arcs"]}
        self.assertEqual([s["id"] for s in arcs["reel-loop"]["stages"]], ["hook", "stake", "body", "payoff", "loop"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
