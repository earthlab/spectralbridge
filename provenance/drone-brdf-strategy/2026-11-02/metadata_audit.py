"""Record bounded, authenticated metadata inquiry; never treats filenames as geometry."""

from pathlib import Path
import hashlib
import json
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
records = {}
for name in ["gordon", "goldhill", "ruby"]:
    sources = []
    for card in [1, 2]:
        p = Path("/private/tmp") / (
            f"SD{card}_image_metadata.csv"
            if name == "goldhill"
            else f"{name}-sd{card}-metadata.csv"
        )
        f = pd.read_csv(p)
        sources.append(
            dict(
                path=str(p),
                remote_origin="i:/iplant/home/shared/earthlab/macrosystems/field-data/uas-packages/"
                + {
                    "gordon": "AOP-GORDON-08-14-23-ExportPackage",
                    "goldhill": "AOP-GOLDHILL-08-14-23-ExportPackage",
                    "ruby": "AOP-Ruby-08-14-23-ExportPackage",
                }[name]
                + f"/Metadata/SD{card}_image_metadata.csv",
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                card=card,
                rows=len(f),
                columns=list(f.columns),
                timestamp_min=f.TIFFTAG_DATETIME.min(),
                timestamp_max=f.TIFFTAG_DATETIME.max(),
                timezone="not supplied",
                example_filename=f.filename.iloc[0],
                camera_positions=False,
                camera_orientation=False,
                per_target_overlap=False,
                panel_or_DLS_values=False,
            )
        )
    records[name] = dict(
        metadata_csv=sources,
        note_date="2023-08-14",
        csv_date="2023-08-15",
        note_time={"gordon": "14:47", "goldhill": "13:41", "ruby": "12:42"}[name],
        note_timezone="not specified",
        radiometric_calibration="UNVERIFIED",
        original_multispectral_photos="Referenced by relative aop/.../RawData/M300/SD1|SD2 paths; not located in inspected shared exports and project-level inventories.",
        original_image_BRDF="POTENTIALLY_RECOVERABLE_WITH_ADDITIONAL_DATA, not demonstrated. Recover originals, calibrated radiance/reflectance, poses/intrinsics/DSM, irradiance timestamps, image-target overlap and geometry-aware resampling/blending provenance; test same-target angular coverage before fitting.",
    )
records["scope"] = dict(
    collections_inspected=[
        "field-data/uas-packages/Gordon and Ruby packages and Gordon Metadata (new listings)",
        "field-data root and macrosystems root (new listings)",
        "macrosystems/tlm, ruby, lens-aop-continental-scaling and drone_diagnostics roots (new listings)",
        "shared/earthlab root (no direct aop archive identified)",
        "Prior P158/P159 Goldhill metadata, calibration_TM and To_Correct inventories",
    ],
    limits="Bounded search of accessible relevant collections; not an exhaustive search of every CyVerse account, local disk or project. Missing from inspected exports does not mean raw imagery is lost or BRDF impossible.",
    available="Orthomosaics, terrain, GCP/mission-plan files, reports, filename/time/software CSVs and sky photographs. Photogrammetric camera calibration and sky photographs alone do not establish radiometric calibration or irradiance stability.",
    unresolved="Original raw image archive and Metashape .psx/.files or machine-readable pose/intrinsic exports; overlap targets; panel/DLS records; true acquisition date/timezone; original terrain and angle-generation units/provenance.",
)
(HERE / "acquisition_metadata_audit.json").write_text(
    json.dumps(records, indent=2) + "\n"
)
print("Three-flight source metadata audit recorded")
