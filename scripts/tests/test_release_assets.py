import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
            "demo_asset_sha256": {self.role: self.hash},
            "first_run_guides": {
                "en": "https://titancsa.github.io/guides/example/",
                "fr": "https://titancsa.github.io/fr/exemple/",
            },
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
            with self.assertRaisesRegex(ValueError, "pinned SHA-256 differs for Example-SDK"):
                checker.check_edition(self.edition, self.role)

    def test_public_contact_audit_checks_the_published_body(self):
        release = self.public_release(self.tag, self.name)
        with patch.object(checker, "fetch_release", return_value=release):
            with self.assertRaisesRegex(ValueError, "missing the Discord contact"):
                checker.check_edition(self.edition, self.role, check_contact=True)
            release["body"] = "Contact TitanCSA on Discord for the full version."
            en, fr = (self.edition["first_run_guides"][lang] for lang in ("en", "fr"))
            release["body"] += f"\n[Guide]({en})\n[French guide]({fr}old/)"
            with self.assertRaisesRegex(ValueError, "missing first-run guides for fr"):
                checker.check_edition(self.edition, self.role, check_contact=True)
            release["body"] = release["body"].replace(f"{fr}old/", fr)
            self.assertEqual(checker.check_edition(self.edition, self.role, check_contact=True), 1)
            release["body"] += " Payment: https://checkout.stripe.com/example"
            with self.assertRaisesRegex(ValueError, "contain a checkout link"):
                checker.check_edition(self.edition, self.role, check_contact=True)

    def test_candidate_supplies_replacement_without_mutating_the_current_edition(self):
        tag = "v1.0.1.0-demo"
        filename = "Native-SDK.zip"
        release = self.public_release(tag, filename)
        with patch.object(checker, "fetch_release", return_value=release):
            row = checker.candidate(self.edition, tag, "1.0.1.0", self.role, [f"sdk={filename}"])
        self.assertEqual(row["tag"], tag)
        self.assertEqual(row["sdk_sha256"], self.hash)
        self.assertEqual(row["demo_asset_sha256"], {self.role: self.hash})
        self.assertEqual(row["demo_files"]["sdk"], filename)
        self.assertEqual(self.edition["tag"], self.tag)
        self.assertEqual(self.edition["demo_files"]["sdk"], self.name)

    def test_installer_digest_is_checked_even_when_the_sdk_is_unchanged(self):
        setup_name = "ExampleSetup.exe"
        changed_setup = self.public_release(self.tag, setup_name, "b" * 64)["assets"][0]
        release = self.public_release(self.tag, self.name)
        release["assets"].append(changed_setup)
        self.edition["demo_files"]["installer"] = setup_name
        self.edition["demo_assets"]["installer"] = changed_setup["browser_download_url"]
        self.edition["demo_asset_sha256"]["installer"] = self.hash
        with patch.object(checker, "fetch_release", return_value=release):
            with self.assertRaisesRegex(ValueError, "pinned SHA-256 differs for ExampleSetup"):
                checker.check_edition(self.edition, self.role)

    def test_candidate_rejects_an_unknown_or_non_file_asset(self):
        for override in ("new=sample.zip", "sdk=../sample.zip"):
            with self.subTest(override=override), patch.object(checker, "fetch_release") as fetch:
                with self.assertRaisesRegex(ValueError, "existing role and a filename"):
                    checker.candidate(self.edition, self.tag, self.version, self.role, [override])
                fetch.assert_not_called()

    def test_apply_updates_one_pin_and_refuses_a_stale_build(self):
        row = {"slug": "example", "tag": self.tag, "demo": self.version, "note": "Preserve this"}
        other = {"slug": "other", "tag": "v9.0.0"}
        source = {"reviewed": "2026-11-24", "editions": [row, other]}
        reviewed = {"slug": "example", "tag": "v1.0.1.0-demo", "demo": "1.0.1.0"}
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "releases.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            self.assertFalse(checker.update_pin(path, row, row))
            self.assertTrue(checker.update_pin(path, row, reviewed))
            saved = path.read_bytes()
            updated = json.loads(saved)
            self.assertEqual(updated["editions"], [{**row, **reviewed}, other])
            with self.assertRaisesRegex(ValueError, "source changed"):
                checker.update_pin(path, row, reviewed)
            self.assertEqual(path.read_bytes(), saved)
            self.assertEqual(list(Path(scratch).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
