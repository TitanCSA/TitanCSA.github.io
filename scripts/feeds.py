"""Publish stable RSS subscriptions for the portal guides."""

from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree import ElementTree as ET


ATOM = "http://www.w3.org/2005/Atom"
DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"


def rss_date(date):
    return format_datetime(datetime.fromisoformat(date).replace(tzinfo=timezone.utc), usegmt=True)


def write_feeds(output, base, pages, reviewed, published, default_review):
    guides = [
        (path, title, description, reviewed.get(path, default_review))
        for path, (title, description, _) in pages.items()
        if path.startswith("guides/") or (path.startswith("fr/") and path != "fr/")
    ]
    guides.sort(key=lambda row: row[0])
    guides.sort(key=lambda row: row[3], reverse=True)
    for abbreviation, namespace in (("atom", ATOM), ("dc", DC), ("dcterms", DCTERMS)):
        ET.register_namespace(abbreviation, namespace)
    for prefix, title, description in (
        ("", "TitanCSA guides", "Practical Windows input and device SDK guides from TitanCSA."),
        ("fr/", "Guides TitanCSA", "Guides pratiques sur les pilotes et SDK Windows de TitanCSA."),
    ):
        entries = [row for row in guides if row[0].startswith(prefix)]
        route = prefix + "rss.xml"
        feed = ET.Element("rss", version="2.0")
        channel = ET.SubElement(feed, "channel")
        ET.SubElement(channel, "title").text = title
        ET.SubElement(channel, "link").text = base + prefix
        ET.SubElement(channel, "description").text = description
        ET.SubElement(channel, "lastBuildDate").text = rss_date(entries[0][3])
        if prefix:
            ET.SubElement(channel, "language").text = "fr"
        ET.SubElement(channel, f"{{{ATOM}}}link", href=base + route, rel="self", type="application/rss+xml")
        for path, name, summary, modified in entries:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = name
            ET.SubElement(item, "link").text = base + path
            ET.SubElement(item, "guid", isPermaLink="true").text = base + path
            ET.SubElement(item, "description").text = summary
            ET.SubElement(item, f"{{{DC}}}language").text = "fr" if path.startswith("fr/") else "en"
            ET.SubElement(item, f"{{{DCTERMS}}}modified").text = modified
            if date := published.get(path):
                ET.SubElement(item, "pubDate").text = rss_date(date)
        ET.indent(feed)
        ET.ElementTree(feed).write(output / route, encoding="utf-8", xml_declaration=True)
