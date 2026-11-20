"""Second frozen photo-only review: Yellowstone meadows and California shrubs.

Uses the first completed power-expansion cohort as an immutable parent. Execute
--freeze once before regional --extract calls; --finalize appends the additions.
"""

import argparse

import landsat_hls_power_reference_build as build


def specification():
    cases = []
    # Sparse woody/rock contexts and the ambiguous senescent 2025 meadow omitted.
    for i in [1, 2, 3, 4, 6, 8]:
        bounds = {1: (-30, 20, 110, 110), 3: (-110, -110, 110, 75)}.get(
            i, (-110, -110, 110, 110)
        )
        cases.append(
            dict(
                context_patch_id=f"power-yellowstone-herbaceous-{i:03}",
                target="Herbaceous",
                patch=build.rectangle(*bounds),
                dark_unknown_max_ceiling=50,
                bright_unknown_floor=180,
                interpretation="Low continuous meadow growth form; bare holes explicit unknown polygons; channel/pond avoided. Single provisional interpretation.",
                unknown_polygons={
                    2: [
                        build.rectangle(-112, 27, -101, 41),
                        build.rectangle(-38, 65, -28, 78),
                        build.rectangle(4, -4, 17, 11),
                        build.rectangle(65, -20, 79, -3),
                    ],
                    6: [
                        build.rectangle(-80, 25, -63, 41),
                        build.rectangle(-42, 8, -25, 25),
                        build.rectangle(-62, -37, -48, -23),
                    ],
                    8: [
                        build.rectangle(-18, 70, -1, 86),
                        build.rectangle(-32, 31, -15, 44),
                        build.rectangle(38, 16, 57, 37),
                        build.rectangle(65, 23, 84, 39),
                    ],
                }.get(i, []),
            )
        )
    for i in [1, 2, 3, 4, 5, 6, 7, 8]:
        bounds = {
            2: (20, -110, 110, 110),
            5: (-110, -110, -50, 110),
            7: (-70, -110, 35, 110),
            8: (-110, 25, 110, 110),
        }.get(i, (-110, -110, 110, 110))
        cases.append(
            dict(
                context_patch_id=f"power-california_shrublands-woody-{i:03}",
                target="Woody shrub",
                patch=build.rectangle(*bounds),
                dark_unknown_max_ceiling=45,
                bright_unknown_floor=120,
                interpretation="Dense low chaparral-form crowns in selected area; pale soil and dark gaps remain unknown using parent photo mask. Growth form not independently height-validated.",
            )
        )
    return cases


def configure():
    build.PARENT = build.COMBINED
    build.REVIEW = build.ROOT / "review-batch-2"
    build.ADDITIONS = build.REVIEW / "hls-additions"
    build.COMBINED = build.REVIEW / "hls-combined"
    build.REGIONS = ["yellowstone", "california_shrublands"]
    build.review_specification = specification


if __name__ == "__main__":
    configure()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--extract", choices=build.REGIONS)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        print("Frozen second review:", len(build.freeze()["cases"]), flush=True)
        build.additional_cases(write_geometry=True)
    if args.extract:
        build.initialize()
        build.builder.extract(args.extract)
    if args.finalize:
        build.finalize()
