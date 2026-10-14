"""Compare completed boosted matching with held-out empirical-template baselines."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from spectralbridge.plant_spectral_quantiles import _model_inputs


def nearest_templates(queries, references, labels, batch_size=16):
    """Bounded MAE/RMSE rankings over an identical supported wavelength set."""
    queries, references = np.asarray(queries), np.asarray(references)
    supported = np.isfinite(queries).all(0) & np.isfinite(references).all(0)
    if supported.sum() < 2:
        raise ValueError("Insufficient common template bands")
    labels = np.asarray(labels)
    mae, rmse = [], []
    for start in range(0, len(queries), batch_size):
        difference = (
            queries[start : start + batch_size, None, supported]
            - references[None, :, supported]
        )
        mae.extend(labels[np.argmin(np.mean(np.abs(difference), axis=2), axis=1)])
        rmse.extend(labels[np.argmin(np.mean(difference**2, axis=2), axis=1)])
    return np.array(mae), np.array(rmse)


def evaluate(comparisons, models, output):
    comparisons, models, out = Path(comparisons), Path(models), Path(output)
    out.mkdir(parents=True, exist_ok=True)
    plants, data, _, _, hashes = _model_inputs(comparisons)
    manifest = json.loads((models / "quantile_manifest.json").read_text())
    if manifest["identity"]["inputs"] != hashes:
        raise ValueError(
            "Model references and compact spectra belong to different inputs"
        )
    split = pd.read_parquet(models / "training_holdout_plants.parquet").set_index(
        "GlobalID"
    )
    positions = plants.set_index("GlobalID").assign(position=np.arange(len(plants)))[
        "position"
    ]
    index = pd.read_parquet(models / "model_index.parquet")
    individual = pd.read_csv(models / "held_out_individual_reference_matches.csv")
    species = pd.read_csv(models / "held_out_species_matches.csv")
    rows = []
    for level, table, grouping in [
        ("species", species, ["scope", "stage"]),
        ("individual", individual, ["region", "stage"]),
    ]:
        for (scope, stage), queries in table.groupby(grouping):
            candidates = index[(index.level == level) & (index.stage == stage)]
            candidates = candidates[
                candidates.partition == ("train" if level == "species" else "full")
            ]
            if level == "species":
                candidates = candidates[candidates.region == scope]
            else:
                candidates = candidates[
                    (candidates.region == scope)
                    & candidates.GlobalID.isin(split.index[split.partition == "train"])
                ]
            training = split[split.partition == "train"]
            if scope != "ALL":
                training = training[training.region == scope]
            training = training[training.species.isin(candidates.species)]
            _, values = data[stage]
            if level == "species":
                templates = []
                labels = []
                for label, group in training.groupby("species", sort=True):
                    selected = values[positions.loc[group.index].to_numpy()]
                    templates.append(
                        np.ma.median(np.ma.masked_invalid(selected), axis=0).filled(
                            np.nan
                        )
                    )
                    labels.append(label)
            else:
                templates = values[positions.loc[training.index].to_numpy()]
                labels = training.species.to_numpy()
            predictions_mae, predictions_rmse = nearest_templates(
                values[positions.loc[queries.GlobalID].to_numpy()],
                np.asarray(templates),
                labels,
            )
            frequencies = training.species.value_counts()
            majority = sorted(
                frequencies.index, key=lambda name: (-frequencies[name], name)
            )[0]
            rows.append(
                {
                    "level": level,
                    "scope": scope,
                    "stage": stage,
                    "held_out_plants": len(queries),
                    "boosted_top1_accuracy": float(queries.top1_correct.mean()),
                    "empirical_template_MAE_accuracy": float(
                        np.mean(predictions_mae == queries.true_species.to_numpy())
                    ),
                    "empirical_template_RMSE_accuracy": float(
                        np.mean(predictions_rmse == queries.true_species.to_numpy())
                    ),
                    "majority_class_accuracy": float(
                        np.mean(queries.true_species == majority)
                    ),
                    "majority_species": majority,
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(out / "matching_baselines.csv", index=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparisons", default="artifacts/plant_spectral_atlas/comparisons"
    )
    parser.add_argument(
        "--models", default="artifacts/plant_spectral_atlas/quantile_models"
    )
    parser.add_argument(
        "--output", default="artifacts/plant_spectral_atlas/quantile_validation"
    )
    args = parser.parse_args()
    print(evaluate(args.comparisons, args.models, args.output).to_string(index=False))
