"""Check rendered internal links, anchors and assets without network requests."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("name"):
            self.ids.add(values["name"])
        key = {"a": "href", "img": "src", "script": "src"}.get(tag)
        if tag == "link" and values.get("rel") in {"stylesheet", "icon"}:
            key = "href"
        if key and values.get(key):
            self.links.append(values[key])


def check(site, base_path="/spectralbridge/"):
    site = Path(site).resolve()
    pages = {path: Page(path.read_text()) for path in site.rglob("*.html")}
    errors = []
    for path, page in pages.items():
        base = "https://internal.invalid/" + path.relative_to(site).as_posix()
        for link in page.links:
            if urlsplit(link).scheme or link.startswith("//"):
                continue  # External sources/DOIs are intentionally not network gates.
            parsed = urlsplit(urljoin(base, link))
            url_path = unquote(parsed.path)
            if url_path.startswith(base_path):
                url_path = "/" + url_path[len(base_path):]
            target = site / url_path.lstrip("/")
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                errors.append(f"{path.relative_to(site)}: missing target {link}")
            elif parsed.fragment and target in pages:
                if unquote(parsed.fragment) not in pages[target].ids:
                    errors.append(f"{path.relative_to(site)}: missing anchor {link}")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing built site: {args.site}")
    errors = check(args.site)
    for error in errors:
        print(error)
    print(f"Rendered internal link/anchor/asset check: {len(errors)} errors")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
