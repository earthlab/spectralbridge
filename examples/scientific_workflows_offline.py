"""Fast offline package example using invented spectra, never empirical evidence."""

import argparse
from pathlib import Path
import json
import tempfile
import numpy as np
import pandas as pd
import duckdb
from spectralbridge import (
    inspect_spectral_library_preflight,
    run_spectral_library_analysis,
)
from spectralbridge.bulk import BulkAnalysisPaths
from spectralbridge.plant_spectral_atlas import (
    harmonize_spectrum,
    run_plant_spectral_atlas,
)
from spectralbridge.sensor_pft_transfer import project_neon_to_oli
from spectralbridge.landsat_agreement import compute_agreement_metrics


def run_example(destination: Path) -> dict:
    """Write tiny teaching inputs/compact atlas and return deterministic checks."""
    destination.mkdir(parents=True, exist_ok=True)
    wavelengths = np.arange(385.0, 2511.0, 5.0)
    values = np.full(len(wavelengths), 0.2)
    mapped = harmonize_spectrum(wavelengths, values, wavelengths)
    oli, response_support = project_neon_to_oli(mapped[None, :], wavelengths)
    np.testing.assert_allclose(oli, 0.2, atol=1e-12)
    agreement = compute_agreement_metrics(oli[0], oli[0])
    rows = []
    for plant in range(2):
        for pixel in range(3):
            rows.append(
                dict(
                    GlobalID=str(plant),
                    species="invented teaching group",
                    flight_id="teaching-flight",
                    source_image="teaching.img",
                    polygon_id=plant,
                    flightline_id="teaching-flight",
                    site="teaching-site",
                    corr_b001_wl0400nm=0.1 + plant * 0.1 + pixel * 0.01,
                    corr_b002_wl0405nm=0.2 + plant * 0.1 + pixel * 0.01,
                    corr_b003_wl0410nm=0.3 + plant * 0.1 + pixel * 0.01,
                )
            )
    source = destination / "teaching.parquet"
    pd.DataFrame(rows).to_parquet(source)
    preflight = inspect_spectral_library_preflight(source)
    library_paths = BulkAnalysisPaths(destination / "library_summary")
    library_paths.database_dir.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(library_paths.database)) as connection:
        library = run_spectral_library_analysis(
            connection,
            library_paths,
            spectral_library=source,
            analysis_run_id="invented-offline-lesson",
            make_summary_plots=False,
            make_full_spectral_reports=False,
        )
    audit = run_plant_spectral_atlas(
        source, destination / "atlas", min_plants_per_species=1, make_figures=False
    )
    return dict(
        data_kind="invented teaching data, not scientific validation",
        pixel_rows=len(rows),
        independent_plants=2,
        atlas_plants=audit["plants_retained"],
        preflight_counts=preflight["counts"],
        compact_library_outputs=library["compact_outputs"],
        OLI_values=oli[0].tolist(),
        response_support=response_support.tolist(),
        identity_RMSE=agreement["RMSE"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Keep the teaching table, atlas and JSON summary in a fresh directory.",
    )
    args = parser.parse_args()
    if args.output_dir is not None:
        destination = args.output_dir.expanduser().resolve()
        try:
            destination.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            parser.error(
                f"Choose a fresh writable output directory: {destination}. {exc}"
            )
        report = run_example(destination)
        report["output_directory"] = str(destination)
        (destination / "example_summary.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(json.dumps(report, indent=2))
        return
    with tempfile.TemporaryDirectory(
        prefix="spectralbridge-science-example-"
    ) as directory:
        print(json.dumps(run_example(Path(directory)), indent=2))


if __name__ == "__main__":
    main()
