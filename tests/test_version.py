from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 CI
    import tomli as tomllib

from scholaraio import __version__


def test_runtime_version_matches_project_version():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "(?P<version>[^"]+)"$', text)
    assert match is not None
    project_version = match.group("version")

    assert __version__ == project_version


def test_citation_version_matches_project_version():
    root = Path(__file__).resolve().parents[1]
    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    project_match = re.search(r'(?m)^version = "(?P<version>[^"]+)"$', pyproject_text)
    assert project_match is not None

    citation_text = (root / "CITATION.cff").read_text(encoding="utf-8")
    citation_match = re.search(r'(?m)^version:\s*"?([^"\n]+)"?\s*$', citation_text)
    assert citation_match is not None

    assert citation_match.group(1).strip() == project_match.group("version")


def test_release_version_is_2_0_0():
    assert __version__ == "2.0.0"


def test_plugin_versions_match_release_version():
    root = Path(__file__).resolve().parents[1]
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))

    assert plugin["version"] == __version__
    assert marketplace["metadata"]["version"] == __version__
    assert {item["version"] for item in marketplace["plugins"]} == {__version__}


def test_mineru_open_api_is_isolated_in_optional_cloud_extra():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert "mineru-open-api>=0.5.9" not in data["project"]["dependencies"]
    assert data["project"]["optional-dependencies"]["mineru-cloud"] == ["mineru-open-api>=0.5.9"]
    assert "scholaraio[mineru-cloud]" not in data["project"]["optional-dependencies"]["full"]


def test_unowned_draw_packages_are_not_published_or_recommended():
    root = Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    install_script = (root / "scripts" / "check-deps.sh").read_text(encoding="utf-8")

    optional = data["project"]["optional-dependencies"]
    all_requirements = [*data["project"]["dependencies"]]
    for requirements in optional.values():
        all_requirements.extend(requirements)

    assert "draw" not in optional
    assert "scholaraio[draw]" not in optional["full"]
    assert not any(requirement.startswith("mermaid-py") for requirement in all_requirements)
    assert not any(requirement.startswith("cli-anything-inkscape") for requirement in all_requirements)
    assert "scholaraio[draw]" not in install_script


def test_plugin_bootstrap_reports_fresh_paper_library_path():
    root = Path(__file__).resolve().parents[1]
    install_script = (root / "scripts" / "check-deps.sh").read_text(encoding="utf-8")

    assert "$GLOBAL_DIR/data/libraries/papers/" in install_script
    assert '"  Your data:    $GLOBAL_DIR/data/papers/"' not in install_script
