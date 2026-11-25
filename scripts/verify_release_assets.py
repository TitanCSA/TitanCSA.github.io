"""Check that every demo asset in the generated catalogue exists on its pinned GitHub release."""

import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


CATALOGUE = Path(__file__).resolve().parents[1] / "dist" / "releases.json"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def fetch_release(url):
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "TitanCSA-Catalogue-Link-Check",
    })
    for attempt in range(3):
        try:
            with urlopen(request, timeout=12) as response:
                return json.load(response)
        except HTTPError as error:
            if attempt == 2 or error.code not in RETRYABLE_STATUS:
                raise
        except URLError:
            if attempt == 2:
                raise
        time.sleep(1 + attempt)


def check_edition(edition):
    repository = urlparse(edition["repository"])
    if repository.scheme != "https" or repository.netloc != "github.com":
        raise ValueError(f"{edition['slug']}: expected the official GitHub repository")

    tag = edition["tag"]
    url = f"https://api.github.com/repos{repository.path}/releases/tags/{quote(tag, safe='')}"
    release = fetch_release(url)
    if release["draft"] or tag != release["tag_name"]:
        raise ValueError(f"{edition['slug']}: unpublished or mismatched release {tag}")

    assets = {asset["name"]: asset for asset in release["assets"]}
    for role, filename in edition["demo_files"].items():
        asset = assets.get(filename)
        if not asset or asset["state"] != "uploaded" or asset["size"] <= 0:
            raise ValueError(f"{edition['slug']} {tag}: missing uploaded {role} asset {filename}")
        if asset["browser_download_url"] != edition["demo_assets"][role]:
            raise ValueError(f"{edition['slug']} {tag}: incorrect {role} URL")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", asset.get("digest") or ""):
            raise ValueError(f"{edition['slug']} {tag}: no SHA-256 recorded for {filename}")
    return len(edition["demo_files"])


def main():
    editions = json.loads(CATALOGUE.read_text(encoding="utf-8"))["editions"]
    checked = 0
    for edition in editions:
        assets = check_edition(edition)
        print(f"{edition['slug']} {edition['tag']}: {assets} official assets")
        checked += assets
    print(f"Verified {checked} asset references across {len(editions)} pinned releases.")


if __name__ == "__main__":
    main()
