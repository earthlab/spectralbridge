"""Shared immutable input references and restart checkpoints for researcher-only v1."""

from pathlib import Path
import hashlib
import json
import logging
import platform
import numpy as np
import pandas as pd
import scipy
import sklearn
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.researcher_information import validate_researcher_labels
from spectralbridge.spectral_learning import LearningConfig, outer_folds
from spectralbridge.bulk.provenance import write_json_atomic

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
CACHE = REPO / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1"
SEED = 20261015
LOG = logging.getLogger("researcher_information")


def save(frame, name):
    path = BASE / "tables" / name
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)


def seed(name):
    return (SEED + int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)) % (2**32 - 1)


def load():
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    compact = REPO / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
    ledger = json.loads((compact.parent / "statistics_manifest.json").read_text())
    assert _file_hash(source) == ledger["identity"]["source"]
    for product in [
        "compact/corr_polygon_year.parquet",
        "compact/olioli_undarkened_polygon_year.parquet",
    ]:
        assert _file_hash(compact.parent / product) == ledger["outputs"][product]
    t, arrays, waves = load_compact_inputs(
        source, compact, include_historical_labels=False
    )
    t = t[
        [
            "GlobalID",
            "site",
            "year",
            "flight_history",
            "flight_observations",
            "cover_category",
            "flights",
        ]
    ].copy()
    validate_researcher_labels(t.cover_category)
    t["label"] = t.cover_category
    assert not t.duplicated(["GlobalID", "year"]).any()
    assert all(np.isfinite(v).all() for v in arrays.values())
    identity = {
        "source_sha256": _file_hash(source),
        "canonical_manifest_sha256": _file_hash(
            compact.parent / "statistics_manifest.json"
        ),
        "label_field": "cover_category",
        "seed": SEED,
        "metadata_rows": len(t),
        "identities": t.GlobalID.nunique(),
        "NEON_coordinates": len(waves["NEON"]),
        "OLI_channels": len(waves["OLI"]),
        "source_read_in_place": True,
        "units": "stored spectral units; absolute reflectance scale unresolved",
    }
    write_json_atomic(BASE / "input_identity.json", identity)
    env = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "platform": platform.platform(),
    }
    write_json_atomic(BASE / "environment.json", env)
    save(t.drop(columns=["flights", "label"]), "observation_index.csv")
    return t, arrays, waves, identity


def folds(t, paired=True):
    for name, kind, tr, te in outer_folds(t, LearningConfig()):
        if kind in {"plant", "site", "year"}:
            yield name, kind, tr, te
    if paired:
        from sklearn.model_selection import StratifiedKFold

        ids = (
            t[t.site.eq("NIWO")]
            .groupby("GlobalID")
            .filter(lambda g: len(g) == 2)
            .drop_duplicates("GlobalID")
        )
        for k, (a, b) in enumerate(
            StratifiedKFold(3, shuffle=True, random_state=SEED).split(ids, ids.label)
        ):
            for trainyear in [2020, 2023]:
                tr = t.GlobalID.isin(ids.GlobalID.iloc[a]) & t.year.eq(trainyear)
                for testyear in [2020, 2023]:
                    te = t.GlobalID.isin(ids.GlobalID.iloc[b]) & t.year.eq(testyear)
                    yield (
                        f"paired_train{trainyear}_target{testyear}_{k}",
                        "paired_year",
                        tr.to_numpy(),
                        te.to_numpy(),
                    )


def checkpoint(name, identity, action):
    directory = CACHE / name
    directory.mkdir(parents=True, exist_ok=True)
    ledger = directory / "complete.json"
    if ledger.exists():
        old = json.loads(ledger.read_text())
        if old["identity"] != identity:
            raise ValueError(
                "Changed checkpoint identity: " + name + "; use a fresh version"
            )
        for p, h in old["outputs"].items():
            if _file_hash(directory / p) != h:
                raise ValueError("Changed owned checkpoint: " + p)
        LOG.info("Reused %s", name)
        return directory
    action(directory)
    outputs = {
        str(p.relative_to(directory)): _file_hash(p)
        for p in directory.rglob("*")
        if p.is_file() and p != ledger
    }
    write_json_atomic(ledger, {"identity": identity, "outputs": outputs})
    return directory
