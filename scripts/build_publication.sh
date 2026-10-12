#!/usr/bin/env bash
# Canonical sources live in paper/; every render goes into paper/generated/.
set -euo pipefail
publication_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$publication_root"
publication_python="${PUBLICATION_PYTHON:-python3}"
publication_image="openjournals/inara@sha256:a0414b8b72fd8923917ede614d340d98dc7aa3102aabc2e955e9c02a6100fd62"
publication_mode="${1:-all}"
mkdir -p paper/generated
if [[ "$publication_mode" == all || "$publication_mode" == paper ]]; then
  "$publication_python" scripts/check_joss_submission.py --output paper/generated/submission-checks.json
  docker run --rm --network none --volume "$publication_root/paper:/data" \
    --user "${PUBLICATION_DOCKER_USER:-$(id -u):$(id -g)}" --env JOURNAL=joss "$publication_image" -o pdf paper.md
  mv paper/paper.pdf paper/generated/paper.pdf
  "$publication_python" scripts/record_publication_build.py --image "$publication_image"
fi
if [[ "$publication_mode" == all || "$publication_mode" == supplement ]]; then
  "$publication_python" scripts/generate_supplement_docs.py --prepare-render
  docker run --rm --network none --entrypoint pandoc --volume "$publication_root/paper:/data" \
    --workdir /data --user "${PUBLICATION_DOCKER_USER:-$(id -u):$(id -g)}" "$publication_image" supplement.md \
    --citeproc --bibliography supplement.bib --metadata title= --mathml --toc --standalone \
    --include-before-body generated/supplement-render-header.html --to html5 \
    --output generated/supplement.html
  "$publication_python" scripts/generate_supplement_docs.py
  "$publication_python" scripts/generate_supplement_docs.py --check
fi
if [[ "$publication_mode" == supplement-pdf ]]; then
  # Optional submission derivative. Review its layout before circulation; the
  # original author-supplied PDF in paper/archive/ remains an immutable snapshot.
  docker run --rm --network none --entrypoint pandoc --volume "$publication_root/paper:/data" \
    --workdir /data --user "${PUBLICATION_DOCKER_USER:-$(id -u):$(id -g)}" "$publication_image" supplement.md \
    --citeproc --bibliography supplement.bib --toc --pdf-engine=xelatex \
    -V geometry:margin=1in -V fontsize=10pt --output generated/supplement.pdf
fi
if [[ "$publication_mode" != all && "$publication_mode" != paper && "$publication_mode" != supplement && "$publication_mode" != supplement-pdf ]]; then
  echo "Usage: scripts/build_publication.sh [all|paper|supplement|supplement-pdf]" >&2
  exit 2
fi
