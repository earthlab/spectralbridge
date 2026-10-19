# API audit and maintenance

The 2026-10-19 recursive audit inspected every Python source file under
`src/spectralbridge`, rather than treating README examples as the complete API.
Before documentation changes it found **131 modules, 432 non-underscore module
functions, 116 non-underscore classes and 289 non-underscore class members**.
These counts include implementation details. **125 functions/classes had no
docstring**, and a name-presence screening flagged **369 functions** whose
arguments were not all mentioned in their docstrings. That screening is a
triage measure, not a judgment that mentioned arguments were adequately explained.

## Scope and classification

The [downloadable inventory](inventory.json) records every module-level function
and class, including private ones; public-looking methods, signatures, parameter
annotations/defaults, class fields, existing docstrings, explicit `__all__`
expressions, imports/re-exports, source locations, example references and narrative
links are included. Each source file is fingerprinted with SHA-256.

- **Public:** existing supported package/subpackage exports and the explicit
  composable `library_analysis` facade. These are the primary integration points.
- **Advanced:** remaining non-private direct-module definitions. Inclusion makes
  these discoverable, not stable. Research functions retain their experimental
  boundaries. A public-looking name alone does not establish support.
- **Internal:** underscore helpers, private dependency adapters, compatibility
  modules, CLI dispatchers and named database/serialization plumbing. These remain
  in the inventory with a reason; their visibility is unchanged.

Canonical definitions render once, and aliases link to them. Methods belong to
their owning class. Explicitly exported constants and type aliases are listed
with their source expressions. Modules with no callable surface remain visible
in the machine-readable module inventory rather than receiving empty pages.

## Initial findings and deferred API design questions

- Package lazy `__getattr__` exports are not fully discovered by the old
  `::: spectralbridge` directive. The generator resolves them from their source
  imports and documents the canonical definitions explicitly.
- `DroneSource`, `BulkSource`, `BulkInputKind` and `BulkInputMode` are type aliases,
  not callable constructors. Import paths and canonical values are recorded.
- Optional plotting exports can depend on installed plotting dependencies;
  inventorying the source does not promise availability in a minimal installation.
- Several module `__all__` lists intentionally include underscore helpers.
  They remain internal in the user glossary, without changing those lists.
- Compatibility and legacy file classes coexist with newer naming/path helpers.
  This documentation task does not redesign those APIs.
- Advanced research/helper docstrings vary in completeness. Their entries retain
  original scientific caveats and expose the current source contract; missing
  descriptions are identified in the inventory, not filled with invented units
  or promoted to stable entry points.
- `exports/` needed a docstring-only `__init__.py` so static collection could find
  its existing modules. No functions or algorithms were moved.

## Rebuild and check coverage

```bash
python scripts/generate_api_reference.py
python scripts/generate_api_reference.py --check
pytest -q tests/test_api_reference.py
mkdocs build --strict
```

The existing MkDocs and mkdocstrings Python handler render source signatures and
NumPy-style structured docstrings; existing Google-style entries are parsed in
their own style. No new documentation framework or dependency is introduced.
Generated Markdown is an index and a set of canonical autodoc directives, not a
second hand-maintained signature source. CI rejects stale generated files.

When adding a callable, document parameters, returned structure, units and
scientific assumptions in the source, add an executable small example where
practical, regenerate the reference, and inspect the rendered page. Narrative
workflow links belong next to the relevant task, not in a replacement tutorial.

## Implementation report — 2026-10-19

| Measure | Result |
| --- | ---: |
| Current Python modules, including the added package marker | 132 |
| Primary public functions / classes | 59 / 25 |
| Public class members with source docstrings | 90 |
| Public function arguments covered by structured parameter entries | 366 |
| Public configuration/record fields covered by structured attributes | 283 |
| Additional advanced functions / classes | 320 / 89 |
| Canonical functions/classes reachable from the glossary | 493 |
| Public-looking implementation functions/classes excluded from the glossary | 55 |
| Canonical generated module pages | 102 |
| Module-level rendered function signatures/defaults checked against source | 379 |

The [initial audit record](audit-baseline.json) lists all 125 initially
undocumented functions/classes and the 369 parameter-name screening gaps. The
current inventory records the audience and source docstring for each object.
All 84 primary public functions/classes have source descriptions; all 59 public
functions have structured argument and return contracts. Configuration/record
classes document fields with NumPy-style Attributes sections. Advanced entries
retain their existing maturity; discovery coverage is not a claim that every
advanced helper now has a complete scientific usage specification.

Three advanced definitions lack original source docstrings and are explicitly
annotated in the glossary because their source files are pinned in earlier
scientific evidence: `mesma_readiness.ReadinessConfig`,
`researcher_information.validate_researcher_labels`, and
`researcher_validation.balanced_accuracy`. Their inventory `summary_basis`
distinguishes the reference annotation from a source docstring. Improving their
source documentation requires a deliberate successor evidence revision, not
rewriting historical manifest hashes.

### What changed

- `scripts/generate_api_reference.py`: deterministic, import-free AST inventory,
  export resolution, audience classification, glossary and canonical autodoc
  directives; `--check` detects stale or omitted generated outputs.
- `scripts/check_api_reference.py`: rendered argument-order, argument-kind and
  default verification for every documented module-level function.
- `docs/api/index.md`, `generated/*.md`, `inventory.json`, this audit, the initial
  audit record, and `examples.md`: browsable reference and documented boundaries.
- Source docstrings in 58 existing modules: structured public contracts, field
  and method explanations, executable numerical examples and missing advanced
  summaries. The [behavior verification record](behavior-verification.json)
  lists those files and the executable-AST fingerprints.
- `src/spectralbridge/exports/__init__.py`: docstring-only marker required by the
  existing static collector; no moved functions or new exports.
- `mkdocs.yml`, the homepage, four workflow pages and the existing scientific API
  map: first-class API Reference navigation and links in both directions; old
  duplicate autodoc entries now link to canonical entries.
- `tests/test_api_reference.py` and existing CI workflows: source coverage,
  alias/default/parameter checks, executable examples, rendered signatures and
  automatic freshness verification. Documentation CI installs the existing
  analytics extra to exercise classifier examples.
- Prompt logging and regenerated AI-transparency artifacts accompany this work.

### Verification and remaining limitations

The targeted API/numerical/public-export suite passes **75 tests**. The strict
MkDocs build, source links, rendered internal anchors/assets, Ruff and generated
freshness checks pass. Eighteen representative desktop/mobile page renders
cover the glossary, long orchestrator signatures, library methods, configuration
records, QA and examples. Data-dependent producer examples are signature-checked
and explicitly skipped, not presented as executed raster processing.

All existing source files have unchanged executable ASTs after removing
docstrings; all **1,053 entries** in the five existing scientific/formal evidence
manifests remain byte-identical. No scientific experiments were rerun. The only
new source module is the docstring-only export package marker.

There are no remaining strict-build warnings or unresolved internal references.
The test run emits the existing `cross_sensor_cal` compatibility deprecation
warning from the polygon import. The following API design questions remain
recommendations, not changes made here:

- Decide whether advanced direct-module helpers merit formal supported exports.
- Expand advanced scientific parameter/return contracts where the original source
  offers only a summary; do not infer units or data requirements from names alone.
- Replace hash-pinned legacy research implementations only through a successor
  provenance contract.
- The legacy `representation_values(arrays, representation)` retains an unused
  `arrays` argument; documentation records that fact without removing it.
- The legacy `to_unitless_reflectance` helper uses a median heuristic, whereas
  explicit metadata-driven conversions exist. The reference describes both and
  does not silently change scaling assumptions.
