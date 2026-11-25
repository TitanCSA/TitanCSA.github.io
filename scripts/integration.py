"""Build the public integration manifest and the shared bilingual SDK table."""

from hashlib import sha256
from html import escape
import json
from pathlib import Path

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

    rows = []
    for slug, edition in editions.items():
        recipe = recipes[slug]
        sample_path = ROOT / "assets" / recipe["sample"]
        implementation = recipe["implementation"]
        api = "C++17" if implementation else "C"
        needs_driver = recipe["needs_installed_driver"]
        rows.append({
            "id": slug,
            "name": edition["name"],
            "source": edition["repository"],
            "overview_url": edition["overview_url"],
            "demo": {
                "version": edition["demo"],
                "tag": edition["tag"],
                "notes_url": edition["demo_url"],
                "setup_download_url": edition["demo_download_url"],
                "setup_format": "installer" if "installer" in edition["demo_assets"] else "zip",
                "supported_driver_architecture": "x64",
                "trial_starts_on": edition["trial_starts"],
            },
            "sdk_check": {
                "api": api,
                "archive_url": edition["demo_assets"][recipe["asset_role"]],
                "archive_sha256": recipe["sha256"],
                "source_url": base + "assets/" + recipe["sample"],
                "source_sha256": sha256(sample_path.read_bytes()).hexdigest(),
                "source_file": recipe["sample"],
                "archive_member_directory": sdk_folder(edition, recipe),
                "implementation_file": implementation,
                "app_architectures": recipe["app_architectures"],
                "needs_installed_driver": needs_driver,
                "opens_input_context": recipe["opens_input_context"],
                "starts_demo_timer": recipe["starts_demo_timer"],
                "result": ("Driver answered." if needs_driver
                           else "Library loaded. Keyboard slots: 10; mouse slots: 10."),
                "exit_codes": {
                    "0": "The driver answered a status query." if needs_driver else "The matching DLL classified its slots.",
                    "1": "The check failed. Read the diagnostic.",
                    **({"2": "Windows could not find the driver interface."} if needs_driver else {}),
                },
                "build_verification": {
                    "platform": "Windows x64 with Visual Studio 2022 C++ desktop tools and CMake 3.20+",
                    "command_from_portal_source": f"python scripts/test_first_sdk.py {slug} --run",
                    "scope": "Compile and run the documented first check. The build does not install a driver.",
                },
            },
        })
    return {
        "schema_version": 1,
        "reviewed": REVIEW_DATE,
        "project_catalogue_url": base + "projects.json",
        "source_repository": "https://github.com/TitanCSA/TitanCSA.github.io",
        "guides": {"en": base + "guides/installer-and-sdk/", "fr": base + "fr/installeur-et-sdk/"},
        "commercial_contact": {
            "platform": "Discord",
            "username": "titancsa",
            "contact_guide_url": base + "about/evidence/#release-contact",
        },
        "products": rows,
    }


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
        lines.append(
            f'<tr><th scope="row"><a href="{escape(row["overview_url"], quote=True)}">{escape(row["name"])}</a></th>'
            f'<td>{links[0]}</td><td>{sdk["api"]} · {architecture}<br>{links[1]} · {links[2]}</td></tr>'
        )
    return "\n".join(lines)
