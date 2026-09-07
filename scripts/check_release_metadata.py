from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


@dataclass(frozen=True)
class ReleaseMetadata:
    tag_version: str
    base_version: str
    pyproject_version: str
    runtime_version: str | None
    citation_version: str | None
    citation_date: str | None
    development_statuses: tuple[str, ...]
    changelog_versions: tuple[str, ...]
    changelog_release_dates: tuple[tuple[str, str], ...]
    is_prerelease: bool
    prerelease_label: str


def read_release_metadata(root: Path, ref_name: str) -> ReleaseMetadata:
    tag_version = ref_name.removeprefix("v")
    base_version, separator, prerelease_label = tag_version.partition("-")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    pyproject_version = project["version"]
    development_statuses = tuple(
        classifier for classifier in project.get("classifiers", []) if classifier.startswith("Development Status ::")
    )

    init_text = (root / "scholaraio" / "__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)

    cff_text = (root / "CITATION.cff").read_text(encoding="utf-8")
    cff_match = re.search(r'^version:\s*"?([^"\n]+)"?\s*$', cff_text, re.MULTILINE)
    cff_date_match = re.search(r'^date-released:\s*"?([^"\n]+)"?\s*$', cff_text, re.MULTILINE)
    changelog_text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog_versions = tuple(re.findall(r"^## \[([^]]+)]", changelog_text, re.MULTILINE))
    changelog_release_dates = tuple(
        re.findall(r"^## \[([^]]+)]\s+—\s+(\d{4}-\d{2}-\d{2})\s*$", changelog_text, re.MULTILINE)
    )

    return ReleaseMetadata(
        tag_version=tag_version,
        base_version=base_version,
        pyproject_version=pyproject_version,
        runtime_version=init_match.group(1) if init_match else None,
        citation_version=cff_match.group(1).strip() if cff_match else None,
        citation_date=cff_date_match.group(1).strip() if cff_date_match else None,
        development_statuses=development_statuses,
        changelog_versions=changelog_versions,
        changelog_release_dates=changelog_release_dates,
        is_prerelease=bool(separator),
        prerelease_label=prerelease_label,
    )


def validate_release_metadata(metadata: ReleaseMetadata) -> None:
    versions = {
        "tag": metadata.base_version,
        "pyproject": metadata.pyproject_version,
        "runtime": metadata.runtime_version,
        "citation": metadata.citation_version,
    }
    mismatches = [f"{name}={value}" for name, value in versions.items() if value != metadata.pyproject_version]
    if mismatches:
        raise SystemExit(
            "Release metadata mismatch detected. Expected all versions to equal "
            f"{metadata.pyproject_version}, got: {', '.join(mismatches)}"
        )

    changelog_section_count = metadata.changelog_versions.count(metadata.tag_version)
    if changelog_section_count != 1:
        raise SystemExit(
            f"Release tag {metadata.tag_version} requires exactly one matching CHANGELOG.md section; "
            f"got: {changelog_section_count}"
        )

    stable_classifier = "Development Status :: 5 - Production/Stable"
    if not metadata.is_prerelease and metadata.development_statuses != (stable_classifier,):
        statuses = ", ".join(metadata.development_statuses) or "missing"
        raise SystemExit(
            f"Stable releases require exactly one Production/Stable development classifier; got: {statuses}"
        )

    if not metadata.is_prerelease:
        changelog_dates = [
            release_date
            for version, release_date in metadata.changelog_release_dates
            if version == metadata.tag_version
        ]
        if len(changelog_dates) != 1:
            raise SystemExit(
                f"Stable release {metadata.tag_version} requires exactly one dated CHANGELOG.md section; "
                f"got: {len(changelog_dates)}"
            )

        changelog_date = changelog_dates[0]
        if metadata.citation_date != changelog_date:
            raise SystemExit(
                "Stable release date mismatch. Expected CITATION.cff and CHANGELOG.md to agree, "
                f"got citation={metadata.citation_date}, changelog={changelog_date}"
            )

        try:
            date.fromisoformat(changelog_date)
        except ValueError as exc:
            raise SystemExit(f"Stable release date is not a valid ISO date: {changelog_date}") from exc


def write_github_outputs(metadata: ReleaseMetadata, output_path: str | None) -> None:
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"is_prerelease={'true' if metadata.is_prerelease else 'false'}\n")
        fh.write(f"tag_version={metadata.tag_version}\n")
        fh.write(f"base_version={metadata.base_version}\n")


def main() -> None:
    metadata = read_release_metadata(Path("."), os.environ["GITHUB_REF_NAME"])
    validate_release_metadata(metadata)
    write_github_outputs(metadata, os.environ.get("GITHUB_OUTPUT"))

    if metadata.is_prerelease:
        print(
            f"Prerelease tag {metadata.tag_version} aligned with base package version "
            f"{metadata.pyproject_version} ({metadata.prerelease_label})"
        )
    else:
        print(f"Release metadata aligned at version {metadata.pyproject_version}")


if __name__ == "__main__":
    main()
