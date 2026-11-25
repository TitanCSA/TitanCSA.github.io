"""Generate the registry install table and the exact package integration data."""

from html import escape
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {
    "npm": {
        "label": "Node.js",
        "runtime": "Node.js 20+",
        "command": "npm install {name}@{version}",
        "page": "https://www.npmjs.com/package/{name}/v/{version}",
        "metadata": "https://registry.npmjs.org/{name}/{version}",
    },
    "pypi": {
        "label": "Python",
        "runtime": "Python 3.10+",
        "command": "python -m pip install {name}=={version}",
        "page": "https://pypi.org/project/{name}/{version}/",
        "metadata": "https://pypi.org/pypi/{name}/{version}/json",
    },
    "nuget-managed": {
        "label": ".NET",
        "runtime": ".NET 8+",
        "command": "dotnet add package {name} --version {version}",
        "page": "https://www.nuget.org/packages/{name}/{version}",
        "metadata": "https://api.nuget.org/v3-flatcontainer/{lower_name}/index.json",
    },
    "nuget-native": {
        "label": "C/C++",
        "runtime": "Visual Studio 2022 with Desktop development with C++",
        "command": "Install-Package {name} -Version {version}",
        "page": "https://www.nuget.org/packages/{name}/{version}",
        "metadata": "https://api.nuget.org/v3-flatcontainer/{lower_name}/index.json",
    },
    "powershell": {
        "label": "PowerShell",
        "runtime": "PowerShell 7.4+",
        "command": "Install-Module {name} -RequiredVersion {version} -Scope CurrentUser",
        "page": "https://www.powershellgallery.com/packages/{name}/{version}",
        "metadata": "https://www.powershellgallery.com/api/v2/Packages(Id='{name}',Version='{version}')",
    },
}


def registry_catalogue(manifest, base):
    targets = {
        row["id"]: {"name": row["name"], "url": row["overview_url"], "type": "driver",
                    "demo_url": row["demo"]["notes_url"], "demo_version": row["demo"]["version"]}
        for row in manifest["products"]
    }
    browser = next(row for row in manifest["applications"] if row["id"] == "browser")
    targets["browser"] = {"name": browser["name"], "type": "windows_app",
                          "url": base + "guides/first-run/#browser",
                          "release_url": browser["source"] + "/releases/tag/" + browser["tag"]}
    rows = json.loads((ROOT / "sdk-registry.json").read_text(encoding="utf-8"))
    proof_file = "assets/sdk-registry-runtime-2026-11-25.json"
    evidence = json.loads((ROOT / proof_file).read_text(encoding="utf-8"))["checks"]
    lab_results = {(row["ecosystem"], row["name"].casefold(), row["version"]): row for row in evidence}
    seen = set()
    for row in rows:
        name, version = row["name"], row["version"]
        key = (row["ecosystem"], name.casefold(), version)
        if (key in seen or not re.fullmatch(r"[A-Za-z0-9._-]+", name)
                or not re.fullmatch(r"\d+\.\d+\.\d+", version)):
            raise ValueError(f"Unexpected SDK package identity {key}")
        seen.add(key)
        registry = REGISTRIES[row["ecosystem"]]
        project = targets[row["edition"]]
        row.update(
            project=project,
            language=registry["label"],
            runtime=registry["runtime"],
            architectures=row.get("architectures", ["x64"]),
            package_url=registry["page"].format(name=name, version=version),
            metadata_url=registry["metadata"].format(name=name, lower_name=name.lower(), version=version),
            install_command=registry["command"].format(name=name, version=version),
            install_context=(".NET project directory" if row["ecosystem"] == "nuget-managed" else
                             "Visual Studio Package Manager Console in a native Visual C++ project"
                             if row["ecosystem"] == "nuget-native" else registry["label"] + " environment"),
            install_includes_driver_or_application=False,
        )
        if result := lab_results.get(key):
            if result["edition"] != row["edition"]:
                raise ValueError(f"Lab result uses a different edition for {name}")
            row["lab_verification"] = {
                "source_url": base + proof_file,
                "driver_version": result["driver_version"],
                "runtime": result["runtime"],
            }
        if row["ecosystem"] == "npm":
            sample = "assets/node-sdk-status.cjs"
            command = f'node node-sdk-status.cjs {row["edition"]}'
        elif row["ecosystem"] == "powershell":
            sample = "assets/gallery-sdk-status.ps1"
            command = f'pwsh -NoProfile -File .\\gallery-sdk-status.ps1 -Module {name}'
        else:
            sample = None
        if sample:
            row["first_check"].update(
                source_url=base + sample,
                source_sha256=sha256((ROOT / sample).read_bytes()).hexdigest(),
                command_from_app_folder=command,
            )
        if row["edition"] == "browser":
            row["first_check"].update(
                source_url=browser["test"]["source_url"],
                source_sha256=browser["test"]["source_sha256"],
                command_from_app_folder="python browser-sdk-first-run.py --installed-client",
            )
    return rows


def registry_tables(rows, *, french=False):
    labels = ("Projet", "Paquet", "Commande") if french else ("Project", "Package", "Install command")
    columns = "".join(f'<th scope="col">{label}</th>' for label in labels)
    sections = []
    for key in ("nuget-native", "pypi", "npm", "nuget-managed", "powershell"):
        registry = REGISTRIES[key]
        language = registry["label"]
        runtime = registry["runtime"]
        if key == "nuget-native" and french:
            runtime = "Visual Studio 2022 avec le développement de bureau en C++"
        table = []
        for row in (item for item in rows if item["ecosystem"] == key):
            name = escape(row["project"]["name"])
            project_url = escape(row["project"]["url"], quote=True)
            package = escape(row["name"]) + " " + escape(row["version"])
            package_url = escape(row["package_url"], quote=True)
            command = escape(row["install_command"])
            table.append(
                f'<tr><th scope="row"><a href="{project_url}">{name}</a></th>'
                f'<td><a href="{package_url}">{package}</a></td><td><code>{command}</code></td></tr>'
            )
        sections.append(f'<details class="first-run-more"><summary>{language}</summary><p>{escape(runtime)}</p>'
                        f'<div class="table-scroll"><table><thead><tr>{columns}</tr></thead>'
                        '<tbody>' + "\n".join(table) + '</tbody></table></div></details>')
    return "\n".join(sections)
