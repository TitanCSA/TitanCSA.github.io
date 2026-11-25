"""Render the same project catalogue in English and French."""

from collections import defaultdict
from html import escape
import re


KIND_FR = {
    "Application": "Application",
    "Dataset": "Résultats de tests",
    "Driver SDK": "Pilote + SDK",
    "Preview": "Aperçu",
    "SDK sources": "Code SDK",
}


def catalogue_sections(projects, french_copy, featured_paths, app_sections, *, french=False):
    groups = defaultdict(list)
    for project in projects:
        groups[project["category"]].append(project)

    cards, options, jumps = [], [], []
    for category, entries in groups.items():
        title = french_copy["categories"][category] if french else entries[0]["category_title"]
        category = escape(category, quote=True)
        options.append(f'<option value="{category}">{escape(title)}</option>')
        jumps.append(f'<a href="#{category}" data-category-jump>{escape(title)}</a>')
        items = []
        for entry in entries:
            name = entry["name"]
            purpose_fr, step_fr = french_copy["projects"][name]
            purpose = purpose_fr if french else entry["plain_purpose"]
            first_step = step_fr if french else entry["plain_first_step"]
            searchable = " ".join((name, entry["description"], entry["plain_purpose"], entry["plain_first_step"],
                                   purpose_fr, step_fr, title, entry["kind"]))
            preview = entry["kind"] == "Preview"
            kind = KIND_FR[entry["kind"]] if french else entry["kind"]
            tag = "tag preview" if preview else "tag"
            no_driver = entry["start_without_adding_driver"]
            mode = "Sans nouveau pilote" if french else entry["start_mode"]
            badge = f'<span class="start-tag">{escape(mode)}</span>' if no_driver else ""
            scope = ""
            if preview and not french:
                scope = f'<p>{escape(entry["first_step"])}</p>'
            if preview and french and category == "virtual-usb":
                scope = "<p>Le code est disponible pour étude. Aucun binaire utilisable n’est publié pour cet aperçu.</p>"
            issue = ""
            if entry["known_issue_url"]:
                label = "État du problème WDF-001" if french else "WDF-001 status by edition"
                issue = f'<a class="known-issue" href="{escape(entry["known_issue_url"], quote=True)}">{label} ↗</a>'
            overview = featured_paths.get(name)
            if name in app_sections:
                guide = "/fr/essayer-sans-pilote/" if french else "/guides/first-run/"
                overview = f'{guide}#{app_sections[name]}'
            overview_label = ("Voir le premier essai" if name in app_sections else "Voir la fiche") if french else (
                "See the first run" if name in app_sections else "Project overview"
            )
            overview_link = f'<p><a href="{escape(overview, quote=True)}">{overview_label}</a></p>' if overview else ""
            ident = "project-" + re.sub(r"[^a-z0-9-]", "-", name.lower())
            url = escape(entry["url"], quote=True)
            label = "Premier essai" if french else "First step"
            items.append(
                f'<article id="{ident}" class="project" data-project data-category="{category}" '
                f'data-no-driver="{str(no_driver).lower()}" data-search="{escape(searchable, quote=True)}">'
                f'<div class="project-title"><h3><a href="{url}">{escape(name)} <span aria-hidden="true">↗</span></a></h3>'
                f'<span class="{tag}">{escape(kind)}</span>{badge}</div>'
                f'<div><p>{escape(purpose)}</p><details><summary>{label}</summary><p>{escape(first_step)}</p>'
                f'{scope}{overview_link}</details>{issue}</div></article>'
            )
        count = len(entries)
        noun = "projets" if french else "entries"
        cards.append(
            f'<section id="{category}" class="project-group" data-project-group aria-labelledby="heading-{category}">'
            f'<div class="group-heading"><h2 id="heading-{category}">{escape(title)}</h2>'
            f'<span class="group-count" data-group-count>{count} {noun}</span></div>{"".join(items)}</section>'
        )
    suffix = "_FR" if french else ""
    return {
        f"PROJECTS{suffix}": "\n".join(cards),
        f"CATEGORY_OPTIONS{suffix}": "".join(options),
        f"CATEGORY_LINKS{suffix}": "".join(jumps),
    }
