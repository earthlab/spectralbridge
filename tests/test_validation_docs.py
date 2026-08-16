from __future__ import annotations

from pathlib import Path

from scripts import generate_validation_docs
from scripts.validation_docs_content import (
    MODULE_GUIDES,
    STAGE_CHECK_GUIDES,
    STAGE_GUIDES,
    stage_check_guide_key,
)


ROOT = Path(__file__).resolve().parents[1]


def test_every_recorded_validation_field_has_a_human_explanation() -> None:
    grouped = generate_validation_docs._group_results(
        generate_validation_docs._campaigns()
    )

    for module, results in grouped.items():
        guide = MODULE_GUIDES[module]
        observed_inputs = {
            name for result in results for name in result.get("inputs", {})
        }
        observed_checks = {
            name for result in results for name in result.get("checks", {})
        }
        observed_diagnostics = {
            name for result in results for name in result.get("diagnostics", {})
        }

        assert observed_inputs <= {field.name for field in guide.inputs}
        assert observed_checks <= {check.name for check in guide.checks}
        assert observed_diagnostics <= {field.name for field in guide.diagnostics}


def test_every_real_stage_check_family_is_documented() -> None:
    reports = generate_validation_docs._real_stage_reports()

    assert set(reports) == {stage["stage_id"] for stage in STAGE_GUIDES}
    for _, report in reports.values():
        for check in report["checks"]:
            key = stage_check_guide_key(str(check["check_id"]))
            assert key in STAGE_CHECK_GUIDES


def test_validation_example_images_exist() -> None:
    images = {image.path for guide in MODULE_GUIDES.values() for image in guide.images}

    assert images
    for relative_path in images:
        assert (ROOT / "docs" / "validation" / relative_path).is_file()


def test_generated_validation_pages_are_current_and_detailed() -> None:
    generated = generate_validation_docs.generated_files()

    assert ROOT / "docs" / "validation" / "stage-qa-guide.md" in generated
    for path, expected in generated.items():
        assert path.read_text(encoding="utf-8") == expected.rstrip() + "\n"
    for slug, guide in MODULE_GUIDES.items():
        page = generated[ROOT / "docs" / "validation" / f"{slug}.md"]
        for check in guide.checks:
            assert f"`{check.name}`" in page
        for image in guide.images:
            assert image.path in page


def test_nested_validation_pages_link_back_to_shared_artifacts() -> None:
    generated = generate_validation_docs.generated_files()
    nested_pages = [
        content for path, content in generated.items() if path.name != "index.md"
    ]

    for page in nested_pages:
        assert 'src="artifacts/' not in page
        assert 'href="artifacts/' not in page
        if "artifacts/r10c-l002-20210915" in page:
            assert "../artifacts/r10c-l002-20210915" in page
