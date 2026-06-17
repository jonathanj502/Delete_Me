import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.state import (
    load_state,
    save_state,
    clear_state,
    is_completed,
    is_interrupted,
    mark_complete,
)


class TestLoadState(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_state(Path(tmp) / "missing.json"), {})

    def test_null_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("null", encoding="utf-8")
            self.assertEqual(load_state(path), {})

    def test_corrupt_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("not json {{{", encoding="utf-8")
            self.assertEqual(load_state(path), {})

    def test_valid_state_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text('{"last_scan_completed_at": "2026-06-16T18:00:00+00:00"}', encoding="utf-8")
            self.assertEqual(load_state(path)["last_scan_completed_at"], "2026-06-16T18:00:00+00:00")


class TestSaveState(unittest.TestCase):
    def test_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "output" / ".scan_state.json"
            save_state({"x": 1}, path)
            self.assertEqual(json.loads(path.read_text())["x"], 1)

    def test_no_tmp_file_left_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            save_state({}, path)
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            save_state({"a": 1}, path)
            save_state({"b": 2}, path)
            loaded = json.loads(path.read_text())
            self.assertNotIn("a", loaded)
            self.assertEqual(loaded["b"], 2)


class TestClearState(unittest.TestCase):
    def test_removes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{}", encoding="utf-8")
            clear_state(path)
            self.assertFalse(path.exists())

    def test_no_error_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            clear_state(Path(tmp) / "missing.json")  # must not raise


class TestIsCompleted(unittest.TestCase):
    def test_true_when_timestamp_present(self):
        self.assertTrue(is_completed({"last_scan_completed_at": "2026-06-16T00:00:00+00:00"}))

    def test_false_when_empty(self):
        self.assertFalse(is_completed({}))

    def test_false_when_key_absent(self):
        self.assertFalse(is_completed({"other": "value"}))


class TestIsInterrupted(unittest.TestCase):
    def test_true_when_state_has_no_completed_key(self):
        self.assertTrue(is_interrupted({"other": "value"}))

    def test_false_when_empty(self):
        self.assertFalse(is_interrupted({}))

    def test_false_when_completed(self):
        self.assertFalse(is_interrupted({"last_scan_completed_at": "2026-06-16T00:00:00+00:00"}))


class TestMarkComplete(unittest.TestCase):
    def test_adds_timestamp(self):
        result = mark_complete({})
        self.assertIn("last_scan_completed_at", result)

    def test_timestamp_is_parseable_iso8601(self):
        ts = mark_complete({})["last_scan_completed_at"]
        datetime.fromisoformat(ts)  # must not raise

    def test_preserves_other_fields(self):
        result = mark_complete({"x": 42})
        self.assertEqual(result["x"], 42)

    def test_does_not_mutate_input(self):
        original = {"x": 1}
        mark_complete(original)
        self.assertNotIn("last_scan_completed_at", original)
