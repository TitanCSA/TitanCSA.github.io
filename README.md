# TitanCSA project portal

Static, public project selection and first-run documentation for Windows applications and developer SDKs.

**Website:** https://titancsa.github.io/

The catalogue contains 60 curated project/SDK entries in ten workflows. It distinguishes application prerequisites, SDK-only sources and engineering previews. Known limits, including the open Vdevice controller teardown finding, remain visible. Package mirrors and account forks are not counted as separate finished products.

## Build

Python 3.10+ is sufficient; no third-party package is required for the build.

```text
python scripts/build.py
python scripts/validate.py
python -m http.server 8778 --bind 127.0.0.1 --directory dist
```

`projects.json` is curated from the public bilingual selection guide. The builder renders every project into HTML so navigation and documentation work without JavaScript. The browser script adds local search, filters and an optional stored theme preference. It sends no search queries to a server and adds no analytics code.

## Update a project

Check the current public README, release, licence and live-validation limits before editing the catalogue. Keep the exact repository link and one entry per product/SDK source. Do not promote an offline model or a preview into a live-supported feature without evidence. Update the checked date only after actually reviewing the changed content.

Guides are in `content/`; presentation and local interactions are in `src/`. The build goes to ignored `dist/`. GitHub Actions validates the output before deploying Pages. The website's source licence does not change any linked product's licence or driver distribution rights.

## Verification

`scripts/validate.py` checks data shape, unique project links, generated metadata, structured data, local links and file budgets. Browser QA checks desktop/mobile layouts, catalogue search/filter/reset behavior, preview warnings, theme switching and navigation without JavaScript. Those checks are distinct from product or driver qualification.

The initial social preview is generated from owned text and shapes; it makes no customer, certification or performance claim. Content and code are maintained with AI assistance.

`site-verification.json`, when present, contains the public Google ownership-verification meta value for this site. It is deliberately rendered in the homepage and is not an API credential. Preserve it for the existing site's verification; replace/remove it before deploying a fork to another website. Search Console ownership and sitemap submission do not guarantee indexing or rankings.

The same file contains a public IndexNow key. The builder publishes its verification file at the site root. Submit only URLs on this host after the updated pages are live.
