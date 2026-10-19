"""Reader-facing metadata contracts; never infer human declarations."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_pypi_readme_links_are_absolute_and_have_no_unresolved_tokens():
    text = (ROOT / 'README.md').read_text()
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text)
    assert links
    assert all(link.startswith('https://') for link in links)
    assert not re.search(r'\b(?:TODO|FIXME|TBD|PLACEHOLDER)\b', text)
    assert 'python -m pip install -e .' in text
    assert 'python examples/first_example.py' in text


def test_known_metadata_url_points_to_existing_changelog():
    text = (ROOT / 'pyproject.toml').read_text()
    assert 'Changelog = "https://github.com/earthlab/spectralbridge/blob/main/CHANGELOG.md"' in text
    assert (ROOT / 'CHANGELOG.md').is_file()
