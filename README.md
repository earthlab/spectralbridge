# SpectralBridge

SpectralBridge is scientific Python software for preparing and comparing
reflectance across airborne, drone and satellite sensor representations. It
serves remote-sensing researchers who need traceable intermediate products,
restart-safe processing and explicit quality checks.

Three separate workflows process NEON flightlines, supported local drone imagery,
and collections of completed products. Spectral libraries and numerical analysis
methods support downstream research. Configured sensor-like bands do not establish
agreement with independent sensor observations or field fractional cover.

[Documentation](https://earthlab.github.io/spectralbridge/) ·
[Scientific synthesis](https://earthlab.github.io/spectralbridge/spectral-library/scientific-synthesis/) ·
[Python API](https://earthlab.github.io/spectralbridge/api/) ·
[Issues](https://github.com/earthlab/spectralbridge/issues)

## Install and verify

The distribution is **`earthlab-spectralbridge`**; the Python import is
**`spectralbridge`**. Python 3.10–3.12 is the tested release range.

These commands install the checked-out source and run an offline lesson. Use a
virtual environment so this installation stays separate from other projects:

```bash
git clone https://github.com/earthlab/spectralbridge.git
cd spectralbridge
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python examples/first_example.py
```

On Windows, activate with `.venv\Scripts\activate` in Command Prompt.
For numerical separability, recognition and mixture examples, install the optional
analysis dependencies with `python -m pip install -e '.[analytics]'`.
Source installation does not imply a published release; check the version with
`python -c "import spectralbridge; print(spectralbridge.__version__)"`.

The tiny example inspects an invented spectral table without downloads or
credentials. It verifies software use, not scientific accuracy.
[Continue the beginner path](https://earthlab.github.io/spectralbridge/getting-started/).

## Choose a workflow

| Your goal / inputs | Start here |
| --- | --- |
| Process NEON airborne flightlines | [NEON processing](https://earthlab.github.io/spectralbridge/vignettes/full-pipeline/) |
| Process supported drone TIFF/HDF5 | [Drone processing](https://earthlab.github.io/spectralbridge/vignettes/drone-processing/) |
| Translate spectra into target-sensor bands | [Sensor harmonization](https://earthlab.github.io/spectralbridge/vignettes/sensor-harmonization/) |
| Create a library from imagery and field polygons | [Polygon extraction](https://earthlab.github.io/spectralbridge/vignettes/polygon-extraction/) |
| Inspect a library or evaluate spectral differences, recognition and mixtures | [Library reporting](https://earthlab.github.io/spectralbridge/vignettes/spectral-library/) and [analysis methods](https://earthlab.github.io/spectralbridge/api/scientific-analysis/) |
| Analyze many completed flightline products | [Bulk analysis](https://earthlab.github.io/spectralbridge/vignettes/bulk-analysis/) |

The [drone architecture study](provenance/drone-architecture-2026-11-06/REPORT.md)
compares verified H5 inputs, camera geometry, compact calibration and original
photographs, with measured benefits and remaining correction limitations.

The [workflow map](https://earthlab.github.io/spectralbridge/vignettes/) lists
inputs, outputs, entry points and support limits. To keep a small result you can
inspect, run `python examples/scientific_workflows_offline.py --output-dir lesson_output`.
It writes an invented teaching table, compact plant summaries and an explained
JSON result without credentials or downloads.

Review [output contracts](https://earthlab.github.io/spectralbridge/pipeline/outputs/)
and [QA evidence](https://earthlab.github.io/spectralbridge/validation/evidence-hierarchy/)
before drawing conclusions. Reusable numerical methods require the `analytics`
extra; [their API guide](https://earthlab.github.io/spectralbridge/api/scientific-analysis/)
separates supported numerical contracts from conditional scientific inference.

For drone work, read [Choosing corrections](https://earthlab.github.io/spectralbridge/concepts/correction-eligibility/)
and [validation findings and current limitations](https://earthlab.github.io/spectralbridge/validation/drone-findings/).
Spatial repair and numerical recovery do not establish physical reflectance or
BRDF eligibility.

## Cite, contribute and find the evidence

Cite the software release actually used and relevant scientific methods.
[Software citation guidance](https://earthlab.github.io/spectralbridge/dev/software-citation/)
explains the current author-metadata and archive limitations. The repository's
[CITATION.cff](https://github.com/earthlab/spectralbridge/blob/main/CITATION.cff)
still requires maintainer-approved authorship; the
[software paper sources](https://github.com/earthlab/spectralbridge/tree/main/paper)
are a prepared manuscript, not an accepted publication.

Read [contribution guidance](https://github.com/earthlab/spectralbridge/blob/main/CONTRIBUTING.md),
[tests](https://github.com/earthlab/spectralbridge/tree/main/tests) and
[release gates](https://earthlab.github.io/spectralbridge/dev/releasing/).
The license is **GPL-3.0-or-later**; see
[LICENSE](https://github.com/earthlab/spectralbridge/blob/main/LICENSE),
[NOTICE](https://github.com/earthlab/spectralbridge/blob/main/NOTICE) and
[HyTools lineage](https://github.com/earthlab/spectralbridge/blob/main/HYTOOLS_PROVENANCE.md).
Historical research is preserved in
[provenance](https://github.com/earthlab/spectralbridge/tree/main/provenance) and
[archive](https://github.com/earthlab/spectralbridge/tree/main/archive).

Read the automated [AI transparency statement](https://earthlab.github.io/spectralbridge/ai-transparency/) for the maintainer-reported GPT-3.5 history, prompt-log figures and evidence limitations.
