import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_release_assets as checker


class ReleaseAssetChecks(unittest.TestCase):
    def setUp(self):
        self.base = "https://github.com/TitanCSA/Example"
        self.hash = "a" * 64
        self.role = "sdk"
        self.tag = "v1.0.0.0-demo"
        self.version = "1.0.0.0"
        self.name = "Example-SDK-1.0.0.0.zip"
        self.edition = {
            "slug": "example",
            "repository": self.base,
            "tag": self.tag,
            "demo": self.version,
            "demo_files": {self.role: self.name},
            "demo_assets": {self.role: f"{self.base}/releases/download/{self.tag}/{self.name}"},
            "sdk_sha256": self.hash,
        }

    def public_release(self, tag, filename, digest=None):
        return {
            "draft": False,
            "tag_name": tag,
            "assets": [{
                "name": filename,
                "state": "uploaded",
                "size": 100,
                "browser_download_url": f"{self.base}/releases/download/{tag}/{filename}",
                "digest": "sha256:" + (digest or self.hash),
            }],
        }

    def test_requires_the_exact_published_sdk_digest(self):
        with patch.object(checker, "fetch_release", return_value=self.public_release(self.tag, self.name)):
            self.assertEqual(checker.check_edition(self.edition, self.role), 1)
        different = self.public_release(self.tag, self.name, "b" * 64)
        with patch.object(checker, "fetch_release", return_value=different):
            with self.assertRaisesRegex(ValueError, "pinned SDK SHA-256"):
                checker.check_edition(self.edition, self.role)

    def test_candidate_supplies_replacement_without_mutating_the_current_edition(self):
        tag = "v1.0.1.0-demo"
        filename = "Native-SDK.zip"
        release = self.public_release(tag, filename)
        with patch.object(checker, "fetch_release", return_value=release):
            row = checker.candidate(self.edition, tag, "1.0.1.0", self.role, [f"sdk={filename}"])
        self.assertEqual(row["tag"], tag)
        self.assertEqual(row["sdk_sha256"], self.hash)
        self.assertEqual(row["demo_files"]["sdk"], filename)
        self.assertEqual(self.edition["tag"], self.tag)
        self.assertEqual(self.edition["demo_files"]["sdk"], self.name)

    def test_candidate_rejects_an_unknown_or_non_file_asset(self):
        for override in ("new=sample.zip", "sdk=../sample.zip"):
            with self.subTest(override=override), patch.object(checker, "fetch_release") as fetch:
                with self.assertRaisesRegex(ValueError, "existing role and a filename"):
                    checker.candidate(self.edition, self.tag, self.version, self.role, [override])
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
