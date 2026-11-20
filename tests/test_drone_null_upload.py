"""Reject stale/null payloads before any datastore mutation."""

import importlib
import json
from pathlib import Path
import sys

import pytest

pytest.importorskip("irods")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
upload = importlib.import_module("upload_unmasked_drone_translation_null")
sys.path.pop(0)


def manifest(tmp_path):
    products = []
    for i in range(6):
        product = dict(site=["ruby", "gordon", "goldhill"][i // 2], sha256={})
        for key in ["output_img", "output_hdr", "provenance_json"]:
            p = tmp_path / f"{i}_{key}"
            p.write_text(f"{i} {key}")
            product[key] = str(p)
            product["sha256"][str(p)] = upload.digest_file(p)
        products.append(product)
    d = dict(
        independent_native_algebra="PASS",
        gdal_metadata="PASS",
        masked_reference_hashes_unchanged=True,
        products=products,
    )
    (tmp_path / "verification.json").write_text(json.dumps(d))
    return d


def test_null_upload_includes_six_verified_products_and_complete_qa(tmp_path):
    manifest(tmp_path)
    files = upload.payload_files(tmp_path)
    assert len(files) == 34
    assert sum(remote.endswith("baseline_brdf_qa.json") for _, remote in files) == 3
    assert any(remote == "translated_null_vs_10percent.csv" for _, remote in files)


def test_null_upload_rejects_changed_product_before_network(tmp_path):
    d = manifest(tmp_path)
    Path(d["products"][0]["output_img"]).write_text("changed")
    with pytest.raises(ValueError, match="Changed verified null product"):
        upload.payload_files(tmp_path)
