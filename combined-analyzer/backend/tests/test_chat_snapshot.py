"""Deterministic input-context regressions; no provider calls."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from services.chat_service import snapshot_files, _build_code_context, encode_image_to_base64
from routers.chat import event_generator


class ChatSnapshotTests(unittest.TestCase):
    def test_legacy_analysis_requires_new_run(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "no saved input snapshot"):
                snapshot_files(SimpleNamespace(selected_files=None), root)

    def test_every_snapshotted_source_is_included_without_truncation(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = []
            for index in range(32):
                name = f"source{index}.txt"
                Path(root, name).write_text("x" * 3100 + f"END{index}", encoding="utf-8")
                snapshot.append({"file_path": name, "file_type": "code"})
            files = snapshot_files(SimpleNamespace(selected_files=snapshot), root)
            context = _build_code_context(files, root)
            for index in range(32):
                self.assertIn(f"END{index}", context)

    def test_missing_source_and_escaping_path_fail(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ("missing.py", "../outside.py"):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unavailable"):
                    snapshot_files(SimpleNamespace(selected_files=[{"file_path": name, "file_type": "code"}]), root)

    def test_unsupported_images_are_not_mislabeled_png(self):
        for suffix in (".svg", ".bmp"):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, "Unsupported image format"):
                encode_image_to_base64("diagram" + suffix)


class ChatStreamErrors(unittest.IsolatedAsyncioTestCase):
    async def test_errors_are_structured_not_assistant_text(self):
        async def failed_stream(*args, **kwargs):
            raise ValueError("No saved input snapshot")
            yield  # Marks this fixture as an async generator.

        events = [
            event async for event in event_generator(
                failed_stream, 1, "question", [], None
            )
        ]
        self.assertEqual(events[0], 'data: {"error": "No saved input snapshot"}\n\n')
        self.assertEqual(events[1], "data: [DONE]\n\n")
