"""Verify the exact installable versions linked in the bilingual SDK guide."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
import json

ROOT = Path(__file__).resolve().parents[1]
GALLERY = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"


def read(url):
    request = Request(url, headers={"User-Agent": "TitanCSA-SDK-Registry-Check"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def verify(row):
    name, version = row["name"], row["version"]
    registry = row["ecosystem"]
    metadata = read(row["metadata_url"])
    archive = row.get("verified_archive")
    if registry == "powershell":
        entry = ET.fromstring(metadata)
        available = (entry.findtext(f".//{GALLERY}Id") == name
                     and entry.findtext(f".//{GALLERY}Version") == version)
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
        else:
            available = version in document["versions"]
            if archive:
                available = available and sha256(read(archive["url"])).hexdigest() == archive["sha256"]
    if not available:
        raise ValueError(f"{name} {version} is missing or differs from the reviewed package")
    return f"{name} {version} ({registry})"


def main():
    rows = json.loads((ROOT / "dist/integration.json").read_text(encoding="utf-8"))["sdk_registry"]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for result in pool.map(verify, rows):
            print(result)
    print(f"Verified {len(rows)} pinned registry versions.")


if __name__ == "__main__":
    main()
