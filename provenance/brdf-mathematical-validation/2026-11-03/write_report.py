"""Refresh the report's measured numerical table without rewriting its narrative."""

import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPORT = HERE.parents[2] / "docs/reports/BRDF_MATHEMATICAL_VALIDATION.md"


def main():
    results = json.loads((HERE / "independent_reference_results.json").read_text())
    table = "| Kernel | Maximum absolute error through 80° | Maximum error / (1 + absolute reference), all cases |\n|---|---:|---:|\n"
    for kernel, row in results["errors"].items():
        table += f"| {kernel} | {row['max_absolute_error_through_80_degrees']:.3g} | {row['maximum_error_scaled_by_one_plus_absolute_expected']:.3g} |\n"
    block = (
        "<!-- numerical-validation:start -->\n"
        + table
        + "<!-- numerical-validation:end -->"
    )
    text = REPORT.read_text()
    if "@ERROR_TABLE@" in text:
        text = text.replace("@ERROR_TABLE@", block)
    else:
        text = re.sub(
            r"<!-- numerical-validation:start -->.*?<!-- numerical-validation:end -->",
            lambda _: block,
            text,
            flags=re.S,
        )
    REPORT.write_text(text)


if __name__ == "__main__":
    main()
