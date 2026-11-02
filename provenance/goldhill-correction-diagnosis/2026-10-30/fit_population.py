"""Count the production BRDF fitting range for every source band, without guessing units."""

from pathlib import Path
import json
import h5py
import numpy as np

F = Path(
    "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products/2023_AOP-GOLDHILL-08-14-23-ExportPackage/AOP_GOLDHILL_20230814"
)
EVIDENCE = Path(__file__).resolve().parent
counts = np.zeros(10, dtype="int64")
finite_counts = counts.copy()
minima = np.full(10, np.inf)
maxima = np.full(10, -np.inf)
with h5py.File(F / (F.name + "__working.h5")) as h:
    group = next(iter(h.values()))["Reflectance"]
    data = group["Reflectance_Data"]
    waves = group["Metadata/Spectral_Data/Wavelength"][()].tolist()
    for start in range(0, data.shape[0], 128):
        values = data[start : start + 128]
        finite = np.isfinite(values)
        counts += np.sum(finite & (values >= 0) & (values <= 2), axis=(0, 1))
        finite_counts += finite.sum(axis=(0, 1))
        minima = np.minimum(minima, np.nanmin(values, axis=(0, 1)))
        maxima = np.maximum(maxima, np.nanmax(values, axis=(0, 1)))
records = [
    {
        "band": i + 1,
        "wavelength_nm": waves[i],
        "finite_pixels": int(finite_counts[i]),
        "in_default_brdf_0_to_2_range": int(counts[i]),
        "fraction_in_fit_range": float(counts[i] / finite_counts[i]),
        "minimum": float(minima[i]),
        "maximum": float(maxima[i]),
    }
    for i in range(10)
]
(EVIDENCE / "fit_population.json").write_text(
    json.dumps(
        {
            "cube_scale_factor": 1.0,
            "rho_min": 0.0,
            "rho_max": 2.0,
            "bands": records,
            "scope": "Exact numeric eligibility counts for the existing default fitter; no physical unit or band-identity interpretation inferred.",
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps(records, indent=2))
