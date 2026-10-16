"""Publication caption assembled from source-derived annotation values."""

from .figure_data import BASE, REPO, load_bundle


def main():
    d = load_bundle()
    a = d["annotations"].set_index("annotation").value
    f = d["F_library_comparison"].pivot(index="method", columns="kind", values="RMSE")
    caption = (
        (
            "**Figure. Spectral differences support recognition, but quantity remains constrained by library variability and ambiguity.** "
            "(A) Corrected NEON category medians and pointwise interquartile ranges across polygon/year observations show structured, overlapping spectra in stored units; absolute reflectance scaling remains unresolved. Grey gaps mark excluded atmospheric regions; upper bars show synthetic OLI centers/full widths at half maximum. "
            "(B) Effects (first category minus second) are cohort medians across four observed site/year groups. Faint cells lack consistent corrected support and direction in all four; they are not zero effects. All ten whole-spectrum contrasts are supported. "
            "(C) Recognition accumulates across wavelengths. Selected and random subsets use matched nested validation; solid/open circles denote new polygons and dashed/filled squares held sites. Envelopes are observed fold/seed ranges, not confidence intervals; Full uses all360 coordinates. "
            f"(D) Held-site confusion (rounded row percentages; true rows, predicted columns) and aligned recall shifts reveal uneven transfer, especially Woody shrub ({a['D_Woody_shrub_site']:.1%}). "
            "(E) Held-site mean calibration shows false abundance at zero and high-fraction shrinkage. Category ordering/colors link recognition and quantification without a population correlation claim. "
            f"(F) Ridge120 lowers mean-fold RMSE versus MESMA15 by {a['F_plant_relative_improvement']:.1%}/{a['F_site_relative_improvement']:.1%} for new-parent/held-site targets. Using the same15 MESMA parents removes that mean NEON advantage: Ridge15 {f.loc['Ridge15', 'plant']:.3f}/{f.loc['Ridge15', 'site']:.3f}, MESMA15 {f.loc['MESMA15', 'plant']:.3f}/{f.loc['MESMA15', 'site']:.3f}. Thin ranges span observed folds. Retained diversity/training bundles also change; intrinsic algorithm superiority is not established. Error can decline in highly ambiguous targets while alternative near-fitting compositions remain feasible; moderate ambiguity can favor MESMA. "
            "All abundance fractions shown here are controlled synthetic algebraic fractions; independent field fractional-cover validation remains outstanding."
        )
        .replace("all360", "all 360")
        .replace("same15", "same 15")
    )
    (BASE / "CAPTION.md").write_text(caption + "\n")
    out = REPO / "output/figures/manuscript_synthesis"
    out.mkdir(exist_ok=True)
    (out / "figure_main_synthesis_caption.txt").write_text(
        caption.replace("**", "") + "\n"
    )
    print("Caption saved:", len(caption.split()), "words.")


if __name__ == "__main__":
    main()
