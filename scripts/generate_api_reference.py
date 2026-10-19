#!/usr/bin/env python3
"""Inventory the Python AST and generate the MkDocs API catalogue without imports.

Run with --check in CI. Canonical definitions render once; exports link to them.
Private members remain in the downloadable inventory, not the public glossary.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREAS = {
    "pipelines": ("NEON and drone workflows", "vignettes/full-pipeline.md"),
    "drone": ("Drone production and translation", "vignettes/drone-processing.md"),
    "bulk": ("Bulk processing and compact results", "vignettes/bulk-analysis.md"),
    "analysis": (
        "Spectral libraries and scientific analysis",
        "api/scientific-analysis.md",
    ),
    "corrections": ("Corrections and spectral processing", "brdf_topo_algorithm.md"),
    "qa": ("Quality assurance and validation", "vignettes/qa-and-analysis.md"),
    "io": ("Input, output and polygon extraction", "vignettes/polygon-extraction.md"),
    "utilities": ("Paths, metadata and utilities", "naming-conventions.md"),
}
ANALYSIS = (
    "library_analysis",
    "plant_",
    "researcher_",
    "spectral_",
    "sensor_pft",
    "pft_",
    "mixtures",
    "mesma_",
    "landsat_",
    "sensor_panel",
)
PINNED_SUMMARIES = {
    "spectralbridge.mesma_readiness.ReadinessConfig": "Configure the experimental MESMA-readiness study and computational budgets.",
    "spectralbridge.researcher_information.validate_researcher_labels": "Validate labels against the five recorded researcher cover categories.",
    "spectralbridge.researcher_validation.balanced_accuracy": "Compute mean class recall with equal total weight per independent identity.",
}
INTERNAL_MODULES = {
    "_cli_compat",
    "_optional",
    "_ray_utils",
    "logging_utils",
    "progress_utils",
    "sort_core",
    "file_sort_adapter",
    "hytools_compat",
    "types_protocol",
}
INTERNAL_NAMES = {
    "main",
    "parse_args",
    "download_main",
    "pipeline_main",
    "qa_main",
    "warn_if_legacy_command",
    "configure_duckdb",
    "copy_table_atomic",
    "finalize_bulk_database",
    "quote_identifier",
    "quote_path",
    "sql_literal",
    "canonical_json",
    "signature_sha256",
    "relative_paths",
    "write_json_atomic",
    "write_text_atomic",
    "pq_read_table",
    "pq_write_table",
    "run_pipeline",
    "run_download",
    "tqdm",
    "ray_map",
    "init_ray",
}


def area(module: str) -> str:
    part = module.removeprefix("spectralbridge.").split(".")[0]
    if part in ("pipelines", "envi_download", "neon_to_envi"):
        return "pipelines"
    if part.startswith("drone") or part == "remote":
        return "drone"
    if part == "bulk":
        return "bulk"
    if part.startswith(ANALYSIS):
        return "analysis"
    if part.startswith("qa") or part == "validation":
        return "qa"
    if part in (
        "brdf_topo",
        "brightness",
        "brightness_config",
        "corrections",
        "resample",
        "standard_resample",
    ):
        return "corrections"
    if part in (
        "io",
        "envi",
        "envi_writer",
        "exports",
        "parquet_export",
        "parquet_validation",
        "polygon_extraction",
        "polygons",
        "merge_duckdb",
        "neon_cube",
    ):
        return "io"
    return "utilities"


def _string_names(node: ast.AST) -> set[str]:
    names = {
        n.value
        for n in ast.walk(node)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    names.update(
        n.value.id
        for n in ast.walk(node)
        if isinstance(n, ast.Attribute)
        and n.attr == "__name__"
        and isinstance(n.value, ast.Name)
    )
    return names


def _signature(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        result = f"{node.name}({ast.unparse(node.args)})"
        if node.returns:
            result += " -> " + ast.unparse(node.returns)
        return result
    return None


def _parameters(node: ast.AST) -> list[dict]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    args = node.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    pairs = list(zip(positional, defaults)) + list(
        zip(args.kwonlyargs, args.kw_defaults)
    )
    if args.vararg:
        pairs.append((args.vararg, None))
    if args.kwarg:
        pairs.append((args.kwarg, None))
    return [
        dict(
            name=a.arg,
            annotation=ast.unparse(a.annotation) if a.annotation else None,
            default=ast.unparse(d) if d is not None else None,
            kind="positional-only"
            if a in args.posonlyargs
            else "keyword-only"
            if a in args.kwonlyargs
            else "variadic-positional"
            if a is args.vararg
            else "variadic-keyword"
            if a is args.kwarg
            else "positional-or-keyword",
        )
        for a, d in pairs
        if a.arg not in ("self", "cls")
    ]


def inventory(root: Path) -> dict:
    modules = []
    docs = {
        str(p.relative_to(root)): p.read_text()
        for p in (root / "docs").rglob("*.md")
        if "api/generated" not in str(p) and p != root / "docs/api/index.md"
    }
    examples = {
        str(p.relative_to(root)): p.read_text()
        for p in (root / "examples").rglob("*.py")
    }
    for path in sorted((root / "src/spectralbridge").rglob("*.py")):
        source = path.read_text()
        tree = ast.parse(source)
        module = ".".join(
            path.relative_to(root / "src").with_suffix("").parts
        ).removesuffix(".__init__")
        exports = set()
        export_expressions = []
        imports = {}
        objects = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                if n.level:
                    parent = (
                        module
                        if path.name == "__init__.py"
                        else module.rpartition(".")[0]
                    )
                    base = ".".join(
                        parent.split(".")[: len(parent.split(".")) - n.level + 1]
                    )
                    target = base + "." + n.module
                else:
                    target = n.module
                for alias in n.names:
                    imports[alias.asname or alias.name] = target + "." + alias.name
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if any(
                    isinstance(t, ast.Name) and t.id in ("__all__", "_PLOT_EXPORTS")
                    for t in targets
                ):
                    exports.update(_string_names(n.value))
                    export_expressions.append(ast.unparse(n))
        for n in tree.body:
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            doc = ast.get_docstring(n) or ""
            qualified = module + "." + n.name
            private_module = (
                any(part.startswith("_") for part in module.split("."))
                or module.split(".")[1:2] == ["cli"]
                or "deprecated" in module.split(".")
                or module.split(".")[-1] in INTERNAL_MODULES
                or module.endswith("topo_and_brdf_correction")
            )
            internal = (
                private_module or n.name.startswith("_") or n.name in INTERNAL_NAMES
            )
            references = sorted(k for k, v in docs.items() if qualified in v)
            obj = dict(
                name=n.name,
                path=qualified,
                kind="class" if isinstance(n, ast.ClassDef) else "function",
                line=n.lineno,
                signature=_signature(n),
                parameters=_parameters(n),
                docstring=doc,
                summary=doc.split("\n")[0]
                if doc
                else PINNED_SUMMARIES.get(qualified, ""),
                summary_basis="source docstring"
                if doc
                else "reference annotation; source hash-pinned in historical evidence"
                if qualified in PINNED_SUMMARIES
                else "not documented",
                audience="internal" if internal else "advanced",
                classification_reason="Private/compatibility/CLI module or implementation utility"
                if internal
                else "Direct module API; no package-level stability guarantee",
                docs_references=references,
                examples=sorted(k for k, v in examples.items() if n.name in v),
                methods=[],
                attributes=[],
                exports=[],
            )
            if isinstance(n, ast.ClassDef):
                for child in n.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        obj["methods"].append(
                            dict(
                                name=child.name,
                                signature=_signature(child),
                                parameters=_parameters(child),
                                docstring=ast.get_docstring(child) or "",
                                private=child.name.startswith("_"),
                                line=child.lineno,
                            )
                        )
                    if isinstance(child, ast.AnnAssign) and isinstance(
                        child.target, ast.Name
                    ):
                        obj["attributes"].append(
                            dict(
                                name=child.target.id,
                                annotation=ast.unparse(child.annotation),
                                default=ast.unparse(child.value)
                                if child.value
                                else None,
                            )
                        )
            objects.append(obj)
        constants = []
        for n in tree.body:
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                for target in n.targets if isinstance(n, ast.Assign) else [n.target]:
                    if (
                        isinstance(target, ast.Name)
                        and (target.id in exports or target.id == "DroneSource")
                        and (
                            not target.id.startswith("_") or target.id == "__version__"
                        )
                    ):
                        constants.append(
                            dict(
                                name=target.id,
                                value=ast.unparse(n.value) if n.value else None,
                                annotation=ast.unparse(n.annotation)
                                if isinstance(n, ast.AnnAssign)
                                else None,
                            )
                        )
        modules.append(
            dict(
                module=module,
                path=str(path.relative_to(root)),
                area=area(module),
                sha256=hashlib.sha256(source.encode()).hexdigest(),
                docstring=ast.get_docstring(tree) or "",
                declared_exports=sorted(exports),
                export_expressions=export_expressions,
                imports=imports,
                objects=objects,
                constants=constants,
            )
        )
    definitions = {o["path"]: o for m in modules for o in m["objects"]}
    # Lazy getattr exports have no import-time alias for static autodoc to follow.
    for m in modules:
        if m["module"] in ("spectralbridge", "spectralbridge.pipelines"):
            source = (root / m["path"]).read_text()
            tree = ast.parse(source)
            for n in ast.walk(tree):
                if isinstance(n, ast.If):
                    names = _string_names(n.test)
                    target_modules = [
                        call.args[0].value
                        for stmt in n.body
                        for call in ast.walk(stmt)
                        if isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == "import_module"
                        and call.args
                        and isinstance(call.args[0], ast.Constant)
                    ]
                    for name in names:
                        for target in target_modules:
                            if target + "." + name in definitions:
                                m["imports"][name] = target + "." + name
    module_map = {m["module"]: m for m in modules}

    def resolve(path, seen=None):
        seen = set() if seen is None else seen
        if path in seen:
            return path
        seen.add(path)
        mod, _, name = path.rpartition(".")
        target = module_map.get(mod, {}).get("imports", {}).get(name)
        return resolve(target, seen) if target else path

    # Resolve imported type aliases as well as callables for lazy package exports.
    for m in modules:
        if m["module"] == "spectralbridge" and "DroneSource" in m["declared_exports"]:
            m["imports"]["DroneSource"] = "spectralbridge.drone_production.DroneSource"
    # Lazy imports often bind _run_* aliases before assigning globals()[name].
    for m in modules:
        for target in list(m["imports"].values()):
            name = target.rsplit(".", 1)[-1]
            if (
                name in m["declared_exports"]
                and name not in m["imports"]
                and target in definitions
            ):
                m["imports"][name] = target
    constants_by_path = {
        m["module"] + "." + c["name"]: c for m in modules for c in m["constants"]
    }
    unresolved = []
    export_records = []
    for m in modules:
        for name in m["declared_exports"]:
            if name.startswith("_") and name != "__version__":
                continue
            canonical = resolve(m["module"] + "." + name)
            export_records.append(
                dict(
                    export=m["module"] + "." + name,
                    canonical=canonical,
                    kind="callable"
                    if canonical in definitions
                    else "module"
                    if canonical in module_map
                    else "constant_or_type_alias",
                )
            )
            if canonical in definitions:
                obj = definitions[canonical]
                obj["exports"].append(m["module"] + "." + name)
                if (
                    m["module"]
                    in (
                        "spectralbridge",
                        "spectralbridge.bulk",
                        "spectralbridge.bulk.analyses",
                        "spectralbridge.io",
                        "spectralbridge.qa",
                        "spectralbridge.utils",
                    )
                    and obj["audience"] != "internal"
                ):
                    obj["audience"] = "public"
                    obj["classification_reason"] = "Explicit package/subpackage export"
            elif (
                canonical not in constants_by_path
                and canonical not in module_map
                and canonical
                not in (
                    "spectralbridge.drone_production.DroneSource",
                    "spectralbridge.DroneSource",
                )
            ):
                unresolved.append(
                    dict(export=m["module"] + "." + name, target=canonical)
                )
    # Explicit composable analysis facade is documented as a module API.
    for o in definitions.values():
        if (
            o["path"].startswith("spectralbridge.library_analysis.")
            and o["audience"] != "internal"
        ):
            o["audience"] = "public"
            o["classification_reason"] = (
                "Explicit __all__ in composable scientific analysis facade"
            )
        if o["audience"] == "advanced" and o["docs_references"]:
            o["classification_reason"] = (
                "Documented direct-module API; advanced or experimental, not promoted by this reference"
            )
    return dict(
        schema_version=1,
        modules=modules,
        unresolved_exports=unresolved,
        export_records=sorted(export_records, key=lambda item: item["export"]),
        policy="Public: explicit supported package/subpackage exports or library_analysis facade. Advanced: other non-private direct-module definitions. Internal: private, compatibility and CLI implementation helpers. Classification documents existing visibility; it changes no exports.",
    )


def page_name(module: str) -> str:
    return (
        module.removeprefix("spectralbridge.").replace(".", "-")
        if module != "spectralbridge"
        else "package"
    )


def anchor(obj: dict) -> str:
    return obj["path"]


def build_outputs(root: Path) -> dict[Path, str]:
    data = inventory(root)
    modules = data["modules"]
    outputs = {
        Path("docs/api/inventory.json"): json.dumps(data, indent=2, sort_keys=True)
        + "\n"
    }
    intro = [
        "# API Reference",
        "",
        "Find a callable by scientific task, then follow its name for the source-derived signature, defaults and docstring. Prefer package exports for supported orchestration; direct-module research APIs retain their existing maturity limits.",
        "",
        "The reference is generated without importing scientific dependencies. Each definition renders once at its canonical module path; exported aliases point to that entry. [Download the complete inventory](inventory.json), try the [checked examples](examples.md), or read the [API audit and maintenance policy](audit.md).",
        "",
        "Workflow guides explain **how to accomplish a task**; these entries explain **how to call a particular object**. See the [scientific API maturity guide](scientific-analysis.md) before interpreting research outputs.",
        "",
    ]
    public = [o for m in modules for o in m["objects"] if o["audience"] == "public"]
    advanced = [o for m in modules for o in m["objects"] if o["audience"] == "advanced"]
    intro += [
        f"This revision documents **{len(public)} public functions/classes** and **{len(advanced)} advanced functions/classes**. Names that merely look public are not a stability guarantee. Private helpers and CLI/compatibility plumbing are listed separately in the inventory.",
        "",
    ]
    intro += [
        "## Package exports",
        "",
        "Use these existing package-level names in scripts. Aliases lead to their canonical callable entries; constants and source-level type aliases remain distinct from functions.",
        "",
        "| Import | Reference |",
        "| --- | --- |",
    ]
    objects = {o["path"]: (m, o) for m in modules for o in m["objects"]}
    for record in data["export_records"]:
        if record["export"].rpartition(".")[0] != "spectralbridge":
            continue
        canonical = record["canonical"]
        if canonical in objects:
            m, o = objects[canonical]
            target = (
                f"[canonical entry](generated/{page_name(m['module'])}.md#{canonical})"
            )
        else:
            target = (
                "Source-level "
                + record["kind"].replace("_", " ")
                + f" (`{canonical}`); see inventory."
            )
        intro += [f"| `{record['export']}` | {target} |"]
    intro += [""]
    for key, (title, workflow) in AREAS.items():
        intro += [
            "## " + title,
            "",
            f"[Workflow / scientific context](../{workflow})",
            "",
            "| Object | Purpose | Audience |",
            "| --- | --- | --- |",
        ]
        for m in modules:
            if m["area"] != key:
                continue
            visible = [o for o in m["objects"] if o["audience"] != "internal"]
            if not visible and not m["constants"]:
                continue
            name = page_name(m["module"])
            detail = [
                "# "
                + {
                    "spectralbridge.pipelines.pipeline": "NEON orchestration",
                    "spectralbridge.pipelines.drone": "Local drone processing",
                    "spectralbridge.pipelines.bulk": "Bulk orchestration",
                    "spectralbridge.bulk.analyses.spectral_library": "Spectral-library inspection and reports",
                    "spectralbridge.library_analysis": "Composable spectral analysis",
                    "spectralbridge.drone_production": "Remote drone campaigns",
                    "spectralbridge": "Package metadata",
                }.get(
                    m["module"],
                    m["module"]
                    .removeprefix("spectralbridge.")
                    .replace(".", " ")
                    .replace("_", " ")
                    .title(),
                ),
                "",
                "Module: `" + m["module"] + "`.",
                "",
                m["docstring"]
                or "Direct-module reference; consult the linked workflow for processing context.",
                "",
                f"[API glossary](../index.md) · [Workflow / scientific context](../../{workflow})",
                "",
                "Signatures and documentation below are collected from the current source. Advanced objects are not newly declared stable by inclusion here.",
                "",
            ]
            for o in visible:
                purpose = (
                    (
                        o["summary"]
                        or "Documentation gap: see source and audit before direct use."
                    )
                    .replace("|", "\\|")
                    .replace("`", "")
                )
                intro += [
                    f"| [`{o['name']}`](generated/{name}.md#{anchor(o)}) | {purpose} | {o['audience']} |"
                ]
                aliases = ", ".join(
                    "`" + a + "`" for a in sorted(set(o["exports"])) if a != o["path"]
                )
                detail += [
                    f"Audience: **{o['audience']}**."
                    + (f" Also exported as {aliases}." if aliases else ""),
                    "",
                ]
                style = "google" if "\nArgs:" in o["docstring"] else "numpy"
                detail += [
                    f"::: {o['path']}",
                    "    options:",
                    f"      docstring_style: {style}",
                    "      show_signature_annotations: true",
                    "      separate_signature: true",
                    "      show_root_heading: true",
                    "      show_root_full_path: false",
                    "      show_bases: false",
                    "      show_source: false",
                    "      signature_crossrefs: false",
                ]
                if o["kind"] == "class":
                    members = [x["name"] for x in o["methods"] if not x["private"]]
                    detail += [
                        "      members: " + json.dumps(members),
                        "      inherited_members: false",
                        "      merge_init_into_class: true",
                    ]
                else:
                    detail += ["      members: false"]
                detail += [""]
            if m["constants"]:
                detail += [
                    "## Explicitly exported constants and type aliases",
                    "",
                    "These values describe package metadata, schemas or configuration; they are not observations from a production dataset.",
                    "",
                    "| Name | Source expression |",
                    "| --- | --- |",
                ]
                for c in m["constants"]:
                    value = (
                        c["value"].replace("|", "\\|").replace("\n", " ")
                        if c["value"]
                        else "No assigned value"
                    )
                    detail += [f"| `{c['name']}` | `{value}` |"]
            outputs[Path("docs/api/generated") / (name + ".md")] = (
                "<!-- Generated by scripts/generate_api_reference.py; edit source docstrings. -->\n"
                + "\n".join(detail)
                + "\n"
            )
        intro += [""]
    outputs[Path("docs/api/index.md")] = "\n".join(intro).rstrip() + "\n"
    return outputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    outputs = build_outputs(args.root)
    stale = []
    expected = {args.root / path for path in outputs}
    for old in (args.root / "docs/api/generated").glob("*.md"):
        if old not in expected:
            if args.check or not old.read_text().startswith(
                "<!-- Generated by scripts/generate_api_reference.py;"
            ):
                stale.append(str(old.relative_to(args.root)))
            else:
                old.unlink()
    for path, text in outputs.items():
        destination = args.root / path
        if args.check:
            if not destination.exists() or destination.read_text() != text:
                stale.append(str(path))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text)
    if stale:
        print("Stale API reference: " + ", ".join(stale))
        return 1
    print(
        f"API reference {'verified' if args.check else 'generated'}: {len(outputs)} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
