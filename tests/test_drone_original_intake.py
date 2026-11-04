"""Original-package selection and verified transfers must not certify calibration."""

import base64
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from spectralbridge.remote import (
    RemoteEntry,
    RemoteError,
    parse_gocmd_json_listing,
    checksum_matches,
    stage_remote_file,
)
from spectralbridge.drone_production import (
    inspect_original_drone_packages,
    stage_original_drone_package,
    verify_uploaded_results,
)
from spectralbridge.pipelines.drone import prepare_drone_orthomosaic
from tests.test_drone_production import FakeRemoteBackend


def test_json_good_replicas_keep_md5_and_reject_disagreement():
    rows = [
        dict(
            Type="data-object",
            Name="original ortho.tif",
            Size="4",
            Checksum="a" * 32,
            Status="Good",
        )
    ] * 2
    listing = json.dumps([dict(title="Content", data=rows)])
    entries = parse_gocmd_json_listing(listing, parent="i:/flight")
    assert len(entries) == 1 and entries[0].name == "original ortho.tif"
    assert entries[0].checksum == "a" * 32
    rows[1] = {**rows[1], "Checksum": "b" * 32}
    with pytest.raises(RemoteError, match="replicas disagree"):
        parse_gocmd_json_listing(json.dumps([dict(data=rows)]), parent="i:/flight")


def test_checksum_algorithms_are_not_all_treated_as_sha256(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"checked observation")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    md5 = hashlib.md5(path.read_bytes()).hexdigest()
    for expected in [
        sha,
        "sha256:" + sha,
        md5,
        "md5:" + md5,
        "sha2:" + base64.b64encode(bytes.fromhex(sha)).decode(),
    ]:
        assert checksum_matches(path, expected)
    assert not checksum_matches(path, "0" * 32)
    with pytest.raises(RemoteError):
        checksum_matches(path, "unknown:123")


def test_verified_transfer_restarts_and_detects_same_size_corruption(tmp_path):
    backend = FakeRemoteBackend({"i:/flight/source.tif": b"abcd"})
    entry = RemoteEntry(
        "i:/flight/source.tif", "source.tif", False, 4, hashlib.md5(b"abcd").hexdigest()
    )
    local = tmp_path / "source.tif"
    first = stage_remote_file(entry, local, backend=backend)
    before = local.stat().st_mtime_ns
    assert stage_remote_file(entry, local, backend=backend)["status"] == "reused"
    assert local.stat().st_mtime_ns == before and len(backend.downloads) == 1
    local.write_bytes(b"bad!")
    assert stage_remote_file(entry, local, backend=backend)["status"] == "downloaded"
    assert local.read_bytes() == b"abcd" and first["remote_checksum_verified"]


def test_failed_transfer_does_not_replace_an_existing_file(tmp_path):
    backend = FakeRemoteBackend({"i:/flight/source.tif": b"bad!"})
    entry = RemoteEntry(
        "i:/flight/source.tif", "source.tif", False, 4, hashlib.md5(b"good").hexdigest()
    )
    path = tmp_path / "source.tif"
    path.write_bytes(b"keep")
    with pytest.raises(RemoteError, match="checksum mismatch"):
        stage_remote_file(entry, path, backend=backend)
    assert path.read_bytes() == b"keep"


def test_original_selection_handles_real_name_variation_and_ambiguity(tmp_path):
    backend = FakeRemoteBackend(
        {
            "i:/originals/AOP-GORDON-08-14-23-ExportPackage/AOP-GORDON-8-14-23-M300_ORTHO.tif": b"original",
            "i:/originals/AOP-GORDON-08-14-23-ExportPackage/aligned_orthomosaic.tif": b"processed",
            "i:/originals/AOP-GORDON-08-14-23-ExportPackage/locations.csv": b"X,Y,Z",
            "i:/originals/AOP-Ruby-08-14-23-ExportPackage/AOP-RUBY-08-14-23-ORTHO_CLIPPED.tif": b"clipped",
        }
    )
    selected = inspect_original_drone_packages(
        "i:/originals", sites=["Gordon", "Ruby"], backend=backend
    )
    assert selected["Gordon"]["orthomosaic"]["name"].endswith("M300_ORTHO.tif")
    assert selected["Gordon"]["flight_stem"] == "AOP_GORDON_20230814"
    assert selected["Ruby"]["clipped_export"]
    staged = stage_original_drone_package(
        selected["Gordon"], staging_dir=tmp_path, backend=backend
    )
    assert Path(staged["orthomosaic_local"]).read_bytes() == b"original"
    assert len(backend.downloads) == 2
    backend.files["i:/originals/AOP-GORDON-08-14-23-ExportPackage/other_ORTHO.tif"] = (
        b"other"
    )
    bad = inspect_original_drone_packages(
        "i:/originals", sites=["Gordon"], backend=backend
    )["Gordon"]
    assert (
        bad["status"] == "AMBIGUOUS_OR_MISSING_ORTHOMOSAIC"
        and len(bad["alternatives"]) == 2
    )
    with pytest.raises(ValueError):
        stage_original_drone_package(bad, staging_dir=tmp_path, backend=backend)


def original(path):
    data = np.full((11, 6, 6), 174, np.uint16)
    data[10] = 65535
    data[:10, 0, 0] = 65535
    data[10, 0, 0] = 0
    data[:10, -1, -1] = 0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=6,
        height=6,
        count=11,
        dtype="uint16",
        transform=from_origin(500000, 4400000, 0.1, 0.1),
        crs=26913,
    ) as out:
        out.write(data)
    path.with_suffix(".tif.aux.xml").write_text(
        '<PAMDataset><PAMRasterBand band="11"><ColorInterp>Alpha</ColorInterp></PAMRasterBand></PAMDataset>'
    )


def test_preparation_preserves_offsets_valid_zero_alpha_and_restart(tmp_path):
    source = tmp_path / "original.tif"
    original(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "prepared.tif"
    record = prepare_drone_orthomosaic(source, destination)
    with rasterio.open(destination) as src:
        assert src.count == 10 and src.crs.to_epsg() == 26913 and src.res == (0.1, 0.1)
        values = src.read(1)
        assert np.isnan(values[0, 0])
        assert values[1, 1] == pytest.approx(174 * 10000 / 65535, abs=3e-6)
        assert values[-1, -1] == 0 and src.dataset_mask()[-1, -1] == 255
    assert (
        record["radiometry"]["status"] == "UNSUPPORTED" and record["clipping"] == "NONE"
    )
    stamp = destination.stat().st_mtime_ns
    assert prepare_drone_orthomosaic(source, destination)["status"] == "reused"
    assert destination.stat().st_mtime_ns == stamp
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    with pytest.raises(ValueError, match="immutable"):
        prepare_drone_orthomosaic(source, source)
    with pytest.raises(ValueError, match="Stale"):
        prepare_drone_orthomosaic(source, destination, resolution=0.2)


def test_strong_upload_verification_rejects_size_only_receipts(tmp_path):
    path = tmp_path / "bundle"
    path.mkdir()
    (path / "result.json").write_bytes(b"abcd")
    backend = FakeRemoteBackend({"i:/uploaded/result.json": b"abcd"})
    result = verify_uploaded_results(
        path, "i:/uploaded", backend=backend, require_checksums=True
    )
    assert not result["verified"] and result["integrity_level"] == "METADATA_ONLY"

    class Checked(FakeRemoteBackend):
        def list_directory(self, root):
            from dataclasses import replace

            return [
                replace(r, checksum=hashlib.md5(self.files[r.path]).hexdigest())
                if not r.is_collection
                else r
                for r in super().list_directory(root)
            ]

    backend = Checked({"i:/uploaded/result.json": b"abcd"})
    assert verify_uploaded_results(
        path, "i:/uploaded", backend=backend, require_checksums=True
    )["verified"]
    backend.files["i:/uploaded/result.json"] = b"bad!"
    assert not verify_uploaded_results(
        path, "i:/uploaded", backend=backend, require_checksums=True
    )["verified"]


def test_coordinate_validation_rejects_goldhill_style_wrong_crs_label(tmp_path):
    from spectralbridge.drone_production import validate_drone_coordinate_table

    source = tmp_path / "source.tif"
    original(source)
    table = tmp_path / "locations.csv"
    table.write_text(
        "PhotoID,X,Y,Z,Timestamp\nimg1,500000.2,4399999.8,2100,2023-08-15T19:00:00Z\n"
    )
    good = validate_drone_coordinate_table(
        table, raster_path=source, declared_crs="EPSG:26913"
    )
    assert (
        good["status"] == "VALID_HORIZONTAL_TABLE"
        and good["positions_in_raster_bounds"] == 1
    )
    bad = validate_drone_coordinate_table(
        table, raster_path=source, declared_crs="EPSG:5070"
    )
    assert bad["status"] == "INVALID" and any(
        "auto-relabel" in s for s in bad["errors"]
    )
    missing = validate_drone_coordinate_table(table, raster_path=source)
    assert missing["status"] == "INVALID"


def test_case_distinct_remote_terrain_survives_local_staging(tmp_path):
    root = "i:/originals/AOP-GOLDHILL-08-14-23-ExportPackage"
    backend = FakeRemoteBackend(
        {
            root + "/AOP-GOLDHILL_ORTHO.tif": b"ortho",
            root + "/terrain-DTM.tif": b"upper terrain",
            root + "/terrain-dtm.tif": b"lower terrain",
        }
    )
    selection = inspect_original_drone_packages(
        "i:/originals", sites=["Goldhill"], backend=backend
    )["Goldhill"]
    single = inspect_original_drone_packages(root, sites=["Goldhill"], backend=backend)[
        "Goldhill"
    ]
    assert single["orthomosaic"] == selection["orthomosaic"]
    result = stage_original_drone_package(
        selection, staging_dir=tmp_path, backend=backend
    )
    paths = [Path(r["local_path"]) for r in result["transfers"]]
    assert len({str(p).casefold() for p in paths}) == 3
    assert {p.read_bytes() for p in paths} == {
        b"ortho",
        b"upper terrain",
        b"lower terrain",
    }
    resumed = stage_original_drone_package(
        selection, staging_dir=tmp_path, backend=backend
    )
    assert all(r["status"] == "reused" for r in resumed["transfers"])


def test_preparation_success_does_not_certify_unsupported_radiometry():
    from spectralbridge.pipelines.drone import _scientific_qa_status

    assert (
        _scientific_qa_status({"radiometry": {"status": "UNSUPPORTED"}})
        == "not_evaluated"
    )
    assert _scientific_qa_status({"radiometry": {"status": "VALID"}}) == "eligible"
    assert (
        _scientific_qa_status(
            {"radiometry": {"status": "VALID"}, "qa_warnings": ["review"]}
        )
        == "caution"
    )


def test_uncalibrated_preparation_reuses_identity_copy_but_blocks_corrections(tmp_path):
    from tests.test_drone_spatial_integrity import source
    from spectralbridge.neon_cube import NeonCube
    from spectralbridge.pipelines.drone import (
        convert_drone_tiff_to_h5,
        export_h5_to_envi,
        apply_drone_corrections,
        DroneCorrectionUnavailableError,
    )

    path, _, _ = source(tmp_path)
    h5 = convert_drone_tiff_to_h5(
        path,
        output_h5_path=tmp_path / "working.h5",
        wavelengths_nm=[500, 650, 860],
        fwhm_nm=[10, 10, 10],
        radiometry={
            "scale": None,
            "offset": None,
            "status": "UNSUPPORTED",
            "provenance": "Uncalibrated regression fixture",
        },
    )
    raw, hdr = export_h5_to_envi(h5, output_stem=tmp_path / "raw")
    kwargs = dict(
        cube=NeonCube(h5),
        envi_img=raw,
        envi_hdr=hdr,
        corrected_stem=tmp_path / "identity",
    )
    img, _, audit = apply_drone_corrections(
        **kwargs, apply_topo=False, apply_brdf=False
    )
    before = img.stat().st_mtime_ns
    _, _, reused = apply_drone_corrections(**kwargs, apply_topo=False, apply_brdf=False)
    assert reused["reused_existing_corrected"] and img.stat().st_mtime_ns == before
    assert not audit["topo_applied"] and not audit["brdf_applied"]
    with pytest.raises(DroneCorrectionUnavailableError, match="Radiometry UNSUPPORTED"):
        apply_drone_corrections(**kwargs, apply_topo=True, apply_brdf=True)
