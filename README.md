# TitanCSA project portal

Static, public project selection and first-run documentation for Windows applications and developer SDKs.

> [!IMPORTANT]
> **Full driver without the one-hour demo limit**
> Add **`titancsa`** on [Discord](https://discord.com/app) and send the project name. TitanCSA shares the purchase details privately.

**Website:** https://titancsa.github.io/

Follow updates with the [guide RSS feed](https://titancsa.github.io/rss.xml) or the [French RSS feed](https://titancsa.github.io/fr/rss.xml).

The catalogue groups project and SDK entries by what users want to do. It distinguishes application prerequisites, SDK-only sources and engineering previews. Known limits, including the Vdevice controller teardown report and its fix, remain visible. Package mirrors and account forks are not counted as separate finished products.

## Build

Python 3.10+ is sufficient; no third-party package is required for the build.

```text
python scripts/build.py
python scripts/validate.py
python -m http.server 8778 --bind 127.0.0.1 --directory dist
```

`projects.json` is curated from the public selection guide. `projects.fr.json` supplies the French purpose and first step for each entry. Both homepages show the same projects, and the build calculates the totals from these records. The published catalogue JSON includes both languages, and local search accepts keywords in either language. All links work with JavaScript disabled.

## Update a project

Check the current public README, release, licence and live-validation limits before editing the catalogue. Keep the exact repository link and one entry per product/SDK source. Do not promote an offline model or a preview into a live-supported feature without evidence. Update the checked date only after actually reviewing the changed content.

Guides are in `content/`; presentation and local interactions are in `src/`. The build goes to ignored `dist/`. GitHub Actions validates the output before deploying Pages. The website's source licence does not change any linked product's licence or driver distribution rights.

## Update a published SDK example

The [public integration manifest](https://titancsa.github.io/integration.json) lists the setup download, SDK archive, app architectures, exact first check and expected output. Its bilingual download table and JSON use the same source data.

Each `sdk_registry` entry has `guide_urls.en` and `guide_urls.fr` linking to the exact package in the installation tables. Use `documentation_url` when available for that package's API instructions.

Each driver product's `first_run_guides` links to its English and French demo instructions. Use `overview_url` for the general product page.

When a version has a verified console setup, `demo.console_setup` gives the asset role, any path inside its ZIP, the executable SHA-256, install and uninstall arguments, restart handling and the test record. Run setup with administrator approval in a separate test environment before querying the installed driver.

The [JSON schema](https://titancsa.github.io/integration.schema.json) defines the fields used by tools consuming the manifest. Both files also ship in the portable starter ZIP. Keep existing fields compatible when adding an optional detail.

Update the approved tag, demo version, asset filenames and SHA-256 values in releases.json. The build derives the native SDK folder from the archive's filename. The file sdk-checks.json holds the sample layout and supported app architectures, which only change when the integration changes.

To preview a proposed update, run the release checker with the edition ID, public GitHub tag and driver version. The command prints the exact metadata without changing files.

    python scripts/verify_release_assets.py --candidate interceptor v1.4.23.0-demo-r3 1.4.23.0

The GitHub tag identifies the exact publication even when a revision retains the same Windows driver version.

Use --asset role=filename when the new release changes a filename's pattern. The pipeline checks the URL and pinned SHA-256 of each asset against GitHub. Its Windows job builds and runs every listed architecture.

Add `--apply` to save the verified candidate to `releases.json`. The command leaves the other editions and commercial metadata in place. Rebuild and run the validation commands below before submitting the change.

Add `--verify-downloads` to fetch the public files and hash their actual bytes. Without a candidate, this checks the entire driver and application catalogue.

The [Audit published downloads](https://github.com/TitanCSA/TitanCSA.github.io/actions/workflows/public-release-audit.yml) workflow runs daily at 04:37 UTC. It checks the pinned release assets against GitHub metadata, hashes both public Rust quickstarts and checks the SDK versions and documentation. Run it on demand with `verify_downloads` to download and hash every pinned file. Results are reported in GitHub Actions.

If an existing release replaces a file, the check reports the filename and leaves the pin in place. Compare the new download with the previously verified package before applying the candidate. For an installer, verify the signed driver files and repeat the install and removal checks. The integration manifest links to console installer evidence only while its exact SHA-256 and SDK match the catalogue.

```text
python scripts/build.py
python scripts/validate.py
python scripts/verify_release_assets.py
python scripts/verify_registry.py --documentation
python scripts/test_first_sdk.py all --expect-clean
```

Run the last command on a Windows x64 host with Visual Studio 2022 C++ desktop tools and CMake 3.20 or later. For a host with the corresponding driver already installed, use `python scripts/test_first_sdk.py <edition> --run`. It queries status without installing a driver or starting a demo.

On Windows x64 with Node.js and npm, run `python scripts/verify_registry.py --check-node-on-clean-windows` to test the published JavaScript examples on a system without the Interceptor demo drivers. CI runs this check with Node.js 24.

Run `python scripts/compile_documented_samples.py` to compile the Vdevice HID example, both architectures of the Interception V2 hardware-ID example, and the read-only HID driver list for Interceptor and Keyboard & Mouse. The check only builds these examples. The dated lab records still point to the versions they originally tested.

Update `starter-apps.json` after checking a new app's released ZIP and exact first run. Update `sdk-registry.json` after confirming that its version is installable from the named registry. The site generates both languages from those records and checks the public links and hashes in CI.

## Verification

`scripts/validate.py` checks data shape, unique project links, generated metadata, structured data, local links and file budgets. Browser QA checks desktop/mobile layouts, catalogue search/filter/reset behavior, preview warnings, theme switching and navigation without JavaScript. Those checks are distinct from product or driver qualification.

Project share images use the portal colours and project names. To regenerate them after an edit, run `python scripts/render_social_previews.py` on Windows with Playwright and Chrome. The deployment uses the PNGs in `assets/`. Content and code are maintained with AI assistance.

`site-verification.json`, when present, contains the public Google ownership-verification meta value for this site. It is deliberately rendered in the homepage and is not an API credential. Preserve it for the existing site's verification; replace/remove it before deploying a fork to another website. Search Console ownership and sitemap submission do not guarantee indexing or rankings.

The build generates `sitemap.xml` and a plain-text `sitemap.txt` from the same canonical pages. Search Console accepts either format.

The same file contains a public IndexNow key. The builder publishes its verification file at the site root. Submit only URLs on this host after the updated pages are live.
