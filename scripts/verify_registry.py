"""Verify the exact installable versions linked in the bilingual SDK guide."""

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
import json
import os
import shlex
import shutil
import subprocess
import sys

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
            if document.get("homepage") != row.get("documentation_url"):
                raise ValueError(f"{name} {version} lists a different SDK guide on npm")
            if archive:
                available = (available and document["dist"]["tarball"] == archive["url"]
                             and sha256(read(archive["url"])).hexdigest() == archive["sha256"])
        elif registry == "packagist":
            available = any(entry["version"].removeprefix("v") == version
                            and entry["source"]["reference"] == row["source_reference"]
                            for entry in document["packages"][name])
        elif registry == "go":
            available = (document["Version"] == "v" + version
                         and archive["url"] == row["metadata_url"].removesuffix(".info") + ".zip"
                         and sha256(read(archive["url"])).hexdigest() == archive["sha256"])
        elif registry == "rubygems":
            available = (document["name"] == name and document["version"] == version
                         and document["gem_uri"] == archive["url"] and document["sha"] == archive["sha256"])
            if row.get("registry_documentation_verified") and document.get("documentation_uri") != row["documentation_url"]:
                raise ValueError(f"{name} {version} lists a different SDK guide on RubyGems")
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


def check_node_examples(rows):
    if sys.platform != "win32":
        raise RuntimeError("The published Node.js SDK examples require Windows x64.")
    npm, node = shutil.which("npm.cmd"), shutil.which("node.exe")
    if not npm or not node:
        raise RuntimeError("Install Node.js 20 or later with npm before running this check.")
    sample = ROOT / "assets/node-sdk-status.cjs"
    checked_sample = sample.read_bytes()
    environment = os.environ.copy()
    for name in ("NODE_OPTIONS", "NODE_PATH", "INTERCEPTOR_SDK_NODE_PATH",
                 "INTERCEPTOR_KEYBOARD_MOUSE_SDK_NODE_PATH", "INTERCEPTOR_GAMEPAD_CONTROLLER_SDK_NODE_PATH"):
        environment.pop(name, None)
    if subprocess.check_output([node, "-p", "process.arch"], env=environment, text=True).strip() != "x64":
        raise RuntimeError("The SDK archives require Node.js x64.")
    for row in rows:
        name, version = row["name"], row["version"]
        archive = row["verified_archive"]
        filename = f"{name}-{version}.tgz"
        wanted = f"https://registry.npmjs.org/{name}/-/{filename}"
        if archive["url"] != wanted or sha256(checked_sample).hexdigest() != row["first_check"]["source_sha256"]:
            raise ValueError(f"{name} {version} has mismatched package or sample metadata.")
        payload = read(wanted)
        if len(payload) > 8 * 1024 * 1024 or sha256(payload).hexdigest() != archive["sha256"]:
            raise ValueError(f"{name} {version} does not match its SHA-256.")
        with TemporaryDirectory(prefix="titancsa-node-sdk-") as directory:
            project = Path(directory)
            (project / "package.json").write_text('{"private":true}', encoding="ascii")
            (project / "npmrc").touch()
            (project / filename).write_bytes(payload)
            (project / sample.name).write_bytes(checked_sample)
            subprocess.run([npm, "install", "./" + filename, "--offline", "--ignore-scripts",
                            "--no-audit", "--no-fund", "--no-save", "--no-package-lock", "--userconfig", "npmrc"],
                           cwd=project, env=environment, check=True, timeout=60)
            installed = json.loads((project / "node_modules" / name / "package.json").read_text(encoding="utf-8"))
            if installed["name"] != name or installed["version"] != version:
                raise ValueError(f"The installed npm package did not match {name} {version}.")
            result = subprocess.run([node, sample.name, row["edition"]], cwd=project, env=environment,
                                    capture_output=True, text=True, timeout=20)
            if result.returncode != 2 or not result.stderr.startswith("Windows 2. Run InterceptorSetup.exe"):
                raise RuntimeError(f"{name} {version} did not report a missing driver: {result.stderr.strip()[:300]}")
            print(f"{name} {version} loaded and returned the documented missing-driver result.")


def check_go_examples(rows):
    go = shutil.which("go.exe")
    if sys.platform != "win32" or not go:
        raise RuntimeError("The Go SDK examples require Go on Windows x64.")
    environment = os.environ.copy()
    for edition in ("INTERCEPTOR", "INTERCEPTOR_KEYBOARD_MOUSE", "INTERCEPTOR_GAMEPAD_CONTROLLER",
                    "VDEVICE", "INTERCEPTION_V2", "TITAN_AUDIO_LINK"):
        environment.pop(edition + "_SDK_NATIVE_PATH", None)
    environment.update(GOENV="off", GOFLAGS="", GOPRIVATE="", GONOPROXY="", GONOSUMDB="",
                       GOWORK="off", GOTOOLCHAIN="local", GOPROXY="https://proxy.golang.org",
                       GOSUMDB="sum.golang.org", GOOS="windows", GOARCH="amd64", CGO_ENABLED="0")
    with TemporaryDirectory(prefix="titancsa-go-sdk-") as directory:
        location = Path(directory)
        environment.update(GOMODCACHE=str(location / "modules"), LOCALAPPDATA=str(location / "appdata"))
        for row in rows:
            check = row["first_check"]
            project = location / row["edition"]
            project.mkdir()
            sample = (ROOT / "dist" / urlsplit(check["source_url"]).path.lstrip("/")).read_bytes()
            if sha256(sample).hexdigest() != check["source_sha256"]:
                raise ValueError(f"{row['name']} example does not match its published checksum.")
            (project / check["save_as"]).write_bytes(sample)

            def run(command):
                return subprocess.check_output([go, *shlex.split(command)[1:]], cwd=project,
                                               env=environment, text=True, timeout=100)

            run(check["create_example_project_command"])
            run(row["install_command"])
            identity = f"{row['name']}@v{row['version']}"
            record = json.loads(run(f"go mod download -json {identity}"))
            archive = Path(record["Zip"]).read_bytes()
            if (record["Path"] != row["name"] or record["Version"] != "v" + row["version"]
                    or sha256(archive).hexdigest() != row["verified_archive"]["sha256"]):
                raise ValueError(f"{identity} archive does not match its published checksum.")
            run("go mod verify")
            expected = {"interception-v2": {"valid": True, "keyboard": True, "mouse": False},
                        "titan-audio-link": []}.get(row["edition"], {"windows_error": 2})
            if json.loads(run(check["command_from_app_folder"])) != expected:
                raise ValueError(f"{identity} did not return the documented clean-Windows result.")
            print(f"{identity} ran its published first check on clean Windows.")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--documentation", action="store_true",
                        help="Check the documentation links as well as registry packages")
    runtime = parser.add_mutually_exclusive_group()
    runtime.add_argument("--check-node-on-clean-windows", action="store_true",
                        help="Install the pinned npm archives and run their documented status sample on Windows x64 without the drivers")
    runtime.add_argument("--check-go-on-clean-windows", action="store_true",
                         help="Run the published first checks with the pinned Go modules on Windows x64 without the drivers")
    args = parser.parse_args()
    rows = json.loads((ROOT / "dist/integration.json").read_text(encoding="utf-8"))["sdk_registry"]
    if args.check_node_on_clean_windows:
        check_node_examples([row for row in rows if row["ecosystem"] == "npm"])
        return
    if args.check_go_on_clean_windows:
        check_go_examples([row for row in rows if row["ecosystem"] == "go"])
        return
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
