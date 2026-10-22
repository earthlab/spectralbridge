"""Independent compact-table, provenance and PDF contract checks for the briefing.

No fitting and no raw-library access. Run with pypdf/pdfplumber for the PDF checks.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
OLD = ROOT / "provenance/researcher-pft-information/2026-10-15/v1"
NEW = ROOT / "provenance/researcher-evidence/2026-10-16/v1"
END = ROOT / "provenance/endmember-quality/2026-10-19/v1"
EXH = END.parent / "exhaustive-v1"


def js(path):
    return json.loads(Path(path).read_text())


def rows(packet, name):
    with (packet / "tables" / name).open(newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_claims():
    """Reaggregate the saved CSV/JSON values without importing the figure builder."""
    f = js(NEW / "foundation.json")
    expected = {
        k: f[k]
        for k in [
            "polygon_GlobalIDs",
            "polygon_year_spectra",
            "repeated_IDs",
            "NEON_coordinates",
            "OLI_channels",
            "source_pixel_rows",
        ]
    }
    cell = rows(NEW, "site_year_category_support.csv")
    expected.update(
        sites=len({r["site"] for r in cell}),
        site_year_cells=len({(r["site"], r["year"]) for r in cell}),
    )
    whole = rows(NEW, "whole_spectrum_separability.csv")
    expected.update(
        supported_contrasts=sum(r["NEON_supported"] == "True" for r in whole),
        pairs=len({r["contrast"] for r in whole}),
        largest_adjusted_p=max(float(r["NEON_p_holm"]) for r in whole),
    )
    assert all(
        r["NEON_supported"] == "True" and r["OLI_supported"] == "True" for r in whole
    )
    perf = rows(OLD, "complementary_feature_performance.csv")
    for sensor, budget in [("NEON", "360"), ("Synthetic OLI", "OLI")]:
        for kind in ["plant", "site"]:
            v = [
                float(r["balanced_accuracy"])
                for r in perf
                if r["kind"] == kind and r["budget"] == budget
            ]
            assert len(v) == 3
            expected[f"{sensor}_{kind}"] = statistics.mean(v)
    categories = list(js(BASE / "figure_manifest.json")["pft_colors"])
    recalls = rows(OLD, "class_specific_transfer.csv")
    for cat in categories:
        expected["recall_" + cat] = statistics.mean(
            float(r["recall"])
            for r in recalls
            if r["kind"] == "site"
            and r["budget"] == "360"
            and r["researcher_category"] == cat
        )
    confusion = [
        r
        for r in rows(OLD, "confusion_plot_values.csv")
        if r["representation"] == "NEON" and r["kind"] == "site"
    ]
    for cat in categories:
        v = [r for r in confusion if r["truth"] == cat]
        assert math.isclose(
            sum(float(r["mean_fold_row_fraction"]) for r in v), 1, abs_tol=1e-10
        )
        assert math.isclose(
            next(
                float(r["mean_fold_row_fraction"]) for r in v if r["predicted"] == cat
            ),
            expected["recall_" + cat],
            abs_tol=1e-10,
        )
    expected["shrub_to_deciduous"] = next(
        float(r["mean_fold_row_fraction"])
        for r in confusion
        if r["truth"] == "Woody shrub" and r["predicted"] == "Deciduous"
    )
    selected = js(END / "summary.json")
    for k in [
        "selected_members",
        "selected_polygon_IDs",
        "selected_macro_same_class_RMSE",
        "selected_single_reference_BA",
        "matched_random_macro_same_class_RMSE_mean",
        "matched_random_single_reference_BA_mean",
        "target_polygon_IDs",
        "target_curves",
    ]:
        expected[k] = selected[k]
    random = rows(END, "coverage_random.csv")
    assert len(random) == 30 * len(categories)
    hull = rows(END, "cross_class_hull.csv")
    assert len(hull) == selected["selected_members"]
    expected["ambiguous"] = sum(r["feasible"] == "True" for r in hull)
    abundance = rows(NEW, "abundance_domain_summary.csv")
    fair = rows(NEW, "same_candidate_ridge.csv")
    for kind in ["plant", "site"]:
        for label, method in [
            ("ridge120", "Ridge"),
            ("MESMA15", "MESMA"),
            ("prior", "Training prior"),
        ]:
            expected[f"{kind}_{label}"] = next(
                float(r["mean"])
                for r in abundance
                if r["kind"] == kind
                and r["representation"] == "NEON"
                and r["method"] == method
            )
        expected[f"{kind}_ridge15"] = statistics.mean(
            float(r["RMSE"])
            for r in fair
            if r["kind"] == kind and r["representation"] == "NEON"
        )
    for method in ["Ridge", "Training prior"]:
        expected["year_" + method] = next(
            float(r["mean"])
            for r in abundance
            if r["kind"] == "year"
            and r["representation"] == "NEON"
            and r["method"] == method
        )
    exhaustive = js(EXH / "comparison_summary.json")
    for k in [
        "targets",
        "model_count",
        "fraction_RMSE",
        "mean_screened_spectral_RMSE",
        "mean_exhaustive_spectral_RMSE",
        "lower_fraction_error_targets",
        "higher_fraction_error_targets",
        "unchanged_fraction_error_targets",
    ]:
        expected["exhaustive_" + k] = exhaustive[k]
    assert (
        exhaustive["max_components"] == 3 and exhaustive["one_reference_per_category"]
    )
    expected["screened_fraction_RMSE"] = selected["synthetic_RMSE"][
        "Selected screened MESMA"
    ]
    expected["spectral_reduction_pct"] = 100 * (
        1
        - exhaustive["mean_exhaustive_spectral_RMSE"]
        / exhaustive["mean_screened_spectral_RMSE"]
    )
    comparison = next(
        r
        for r in exhaustive["paired_comparisons"]
        if r["comparator"] == "Screened selected (3/category)"
    )
    for k in ["conditional_bundle_bootstrap_2_5", "conditional_bundle_bootstrap_97_5"]:
        expected[k] = comparison[k]
    for label, key in [
        ("oracle", "Known-parent FCLS oracle"),
        ("sparse_prior", "Sparse design prior"),
        ("dense_prior", "Uniform design prior"),
    ]:
        expected[label] = selected["synthetic_RMSE"][key]
    return expected


def validate_claims(claims, expected):
    ids = [r["id"] for r in claims]
    assert len(set(ids)) == len(ids), "Duplicate numeric claim IDs"
    assert set(ids) == set(expected), "Missing or unexpected claim IDs"
    for r in claims:
        assert math.isclose(
            float(r["value"]), float(expected[r["id"]]), rel_tol=1e-12, abs_tol=1e-14
        ), r["id"]
        assert (ROOT / r["source"]).is_file(), r["source"]
        assert r["selection"] and r["scope"], r["id"]


def main():
    from pypdf import PdfReader
    import pdfplumber

    manifest = js(BASE / "figure_manifest.json")
    report = js(BASE / "report_manifest.json")
    claims = js(BASE / "claims.json")
    validate_claims(claims, expected_claims())
    # Check against each authoritative, previously sealed result ledger, not just
    # new hashes that could conceal a changed source.
    authoritative = {}
    for packet, key, relative in [
        (OLD, "sha256", False),
        (NEW, "sha256", False),
        (END, "sha256", False),
        (EXH, "files", True),
    ]:
        name = "final_manifest.json" if packet in (OLD, NEW) else "packet_manifest.json"
        for path, digest in js(packet / name)[key].items():
            authoritative[(packet / path if relative else ROOT / path).resolve()] = (
                digest
            )
    for path, record in manifest["sources"].items():
        full = ROOT / path
        if path.endswith("corr_polygon_year.parquet"):
            ledger = js(full.parent.parent / "statistics_manifest.json")
            authoritative[full.resolve()] = ledger["outputs"][
                "compact/corr_polygon_year.parquet"
            ]
        assert sha(full) == record["sha256"] == authoritative[full.resolve()], path
    assert sha(BASE / "build_figures.py") == manifest["source_builder_sha256"]
    assert sha(BASE / "build_report.py") == report["report_builder_sha256"]
    assert sha(BASE / "figure_manifest.json") == report["figure_manifest_sha256"]
    assert len(manifest["figures"]) == 9
    content = js(BASE / "report_content.json")
    claim_ids = {r["id"] for r in claims}
    for f, page in zip(manifest["figures"], content["pages"]):
        assert page["figure"] == f["number"]
        assert set(page["claims"]) <= claim_ids, (
            f["number"],
            set(page["claims"]) - claim_ids,
        )
        assert all(s in manifest["sources"] for s in f["sources"])
        assert page["caption"].count(f"Figure {f['number']}.") == 1
        for ext in ["png", "svg"]:
            assert (
                sha((ROOT / f["filename"]).with_suffix("." + ext)) == f["sha256"][ext]
            )
    pdf = ROOT / report["output"]
    assert sha(pdf) == report["sha256"]
    reader = PdfReader(pdf)
    assert len(reader.pages) == 11
    texts = [p.extract_text() or "" for p in reader.pages]
    alltext = "\n".join(texts)
    for forbidden in [
        "C3 grass",
        "C4 grass",
        "taxonomic",
        "PCA results",
        "validated field abundance",
    ]:
        assert forbidden not in alltext, forbidden
    for text in ["Separability", "Identifiability", "Abundance"]:
        assert text.upper() in alltext.upper()
    assert "real-world abundance accuracy is not established" in alltext.replace(
        "\n", " "
    )
    assert "85.2%" in texts[4] and "73.8%" in texts[4]
    assert "94.2%" in texts[5] and "46.3%" in texts[5]
    assert "NEON p-value was 0.004" in texts[2].replace("\n", " ")
    assert "0.322 to 0.334" in texts[9].replace("\n", " ")
    for cat in manifest["pft_colors"]:
        assert cat in texts[0]
    for i, page in enumerate(texts[1:10], 1):
        assert page.count(f"Figure {i}.") == 1
        assert "WHAT THIS TELLS US" in page
    # PDF text/image bounds are a supplement to, not a substitute for visual QA.
    with pdfplumber.open(pdf) as document:
        for i, page in enumerate(document.pages, 1):
            for ch in page.chars:
                assert 17 <= ch["x0"] <= ch["x1"] <= 595, (i, ch)
                assert 15 <= ch["top"] <= ch["bottom"] <= 780, (i, ch)
            if 2 <= i <= 10:
                assert page.images
                for im in page.images:
                    assert im["width"] > 400 and im["height"] > 250, (i, im)
    # Historic collaborator reports must remain byte-identical to the source
    # revision recorded on every report page.
    historic = [
        ROOT / "output/pdf/lab_story/SpectralBridge_The_Visual_Scientific_Story.pdf",
        ROOT
        / "output/pdf/scientific_closure/What_Can_We_Reliably_Learn_from_the_SpectralBridge_Spectral_Library.pdf",
        ROOT
        / "output/pdf/researcher_pft_information/Researcher_Categories_Spectral_Information_and_Abundance.pdf",
        ROOT
        / "output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf",
        END / "ENDMEMBER_QUALITY_REPORT.md",
        EXH / "EXHAUSTIVE_MESMA_REPORT.md",
    ]
    preserved = {}
    for path in historic:
        rel = str(path.relative_to(ROOT))
        prior = subprocess.run(
            ["git", "show", f"{manifest['git_commit']}:{rel}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(prior).hexdigest() == sha(path), rel
        preserved[rel] = sha(path)
    result = {
        "status": "PASS",
        "pages": 11,
        "scientific_figures": 9,
        "independently_rechecked_numeric_claims": len(claims),
        "verified_source_files": len(manifest["sources"]),
        "historic_reports_preserved": preserved,
        "visual_QA": "External manual check; see VISUAL_QA.md for the inspected PDF fingerprint and page record.",
        "checks": [
            "55 numeric claims independently reaggregated from CSV/JSON",
            "20 input files match historical authoritative ledgers",
            "9 PNG/SVG pairs and builder/report fingerprints",
            "PDF headings, dynamic display values and category labels",
            "All text/image bounds and large figure dimensions",
            "Six earlier collaborator reports unchanged against recorded Git revision",
        ],
        "raw_library_read": False,
        "model_refits": False,
    }
    (BASE / "validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"PASS: {len(reader.pages)} pages, 9 figures, {len(claims)} numeric claims, {len(manifest['sources'])} sealed sources; six prior reports unchanged."
    )


if __name__ == "__main__":
    main()
