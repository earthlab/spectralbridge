# SpectralBridge notebook vignettes

These are the actual Jupyter `.ipynb` files used by the vignette catalog. Open
them in numeric order or choose the stage you need. GitHub can display their
Markdown and code cells, but it does not execute them; clone or download the
repository to run or edit a notebook.

The website catalog, purpose of each notebook, and setup instructions are in
[`../notebook-vignettes.md`](../notebook-vignettes.md). Its notebook links point
back to these tracked files in GitHub's repository viewer rather than to static
copies on GitHub Pages.

All learning examples default to `RUN = False`. The advanced CyVerse bulk
production notebook also has an explicit `RUN = False` guard, but can transfer
large datasets once enabled. Edit its collection, VM output paths, disk limits,
and stage before running it.

The first ten examples intentionally mirror the working patterns in the root
`Raster_processing.ipynb` and `Drone_processing.ipynb`: configure with ordinary
`Path` values, call the public orchestrator, print its result or output paths,
and inspect the concrete Parquet, ENVI, and QA artifacts. The vignette versions
remove saved outputs and environment-specific transfer commands so they can be
opened safely in a fresh clone. The advanced production notebook is the
exception: it preserves the supplied CyVerse transfer and closeout gates for
curated archives. The supplied PDF printout is not published because its code
is clipped; use the notebook as executable source.
