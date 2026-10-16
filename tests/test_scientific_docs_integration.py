"""Offline evidence, documentation, API example and publication-composition checks."""

from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd
import pytest
import yaml

from spectralbridge.landsat_agreement import compute_agreement_metrics, spectral_angle
from scripts.generate_scientific_docs import generated_files

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests/data/scientific_regression"
pytestmark = [pytest.mark.scientific, pytest.mark.regression]


def test_frozen_derived_real_landsat_fixture_reproduces_measured_summaries():
    fixture = json.loads((DATA / "landsat_derived.json").read_text())
    real, synthetic = np.array(fixture["real"]), np.array(fixture["synthetic"])
    expected = fixture["expected"]
    np.testing.assert_allclose(
        np.sqrt(np.mean((synthetic - real) ** 2)), expected["pooled_RMSE"], rtol=1e-12
    )
    np.testing.assert_allclose(
        (synthetic - real).mean(), expected["mean_bias"], atol=1e-14
    )
    np.testing.assert_allclose(
        np.median(spectral_angle(real, synthetic)),
        expected["median_angle_deg"],
        atol=1e-9,
    )
    for j in range(7):
        result = compute_agreement_metrics(real[:, j], synthetic[:, j])
        np.testing.assert_allclose(result["RMSE"], expected["band_RMSE"][j], rtol=1e-12)
        assert result["N"] == 6


def test_frozen_pft_evidence_has_not_been_silently_revised():
    fixture = json.loads((DATA / "pft_transfer.json").read_text())
    source = ROOT / fixture["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == fixture["source_sha256"]
    data = pd.read_csv(source).query("scheme=='inferred_pft'")
    expected = pd.DataFrame(fixture["records"])
    pd.testing.assert_frame_equal(
        data[expected.columns].reset_index(drop=True),
        expected,
        check_exact=False,
        rtol=1e-12,
    )
    assert len(data) == fixture["eligible"] == 21
    assert data.NEON_supported.sum() == fixture["NEON_supported"] == 16
    assert (data.NEON_supported & data.OLI_supported).sum() == fixture["retained"] == 15
    assert data.query("contrast=='DBT / ECS'").NEON_supported.eq(False).all()
    assert data.query("contrast=='DBS / ECT'").NEON_supported.all()


def test_generated_scientific_pages_and_images_match_verified_sources():
    for path, expected in generated_files().items():
        assert path.read_bytes() == expected, path


def test_scientific_navigation_and_accessible_local_figures():
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text())

    def paths(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for x in value:
                yield from paths(x)
        elif isinstance(value, dict):
            for x in value.values():
                yield from paths(x)

    navigation = set(paths(config["nav"]))
    critical = [
        "spectral-library/index.md",
        "spectral-library/atlas.md",
        "spectral-library/labels.md",
        "spectral-library/biological-variation.md",
        "spectral-library/sensor-transfer.md",
        "spectral-library/mesma-readiness.md",
        "validation/landsat-pilot.md",
        "validation/pft-methods.md",
        "validation/scientific-validation.md",
        "api/scientific-analysis.md",
        "dev/scientific-testing.md",
    ]
    assert set(critical) <= navigation
    for name in critical:
        page = ROOT / "docs" / name
        assert page.is_file()
        for alt, url in re.findall(r"!\[([^\]]*)\]\(([^)]*)\)", page.read_text()):
            assert len(alt) > 30
            assert not url.startswith("http"), (
                "Scientific docs must build without a remote image dependency"
            )
            assert (page.parent / url).resolve().is_file()


def test_offline_package_example_executes_and_keeps_original_table(tmp_path):
    import subprocess
    import sys

    # Run as a real installed-package user would, isolated from legacy tests
    # that temporarily replace optional IO modules in the parent interpreter.
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,sys; from pathlib import Path; "
            "from examples.scientific_workflows_offline import run_example; "
            "print(json.dumps(run_example(Path(sys.argv[1]))))",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(process.stdout)
    assert result["atlas_plants"] == result["independent_plants"] == 2
    assert result["pixel_rows"] == 6
    assert result["identity_RMSE"] < 1e-12
    np.testing.assert_allclose(result["OLI_values"], 0.2, atol=1e-12)
    assert (tmp_path / "teaching.parquet").stat().st_size > 0


def test_documented_small_python_snippet_executes():
    text = (ROOT / "docs/api/scientific-analysis.md").read_text()
    code = re.search(r"```python\n(.*?)```", text, re.S).group(1)
    scope = {}
    exec(compile(code, "docs/api/scientific-analysis.md", "exec"), scope)
    assert scope["oli"].shape == (1, 7)
    assert scope["metrics"]["RMSE"] < 1e-12


@pytest.mark.integration
def test_both_publication_figures_compose_offline_without_original_archive(tmp_path):
    # Toy atlas panels + frozen canonical contrast/pilot records; temporary smoke
    # outputs are test inputs, not replacement scientific publication figures.
    from examples.publication_figures.figure_data import CATEGORIES, weighted_pca
    from examples.publication_figures.figure_panels import style
    from examples.publication_figures.build_spectral_library_figures import (
        build_figure1,
        build_figure2,
    )

    fixture = json.loads((DATA / "pft_transfer.json").read_text())
    effects = pd.DataFrame(fixture["records"])
    effects["a"] = effects.contrast.str.split(" / ").str[0]
    effects["b"] = effects.contrast.str.split(" / ").str[1]
    w = np.r_[
        np.arange(400, 901, 25), np.arange(1500, 1751, 25), np.arange(2100, 2301, 25)
    ]
    rng = np.random.default_rng(42)
    y = rng.uniform(0.1, 0.4, size=(10, len(w)))
    # PCA helper expects max-gap=8, so use the established 5 nm support here.
    w = np.r_[
        np.arange(400, 901, 5), np.arange(1500, 1751, 5), np.arange(2100, 2301, 5)
    ]
    y = rng.uniform(0.1, 0.4, size=(10, len(w)))
    table = pd.DataFrame(
        {
            "cover_category": CATEGORIES * 2,
            "site": ["NIWO", "WREF", "YELL", "NIWO", "WREF"] * 2,
            "year": [2023] * 10,
        }
    )
    scores, variance, _ = weighted_pca(y, w)
    local = pd.DataFrame(
        [
            dict(
                contrast=a + " / ECT",
                wavelength_nm=x,
                standardized_delta=np.sin(x / 100),
                excursion_family=True,
            )
            for a in ["DBS", "DBT"]
            for x in w
        ]
    )
    pilot = json.loads((DATA / "landsat_derived.json").read_text())
    real = np.array(pilot["real"]).T.reshape(7, 2, 3)
    synthetic = np.array(pilot["synthetic"]).T.reshape(7, 2, 3)
    from scipy.stats import pearsonr, spearmanr

    correlations = pd.DataFrame(
        {
            "method": ["Pearson", "Spearman"],
            "correlation": [
                pearsonr(effects.NEON_effect, effects.OLI_effect).statistic,
                spearmanr(effects.NEON_effect, effects.OLI_effect).statistic,
            ],
        }
    )
    d = dict(
        table=table,
        spectra={"NEON": y, "OLI": rng.uniform(0.1, 0.4, (10, 7))},
        waves={"NEON": w},
        counts=dict(
            identities=10,
            pixel_rows=30,
            polygon_years=10,
            species_identified=10,
            species_missing=0,
            sites=3,
            years=1,
            cover_categories=5,
        ),
        representatives=dict(zip(CATEGORIES, range(5))),
        scores=scores,
        variance=variance,
        effects=effects,
        localization=local,
        correlations=correlations,
        retention=pd.Series({"retained": 15, "NEON_supported": 16}),
        oli_centers=np.array([443, 482, 561.4, 654.6, 864.7, 1608.9, 2200.7]),
        images={
            "actual": real,
            "undarkened": synthetic,
            "common": np.ones((2, 3), bool),
        },
        grid={"transform": [30, 0, 0, 0, -30, 60]},
        flight=pd.Series(
            {
                "pooled_seven_band_RMSE": pilot["expected"]["pooled_RMSE"],
                "median_spectral_angle_deg": pilot["expected"]["median_angle_deg"],
                "N": 6,
            }
        ),
        metrics=pd.DataFrame(
            {
                "Pearson_r": [
                    compute_agreement_metrics(real[j].ravel(), synthetic[j].ravel())[
                        "Pearson_r"
                    ]
                    for j in range(7)
                ]
            }
        ),
    )
    style()
    build_figure1(d, tmp_path)
    build_figure2(d, tmp_path)
    for name in ["Figure_1_spectral_library", "Figure_2_ecological_information"]:
        for ext in ["pdf", "png", "svg"]:
            path = tmp_path / (name + "." + ext)
            assert path.is_file() and path.stat().st_size > 1000


def test_closure_snapshot_rejects_modified_source_table(tmp_path):
    import shutil
    from scripts.generate_scientific_docs import closure_generated_files

    relative = Path("provenance/scientific-closure/2026-10-15")
    base = tmp_path / relative
    (base / "tables").mkdir(parents=True)
    (base / "manifests").mkdir()
    (base / "figures").mkdir()
    for name in [
        "biological_generalization.csv",
        "paired_temporal_recognition.csv",
        "closed_set_coverage.csv",
    ]:
        shutil.copyfile(ROOT / relative / "tables" / name, base / "tables" / name)
    shutil.copyfile(
        ROOT / relative / "manifests/report_manifest.json",
        base / "manifests/report_manifest.json",
    )
    shutil.copyfile(
        ROOT / relative / "figures/F2_temporal_resolution.png",
        base / "figures/F2_temporal_resolution.png",
    )
    outputs = closure_generated_files(tmp_path)
    assert b"closed-set" in outputs[tmp_path / "docs/spectral-library/_closure.md"]
    with (base / "tables/biological_generalization.csv").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="Changed closure evidence"):
        closure_generated_files(tmp_path)


def test_researcher_primary_snapshot_rejects_changed_results(tmp_path):
    from scripts.generate_scientific_docs import researcher_generated_files

    base = tmp_path / "provenance/researcher-pft-information/2026-10-15/v1"
    (base / "tables").mkdir(parents=True)
    (base / "figures").mkdir()
    features = pd.DataFrame(
        [
            dict(kind=k, budget=b, balanced_accuracy=v)
            for k in ["plant", "site"]
            for b, v in [("360", 0.8), ("OLI", 0.6)]
        ]
    )
    abundance = pd.DataFrame(
        [
            dict(
                kind=k,
                method=m,
                representation="NEON",
                fold="example",
                target="target",
                RMSE=v,
            )
            for k in ["plant", "site"]
            for m, v in [("MESMA", 0.4), ("Ridge", 0.2)]
        ]
    )
    features.to_csv(base / "tables/complementary_feature_performance.csv", index=False)
    abundance.to_csv(base / "tables/abundance_model_comparison.csv", index=False)
    raw = b"fixture image bytes"
    (base / "figures/R03_single_wavelength_prediction.png").write_bytes(raw)
    table_hashes = {
        f"tables/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (base / "tables").iterdir()
    }
    (base / "report_manifest.json").write_text(
        json.dumps(
            {
                "table_hashes": table_hashes,
                "figure_hashes": {
                    "figures/R03_single_wavelength_prediction.png": hashlib.sha256(
                        raw
                    ).hexdigest()
                },
            }
        )
    )
    outputs = researcher_generated_files(tmp_path)
    text = outputs[
        tmp_path / "docs/spectral-library/_researcher_information.md"
    ].decode()
    assert "80.0%" in text and "0.200" in text
    assert "DBS" not in text and "DBT" not in text
    (base / "tables/abundance_model_comparison.csv").write_text("changed")
    with pytest.raises(ValueError, match="Changed canonical researcher evidence"):
        researcher_generated_files(tmp_path)
