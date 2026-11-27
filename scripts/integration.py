"""Build the public integration manifest and the shared bilingual SDK table."""

from hashlib import sha256
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZIP_STORED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DATE = "2026-11-26"
WINDOWS_CXX_DEFINITIONS = ("UNICODE", "_UNICODE", "NOMINMAX")


def sdk_folder(edition, recipe):
    subdirectory = recipe["sdk_subdirectory"]
    if recipe["asset_role"] == "archive":
        return subdirectory
    archive_name = edition["demo_files"][recipe["asset_role"]]
    return f"{Path(archive_name).stem}/{subdirectory}"


def console_setup(asset_role, archive_member, installer_sha256, evidence_url):
    return {
        "asset_role": asset_role,
        "archive_member": archive_member,
        "installer_sha256": installer_sha256,
        "requires_administrator": True,
        "install_arguments": ["/install"],
        "uninstall_arguments": ["/uninstall"],
        "success_exit_codes": [0, 3010],
        "restart_required_exit_code": 3010,
        "restart_before_check": True,
        "evidence_url": evidence_url,
    }


def make_manifest(base, editions):
    recipes = json.loads((ROOT / "sdk-checks.json").read_text(encoding="utf-8"))
    if recipes.keys() != editions.keys():
        raise ValueError("Every driver edition needs one SDK check recipe")
    proof_file = "assets/demo-install-verification-2026-11-25.json"
    installed_evidence = json.loads((ROOT / proof_file).read_text(encoding="utf-8"))["editions"]
    inventory_file = "assets/interception-v2-install-verification-2026-11-25.json"
    inventory = json.loads((ROOT / inventory_file).read_text(encoding="utf-8"))
    audio_file = "assets/titan-audio-link-install-verification-2026-11-25.json"
    audio = json.loads((ROOT / audio_file).read_text(encoding="utf-8"))
    audio_hvci_file = "assets/titan-audio-link-memory-integrity-2026-11-26.json"
    audio_hvci = json.loads((ROOT / audio_hvci_file).read_text(encoding="utf-8"))
    vdevice_proof_file = "assets/vdevice-signed-versions-2026-11-25.json"
    vdevice_proof = json.loads((ROOT / vdevice_proof_file).read_text(encoding="utf-8"))
    mouse_switch_file = "assets/interceptor-mouse-driver-switch-2026-11-26.json"
    mouse_switch = json.loads((ROOT / mouse_switch_file).read_text(encoding="utf-8"))["editions"]
    keyboard_capture_file = "assets/interceptor-keyboard-mouse-two-keyboard-check-2026-11-26.json"
    keyboard_capture = json.loads((ROOT / keyboard_capture_file).read_text(encoding="utf-8"))
    keyboard_package = keyboard_capture["interceptor_keyboard_mouse"]
    audio_pair_file = "assets/titan-audio-link-sdk-pair-check-2026-11-26.json"
    audio_pair = json.loads((ROOT / audio_pair_file).read_text(encoding="utf-8"))
    python_wheels = {}
    for path in sorted((ROOT / "assets").glob("*-python-wheel-check-*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        python_wheels[report["edition"]] = (path.relative_to(ROOT).as_posix(), report)

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
            "purpose": edition["use"],
            "source": edition["repository"],
            "overview_url": edition["overview_url"],
            "first_run_guides": edition["first_run_guides"],
            "demo": {
                "version": edition["demo"],
                "tag": edition["tag"],
                "notes_url": edition["demo_url"],
                "setup_download_url": edition["demo_download_url"],
                "setup_download_sha256": digests[setup_role],
                "setup_format": "installer" if setup_role == "installer" else "zip",
                "setup_member": edition.get("setup_member"),
                "supported_driver_architecture": "x64",
                "trial_duration_minutes": 60,
                "trial_scope": "windows_kernel_boot",
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
                "compile_definitions": list(WINDOWS_CXX_DEFINITIONS) if implementation else [],
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
        if recipe["expected_after_setup"] != recipe["expected_without_driver"]:
            row["sdk_check"]["build_verification"]["command_after_setup"] = (
                f"python scripts/test_first_sdk.py {slug} --expect-installed")
        if (audio_pair["edition"] == slug and audio_pair["demo_tag"] == edition["tag"]
                and audio_pair["sdk_archive_sha256"] == edition["sdk_sha256"]
                and audio_pair["source_sha256"] == row["sdk_check"]["source_sha256"]):
            row["sdk_check"]["installed_validation_url"] = base + audio_pair_file
        if wheel_report := python_wheels.get(slug):
            python_wheel_file, python_wheel = wheel_report
            package = python_wheel["wheel"]
            source = python_wheel["source_file"]
            guides = {lang: url + "#python-sdk" for lang, url in row["first_run_guides"].items()}
            row["python_wheel"] = {
                **package,
                "python_requires": ">=3.10",
                "architecture": "x64",
                "install_command": f'python -m pip install "{package["url"]}#sha256={package["sha256"]}"',
                "source_url": base + "assets/" + source,
                "source_sha256": python_wheel["source_sha256"],
                "check_command": " ".join(("python", source, *python_wheel.get("check_args", []))),
                "tested_demo_version": python_wheel["driver_demo"]["version"],
                "tested_demo_tag": python_wheel["driver_demo"]["tag"],
                "guide_urls": guides,
                "evidence_url": base + python_wheel_file,
            }
            if "inventory" in python_wheel:
                row["python_wheel"]["installed_inventory"] = {
                    "command": f"python {source} --inventory",
                    "starts_demo_timer": True,
                }
        proof = installed_evidence.get(slug)
        if (proof and proof["version"] == edition["demo"]
                and proof["sdk_archive_sha256"] == edition["sdk_sha256"]
                and proof["installer_url"] == edition["demo_assets"].get("console_installer")
                and proof["installer_sha256"] == digests.get("console_installer")):
            row["demo"]["read_only_install_verification"] = {"url": base + proof_file, "edition": slug}
            row["demo"]["console_setup"] = console_setup(
                "console_installer", None, proof["installer_sha256"], base + proof_file)
            row["sdk_check"]["tested_account"] = "Administrator on Windows 11 x64"
        switch = mouse_switch.get(slug)
        if (switch and switch["tag"] == edition["tag"]
                and switch["sdk_sha256"] == edition["sdk_sha256"]
                and switch["console_installer_sha256"] == digests.get("console_installer")):
            row["demo"]["mouse_driver_switch_verification_url"] = base + mouse_switch_file
        if (keyboard_capture["edition"] == slug and keyboard_package["demo_tag"] == edition["tag"]
                and keyboard_package["sdk_archive_sha256"] == edition["sdk_sha256"]
                and keyboard_package["console_installer_sha256"] == digests.get("console_installer")):
            row["demo"]["keyboard_capture_verification_url"] = base + keyboard_capture_file
        if (inventory["edition"] == slug and inventory["demo_version"] == edition["demo"]
                and inventory["demo_archive"]["sha256"] == digests[setup_role]):
            row["demo"]["console_setup"] = console_setup(
                "archive", edition["setup_member"], inventory["demo_archive"]["bundled_installer_sha256"],
                base + inventory_file)
            row["demo"]["live_inventory_verification"] = {
                "url": base + inventory_file,
                "sample_source_url": inventory["sample"]["source_url"],
                "app_architectures": app_architectures,
                "opens_input_context": True,
            }
        audio_archive = audio["demo_archive"]
        if (audio["edition"] == slug and audio["demo_version"] == edition["demo"]
                and audio_archive["sha256"] == digests[setup_role]):
            row["demo"]["console_setup"] = console_setup(
                "archive", audio_archive["bundled_installer_member"], audio_archive["bundled_installer_sha256"],
                base + audio_file)
            if (audio_hvci["edition"] == slug and audio_hvci["demo_version"] == edition["demo"]
                    and audio_hvci["environment"]["memory_integrity"] is True
                    and audio_hvci["demo_archive"] == audio_archive
                    and audio_archive["url"] == edition["demo_download_url"]):
                row["demo"]["installer_verification_url"] = base + audio_hvci_file
                row["demo"]["console_setup"]["evidence_url"] = base + audio_hvci_file
        if slug == vdevice_proof["project"]:
            verified_demo = vdevice_proof["versions"]["demo"]
            qualified_installers = {record["installer"]: record["installer_sha256"]
                                    for record in verified_demo["installer_qualification"]}
            if (verified_demo["package_version"] == edition["demo"]
                    and verified_demo["public_notes_url"] == edition["demo_url"]
                    and verified_demo["signed_driver_archive_sha256"] == digests.get("driver")
                    and qualified_installers.get("graphical") == digests[setup_role]
                    and qualified_installers.get("console") == digests.get("console_installer")):
                row["demo"]["installer_verification_url"] = base + vdevice_proof_file
                lab = verified_demo.get("secure_boot_read_only_lab", {})
                if (lab.get("sdk_archive_sha256") == edition["sdk_sha256"]
                        and lab.get("installer_sha256") == digests.get("console_installer")):
                    row["sdk_check"]["tested_account"] = "Administrator on Windows 11 x64"
            commercial = edition["commercial"]
            verified_release = vdevice_proof["versions"]["release"]
            if all(verified_release[key] == commercial[key] for key in ("package_version", "driver_version")):
                row["commercial_install_verification"] = {"url": base + vdevice_proof_file, **commercial}
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
            "purchase_details_shared_privately": True,
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


def python_status_wheel_details(wheel, language):
    if language == "fr":
        title = "Vérifier le pilote avec Python"
        intro = ('Utilise Python 3.10 ou plus récent en 64 bits sous Windows. Place le {package} et le {sample} '
                 'dans le même dossier, puis ouvre PowerShell dans ce dossier.')
        status = ('Avec la démo {demo}, <code>installed: true</code> confirme que le pilote de cette édition répond. '
                  'Sur une installation neuve, <code>trial_state: 0</code> indique que le compteur est encore arrêté. '
                  'Windows 2 indique que le script ne trouve pas le pilote de cette édition.')
        package, sample, report = "paquet Python", "script", "Tests et SHA-256 du paquet"
    else:
        title = "Check the driver from Python"
        intro = ('Use 64-bit Python 3.10 or later on Windows. Put the {package} and {sample} in the same folder, '
                 'then open PowerShell there.')
        status = ('With demo {demo}, <code>installed: true</code> means the driver for this edition answered. '
                  'On a fresh install, <code>trial_state: 0</code> means its demo timer is still unstarted. '
                  'Windows error 2 means the script could not find this edition’s driver.')
        package, sample, report = "Python wheel", "check script", "Test results and wheel SHA-256"
    package_link = f'<a href="{escape(wheel["url"], quote=True)}">{package}</a>'
    source = "/" + urlsplit(wheel["source_url"]).path.lstrip("/")
    sample_link = f'<a href="{escape(source, quote=True)}" download>{sample}</a>'
    install = 'python -m pip install .\\' + wheel["filename"]
    return (
        f'<details class="more-info"><summary>{title}</summary><div id="python-sdk">'
        f'<p>{intro.format(package=package_link, sample=sample_link)}</p>'
        f'<pre><code>{escape(install)}\n{escape(wheel["check_command"])}</code></pre>'
        f'<p>{status.format(demo=escape(wheel["tested_demo_version"]))}</p>'
        f'<p><a href="{escape(wheel["evidence_url"], quote=True)}">{report}</a></p></div></details>'
    )


def first_sdk_check(product, starter_url, language):
    sdk = product["sdk_check"]
    package_link = f'https://github.com/TitanCSA/sdk-packages/tree/main/projects/{product["source"].rsplit("/", 1)[-1]}#readme'
    command = escape(sdk["build_verification"]["command_from_starter_zip"])
    installed_command = sdk["build_verification"].get("command_after_setup")
    result = escape(sdk["expected_after_setup"]["output_contains"])
    driver_needed = sdk["needs_installed_driver"]
    if language == "fr":
        title, download, reference = "Compiler le premier test SDK", "ZIP de départ", "Documentation du SDK"
        requirements = "Sous Windows, installe Visual Studio 2022 avec les outils C++, CMake 3.20+ et Python 3.10+."
        setup = "Installe la démo ci-dessus. " if driver_needed else ""
        instructions = "Décompresse le ZIP et ouvre PowerShell dans le dossier extrait."
        outcome = "Résultat attendu après installation" if installed_command else "Résultat attendu"
        verify_setup = "Pour exiger le résultat après installation, lance"
    else:
        title, download, reference = "Build the first SDK check", "Starter ZIP", "SDK documentation"
        requirements = "On Windows, install Visual Studio 2022 with the C++ desktop tools, CMake 3.20+, and Python 3.10+."
        setup = "Install the demo above. " if driver_needed else ""
        instructions = "Extract the ZIP and open PowerShell in the extracted folder."
        outcome = "Expected after installation" if installed_command else "Expected result"
        verify_setup = "To require the post-install result, run"
    installed_check = (
        f'<p>{verify_setup} <code>{escape(installed_command)}</code>.</p>' if installed_command else "")
    return (
        f'<details class="more-info"><summary>{title}</summary><div id="first-sdk-check">'
        f'<p>{requirements} {setup}{instructions}</p>'
        f'<p><a href="{escape(starter_url, quote=True)}">{download}</a></p>'
        f'<pre><code>{command}</code></pre>{installed_check}'
        f'<p>{outcome} <code>{result}</code></p>'
        f'<p><a href="{escape(package_link, quote=True)}">{reference}</a></p></div></details>'
    )


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


def write_sdk_reference(path, base, manifest, language):
    if language == "fr":
        title = "Pilotes et SDK Windows TitanCSA"
        intro = ("Choisis ton édition. L’installateur ajoute le pilote à Windows. "
                 "Le SDK donne le code et les bibliothèques pour créer ta propre application.")
        guide, download, archive, source = "Guide de premier essai", "Démo signée", "Archive SDK", "Code du test"
        starter = "Pour compiler le premier test natif, décompresse le ZIP de départ et lance la commande de ton édition."
        starter_label = "ZIP de départ"
        checks = "Ces tests n’ouvrent pas de capture et ne démarrent pas le compteur de la démo."
        member_label, after, before = "Installateur dans le ZIP", "Après installation", "Sans pilote installé"
        contact = "Version sans la limite d’une heure · contacte titancsa sur Discord"
        contact_url = base + "fr/pilotes-entree-windows/#contact-release"
    else:
        title = "TitanCSA Windows drivers and SDKs"
        intro = ("Choose your edition. The installer adds its driver to Windows. "
                 "The SDK supplies the code and libraries to write your own application.")
        guide, download, archive, source = "First-run guide", "Signed demo", "SDK archive", "Test source"
        starter = "To build the first native check, extract the starter ZIP and run the command for your edition."
        starter_label = "Starter ZIP"
        checks = "These checks leave input capture closed and the demo timer unstarted."
        member_label, after, before = "Installer inside the ZIP", "After setup", "With no driver installed"
        contact = "Release without the one-hour demo limit · contact titancsa on Discord"
        contact_url = manifest["commercial_contact"]["contact_guide_url"]
    lines = [
        f"# {title}", "", intro, "",
        f"[{starter_label}]({manifest['starter_zip_url']}) · [integration.json]({base}integration.json)",
        "", starter, checks,
    ]
    for product in manifest["products"]:
        demo, sdk = product["demo"], product["sdk_check"]
        architectures = " / ".join(sdk["app_architectures"])
        lines.extend([
            "", f"## {product['name']}", "",
            f"- [{guide}]({product['first_run_guides'][language]})",
            f"- [{download} {demo['version']}]({demo['setup_download_url']}) · SHA-256 `{demo['setup_download_sha256']}`",
            f"- [{archive}]({sdk['archive_url']}) · {sdk['api']} · {architectures} · SHA-256 `{sdk['archive_sha256']}`",
            f"- [{source}]({sdk['source_url']})",
            f"- `{sdk['build_verification']['command_from_starter_zip']}`",
        ])
        if demo["setup_member"]:
            lines.append(f"- {member_label} `{demo['setup_member']}`")
        installed = sdk["expected_after_setup"]
        clean = sdk["expected_without_driver"]
        if clean == installed:
            lines.append(f"- {before} · `{clean['output_contains']}`")
        else:
            installed_command = sdk["build_verification"]["command_after_setup"]
            lines.append(f"- {after} · `{installed_command}` → `{installed['output_contains']}`")
            lines.append(f"- {before} · `{clean['output_contains']}`")
    lines.extend(["", f"[{contact}]({contact_url})", ""])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


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
    # Generated JSON and Git checkouts can use CRLF locally. Store canonical LF
    # for the starter metadata and scripts so its checksum is reproducible.
    items = {name: path.read_bytes().replace(b"\r\n", b"\n") for name, path in files.items()}
    for row in manifest["products"]:
        source = "assets/" + row["sdk_check"]["source_file"]
        items[source] = (ROOT / source).read_bytes()
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
