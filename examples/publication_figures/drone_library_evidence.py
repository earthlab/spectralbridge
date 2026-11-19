"""Exploratory five-band PFT evidence from verified calibration-site polygons."""

import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from landsat_pft_panel import BANDS, CATEGORIES, DRONE, LABEL, OUTPUT, load_spectra
from spectralbridge.pft_method_audit import AuditConfig, method_statistics
from spectralbridge.plant_pft_statistics import holm

DESTINATION = OUTPUT / "drone_library_tests"
SEED = 20261118


def classify(frame):
    """Hold each polygon out once; fit scaling and model on training rows only."""
    x, y = frame[BANDS[:5]].to_numpy(), frame[LABEL].to_numpy()
    records = []
    schemes = {
        "unseen_polygon": list(
            StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
        ),
        "held_out_site": [
            (np.flatnonzero(frame.site.ne(site)), np.flatnonzero(frame.site.eq(site)))
            for site in sorted(frame.site.unique())
        ],
    }
    for scheme, splits in schemes.items():
        for fold, (train, test) in enumerate(splits):
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced", C=1, max_iter=2000),
            )
            model.fit(x[train], y[train])
            predicted = model.predict(x[test])
            for index, prediction in zip(test, predicted, strict=True):
                records.append(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        GlobalID=frame.iloc[index].GlobalID,
                        site=frame.iloc[index].site,
                        truth=y[index],
                        prediction=prediction,
                        truth_in_training=bool(y[index] in y[train]),
                    )
                )
    return pd.DataFrame(records)


def run():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    sources = sorted(DRONE.glob("**/*__polygons.parquet"))
    identity = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
    }
    identity["builder"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    identity["figure_loader"] = hashlib.sha256(
        Path(__file__).with_name("landsat_pft_panel.py").read_bytes()
    ).hexdigest()
    identity["statistic_code"] = hashlib.sha256(
        Path(
            __import__("spectralbridge.pft_method_audit", fromlist=["x"]).__file__
        ).read_bytes()
    ).hexdigest()
    frame = (
        list(load_spectra().values())[2].sort_values("GlobalID").reset_index(drop=True)
    )
    if (
        frame.GlobalID.duplicated().any()
        or not np.isfinite(frame[BANDS[:5]]).all().all()
    ):
        raise ValueError("Drone evidence requires unique finite polygon spectra")
    manifest = DESTINATION / "manifest.json"
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if saved.get("identity") == identity and all(
            (DESTINATION / name).exists()
            and hashlib.sha256((DESTINATION / name).read_bytes()).hexdigest() == digest
            for name, digest in saved["outputs"].items()
        ):
            print("Reusing verified drone evidence", flush=True)
            return
    frame.to_csv(DESTINATION / "polygon_spectra.csv", index=False)
    pairs = []
    for index, (a, b) in enumerate(combinations(CATEGORIES, 2)):
        pair = frame.loc[frame[LABEL].isin([a, b])].copy()
        # Permute complete polygon labels only in sites containing both classes.
        mixed = pair.groupby("site")[LABEL].nunique()
        pair = pair.loc[pair.site.isin(mixed.index[mixed.eq(2)])]
        n_a, n_b = int(pair[LABEL].eq(a).sum()), int(pair[LABEL].eq(b).sum())
        print(f"Drone pair {index + 1}/10: {a} / {b}; n={n_a}/{n_b}", flush=True)
        record = dict(
            a=a,
            b=b,
            n_a=n_a,
            n_b=n_b,
            sites=pair.site.nunique(),
            p_npc=np.nan,
            status="insufficient_support",
        )
        if min(n_a, n_b) >= 2:
            result = method_statistics(
                pair[BANDS[:5]],
                pair[LABEL].eq(a).astype(int),
                pair.site,
                [444, 475, 560, 668, 842],
                config=AuditConfig(permutations=9999, seed=SEED + index),
                integration_weights=np.ones(5),
            )
            record.update(
                p_npc=result["p"]["npc"], status="exploratory_calibration_library"
            )
        pairs.append(record)
    pairs = pd.DataFrame(pairs)
    pairs["p_npc_holm"] = holm(pairs.p_npc.fillna(1))
    pairs.loc[pairs.p_npc.isna(), "p_npc_holm"] = np.nan
    pairs.to_csv(DESTINATION / "separability.csv", index=False)
    predictions = classify(frame)
    predictions.to_csv(DESTINATION / "identification_predictions.csv", index=False)
    rows = []
    for category in CATEGORIES:
        tests = pairs.loc[pairs.a.eq(category) | pairs.b.eq(category)]
        supported = int(tests.p_npc_holm.le(0.05).sum())
        recalls = []
        for scheme in ["unseen_polygon", "held_out_site"]:
            selected = predictions.loc[
                predictions.scheme.eq(scheme) & predictions.truth.eq(category)
            ]
            recalls.append(
                float(selected.prediction.eq(selected.truth).mean())
                if selected.truth_in_training.all()
                else np.nan
            )
        rows.append(
            dict(
                category=category,
                n=int(frame[LABEL].eq(category).sum()),
                separability=f"{supported}/{int(tests.p_npc.notna().sum())} supported‡",
                identification=" / ".join(
                    f"{value:.0%}" if np.isfinite(value) else "NA" for value in recalls
                )
                + "‡",
                supported_pairs=supported,
                tested_pairs=int(tests.p_npc.notna().sum()),
                unseen_polygon_recall=recalls[0],
                held_out_site_recall=recalls[1],
            )
        )
    pd.DataFrame(rows).to_csv(DESTINATION / "class_summary.csv", index=False)
    outputs = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in DESTINATION.glob("*.csv")
    }
    manifest.write_text(
        json.dumps(
            dict(
                identity=identity,
                outputs=outputs,
                seed=SEED,
                permutations=9999,
                bands=BANDS[:5],
                scale="physical reflectance polygon medians; tests unnormalized",
                model="StandardScaler + balanced logistic C=1; five stratified polygon folds and two leave-site-out folds",
                limitations="Two calibration sites; conditional site exchangeability; no independent external validation. Different protocol from archived NEON classification. When a class is absent from the training site, its held-site recall is unavailable (NA); predictions and support flags remain archived.",
                versions=dict(
                    numpy=np.__version__,
                    pandas=pd.__version__,
                    sklearn=__import__("sklearn").__version__,
                ),
            ),
            indent=2,
        )
        + "\n"
    )
    print(pd.DataFrame(rows).to_string(index=False), flush=True)


if __name__ == "__main__":
    run()
