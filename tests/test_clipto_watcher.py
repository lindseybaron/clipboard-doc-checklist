import json
import tempfile
import unittest
from pathlib import Path

from tools.clipto_watcher import load_config, parse_clipboard_text


class ParseClipboardTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tag_map = {
            "todo": "TODO",
            "next": "Next Actions",
            "idea": "Ideas",
            "misc": "Miscellany",
        }

    def test_parses_first_non_empty_tagged_line(self) -> None:
        payload = parse_clipboard_text("\n\nTODO: ship release\nnext: ignore", "map_to_misc", self.tag_map)
        self.assertEqual(
            payload,
            {
                "type": "todo",
                "section": "TODO",
                "text": "ship release",
            },
        )

    def test_returns_none_for_untagged_text(self) -> None:
        self.assertIsNone(parse_clipboard_text("just a sentence", "map_to_misc", self.tag_map))

    def test_unknown_tag_maps_to_misc_when_enabled(self) -> None:
        payload = parse_clipboard_text("rand: note", "map_to_misc", self.tag_map)
        self.assertEqual(payload and payload["type"], "misc")
        self.assertEqual(payload and payload["section"], "Miscellany")

    def test_unknown_tag_ignored_when_configured(self) -> None:
        self.assertIsNone(parse_clipboard_text("rand: note", "ignore", self.tag_map))


class LoadConfigTests(unittest.TestCase):
    def write_config(self, config: dict) -> Path:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        path = Path(tmp_dir.name) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_load_config_applies_defaults(self) -> None:
        config_path = self.write_config({"web_app_url": "https://script.google.com/macros/s/x/exec"})
        loaded = load_config(config_path)
        self.assertEqual(loaded["who"], "ME")
        self.assertEqual(loaded["unknown_prefix_behavior"], "map_to_misc")
        self.assertIn("todo", loaded["tag_map"])

    def test_load_config_requires_web_app_url(self) -> None:
        config_path = self.write_config({})
        with self.assertRaises(ValueError):
            load_config(config_path)


if __name__ == "__main__":
    unittest.main()
