#!/usr/bin/env python3
"""Validate this folder using unittest: python check_figure_4.py (no pytest)."""

from pathlib import Path
import tempfile
import hashlib
import json
import unittest

import numpy as np
import pandas as pd

import plot_figure_4 as figure

HERE = Path(__file__).resolve().parent


class Figure4Checks(unittest.TestCase):
    def test_all_inputs_validate(self):
        summary = figure.load_summary(
            HERE / "data/spectral_medians_and_interquartile_ranges.csv"
        )
        table = figure.load_table(
            HERE / "data/pft_separability_and_identifiability.csv"
        )
        self.assertEqual(len(summary), 3)
        self.assertEqual(len(table), 15)
        gaps = figure.band_gaps(summary)
        self.assertEqual(gaps.shape, (5, 3, 7))
        self.assertEqual(int(np.isnan(gaps).sum()), 20)

    def test_saved_spectra_reproduce_every_median_quartile_and_count(self):
        calculated = figure.recalculate_spectra(
            HERE / "data/spectral_observations_by_footprint.csv"
        )
        saved = pd.read_csv(HERE / "data/spectral_medians_and_interquartile_ranges.csv")
        key = ["sensor", "category", "band"]
        left = calculated.set_index(key).sort_index()
        right = saved.set_index(key).sort_index()
        pd.testing.assert_frame_equal(
            left, right, check_exact=False, atol=1e-12, rtol=1e-12
        )

    def test_plotted_hls_is_exactly_the_primary_cohort_used_for_tests(self):
        source_path = HERE / "evidence/landsat_hls_primary_reference_observations.csv"
        source = pd.read_csv(source_path)
        observations = pd.read_csv(HERE / "data/spectral_observations_by_footprint.csv")
        self.assertFalse(observations.sensor.eq("Landsat 9 OLI-2").any())
        hls = (
            observations.loc[observations.sensor.eq("HLS L30 NBAR")]
            .set_index("footprint_id")
            .sort_index()
        )
        primary = source.set_index("candidate_id").sort_index()
        self.assertEqual(set(hls.index), set(primary.index))
        np.testing.assert_allclose(
            hls[figure.BANDS], primary[figure.BANDS], rtol=0, atol=1e-12
        )
        self.assertTrue(hls.brdf_normalized.all())
        self.assertTrue(hls.source_item_id.eq(primary.hls_item_id).all())
        analysis = json.loads(
            (HERE / "evidence/landsat_hls_analysis_manifest.json").read_text()
        )
        self.assertEqual(
            hashlib.sha256(source_path.read_bytes()).hexdigest(),
            analysis["input_sha256"]["hls_l30_nominal_95pct_observations.csv"],
        )
        predictions = pd.read_csv(
            HERE / "evidence/landsat_exploratory_held_out_predictions.csv"
        )
        pixels = predictions.loc[
            predictions.scheme.eq("leave_one_patch_out") & predictions.unit.eq("pixel")
        ]
        self.assertEqual(set(pixels.candidate_id), set(primary.index))
        summary = pd.read_csv(
            HERE / "data/spectral_medians_and_interquartile_ranges.csv"
        )
        summary = summary.loc[summary.sensor.eq("HLS L30 NBAR")]
        for category, g in source.groupby("researcher_category"):
            self.assertTrue(
                summary.loc[summary.category.eq(category)].n.eq(len(g)).all()
            )

    def test_numeric_evidence_agrees_with_archived_sources(self):
        table = pd.read_csv(HERE / "data/pft_separability_and_identifiability.csv")
        drone = pd.read_csv(HERE / "evidence/drone_pairwise_separability.csv")
        predictions = pd.read_csv(HERE / "evidence/drone_held_out_predictions.csv")
        self.assertFalse(predictions.duplicated(["scheme", "GlobalID"]).any())
        neon = pd.read_csv(HERE / "evidence/neon_pairwise_separability.csv")
        for row in table.itertuples():
            if row.sensor.startswith("Drone"):
                pairs = drone.loc[drone.a.eq(row.category) | drone.b.eq(row.category)]
                self.assertEqual(row.supported_tests, pairs.p_npc_holm.le(0.05).sum())
                self.assertEqual(row.total_tests, pairs.p_npc.notna().sum())
                for scheme, value in [
                    ("unseen_polygon", row.unseen_polygon_recall),
                    ("held_out_site", row.held_out_site_recall),
                ]:
                    subset = predictions.loc[
                        predictions.scheme.eq(scheme)
                        & predictions.truth.eq(row.category)
                    ]
                    if subset.truth_in_training.all():
                        self.assertAlmostEqual(
                            value, subset.truth.eq(subset.prediction).mean()
                        )
                    else:
                        self.assertTrue(pd.isna(value))
            elif row.sensor.startswith(("Landsat", "HLS")):
                pairs = pd.read_csv(
                    HERE / "evidence/landsat_exploratory_patch_separability.csv"
                )
                pairs = pairs.loc[
                    pairs.scope.eq("pooled_patches_region_confounded")
                    & (pairs.a.eq(row.category) | pairs.b.eq(row.category))
                ]
                self.assertEqual(row.supported_tests, pairs.p_npc_holm.le(0.05).sum())
                self.assertEqual(row.total_tests, pairs.p_npc.notna().sum())
                predicted = pd.read_csv(
                    HERE / "evidence/landsat_exploratory_held_out_predictions.csv"
                )
                predicted = predicted.loc[
                    predicted.unit.eq("patch")
                    & predicted.scheme.eq("leave_one_patch_out")
                    & predicted.truth.eq(row.category)
                ]
                self.assertFalse(predicted.patch_group_id.duplicated().any())
                supported = predicted.loc[predicted.truth_in_training]
                self.assertEqual(row.supported_test_patches, len(supported))
                rendered = figure.load_table(
                    HERE / "data/pft_separability_and_identifiability.csv"
                )[(row.sensor, row.category)]
                if row.total_tests:
                    self.assertEqual(
                        rendered[0],
                        f"{int(row.supported_tests)}/{int(row.total_tests)} supported†",
                    )
                else:
                    self.assertEqual(rendered[0], "Insufficient patches†")
                if len(supported) == len(predicted) and len(predicted):
                    self.assertAlmostEqual(
                        row.held_out_patch_recall,
                        supported.truth.eq(supported.prediction).mean(),
                    )
                    self.assertEqual(
                        rendered[1],
                        f"{row.held_out_patch_recall:.0%} ({int(row.held_out_patch_correct)}/{int(row.held_out_patch_total)})†",
                    )
                else:
                    self.assertEqual(len(supported), 0)
                    self.assertTrue(pd.isna(row.held_out_patch_recall))
                    self.assertEqual(
                        rendered[1], f"NA ({int(row.held_out_patch_total)} patch)†"
                    )
            elif row.sensor.startswith("NEON"):
                pairs = neon.loc[neon.a.eq(row.category) | neon.b.eq(row.category)]
                self.assertEqual(row.supported_tests, pairs.OLI_supported.sum())
                self.assertEqual(row.total_tests, len(pairs))

    def test_patch_recall_counts_cannot_disagree(self):
        frame = pd.read_csv(HERE / "data/pft_separability_and_identifiability.csv")
        index = frame.index[frame.sensor.str.startswith(("Landsat", "HLS"))][0]
        frame.loc[index, "held_out_patch_correct"] = (
            frame.loc[index, "held_out_patch_total"] + 1
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid_counts.csv"
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "correct/total"):
                figure.load_table(path)

    def test_unavailable_recall_cannot_be_fabricated(self):
        frame = pd.read_csv(HERE / "data/pft_separability_and_identifiability.csv")
        index = frame.index[frame.sensor.str.startswith(("Landsat", "HLS"))][0]
        frame.loc[index, "identifiability_status"] = "insufficient_training_patches"
        frame.loc[index, "supported_test_patches"] = 0
        frame.loc[index, "held_out_patch_recall"] = 0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid_unavailable.csv"
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Unavailable held-class"):
                figure.load_table(path)

    def test_invalid_quartiles_fail_instead_of_silently_plotting(self):
        frame = pd.read_csv(HERE / "data/spectral_medians_and_interquartile_ranges.csv")
        frame.loc[0, "q25"] = frame.loc[0, "median"] + 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid_summary.csv"
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "q25"):
                figure.load_summary(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
