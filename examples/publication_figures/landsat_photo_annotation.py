"""Measure dated photo-interpretation polygons and test conditional PFT contrasts."""

import argparse
import hashlib
import json
from itertools import combinations, product
from math import prod
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import shapes
from rasterio.transform import from_origin
from shapely import Point, Polygon, box, union_all
from shapely.affinity import translate
from shapely.geometry import shape
from shapely.geometry.polygon import orient

from landsat_purity_audit import SOURCES
from landsat_seasonal_archive import (
    BANDS,
    CACHE,
    OUTPUT as ARCHIVE,
    REFERENCE,
    reference_frame,
    reflectance,
)
from spectralbridge.bulk.provenance import (
    signature_sha256,
    write_json_atomic,
    write_text_atomic,
)
from spectralbridge.pft_method_audit import npc_probability
from spectralbridge.plant_pft_statistics import _center, holm

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REFERENCE.parent / "photo-annotation"
POLICY = OUTPUT / "annotation_policy.json"
CATEGORIES = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Non-vegetated & dead",
    "Woody shrub",
]
CELL = box(-15, -15, 15, 15)
DOMAIN = box(-40, -40, 40, 40)


def image_classes(case, image, year, boundary_uncertainty=0):
    """Partition the reference view into target, known other, and uncertain cover."""
    if year in case.get("unresolved_years", []):
        return dict(target=Polygon(), other=Polygon(), uncertain=DOMAIN)
    patch = Polygon(case["patch"]).intersection(DOMAIN)
    manual = [Polygon(points) for points in case.get("unknown_polygons", [])]
    flagged = np.zeros(image.shape[1:], dtype=bool)
    if "dark_unknown_ceiling" in case:
        flagged |= image.min(axis=0) < case["dark_unknown_ceiling"]
    if "bright_unknown_floor" in case:
        flagged |= image.min(axis=0) > case["bright_unknown_floor"]
    if flagged.any():
        height, width = flagged.shape
        transform = from_origin(-40, 40, 80 / width, 80 / height)
        manual.extend(
            shape(geometry)
            for geometry, value in shapes(
                flagged.astype(np.uint8), mask=flagged, transform=transform
            )
            if value == 1
        )
    others = case.get("other_polygons", []) + case.get("year_other_polygons", {}).get(
        str(year), []
    )
    if boundary_uncertainty:
        manual.extend(
            Polygon(points).boundary.buffer(boundary_uncertainty) for points in others
        )
        manual.extend(
            Polygon(points).boundary.buffer(boundary_uncertainty)
            for points in case.get("unknown_polygons", [])
        )
    other = union_all([Polygon(points) for points in others]).intersection(DOMAIN)
    uncertain = (
        DOMAIN.difference(patch)
        .union(union_all(manual))
        .intersection(DOMAIN)
        .difference(other)
    )
    target = patch.difference(uncertain).difference(other)
    result = dict(target=target, other=other, uncertain=uncertain)
    if not all(geometry.is_valid for geometry in result.values()):
        raise ValueError("Invalid annotation geometry")
    if abs(sum(geometry.area for geometry in result.values()) - DOMAIN.area) > 1e-6:
        raise ValueError("Annotation classes do not partition the reference view")
    return result


def fractions(classes, cell=CELL):
    return {
        key: geometry.intersection(cell).area / cell.area
        for key, geometry in classes.items()
    }


def shifted_lower_bound(classes, distance):
    return min(
        fractions(classes, translate(CELL, xoff=x, yoff=y))["target"]
        for x, y in product((-distance, 0, distance), repeat=2)
    )


def image_for(reference, aerial_id):
    identity = signature_sha256(
        dict(
            id=reference.name,
            east=reference.easting,
            north=reference.northing,
            epsg=int(reference.landsat_epsg),
            aerial=aerial_id,
        )
    )[:20]
    path = CACHE / f"aerial-{identity}.npy"
    return np.load(path), path


def annotate():
    policy = json.loads(POLICY.read_text())
    references = pd.read_csv(REFERENCE / "regional_candidate_dataset.csv").set_index(
        "candidate_id"
    )
    aerials = pd.concat(
        [pd.read_csv(path) for path in ARCHIVE.glob("*-aerial-timeline.csv")],
        ignore_index=True,
    )
    rows, features, panels = [], [], []
    for case in policy["cases"]:
        candidate = case["candidate_id"]
        reference = references.loc[candidate]
        for year in case["years"]:
            matching = aerials.loc[
                aerials.candidate_id.eq(candidate)
                & aerials.aerial_date.str[:4].eq(str(year))
            ]
            if len(matching) != 1:
                raise ValueError(
                    f"Need exactly one reviewed aerial epoch for {candidate}/{year}"
                )
            aerial = matching.iloc[0]
            image, path = image_for(reference, aerial.aerial_id)
            classes = image_classes(
                case, image, year, policy.get("manual_boundary_uncertainty_m", 0)
            )
            fraction = fractions(classes)
            event_id = f"{candidate}-{year}"
            rows.append(
                dict(
                    annotation_id=event_id,
                    candidate_id=candidate,
                    region=reference.region,
                    year=year,
                    target=case["target"],
                    aerial_id=aerial.aerial_id,
                    aerial_date=aerial.aerial_date,
                    target_fraction=fraction["target"],
                    other_fraction=fraction["other"],
                    uncertain_fraction=fraction["uncertain"],
                    target_upper_bound=fraction["target"] + fraction["uncertain"],
                    target_area_m2=fraction["target"] * 900,
                    other_area_m2=fraction["other"] * 900,
                    uncertain_area_m2=fraction["uncertain"] * 900,
                    lower_shift3=shifted_lower_bound(classes, 3),
                    lower_shift5=shifted_lower_bound(classes, 5),
                    interpreter=policy["interpreter"],
                    independent_second_interpreter=False,
                    source_view_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    source_view=str(path.relative_to(ROOT)),
                    interpretation=case["note"],
                )
            )
            for label, geometry in classes.items():
                if not geometry.is_empty:
                    features.append(
                        dict(
                            annotation_id=event_id,
                            candidate_id=candidate,
                            year=year,
                            target=case["target"],
                            area_class=label,
                            aerial_id=aerial.aerial_id,
                            epsg=int(reference.landsat_epsg),
                            geometry=translate(
                                geometry, reference.easting, reference.northing
                            ),
                        )
                    )
            panels.append((event_id, image, classes, fraction))
    table = pd.DataFrame(rows)
    write_text_atomic(OUTPUT / "dated_cover_fractions.csv", table.to_csv(index=False))
    temporary = OUTPUT / "annotations.tmp.gpkg"
    if temporary.exists():
        temporary.unlink()
    for epsg in sorted({row["epsg"] for row in features}):
        frame = gpd.GeoDataFrame(
            [row for row in features if row["epsg"] == epsg], crs=epsg
        )
        frame.to_file(temporary, layer=f"cover_epsg{epsg}", driver="GPKG")
    temporary.replace(OUTPUT / "annotations.gpkg")
    draw_annotations(panels)
    record_field_support(references, policy["cases"])
    write_json_atomic(
        OUTPUT / "annotation_manifest.json",
        dict(
            policy_sha256=hashlib.sha256(POLICY.read_bytes()).hexdigest(),
            fraction_sha256=hashlib.sha256(
                (OUTPUT / "dated_cover_fractions.csv").read_bytes()
            ).hexdigest(),
            geometry_sha256=hashlib.sha256(
                (OUTPUT / "annotations.gpkg").read_bytes()
            ).hexdigest(),
            source_reference_sha256=hashlib.sha256(
                (REFERENCE / "regional_candidate_dataset.csv").read_bytes()
            ).hexdigest(),
            annotation_count=len(table),
            footprint_count=int(table.candidate_id.nunique()),
            interpreter=policy["interpreter"],
            independent_second_interpreter=False,
        ),
    )
    return table


def record_field_support(references, cases):
    sources = []
    for name, path in SOURCES.items():
        source = gpd.read_file(
            path, columns=["GlobalID", "cover_category", "collection_date"]
        )
        source.geometry = source.geometry.make_valid()
        source["field_source"] = name
        sources.append(source.to_crs(4326))
    fields = gpd.GeoDataFrame(pd.concat(sources, ignore_index=True), crs=4326)
    records = []
    for case in cases:
        reference = references.loc[case["candidate_id"]]
        projected = fields.to_crs(int(reference.landsat_epsg))
        cell = translate(CELL, reference.easting, reference.northing)
        distances = projected.geometry.distance(
            Point(reference.easting, reference.northing)
        )
        nearest = projected.iloc[int(np.argmin(distances.to_numpy()))]
        target = projected.loc[projected.cover_category.eq(case["target"])]
        target_distance = target.geometry.distance(
            Point(reference.easting, reference.northing)
        ).min()
        overlapping = projected.iloc[
            projected.sindex.query(cell, predicate="intersects")
        ]
        covered = union_all(overlapping.geometry).intersection(cell).area / 900
        target_covered = (
            union_all(
                overlapping.loc[
                    overlapping.cover_category.eq(case["target"]), "geometry"
                ]
            )
            .intersection(cell)
            .area
            / 900
        )
        records.append(
            dict(
                candidate_id=case["candidate_id"],
                proposed_target=case["target"],
                mapped_field_fraction=covered,
                mapped_target_field_fraction=target_covered,
                nearest_field_distance_m=float(distances.min()),
                nearest_field_category=nearest.cover_category,
                nearest_field_id=nearest.GlobalID,
                nearest_field_date=str(nearest.collection_date),
                nearest_target_field_distance_m=float(target_distance),
            )
        )
    write_text_atomic(
        OUTPUT / "field_anchor_support.csv", pd.DataFrame(records).to_csv(index=False)
    )


def draw_geometry(ax, geometry, color, alpha):
    parts = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    for polygon in parts:
        if polygon.is_empty:
            continue
        polygon = orient(polygon, sign=1)
        paths = []
        for ring in (polygon.exterior, *polygon.interiors):
            vertices = np.asarray(ring.coords)
            codes = np.full(len(vertices), PlotPath.LINETO)
            codes[0], codes[-1] = PlotPath.MOVETO, PlotPath.CLOSEPOLY
            paths.append(PlotPath(vertices, codes))
        ax.add_patch(
            PathPatch(
                PlotPath.make_compound_path(*paths),
                facecolor=color,
                edgecolor="none",
                alpha=alpha,
            )
        )


def draw_annotations(panels):
    for start in range(0, len(panels), 4):
        subset = panels[start : start + 4]
        figure, axes = plt.subplots(
            len(subset), 2, figsize=(11, 3 * len(subset)), squeeze=False
        )
        for index, (event, image, classes, fraction) in enumerate(subset):
            for ax in axes[index]:
                ax.imshow(
                    np.moveaxis(image / 255, 0, -1),
                    extent=(-40, 40, -40, 40),
                    interpolation="nearest",
                )
                ax.add_patch(
                    plt.Rectangle(
                        (-15, -15), 30, 30, fill=False, edgecolor="cyan", linewidth=1.2
                    )
                )
                ax.set_xlim(-20, 20)
                ax.set_ylim(-20, 20)
                ax.tick_params(labelsize=7)
            axes[index, 0].set_title(event, fontsize=9)
            axes[index, 1].set_title(
                f"Mapped target {fraction['target']:.1%} · uncertain {fraction['uncertain']:.1%} · other {fraction['other']:.1%}",
                fontsize=9,
            )
            draw_geometry(axes[index, 1], classes["uncertain"], "#ffbd2e", 0.55)
            draw_geometry(axes[index, 1], classes["other"], "#d12175", 0.60)
        figure.suptitle("Photo reference and interpreted exclusions", weight="bold")
        figure.text(
            0.5,
            0.012,
            "Cyan = 30 m cell. Orange = uncertain. Magenta = known other cover. Target remains visible beneath the annotation.",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.035, 1, 0.97))
        figure.savefig(OUTPUT / f"annotation-review-{start // 4 + 1:02d}.png", dpi=130)
        plt.close(figure)


def exact_statistics(values, labels, blocks):
    """Enumerate whole-footprint labels using the package's max/integrated NPC."""
    y, z, b = np.asarray(values, float), np.asarray(labels, float), np.asarray(blocks)
    centered = _center(y, b)
    scale = np.sqrt(np.sum(centered**2, axis=0) / (len(y) - len(np.unique(b))))
    informative = np.isfinite(y).all(axis=0) & (scale > 0)
    if informative.sum() < 2:
        raise ValueError("Need two finite variable bands")
    standardized = centered[:, informative] / scale[informative]
    x = _center(z[:, None], b).ravel()
    xx = x @ x
    choices = []
    for block in np.unique(b):
        indices = np.flatnonzero(b == block)
        positives = int(z[indices].sum())
        choices.append(list(combinations(indices, positives)))
    count = prod(len(choice) for choice in choices)
    if count > 100000:
        raise ValueError("Exact reference permutation budget exceeded")
    permutations = []
    for assignment in product(*choices):
        row = np.zeros(len(z))
        for indices in assignment:
            row[list(indices)] = 1
        permutations.append(row)
    ensemble = np.asarray(permutations)
    observed = np.flatnonzero(np.all(ensemble == z, axis=1))[0]
    ensemble[[0, observed]] = ensemble[[observed, 0]]
    t = ensemble @ standardized / np.sqrt(xx)
    stats = np.column_stack([np.abs(t).max(axis=1), np.mean(t * t, axis=1)])
    p_max = float(
        np.mean(stats[:, 0] >= stats[0, 0] - 1e-12 * max(1, abs(stats[0, 0])))
    )
    p_integrated = float(
        np.mean(stats[:, 1] >= stats[0, 1] - 1e-12 * max(1, abs(stats[0, 1])))
    )
    beta = z @ centered[:, informative] / xx
    return dict(
        p_npc=npc_probability(stats),
        p_max=p_max,
        p_integrated=p_integrated,
        permutations=count,
        effect=float(np.sqrt(np.mean((beta / scale[informative]) ** 2))),
        observed_max=float(stats[0, 0]),
        observed_integrated=float(stats[0, 1]),
    )


def scene_candidates(accepted, qa, maximum_gap_days=45):
    matched = qa.merge(accepted, on=["candidate_id", "year"], validate="many_to_one")
    matched = matched.loc[matched.eligible_observation].copy()
    gap = (
        (
            pd.to_datetime(
                matched.acquisition_datetime.map(pd.Timestamp), utc=True
            ).dt.normalize()
            - pd.to_datetime(
                matched.aerial_date.map(pd.Timestamp), utc=True
            ).dt.normalize()
        )
        .abs()
        .dt.days
    )
    matched["aerial_gap_days"] = gap
    return matched.loc[gap.le(maximum_gap_days)]


def extract_cohort(group):
    region, year, scene_id = (
        group.region.iloc[0],
        int(group.year.iloc[0]),
        group.scene_id.iloc[0],
    )
    items = json.loads((ARCHIVE / f"{region}-{year}-catalogue.json").read_text())[
        "features"
    ]
    item = next(item for item in items if item["id"] == scene_id)
    references = reference_frame(region)
    identity = signature_sha256(
        references[
            ["candidate_id", "easting", "northing", "landsat_epsg", "scene_datetime"]
        ].to_dict("records")
    )[:16]
    values = reflectance(item, references, identity)
    positions = {value: index for index, value in enumerate(references.candidate_id)}
    result = group.copy()
    for band_index, band in enumerate(BANDS):
        result[band] = [
            values[positions[value], band_index] for value in group.candidate_id
        ]
    return result.loc[np.isfinite(result[BANDS]).all(axis=1)]


def validate_annotation_checkpoint():
    ledger = json.loads((OUTPUT / "annotation_manifest.json").read_text())
    inputs = {
        "policy_sha256": POLICY,
        "fraction_sha256": OUTPUT / "dated_cover_fractions.csv",
        "geometry_sha256": OUTPUT / "annotations.gpkg",
        "source_reference_sha256": REFERENCE / "regional_candidate_dataset.csv",
    }
    for key, path in inputs.items():
        if ledger.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(
                f"Stale annotation checkpoint for {path.name}. Rebuild with --annotate before --test."
            )


def run_tests():
    validate_annotation_checkpoint()
    fractions_table = pd.read_csv(OUTPUT / "dated_cover_fractions.csv")
    qa = pd.concat(
        [pd.read_csv(path) for path in ARCHIVE.glob("*-qa.csv")], ignore_index=True
    )
    policy = json.loads(POLICY.read_text())
    primary = fractions_table.loc[
        fractions_table.target_fraction.ge(policy["primary_threshold"] - 1e-9)
    ]
    annual = pd.read_csv(ARCHIVE / "seasonal_observations.csv")
    primary_data = scene_candidates(
        primary[
            [
                "annotation_id",
                "candidate_id",
                "year",
                "target",
                "aerial_date",
                "target_fraction",
                "uncertain_fraction",
                "other_fraction",
            ]
        ],
        annual.loc[annual.observation_status.eq("selected")],
        policy["maximum_same_year_aerial_landsat_gap_days"],
    )
    primary_data["reference_status"] = "single_interpreter_photo_annotation"
    primary_data["photo_screen_pass"] = True
    primary_data["independent_second_interpreter"] = False
    write_text_atomic(
        OUTPUT / "photo_supported_observations.csv", primary_data.to_csv(index=False)
    )
    all_results, memberships, support = [], [], []
    for threshold, shift in product(
        policy["sensitivity_thresholds"], policy["shift_distances_m"]
    ):
        column = "target_fraction" if shift == 0 else f"lower_shift{shift}"
        accepted = fractions_table.loc[
            fractions_table[column].ge(threshold - 1e-9)
        ].copy()
        matched = scene_candidates(
            accepted, qa, policy["maximum_same_year_aerial_landsat_gap_days"]
        )
        for label in CATEGORIES:
            group = matched.loc[matched.target.eq(label)]
            support.append(
                dict(
                    threshold=threshold,
                    shift_m=shift,
                    label=label,
                    accepted_footprints=group.candidate_id.nunique(),
                    supported_photo_years=group[["candidate_id", "year"]]
                    .drop_duplicates()
                    .shape[0],
                )
            )
        for a, b in combinations(CATEGORIES, 2):
            pair = matched.loc[matched.target.isin([a, b])]
            selected = []
            for region, regional in pair.groupby("region"):
                ranked = []
                for (year, scene), cohort in regional.groupby(["year", "scene_id"]):
                    counts = cohort.target.value_counts()
                    if min(counts.get(a, 0), counts.get(b, 0)) > 0:
                        ranked.append(
                            (
                                (
                                    -min(counts[a], counts[b]),
                                    -len(cohort),
                                    -int(cohort.preferred_aerosol.sum()),
                                    int(cohort.aerial_gap_days.sum()),
                                    scene,
                                ),
                                cohort,
                            )
                        )
                for _, cohort in sorted(ranked, key=lambda item: item[0]):
                    data = extract_cohort(cohort)
                    if set(data.target) == {a, b}:
                        selected.append(data)
                        break
            row = dict(
                threshold=threshold,
                shift_m=shift,
                a=a,
                b=b,
                status="no_matched_photo_supported_cohort",
                n_a=0,
                n_b=0,
                blocks=0,
                p_npc=np.nan,
                p_max=np.nan,
                p_integrated=np.nan,
                permutations=0,
                effect=np.nan,
            )
            if selected:
                data = pd.concat(selected, ignore_index=True)
                if data.candidate_id.duplicated().any():
                    raise ValueError("Repeated footprint in a permutation cohort")
                blocks = pd.factorize(data.region.astype(str) + "/" + data.scene_id)[0]
                result = exact_statistics(
                    data[BANDS].to_numpy(), data.target.eq(a).to_numpy(float), blocks
                )
                row.update(
                    result,
                    status="exploratory_photo_labels",
                    n_a=int(data.target.eq(a).sum()),
                    n_b=int(data.target.eq(b).sum()),
                    blocks=len(np.unique(blocks)),
                )
                data = data[
                    [
                        "candidate_id",
                        "region",
                        "year",
                        "scene_id",
                        "acquisition_datetime",
                        "target",
                        "aerial_date",
                        *BANDS,
                    ]
                ].copy()
                data["threshold"], data["shift_m"], data["contrast"] = (
                    threshold,
                    shift,
                    a + " / " + b,
                )
                memberships.append(data)
            all_results.append(row)
    results = pd.DataFrame(all_results)
    results["p_npc_holm"] = np.nan
    for _, indices in results.groupby(["threshold", "shift_m"]).groups.items():
        values = results.loc[indices, "p_npc"].fillna(1).to_numpy()
        adjusted = holm(values)
        tested = results.loc[indices, "p_npc"].notna().to_numpy()
        results.loc[np.asarray(indices)[tested], "p_npc_holm"] = adjusted[tested]
    write_text_atomic(OUTPUT / "separability.csv", results.to_csv(index=False))
    write_text_atomic(
        OUTPUT / "purity_support.csv", pd.DataFrame(support).to_csv(index=False)
    )
    if memberships:
        write_text_atomic(
            OUTPUT / "test_memberships.csv",
            pd.concat(memberships, ignore_index=True).to_csv(index=False),
        )
    return results


def write_provenance():
    files = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(OUTPUT.iterdir())
        if path.suffix in {".json", ".csv", ".png", ".gpkg", ".md"}
        and path.name != "provenance.json"
    }
    write_json_atomic(
        OUTPUT / "provenance.json",
        dict(
            builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            seasonal_archive_manifest_sha256=hashlib.sha256(
                (ARCHIVE / "manifest.json").read_bytes()
            ).hexdigest(),
            field_source_sha256={
                str(path.relative_to(ROOT)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in SOURCES.values()
            },
            interpreter="OpenAI Codex",
            independent_second_interpreter=False,
            files=files,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.annotate:
        frame = annotate()
        print(
            frame[
                [
                    "candidate_id",
                    "year",
                    "target",
                    "target_fraction",
                    "uncertain_fraction",
                    "other_fraction",
                ]
            ].to_string(index=False)
        )
    if args.test:
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            GDAL_HTTP_TIMEOUT=30,
            GDAL_HTTP_MAX_RETRY=2,
        ):
            result = run_tests()
        print(result.query("threshold==.95 and shift_m==0").to_string(index=False))

    if args.annotate or args.test:
        write_provenance()
