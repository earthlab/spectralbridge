"""Check rendered local links/images, code syntax and source-only docstring edits.

Run after a strict MkDocs build; does not process imagery or contact the network.
"""

import argparse
import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links, self.images, self.ids = [], [], set()
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.add(d["id"])
        if tag == "a" and d.get("href"):
            self.links.append(d["href"])
        if tag == "img" and d.get("src"):
            self.images.append(d["src"])


def strip_docs(tree):
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            if node.body and isinstance(node.body[0], ast.Expr):
                expr = node.body[0].value
                if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
                    node.body.pop(0)
    return ast.dump(tree, include_attributes=False)


def main(site):
    evidence = json.loads((HERE / "evidence_map.json").read_text())
    docs = sorted({p for e in evidence for p in e["documentation_pages"]})
    errors, checked, syntax = [], 0, 0
    cache = {}
    for name in docs:
        src = ROOT / name
        if not name.startswith("docs/") or src.suffix != ".md":
            continue
        target = site / src.relative_to(ROOT / "docs").with_suffix("") / "index.html"
        if src.name == "index.md":
            target = site / src.relative_to(ROOT / "docs").parent / "index.html"
        if not target.exists():
            errors.append(f"Missing rendered page {target}")
            continue
        page = Page(target)
        for link in page.links + page.images:
            u = urlsplit(link)
            if u.scheme or u.netloc:
                continue
            dest = (
                (
                    (site / unquote(u.path).lstrip("/"))
                    if u.path.startswith("/")
                    else (target.parent / unquote(u.path))
                ).resolve()
                if u.path
                else target
            )
            if dest.is_dir():
                dest /= "index.html"
            if not dest.exists():
                errors.append(f"{name}: missing {link}")
            elif u.fragment and dest.suffix == ".html":
                if dest not in cache:
                    cache[dest] = Page(dest)
                if unquote(u.fragment) not in cache[dest].ids:
                    errors.append(f"{name}: missing fragment {link}")
            checked += 1
        for code in re.findall(r"```python\n(.*?)```", src.read_text(), re.S):
            try:
                ast.parse(code)
                syntax += 1
            except SyntaxError as exc:
                errors.append(f"{name}: Python syntax {exc}")
    for name in [
        "src/spectralbridge/pipelines/drone.py",
        "src/spectralbridge/corrections.py",
    ]:
        old = subprocess.check_output(
            ["git", "show", f"HEAD:{name}"], cwd=ROOT, text=True
        )
        assert strip_docs(ast.parse(old)) == strip_docs(
            ast.parse((ROOT / name).read_text())
        ), name
    notebooks = [
        "Drone_processing.ipynb",
        "Drone_2023_2024_Cloud_Production.ipynb",
        "docs/vignettes/notebooks/06_drone_pipeline.ipynb",
        "docs/vignettes/notebooks/10_bulk_production_cyverse.ipynb",
    ]
    for name in notebooks:
        for cell in json.loads((ROOT / name).read_text())["cells"]:
            if cell["cell_type"] == "code":
                code = "".join(cell["source"])
                if not any(
                    line.lstrip().startswith(("%", "!")) for line in code.splitlines()
                ):
                    ast.parse(code)
                    syntax += 1
    report = dict(
        status="failed" if errors else "passed",
        errors=errors,
        rendered_local_references=checked,
        code_blocks_or_cells=syntax,
        source_executable_ast="unchanged from HEAD",
        pages=docs,
        limitation="Data-dependent examples are syntax checked; no physical-calibration or production run is claimed.",
    )
    (HERE / "documentation_checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "pages"}, indent=2))
    return bool(errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    raise SystemExit(main(parser.parse_args().site.resolve()))
