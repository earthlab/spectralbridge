"""Independent seven-band NEON-to-real-Landsat validation, one flight at a time.

Extends existing Landsat transport/identity/scaling helpers. No calibration is fit.
"""

from dataclasses import dataclass, asdict
from datetime import timedelta
from pathlib import Path
import json
import logging

import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt

from . import landsat_validation as legacy
from .landsat_agreement import (
    ReferenceGrid,
    OLI_CHANNELS,
    OLI_CENTERS,
    mask_landsat_qa,
    scale_landsat_sr,
    aggregate_to_landsat_grid,
    compute_agreement_metrics,
    spatial_bootstrap_indices,
    spectral_angle,
)
from .bulk.provenance import signature_sha256, write_json_atomic
from .plant_spectral_atlas import _file_hash

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class FlightValidationInput:
    """Specify existing raw/adjusted synthetic products and an actual Landsat comparison source for one flight."""

    flight_id: str
    site: str
    acquisition_datetime: str
    corrected_raster: str
    undarkened_raster: str
    adjusted_raster: str
    synthetic_scale_factor: float
    time_provenance: str
    source_h5: str | None = None
    timezone_verified: bool = False


@dataclass(frozen=True)
class FlightValidationConfig:
    """Configure explicit support, acquisition-time, screening and rendering settings for flight validation."""

    search_days: int = 16
    minimum_valid_coverage: float = 0.90
    minimum_pixels: int = 100
    bootstraps: int = 499
    spatial_block_pixels: int = 10
    seed: int = 20261014
    rgb_max: float = 0.4

    def validate(self):
        if (
            self.search_days < 0
            or not 0 < self.minimum_valid_coverage <= 1
            or self.minimum_pixels < 3
            or self.bootstraps < 19
            or self.spatial_block_pixels < 1
            or self.rgb_max <= 0
        ):
            raise ValueError("Invalid flight validation settings")


def candidate_records(items, neon_datetime):
    """All searched scenes; compatibility and collection are explicit gates."""
    acquired = legacy._parse_datetime(neon_datetime)
    if acquired is None:
        raise ValueError("Invalid NEON datetime")
    rows = []
    for item in items:
        p = item.properties
        t = legacy._parse_datetime(p.get("datetime"))
        sensor = legacy._item_sensor(item)
        assets = {legacy._asset_common_name(k, a): a for k, a in item.assets.items()}
        missing = [
            k for k in [*OLI_CHANNELS, "qa_pixel", "qa_radsat"] if k not in assets
        ]
        collection = getattr(item, "collection_id", None)
        level = p.get("landsat:processing_level", p.get("landsat:correction", ""))
        compatible = sensor in {"Landsat_8_OLI", "Landsat_9_OLI-2"}
        reason = "pending_QA"
        if collection != legacy.LANDSAT_COLLECTION or level not in ["L2SP", "L2SR"]:
            reason = "wrong_collection_or_processing_level"
        elif not compatible:
            reason = "incompatible_sensor_for_seven_band_OLI"
        elif missing:
            reason = "missing_required_assets:" + ",".join(missing)
        elif t is None:
            reason = "missing_scene_datetime"
        delta = (t - acquired).total_seconds() / 3600 if t else np.nan
        row = dict(
            item_id=item.id,
            product_id=p.get(
                "landsat:product_id",
                Path(assets["red"].href.split("?")[0]).name.split("_SR_B")[0]
                if "red" in assets
                else item.id,
            ),
            platform=p.get("platform"),
            sensor=sensor,
            acquisition_datetime=t.isoformat() if t else None,
            processing_level=level,
            collection=collection,
            collection_number=p.get("landsat:collection_number"),
            cloud_cover=p.get("eo:cloud_cover"),
            sun_elevation=p.get("view:sun_elevation"),
            sun_azimuth=p.get("view:sun_azimuth"),
            spatial_footprint=json.dumps(getattr(item, "geometry", None)),
            delta_time_hours=delta,
            absolute_delta_hours=abs(delta),
            sensor_rank=0 if sensor == "Landsat_8_OLI" else 1,
            quality=p.get("landsat:collection_category", str(item.id).split("_")[-1]),
            status=reason,
            same_calendar_day=bool(t and t.date() == acquired.date()),
        )
        for days in [1, 3, 7, 16]:
            row[f"within_{days}_days"] = bool(t and abs(delta) <= days * 24)
        rows.append(row)
    return pd.DataFrame(rows)


def rank_scene_candidates(table, minimum_pixels=100):
    """Temporal -> clear overlap -> compatibility -> coverage -> quality; never error."""
    if table.empty or "usable_pixels" not in table:
        return table.iloc[:0].copy()
    eligible = table[
        table.status.eq("QA_evaluated") & (table.usable_pixels >= minimum_pixels)
    ].copy()
    return eligible.sort_values(
        [
            "absolute_delta_hours",
            "clear_overlap_fraction",
            "sensor_rank",
            "spatial_coverage_fraction",
            "quality",
            "cloud_cover",
            "item_id",
        ],
        ascending=[True, False, True, False, True, True, True],
        na_position="last",
    )


def _assets(item):
    return {legacy._asset_common_name(k, a): a for k, a in item.assets.items()}


def load_scene_qa(item, bounds_wgs84, cache):
    """Windowed Collection 2 QA with a 600-m halo for conservative proximity."""
    import planetary_computer
    import rasterio
    from rasterio.windows import from_bounds, Window
    from rasterio.warp import transform_bounds

    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    identity = dict(
        item=item.to_dict(transform_hrefs=False),
        bounds=list(bounds_wgs84),
        halo_pixels=20,
        schema=1,
    )
    signature = signature_sha256(identity)
    ledger = cache / "qa_manifest.json"
    arrayfile = cache / "qa.npz"
    if ledger.is_file() and arrayfile.is_file():
        saved = json.loads(ledger.read_text())
        if saved["signature"] == signature and saved["sha256"] == _file_hash(arrayfile):
            with np.load(arrayfile) as f:
                arrays = {k: f[k] for k in f.files}
            return arrays, ReferenceGrid(**saved["grid"])
    signed = planetary_computer.sign(item)
    assets = _assets(signed)
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
    ):
        with rasterio.open(assets["coastal"].href) as src:
            b = transform_bounds("EPSG:4326", src.crs, *bounds_wgs84, densify_pts=21)
            w = from_bounds(*b, src.transform)
            c0 = max(0, int(np.floor(w.col_off)))
            r0 = max(0, int(np.floor(w.row_off)))
            c1 = min(src.width, int(np.ceil(w.col_off + w.width)))
            r1 = min(src.height, int(np.ceil(w.row_off + w.height)))
            if c1 <= c0 or r1 <= r0:
                raise ValueError("No raster overlap")
            core = Window(c0, r0, c1 - c0, r1 - r0)
            halo = Window(
                max(0, c0 - 20),
                max(0, r0 - 20),
                min(src.width, c1 + 20) - max(0, c0 - 20),
                min(src.height, r1 + 20) - max(0, r0 - 20),
            )
            grid = ReferenceGrid(
                str(src.crs),
                tuple(src.window_transform(core))[:6],
                int(core.width),
                int(core.height),
                r0,
                c0,
            )
            reference = (src.crs, src.transform, src.width, src.height)
        arrays = {}
        for key in ["qa_pixel", "qa_radsat"]:
            with rasterio.open(assets[key].href) as src:
                if (src.crs, src.transform, src.width, src.height) != reference:
                    raise ValueError(
                        "Landsat QA assets do not share the SR reference grid"
                    )
                arrays[key] = src.read(1, window=core)
                if key == "qa_pixel":
                    halo_qa = src.read(1, window=halo)
                    bad = (halo_qa & np.uint16(2 | 4 | 8 | 16)) != 0
                    distance = distance_transform_edt(
                        np.pad(~bad, 1, constant_values=False)
                    )[1:-1, 1:-1] * abs(grid.affine.a)
                    rr = int(core.row_off - halo.row_off)
                    cc = int(core.col_off - halo.col_off)
                    arrays["cloud_distance_lower_bound_m"] = distance[
                        rr : rr + grid.height, cc : cc + grid.width
                    ]
    np.savez_compressed(arrayfile, **arrays)
    write_json_atomic(
        ledger,
        dict(
            signature=signature,
            sha256=_file_hash(arrayfile),
            grid=asdict(grid),
            item_id=item.id,
        ),
    )
    return arrays, grid


def load_scene_surface_reflectance(item, grid, qa, cache):
    """Read seven real SR assets on their native Landsat window; no TOA route."""
    import planetary_computer
    import rasterio
    from rasterio.windows import Window

    cache = Path(cache)
    output = cache / "actual_surface_reflectance.tif"
    ledger = cache / "sr_manifest.json"
    identity = signature_sha256(
        dict(
            item=item.to_dict(transform_hrefs=False),
            grid=asdict(grid),
            qa=_file_hash(cache / "qa.npz"),
            schema=1,
        )
    )
    if output.exists() and ledger.exists():
        saved = json.loads(ledger.read_text())
        if saved["signature"] == identity and saved["sha256"] == _file_hash(output):
            with rasterio.open(output) as src:
                return src.read().astype(float), output
    arrays = []
    assets = _assets(planetary_computer.sign(item))
    valid, _ = mask_landsat_qa(qa["qa_pixel"], qa["qa_radsat"])
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
    ):
        for name in OLI_CHANNELS:
            asset = assets[name]
            scale, offset, _ = legacy._asset_scale_offset(asset)
            if not np.isclose(
                scale, legacy.LANDSAT_SURFACE_REFLECTANCE_SCALE, rtol=0, atol=1e-12
            ) or not np.isclose(offset, legacy.LANDSAT_SURFACE_REFLECTANCE_OFFSET):
                raise ValueError("Unexpected Collection 2 SR asset scale/offset")
            with rasterio.open(asset.href) as src:
                win = Window(grid.col_offset, grid.row_offset, grid.width, grid.height)
                if src.crs.to_string() != grid.crs or not np.allclose(
                    tuple(src.window_transform(win))[:6], grid.transform
                ):
                    raise ValueError("SR asset grid mismatch")
                dn = src.read(1, window=win)
            arrays.append(np.where(valid, scale_landsat_sr(dn), np.nan))
    # The cached float32 crop is the canonical observation on every run.
    values = np.stack(arrays).astype(np.float32).astype(float)
    with rasterio.open(
        output,
        "w",
        driver="GTiff",
        width=grid.width,
        height=grid.height,
        count=7,
        dtype="float32",
        crs=grid.crs,
        transform=grid.affine,
        nodata=np.nan,
        compress="deflate",
    ) as dst:
        dst.write(values.astype("float32"))
        dst.update_tags(
            product_id=item.properties.get("landsat:product_id", item.id),
            stac_item_id=item.id,
            product_semantics="actual_landsat_collection_2_level_2_surface_reflectance",
            reflectance_units="unitless",
            source_scale=str(legacy.LANDSAT_SURFACE_REFLECTANCE_SCALE),
            source_offset=str(legacy.LANDSAT_SURFACE_REFLECTANCE_OFFSET),
        )
        for i, name in enumerate(OLI_CHANNELS, 1):
            dst.set_band_description(i, name)
    write_json_atomic(
        ledger,
        dict(
            signature=identity,
            sha256=_file_hash(output),
            scaling="DN * 0.0000275 - 0.2",
            qa="QA_PIXEL bits0-5; QA_RADSAT B1-B7 and terrain",
            item=item.to_dict(transform_hrefs=False),
        ),
    )
    return values, output


def _validate_sources(flight):
    import rasterio

    if legacy._parse_datetime(flight.acquisition_datetime) is None or not any(
        v in flight.acquisition_datetime[10:] for v in ["Z", "+", "-"]
    ):
        raise ValueError("Explicit acquisition timezone/basis required")
    if not Path(flight.corrected_raster).is_file():
        raise FileNotFoundError("Corrected NEON raster is required")
    fingerprints = {}
    for name, path in [
        ("undarkened", flight.undarkened_raster),
        ("adjusted", flight.adjusted_raster),
    ]:
        with rasterio.open(path) as src:
            text = src.tags(ns="ENVI").get("wavelength", "")
            try:
                w = np.array([float(v.strip()) for v in text.strip("{} ").split(",")])
            except ValueError as exc:
                raise ValueError(
                    "Numeric physical OLI wavelength metadata required"
                ) from exc
            if (
                src.count != 7
                or len(w) != 7
                or not np.allclose(w, OLI_CENTERS, atol=0.51, rtol=0)
            ):
                raise ValueError(
                    "Synthetic OLI band metadata do not match seven declared channels"
                )
        fingerprints[name] = _file_hash(path)
        header = Path(path).with_suffix(".hdr")
        if header.exists():
            fingerprints[name + "_header"] = _file_hash(header)
    header = Path(flight.corrected_raster).with_suffix(".hdr")
    if header.exists():
        fingerprints["corrected_header"] = _file_hash(header)
    return fingerprints


def _interval_metrics(x, values, draws):
    rows = []
    paired = []
    keys = ["mean_bias", "MAE", "RMSE", "deming_slope", "deming_intercept", "Pearson_r"]
    for variant, y in values.items():
        boot = []
        for ix in draws:
            per = []
            for band in range(7):
                m = compute_agreement_metrics(x[ix, band], y[ix, band])
                per.append([m.get(k, np.nan) for k in keys])
            boot.append(per)
        boot = np.array(boot)
        for band, name in enumerate(OLI_CHANNELS):
            m = compute_agreement_metrics(x[:, band], y[:, band])
            m.update(variant=variant, band=name)
            for j, key in enumerate(keys):
                if len(draws):
                    m[key + "_lo"], m[key + "_hi"] = map(
                        float, np.nanquantile(boot[:, band, j], [0.025, 0.975])
                    )
            rows.append(m)
        paired.append((variant, boot))
    return rows, dict(paired), keys


def compare_flight_to_real_landsat(
    flight, output, *, config=None, items=None, client=None
) -> dict:
    """Select one real scene and compare it with a verified seven-band flight.

    Args:
        flight (FlightValidationInput): Source paths, identity, acquisition time
            and explicit scale/time provenance. Synthetic bands must be ordered
            coastal/blue/green/red/NIR/SWIR1/SWIR2.
        output (str or pathlib.Path): Checkpoint/result directory.
        config (FlightValidationConfig, optional): Search, coverage and bootstrap
            settings; defaults include 0.9 whole-footprint valid coverage.
        items (sequence, optional): Supplied STAC items; None enables discovery.
        client (object, optional): STAC client for discovery.

    Returns:
        dict: Status/identity/checksummed output manifest. Explicit no-scene and
            unusable-scene statuses are retained, not fabricated successful fits.
            Results contain matched arrays, tables, QA and figures in output.

    Raises:
        ValueError: Source coordinates/scales, metadata or configuration invalid.
        OSError: Source/cache/output IO fails. Network/library errors propagate
            when discovery/download is requested; use optional landsat extra.

    Inputs are read in place. Complete valid outputs are reused. Uses actual
    footprint area, QA_PIXEL/RADSAT, official C2 SR scaling, seven-band joint
    support and spatial-block uncertainty. One flight is not cross-site evidence.
    """
    config = config or FlightValidationConfig()
    config.validate()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    inputs = _validate_sources(flight)
    identity = dict(
        flight=asdict(flight),
        config=asdict(config),
        inputs=inputs,
        code=_file_hash(__file__),
        agreement_code=_file_hash(Path(__file__).with_name("landsat_agreement.py")),
        legacy_code=_file_hash(Path(__file__).with_name("landsat_validation.py")),
        report_code=_file_hash(Path(__file__).with_name("landsat_flight_report.py")),
    )
    manifest_path = root / "statistics_manifest.json"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text())
        if m["identity"] == identity and all(
            (root / n).is_file() and _file_hash(root / n) == h
            for n, h in m["outputs"].items()
        ):
            return m
    bounds = legacy.raster_bounds_wgs84(flight.undarkened_raster)
    acquired = legacy._parse_datetime(flight.acquisition_datetime)
    if items is None:
        import pystac_client

        client = client or pystac_client.Client.open(legacy.PLANETARY_COMPUTER_STAC)
        start = acquired.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=config.search_days
        )
        stop = start + timedelta(days=2 * config.search_days + 1)
        items = list(
            client.search(
                collections=[legacy.LANDSAT_COLLECTION],
                bbox=bounds,
                datetime=f"{start.isoformat()}/{stop.isoformat()}",
            ).items()
        )
    items = list(items)
    lookup = {i.id: i for i in items}
    write_json_atomic(
        root / "search_items.json",
        dict(
            type="FeatureCollection",
            features=[i.to_dict(transform_hrefs=False) for i in items],
            bounds_wgs84=bounds,
            search_days=config.search_days,
        ),
    )
    table = candidate_records(items, flight.acquisition_datetime)
    if table.empty:
        pd.DataFrame(columns=["item_id", "status"]).to_csv(
            root / "scene_candidates.csv", index=False
        )
        pd.DataFrame(columns=["item_id", "selected", "reason"]).to_csv(
            root / "scene_selection.csv", index=False
        )
        write_json_atomic(
            root / "status.json",
            dict(status="no_scene", reason="No STAC candidates in declared window"),
        )
        return dict(status="no_scene")
    products = {
        "undarkened": flight.undarkened_raster,
        "adjusted": flight.adjusted_raster,
    }
    scales = {k: flight.synthetic_scale_factor for k in products}
    evaluated = {}
    for i, row in table.iterrows():
        if row.status != "pending_QA":
            continue
        LOG.info("Candidate QA: %s", row.item_id)
        try:
            qa, grid = load_scene_qa(
                lookup[row.item_id], bounds, root / "cache" / row.item_id
            )
            aggregation = aggregate_to_landsat_grid(
                products, grid, scale_factors=scales
            )
            good = (
                aggregation["valid_coverage_fraction"] >= config.minimum_valid_coverage
            )
            qavalid, _ = mask_landsat_qa(qa["qa_pixel"], qa["qa_radsat"])
            usable = good & qavalid
            table.loc[i, "usable_pixels"] = int(usable.sum())
            table.loc[i, "clear_overlap_fraction"] = float(
                usable.sum() / max(1, good.sum())
            )
            table.loc[i, "spatial_coverage_fraction"] = float(
                np.mean(aggregation["coverage_fraction"])
            )
            table.loc[i, "status"] = (
                "QA_evaluated"
                if usable.sum() >= config.minimum_pixels
                else "insufficient_QA_overlap"
            )
            evaluated[row.item_id] = (qa, grid, aggregation)
        except (OSError, ValueError, RuntimeError) as exc:
            # Avoid leaking ephemeral signed asset query strings in provenance.
            table.loc[i, "status"] = "QA_failed:" + type(exc).__name__
    ranked = rank_scene_candidates(table, config.minimum_pixels)
    table.to_csv(root / "scene_candidates.csv", index=False)
    selection = table[["item_id", "product_id", "status"]].copy()
    selection["selected"] = False
    if ranked.empty:
        selection["reason"] = (
            "No candidate met the declared sensor/level/QA/coverage criteria"
        )
        selection.to_csv(root / "scene_selection.csv", index=False)
        write_json_atomic(root / "status.json", dict(status="no_eligible_scene"))
        return dict(status="no_eligible_scene")
    selected = ranked.iloc[0]
    selection.loc[selection.item_id.eq(selected.item_id), "selected"] = True
    selection["reason"] = np.where(
        selection.selected,
        "First eligible by time, clear overlap, sensor match, coverage and quality; never reflectance agreement",
        "Not selected; see status and declared ranking",
    )
    selection.to_csv(root / "scene_selection.csv", index=False)
    item = lookup[selected.item_id]
    qa, grid, aggregation = evaluated[selected.item_id]
    actual, actual_path = load_scene_surface_reflectance(
        item, grid, qa, root / "cache" / selected.item_id
    )
    qavalid, category = mask_landsat_qa(qa["qa_pixel"], qa["qa_radsat"])
    common = (
        qavalid
        & np.isfinite(actual).all(0)
        & (aggregation["valid_coverage_fraction"] >= config.minimum_valid_coverage)
    )
    for v in aggregation["means"].values():
        common &= np.isfinite(v).all(0)
    if common.sum() < config.minimum_pixels:
        raise ValueError(
            "Too little common reflectance support after SR nodata masking"
        )
    rr, cc = np.nonzero(common)
    x = actual[:, rr, cc].T
    values = {k: v[:, rr, cc].T for k, v in aggregation["means"].items()}
    heterogeneity = np.sqrt(
        np.mean(aggregation["variances"]["undarkened"][:, rr, cc], axis=0)
    )
    xx, yy = grid.affine * (cc + 0.5, rr + 0.5)
    pixels = pd.DataFrame(
        dict(
            flight_id=flight.flight_id,
            site=flight.site,
            neon_datetime=flight.acquisition_datetime,
            landsat_datetime=selected.acquisition_datetime,
            delta_time_hours=selected.delta_time_hours,
            landsat_product_id=selected.product_id,
            landsat_item_id=selected.item_id,
            row=rr + grid.row_offset,
            col=cc + grid.col_offset,
            x=xx,
            y=yy,
            crs=grid.crs,
            coverage_fraction=aggregation["coverage_fraction"][rr, cc],
            valid_fraction=aggregation["valid_fraction"][rr, cc],
            valid_coverage_fraction=aggregation["valid_coverage_fraction"][rr, cc],
            neon_contributing_pixels=aggregation["contributing_pixels"][rr, cc],
            heterogeneity=heterogeneity,
            cloud_distance_lower_bound_m=qa["cloud_distance_lower_bound_m"][rr, cc],
            water=(qa["qa_pixel"][rr, cc] & (1 << 7)) != 0,
        )
    )
    for band, name in enumerate(OLI_CHANNELS):
        pixels["real_" + name] = x[:, band]
        for variant, y in values.items():
            pixels[variant + "_" + name] = y[:, band]
            pixels[variant + "_residual_" + name] = y[:, band] - x[:, band]
    for variant, y in values.items():
        pixels[variant + "_spectral_angle_deg"] = spectral_angle(x, y)
        pixels[variant + "_multiband_RMSE"] = np.sqrt(np.mean((y - x) ** 2, axis=1))
    pixels.to_parquet(root / "pixel_metrics.parquet", index=False)
    draws, nblocks = spatial_bootstrap_indices(
        pixels.row,
        pixels.col,
        config.bootstraps,
        config.spatial_block_pixels,
        config.seed,
    )
    metrics, boot, keys = _interval_metrics(x, values, draws)
    metrics = pd.DataFrame(metrics)
    metrics["flight_id"] = flight.flight_id
    metrics["site"] = flight.site
    metrics["delta_time_hours"] = selected.delta_time_hours
    metrics["spatial_blocks"] = nblocks
    metrics.to_csv(root / "band_metrics.csv", index=False)
    paired = []
    for i, name in enumerate(OLI_CHANNELS):
        for key in ["mean_bias", "MAE", "RMSE", "deming_slope", "deming_intercept"]:
            j = keys.index(key)
            delta = boot["adjusted"][:, i, j] - boot["undarkened"][:, i, j]
            a = metrics[(metrics.variant == "adjusted") & (metrics.band == name)].iloc[
                0
            ][key]
            u = metrics[
                (metrics.variant == "undarkened") & (metrics.band == name)
            ].iloc[0][key]
            lo, hi = np.nanquantile(delta, [0.025, 0.975])
            paired.append(
                dict(
                    band=name, metric=key, adjusted_minus_undarkened=a - u, lo=lo, hi=hi
                )
            )
    for metric in ["pooled_seven_band_RMSE", "median_spectral_angle_deg"]:
        if metric == "pooled_seven_band_RMSE":
            j = keys.index("RMSE")
            distributions = {
                v: np.sqrt(np.mean(boot[v][:, :, j] ** 2, axis=1)) for v in values
            }
            point = {
                v: float(np.sqrt(np.mean((y - x) ** 2))) for v, y in values.items()
            }
        else:
            sam = {v: spectral_angle(x, y) for v, y in values.items()}
            distributions = {
                v: np.array([np.nanmedian(a[ix]) for ix in draws])
                for v, a in sam.items()
            }
            point = {v: float(np.nanmedian(a)) for v, a in sam.items()}
        delta = distributions["adjusted"] - distributions["undarkened"]
        lo, hi = np.nanquantile(delta, [0.025, 0.975])
        paired.append(
            dict(
                band="seven_band",
                metric=metric,
                adjusted_minus_undarkened=point["adjusted"] - point["undarkened"],
                lo=lo,
                hi=hi,
            )
        )
    pd.DataFrame(paired).to_csv(root / "brightness_comparison.csv", index=False)
    low, high = np.quantile(heterogeneity, [1 / 3, 2 / 3])
    masks = {
        "all_eligible": np.ones(len(pixels), bool),
        "homogeneous_tertile": heterogeneity <= low,
        "heterogeneous_tertile": heterogeneity >= high,
        "coverage_99pct": pixels.valid_coverage_fraction.to_numpy() >= 0.99,
        "cloud_distance_90m": pixels.cloud_distance_lower_bound_m.to_numpy() >= 90,
        "same_day_gold": np.repeat(bool(selected.same_calendar_day), len(pixels))
        & (pixels.cloud_distance_lower_bound_m.to_numpy() >= 90),
    }
    subsets = []
    for subset, mask in masks.items():
        for variant, y in values.items():
            for band, name in enumerate(OLI_CHANNELS):
                subsets.append(
                    dict(
                        subset=subset,
                        variant=variant,
                        band=name,
                        **compute_agreement_metrics(x[mask, band], y[mask, band]),
                    )
                )
    pd.DataFrame(subsets).to_csv(root / "subset_metrics.csv", index=False)
    flightrows = []
    for variant in values:
        sam = pixels[variant + "_spectral_angle_deg"]
        rms = pixels[variant + "_multiband_RMSE"]
        flightrows.append(
            dict(
                flight_id=flight.flight_id,
                site=flight.site,
                landsat_product_id=selected.product_id,
                neon_datetime=flight.acquisition_datetime,
                landsat_datetime=selected.acquisition_datetime,
                delta_time_hours=selected.delta_time_hours,
                N=len(pixels),
                variant=variant,
                median_spectral_angle_deg=float(sam.median()),
                mean_multiband_RMSE=float(rms.mean()),
                pooled_seven_band_RMSE=float(
                    np.sqrt(np.mean((values[variant] - x) ** 2))
                ),
                median_multiband_RMSE=float(rms.median()),
                same_day_gold_N=int(masks["same_day_gold"].sum()),
                spatial_blocks=nblocks,
            )
        )
    pd.DataFrame(flightrows).to_csv(root / "flight_metrics.csv", index=False)
    _registration(products, scales, grid, qavalid, actual, root, config)
    _decomposition(pixels, root)
    arrays = dict(
        actual=actual,
        qa_category=category,
        qa_valid=qavalid,
        common=common,
        coverage=aggregation["valid_coverage_fraction"],
        cloud_distance=qa["cloud_distance_lower_bound_m"],
        **{k: v for k, v in aggregation["means"].items()},
    )
    np.savez_compressed(root / "matched_grid.npz", **arrays)
    write_json_atomic(root / "grid.json", asdict(grid))
    write_json_atomic(
        root / "status.json",
        dict(
            status="complete_single_flight",
            flight=asdict(flight),
            config=asdict(config),
            selected_scene=selected.to_dict(),
            N=len(pixels),
            spatial_blocks=nblocks,
            aggregation_method=aggregation["method"],
            actual_raster=str(actual_path),
            brightness_training_provenance="Packaged description identifies NEON-to-synthetic-sensor differences, not an empirical Landsat fit; calibration scene IDs unavailable; no coefficients refit here",
            evidence_level="Independent real observation, one flight; no cross-flight/site or held-out calibration claim",
        ),
    )
    from .landsat_flight_report import build_flight_validation_figures

    build_flight_validation_figures(root, config.rgb_max)
    summarize_flight_validations([root], root / "across_flight_metrics.csv")
    outputs = {
        str(p.relative_to(root)): _file_hash(p)
        for p in root.rglob("*")
        if p.is_file() and p != manifest_path
    }
    result = dict(status="complete_single_flight", identity=identity, outputs=outputs)
    write_json_atomic(manifest_path, result)
    return result


def _registration(products, scales, grid, qavalid, actual, root, config):
    aggregates = {}
    for dy in [-30.0, 0.0, 30.0]:
        for dx in [-30.0, 0.0, 30.0]:
            LOG.info(
                "Registration sensitivity: source dx=%sm, dy=%sm; no shift applied to primary",
                dx,
                dy,
            )
            aggregates[(dx, dy)] = aggregate_to_landsat_grid(
                products, grid, scale_factors=scales, offset_m=(dx, dy)
            )
    common = qavalid & np.isfinite(actual).all(0)
    for agg in aggregates.values():
        common &= agg["valid_coverage_fraction"] >= config.minimum_valid_coverage
    rows = []
    for (dx, dy), agg in aggregates.items():
        for variant, y in agg["means"].items():
            for i, band in enumerate(OLI_CHANNELS):
                rows.append(
                    dict(
                        dx_m=dx,
                        dy_m=dy,
                        variant=variant,
                        band=band,
                        primary_alignment=dx == 0 and dy == 0,
                        **compute_agreement_metrics(actual[i][common], y[i][common]),
                    )
                )
    pd.DataFrame(rows).to_csv(root / "registration_sensitivity.csv", index=False)


def _decomposition(pixels, root):
    rows = []
    for variant in ["undarkened", "adjusted"]:
        error = pixels[variant + "_multiband_RMSE"]
        for feature in [
            "heterogeneity",
            "valid_coverage_fraction",
            "cloud_distance_lower_bound_m",
        ]:
            from scipy.stats import spearmanr

            rho = (
                float(spearmanr(pixels[feature], error).statistic)
                if pixels[feature].nunique() > 1 and error.nunique() > 1
                else np.nan
            )
            rows.append(
                dict(
                    variant=variant,
                    feature=feature,
                    error_metric="multiband_RMSE",
                    Spearman_rho=rho,
                    N=len(pixels),
                    interpretation="descriptive_within_one_spatially_correlated_flight_no_iid_pvalue",
                )
            )
    pd.DataFrame(rows).to_csv(root / "error_decomposition.csv", index=False)
    worst = pixels.nlargest(20, "undarkened_multiband_RMSE")
    worst.to_csv(root / "failure_pixels.csv", index=False)


def summarize_flight_validations(outputs, destination):
    """Read compact completed results only; equally weight flights, never pixels."""
    frames = []
    for path in outputs:
        root = Path(path)
        if (
            json.loads((root / "status.json").read_text())["status"]
            != "complete_single_flight"
        ):
            continue
        frames.append(pd.read_csv(root / "band_metrics.csv"))
    if not frames:
        raise ValueError("No completed flight validation metrics")
    all_rows = pd.concat(frames, ignore_index=True)
    if all_rows.duplicated(["flight_id", "variant", "band"]).any():
        raise ValueError("Duplicate flight validation summaries")
    records = []
    for (variant, band), group in all_rows.groupby(["variant", "band"]):
        row = dict(
            variant=variant, band=band, number_of_flights=group.flight_id.nunique()
        )
        for key in ["mean_bias", "MAE", "RMSE", "Pearson_r", "deming_slope"]:
            row["median_" + key] = group[key].median()
            row["min_" + key] = group[key].min()
            row["max_" + key] = group[key].max()
        row["replication_status"] = (
            "single_flight_not_cross_flight_evidence"
            if len(group) == 1
            else "equally_weighted_flight_distribution"
        )
        records.append(row)
    result = pd.DataFrame(records)
    result.to_csv(destination, index=False)
    return result
