"""Build a minimal Windows sample against an exact published SDK archive."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zipfile import ZipFile

from integration import sdk_folder

ROOT = Path(__file__).resolve().parents[1]
GENERATORS = {"x86": "Win32", "x64": "x64"}


def checked_archive(url, expected, destination):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith(("/TitanCSA/", "/titanfyre/")):
        raise ValueError(f"Expected an official GitHub SDK asset: {url}")
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("Missing SHA-256 for the SDK archive")
    request = Request(url, headers={"User-Agent": "TitanCSA SDK example check"})
    with urlopen(request, timeout=40) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024 or sha256(data).hexdigest() != expected:
        raise ValueError("SDK archive size or SHA-256 did not match")
    destination.write_bytes(data)


def safe_extract(archive, directory):
    with ZipFile(archive) as zipped:
        size = 0
        for member in zipped.infolist():
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in member.filename or ":" in member.filename:
                raise ValueError(f"Unexpected SDK archive path: {member.filename}")
            size += member.file_size
        if size > 128 * 1024 * 1024:
            raise ValueError("SDK archive expands past the expected size")
        zipped.extractall(directory)


def make_project(directory, sdk, recipe, arch):
    sample = recipe["sample"]
    checked_source = ROOT / "assets" / sample
    if not checked_source.is_file() or checked_source.parent != ROOT / "assets":
        raise ValueError("The manifest must name a local sample file")
    shutil.copyfile(checked_source, directory / sample)
    impl = recipe["implementation"]
    cmake = [
        "cmake_minimum_required(VERSION 3.20)",
        "cmake_policy(SET CMP0091 NEW)",
        "project(FirstSdkCheck LANGUAGES CXX)" if impl else "project(FirstSdkCheck LANGUAGES C)",
        f'add_executable(first-sdk-check "{sample}")',
        'set_property(TARGET first-sdk-check PROPERTY MSVC_RUNTIME_LIBRARY MultiThreaded)',
        "target_compile_options(first-sdk-check PRIVATE /W4 /WX /utf-8)",
        f'target_include_directories(first-sdk-check PRIVATE "{sdk.as_posix()}")',
    ]
    if impl:
        cmake += [
            f'target_sources(first-sdk-check PRIVATE "{(sdk / impl).as_posix()}")',
            "target_compile_features(first-sdk-check PRIVATE cxx_std_17)",
            "target_compile_options(first-sdk-check PRIVATE /EHsc /permissive-)",
            "target_compile_definitions(first-sdk-check PRIVATE UNICODE _UNICODE NOMINMAX)",
        ]
    else:
        library = sdk / arch / "interception.lib"
        cmake.append(f'target_link_libraries(first-sdk-check PRIVATE "{library.as_posix()}")')
    libraries = recipe.get("link_libraries", [])
    if libraries:
        cmake.append("target_link_libraries(first-sdk-check PRIVATE " + " ".join(libraries) + ")")
    (directory / "CMakeLists.txt").write_text("\n".join(cmake) + "\n", encoding="utf-8")


def cmake(command, verbose):
    completed = subprocess.run(["cmake", *command],
                               stdout=None if verbose else subprocess.PIPE,
                               stderr=None if verbose else subprocess.STDOUT,
                               text=True, errors="replace")
    if completed.returncode:
        if completed.stdout:
            print(completed.stdout, end="", file=sys.stderr)
        completed.check_returncode()


def run_check(slug, arch, run, expect_clean, cached_archive, verbose, *, compile_sample=None):
    rows = json.loads((ROOT / "dist/releases.json").read_text(encoding="utf-8"))["editions"]
    edition = next(row for row in rows if row["slug"] == slug)
    recipe = json.loads((ROOT / "sdk-checks.json").read_text(encoding="utf-8"))[slug]
    if compile_sample is not None:
        if run:
            raise ValueError("Documented samples are compile-only in this check")
        recipe["sample"] = compile_sample
    if arch not in recipe["app_architectures"]:
        raise ValueError(f"{slug} does not publish this example for {arch}")
    url = edition["demo_assets"][recipe["asset_role"]]
    with TemporaryDirectory(prefix=f"titancsa-{slug}-") as scratch:
        folder = Path(scratch)
        archive = folder / "sdk.zip"
        if cached_archive:
            if sha256(cached_archive.read_bytes()).hexdigest() != edition["sdk_sha256"]:
                raise ValueError("Cached archive SHA-256 does not match the pinned asset")
            shutil.copyfile(cached_archive, archive)
        else:
            checked_archive(url, edition["sdk_sha256"], archive)
        safe_extract(archive, folder / "sdk")
        setup_member = edition.get("setup_member")
        if setup_member and not (folder / "sdk" / setup_member).is_file():
            raise ValueError("The downloaded demo archive does not have the documented installer")
        sdk = folder / "sdk" / sdk_folder(edition, recipe)
        implementation = recipe["implementation"]
        header = f"{Path(implementation).stem}.h" if implementation else "interception.h"
        if not (sdk / header).is_file():
            raise ValueError("The pinned SDK archive is missing its documented native header")
        make_project(folder, sdk, recipe, arch)
        build = folder / "build"
        cmake(["-S", str(folder), "-B", str(build), "-G", "Visual Studio 17 2022", "-A", GENERATORS[arch]], verbose)
        cmake(["--build", str(build), "--config", "Release"], verbose)
        if not run:
            return
        exe = build / "Release" / "first-sdk-check.exe"
        if not recipe["implementation"]:
            shutil.copyfile(sdk / arch / "interception.dll", exe.with_name("interception.dll"))
        result = subprocess.run([str(exe)], cwd=exe.parent, timeout=10, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        print(result.stdout, end="")
        print(result.stderr, end="")
        expected = [recipe["expected_without_driver"]]
        if not expect_clean:
            expected.append(recipe["expected_after_setup"])
        valid = any(result.returncode == item["exit_code"] and
                    item["output_contains"] in result.stdout + result.stderr for item in expected)
        if not valid:
            raise RuntimeError(f"Unexpected {slug} sample result: exit {result.returncode}")


def main():
    recipes = json.loads((ROOT / "sdk-checks.json").read_text(encoding="utf-8"))
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=(*recipes, "all"))
    parser.add_argument("--arch", choices=tuple(GENERATORS))
    parser.add_argument("--run", action="store_true", help="Run the sample without installing a driver")
    parser.add_argument("--expect-clean", action="store_true", help="Require the expected missing-driver result on a clean host")
    parser.add_argument("--cached-archive", type=Path, help="Use a previously downloaded SDK ZIP and check its SHA-256")
    parser.add_argument("--verbose", action="store_true", help="Print full compiler and linker output")
    args = parser.parse_args()
    if args.edition == "all":
        if args.cached_archive or args.arch:
            parser.error("Use --arch or --cached-archive with a single edition")
        pairs = [(slug, architecture) for slug, recipe in recipes.items()
                 for architecture in recipe["app_architectures"]]
    else:
        pairs = [(args.edition, args.arch or "x64")]
    for slug, arch in pairs:
        print(f"Checking {slug} ({arch})", flush=True)
        run_check(slug, arch, args.run or args.expect_clean, args.expect_clean, args.cached_archive, args.verbose)


if __name__ == "__main__":
    main()
