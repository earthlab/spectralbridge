"""Refresh Figure4 from the completed pure-pixel expansion, without refitting.

Run from repository root. Verify archived analysis/source hashes, preserve prior
publisher ZIP, replace only HLS evidence/table rows, and use the existing offline
spectral updater. Caption and README describe the new cohort separately.
"""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "publication/figure_4_plant_functional_types"
SOURCE = (
    ROOT
    / "provenance/landsat-pure-pixels/2026-11-18/expanded-search/round-2/power-directed-expansion/review-batch-2/hls-combined"
)
ANALYSIS = SOURCE.parent / "analysis"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    manifest = json.loads((ANALYSIS / "manifest.json").read_text())
    for p, h in manifest["input_sha256"].items():
        if sha(SOURCE / p) != h:
            raise ValueError("Changed reference " + p)
    for p, h in manifest["output_sha256"].items():
        if sha(ANALYSIS / p) != h:
            raise ValueError("Changed analysis " + p)
    source = pd.read_csv(SOURCE / "hls_l30_nominal_95pct_observations.csv")
    summary = pd.read_csv(ANALYSIS / "nominal_primary/figure_table_summary.csv")
    old = pd.read_csv(FIG / "data/pft_separability_and_identifiability.csv")
    before = old[~old.sensor.eq("HLS L30 NBAR")].reset_index(drop=True)
    # Preserve the delivered496cell version once; repeated refresh never overwrites it.
    archive = ROOT / "publication/figure_4_plant_functional_types.zip"
    history = (
        ROOT / "publication/figure_4_plant_functional_types_2026-11-19_496_cells.zip"
    )
    if archive.exists() and not history.exists():
        shutil.copy2(archive, history)
        history.with_suffix(".zip.sha256").write_text(
            sha(history) + "  " + history.name + "\n"
        )
    mappings = {
        SOURCE
        / "hls_l30_nominal_95pct_observations.csv": "landsat_hls_primary_reference_observations.csv",
        SOURCE
        / "hls_l30_strict_source_support_95pct_observations.csv": "landsat_hls_expanded_source_support_reference_observations.csv",
        SOURCE / "expansion_provenance.json": "landsat_hls_expansion_provenance.json",
        ANALYSIS / "manifest.json": "landsat_hls_analysis_manifest.json",
        ANALYSIS / "analysis_design.json": "landsat_hls_current_analysis_design.json",
        ANALYSIS
        / "computation_provenance.json": "landsat_hls_current_computation_provenance.json",
        ANALYSIS / "cohort_comparison.csv": "landsat_hls_cohort_comparison.csv",
    }
    for folder, prefix in [
        ("nominal_primary", "landsat_exploratory"),
        (
            "source_support_sensitivity",
            "landsat_hls_expanded_source_support_sensitivity",
        ),
    ]:
        for name, label in [
            (
                "separability",
                "patch_separability" if folder == "nominal_primary" else "separability",
            ),
            ("held_out_predictions", "held_out_predictions"),
            ("identifiability_summary", "identifiability_summary"),
            ("patch_median_reflectance", "patch_median_spectra"),
        ]:
            mappings[ANALYSIS / folder / (name + ".csv")] = (
                prefix + "_" + label + ".csv"
            )
    mappings[ANALYSIS / "nominal_primary/figure_table_summary.csv"] = (
        "landsat_hls_figure_table_summary.csv"
    )
    mappings[ANALYSIS / "nominal_primary/pairwise_balanced_accuracy.csv"] = (
        "landsat_hls_pairwise_balanced_accuracy.csv"
    )
    mappings[ANALYSIS / "nominal_primary/pairwise_held_patch_predictions.csv"] = (
        "landsat_hls_pairwise_held_patch_predictions.csv"
    )
    # Refresh every existing sensitivity alias, so no161cell summary masquerades
    # as the current362cell sensitivity alongside the new manifest.
    for name in [
        "figure_table_summary",
        "pairwise_balanced_accuracy",
        "pairwise_held_patch_predictions",
        "patch_median_reflectance",
    ]:
        mappings[ANALYSIS / "source_support_sensitivity" / (name + ".csv")] = (
            "landsat_hls_expanded_source_support_sensitivity_" + name + ".csv"
        )
    for path, name in mappings.items():
        shutil.copy2(path, FIG / "evidence" / name)
    for row in summary.itertuples():
        ix = old.sensor.eq("HLS L30 NBAR") & old.category.eq(row.researcher_category)
        if ix.sum() != 1:
            raise ValueError("Need one current HLS row per class")
        values = dict(
            supported_tests=row.supported_pairs,
            total_tests=row.tested_pairs,
            held_out_patch_recall=row.held_patch_recall,
            held_out_patch_correct=row.correct_supported_patches,
            held_out_patch_total=row.held_patches,
            supported_test_patches=row.supported_test_patches,
            planned_pairs=row.planned_pairs,
            evidence_product="HLS L30 v2 NBAR expanded1241cell/61patch nominal95% cohort",
        )
        for key, value in values.items():
            old.loc[ix, key] = value
    old.to_csv(FIG / "data/pft_separability_and_identifiability.csv", index=False)
    subprocess.run(
        [sys.executable, str(FIG / "update_hls_spectral_inputs.py")], check=True
    )
    after = pd.read_csv(FIG / "data/pft_separability_and_identifiability.csv")
    pd.testing.assert_frame_equal(
        before,
        after[~after.sensor.eq("HLS L30 NBAR")].reset_index(drop=True),
        check_exact=False,
        atol=1e-14,
        rtol=1e-14,
    )
    path = FIG / "provenance.json"
    record = json.loads(path.read_text())
    record["updated"] = "2026-11-20"
    record["observations"]["HLS L30 NBAR"] = len(source)
    record["source_items"] = sorted(source.hls_item_id.unique())
    record["panel_b_landsat"].update(
        cohort_cells=len(source),
        spatial_patch_groups=source.patch_group_id.nunique(),
        new_references=dict(
            cells=745,
            spatial_patches=37,
            selection="Two fixed cover/structure-reviewed batches, without selection by spectral or test outcomes",
        ),
        unique_testable_pairs=10,
        supported_pooled_pairs=10,
        five_class_patch_accuracy="58/61 (95.1%)",
        source_area_sensitivity=dict(
            cells=362,
            patches=30,
            supported_pooled_pairs=6,
            five_class_accuracy="28/30 (93.3%)",
            limitation="Conservative unweighted120m source-area sensitivity; not standard HLS purity or a confidence bound",
        ),
        pairwise_predictive_diagnostic="mean balanced accuracy99.7%; point estimate, not significance or validation",
        panel_a="same1241HLS cells/61patches; normalized cell medians/IQR/counts; no C2",
        within_region=dict(
            testable_pairs=3,
            supported_pairs=2,
            unsupported_pairs=7,
            limitation="Pooled10/10 is strongly region/season confounded; new-region generalization not established",
        ),
    )
    record["panel_b_landsat"]["primary_classes"] = {
        r.researcher_category: dict(
            cells=int(source.researcher_category.eq(r.researcher_category).sum()),
            patches=int(r.held_patches),
            supported_testable_pairs=f"{r.supported_pairs}/{r.tested_pairs}",
            held_patch_recall=f"{r.correct_supported_patches}/{r.held_patches}",
        )
        for r in summary.itertuples()
    }
    spectral = json.loads((FIG / "hls_spectral_update_manifest.json").read_text())
    record["spectral_panels"].update(
        primary_cells=len(source),
        patch_groups=source.patch_group_id.nunique(),
        class_counts=spectral["class_counts"],
        source_sha256=spectral["source_sha256"],
    )
    record["pure_pixel_expansion_refresh"] = dict(
        date="2026-11-20",
        code_sha256=sha(Path(__file__)),
        source=str(SOURCE.relative_to(ROOT)),
        analysis_manifest_sha256=sha(ANALYSIS / "manifest.json"),
        source_manifest_sha256=sha(SOURCE / "expansion_provenance.json"),
        previous_publisher_archive=str(history.relative_to(ROOT)),
        non_hls_table_values_preserved=True,
        protocol="Unchanged existing7band NPC/whole-patch LOPO; separate BRDF audit scores not substituted",
    )
    for p in [
        SOURCE / "hls_l30_nominal_95pct_observations.csv",
        ANALYSIS / "manifest.json",
        Path(__file__),
    ]:
        relative = str(p.relative_to(ROOT))
        existing = next(
            (
                x
                for x in record["source_files"]
                if x["repository_relative_path"] == relative
            ),
            None,
        )
        if existing is None:
            record["source_files"].append(
                dict(repository_relative_path=relative, sha256=sha(p))
            )
        else:
            existing["sha256"] = sha(p)
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(
        "Figure4HLS inputs refreshed:",
        len(source),
        "cells/",
        source.patch_group_id.nunique(),
        "patches",
    )


if __name__ == "__main__":
    run()
