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

At the 19 October 2026 audit, PyPI did not expose this distribution name.
Use the source installation below. Repository HEAD identifies `2.3.0rc1`,
which is a candidate identity rather than a published release. Create a virtual
environment, then run:

```bash
git clone https://github.com/earthlab/spectralbridge.git
cd spectralbridge
python -m pip install -e .
python examples/first_example.py
```

The tiny example inspects an invented spectral table without downloads or
credentials. It verifies software use, not scientific accuracy.
[Continue the beginner path](https://earthlab.github.io/spectralbridge/getting-started/).

## Choose a workflow

| Your inputs | Guide |
| --- | --- |
| NEON airborne flightlines | [NEON processing](https://earthlab.github.io/spectralbridge/vignettes/full-pipeline/) |
| Supported local drone TIFF/HDF5 | [Drone processing](https://earthlab.github.io/spectralbridge/vignettes/drone-processing/) |
| Completed flightline products | [Bulk analysis](https://earthlab.github.io/spectralbridge/vignettes/bulk-analysis/) |
| Existing polygon spectral library | [Library preflight and reporting](https://earthlab.github.io/spectralbridge/vignettes/spectral-library/) |

Review [output contracts](https://earthlab.github.io/spectralbridge/pipeline/outputs/)
and [QA evidence](https://earthlab.github.io/spectralbridge/validation/evidence-hierarchy/)
before drawing conclusions. Reusable numerical methods require the `analytics`
extra; [their API guide](https://earthlab.github.io/spectralbridge/api/scientific-analysis/)
separates supported numerical contracts from conditional scientific inference.

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
