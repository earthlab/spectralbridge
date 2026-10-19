"""Verify rendered callable parameter order, kinds and defaults against source.

Mkdocstrings may shorten annotation namespaces; source annotation and runtime
signature equality is tested separately. This check compares actual callable
arguments/defaults, not presentation whitespace or shortened type names.
"""

from __future__ import annotations

import argparse
import ast
from html.parser import HTMLParser
import json
from pathlib import Path


class Signatures(HTMLParser):
    """Extract the visible signature text from mkdocstrings HTML blocks."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.results = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            self.depth += 1
        elif "doc-signature" in dict(attrs).get("class", "").split():
            self.depth = 1
            self.current = []

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1
            if not self.depth:
                self.results.append("".join(self.current).strip())

    def handle_data(self, data):
        if self.depth:
            self.current.append(data)


def arguments(signature):
    """Normalize syntactic arguments while retaining every actual default."""
    node = ast.parse("def " + signature + ":\n    pass").body[0]
    for child in ast.walk(node.args):
        if isinstance(child, ast.arg):
            child.annotation = None
    return ast.dump(node.args, include_attributes=False)


def check(site: Path, root: Path) -> dict:
    inventory = json.loads((root / "docs/api/inventory.json").read_text())
    checked = []
    errors = []
    for module in inventory["modules"]:
        selected = [
            o
            for o in module["objects"]
            if o["audience"] != "internal" and o["kind"] == "function"
        ]
        if not selected:
            continue
        name = module["module"].removeprefix("spectralbridge.").replace(".", "-")
        page = site / "api/generated" / name / "index.html"
        if not page.exists():
            errors.append("Missing module page: " + str(page))
            continue
        parser = Signatures()
        parser.feed(page.read_text())
        for obj in selected:
            actual = next(
                (text for text in parser.results if text.startswith(obj["name"] + "(")),
                None,
            )
            if actual is None:
                errors.append("Missing signature: " + obj["path"])
            elif arguments(actual) != arguments(obj["signature"]):
                errors.append("Signature/default mismatch: " + obj["path"])
            else:
                checked.append(obj["path"])
    return dict(
        status="failed" if errors else "passed",
        checked_count=len(checked),
        errors=errors,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    result = check(args.site, args.root)
    print(json.dumps(result, indent=2))
    return result["status"] != "passed"


if __name__ == "__main__":
    raise SystemExit(main())
