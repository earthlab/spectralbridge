"""Create read-only visual review evidence for every current HLS reference cell.

No new labels/imagery/spectra are created. Frozen aerials, cover polygons, structural
arrays and current cohort are the evidence. Writes numbered plates and a blank
team review ledger. Example selection uses geometry/support only, never spectra.
"""

import json
from itertools import product
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely import box

from landsat_hls_reference_rebuild import (
    photo_fraction,
    source_kernel,
    structural_fraction,
)
from landsat_spatial_expansion import ROOT, sha

ROUND = ROOT / "provenance/landsat-pure-pixels/2026-11-18/expanded-search/round-2"
POWER = ROUND / "power-directed-expansion"
COHORT = POWER / "review-batch-2/hls-combined"
REPORT = ROOT / "provenance/landsat-pure-pixels/2026-11-19/team-validation"
CATEGORIES = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "Non-vegetated & dead",
]
CACHE_DIRS = [
    ROOT / "archive/local/landsat-spatial-expansion",
    ROOT / "archive/local/landsat-power-expansion",
]
PALETTE = ["#ccd0d3", "#218b86", "#bb8759"]


def choose_examples(accepted, candidates):
    """Interior, weakest retained nominal cell, closest rejected cover cell."""
    easy = accepted.sort_values(
        ["source_kernel_target_fraction", "nominal_target_fraction", "candidate_id"],
        ascending=[False, False, True],
    ).iloc[0]
    rest = accepted[accepted.candidate_id != easy.candidate_id]
    edge = (
        (rest if len(rest) else accepted)
        .sort_values(
            ["nominal_target_fraction", "source_kernel_target_fraction", "candidate_id"]
        )
        .iloc[0]
    )
    rejected = candidates[~candidates.nominal_95pct]
    reject = (
        rejected.sort_values(
            ["nominal_target_fraction", "candidate_id"], ascending=[False, True]
        ).iloc[0]
        if len(rejected)
        else None
    )
    return [("A", easy), ("B", edge), ("R", reject)]


def bool_value(x):
    return str(x).lower() in {"true", "1"}


def preserve_team_reviews(ledger, path):
    """Never erase human decisions when reproducing a review pack."""
    fields = [
        "reviewer",
        "team_decision",
        "revised_pft",
        "confidence",
        "issue_tags",
        "review_notes",
    ]
    if not path.exists():
        return ledger
    previous = pd.read_csv(path, keep_default_na=False)
    if set(previous.review_id) != set(ledger.review_id):
        raise ValueError("Review identity set changed; use a new report version")
    old = previous.set_index("review_id")
    if (
        not ledger.set_index("review_id")
        .candidate_id.sort_index()
        .equals(old.candidate_id.sort_index())
    ):
        raise ValueError(
            "Review IDs point to different candidates; preserve existing reviews"
        )
    result = ledger.copy()
    for field in fields:
        result[field] = result.review_id.map(old[field])
    return result


def load_sources():
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "plates").mkdir(exist_ok=True)
    obs = pd.read_csv(COHORT / "hls_l30_nominal_95pct_observations.csv")
    if len(obs) != 1241 or obs.context_patch_id.nunique() != 61:
        raise ValueError(
            "Current frozen cohort differs; explicitly version this report"
        )
    if obs.candidate_id.duplicated().any():
        raise ValueError("Repeated physical cells")
    assert (
        not obs.pft_purity_verified.any()
        and not obs.independent_second_interpreter.any()
    )
    sources = {
        str(COHORT / "hls_l30_nominal_95pct_observations.csv"): sha(
            COHORT / "hls_l30_nominal_95pct_observations.csv"
        )
    }
    covers = pd.concat(
        [pd.read_csv(p) for p in sorted(COHORT.glob("*-all_cover_measurements.csv"))],
        ignore_index=True,
    ).drop_duplicates(["context_patch_id", "candidate_id", "aerial_year"])
    qa = pd.concat(
        [pd.read_csv(p) for p in sorted(COHORT.glob("*-hls_qa_audit.csv"))],
        ignore_index=True,
    ).drop_duplicates(["candidate_id", "aerial_year", "hls_item_id"])
    for p in list(COHORT.glob("*-all_cover_measurements.csv")) + list(
        COHORT.glob("*-hls_qa_audit.csv")
    ):
        sources[str(p)] = sha(p)
    geometries = {}
    gpkg_paths = [
        ROUND / "photo_reference_annotations.gpkg",
        ROUND / "hls-l30-expanded-references/additional_photo_annotations.gpkg",
        POWER / "review-batch-1/reviewed_photo_cover.gpkg",
        POWER / "review-batch-2/reviewed_photo_cover.gpkg",
    ]
    for p in gpkg_paths:
        sources[str(p)] = sha(p)
        for layer in gpd.list_layers(p).name:
            frame = gpd.read_file(p, layer=layer)
            for key, group in frame.groupby("context_patch_id"):
                geometries[key] = {r.cover: r.geometry for r in group.itertuples()}
    policies = {}
    for p in [
        ROUND / "reviewed_patch_policy.json",
        ROUND / "hls-l30-expanded-references/additional_review_policy.json",
        POWER / "review-batch-1/frozen_review_policy.json",
        POWER / "review-batch-2/frozen_review_policy.json",
    ]:
        sources[str(p)] = sha(p)
        for case in json.loads(p.read_text())["cases"]:
            policies[case["context_patch_id"]] = case
    return obs, covers, qa, geometries, policies, sources


def overlay_cells(ax, frame, anchor, color="white", labels=True):
    for r in frame.itertuples():
        x = r.easting - anchor["easting"]
        y = r.northing - anchor["northing"]
        ax.add_patch(Rectangle((x - 15, y - 15), 30, 30, fill=False, ec=color, lw=0.65))
        if labels:
            ax.text(
                x,
                y,
                str(r.cell_number),
                ha="center",
                va="center",
                fontsize=5.5,
                color="black",
                bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", pad=0.4),
            )


def plate(context, accepted, candidates, image, classes, meta, grid, examples, path):
    fig = plt.figure(figsize=(8, 7.1))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.7, 1], hspace=0.34, wspace=0.36)
    ax = fig.add_subplot(gs[0, :3])
    bx = fig.add_subplot(gs[0, 3:])
    rgb = np.moveaxis(image[:3], 0, -1)
    ax.imshow(rgb, extent=[-120, 120, -120, 120], origin="upper")
    overlay_cells(ax, accepted, meta)
    edge = examples[1][1]
    kernel = source_kernel(edge.easting, edge.northing, meta)
    west, south, east, north = kernel.bounds
    ax.add_patch(
        Rectangle(
            (west - meta["easting"], south - meta["northing"]),
            east - west,
            north - south,
            fill=False,
            ec="#00ddff",
            ls="--",
            lw=1.5,
        )
    )
    ax.set_title("Aerial image: every retained 30 m cell", fontsize=9)
    if grid is None:
        shapes = [
            (g, {"target": 1, "other": 2, "uncertain": 0}[name])
            for name, g in classes.items()
            if not g.is_empty
        ]
        mask = rasterize(
            shapes,
            out_shape=(600, 600),
            transform=from_origin(
                meta["easting"] - 120, meta["northing"] + 120, 0.4, 0.4
            ),
            fill=0,
            dtype="uint8",
        )
        bx.imshow(
            mask,
            extent=[-120, 120, -120, 120],
            origin="upper",
            cmap=ListedColormap(PALETTE),
            vmin=0,
            vmax=2,
            interpolation="nearest",
        )
        bx.set_title("Frozen interpretation: target / other / unknown", fontsize=9)
    else:
        mask = np.where(~np.isfinite(grid), 0, np.where(grid > 5, 1, 2))
        bx.imshow(
            mask,
            extent=[-120, 120, -120, 120],
            origin="lower",
            cmap=ListedColormap(PALETTE),
            vmin=0,
            vmax=2,
            interpolation="nearest",
        )
        bx.set_title("OLDER lidar: >5 m / <=5 m / unknown", fontsize=9)
    overlay_cells(bx, accepted, meta, color="#263e56")
    for a in [ax, bx]:
        a.set_xlim(-120, 120)
        a.set_ylim(-120, 120)
        a.set_xlabel("Metres east of context centre", fontsize=7)
        a.tick_params(labelsize=6)
        a.set_aspect("equal")
        a.plot([-105, -55], [-106, -106], color="white" if a == ax else "black", lw=2)
        a.text(
            -80,
            -101,
            "50 m",
            ha="center",
            fontsize=6,
            color="white" if a == ax else "black",
        )
    ax.set_ylabel("Metres north of centre", fontsize=7)
    for i, (role, row) in enumerate(examples):
        a = fig.add_subplot(gs[1, 2 * i : 2 * i + 2])
        a.imshow(rgb, extent=[-120, 120, -120, 120], origin="upper")
        a.set_facecolor("#dddddd")
        if row is None:
            a.set_title("No rejected cell in reviewed view", fontsize=8)
            a.axis("off")
            continue
        x = row.easting - meta["easting"]
        y = row.northing - meta["northing"]
        a.add_patch(
            Rectangle(
                (x - 15, y - 15),
                30,
                30,
                fill=False,
                ec="#00ddff" if role != "R" else "#ee5577",
                lw=1.7,
            )
        )
        if role == "B":
            dx = float(row.get("shift5_dx", 0))
            dy = float(row.get("shift5_dy", 0))
            a.add_patch(
                Rectangle(
                    (x + dx - 15, y + dy - 15),
                    30,
                    30,
                    fill=False,
                    ec="#ffad33",
                    ls=":",
                    lw=1.3,
                )
            )
        a.set_xlim(x - 40, x + 40)
        a.set_ylim(y - 40, y + 40)
        a.set_aspect("equal")
        a.set_xticks([])
        a.set_yticks([])
        status = (
            "Interior retained"
            if role == "A"
            else "Edge retained"
            if role == "B"
            else "REJECTED for proposed PFT"
        )
        code = f"C{int(row.cell_number):02}" if role != "R" else "R (not retained)"
        a.set_title(f"{role}: {status}\n{code}", fontsize=8)
        a.set_xlabel(
            f"30 m fraction {row.nominal_target_fraction:.3%}\n120 m support {row.source_kernel_target_fraction:.1%}",
            fontsize=7,
        )
    fig.text(
        0.5,
        0.01,
        "Teal = mapped target / tall proxy; tan = other / low proxy; grey = unknown. Dashed cyan = 120 m support for example B.",
        ha="center",
        fontsize=6.9,
    )
    fig.savefig(
        path, dpi=180, pil_kwargs={"quality": 91, "optimize": True}, bbox_inches="tight"
    )
    plt.close(fig)


def run():
    obs, covers, qa, geometries, policies, sources = load_sources()
    all_records = []
    contexts = []
    checks = []
    order = {c: i for i, c in enumerate(CATEGORIES)}
    keys = sorted(
        obs.context_patch_id.unique(),
        key=lambda k: (
            order[obs[obs.context_patch_id == k].researcher_category.iloc[0]],
            k,
        ),
    )
    for n, key in enumerate(keys, 1):
        accepted = (
            obs[obs.context_patch_id == key]
            .sort_values(["northing", "easting"], ascending=[False, True])
            .copy()
            .reset_index(drop=True)
        )
        accepted["cell_number"] = np.arange(1, len(accepted) + 1)
        accepted["review_id"] = [f"P{n:02}-C{i:02}" for i in accepted.cell_number]
        root = next(p for p in CACHE_DIRS if (p / (key + ".npy")).exists())
        imgpath = root / (key + ".npy")
        metapath = root / (key + ".json")
        meta = json.loads(metapath.read_text())
        image = np.load(imgpath)
        digest = sha(imgpath)
        assert accepted.image_sha256.eq(digest).all() and meta["image_sha256"] == digest
        sources[str(imgpath)] = digest
        sources[str(metapath)] = sha(metapath)
        group = covers[covers.context_patch_id == key].copy()
        group["nominal_95pct"] = group.nominal_95pct.map(bool_value)
        grid = None
        grid_meta = None
        classes = geometries.get(key, {})
        if accepted.reference_basis.str.contains("lidar").any():
            project = accepted.structural_project.iloc[0]
            candidates = [
                p / (f"{key}-{project}.npy")
                for p in [ROUND / "evergreen-pointcloud", POWER / "pointcloud-cascades"]
            ]
            gridpath = next(p for p in candidates if p.exists())
            grid = np.load(gridpath)
            grid_meta = json.loads(gridpath.with_suffix(".json").read_text())
            assert sha(gridpath) == grid_meta["array_sha256"]
            sources[str(gridpath)] = sha(gridpath)
            sources[str(gridpath.with_suffix(".json"))] = sha(
                gridpath.with_suffix(".json")
            )
        for row in accepted.itertuples():
            cell = box(
                row.easting - 15, row.northing - 15, row.easting + 15, row.northing + 15
            )
            kernel = source_kernel(row.easting, row.northing, meta)
            if grid is None:
                fraction = photo_fraction(classes["target"], cell)
                support = photo_fraction(classes["target"], kernel)
            else:
                fraction, _ = structural_fraction(grid, cell, meta)
                support, _ = structural_fraction(grid, kernel, meta)
            assert (
                abs(fraction - row.nominal_target_fraction) < 1e-8
                and abs(support - row.source_kernel_target_fraction) < 1e-8
            )
            assert row.nominal_target_fraction >= 0.95 - 1e-12
            for distance in (3, 5):
                trials = []
                for dx, dy in product((-distance, 0, distance), repeat=2):
                    shifted = box(
                        row.easting + dx - 15,
                        row.northing + dy - 15,
                        row.easting + dx + 15,
                        row.northing + dy + 15,
                    )
                    value = (
                        photo_fraction(classes["target"], shifted)
                        if grid is None
                        else structural_fraction(grid, shifted, meta)[0]
                    )
                    trials.append((value, dx, dy))
                lowest, dx, dy = min(trials)
                accepted.loc[
                    accepted.candidate_id == row.candidate_id,
                    f"shift{distance}_min_fraction",
                ] = lowest
                accepted.loc[
                    accepted.candidate_id == row.candidate_id, f"shift{distance}_dx"
                ] = dx
                accepted.loc[
                    accepted.candidate_id == row.candidate_id, f"shift{distance}_dy"
                ] = dy
            checks.append(
                dict(
                    review_id=row.review_id,
                    fraction_recalculation="PASS",
                    support_recalculation="PASS",
                )
            )
        examples = choose_examples(accepted, group)
        target = accepted.researcher_category.iloc[0]
        case = policies.get(key, {})
        note = case.get(
            "interpretation",
            case.get(
                "notes",
                "Reviewed forest context plus older tall-canopy proxy; current evergreen identity remains provisional.",
            ),
        )
        example_records = []
        for role, row in examples:
            if row is None:
                continue
            example_records.append(
                dict(
                    role=role,
                    candidate_id=row.candidate_id,
                    review_id=row.get("review_id", "R"),
                    easting=float(row.easting),
                    northing=float(row.northing),
                    nominal=float(row.nominal_target_fraction),
                    support=float(row.source_kernel_target_fraction),
                    retained=role != "R",
                )
            )
        platepath = REPORT / "plates" / f"P{n:02}-{key}.jpg"
        signature = dict(
            image=digest,
            metadata=sha(metapath),
            cohort=sha(COHORT / "hls_l30_nominal_95pct_observations.csv"),
            code=sha(Path(__file__)),
        )
        savedpath = platepath.with_suffix(".json")
        if not (
            savedpath.exists()
            and json.loads(savedpath.read_text()).get("identity") == signature
            and platepath.exists()
            and json.loads(savedpath.read_text()).get("sha256") == sha(platepath)
        ):
            plate(n, accepted, group, image, classes, meta, grid, examples, platepath)
            savedpath.write_text(
                json.dumps(dict(identity=signature, sha256=sha(platepath)), indent=2)
                + "\n"
            )
        context = dict(
            number=n,
            id=f"P{n:02}",
            context_patch_id=key,
            target=target,
            region=accepted.region.iloc[0],
            count=len(accepted),
            strict_count=int(accepted.strict_support_95pct.sum()),
            plate=str(platepath.relative_to(ROOT)),
            plate_sha256=sha(platepath),
            meta=meta,
            interpretation=note,
            policy=case,
            examples=example_records,
            structural=grid is not None,
            structural_metadata=grid_meta,
            nominal_min=float(accepted.nominal_target_fraction.min()),
            shift3_min=float(accepted.shift3_min_fraction.min()),
            shift5_min=float(accepted.shift5_min_fraction.min()),
            support_min=float(accepted.source_kernel_target_fraction.min()),
            support_max=float(accepted.source_kernel_target_fraction.max()),
            photo_date=accepted.aerial_datetime.iloc[0],
            hls_dates=sorted(accepted.acquisition_datetime.unique()),
            hls_items=sorted(accepted.hls_item_id.unique()),
            aerial_gap_max=int(accepted.aerial_gap_days.max()),
            minimum_season_offset=int(accepted.season_offset_days.min()),
            maximum_season_offset=int(accepted.season_offset_days.max()),
        )
        contexts.append(context)
        accepted["atlas_plate_page"] = 5 + 2 * (n - 1)
        accepted["atlas_ledger_page"] = 6 + 2 * (n - 1)
        for field in [
            "reviewer",
            "team_decision",
            "revised_pft",
            "confidence",
            "issue_tags",
            "review_notes",
        ]:
            accepted[field] = ""
        all_records.append(accepted)
        print(
            f"{n}/61 {key}: {len(accepted)} individual fractions and support areas independently reproduced",
            flush=True,
        )
    ledger = pd.concat(all_records, ignore_index=True)
    ledger = preserve_team_reviews(ledger, REPORT / "team_pixel_review.csv")
    ledger.to_csv(REPORT / "team_pixel_review.csv", index=False)
    pd.DataFrame(checks).to_csv(REPORT / "geometry_verification.csv", index=False)
    # Select two contrasting accepted contexts per class using geometry only.
    chosen = []
    for category in CATEGORIES:
        eligible = [c for c in contexts if c["target"] == category]
        easy = max(
            eligible,
            key=lambda c: (
                c["strict_count"] / c["count"],
                c["nominal_min"],
                c["count"],
            ),
        )
        edge = min(
            [c for c in eligible if c["id"] != easy["id"]],
            key=lambda c: (c["support_min"], c["nominal_min"]),
        )
        chosen.extend(
            [
                dict(context=easy["id"], role="Interior / stronger support"),
                dict(context=edge["id"], role="Boundary / weaker source support"),
            ]
        )
    qa_current = qa[qa.candidate_id.isin(obs.candidate_id)].copy()
    qa_current.to_csv(REPORT / "candidate_date_qa_review.csv", index=False)
    qa_examples = []
    for field in ["photo_date_match", "core_qa_clear", "context_150m_clear"]:
        rows = qa_current[~qa_current[field].map(bool_value)]
        if len(rows):
            qa_examples.append(dict(reason=field, **rows.iloc[0].to_dict()))
    # Compact source-only manifests and lookups; no source data is rewritten.
    manifest = dict(
        date="2026-11-19",
        cohort_count=len(obs),
        context_count=len(contexts),
        strict_count=int(obs.strict_support_95pct.sum()),
        pft_counts=obs.groupby("researcher_category").size().to_dict(),
        region_counts=obs.groupby(["region", "researcher_category"])
        .size()
        .reset_index(name="cells")
        .to_dict("records"),
        contexts=contexts,
        guide_examples=chosen,
        qa_examples=qa_examples,
        sources=sources,
        code_sha256=sha(Path(__file__)),
        selection_rule="Two contexts per PFT selected by mapped/structural cover and source support only; A=max support interior, B=weakest retained nominal cover, R=closest rejected nominal cover within same context; no spectra or statistical accuracy used",
        status="All labels provisional; no independent second-interpreter or field verification",
    )
    (REPORT / "review_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n"
    )
    print("Complete review ledger and61 visual plates:", REPORT, flush=True)


if __name__ == "__main__":
    run()
