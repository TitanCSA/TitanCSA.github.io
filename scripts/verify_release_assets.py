"""Check pinned GitHub assets or preview the metadata for a candidate tag."""

from argparse import ArgumentParser
from contextlib import nullcontext
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
from tempfile import NamedTemporaryFile, TemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "dist" / "releases.json"
SOURCE = ROOT / "releases.json"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
SHA256_TAG = re.compile(r"sha256:([0-9a-f]{64})")
PUBLIC_CHECKOUT = re.compile(r"licences\.configcsa\.com|checkout\.stripe\.com|buy\.stripe\.com", re.I)
MARKDOWN_LINK = re.compile(r"\]\((https://[^\s)]+)\)")


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


def official_assets(edition, tag, filenames, *, check_contact=False):
    repository = urlparse(edition["repository"])
    if (repository.scheme != "https" or repository.netloc != "github.com"
            or not re.fullmatch(r"/(?:TitanCSA|titanfyre)/[A-Za-z0-9._-]+", repository.path)):
        raise ValueError(f"{edition['slug']}: expected the official GitHub repository")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", tag):
        raise ValueError("Unexpected release tag")
    release = fetch_release(f"https://api.github.com/repos{repository.path}/releases/tags/{quote(tag, safe='')}")
    if release["draft"] or tag != release["tag_name"]:
        raise ValueError(f"{edition['slug']}: unpublished or mismatched release {tag}")
    if check_contact:
        body = release.get("body") or ""
        if PUBLIC_CHECKOUT.search(body):
            raise ValueError(f"{edition['slug']} {tag}: public release notes contain a checkout link")
        if not all(word in body.casefold() for word in ("discord", "titancsa")):
            raise ValueError(f"{edition['slug']} {tag}: release notes are missing the Discord contact")
        links = set(MARKDOWN_LINK.findall(body))
        missing = [language for language, url in edition["first_run_guides"].items() if url not in links]
        if missing:
            raise ValueError(f"{edition['slug']} {tag}: release notes are missing first-run guides for {', '.join(missing)}")

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


def verify_download(url, expected, *, check_contact=False):
    request = Request(url, headers={"User-Agent": "TitanCSA-Catalogue-Download-Check"})
    digest = sha256()
    check_zip = check_contact and urlparse(url).path.lower().endswith(".zip")
    with (TemporaryFile() if check_zip else nullcontext()) as copy:
        with urlopen(request, timeout=30) as response:
            for chunk in iter(lambda: response.read(1 << 20), b""):
                digest.update(chunk)
                if check_zip:
                    copy.write(chunk)
        if digest.hexdigest() != expected:
            raise ValueError(f"Downloaded bytes differ from the expected SHA-256: {url}")
        if check_zip:
            with ZipFile(copy) as archive:
                for member in archive.infolist():
                    if Path(member.filename).suffix.lower() not in {".txt", ".md", ".htm", ".html"}:
                        continue
                    data = archive.read(member)
                    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
                    if PUBLIC_CHECKOUT.search(data.decode(encoding, errors="replace")):
                        raise ValueError(f"Public archive documentation contains a checkout link: {url} > {member.filename}")


def check_edition(edition, sdk_role, verify_bytes=False, *, check_contact=False):
    assets = official_assets(edition, edition["tag"], edition["demo_files"], check_contact=check_contact)
    if edition["demo_assets"] != {role: url for role, (url, _) in assets.items()}:
        raise ValueError(f"{edition['slug']}: generated asset URLs differ from the official URLs")
    pinned = edition["demo_asset_sha256"]
    changed = [filename for role, filename in edition["demo_files"].items()
               if pinned.get(role) != assets[role][1]]
    sdk_file = edition["demo_files"][sdk_role]
    if assets[sdk_role][1] != edition["sdk_sha256"] and sdk_file not in changed:
        changed.append(sdk_file)
    if changed:
        raise ValueError(f"{edition['slug']} {edition['tag']}: pinned SHA-256 differs for {', '.join(changed)}")
    if pinned.keys() != assets.keys():
        raise ValueError(f"{edition['slug']} {edition['tag']}: unexpected pinned asset roles")
    if verify_bytes:
        for url, digest in assets.values():
            verify_download(url, digest, check_contact=check_contact)
    return len(assets)


def candidate(edition, tag, version, sdk_role, overrides, verify_bytes=False, *, check_contact=False):
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ValueError("Supply the four-part demo driver version")
    filenames = {role: name.replace(edition["demo"], version) for role, name in edition["demo_files"].items()}
    for change in overrides:
        role, sep, filename = change.partition("=")
        if not sep or role not in filenames or not re.fullmatch(r"[A-Za-z0-9._-]+", filename):
            raise ValueError("Use --asset once per replacement with an existing role and a filename")
        filenames[role] = filename
    assets = official_assets(edition, tag, filenames, check_contact=check_contact)
    if verify_bytes:
        for url, digest in assets.values():
            verify_download(url, digest, check_contact=True)
    source_fields = {"slug", "demo", "tag", "commercial", "use", "api", "trial_starts", "note", "demo_files", "sdk_sha256",
                     "setup_member", "setup_requirements"}
    row = {name: value for name, value in edition.items() if name in source_fields}
    row.update(demo=version, tag=tag, demo_files=filenames, sdk_sha256=assets[sdk_role][1],
               demo_asset_sha256={role: digest for role, (_, digest) in assets.items()})
    return row


def update_pin(path, previous, reviewed):
    original = path.read_bytes()
    source = json.loads(original)
    for index, row in enumerate(source["editions"]):
        if row["slug"] != reviewed["slug"]:
            continue
        if any(previous.get(key) != value for key, value in row.items()):
            raise ValueError("The source changed since the build. Rebuild before updating a release pin.")
        replacement = {**row, **reviewed}
        if replacement == row:
            return False
        source["editions"][index] = replacement
        source["reviewed"] = datetime.now(timezone.utc).date().isoformat()
        output = NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                    prefix=path.stem + "-", suffix=".tmp", delete=False)
        temporary = Path(output.name)
        try:
            with output:
                json.dump(source, output, ensure_ascii=False, indent=2)
                output.write("\n")
            if path.read_bytes() != original:
                raise ValueError("The catalogue changed during the update. Rebuild and retry.")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return True
    raise ValueError(f"No source release entry for {reviewed['slug']}")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", nargs=3, metavar=("EDITION", "TAG", "VERSION"))
    parser.add_argument("--asset", action="append", default=[], metavar="ROLE=FILENAME")
    parser.add_argument("--apply", action="store_true",
                        help="Check the candidate release notes and downloads, then write to releases.json")
    parser.add_argument("--verify-downloads", action="store_true", help="Download each public file and hash its bytes")
    parser.add_argument("--check-public-contact", action="store_true",
                        help="Audit demo notes and any downloaded ZIP documentation for public purchase links")
    args = parser.parse_args()
    if (args.asset or args.apply) and not args.candidate:
        parser.error("--asset and --apply require --candidate")
    if args.check_public_contact and args.candidate:
        parser.error("--check-public-contact audits the currently pinned releases")
    if not CATALOGUE.is_file():
        parser.error("Run python scripts/build.py before checking a release.")
    editions = json.loads(CATALOGUE.read_text(encoding="utf-8"))["editions"]
    recipes = json.loads((ROOT / "sdk-checks.json").read_text(encoding="utf-8"))
    if args.candidate:
        name, tag, version = args.candidate
        edition = next((row for row in editions if row["slug"] == name), None)
        if edition is None:
            parser.error(f"Unknown edition {name}")
        reviewed = candidate(edition, tag, version, recipes[name]["asset_role"], args.asset,
                             args.verify_downloads or args.apply, check_contact=args.apply)
        if args.apply:
            update_pin(SOURCE, edition, reviewed)
        print(json.dumps(reviewed, ensure_ascii=False, indent=2))
        return
    checked = 0
    for edition in editions:
        count = check_edition(edition, recipes[edition["slug"]]["asset_role"], args.verify_downloads,
                              check_contact=args.check_public_contact)
        print(f"{edition['slug']} {edition['tag']}: {count} official assets and exact SDK digest")
        checked += count
    integration = json.loads((ROOT / "dist" / "integration.json").read_text(encoding="utf-8"))
    apps = integration["applications"]
    for app in apps:
        edition = {"slug": app["id"], "repository": app["source"]}
        archive = official_assets(edition, app["tag"], {"zip": app["zip"]})["zip"]
        if archive != (app["download_url"], app["sha256"]):
            raise ValueError(f"{app['id']}: pinned app ZIP differs from the official release")
        if args.verify_downloads:
            verify_download(*archive, check_contact=args.check_public_contact)
        print(f"{app['id']} {app['tag']}: exact app ZIP digest")
    scope = "downloaded files" if args.verify_downloads else "asset references"
    print(f"Verified {checked + len(apps)} {scope} across {len(editions) + len(apps)} pinned releases.")
    if args.check_public_contact:
        print(f"Verified the Discord contact and first-run guides in all {len(editions)} pinned driver demo notes.")
        if args.verify_downloads:
            print("Checked downloaded demo and application ZIP documentation for checkout links.")
    quickstarts = integration.get("sdk_quickstarts", [])
    for release_url in sorted({item["release_url"] for item in quickstarts}):
        repository, separator, tag = release_url.rpartition("/releases/tag/")
        if not separator:
            raise ValueError("A quickstart must link to its GitHub release.")
        pinned = {item["edition"]: item for item in quickstarts if item["release_url"] == release_url}
        filenames = {key: row["download_url"].rsplit("/", 1)[-1] for key, row in pinned.items()}
        assets = official_assets({"slug": "rust quickstarts", "repository": repository}, tag, filenames)
        for key, (url, digest) in assets.items():
            if (url, digest) != (pinned[key]["download_url"], pinned[key]["sha256"]):
                raise ValueError(f"{key}: pinned quickstart differs from the official release.")
            verify_download(url, digest, check_contact=args.check_public_contact)
        print(f"{tag}: verified {len(assets)} public quickstart archives and their SHA-256 values.")


if __name__ == "__main__":
    main()
