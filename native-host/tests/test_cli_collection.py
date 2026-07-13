import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zotero_script_trigger_cli import build_request, create_parser


class CollectionTargetCliTests(unittest.TestCase):
    def test_build_request_adds_collection_fields_to_save_action(self):
        request = build_request(
            "save-url",
            url="https://example.org/paper",
            collection_path="自动文献收集/第一轮广义收集",
            library_target="L1",
            request_id="req-1",
        )
        self.assertEqual(request["collectionPath"], "自动文献收集/第一轮广义收集")
        self.assertEqual(request["libraryTarget"], "L1")

    def test_parser_accepts_collection_options_after_save_command(self):
        args = create_parser().parse_args([
            "save-url",
            "--url", "https://example.org/paper",
            "--collection", "自动文献收集/第一轮广义收集",
            "--library-target", "L1",
        ])
        self.assertEqual(args.collection_path, "自动文献收集/第一轮广义收集")
        self.assertEqual(args.library_target, "L1")

    def test_collection_path_is_rejected_for_non_save_action(self):
        with self.assertRaises(SystemExit):
            create_parser().parse_args(["ping", "--collection", "A/B"])


if __name__ == "__main__":
    unittest.main()
