import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from runtime.a2ui import CATALOG, result_messages
from server import Jobs, validate_document


class WebServiceTests(unittest.TestCase):
    def test_a2ui_envelopes_and_download_action(self):
        messages = result_messages({"status": "needs_review", "execution_mode": "demo"}, "job")
        self.assertTrue(all(message["version"] == "v0.9" for message in messages))
        self.assertEqual(messages[0]["createSurface"]["catalogId"], CATALOG)
        components = messages[-1]["updateComponents"]["components"]
        self.assertIn("root", [component["id"] for component in components])
        self.assertEqual(next(component for component in components if component["id"] == "download")["action"]["event"]["name"], "download_result")

    def test_upload_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pdf"
            path.write_bytes(b"not pdf")
            with self.assertRaises(ValueError):
                validate_document(path, ".pdf")
            path.write_bytes(b"%PDF-1.7 fixture")
            validate_document(path, ".pdf")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("random.txt", "not a workbook")
            with self.assertRaises(ValueError):
                validate_document(path, ".xlsx")

    def test_queue_limit_and_restart_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs = Jobs(directory, "test-token", capacity=1)
            try:
                with patch.object(jobs.executor, "submit"):
                    task = jobs.submit("report.pdf", b"%PDF-1.7 fixture", True)
                    with self.assertRaises(OverflowError):
                        jobs.submit("another.pdf", b"%PDF-1.7", True)
                restarted = Jobs(directory, "test-token")
                try:
                    self.assertEqual(restarted.items[task["id"]]["status"], "interrupted")
                finally:
                    restarted.executor.shutdown()
            finally:
                jobs.executor.shutdown()
