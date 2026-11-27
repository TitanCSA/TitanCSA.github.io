"""Generate the registry install table and the exact package integration data."""

from html import escape
from hashlib import sha256
from pathlib import Path
import json
import re
from urllib.parse import urlsplit

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
    "cargo": {
        "label": "Rust",
        "runtime": "Rust 1.82+ with the Windows x64 MSVC toolchain",
        "command": "cargo add {name}@={version} serde_json@1",
        "page": "https://crates.io/crates/{name}/{version}",
        "metadata": "https://crates.io/api/v1/crates/{name}/{version}",
        "context": "A Cargo project directory with Cargo.toml",
    },
    "go": {
        "label": "Go",
        "runtime": "Go 1.22+ on Windows x64, without cgo",
        "command": "go get {name}@v{version}",
        "page": "https://pkg.go.dev/{name}@v{version}",
        "metadata": "https://proxy.golang.org/{proxy_name}/@v/v{version}.info",
        "context": "Go module directory with a go.mod file",
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
PACKAGE_GUIDES = {
    "primary": {"en": "guides/windows-input-sdk-packages/", "fr": "fr/installer-sdk-windows/"},
    "secondary": {"en": "guides/windows-input-sdk-java-php-ruby/", "fr": "fr/sdk-java-php-ruby/"},
}


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
    browser_proof_file = "assets/browser-python-first-run-2026-11-27.json"
    browser_proof = json.loads((ROOT / browser_proof_file).read_text(encoding="utf-8"))
    targets["browser"] = {"name": browser["name"], "type": "windows_app",
                          "url": base + "guides/first-run/#browser",
                          "release_url": browser["source"] + "/releases/tag/" + browser["tag"]}
    rows = json.loads((ROOT / "sdk-registry.json").read_text(encoding="utf-8"))
    clean_checks = {}
    for ecosystem, proof_file in (
        ("go", "assets/go-sdk-first-checks-2026-11-26.json"),
        ("cargo", "assets/rust-sdk-first-checks-2026-11-26.json"),
    ):
        proof = json.loads((ROOT / proof_file).read_text(encoding="utf-8"))
        for result in proof["checks"]:
            clean_checks[(ecosystem, result["name"], result["version"])] = (proof_file, result)
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
        namespace = {"maven": r"io\.github\.titancsa:", "packagist": "titancsa/",
                     "go": r"github\.com/(?:TitanCSA|titanfyre)/[A-Za-z0-9._-]+/"}.get(ecosystem, "")
        if (key in seen or not re.fullmatch(namespace + r"[A-Za-z0-9._-]+", name)
                or not re.fullmatch(r"\d+\.\d+\.\d+", version)):
            raise ValueError(f"Unexpected SDK package identity {key}")
        seen.add(key)
        registry = REGISTRIES[ecosystem]
        project = targets[row["edition"]]
        anchor = "package-" + ecosystem + "-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        guides = PACKAGE_GUIDES["secondary" if ecosystem in SECONDARY_REGISTRIES else "primary"]
        artifact = name.rsplit(":", 1)[-1]
        arguments = {"name": name, "version": version, "lower_name": name.lower(), "artifact": artifact}
        if ecosystem == "go":
            arguments["proxy_name"] = "".join("!" + char.lower() if "A" <= char <= "Z" else char for char in name)
        if clean_check := clean_checks.get((ecosystem, name, version)):
            proof_file, proof = clean_check
            if proof["edition"] == row["edition"] and proof["package_sha256"] == row["verified_archive"]["sha256"]:
                row["first_check"]["without_driver_evidence_url"] = base + proof_file
        row.update(
            project=project,
            language=registry["label"],
            runtime=registry["runtime"],
            architectures=row.get("architectures", ["x64"]),
            package_url=registry["page"].format(**arguments),
            guide_urls={locale: f"{base}{route}#{anchor}" for locale, route in guides.items()},
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
            if (browser_proof["wheel"]["version"] == version
                    and browser_proof["wheel"]["sha256"] == row["verified_archive"]["sha256"]
                    and browser_proof["application"]["archive_sha256"] == browser["sha256"]
                    and browser_proof["source_sha256"] == row["first_check"]["source_sha256"]):
                row["first_check"]["application_test_evidence_url"] = base + browser_proof_file
    return rows


def package_documentation_link(row, french):
    if url := row.get("documentation_url"):
        label = "Guide SDK" if french else "SDK guide"
        return f'<br><a href="{escape(url, quote=True)}">{label}</a>'
    return ""


def secondary_registry_rows(rows, edition_order, *, french=False):
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
            anchor = urlsplit(row["guide_urls"]["en"]).fragment
            guide = package_documentation_link(row, french)
            cells.append(f'<td id="{anchor}"><a href="{url}"><code>{label}</code></a>{guide}</td>')
        table.append(f'<tr><th scope="row"><a href="{project_url}">{name}</a></th>{"".join(cells)}</tr>')
    return "\n".join(table)


def registry_tables(rows, *, french=False, rust_quickstarts=()):
    labels = ("Projet", "Paquet", "Commande") if french else ("Project", "Package", "Install command")
    columns = "".join(f'<th scope="col">{label}</th>' for label in labels)
    sections = []
    for key in ("nuget-native", "pypi", "npm", "nuget-managed", "powershell", "go", "cargo"):
        registry = REGISTRIES[key]
        language = registry["label"]
        runtime = registry["runtime"]
        if key == "nuget-native" and french:
            runtime = "Visual Studio 2022 avec le développement de bureau en C++"
        if key == "go" and french:
            runtime = "Go 1.22 ou supérieur sous Windows x64, sans cgo"
        if key == "cargo" and french:
            runtime = "Rust 1.82 ou supérieur avec la chaîne MSVC sous Windows x64"
        table = []
        for row in (item for item in rows if item["ecosystem"] == key):
            name = escape(row["project"]["name"])
            project_url = escape(row["project"]["url"], quote=True)
            package = escape(row["name"]) + " " + escape(row["version"])
            package_url = escape(row["package_url"], quote=True)
            command = escape(row["install_command"])
            anchor = urlsplit(row["guide_urls"]["en"]).fragment
            guide = package_documentation_link(row, french)
            sample = ""
            if key in ("go", "cargo"):
                check = row["first_check"]
                source = escape(urlsplit(check["source_url"]).path, quote=True)
                filename = escape(check["save_as"], quote=True)
                label = f"Fichier {filename}" if french else f"Download {filename}"
                sample = f'<br><a href="{source}" download="{filename}">{label}</a>'
            table.append(
                f'<tr id="{anchor}"><th scope="row"><a href="{project_url}">{name}</a></th>'
                f'<td><a href="{package_url}">{package}</a>{guide}</td><td><code>{command}</code>{sample}</td></tr>'
            )
        steps = ""
        if key == "go":
            instructions = ("Dans un dossier vide, lance <code>go mod init example.com/titancsa-check</code>. "
                            "Copie la commande du tableau, enregistre le fichier sous <code>main.go</code> "
                            "puis lance <code>go run .</code>.") if french else (
                            "In an empty folder, run <code>go mod init example.com/titancsa-check</code>. "
                            "Copy the command from the table, save its sample as <code>main.go</code> "
                            "and run <code>go run .</code>.")
            steps = f"<p>{instructions}</p>"
        if key == "cargo":
            instructions = ("Lance <code>cargo new titancsa-check --vcs none</code>, puis <code>cd titancsa-check</code>. "
                            "Copie la commande du tableau, remplace <code>src/main.rs</code> par le fichier téléchargé "
                            "et lance <code>cargo run</code>. Si tu distribues le fichier <code>.exe</code>, "
                            "place la DLL du paquet à côté.") if french else (
                            "Run <code>cargo new titancsa-check --vcs none</code>, then <code>cd titancsa-check</code>. "
                            "Copy the command from the table, replace <code>src/main.rs</code> with its sample "
                            "and run <code>cargo run</code>. When distributing the <code>.exe</code>, "
                            "place the crate’s DLL beside it.")
            steps = f"<p>{instructions}</p>"
        bundles = ""
        if key == "cargo" and rust_quickstarts:
            links = " · ".join(f'<a href="{escape(item["download_url"], quote=True)}">{escape(item["name"])}</a>'
                               for item in rust_quickstarts)
            instructions = ("Exemples ZIP prêts à lancer. Décompresse le ZIP et lance <code>cargo run --locked</code> "
                            "dans son dossier.") if french else ("Standalone ZIP examples. Extract the ZIP and run "
                            "<code>cargo run --locked</code> in its folder.")
            bundles = f'<p id="rust-quickstarts">{instructions}</p><p>{links}</p>'
        sections.append(f'<details class="first-run-more"><summary>{language}</summary><p>{escape(runtime)}</p>{steps}'
                        f'<div class="table-scroll"><table><thead><tr>{columns}</tr></thead>'
                        '<tbody>' + "\n".join(table) + f'</tbody></table></div>{bundles}</details>')
    return "\n".join(sections)
