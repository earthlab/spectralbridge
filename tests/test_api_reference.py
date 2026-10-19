"""Source/reference coverage, real signatures and executable scientific examples."""

from __future__ import annotations

import ast
from collections import Counter
import doctest
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_api_reference", ROOT / "scripts/generate_api_reference.py"
)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)


@pytest.fixture(scope="module")
def inventory():
    return GENERATOR.inventory(ROOT)


def test_reference_is_current_and_has_no_duplicate_or_private_entries(inventory):
    outputs = GENERATOR.build_outputs(ROOT)
    for path, text in outputs.items():
        assert (ROOT / path).read_text() == text, path
    directives = []
    for path in (ROOT / "docs/api").rglob("*.md"):
        directives.extend(re.findall(r"^::: (\S+)", path.read_text(), re.M))
    counts = Counter(directives)
    expected = {
        o["path"]
        for m in inventory["modules"]
        for o in m["objects"]
        if o["audience"] != "internal"
    }
    assert set(counts) == expected
    assert all(n == 1 for n in counts.values())
    assert not any(part.startswith("_") for name in counts for part in name.split("."))
    assert not inventory["unresolved_exports"]
    for key in GENERATOR.AREAS:
        assert any(
            m["area"] == key and any(o["audience"] != "internal" for o in m["objects"])
            for m in inventory["modules"]
        )


def test_inventory_covers_every_source_definition_and_metadata(inventory):
    paths = {m["path"] for m in inventory["modules"]}
    assert paths == {
        str(p.relative_to(ROOT)) for p in (ROOT / "src/spectralbridge").rglob("*.py")
    }
    for m in inventory["modules"]:
        tree = ast.parse((ROOT / m["path"]).read_text())
        definitions = {
            n.name
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        assert definitions == {o["name"] for o in m["objects"]}
        for o in m["objects"]:
            assert o["classification_reason"]
            assert isinstance(o["docs_references"], list) and isinstance(
                o["examples"], list
            )


def _documented_parameters(doc):
    names = set()
    for line in doc.splitlines():
        match = re.match(r"^([\w, ]+)\s*:\s*\S", line)
        if match:
            names.update(n.strip() for n in match[1].split(","))
    return names


def test_supported_public_contracts_have_structured_docstrings(inventory):
    for m in inventory["modules"]:
        for o in m["objects"]:
            if o["audience"] != "public":
                continue
            doc = o["docstring"]
            assert doc.strip(), o["path"]
            if o["kind"] == "function":
                assert "Returns\n-------" in doc, o["path"]
                assert {p["name"] for p in o["parameters"]} <= _documented_parameters(
                    doc
                ), o["path"]
            elif o["attributes"]:
                assert "Attributes\n----------" in doc, o["path"]
                assert {a["name"] for a in o["attributes"]} <= _documented_parameters(
                    doc
                ), o["path"]
            assert all(
                method["docstring"] for method in o["methods"] if not method["private"]
            ), o["path"]


def test_supported_signatures_and_defaults_match_installed_source(inventory):
    for m in inventory["modules"]:
        selected = [
            o
            for o in m["objects"]
            if o["audience"] == "public" and o["kind"] == "function"
        ]
        if not selected:
            continue
        module = importlib.import_module(m["module"])
        for o in selected:
            signature = inspect.signature(getattr(module, o["name"]))
            assert list(signature.parameters) == [p["name"] for p in o["parameters"]]
            for p in o["parameters"]:
                actual = signature.parameters[p["name"]]
                assert (
                    actual.kind.name.casefold()
                    .replace("_", "-")
                    .replace("var-", "variadic-")
                    == p["kind"]
                )
                if p["kind"].startswith("variadic"):
                    continue
                assert (actual.default is inspect.Parameter.empty) == (
                    p["default"] is None
                )
                if p["default"] is not None:
                    # Resolve source defaults in the function's actual module globals.
                    expected = eval(p["default"], vars(module))
                    assert actual.default is expected or actual.default == expected


@pytest.mark.parametrize(
    "module_name",
    [
        "spectralbridge.library_analysis",
        "spectralbridge.qa.metrics",
        "spectralbridge.brightness",
        "spectralbridge.brightness_config",
        "spectralbridge.utils.paths",
    ],
)
def test_public_docstring_examples_execute(module_name, inventory):
    if module_name == "spectralbridge.library_analysis":
        pytest.importorskip("sklearn")
    module = importlib.import_module(module_name)
    entry = next(m for m in inventory["modules"] if m["module"] == module_name)
    runner = doctest.DocTestRunner()
    attempted = 0
    for obj in entry["objects"]:
        if obj["audience"] != "public" or "Examples\n--------" not in obj["docstring"]:
            continue
        test = doctest.DocTestParser().get_doctest(
            obj["docstring"], vars(module), obj["path"], entry["path"], obj["line"]
        )
        result = runner.run(test)
        assert result.failed == 0, obj["path"]
        attempted += result.attempted
    assert attempted > 0


def test_lazy_exports_resolve_to_canonical_definitions(inventory):
    exports = {e["export"]: e for e in inventory["export_records"]}
    assert (
        exports["spectralbridge.run_bulk_pipeline"]["canonical"]
        == "spectralbridge.pipelines.bulk.run_bulk_pipeline"
    )
    assert (
        exports["spectralbridge.apply_brightness_correction"]["canonical"]
        == "spectralbridge.brightness.apply_brightness_correction"
    )
    assert exports["spectralbridge.DroneSource"]["kind"] == "constant_or_type_alias"
    assert (
        exports["spectralbridge.bulk.BulkInputMode"]["canonical"]
        == "spectralbridge.bulk.models.BulkInputMode"
    )
    assert (
        json.loads((ROOT / "docs/api/inventory.json").read_text())["schema_version"]
        == 1
    )


def test_data_dependent_examples_bind_to_actual_signatures(inventory):
    checked = 0
    for m in inventory["modules"]:
        for obj in m["objects"]:
            if obj["audience"] != "public" or "doctest: +SKIP" not in obj["docstring"]:
                continue
            scope = {}
            for example in doctest.DocTestParser().get_examples(obj["docstring"]):
                tree = ast.parse(example.source)
                if isinstance(tree.body[0], ast.ImportFrom):
                    statement = tree.body[0]
                    imported = importlib.import_module(statement.module)
                    scope.update(
                        {
                            a.asname or a.name: getattr(imported, a.name)
                            for a in statement.names
                        }
                    )
                if "doctest: +SKIP" in example.source:
                    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
                    function = scope[call.func.id]
                    inspect.signature(function).bind(
                        *[object() for _ in call.args],
                        **{kw.arg: object() for kw in call.keywords},
                    )
                    checked += 1
    assert checked >= 11


def test_runtime_package_exports_are_all_in_the_inventory(inventory):
    import spectralbridge

    recorded = {record["export"] for record in inventory["export_records"]}
    assert {"spectralbridge." + name for name in spectralbridge.__all__} <= recorded


def test_rendered_signature_parser_keeps_defaults_and_argument_kinds():
    spec = importlib.util.spec_from_file_location(
        "check_api_reference", ROOT / "scripts/check_api_reference.py"
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    parsed = checker.Signatures()
    parsed.feed(
        '<div class="doc-signature"><pre><code>sample(<span>a</span>: int=2, *, b=None)</code></pre></div>'
    )
    assert parsed.results == ["sample(a: int=2, *, b=None)"]
    assert checker.arguments(parsed.results[0]) == checker.arguments(
        "sample(a=2, *, b=None)"
    )
    assert checker.arguments(parsed.results[0]) != checker.arguments(
        "sample(a=3, *, b=None)"
    )
    assert checker.arguments(parsed.results[0]) != checker.arguments(
        "sample(a=2, b=None)"
    )
