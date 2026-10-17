"""Exercise safety gates without connecting to Lightroom or touching real photos."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from initialize_photo_grade_workspace import initialize
from add_photo_grade_taste import append_taste
from validate_photo_grade_proposal import validate


def proposal(key="Exposure2012", old=0, new=0.5, source_type="raw"):
    return {"photos": [{"photo_id": "1", "source_type": source_type,
                        "baseline_develop": {key: old}, "proposed_settings": {key: new}}]}


class ProposalTests(unittest.TestCase):
    def test_valid_settings_and_temperature_scales(self):
        for value in [proposal(), proposal("HueAdjustmentOrange", 0, 35),
                      proposal("WhiteBalance", "As Shot", "Custom"),
                      proposal("Temperature", 5500, 8000),
                      proposal("Temperature", 0, 35),
                      proposal("Temperature", 0, 20, "jpeg")]:
            with self.subTest(value=value):
                self.assertEqual(validate(value), [])

    def test_rejects_unsafe_or_malformed_proposals(self):
        values = [None, [], {"photos": {}}, {"photos": [None]},
                  proposal("CropTop", 0, 0.1), proposal(new=1.26),
                  proposal(new=True), proposal(new=float("nan")),
                  proposal(new=float("inf")), proposal(new="0.5"),
                  proposal("Temperature", 0, 21, "jpeg"),
                  proposal("Temperature", 5500, 8001),
                  proposal("WhiteBalance", None, "Custom"),
                  proposal("WhiteBalance", "Custom", "Daylight"),
                  {"photos": [proposal()["photos"][0]] * 101}]
        missing = proposal()
        missing["photos"][0]["baseline_develop"] = {}
        empty = proposal()
        empty["photos"][0]["proposed_settings"] = {}
        duplicate = proposal()
        duplicate["photos"].append(copy.deepcopy(duplicate["photos"][0]))
        values.extend([missing, empty, duplicate])
        for value in values:
            with self.subTest(value=value):
                self.assertTrue(validate(value))

    def test_legacy_hsl_requires_numeric_baselines(self):
        self.assertEqual(validate(proposal("HSL", {"Hue": {"Red": 0}}, {"Hue": {"Red": 20}})), [])
        for old, new in [(None, {}), ({"Hue": {}}, {"Hue": {"Red": 1}}),
                         ({"Hue": {"Red": 0}}, {"Hue": {"Red": 36}}),
                         ({}, {"Other": {"Red": 0}}), ({}, [])]:
            self.assertTrue(validate(proposal("HSL", old, new)))

    def test_cli_exit_codes_and_bom(self):
        script = Path(__file__).resolve().parents[1] / "scripts/validate_photo_grade_proposal.py"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "方案 test.json"
            for value, expected in [(proposal(), 0), (proposal(new=99), 1)]:
                path.write_text(json.dumps(value), encoding="utf-8-sig")
                result = subprocess.run([sys.executable, str(script), "--path", str(path)], capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)
            path.write_text("{", encoding="utf-8")
            self.assertNotEqual(subprocess.run([sys.executable, str(script), "--path", str(path)], capture_output=True).returncode, 0)


class StateTests(unittest.TestCase):
    def test_session_preserves_active_and_completed_rollback(self):
        with tempfile.TemporaryDirectory(prefix="调色 space ") as tmp:
            current = initialize(Path(tmp))
            manifest = current / "manifest.json"
            preview = current / "before" / "原片.jpg"
            preview.write_bytes(b"baseline")
            for status in ["planned", "pilot_applied", "pilot_approved", "batch_applied", "unknown"]:
                data = json.loads(manifest.read_text())
                data["status"] = status
                manifest.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    initialize(Path(tmp), replace_finished=True)
                self.assertEqual(preview.read_bytes(), b"baseline")
            data["status"] = "completed"
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                initialize(Path(tmp))
            initialize(Path(tmp), replace_finished=True)
            archives = list(current.parent.glob("previous-*"))
            self.assertEqual(len(archives), 1)
            self.assertEqual((archives[0] / "before/原片.jpg").read_bytes(), b"baseline")
            self.assertEqual(json.loads(manifest.read_text())["status"], "planned")

    def test_symlink_cannot_redirect_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            outside = Path(tmp) / "outside"
            workspace.mkdir()
            outside.mkdir()
            (workspace / ".photo-grade").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                initialize(workspace)
            self.assertEqual(list(outside.iterdir()), [])

    def test_taste_is_utf8_idempotent_and_confined(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, "home", return_value=Path(tmp)):
            append_taste("portrait.md", " 自然肤色\n避免过饱和 ")
            target = Path(tmp) / ".photo-grade/tastes/portrait.md"
            before = target.read_text()
            self.assertIn("自然肤色 避免过饱和", before)
            append_taste("portrait.md", "自然肤色 避免过饱和")
            self.assertEqual(target.read_text(), before)
            for filename, entry in [("../escape.md", "x"), ("portrait.md", "\n ")]:
                with self.assertRaises(ValueError):
                    append_taste(filename, entry)
            outside = Path(tmp) / "outside.md"
            outside.write_text("keep")
            (target.parent / "linked.md").symlink_to(outside)
            with self.assertRaises(ValueError):
                append_taste("linked.md", "x")
            self.assertEqual(outside.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
