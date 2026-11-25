"""Check pinned GitHub assets or preview the metadata for a candidate tag."""

from argparse import ArgumentParser
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "dist" / "releases.json"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
SHA256_TAG = re.compile(r"sha256:([0-9a-f]{64})")


def fetch_release(url):
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "TitanCSA-Catalogue-Link-Check",
    })
    token = os.environ.get("TITANCSA_CATALOGUE_TOKEN")
    if token and urlparse(url).netloc == "api.github.com":
        request.add_unredirected_header("Authorization", f"Bearer {token}")
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


def official_assets(edition, tag, filenames):
    repository = urlparse(edition["repository"])
    if (repository.scheme != "https" or repository.netloc != "github.com"
            or not re.fullmatch(r"/(?:TitanCSA|titanfyre)/[A-Za-z0-9._-]+", repository.path)):
        raise ValueError(f"{edition['slug']}: expected the official GitHub repository")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", tag):
        raise ValueError("Unexpected release tag")
    release = fetch_release(f"https://api.github.com/repos{repository.path}/releases/tags/{quote(tag, safe='')}")
    if release["draft"] or tag != release["tag_name"]:
        raise ValueError(f"{edition['slug']}: unpublished or mismatched release {tag}")

    assets = {asset["name"]: asset for asset in release["assets"]}
    result = {}
    for role, filename in filenames.items():
        asset = assets.get(filename)
        if not asset or asset["state"] != "uploaded" or asset["size"] <= 0:
            raise ValueError(f"{edition['slug']} {tag}: missing uploaded {role} asset {filename}")
        expected = f'{edition["repository"]}/releases/download/{tag}/{filename}'
        if asset["browser_download_url"] != expected:
            raise ValueError(f"{edition['slug']} {tag}: incorrect {role} URL")
        digest = SHA256_TAG.fullmatch(asset.get("digest") or "")
        if not digest:
            raise ValueError(f"{edition['slug']} {tag}: no SHA-256 recorded for {filename}")
        result[role] = (expected, digest[1])
    return result


def check_edition(edition, sdk_role):
    assets = official_assets(edition, edition["tag"], edition["demo_files"])
    if edition["demo_assets"] != {role: url for role, (url, _) in assets.items()}:
        raise ValueError(f"{edition['slug']}: generated asset URLs differ from the official URLs")
    if assets[sdk_role][1] != edition["sdk_sha256"]:
        raise ValueError(f"{edition['slug']}: pinned SDK SHA-256 differs from the official digest")
    if edition["demo_asset_sha256"] != {role: digest for role, (_, digest) in assets.items()}:
        raise ValueError(f"{edition['slug']}: pinned asset SHA-256 differs from the official digest")
    return len(assets)


def candidate(edition, tag, version, sdk_role, overrides):
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ValueError("Supply the four-part demo driver version")
    filenames = {role: name.replace(edition["demo"], version) for role, name in edition["demo_files"].items()}
    for change in overrides:
        role, sep, filename = change.partition("=")
        if not sep or role not in filenames or not re.fullmatch(r"[A-Za-z0-9._-]+", filename):
            raise ValueError("Use --asset once per replacement with an existing role and a filename")
        filenames[role] = filename
    assets = official_assets(edition, tag, filenames)
    source_fields = {"slug", "demo", "tag", "commercial", "use", "api", "trial_starts", "note", "demo_files", "sdk_sha256", "setup_member"}
    row = {name: value for name, value in edition.items() if name in source_fields}
    row.update(demo=version, tag=tag, demo_files=filenames, sdk_sha256=assets[sdk_role][1],
               demo_asset_sha256={role: digest for role, (_, digest) in assets.items()})
    return row


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", nargs=3, metavar=("EDITION", "TAG", "VERSION"))
    parser.add_argument("--asset", action="append", default=[], metavar="ROLE=FILENAME")
    args = parser.parse_args()
    editions = json.loads(CATALOGUE.read_text(encoding="utf-8"))["editions"]
    recipes = json.loads((ROOT / "sdk-checks.json").read_text(encoding="utf-8"))
    if args.candidate:
        name, tag, version = args.candidate
        edition = next((row for row in editions if row["slug"] == name), None)
        if edition is None:
            parser.error(f"Unknown edition {name}")
        print(json.dumps(candidate(edition, tag, version, recipes[name]["asset_role"], args.asset),
                         ensure_ascii=False, indent=2))
        return
    if args.asset:
        parser.error("--asset requires --candidate")
    checked = 0
    for edition in editions:
        count = check_edition(edition, recipes[edition["slug"]]["asset_role"])
        print(f"{edition['slug']} {edition['tag']}: {count} official assets and exact SDK digest")
        checked += count
    apps = json.loads((ROOT / "dist" / "integration.json").read_text(encoding="utf-8"))["applications"]
    for app in apps:
        edition = {"slug": app["id"], "repository": app["source"]}
        archive = official_assets(edition, app["tag"], {"zip": app["zip"]})["zip"]
        if archive != (app["download_url"], app["sha256"]):
            raise ValueError(f"{app['id']}: pinned app ZIP differs from the official release")
        print(f"{app['id']} {app['tag']}: exact app ZIP digest")
    print(f"Verified {checked + len(apps)} asset references across {len(editions) + len(apps)} pinned releases.")


if __name__ == "__main__":
    main()
