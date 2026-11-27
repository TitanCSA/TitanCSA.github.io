"""Check the public documentation from llms.txt as an independent reader."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree


BASE = "https://titancsa.github.io/"
SEARCH_AGENTS = ("Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot")
PURCHASE_LINK = re.compile(r"licences\.configcsa\.com|checkout\.stripe\.com|buy\.stripe\.com", re.I)
PACKAGE_GUIDES = {
    "en": "guides/windows-input-sdk-packages/",
    "fr": "fr/installer-sdk-windows/",
}
DOWNLOAD_CHECK_GUIDES = (
    "guides/verify-windows-driver-package/",
    "fr/verifier-pilote-windows/",
)


def fetch(address, content_type=None, *, host="titancsa.github.io"):
    parsed = urlsplit(address)
    assert (parsed.scheme, parsed.netloc) == ("https", host), address
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
        self.links = set()
        self.download_options = {}
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag == "a" and attrs.get("href"):
            self.links.add(urljoin(self.address, attrs["href"]))
        if tag == "option" and "data-sha256" in attrs:
            assert attrs["value"] not in self.download_options, self.address
            self.download_options[attrs["value"]] = attrs["data-sha256"]
        if tag == "meta" and attrs.get("name", "").lower() in ("robots", *map(str.lower, SEARCH_AGENTS)):
            assert "noindex" not in attrs.get("content", "").lower(), self.address
        if "id" in attrs:
            self.ids.add(attrs["id"])


def verify_project_public_files(product, contact):
    source = urlsplit(product["source"])
    assert source.scheme == "https" and source.netloc == "github.com", source.geturl()
    assert re.fullmatch(r"/[\w.-]+/[\w.-]+", source.path), source.geturl()
    host = "raw.githubusercontent.com"
    address = f"https://{host}{source.path}/refs/heads/main/README.md"
    readme = fetch(address, "text/plain", host=host)
    first_steps = re.search(r"<!-- simple-start:start -->(.*?)<!-- simple-start:end -->", readme, re.S)
    assert first_steps, address
    demo = product["demo"]
    links = (demo["setup_download_url"], product["first_run_guides"]["fr"], contact["contact_guide_url"])
    assert all(link in first_steps[1] for link in links), address
    viewer = demo["assets"].get("viewer")
    assert not viewer or viewer["url"] in first_steps[1], address
    contact_block = re.search(r"<!-- full-version-contact:start -->(.*?)<!-- full-version-contact:end -->",
                              "\n".join(readme.splitlines()[:35]), re.S)
    assert contact_block, address
    assert contact["username"] in contact_block[1] and "one-hour demo limit" in contact_block[1], address
    assert "## SDK and packages" in readme and product["first_run_guides"]["en"] + "#first-sdk-check" in readme, address
    if wheel := product.get("python_wheel"):
        assert wheel["guide_urls"]["en"] in readme, address
    citation_url = f"https://{host}{source.path}/refs/heads/main/CITATION.cff"
    citation = set(fetch(citation_url, "text/plain", host=host).splitlines())
    for field, value in (("repository-code", product["source"]), ("url", product["overview_url"])):
        assert f"{field}: {value}" in citation, citation_url


def verify_python_wheel(product, guides, package_guides):
    wheel = product["python_wheel"]
    evidence_url = wheel["evidence_url"]
    evidence = json.loads(fetch(evidence_url, "application/json"))
    assert evidence["edition"] == product["id"], evidence_url
    assert all(evidence["wheel"][key] == wheel[key] for key in ("filename", "url", "sha256")), evidence_url
    assert evidence["driver_demo"]["tag"] == wheel["tested_demo_tag"], evidence_url
    assert evidence["driver_demo"]["version"] == wheel["tested_demo_version"], evidence_url
    source_url = wheel["source_url"]
    assert source_url == BASE + "assets/" + evidence["source_file"], source_url
    source_digest = sha256(fetch(source_url).encode("utf-8")).hexdigest()
    assert source_digest == wheel["source_sha256"] == evidence["source_sha256"], source_url
    assert set(wheel["guide_urls"]) == set(product["first_run_guides"]), product["id"]
    for language, guide in wheel["guide_urls"].items():
        address, fragment = urldefrag(guide)
        assert address == product["first_run_guides"][language], guide
        assert fragment and fragment in guides[address].ids, guide
        assert {wheel["url"], source_url} <= guides[address].links, guide
        assert guide in package_guides[language].links, guide


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
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda product: verify_project_public_files(product, contact), manifest["products"]))

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
        guides = dict(zip(documents, pool.map(lambda url: Guide(url, fetch(url, "text/html")), documents)))
    for address, page in guides.items():
        assert page.canonicals == [address] and "first-sdk-check" in page.ids, address

    expected_options = {
        f'{product["id"]}:{role}': asset["sha256"]
        for product in manifest["products"]
        for role, asset in product["demo"]["assets"].items()
    }
    for route in DOWNLOAD_CHECK_GUIDES:
        address = BASE + route
        assert address in references and address in sitemap, address
        assert all(robots.can_fetch(agent, address) for agent in SEARCH_AGENTS), address
        page = Guide(address, fetch(address, "text/html"))
        assert page.canonicals == [address] and "check-download" in page.ids, address
        assert page.download_options == expected_options, address

    sources = {(product["sdk_check"]["source_url"], product["sdk_check"]["source_sha256"])
               for product in manifest["products"]}
    for address, digest in sorted(sources):
        assert sha256(fetch(address).encode("utf-8")).hexdigest() == digest, address

    wheel_products = [product for product in manifest["products"] if "python_wheel" in product]
    package_guides = {}
    for language, route in PACKAGE_GUIDES.items():
        address = BASE + route
        assert address in references and address in sitemap, address
        assert all(robots.can_fetch(agent, address) for agent in SEARCH_AGENTS), address
        page = Guide(address, fetch(address, "text/html"))
        assert page.canonicals == [address], address
        package_guides[language] = page
    for product in wheel_products:
        verify_python_wheel(product, guides, package_guides)

    for language, guide in manifest["guides"].items():
        reference_url = guide + "quick-reference.md"
        assert reference_url in references, language
        assert all(robots.can_fetch(agent, reference_url) for agent in SEARCH_AGENTS), reference_url
        sections = re.split(r"^## ", fetch(reference_url), flags=re.MULTILINE)[1:]
        assert len(sections) == len(manifest["products"]), language
        for section, product in zip(sections, manifest["products"]):
            sdk, demo = product["sdk_check"], product["demo"]
            command = sdk["build_verification"]["command_from_starter_zip"]
            installed_command = sdk["build_verification"].get("command_after_setup")
            expected = sdk["expected_after_setup"]["output_contains"]
            assert section.startswith(product["name"] + "\n") and all(item in section for item in (
                product["first_run_guides"][language], demo["setup_download_sha256"],
                sdk["archive_sha256"], command, expected,
                f'build {demo["setup_requirements"]["windows_10_minimum_build"]}',
            )), (language, product["id"])
            assert not installed_command or installed_command in section

    print(json.dumps({
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "products": len(manifest["products"]),
        "github_readmes_with_verified_first_steps": len(manifest["products"]),
        "github_citations_with_verified_links": len(manifest["products"]),
        "bilingual_download_check_files": len(expected_options),
        "canonical_sdk_pages": len(guides),
        "sdk_sources_with_verified_hash": len(sources),
        "archived_python_wheels_with_verified_guides_and_sources": len(wheel_products),
        "markdown_languages": sorted(manifest["guides"]),
        "search_agents_allowed_by_robots": list(SEARCH_AGENTS),
    }))


if __name__ == "__main__":
    main()
