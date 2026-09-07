from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts.check_release_metadata import (
    ReleaseMetadata,
    read_release_metadata,
    validate_release_metadata,
    write_github_outputs,
)


def test_release_metadata_accepts_exact_release_tag() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")

    validate_release_metadata(metadata)

    assert metadata.is_prerelease is False
    assert metadata.base_version == "2.0.0"
    assert metadata.development_statuses == ("Development Status :: 5 - Production/Stable",)
    assert "2.0.0" in metadata.changelog_versions
    assert metadata.citation_date == "2026-08-17"
    assert dict(metadata.changelog_release_dates)["2.0.0"] == metadata.citation_date


def test_release_metadata_accepts_prerelease_tag_with_current_base_version(tmp_path) -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0-beta.1")
    output = tmp_path / "github-output.txt"

    validate_release_metadata(metadata)
    write_github_outputs(metadata, str(output))

    assert metadata.is_prerelease is True
    assert metadata.base_version == "2.0.0"
    assert metadata.prerelease_label == "beta.1"
    assert "is_prerelease=true" in output.read_text(encoding="utf-8")


def test_release_metadata_rejects_wrong_base_tag_version() -> None:
    metadata = ReleaseMetadata(
        tag_version="1.6.0-beta.1",
        base_version="1.6.0",
        pyproject_version="2.0.0",
        runtime_version="2.0.0",
        citation_version="2.0.0",
        citation_date="2026-08-17",
        development_statuses=("Development Status :: 5 - Production/Stable",),
        changelog_versions=("2.0.0",),
        changelog_release_dates=(("2.0.0", "2026-08-17"),),
        is_prerelease=True,
        prerelease_label="beta.1",
    )

    with pytest.raises(SystemExit, match=r"tag=1\.6\.0"):
        validate_release_metadata(metadata)


def test_release_metadata_rejects_stable_tag_without_changelog_section() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")
    metadata = replace(metadata, changelog_versions=("2.0.0-beta.1",))

    with pytest.raises(SystemExit, match="exactly one matching CHANGELOG"):
        validate_release_metadata(metadata)


def test_release_metadata_rejects_duplicate_changelog_sections() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")
    metadata = replace(metadata, changelog_versions=(*metadata.changelog_versions, "2.0.0"))

    with pytest.raises(SystemExit, match=r"exactly one matching CHANGELOG.*got: 2"):
        validate_release_metadata(metadata)


def test_release_metadata_rejects_beta_classifier_for_stable_tag() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")
    metadata = replace(
        metadata,
        development_statuses=("Development Status :: 4 - Beta",),
    )

    with pytest.raises(SystemExit, match="Production/Stable"):
        validate_release_metadata(metadata)


def test_release_metadata_rejects_mismatched_stable_release_dates() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")
    metadata = replace(metadata, citation_date="2026-07-21")

    with pytest.raises(SystemExit, match="release date mismatch"):
        validate_release_metadata(metadata)


def test_release_metadata_rejects_missing_stable_release_dates() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")
    metadata = replace(metadata, citation_date=None, changelog_release_dates=())

    with pytest.raises(SystemExit, match="exactly one dated CHANGELOG"):
        validate_release_metadata(metadata)


def test_release_metadata_rejects_invalid_stable_release_date() -> None:
    metadata = read_release_metadata(root=Path("."), ref_name="v2.0.0")
    metadata = replace(
        metadata,
        citation_date="2026-99-99",
        changelog_release_dates=(("2.0.0", "2026-99-99"),),
    )

    with pytest.raises(SystemExit, match="not a valid ISO date"):
        validate_release_metadata(metadata)
