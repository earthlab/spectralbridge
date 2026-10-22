"""Export both explicit label options aligned to the unchanged new spectral array."""

from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent


def main():
    d = pd.read_csv(OUT / "tables/new_selected_identity.csv")
    original = d.cover_category.to_numpy(str)
    revised = np.array(
        [
            "Herbaceous_woody_shrub" if atom in ("Herbaceous", "Woody shrub") else atom
            for atom in d.atom
        ],
        dtype=str,
    )
    np.save(
        OUT / "new_IES_original_researcher_labels.npy", original, allow_pickle=False
    )
    np.save(OUT / "new_IES_revised_labels.npy", revised, allow_pickle=False)
    d[["array_index", "GlobalID", "cover_category", "atom", "site", "year"]].assign(
        new_class=revised, selected_column=np.arange(len(d))
    ).to_csv(OUT / "tables/new_label_options.csv", index=False)
    print(
        f"Exported two string-label options for {len(d)} unchanged spectral columns; no spectral library copied."
    )


if __name__ == "__main__":
    main()
