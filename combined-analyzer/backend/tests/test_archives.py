"""Archive boundary regressions; run with isolated backend configuration."""

import asyncio
import io
import stat
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, UploadFile
from services import folder_service
from services.folder_service import extract_zip_safely, flatten_single_root_directory


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = self.root / "input.zip"
        self.destination = self.root / "repo"
        self.destination.mkdir()

    def make_archive(self, entries):
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries:
                archive.writestr(name, content)

    def test_regular_nested_root_with_same_name(self):
        self.make_archive([("project/project/code.py", b"print('real')")])
        extract_zip_safely(self.archive, self.destination)
        flatten_single_root_directory(self.destination)
        self.assertEqual((self.destination / "project/code.py").read_bytes(), b"print('real')")

    def test_windows_and_posix_escape_paths(self):
        for name in ("/root.txt", "\\root.txt", "C:/root.txt", "C:root.txt", "C:\\root.txt", "\\\\host\\share\\file", "../escape.txt", "x\\..\\escape.txt", ".. /escape.txt", "x/file:stream", "NUL.txt"):
            with self.subTest(name=name):
                self.make_archive([(name, b"bad")])
                with self.assertRaises(HTTPException):
                    extract_zip_safely(self.archive, self.destination)
                self.assertEqual(list(self.destination.iterdir()), [])

    def test_symlink_member_rejected(self):
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_archive([(info, b"../outside")])
        with self.assertRaises(HTTPException):
            extract_zip_safely(self.archive, self.destination)

    def test_file_and_total_expansion_bounds(self):
        self.make_archive([("a.txt", b"a" * 2048), ("b.txt", b"b" * 2048)])
        for limits in ({"MAX_FILE_SIZE": 1024}, {"MAX_EXPANDED_SIZE": 3000}, {"MAX_ARCHIVE_FILES": 1}, {"MAX_UPLOAD_SIZE": 1}):
            with self.subTest(limits=limits), patch.multiple(folder_service, **limits):
                with self.assertRaises(HTTPException):
                    extract_zip_safely(self.archive, self.destination)
                for file in self.destination.iterdir():
                    file.unlink()

    def test_rejected_upload_removes_partial_files(self):
        self.make_archive([("valid.txt", b"ok"), ("../escape.txt", b"bad")])
        upload = UploadFile(filename="input.zip", file=io.BytesIO(self.archive.read_bytes()))
        db = AsyncMock()
        with patch.object(folder_service, "REPOS_DIR", self.destination), patch.object(folder_service, "require_registered_user", AsyncMock(return_value="owner")):
            with self.assertRaises(HTTPException):
                asyncio.run(folder_service.save_and_extract_zip(upload, db, owner_user_id="owner"))
        self.assertEqual(list(self.destination.iterdir()), [])
        db.commit.assert_not_called()
        db.flush.assert_not_called()

    def test_cancelled_upload_waits_for_extraction_before_cleanup(self):
        self.make_archive([("code.py", b"print('complete')")])
        upload = UploadFile(filename="input.zip", file=io.BytesIO(self.archive.read_bytes()))
        release = threading.Event()

        async def scenario():
            started = asyncio.Event()
            finished = asyncio.Event()
            loop = asyncio.get_running_loop()

            def delayed_extraction(archive_path, destination):
                with zipfile.ZipFile(archive_path) as archive:
                    content = archive.read("code.py")
                loop.call_soon_threadsafe(started.set)
                try:
                    if not release.wait(5):
                        raise TimeoutError("Extraction was not released")
                    destination.mkdir(parents=True, exist_ok=True)
                    (destination / "code.py").write_bytes(content)
                finally:
                    loop.call_soon_threadsafe(finished.set)

            with patch.object(folder_service, "REPOS_DIR", self.destination), patch.object(folder_service, "require_registered_user", AsyncMock(return_value="owner")), patch.object(folder_service, "extract_zip_safely", delayed_extraction):
                task = asyncio.create_task(folder_service.save_and_extract_zip(upload, AsyncMock(), owner_user_id="owner"))
                try:
                    await asyncio.wait_for(started.wait(), 5)
                    task.cancel()
                    await asyncio.sleep(0)
                    release.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                    await asyncio.wait_for(finished.wait(), 5)
                    self.assertEqual(list(self.destination.iterdir()), [])
                finally:
                    release.set()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
