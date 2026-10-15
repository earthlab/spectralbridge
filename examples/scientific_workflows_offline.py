"""Fast offline package example using invented spectra, never empirical evidence."""

from pathlib import Path
import json
import tempfile
import numpy as np
import pandas as pd
from spectralbridge import inspect_spectral_library_preflight
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
    audit = run_plant_spectral_atlas(
        source, destination / "atlas", min_plants_per_species=1, make_figures=False
    )
    return dict(
        data_kind="invented teaching data, not scientific validation",
        pixel_rows=len(rows),
        independent_plants=2,
        atlas_plants=audit["plants_retained"],
        preflight_counts=preflight["counts"],
        OLI_values=oli[0].tolist(),
        response_support=response_support.tolist(),
        identity_RMSE=agreement["RMSE"],
    )


def main():
    with tempfile.TemporaryDirectory(
        prefix="spectralbridge-science-example-"
    ) as directory:
        print(json.dumps(run_example(Path(directory)), indent=2))


if __name__ == "__main__":
    main()
