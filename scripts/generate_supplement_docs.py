"""Publish the complete rendered SI into MkDocs, without summarizing its content.

First prepare its source fingerprint and render supplement.html with Pandoc/citeproc as documented in
drafts/joss/README.md. Then run this script; --check detects stale source/assets.
"""

from pathlib import Path
import argparse
import hashlib
import json
import re
import io
import zipfile
from html import escape

import yaml


ROOT = Path(__file__).resolve().parents[1]


def source_digest(draft):
    return hashlib.sha256(
        (draft / "supplement.md").read_bytes() + b"\0" + (draft / "supplement.bib").read_bytes()
    ).hexdigest()


def outputs(root=ROOT):
    draft = root / "drafts/joss"
    html = (draft / "supplement.html").read_text()
    body = re.search(r"<body>\s*(.*?)\s*</body>", html, re.S).group(1)
    images = re.findall(r'<img[^>]+src="([^"]+)"', body)
    assert len(images) == 23, "Expected both SI figures and all table-page images"
    assert body.count("<table>") == 23, "Expected all 23 editable SI tables"
    assert len(re.findall(r'id="ref-', body)) == 101, "Expected all SI references"
    assert body.count('<math display="block"') == 3, "Expected all three equations"
    assert "[@si_" not in body, "Citations must be rendered"
    assert f"<!-- SI source SHA256: {source_digest(draft)} -->" in body, "SI HTML is stale; rerender"
    for image in images:
        body = body.replace(f'src="{image}"', f'src="../supplement-assets/{Path(image).name}"')
    # Citeproc styles can omit BibTeX notes. Keep the SI's access dates, source
    # revision boundaries and unavailable-evidence declarations visible online.
    notes = 0
    for entry in re.split(r"(?=^@)", (draft / "supplement.bib").read_text(), flags=re.M):
        key = re.search(r"@\w+\{([^,]+),", entry)
        note = re.search(r"\bnote\s*=\s*\{([^{}]*)\}", entry)
        if key and note:
            pattern = rf'(<div id="ref-{re.escape(key.group(1))}"[^>]*>)(.*?)(</div>)'
            body, replaced = re.subn(
                pattern,
                lambda match: match.group(1) + match.group(2)
                + f'<p class="si-reference-note">Source note: {escape(note.group(1))}</p>'
                + match.group(3), body, flags=re.S,
            )
            assert replaced == 1, f"Missing reference for provenance note: {key.group(1)}"
            notes += 1
    source = (draft / "supplement.md").read_text()
    metadata = yaml.safe_load(source.split("---", 2)[1])
    authors = []
    for author in metadata["authors"]:
        label = escape(author["name"]) + "<sup>" + escape(str(author["affiliation"])) + "</sup>"
        if author.get("corresponding"):
            label += " (corresponding author)"
        if author.get("orcid"):
            orcid = escape(author["orcid"])
            label += f' · <a href="https://orcid.org/{orcid}">ORCID {orcid}</a>'
        authors.append(f"<li>{label}</li>")
    affiliations = [f'<li value="{item["index"]}">{escape(item["name"])}</li>'
                    for item in metadata["affiliations"]]
    identity = (f'<h2>Manuscript identity</h2><p>{escape(metadata["title"])}</p>'
                f'<p>Revised {escape(str(metadata["date"]))}.</p><ul>' + "".join(authors)
                + "</ul><ol>" + "".join(affiliations) + "</ol>"
                + '<p>Correspondence: <a href="mailto:ty.tuff@colorado.edu">ty.tuff@colorado.edu</a></p>')
    intro = """---
title: Complete manuscript supplement
hide:
  - toc
---

# Complete manuscript supplement

This is the complete supplementary material supplied with the manuscript revised
12 October 2026, including all sections and appendices, 23 editable tables, two
figures, three equations and 101 references. It retains the source's historical
revision boundaries, incomplete-run records and unresolved scientific questions.
Those observations describe the cited runs and revisions, rather than a live
certification of the current software. Consult the current workflow guides for
operational instructions.

Download the [original 44-page SI PDF](supplement-assets/supplement-10.pdf),
[Markdown source bundle](supplement-assets/supplement-source.zip),
[bibliography](supplement-assets/supplement.bib), or
[Google Docs import copy](supplement-assets/SpectralBridge-SI.docx).
Wrapped PDF table lines remain separate rows where their semantic grouping is
uncertain; the source-page images remain alongside the tables for comparison.

<div class="sb-supplement-content">
"""
    result = {"docs/validation/supplement.md": (intro + identity + body + "\n</div>\n").encode()}
    assets = {Path(x).name: draft / x for x in images}
    assets.update({x: draft / x for x in ("supplement-10.pdf", "supplement.bib")})
    assets["SpectralBridge-SI.docx"] = draft / "google-docs/SpectralBridge-SI.docx"
    for name, source in assets.items():
        result[f"docs/validation/supplement-assets/{name}"] = source.read_bytes()
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ["supplement.md", "supplement.bib"] + images:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (draft / name).read_bytes())
    result["docs/validation/supplement-assets/supplement-source.zip"] = bundle.getvalue()
    inputs = [draft / x for x in ("supplement.md", "supplement.bib", "supplement.html", "supplement-10.pdf")]
    inputs += list(assets.values())
    hashes = {str(x.relative_to(root)): hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}
    manifest = {"source_sha256": hashes, "tables": 23, "figures": 2,
                "table_page_images": 21, "equations": 3, "references": 101,
                "reference_provenance_notes": notes,
                "section_headings": re.findall(r"^#{1,2} (.+)$", (draft / "supplement.md").read_text(), re.M),
                "policy": "Complete supplied SI; historical claims preserved; no inferred validation"}
    result["docs/validation/supplement-coverage.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prepare-render", action="store_true", help="Write source fingerprint before Pandoc render")
    args = parser.parse_args()
    if args.prepare_render:
        draft = ROOT / "drafts/joss"
        (draft / "supplement-render-header.html").write_text(
            f"<!-- SI source SHA256: {source_digest(draft)} -->\n"
        )
        return
    for name, data in outputs().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Stale supplementary documentation: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Complete SI documentation verified" if args.check else "Complete SI documentation generated")


if __name__ == "__main__":
    main()
