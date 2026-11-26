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
        "context": ".NET project directory",
    },
    "nuget-native": {
        "label": "C/C++",
        "runtime": "Visual Studio 2022 with Desktop development with C++",
        "command": "Install-Package {name} -Version {version}",
        "page": "https://www.nuget.org/packages/{name}/{version}",
        "metadata": "https://api.nuget.org/v3-flatcontainer/{lower_name}/index.json",
        "context": "Visual Studio Package Manager Console in a native Visual C++ project",
    },
    "powershell": {
        "label": "PowerShell",
        "runtime": "PowerShell 7.4+",
        "command": "Install-Module {name} -RequiredVersion {version} -Scope CurrentUser",
        "page": "https://www.powershellgallery.com/packages/{name}/{version}",
        "metadata": "https://www.powershellgallery.com/api/v2/Packages(Id='{name}',Version='{version}')",
    },
    "maven": {
        "label": "Java",
        "runtime": "JDK 22+ with Foreign Function and Memory API",
        "command": "mvn dependency:get -Dartifact={name}:{version}",
        "page": "https://central.sonatype.com/artifact/io.github.titancsa/{artifact}/{version}",
        "metadata": "https://repo.maven.apache.org/maven2/io/github/titancsa/{artifact}/{version}/{artifact}-{version}.pom",
        "context": "Maven CLI to fetch the package. Use the dependency XML in a project's pom.xml.",
    },
    "packagist": {
        "label": "PHP",
        "runtime": "PHP 8.2+ x64 with ext-ffi and the Windows Visual C++ v14 runtime",
        "command": "composer require {name}:{version}",
        "page": "https://packagist.org/packages/{name}",
        "metadata": "https://repo.packagist.org/p2/{name}.json",
    },
    "rubygems": {
        "label": "Ruby",
        "runtime": "Ruby 3.1+",
        "command": "gem install {name} -v {version}",
        "page": "https://rubygems.org/gems/{name}/versions/{version}",
        "metadata": "https://rubygems.org/api/v2/rubygems/{name}/versions/{version}.json",
    },
}

SECONDARY_REGISTRIES = ("maven", "packagist", "rubygems")


def runtime_reports(assets):
    """Read dated package reports from oldest to newest."""
    for path in sorted(assets.glob("sdk-registry-runtime-*.json")):
        if re.fullmatch(r"sdk-registry-runtime-\d{4}-\d{2}-\d{2}\.json", path.name):
            yield "assets/" + path.name, json.loads(path.read_text(encoding="utf-8"))


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
    lab_results = {}
    for proof_file, proof in runtime_reports(ROOT / "assets"):
        for observed in proof["checks"]:
            key = (observed["ecosystem"], observed["name"].casefold(), observed["version"])
            lab_results[key] = (proof_file, observed)
    seen = set()
    for row in rows:
        name, version = row["name"], row["version"]
        ecosystem = row["ecosystem"]
        key = (ecosystem, name.casefold(), version)
        namespace = {"maven": r"io\.github\.titancsa:", "packagist": "titancsa/"}.get(ecosystem, "")
        if (key in seen or not re.fullmatch(namespace + r"[A-Za-z0-9._-]+", name)
                or not re.fullmatch(r"\d+\.\d+\.\d+", version)):
            raise ValueError(f"Unexpected SDK package identity {key}")
        seen.add(key)
        registry = REGISTRIES[ecosystem]
        project = targets[row["edition"]]
        artifact = name.rsplit(":", 1)[-1]
        arguments = {"name": name, "version": version, "lower_name": name.lower(), "artifact": artifact}
        row.update(
            project=project,
            language=registry["label"],
            runtime=registry["runtime"],
            architectures=row.get("architectures", ["x64"]),
            package_url=registry["page"].format(**arguments),
            metadata_url=registry["metadata"].format(**arguments),
            install_command=registry["command"].format(**arguments),
            install_context=registry.get("context", registry["label"] + " environment"),
            install_includes_driver_or_application=False,
        )
        if ecosystem == "maven":
            row["dependency_xml"] = (
                "<dependency>\n  <groupId>io.github.titancsa</groupId>\n"
                f"  <artifactId>{artifact}</artifactId>\n  <version>{version}</version>\n</dependency>"
            )
        if lab := lab_results.get(key):
            proof_file, result = lab
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
        elif row["ecosystem"] == "pypi" and name == "interceptor-multilang":
            sample = "assets/python-interceptor-status.py"
            command = "python python-interceptor-status.py"
            row["first_check"]["after_setup_command_from_app_folder"] = command + " --status"
        elif row["ecosystem"] == "nuget-managed" and name == "Interceptor.MultiLang":
            sample = "assets/dotnet-interceptor-status.cs"
            command = "dotnet run --arch x64"
            row["first_check"].update(
                create_example_project_command="dotnet new console --framework net8.0 --output InterceptorSdkCheck",
                save_as="Program.cs",
            )
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


def secondary_registry_rows(rows, edition_order):
    packages = {(row["edition"], row["ecosystem"]): row for row in rows}
    table = []
    for edition in edition_order:
        project = packages[edition, "maven"]["project"]
        name = escape(project["name"])
        project_url = escape(project["url"], quote=True)
        cells = []
        for ecosystem in SECONDARY_REGISTRIES:
            row = packages[edition, ecosystem]
            label = escape(f'{row["name"]} {row["version"]}')
            url = escape(row["package_url"], quote=True)
            cells.append(f'<td><a href="{url}"><code>{label}</code></a></td>')
        table.append(f'<tr><th scope="row"><a href="{project_url}">{name}</a></th>{"".join(cells)}</tr>')
    return "\n".join(table)


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
