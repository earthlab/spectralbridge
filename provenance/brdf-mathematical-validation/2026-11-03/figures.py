"""Scientific figures from current kernels, frozen references and actual geometry."""

import importlib.util
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge import corrections as c  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "math_old",
    ROOT / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py",
)
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.formatter.useoffset": False,
        "svg.fonttype": "none",
    }
)
record = json.loads((HERE / "real_geometry_validation.json").read_text())
manifest = []


def save(fig, name, caption):
    fig.savefig(HERE / (name + ".png"), dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    manifest.append(dict(name=name, caption=caption))


def main():
    s, v = np.meshgrid(
        np.deg2rad(np.linspace(0, 80, 321)), np.deg2rad(np.linspace(0, 80, 321))
    )
    for kernel, title, name in [
        ("RossThick", "RossThick volumetric response", "figure01_ross_response"),
        (
            "LiDenseR",
            "LiDenseR reciprocal dense response | b/r=10, h/b=2",
            "figure02_dense_response",
        ),
    ]:
        fig, axs = plt.subplots(1, 3, figsize=(15, 5), layout="constrained")
        values = []
        for phi in [0, 90, 180]:
            values.append(
                c.calc_volume_kernel(0, s, np.deg2rad(phi), v, kernel_type=kernel)
                if kernel == "RossThick"
                else c.calc_geom_kernel(
                    0, s, np.deg2rad(phi), v, kernel_type=kernel, b_r=10, h_b=2
                )
            )
        lim = max(float(np.max(np.abs(x))) for x in values)
        for ax, phi, a in zip(axs, [0, 90, 180], values):
            im = ax.imshow(
                a,
                origin="lower",
                extent=[0, 80, 0, 80],
                cmap="RdBu_r",
                norm=TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim),
            )
            ax.set(
                xlabel="Solar zenith (degrees)",
                ylabel="View zenith (degrees)",
                title=f"Relative azimuth {phi}°",
            )
        fig.colorbar(im, ax=axs, label="Unscaled kernel value", shrink=0.8)
        fig.suptitle(title, fontsize=17)
        save(
            fig,
            name,
            "Synthetic angular response, not measured imagery or a fitted correction. Same color scale within each figure. Relative azimuth zero is backscatter. Both kernels are zero at double nadir; the dense model is not sparse reciprocal. Upper-hemisphere support is 0 <= zenith < 90 degrees; displaying 0–80 degrees is not an empirical validation domain.",
        )
    az = np.linspace(0, 360, 721)
    a = [
        np.full((1, len(az)), x, np.float32)
        for x in [np.deg2rad(188.00578), np.deg2rad(37.412113), 0, 0]
    ]
    a[2][0] = np.deg2rad(az)
    current = c.calc_geom_kernel(*a, kernel_type="LiDenseR", b_r=10)
    historic = old.calc_geom_kernel(*a, kernel_type="LiDenseR", b_r=10)
    fig, axs = plt.subplots(1, 2, figsize=(14, 5), layout="constrained")
    axs[0].plot(az, historic[0], label="Historical defective LiDenseR", color="#b67732")
    axs[0].plot(az, current[0], label="Verified reciprocal dense", color="#276f91")
    axs[0].set(
        xlabel="Arbitrary sensor azimuth at exact nadir (degrees)",
        ylabel="Kernel value",
        title="Only the historical kernel creates an azimuth response",
    )
    axs[0].legend()
    for br in [1, 2.5, 10]:
        axs[1].plot(
            az,
            c.calc_geom_kernel(a[0], a[1], a[2], a[3], kernel_type="LiDenseR", b_r=br)[
                0
            ],
            label=f"b/r={br}",
        )
    axs[1].set(
        xlabel="Arbitrary sensor azimuth (degrees)",
        ylabel="Kernel value",
        title="Nadir invariance holds across crown-shape parameters",
    )
    axs[1].legend()
    fig.suptitle("Nadir viewing cannot identify a sensor azimuth", fontsize=17)
    save(
        fig,
        "figure03_nadir_invariance",
        "Controlled geometry at solar zenith 37.412113 degrees and exact zero view zenith. The historical kernel retained cos(relative azimuth) where a phase-angle dependence was required, along with incorrect crown and overlap terms. Constant verified curves are the required invariance, not evidence that a fixed view can support three coefficients.",
    )
    for flight, name in [
        ("neon", "figure04_neon_geometry"),
        ("goldhill", "figure05_goldhill_geometry"),
    ]:
        d = np.load(HERE / f"{flight}_geometry_display.npz")
        if flight == "neon":
            fields = [
                ("sensor_zenith", "Measured AOP view zenith (deg)"),
                ("sensor_azimuth", "Measured AOP view azimuth (deg)"),
                ("ross", "Verified RossThick"),
                ("dense", "Verified LiDenseR"),
                ("old_dense", "Historical defective LiDenseR"),
                ("difference", "Verified minus historical LiDenseR"),
            ]
        else:
            fields = [
                ("solar_azimuth", "Derived solar azimuth | time unverified"),
                ("old_dense", "Historical LiDenseR | spurious spatial gradient"),
                ("dense", "Verified LiDenseR | uniform at this scene/nadir"),
                ("difference", "Verified minus historical LiDenseR"),
            ]
        fig, axs = plt.subplots(
            3 if flight == "neon" else 2, 2, figsize=(16, 10), layout="constrained"
        )
        for ax, (key, label) in zip(axs.flat, fields):
            a = d[key]
            cm = plt.get_cmap(
                "twilight" if key == "sensor_azimuth" else "viridis"
            ).copy()
            cm.set_bad("#d5d5d5")
            im = ax.imshow(
                np.ma.masked_invalid(a),
                extent=[
                    -record["flights"][flight]["display_stride"] / 2,
                    (a.shape[1] - 0.5) * record["flights"][flight]["display_stride"],
                    (a.shape[0] - 0.5) * record["flights"][flight]["display_stride"],
                    -record["flights"][flight]["display_stride"] / 2,
                ],
                origin="upper",
                cmap=cm,
                interpolation="nearest",
            )
            ax.set(
                title=label, xlabel="Native source column", ylabel="Native source row"
            )
            if np.nanmin(a) == np.nanmax(a):
                ax.text(
                    0.02,
                    0.05,
                    f"Constant {np.nanmin(a):.9g}",
                    transform=ax.transAxes,
                    bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"),
                )
            else:
                fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
        fig.suptitle(
            (
                "Genuine NEON R10C L002, 15 September 2021"
                if flight == "neon"
                else "Goldhill: unchanged zero-view placeholders reveal missing angular support"
            )
            + "\nActual native geometry; panels have labeled independent scales",
            fontsize=17,
        )
        save(
            fig,
            name,
            "Native source row/column orientation is preserved; gray denotes invalid source/geometry. Display arrays are deterministic native point samples (NEON stride 4, Goldhill stride 6); quantitative ranges, maxima and QR/SVD use every retained native pixel. Scene solar zenith is used for both historical and current comparisons. Goldhill views remain placeholders and are never invented; source alpha is not rewritten. A narrower color range in the old Goldhill map exposes tiny artificial variation, not comparable physical signal amplitude.",
        )
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for ax, name in zip(axs, ["neon", "goldhill"]):
        f = record["flights"][name]
        for variant, color in [("current", "#276f91"), ("historical", "#b67732")]:
            design = f["designs"][variant]
            sv = np.array(design["singular_values"])
            ax.plot(
                [1, 2, 3],
                sv / sv[0],
                marker="o",
                color=color,
                label=f"{variant}: rank {design['rank']}/3",
            )
        ax.set(
            yscale="log",
            xlabel="Singular-value index",
            ylabel="Singular value / largest",
            title=name.title()
            + f" | {f['positive_polar_geometry_pixels']:,} native pixels",
            xticks=[1, 2, 3],
        )
        ax.legend()
    fig.suptitle(
        "Real AOP angular variation is informative; the drone placeholder field is deficient",
        fontsize=17,
    )
    save(
        fig,
        "figure06_design_singular_values",
        "Tall-skinny QR followed by SVD on the full native angular design [1,K_Ross,K_Li]. NEON rank 3 and conditioning are numerical geometry diagnostics, not proof of calibrated surface normalization across heterogeneous pixels. Goldhill rank 1 implies infinite mathematical condition number; its tiny numerical trailing singular values depend on floating-point accumulation and must not be interpreted as recovered angles. Historical Goldhill rank 2 is manufactured by the defective kernel and remains unsupported.",
    )
    refs = json.loads(
        (ROOT / "tests/data/brdf/published_equation_references.json").read_text()
    )
    errors = {k: [] for k in ["RossThick", "LiDenseR", "LiSparseReciprocal"]}
    for row in refs["rows"]:
        a = np.deg2rad([0, row["solar_deg"], row["relative_deg"], row["view_deg"]])
        for k in errors:
            actual = (
                c.calc_volume_kernel(*a, kernel_type=k)
                if k == "RossThick"
                else c.calc_geom_kernel(
                    *a, kernel_type=k, b_r=row["b_r"], h_b=row["h_b"]
                )
            )
            errors[k].append(abs(float(actual) - row[k]))
    error_record = {}
    for k, values in errors.items():
        worst = int(np.argmax(values))
        expected = np.array([r[k] for r in refs["rows"]])
        ordinary = np.array(
            [max(r["solar_deg"], r["view_deg"]) <= 80 for r in refs["rows"]]
        )
        error_record[k] = dict(
            cases=len(values),
            max_absolute_error=max(values),
            median_absolute_error=float(np.median(values)),
            maximum_error_scaled_by_one_plus_absolute_expected=float(
                np.max(np.array(values) / (1 + np.abs(expected)))
            ),
            max_absolute_error_through_80_degrees=float(
                np.max(np.array(values)[ordinary])
            ),
            worst_absolute_case=refs["rows"][worst],
        )
    (HERE / "independent_reference_results.json").write_text(
        json.dumps(
            dict(
                reference_method=refs["method"],
                current_kernel_version=c.BRDF_KERNEL_MATH_VERSION,
                errors=error_record,
                external_cpp=refs["independent_cpp"],
            ),
            indent=2,
        )
        + "\n"
    )
    fig, ax = plt.subplots(figsize=(12, 5), layout="constrained")
    for k, e in errors.items():
        ax.plot(np.maximum(e, np.finfo(float).eps), label=k, alpha=0.7)
    ax.set(
        yscale="log",
        xlabel="Frozen independent reference case",
        ylabel="Absolute kernel error (floor epsilon for display only)",
        title=f"{len(refs['rows'])} independently calculated 60-digit geometries per kernel",
    )
    ax.legend()
    save(
        fig,
        "figure07_reference_errors",
        "Expected values are evaluated by an independent scalar arbitrary-precision implementation of published equations; no SpectralBridge function generates them. Grazing geometries amplify input-angle representation error, so tests use a documented relative tolerance. The external pinned C++ Ross and nonreciprocal dense functions are separately executed, with an explicit reciprocal conversion; they are not assumed interchangeable without that conversion. The epsilon plot floor changes no reported errors.",
    )
    fig, axs = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    for i, flight in enumerate(["neon", "goldhill"]):
        data = np.load(HERE / f"{flight}_geometry_display.npz")
        for j, kernel in enumerate(["ross", "dense"]):
            ax = axs[i, j]
            for key, color in [(kernel, "#276f91"), ("old_" + kernel, "#b67732")]:
                values = data[key][np.isfinite(data[key])]
                label = "Verified" if key == kernel else "Historical defective"
                if np.ptp(values) == 0:
                    ax.axvline(
                        values[0],
                        color=color,
                        label=f"{label}: constant {values[0]:.9g}",
                    )
                else:
                    ax.hist(values, bins=70, histtype="step", color=color, label=label)
            ax.set(
                title=flight.title()
                + " | "
                + ("RossThick" if kernel == "ross" else "LiDenseR"),
                xlabel="Unscaled kernel value",
                ylabel="Native-point display-sample count",
            )
            ax.legend(fontsize=9)
    fig.suptitle(
        "Actual kernel distributions | spatial sample counts are not independent camera observations",
        fontsize=16,
    )
    save(
        fig,
        "figure08_kernel_distributions",
        "Histograms use the compact native-point display sample; complete native min/max/mean/standard deviation are in real_geometry_validation.json. Goldhill constant fields use single-value lines. Narrow old Goldhill variation is numerical artifact, not an independent viewing population. Counts describe spatial samples and are not empirical BRDF replicate counts.",
    )
    (HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Eight PNG/SVG figure pairs and independent error audit complete", flush=True)


if __name__ == "__main__":
    main()
