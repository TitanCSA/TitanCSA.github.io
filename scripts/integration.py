"""Build the public integration manifest and the shared bilingual SDK table."""

from hashlib import sha256
from html import escape
import json
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DATE = "2026-11-25"


def sdk_folder(edition, recipe):
    subdirectory = recipe["sdk_subdirectory"]
    if recipe["asset_role"] == "archive":
        return subdirectory
    archive_name = edition["demo_files"][recipe["asset_role"]]
    return f"{Path(archive_name).stem}/{subdirectory}"


def make_manifest(base, editions):
    recipes = json.loads((ROOT / "sdk-checks.json").read_text(encoding="utf-8"))
    if recipes.keys() != editions.keys():
        raise ValueError("Every driver edition needs one SDK check recipe")
    proof_file = "assets/demo-install-verification-2026-11-25.json"
    installed_evidence = json.loads((ROOT / proof_file).read_text(encoding="utf-8"))["editions"]

    rows = []
    for slug, edition in editions.items():
        recipe = recipes[slug]
        sample_path = ROOT / "assets" / recipe["sample"]
        implementation = recipe["implementation"]
        api = "C++17" if implementation else "C"
        needs_driver = recipe["needs_installed_driver"]
        header = f"{Path(implementation).stem}.h" if implementation else "interception.h"
        desktop_libraries = recipe.get("link_libraries", [])
        app_architectures = recipe["app_architectures"]
        setup_role = "installer" if "installer" in edition["demo_assets"] else "archive"
        digests = edition["demo_asset_sha256"]
        row = {
            "id": slug,
            "name": edition["name"],
            "source": edition["repository"],
            "overview_url": edition["overview_url"],
            "demo": {
                "version": edition["demo"],
                "tag": edition["tag"],
                "notes_url": edition["demo_url"],
                "setup_download_url": edition["demo_download_url"],
                "setup_download_sha256": digests[setup_role],
                "setup_format": "installer" if setup_role == "installer" else "zip",
                "setup_member": edition.get("setup_member"),
                "supported_driver_architecture": "x64",
                "trial_starts_on": edition["trial_starts"],
                "assets": {role: {"url": url, "sha256": digests[role]}
                           for role, url in edition["demo_assets"].items()},
            },
            "sdk_check": {
                "api": api,
                "archive_url": edition["demo_assets"][recipe["asset_role"]],
                "archive_sha256": edition["sdk_sha256"],
                "source_url": base + "assets/" + recipe["sample"],
                "source_sha256": sha256(sample_path.read_bytes()).hexdigest(),
                "source_file": recipe["sample"],
                "archive_member_directory": sdk_folder(edition, recipe),
                "header_file": header,
                "implementation_file": implementation,
                "link_libraries": desktop_libraries,
                "import_library_by_architecture": ({} if implementation else
                    {arch: f"{arch}/interception.lib" for arch in app_architectures}),
                "runtime_file_by_architecture": ({} if implementation else
                    {arch: f"{arch}/interception.dll" for arch in app_architectures}),
                "app_architectures": app_architectures,
                "needs_installed_driver": needs_driver,
                "opens_input_context": recipe["opens_input_context"],
                "starts_demo_timer": recipe["starts_demo_timer"],
                "result": recipe["expected_after_setup"]["output_contains"],
                "expected_without_driver": recipe["expected_without_driver"],
                "expected_after_setup": recipe["expected_after_setup"],
                "exit_codes": {
                    "0": "The check completed.",
                    "1": "The check failed. Read the diagnostic.",
                    **({"2": "Windows could not find the driver interface."} if needs_driver else {}),
                },
                "build_verification": {
                    "platform": "Windows x64 with Visual Studio 2022 C++ desktop tools and CMake 3.20+",
                    "command_from_portal_source": f"python scripts/test_first_sdk.py {slug} --run",
                    "command_from_starter_zip": f"python scripts/test_first_sdk.py {slug} --run",
                    "scope": "Compile and run the documented first check. The build does not install a driver.",
                },
            },
        }
        proof = installed_evidence.get(slug)
        if proof and proof["version"] == edition["demo"] and proof["sdk_archive_sha256"] == edition["sdk_sha256"]:
            row["demo"]["read_only_install_verification"] = {"url": base + proof_file, "edition": slug}
            row["sdk_check"]["tested_account"] = "Administrator on Windows 11 x64"
        rows.append(row)
    applications = json.loads((ROOT / "starter-apps.json").read_text(encoding="utf-8"))
    for app in applications:
        repository = f'https://github.com/{app["repository"]}'
        app.update(
            source=repository,
            download_url=f'{repository}/releases/download/{app["tag"]}/{app["zip"]}',
            platform="Windows x64",
            needs_input_driver_for_first_run=False,
        )
        test = app["test"]
        if "source_path" in test:
            path = test.pop("source_path").lstrip("/")
            test.update(source_url=base + path, source_sha256=sha256((ROOT / path).read_bytes()).hexdigest())
    return {
        "$schema": base + "integration.schema.json",
        "schema_version": 1,
        "reviewed": REVIEW_DATE,
        "project_catalogue_url": base + "projects.json",
        "starter_zip_url": base + "downloads/first-sdk-checks.zip",
        "starter_zip_checksum_url": base + "downloads/first-sdk-checks.zip.sha256",
        "source_repository": "https://github.com/TitanCSA/TitanCSA.github.io",
        "guides": {"en": base + "guides/installer-and-sdk/", "fr": base + "fr/installeur-et-sdk/"},
        "commercial_contact": {
            "platform": "Discord",
            "username": "titancsa",
            "contact_guide_url": base + "about/evidence/#release-contact",
        },
        "products": rows,
        "first_run_guides": {"en": base + "guides/first-run/", "fr": base + "fr/essayer-sans-pilote/"},
        "applications": applications,
    }


def app_cards(manifest, language, *, more=False):
    french = language == "fr"
    cards = []
    apps = manifest["applications"]
    for app in (apps[4:] if more else apps[:4]):
        name = escape(app["name"])
        download = escape(app["download_url"], quote=True)
        download_label = "Télécharger le ZIP" if french else "Download the ZIP"
        title = f'<h3 id="{app["id"]}">{name}</h3>'
        intro = f'<p>{escape(app["purpose"][language])}</p>'
        steps = f'<ol><li><a href="{download}">{download_label}</a>.</li><li>{escape(app["steps"][language])}</li></ol>'
        command = f'<pre><code>{escape(app["command"])}</code></pre>' if "command" in app else ""
        outcome = "À l’écran" if french else "What you should see"
        result = f'<p><strong>{outcome}.</strong> {escape(app["expected"][language])}</p>'
        screenshot = ""
        if "picture" in app:
            picture = app["picture"]
            image_path = escape(picture["path"], quote=True)
            alt = escape(picture["alt"][language], quote=True)
            label = "Voir la capture" if french else "See the screenshot"
            screenshot = (f'<details><summary>{label}</summary><img class="first-run-image" loading="lazy" '
                          f'width="{picture["width"]}" height="{picture["height"]}" src="{image_path}" alt="{alt}"></details>')
        cards.append(f'<article class="guide-card">{title}{intro}{steps}{command}{result}{screenshot}</article>')
    return '<div class="guide-grid">' + "\n".join(cards) + '</div>'


def sdk_rows(manifest, french=False):
    labels = (("Installer", "Archive SDK", "Code du test") if french else
              ("Setup download", "SDK archive", "Test source"))
    lines = []
    for row in manifest["products"]:
        sdk = row["sdk_check"]
        setup = row["demo"]
        architecture = " / ".join(sdk["app_architectures"])
        links = [
            f'<a href="{escape(url, quote=True)}">{label}</a>'
            for url, label in zip(
                (setup["setup_download_url"], sdk["archive_url"], sdk["source_url"]),
                (("ZIP complet" if french else "Full ZIP") if setup["setup_format"] == "zip" else labels[0],
                 *labels[1:]),
            )
        ]
        setup_hint = ""
        if setup["setup_member"]:
            file = escape(Path(setup["setup_member"]).name)
            label = "Ouvre ensuite" if french else "Then open"
            setup_hint = f'<br>{label} <code>{file}</code>'
        lines.append(
            f'<tr><th scope="row"><a href="{escape(row["overview_url"], quote=True)}">{escape(row["name"])}</a></th>'
            f'<td>{links[0]}{setup_hint}</td><td>{sdk["api"]} · {architecture}<br>{links[1]} · {links[2]}</td></tr>'
        )
    return "\n".join(lines)


def write_starter(out, manifest):
    files = {
        "LICENSE": ROOT / "LICENSE",
        "sdk-checks.json": ROOT / "sdk-checks.json",
        "integration.json": out / "integration.json",
        "integration.schema.json": out / "integration.schema.json",
        "dist/releases.json": out / "releases.json",
        "scripts/integration.py": ROOT / "scripts/integration.py",
        "scripts/test_first_sdk.py": ROOT / "scripts/test_first_sdk.py",
    }
    for row in manifest["products"]:
        source = "assets/" + row["sdk_check"]["source_file"]
        files[source] = ROOT / source
    items = {name: path.read_bytes() for name, path in files.items()}
    items["START-HERE.txt"] = b"""First Windows SDK check

You need Python 3.10+, CMake 3.20+, and Visual Studio 2022 with
Desktop development with C++ on a Windows x64 PC.

1. Extract this ZIP.
2. Open PowerShell in the extracted folder.
3. Run the check for your edition. For example:

   python scripts/test_first_sdk.py vdevice --run

The script downloads the exact SDK archive, checks its SHA-256 and runs
a small program. Windows 2 means a driver status check could not find
the driver interface. Install the matching demo and run the check again.

For Interception V2, append --arch x86 if your own app is 32-bit.
The sample reports DLL slot ranges without opening a device context.
For Titan Audio Link, zero matching endpoints is normal before installation.

See integration.json for edition IDs and official source links.
Human instructions are at https://titancsa.github.io/guides/installer-and-sdk/
"""
    downloads = out / "downloads"
    downloads.mkdir(exist_ok=True)
    path = downloads / "first-sdk-checks.zip"
    with ZipFile(path, "w", compression=ZIP_STORED) as zipped:
        for name, content in sorted(items.items()):
            entry = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            zipped.writestr(entry, content)
    digest = sha256(path.read_bytes()).hexdigest()
    path.with_suffix(".zip.sha256").write_bytes(f"{digest}  {path.name}\n".encode("ascii"))
