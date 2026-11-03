"""Bounded inventory, code evidence, operation states and field provenance matrix."""

import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/photogrammetry-metadata-20261102")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(n, x):
    (HERE / n).write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n")


records = json.loads((HERE / "validation.json").read_text())
# Record objects seen in bounded collection inventories; missing hashes are explicit.
inventories = list(WORK.glob("*inventory.txt")) + list(WORK.glob("search-*.txt"))
objects = []
for inv in inventories:
    text = inv.read_text()
    collection = None
    for line in text.splitlines():
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) > 1 and cols[0] == "collection" and cols[1].startswith("/iplant/"):
            collection = cols[1]
        if len(cols) >= 4 and cols[0] == "data-object":
            try:
                size = int(cols[2])
            except ValueError:
                continue
            objects.append(
                dict(
                    remote_path="i:" + collection + "/" + cols[1]
                    if collection
                    else None,
                    size_bytes=size,
                    owner=cols[3],
                    modify_time=cols[4] if len(cols) > 4 else None,
                    sha256=None,
                    hash_status="NOT_DOWNLOADED / remote listing has no digest",
                    inventory_file=str(inv),
                )
            )
local = []
for p in sorted(WORK.iterdir()):
    if p.is_file() and p.suffix.lower() in {
        ".tif",
        ".pdf",
        ".r",
        ".py",
        ".ipynb",
        ".txt",
    }:
        local.append(
            dict(
                local_path=str(p),
                size_bytes=p.stat().st_size,
                sha256=sha(p),
                role="downloaded source or derived read-only inspection record; inspect suffix/name",
                remote_origin=None,
            )
        )
for name, r in records.items():
    for key in ["source_h5", "working_h5"]:
        p = Path(r[key])
        local.append(
            dict(
                local_path=str(p),
                size_bytes=p.stat().st_size,
                sha256=sha(p),
                role=key,
                flight=name,
            )
        )
write(
    "source_inventory.json",
    dict(
        remote_objects=objects,
        local_files=local,
        search_scope="Bounded accessible shared export/terrain/processing roots and repository history; previous P161 inventory extends scope. No full raw-photo downloads; no exhaustive search of private accounts or unavailable mounts.",
        missing_projects="No matching Gordon/Goldhill/Ruby .psx/.psz/.files/pose or source-contribution export located in inspected collections. Unrelated Table Mountain projects were excluded.",
        unavailable_documented_location="Relative aop/.../RawData/M300/SD1|SD2 paths are not resolved to a current accessible collection; historical local data_set2 path not present in inspected shared cross-sensor-cal root.",
        known_limits="Remote object owner/mtime are storage metadata, not proof of processing authorship or execution date. A local SHA-256 is not an independently fetched remote digest.",
    ),
)
legacy = subprocess.check_output(
    ["git", "show", "94ef270:drone_cor_sup/utils.py"], text=True
)
start = legacy.index("def get_computed_azimuth_zenith")
stop = legacy.index("def process_hdf5", start)
zero = legacy.index("    # Set sensor angles to zero")
zero_end = legacy.index("    # Extract spatial metadata", zero)
code = dict(
    historical_ref="94ef270",
    historical_path="drone_cor_sup/utils.py",
    historical_blob_sha256=hashlib.sha256(legacy.encode()).hexdigest(),
    legacy_tiff_to_h5_zero_excerpt=legacy[zero:zero_end],
    legacy_solar_function=legacy[start:stop],
    snapshot_history="94ef270 (2025-04-23), author ttuff, imports legacy code; not evidence of original author or execution of a named flight. Removed in 44a26ea (2025-06-18).",
    parallel_notebooks=[
        "Drone_correction_and_pixel_extraction.ipynb cells 6/7, executed counters 247/248; example paths are data_set2, not exact execution records for all mosaics",
        "drone_cor_sup/tiff_to_envi_drone.ipynb cell 1 has same zero assignment; cell 0 comment explicitly calls nadir zero",
    ],
    current_copy="scripts/drone_cloud_workflow.py:prepare_reference reads and tests source matrices, records source_recipe.json view constants, returns tiff_sensor_zenith_deg/azimuth_deg",
    current_write="src/spectralbridge/pipelines/drone.py:convert_drone_tiff_to_h5 writes explicitly supplied scalar angles; defaults are None, not zero",
    current_reader="src/spectralbridge/neon_cube.py:NeonCube.get_ancillary broadcasts supplied scalar metadata; missing view metadata raises, rather than inventing zeros",
    current_solar="src/spectralbridge/pipelines/drone.py:_compute_solar_geometry_arrays; NOAA fractional-year approximation from each pixel center and one manifest UTC time, no terrain altitude/refraction",
    code_history=[
        dict(
            commit="5e88b8c",
            date="2026-06-03",
            event="Adds optional TIFF bridge scalar/raster geometry",
        ),
        dict(
            commit="fc60390",
            date="2026-06-09",
            event="Adds manifest timestamps and approximate computed solar geometry",
        ),
        dict(
            commit="5ed728c",
            date="2026-09-18",
            event="Adds read-only solar consistency QA",
        ),
        dict(
            commit="ecd0df2 plus preserved Oct29 working-tree patch",
            date="2026-10-29",
            event="Recorded three-flight run uses prepare_reference TIFF recipe, copied zero views and manifest-computed solar; actual source hashes/patch/execution logs retained",
        ),
    ],
    attribution_limit="No claim that a Git snapshot author ran the original converter. Numerical solar fingerprints plus matching H5 schema support algorithmic lineage, not identity of the human executor.",
)
write("code_evidence.json", code)
fields = [
    (
        "Camera position",
        "Raw GNSS not recovered",
        "ESTIMATED: report camera-location figures and alignment",
        "MISSING",
        "MISSING",
        "MISSING_FOR_RECOVERY",
        "Reports camera-location page 13; no machine-readable poses found",
    ),
    (
        "Camera orientation",
        "Raw attitude not recovered",
        "ESTIMATED: aligned cameras; Yaw/Pitch/Roll convention documented",
        "MISSING",
        "MISSING",
        "MISSING_FOR_RECOVERY",
        "Report alignment/calibration; exact matrices unavailable",
    ),
    (
        "Camera intrinsics / lens",
        "Original sensor records unavailable",
        "DERIVED/GEOMETRIC: numerical calibration tables in reports",
        "MISSING",
        "MISSING",
        "PARTLY_RECOVERABLE",
        "PDF coefficients exist, but distortion model/version/band assignments need project export",
    ),
    (
        "Camera timestamps",
        "RECORDED in six SD CSV snapshots; timezone unverified",
        "UNKNOWN per exposure/project",
        "Not preserved in inspected ortho tags",
        "Single manifest datetime; not per-observation",
        "UNVERIFIED",
        "CSV date Aug15, notes Aug14, Ruby manifest Aug16",
    ),
    (
        "View zenith",
        "Can derive only from rays/ground, not recovered",
        "Camera geometry implies possible ray reconstruction",
        "MISSING",
        "PLACEHOLDER: old matrix 0; working scalar 0",
        "PLACEHOLDER",
        "utils.tiff_to_h5 zeros; prepare_reference explicit copy; converter writes; reader broadcasts",
    ),
    (
        "View azimuth",
        "Can derive only from rays/ground, not recovered",
        "No per-pixel contributor export found",
        "MISSING",
        "PLACEHOLDER: old matrix 0; working scalar 0",
        "PLACEHOLDER",
        "Same explicit code chain; at nadir azimuth is not an independent direction",
    ),
    (
        "Solar zenith",
        "Date/time/position records conflict",
        "UNKNOWN: not established as Metashape output",
        "MISSING in inspected input ortho metadata",
        "DERIVED: old mixed-unit PyEphem bug; working NOAA manifest calculation",
        "DERIVED_UNVERIFIED_TIME",
        "25-point exact replays per flight, independent SPA check",
    ),
    (
        "Solar azimuth",
        "Date/time/position records conflict",
        "UNKNOWN",
        "MISSING",
        "DERIVED: old coordinate-unit bug; working NOAA calculation",
        "DERIVED_UNVERIFIED_TIME",
        "Historical values and corrected algorithm kept separate",
    ),
    (
        "Source-image contributors / blend weights",
        "Original overlapping images referenced, not found",
        "Gordon/Ruby report Mosaic blending; Goldhill ortho settings absent",
        "MISSING",
        "MISSING",
        "MISSING_FOR_RECOVERY",
        "Mosaic mode is not proof of exact per-pixel weighting or color balancing",
    ),
    (
        "DEM / elevation",
        "LAS and native DEM/DTM exports present",
        "DERIVED: Gordon tie points; Goldhill mesh; Ruby DEM source unlisted",
        "PRESENT: exact target aligned_dem now retrieved",
        "Elevation absent as named field; Path_Length is not elevation",
        "DERIVED_SOURCE_UNVERIFIED",
        "Reported dimensions differ from some exported rasters; source/version link unresolved",
    ),
    (
        "Slope",
        "Derived terrain, exact source surface not established",
        "Not a required photogrammetry export in inspected reports",
        "PRESENT aligned_slope; degree-unit R scripts",
        "PRESENT; exact TIFF equality",
        "DERIVED_PARTLY_VERIFIED",
        "R files show intended ground classification/0.25m TIN then degree slope; no execution log",
    ),
    (
        "Aspect",
        "Derived terrain, exact source surface unverified",
        "UNKNOWN",
        "PRESENT; scripts specify clockwise North degrees and scalar bilinear resampling",
        "PRESENT; exact TIFF equality",
        "DERIVED_PARTLY_VERIFIED",
        "Independent Horn aligned DEM comparison; circular errors retained",
    ),
    (
        "Illumination / cosine incidence",
        "Requires credible terrain and acquisition geometry",
        "UNKNOWN",
        "No authoritative solar/illumination raster metadata",
        "DERIVED by calc_cosine_i, degree-to-radian boundary",
        "DERIVED_UNVERIFIED_INPUTS",
        "Shared SCS+C denominator replay exact; high gains are cancellation, not proof of wrong units",
    ),
    (
        "Path length",
        "No actual camera-ground distances recovered",
        "Potentially derivable from rays/project",
        "Not a measured spectral band",
        "Working bridge writes array of ones",
        "PLACEHOLDER",
        "convert_drone_tiff_to_h5 Path_Length; never call it measured altitude",
    ),
    (
        "Reflectance-panel calibration",
        "Panel images/certificate not located",
        "UNKNOWN enabled/disabled",
        "No physical unit/certificate",
        "UNVERIFIED",
        "UNVERIFIED",
        "Photogrammetric precalibrated cameras means lens geometry, not reflectance",
    ),
    (
        "DLS / irradiance",
        "Original raw EXIF/XMP not located",
        "UNKNOWN enabled/disabled",
        "Not retained in inspected tags",
        "MISSING",
        "UNVERIFIED",
        "Filename/time/software CSVs contain no irradiance",
    ),
    (
        "Exposure / gain / vignette",
        "Raw camera radiometric metadata not recovered",
        "UNKNOWN applied/settings",
        "Not retained as original-image parameters",
        "MISSING",
        "UNVERIFIED",
        "No duplication can be established from software capability",
    ),
    (
        "UInt16 physical encoding",
        "Original files UInt16, minima/maxima recorded",
        "10-band UInt16 in reports; physical semantics UNKNOWN",
        "Identity TIFF scales/offsets; no physical units",
        "Scale_Factor=1 on working bridge is not calibration",
        "UNVERIFIED",
        "Vendor 32768 convention remains conditional on actual calibration/export settings",
    ),
    (
        "Numeric min/max normalization",
        "Verified original-extrema mapping",
        "Not established as Metashape operation",
        "DERIVED: per-band S to 0..10000",
        "Same spectral numbers, later inverse recoverable",
        "NUMERIC_MAPPING_VERIFIED",
        "P159 real same-grid evidence; exact exporter script still absent",
    ),
    (
        "Spatial reference / orientation",
        "NAD83 UTM13 exports",
        "EPSG26913 in reports",
        "North-up source transform",
        "Old signed size/datum/corner defects; working TIFF-corner repair",
        "SPATIAL_VERIFIED",
        "Oct29 full value/membership tests; no new resampling here",
    ),
    (
        "Researcher labels / library provenance",
        "Researcher polygons with IDs/categories",
        "Not a photogrammetric radiometric validation",
        "External polygon dataset",
        "Extracted by fixed spatial memberships",
        "PRESERVED_NOT_RADIOMETRIC_TRUTH",
        "P161 matched 301 polygons; lower variance is not physical accuracy",
    ),
]
rows = [
    dict(
        metadata=x[0],
        original_source=x[1],
        photogrammetry=x[2],
        TIFF=x[3],
        H5=x[4],
        status=x[5],
        evidence=x[6],
    )
    for x in fields
]
write(
    "metadata_provenance_matrix.json",
    dict(
        fields=rows,
        status_key="MEASURED / DERIVED / PLACEHOLDER / MISSING / UNVERIFIED are distinguished; measured source-camera data are not claimed where only reports/CSV snapshots exist.",
    ),
)
with (HERE / "metadata_provenance_matrix.csv").open("w") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
operations = []
for op in [
    "Reflectance panel calibration",
    "Downwelling irradiance correction",
    "Exposure/gain normalization",
    "Lens vignetting correction",
    "Camera-specific radiometric calibration",
    "Brightness/color balancing",
    "Radiometric block adjustment",
    "BRDF/angular normalization",
]:
    operations.append(
        dict(
            operation=op,
            metashape_state="UNKNOWN",
            evidence="No matching project flags, raw metadata or calibration log recovered; software capability and lens-calibration report are insufficient.",
            spectralbridge="Historical BRDF applied; invalid model diagnosed"
            if op == "BRDF/angular normalization"
            else "No separate verified equivalent operation demonstrated in the audited run",
            duplication="NOT_ESTABLISHED; cannot exclude upstream execution",
        )
    )
operations.append(
    dict(
        operation="Orthomosaic Mosaic blending",
        metashape_state="ENABLED in Gordon/Ruby report snapshots; Goldhill ortho setting UNKNOWN",
        evidence="Report page 19 for Gordon/Ruby; source/project dimensions differ from final exported files, so exact export equivalence remains unresolved",
        spectralbridge="No orthomosaic reconstruction in the three-flight run",
        duplication="Not a proof of brightness/color balancing or physical reflectance",
    )
)
write("upstream_correction_operations.json", operations)
priorities = [
    dict(
        priority=1,
        item="Matched Metashape .psx/.psz and complete .files plus original image references",
        resolves="Camera intrinsics/extrinsics, processing tasks, per-band sensitivity, reflectance-calibration flags, actual orthomosaic surface/blending and export settings",
        minimum="Project/task/metadata XML plus machine-readable cameras/sensors and explicit project-to-export identity; do not need all raw images to inspect settings",
    ),
    dict(
        priority=2,
        item="Panel images/certificate, DLS/exposure/gain records and normalization/export equations",
        resolves="Absolute physical calibration and whether vignette/irradiance/BRDF operations occurred upstream; prevents double corrections",
        minimum="Representative original ten-band capture plus calibration images/records and project radiometric parameters",
    ),
    dict(
        priority=3,
        item="Authoritative acquisition dates/times/timezones, especially Ruby",
        resolves="Aug14 notes vs Aug15 CSVs vs Aug16 Ruby manifest; pixel-time assumptions and illumination",
        minimum="Raw EXIF/XMP + flight log + verified timezone; UTC/Denver conversion alone does not fix date conflict",
    ),
    dict(
        priority=4,
        item="Exact terrain generating inputs and executed R/GDAL commands/versions",
        resolves="Classified LAS/DTM version, grid/north conventions, derivative-before/after-resampling and circular aspect handling",
        minimum="Match aligned_dem/slope/aspect SHA-256 to processing log, source surface and classifications",
    ),
    dict(
        priority=5,
        item="Original images, per-image target visibility and seam/contributor/blend records",
        resolves="Same-target repeated angular observations, pre-mosaic block/angular feasibility and whether current mosaic geometry can be reconstructed",
        minimum="Small calibrated overlapping subset with poses, DSM/occlusion and independent held-out targets/views first",
    ),
]
write("missing_artifacts_prioritized.json", priorities)
print(
    "Inventories, code evidence, field/operation matrices and recovery priorities written"
)
# Bind downloaded aliases to their exact remote paths; derived inspections retain
# null origins rather than masquerading as source files.
inv = json.loads((HERE / "source_inventory.json").read_text())
base = "i:/iplant/home/shared/earthlab/macrosystems/field-data/"
packages = {
    "gordon": "AOP-GORDON-08-14-23-ExportPackage",
    "goldhill": "AOP-GOLDHILL-08-14-23-ExportPackage",
    "ruby": "AOP-Ruby-08-14-23-ExportPackage",
}
filenames = {
    "gordon": {
        "dem": "AOP-GORDON-8-14-23-M300_DEM.tif",
        "dtm": "AOP-GORDON-8-14-23-M300_DTM.tif",
        "report": "AOP-GORDON-8-14-23-M300_REPORT.pdf",
    },
    "goldhill": {
        "dem": "AOP-GOLDHILL-08-14-23_DEM.tif",
        "dtm": "AOP-GOLDHILL-08-14-23-DTM.tif",
        "report": "AOP-GOLDHILL-08-14-23_report.pdf",
    },
    "ruby": {
        "dem": "AOP-RUBY-08-14-23-DEM.tif",
        "dtm": "AOP-RUBY-08-14-23-DTM.tif",
        "report": "AOP-RUBY-08-14-23_report.pdf",
    },
}
papers = json.loads((HERE / "literature.json").read_text())
for row in inv["local_files"]:
    n = Path(row["local_path"]).name
    for name, pkg in packages.items():
        for kind, filename in filenames[name].items():
            if n == name + "_" + kind + (".pdf" if kind == "report" else ".tif"):
                row["remote_origin"] = base + "uas-packages/" + pkg + "/" + filename
        if n == name + "_aligned_dem.tif":
            row["remote_origin"] = (
                base + "output/summer-2023-10cm-10k/" + pkg + "/aligned_dem.tif"
            )
    if n == "dsm_to_slope_aspect.R":
        row["remote_origin"] = base + n
    for paper in papers:
        if n == paper["key"] + ".pdf":
            row["remote_origin"] = paper["pdf_source"]
            row["doi"] = paper["doi"]
write("source_inventory.json", inv)
