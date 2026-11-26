import json
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_registry as registry


class RegistryDocumentationChecks(unittest.TestCase):
    documentation = "https://github.com/TitanCSA/Browser-Control-SDK/blob/main/SDK/Python/README.md"
    source = "https://raw.githubusercontent.com/TitanCSA/Browser-Control-SDK/main/SDK/Python/README.md"

    def failure(self, address, status):
        return HTTPError(address, status, "Unavailable", {}, None)

    def test_npm_homepage_matches_the_maintained_sdk_guide(self):
        row = {
            "name": "interceptor-sdk", "version": "1.0.1", "ecosystem": "npm",
            "metadata_url": "https://registry.npmjs.org/interceptor-sdk/1.0.1",
            "documentation_url": "https://github.com/TitanCSA/sdk-packages/tree/main/projects/Interceptor/Interceptor-JavaScript-npm#readme",
        }
        doc = {
            "name": row["name"], "version": row["version"], "homepage": row["documentation_url"],
            "dist": {"integrity": "sha512-fixture"},
        }
        with patch.object(registry, "read", return_value=json.dumps(doc).encode()):
            self.assertEqual(registry.verify(row), "interceptor-sdk 1.0.1 (npm)")
        doc["homepage"] = "https://github.com/TitanCSA/Interceptor/tree/main/Interceptor-JavaScript-npm#readme"
        with patch.object(registry, "read", return_value=json.dumps(doc).encode()):
            with self.assertRaisesRegex(ValueError, "different SDK guide"):
                registry.verify(row)

    def test_recovers_from_transient_github_view_error(self):
        with patch.object(registry, "read", side_effect=[self.failure(self.documentation, 503), b"# Python SDK"]) as read:
            registry.verify_documentation(self.documentation)
        self.assertEqual(read.call_args_list, [call(self.documentation), call(self.source)])

    def test_a_broken_github_view_still_fails(self):
        with patch.object(registry, "read", side_effect=self.failure(self.documentation, 404)) as read:
            with self.assertRaisesRegex(ValueError, "404"):
                registry.verify_documentation(self.documentation)
        read.assert_called_once_with(self.documentation)

    def test_a_missing_file_cannot_mask_the_view_error(self):
        with patch.object(registry, "read", side_effect=[self.failure(self.documentation, 503), self.failure(self.source, 404)]):
            with self.assertRaisesRegex(ValueError, "503.*404"):
                registry.verify_documentation(self.documentation)

    def test_a_third_party_site_has_no_raw_retry(self):
        address = self.documentation.replace("TitanCSA", "another-author")
        with patch.object(registry, "read", side_effect=self.failure(address, 503)) as read:
            with self.assertRaisesRegex(ValueError, "503"):
                registry.verify_documentation(address)
        read.assert_called_once_with(address)
