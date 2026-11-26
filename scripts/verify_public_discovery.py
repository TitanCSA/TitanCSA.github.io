"""Check the public documentation from llms.txt as an independent reader."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
from urllib.parse import urldefrag, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree


BASE = "https://titancsa.github.io/"
SEARCH_AGENTS = ("Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot")
PURCHASE_LINK = re.compile(r"licences\.configcsa\.com|checkout\.stripe\.com|buy\.stripe\.com", re.I)


def fetch(address, content_type=None):
    parsed = urlsplit(address)
    assert (parsed.scheme, parsed.netloc) == ("https", "titancsa.github.io"), address
    request = Request(address, headers={"User-Agent": "TitanCSA-Public-Documentation-Audit"})
    with urlopen(request, timeout=15) as response:
        assert response.status == 200 and response.geturl() == address, address
        assert "noindex" not in response.headers.get("X-Robots-Tag", "").lower(), address
        assert not content_type or response.headers.get_content_type() == content_type, address
        document = response.read().decode("utf-8")
    assert not PURCHASE_LINK.search(document), address
    return document


class Guide(HTMLParser):
    def __init__(self, address, document):
        super().__init__()
        self.address = address
        self.canonicals = []
        self.ids = set()
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag == "meta" and attrs.get("name", "").lower() in ("robots", *map(str.lower, SEARCH_AGENTS)):
            assert "noindex" not in attrs.get("content", "").lower(), self.address
        if "id" in attrs:
            self.ids.add(attrs["id"])


def main():
    entry = fetch(BASE + "llms.txt", "text/plain")
    assert entry.startswith("# TitanCSA\n"), "llms.txt title"
    references = set(re.findall(r"^\s*- \[[^\n]+?\]\((https://[^\s)]+)\)", entry, re.MULTILINE))
    integration_url = BASE + "integration.json"
    assert integration_url in references, "Manifest missing from llms.txt"
    manifest = json.loads(fetch(integration_url, "application/json"))
    contact = manifest["commercial_contact"]
    assert contact["platform"] == "Discord" and contact["purchase_details_shared_privately"]
    contact_url, contact_anchor = urldefrag(contact["contact_guide_url"])
    contact_page = fetch(contact_url, "text/html")
    assert contact["contact_guide_url"] in references and contact["username"] in contact_page
    assert contact_anchor in Guide(contact_url, contact_page).ids

    robots = RobotFileParser()
    robots.parse(fetch(BASE + "robots.txt", "text/plain").splitlines())
    xml = ElementTree.fromstring(fetch(BASE + "sitemap.xml"))
    sitemap = {element.text for element in xml.findall(".//{*}loc")}
    documents = sorted({
        urldefrag(url)[0]
        for product in manifest["products"]
        for url in (product["overview_url"], *product["first_run_guides"].values())
    })
    assert set(documents) <= sitemap, sorted(set(documents) - sitemap)
    assert all(robots.can_fetch(agent, url) for agent in SEARCH_AGENTS for url in (
        BASE + "llms.txt", integration_url, *documents)), "robots.txt blocks a documentation route"
    assert set(documents) <= references, sorted(set(documents) - references)
    with ThreadPoolExecutor(max_workers=5) as pool:
        guides = dict(zip(documents, pool.map(lambda url: fetch(url, "text/html"), documents)))
    for address, document in guides.items():
        page = Guide(address, document)
        assert page.canonicals == [address] and "first-sdk-check" in page.ids, address

    for language, guide in manifest["guides"].items():
        reference_url = guide + "quick-reference.md"
        assert reference_url in references, language
        assert all(robots.can_fetch(agent, reference_url) for agent in SEARCH_AGENTS), reference_url
        sections = re.split(r"^## ", fetch(reference_url), flags=re.MULTILINE)[1:]
        assert len(sections) == len(manifest["products"]), language
        for section, product in zip(sections, manifest["products"]):
            sdk, demo = product["sdk_check"], product["demo"]
            command = sdk["build_verification"]["command_from_starter_zip"]
            expected = sdk["expected_after_setup"]["output_contains"]
            assert section.startswith(product["name"] + "\n") and all(item in section for item in (
                product["first_run_guides"][language], demo["setup_download_sha256"],
                sdk["archive_sha256"], command, expected,
            )), (language, product["id"])

    print(json.dumps({
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "products": len(manifest["products"]),
        "canonical_sdk_pages": len(guides),
        "markdown_languages": sorted(manifest["guides"]),
        "search_agents_allowed_by_robots": list(SEARCH_AGENTS),
    }))


if __name__ == "__main__":
    main()
