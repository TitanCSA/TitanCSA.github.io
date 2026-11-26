"""Verify the exact installable versions linked in the bilingual SDK guide."""

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
import json

ROOT = Path(__file__).resolve().parents[1]
GALLERY = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
POM = "{http://maven.apache.org/POM/4.0.0}"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def read(url):
    request = Request(url, headers={"User-Agent": "TitanCSA-SDK-Registry-Check"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except HTTPError as error:
            if attempt == 2 or error.code not in RETRYABLE_STATUS:
                raise
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
        sleep(1 + attempt)


def verify(row):
    name, version = row["name"], row["version"]
    registry = row["ecosystem"]
    metadata = read(row["metadata_url"])
    archive = row.get("verified_archive")
    if registry == "powershell":
        entry = ET.fromstring(metadata)
        available = (entry.findtext(f".//{GALLERY}Id") == name
                     and entry.findtext(f".//{GALLERY}Version") == version)
    elif registry == "maven":
        entry = ET.fromstring(metadata)
        coordinate = entry.findtext(POM + "groupId", "") + ":" + entry.findtext(POM + "artifactId", "")
        available = coordinate == name and entry.findtext(POM + "version") == version
        available = available and sha256(read(archive["url"])).hexdigest() == archive["sha256"]
    else:
        document = json.loads(metadata)
        if registry == "pypi":
            release_files = [file for file in document["urls"] if not file["yanked"]]
            available = document["info"]["name"].casefold() == name.casefold()
            available = available and document["info"]["version"] == version and bool(release_files)
            if archive:
                available = available and any(
                    file["filename"] == archive["filename"] and file["digests"]["sha256"] == archive["sha256"]
                    for file in release_files
                )
        elif registry == "npm":
            available = document["name"] == name and document["version"] == version and bool(document["dist"]["integrity"])
            if archive:
                available = (available and document["dist"]["tarball"] == archive["url"]
                             and sha256(read(archive["url"])).hexdigest() == archive["sha256"])
        elif registry == "packagist":
            available = any(entry["version"].removeprefix("v") == version
                            and entry["source"]["reference"] == row["source_reference"]
                            for entry in document["packages"][name])
        elif registry == "rubygems":
            available = (document["name"] == name and document["version"] == version
                         and document["gem_uri"] == archive["url"] and document["sha"] == archive["sha256"])
        else:
            available = version in document["versions"]
            if archive:
                available = available and sha256(read(archive["url"])).hexdigest() == archive["sha256"]
    if not available:
        raise ValueError(f"{name} {version} is missing or differs from the reviewed package")
    return f"{name} {version} ({registry})"


def verify_documentation(url):
    try:
        read(url)
    except HTTPError as error:
        address = urlsplit(url)
        repository, view, path = address.path.lstrip("/").partition("/blob/main/")
        owner, separator, repo = repository.partition("/")
        if (error.code in RETRYABLE_STATUS and address.scheme == "https" and address.netloc == "github.com"
                and owner.casefold() in {"titancsa", "titanfyre"} and separator and repo and "/" not in repo
                and view and path and not (address.query or address.fragment)):
            raw = f"https://raw.githubusercontent.com/{repository}/main/{path}"
            try:
                if not read(raw):
                    raise ValueError("The source file is empty.")
            except (ValueError, TimeoutError, URLError) as fallback_error:
                raise ValueError(f"SDK documentation unavailable at {url}: {error}; source: {fallback_error}") from fallback_error
            print(f"GitHub documentation view returned {error.code}. Verified the exact source file for {url}.")
            return
        raise ValueError(f"SDK documentation unavailable at {url}: {error}") from error
    except (TimeoutError, URLError) as error:
        raise ValueError(f"SDK documentation unavailable at {url}: {error}") from error


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--documentation", action="store_true",
                        help="Check the documentation links as well as registry packages")
    args = parser.parse_args()
    rows = json.loads((ROOT / "dist/integration.json").read_text(encoding="utf-8"))["sdk_registry"]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for result in pool.map(verify, rows):
            print(result)
        print(f"Verified {len(rows)} pinned registry versions.")
        if args.documentation:
            links = sorted({urldefrag(row["documentation_url"]).url for row in rows if row.get("documentation_url")})
            for _ in pool.map(verify_documentation, links):
                pass
            print(f"Verified {len(links)} distinct SDK documentation links.")


if __name__ == "__main__":
    main()
