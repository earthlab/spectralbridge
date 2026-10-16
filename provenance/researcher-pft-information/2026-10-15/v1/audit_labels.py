"""Inventory historical label references and declare the active analysis boundary."""

import csv
import json
import re
from common import BASE, REPO

PATTERN = re.compile(
    r"\b(?:DBS|DBT|EBS|ECS|ECT)\b|inferred_pft|[Ii]nferred PFT|species-derived (?:woody )?PFT"
)


def main():
    rows = []
    roots = ["src/spectralbridge", "examples", "scripts", "docs", "provenance"]
    files = []
    for root in roots:
        files.extend(
            p
            for p in (REPO / root).rglob("*")
            if p.is_file()
            and p.suffix in {".py", ".md", ".csv", ".ipynb", ".json"}
            and "__pycache__" not in p.parts
        )
    files.extend(REPO.glob("*.ipynb"))
    files.extend(
        REPO / p
        for p in [
            "README.md",
            "FINAL_SCIENTIFIC_SYNTHESIS.md",
            "FINAL_READINESS_MATRIX.csv",
            "FINAL_ANALYSIS_AUDIT.md",
        ]
    )
    for p in sorted(set(files)):
        text = p.read_text(errors="replace")
        matches = PATTERN.findall(text)
        if not matches:
            continue
        name = str(p.relative_to(REPO))
        if p.is_relative_to(BASE):
            status = "audit_or_historical_exclusion_text_only"
        elif name.startswith("provenance/") or p.suffix == ".ipynb":
            status = "historical_exploratory_preserved"
        elif name.startswith("docs/"):
            status = "historical_documentation_reference_review"
        elif name.startswith("scripts/generate_scientific_docs"):
            status = "historical_snapshot_generator_retained_new_primary_adapter"
        elif name.startswith(("src/", "examples/")):
            status = "historical_workflow_or_compatibility_utility_not_primary"
        else:
            status = "replace_primary_pointer_or_summary"
        rows.append(
            dict(
                path=name,
                matches=len(matches),
                status=status,
                action="preserve history; researcher-only v1 is canonical",
            )
        )
    with (BASE / "label_system_inventory.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=["path", "matches", "status", "action"])
        w.writeheader()
        w.writerows(rows)
    historical = []
    for name in [
        "provenance/pft",
        "provenance/pft-audit",
        "provenance/publication-figures",
        "provenance/sensor-pft-transfer",
        "provenance/mesma-readiness",
        "provenance/spectral-library-analytics",
        "provenance/scientific-closure",
        "provenance/lab-story",
    ]:
        historical.append(
            dict(
                path=name,
                status="historical_or_superseded_primary",
                reason="may contain retired species-derived grouping; use category-only reusable evidence only",
            )
        )
    registry = {
        "canonical_label_field": "cover_category",
        "canonical_classes": [
            "Deciduous",
            "Evergreen",
            "Herbaceous",
            "Non-vegetated & dead",
            "Woody shrub",
        ],
        "primary_analysis": str(BASE.relative_to(REPO)),
        "primary_entrypoint": "examples/researcher_pft_information.py",
        "historical_material": historical,
        "policy": "Historical builders/artifacts remain frozen for checksum provenance; they are not final primary outputs. New final builder admits recorded researcher categories only.",
    }
    (BASE / "analysis_registry.json").write_text(json.dumps(registry, indent=2) + "\n")
    (
        BASE / "LABEL_SYSTEM_AUDIT.md"
    ).write_text("""# Canonical grouping and historical label audit

The only primary biological field is `cover_category`, with the five recorded
researcher categories. No inferred taxonomic grouping enters the new loader,
feature selectors, prediction labels, mixture fractions, primary figures or
scientific conclusions. A compatibility option in `load_compact_inputs` avoids
constructing historical labels at all for this workflow.

`label_system_inventory.csv` inventories textual references across package code,
examples, scripts, docs, notebooks, prior tables/builders and root final links.
`analysis_registry.json` is the explicit active/historical boundary. Legacy
inference/ML/report builders remain frozen and available for reproduction, not
silently rewritten or deleted. Scientific code shared with those analyses is
retained; a historical implementation is not the primary analysis merely because
it remains importable. Tests may retain historical synthetic fixtures.

Primary entry points, final root pointers and website pages now identify the
recorded researcher categories. Prior reports, including the two-label lab-story
and scientific-closure reports, are superseded for biological interpretation;
they remain historical evidence. Their historical lookup/sensor conclusions must
not be quoted as primary researcher-category findings. The older label crosswalk
and source taxonomic metadata are retained as provenance only.

The new report builder reads only the category-only v1 tables and checks their
class fields. A separate validation scans all primary tabular label values;
mentions of retired codes in this audit or historical warning are not results.
No notebook cells or historical figures/data were deleted. Generic processing,
NEON correction, sensor definitions and production defaults are unchanged.
""")
    print("Inventoried", len(rows), "historical-reference files")


if __name__ == "__main__":
    main()
