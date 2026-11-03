"""Confirm real Goldhill normalized DN cannot enter a physical BRDF fit."""

import json
from pathlib import Path

from spectralbridge.corrections import fit_and_save_brdf_model
from spectralbridge.neon_cube import NeonCube
from spectralbridge.radiometry import Radiometry

HERE = Path(__file__).resolve().parent
result = json.loads((HERE / "results.json").read_text())
cube = NeonCube("/private/tmp/assumed-viewing-angles-20261103/goldhill_working.h5")
cube.radiometry = Radiometry.from_record(result["diagnostic_radiometry"])
path = fit_and_save_brdf_model(cube, HERE / "normalized_units_rejection")
model = json.loads(path.read_text())
assert model["validation"]["status"] == "UNSUPPORTED"
assert not model["validation"]["fits"]
assert "iso" not in model
assert model["fitting_population"]["eligible"] is None
(HERE / "physical_fit_gate.json").write_text(
    json.dumps(
        dict(
            status="PASS",
            model_path=str(path.relative_to(HERE)),
            validation=model["validation"],
            fitting_population=model["fitting_population"],
            meaning="No physical calibration was inferred from the diagnostic normalized fraction.",
        ),
        indent=2,
    )
    + "\n"
)
print(
    "Real Goldhill normalized-DN physical fit rejected explicitly; no coefficients emitted"
)
