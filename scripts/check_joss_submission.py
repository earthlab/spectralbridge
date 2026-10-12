#!/usr/bin/env python3
"""Check local JOSS source contracts; author declarations are never inferred."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = (
    "Summary", "Statement of need", "State of the field", "Software design",
    "Research impact statement", "AI usage disclosure", "Acknowledgements", "References",
)


def bibliography_entries(text: str) -> dict[str, dict[str, str]]:
    """Read the brace-delimited entries used by this paper, including nested titles."""
    entries: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"@([A-Za-z]+)\s*\{([^,]+),", text):
        key = match[2].strip()
        if key in entries:
            raise ValueError(f"Duplicate bibliography key: {key}")
        fields = {"entrytype": match[1].lower()}
        pos = match.end()
        closed = False
        while pos < len(text):
            field = re.match(r"\s*,?\s*([\w-]+)\s*=\s*\{", text[pos:])
            if not field:
                if not re.match(r"\s*,?\s*\}", text[pos:]):
                    raise ValueError(f"Malformed bibliography entry: {key}")
                closed = True
                break
            name = field[1].lower()
            pos += field.end()
            start, depth = pos, 1
            while pos < len(text) and depth:
                if text[pos] == "\\":
                    pos += 2
                    continue
                depth += (text[pos] == "{") - (text[pos] == "}")
                pos += 1
            if depth:
                raise ValueError(f"Unbalanced bibliography field: {key}.{name}")
            fields[name] = text[start:pos - 1]
        if not closed:
            raise ValueError(f"Unclosed bibliography entry: {key}")
        entries[key] = fields
    if not entries:
        raise ValueError("No bibliography entries found")
    return entries


def valid_orcid(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", value):
        return False
    total = 0
    for digit in value.replace("-", "")[:-1]:
        total = (total + int(digit)) * 2
    checksum = (12 - total % 11) % 11
    return value[-1] == ("X" if checksum == 10 else str(checksum))


def word_count(body: str, *, captions: bool) -> int:
    text = re.sub(r"\$\$.*?\$\$", " ", body, flags=re.S)
    text = re.sub(r"!\[([^\n]*?)\]\([^\n]*?\)(?:\{[^\n]*?\})?", lambda m: m[1] if captions else " ", text)
    text = re.sub(r"\[@[^\]]*\]", " ", text)
    text = re.sub(r"\\(?:auto)?ref\{[^}]*\}", "reference", text)
    return len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b", text))


def check_paper(path: Path) -> dict:
    errors: list[str] = []
    author_actions: list[str] = []
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not match:
        return {"errors": ["Missing YAML front matter"], "author_actions": []}
    metadata = yaml.safe_load(match[1])
    body = match[2]
    if not isinstance(metadata, dict):
        return {"errors": ["YAML metadata is not a mapping"], "author_actions": []}
    for field in ("title", "authors", "affiliations", "date", "bibliography", "tags"):
        if not metadata.get(field):
            errors.append(f"Missing metadata: {field}")
    indices = {str(a["index"]) for a in metadata.get("affiliations", [])}
    for author in metadata.get("authors", []):
        if not author.get("name"):
            errors.append("Author lacks a name")
        if not set(str(author.get("affiliation", "")).replace(" ", "").split(",")) <= indices:
            errors.append(f"Unknown affiliation: {author.get('name')}")
        if author.get("orcid") and not valid_orcid(str(author["orcid"])):
            errors.append(f"Invalid ORCID checksum: {author.get('name')}")
    headings = re.findall(r"^# (.+)$", body, re.M)
    if path.name == "paper.md":
        for section in SECTIONS:
            if headings.count(section) != 1:
                errors.append(f"Expected exactly one section: {section}")
        count = word_count(body, captions=True)
        if not 750 <= count <= 1750:
            errors.append(f"Paper length outside 750–1750 words: {count} including captions")
    else:
        count = word_count(body, captions=True)
    if body.count("```") % 2:
        errors.append("Unbalanced code fences")
    bib_path = path.parent / metadata.get("bibliography", "missing.bib")
    try:
        entries = bibliography_entries(bib_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        entries = {}
    citations = set(re.findall(r"@([a-zA-Z][\w:.-]*)", body))
    for key in sorted(citations - entries.keys()):
        errors.append(f"Unresolved citation: {key}")
    for key, entry in entries.items():
        for field in ("author", "title", "year"):
            if not entry.get(field):
                errors.append(f"Missing bibliography field: {key}.{field}")
        if entry.get("entrytype") == "article" and not entry.get("journal"):
            errors.append(f"Missing journal: {key}")
        if entry.get("url") and re.search(r"\s", entry["url"]):
            errors.append(f"Whitespace in bibliography URL: {key}")
        if entry.get("doi") and not re.fullmatch(r"10\.\d{4,9}/\S+", entry["doi"]):
            errors.append(f"Malformed DOI: {key}")
    images = re.findall(r"\]\((figures/[^)]+)\)", body)
    for image in images:
        if not (path.parent / image).is_file():
            errors.append(f"Missing figure: {image}")
    labels = set(re.findall(r"\{#([^} ]+)|\\label\{([^}]+)\}", body))
    identifiers = {a or b for a, b in labels}
    for ref in re.findall(r"\\(?:auto)?ref\{([^}]+)\}", body):
        if ref not in identifiers:
            errors.append(f"Unresolved internal reference: {ref}")
    author_actions.extend(re.findall(r"\[AUTHOR INPUT REQUIRED: ([^\]]+)\]", body))
    return {
        "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "word_count_including_captions": count,
        "word_count_excluding_captions": word_count(body, captions=False),
        "bibliography_entries": len(entries), "unique_citation_keys": len(citations),
        "images": len(images), "errors": errors, "author_actions": author_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready", action="store_true", help="Also fail for unresolved author declarations")
    parser.add_argument("--output", type=Path, help="Write machine-readable report")
    args = parser.parse_args()
    reports = [check_paper(ROOT / "paper" / name) for name in ("paper.md", "supplement.md")]
    report = {"papers": reports, "format_checks_pass": not any(r["errors"] for r in reports),
              "author_declarations_complete": not any(r["author_actions"] for r in reports)}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(not report["format_checks_pass"] or (args.ready and not report["author_declarations_complete"]))


if __name__ == "__main__":
    raise SystemExit(main())
