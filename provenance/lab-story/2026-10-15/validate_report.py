"""Validate curated claims, source hashes, PDF structure and reconstruction."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pdfplumber
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
CLOSE = REPO / "provenance/scientific-closure/2026-10-15/tables"
PRIOR = REPO / "provenance/spectral-library-analytics/2026-10-14/tables"
checks = []


def close(name, actual, expected, tolerance=0.00051):
    assert abs(float(actual) - expected) <= tolerance, (name, actual, expected)
    checks.append(
        dict(claim=name, actual=float(actual), expected=expected, tolerance=tolerance)
    )


def main():
    manifest = json.loads((BASE / "evidence_manifest.json").read_text())
    pdf = REPO / manifest["pdf"]
    before = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert before == manifest["pdf_sha256"]
    for name, digest in manifest["inputs"].items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest, name
    # Verify selected legacy assets against their sealed earlier ledgers too.
    legacy = {}
    old = json.loads(
        (
            REPO
            / "provenance/scientific-closure/2026-10-15/manifests/final_evidence.json"
        ).read_text()
    )
    legacy.update(old["files"])
    old = json.loads(
        (
            REPO
            / "provenance/spectral-library-analytics/2026-10-14/evidence_manifest.json"
        ).read_text()
    )
    legacy.update(
        {
            "provenance/spectral-library-analytics/2026-10-14/" + k: v
            for k, v in old["outputs"].items()
        }
    )
    old = json.loads(
        (
            REPO / "provenance/publication-figures/2026-10-14/evidence_manifest.json"
        ).read_text()
    )
    legacy.update(old["owned_files"])
    verified_legacy = 0
    for name, digest in manifest["inputs"].items():
        if name in legacy:
            assert digest == legacy[name], name
            verified_legacy += 1
    assert verified_legacy >= 20, verified_legacy
    src = json.loads((BASE / "report_source.json").read_text())
    assert len(src["figures"]) == 23
    assert len({f["image"] for f in src["figures"]}) == 23
    pages = PdfReader(pdf).pages
    assert len(pages) == 29
    for n, item in enumerate(src["figures"], 1):
        text = pages[n + 2].extract_text()
        assert f"Figure {n}. {item['title']}" in text
        for heading in (
            "HOW TO READ IT",
            "WHAT TO UNDERSTAND",
            "WHAT IT DOES NOT ESTABLISH",
        ):
            assert heading in text, (n, heading)
        assert pages[n + 2]["/Resources"].get("/XObject"), n
    outside = []
    with pdfplumber.open(pdf) as doc:
        for n, page in enumerate(doc.pages, 1):
            for word in page.extract_words():
                if (
                    word["x0"] < 0
                    or word["x1"] > page.width + 0.5
                    or word["top"] < 0
                    or word["bottom"] > page.height + 0.5
                ):
                    outside.append((n, word["text"]))
    assert not outside, outside
    g = pd.read_csv(CLOSE / "biological_generalization.csv")
    g = g[
        g.probability.eq("raw")
        & g.experiment.eq("hierarchy")
        & g["mode"].eq("stored")
        & g.representation.eq("NEON_full")
    ]
    for scheme, kind, expected in [
        ("species_level", "plant", 0.717),
        ("species_level", "site", 0.474),
        ("researcher_level", "plant", 0.858),
        ("researcher_level", "site", 0.725),
        ("broad_pft", "plant", 0.967),
        ("broad_pft", "site", 0.901),
    ]:
        close(
            f"{scheme}_{kind}_BA",
            g[g.scheme.eq(scheme) & g.kind.eq(kind)].balanced_accuracy.mean(),
            expected,
        )
    s = pd.read_csv(CLOSE / "brightness_sampling_sensitivity.csv")
    for mode, expected in [("shape", 0.926), ("amplitude", 0.674)]:
        close(
            "broad_site_" + mode,
            s[
                s.scheme.eq("broad_pft") & s.kind.eq("site") & s["mode"].eq(mode)
            ].sensitivity_BA.mean(),
            expected,
        )
    p = pd.read_csv(CLOSE / "paired_temporal_recognition.csv")
    for scheme, year, expected in [
        ("species_level", 2020, 0.639),
        ("species_level", 2023, 0.300),
        ("broad_pft", 2020, 0.959),
        ("broad_pft", 2023, 0.863),
    ]:
        q = p[
            p.scheme.eq(scheme)
            & p.representation.eq("NEON_full")
            & p.training_year.eq(2020)
            & p.test_year.eq(year)
        ]
        close(f"paired_train2020_{scheme}_{year}", q.balanced_accuracy.mean(), expected)
    c = pd.read_csv(CLOSE / "closed_set_coverage.csv")
    close(
        "species_WREF_target_coverage",
        c[
            c.level.eq("species_level") & c.fold.eq("site_WREF")
        ].closed_set_fraction.iloc[0],
        0.243,
    )
    a = pd.read_csv(REPO / "output/pdf/plant_spectral_review/accuracy_intervals.csv")
    for stage, expected in [
        ("raw", 0.18181818),
        ("corr", 0.15702479),
        ("olioli", 0.20936639),
        ("micasense", 0.12947658),
    ]:
        q = a[a.scope.eq("ALL") & a.stage.eq(stage)]
        close("early_match_" + stage, q.accuracy.iloc[0], expected, 1e-7)
        assert q.n.iloc[0] == 363
    r = pd.read_csv(
        REPO / "provenance/sensor-pft-transfer/2026-10-14/retention_summary.csv"
    )
    r = r[r.scheme.eq("inferred_pft")].iloc[0]
    close("retained_NEON_supported_inferred_contrasts", r.retained, 15, 0)
    close("median_effect_ratio", r.median_effect_ratio, 0.824039665, 1e-8)
    close("effect_ratio_interval_low", r.median_ratio_lo, 0.801403302, 1e-8)
    close("effect_ratio_interval_high", r.median_ratio_hi, 0.888761521, 1e-8)
    assert r.dark_max_delta_error < 8.8e-8
    u = pd.read_csv(PRIOR / "unknown_material_detection.csv")
    u = u[
        u.scheme.eq("inferred_pft")
        & u.representation.eq("NEON_full")
        & u.detector.eq("nearest_angle_deg")
    ]
    close("unknown_recall", u.unknown_recall.mean(), 0.164552)
    close("known_false_rejection", u.known_false_rejection.mean(), 0.037473)
    u = pd.read_csv(PRIOR / "uncertainty_calibration.csv")
    u = u[
        u.scheme.eq("inferred_pft")
        & u.representation.eq("NEON_full")
        & u.model.eq("logistic")
        & u.probability.eq("raw")
    ]
    for kind, lo, hi in [("plant", 0.884, 0.902), ("site", 0.503, 0.837)]:
        v = u[u.kind.eq(kind)].identity_joint_coverage
        close(kind + "_conformal_low", v.min(), lo)
        close(kind + "_conformal_high", v.max(), hi)
    r = pd.read_csv(PRIOR / "real_landsat_flight_metrics.csv")
    q = r[r.variant.eq("undarkened")].iloc[0]
    assert q.N == 3583 and q.spatial_blocks == 56
    close("real_pilot_RMSE", q.pooled_seven_band_RMSE, 0.0147706508514, 1e-12)
    close("real_pilot_angle", q.median_spectral_angle_deg, 2.08910076, 1e-8)
    # The report itself must reconstruct byte-identically from its editable source.
    subprocess.run(
        [sys.executable, str(BASE / "build_report.py")], cwd=REPO, check=True
    )
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == before
    result = {
        "status": "passed",
        "pages": 29,
        "figure_stories": 23,
        "outside_text_words": outside,
        "hashed_source_files_verified": len(manifest["inputs"]),
        "sources_compared_to_prior_sealed_ledgers": verified_legacy,
        "report_rebuild_byte_identical": True,
        "numeric_checks": checks,
    }
    (BASE / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Passed {len(checks)} quantitative checks, all source hashes, 29 pages and byte-identical PDF rebuild."
    )


if __name__ == "__main__":
    main()
