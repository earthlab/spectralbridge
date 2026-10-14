# Verification record

- Full suite: 616 passed, 8 skipped, 29 warnings (122.92 s).
- Four new focused regression contracts pass.
- Independent numerical/export validator passes; all 338 canonical owned files and sensor evidence hashes verified.
- All ten PDF pages have no text outside page boundaries; main PDF/PNG/SVG and eight standalone panels inspected.
- Consecutive complete builds reproduce all 33 deliverable files byte for byte.
- Focused Ruff, strict MkDocs, docs links, prompt transparency regeneration and whitespace pass.
- The plotting command uses `.venv/bin/python`; PDF geometry QA uses the bundled PDF runtime; Poppler and sharp/libvips provide independent vector renderers.

Exact logs: checks/. Machine-readable QA: numerical_validation.json, pdf_validation.json and reproducibility_validation.json. Scientific details and limits: FIGURE_VALIDATION.md.
