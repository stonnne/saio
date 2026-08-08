"""Contract tests for BibTeX export.

Verifies: given well-formed metadata, export produces valid BibTeX.
Does NOT test: internal helper functions, exact string formatting.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from scholaraio.services.export import export_bibtex, meta_to_bibtex


class TestMetaToBibtex:
    """Single-entry BibTeX conversion contract."""

    def test_journal_article_has_required_fields(self):
        meta = {
            "title": "Some Title",
            "authors": ["Alice", "Bob"],
            "year": 2023,
            "journal": "Nature",
            "doi": "10.1234/test",
            "paper_type": "journal-article",
            "first_author_lastname": "Alice",
        }
        bib = meta_to_bibtex(meta)
        assert bib.startswith("@article{")
        assert "Some Title" in bib
        assert "author = {Alice and Bob}" in bib
        assert "year = {2023}" in bib
        assert "doi = {10.1234/test}" in bib

    def test_thesis_maps_to_phdthesis(self):
        meta = {
            "title": "My Thesis",
            "authors": ["Grad Student"],
            "year": 2024,
            "paper_type": "thesis",
            "first_author_lastname": "Student",
        }
        bib = meta_to_bibtex(meta)
        assert bib.startswith("@phdthesis{")

    def test_special_chars_escaped(self):
        meta = {
            "title": "CO2 & H2O: 50% of the #1 problem",
            "authors": [],
            "first_author_lastname": "Test",
        }
        bib = meta_to_bibtex(meta)
        assert "\\&" in bib
        assert "\\%" in bib
        assert "\\#" in bib

    def test_string_authors_and_numeric_fields_are_normalized(self):
        meta = {
            "title": "Robust metadata",
            "authors": "Doe, Jane and Roe, Alex",
            "first_author_lastname": "Doe",
            "year": 2026,
            "journal": "Journal of Tests",
            "volume": 12,
            "issue": 3,
            "pages": 42,
            "paper_type": "journal-article",
        }

        bib = meta_to_bibtex(meta)

        assert "author = {Doe, Jane and Roe, Alex}" in bib
        assert "D and o and e" not in bib
        assert "volume = {12}" in bib
        assert "number = {3}" in bib
        assert "pages = {42}" in bib

    def test_conference_paper_includes_booktitle(self):
        bib = meta_to_bibtex(
            {
                "title": "Conference result",
                "authors": ["Pat Chen"],
                "year": 2026,
                "paper_type": "ConferencePaper",
                "booktitle": "Proceedings of Tests",
                "first_author_lastname": "Chen",
            }
        )

        assert bib.startswith("@inproceedings{")
        assert "booktitle = {Proceedings of Tests}" in bib


class TestExportBibtex:
    """Batch export contract: filters work, output is concatenated entries."""

    def test_export_all(self, tmp_papers):
        result = export_bibtex(tmp_papers)
        assert "@article{" in result
        assert "@phdthesis{" in result

    def test_filter_by_year(self, tmp_papers):
        result = export_bibtex(tmp_papers, year="2024")
        assert "Deep learning" in result
        assert "Turbulence" not in result

    def test_filter_by_journal(self, tmp_papers):
        result = export_bibtex(tmp_papers, journal="Fluid Mechanics")
        assert "Turbulence" in result
        assert "Deep learning" not in result

    def test_filter_by_paper_type(self, tmp_papers):
        result = export_bibtex(tmp_papers, paper_type="THES")
        assert "Deep learning" in result
        assert "Turbulence" not in result

    def test_filter_by_paper_ids(self, tmp_papers):
        result = export_bibtex(tmp_papers, paper_ids=["Smith-2023-Turbulence"])
        assert "Turbulence" in result
        assert "Deep learning" not in result

    def test_empty_result_returns_empty_string(self, tmp_papers):
        result = export_bibtex(tmp_papers, year="1900")
        assert result == ""


def _write_paper(papers_dir: Path, dir_name: str, meta: dict) -> None:
    """Write a minimal paper directory so export_bibtex picks it up."""
    d = papers_dir / dir_name
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def _cite_keys(bibtex: str) -> list[str]:
    return re.findall(r"^@\w+\{([^,]+),", bibtex, re.M)


class TestCiteKeyUniqueness:
    """Every entry in one export must carry a distinct key.

    BibTeX keeps a single entry per key, so a duplicate silently points every
    ``\\cite`` at the same paper (and biber fails outright) -- a real library hit
    both failure modes below: two Murray 1926 PNAS papers, and two Chinese-language
    articles whose keys degenerated to the bare year ``2022``.
    """

    def test_same_author_year_and_title_word_get_distinct_keys(self, tmp_path: Path):
        papers_dir = tmp_path / "papers"
        papers_dir.mkdir()
        for n, subtitle in ((1, "part one"), (2, "part two")):
            _write_paper(
                papers_dir,
                f"Murray-1926-Physiological-{n}",
                {
                    "title": f"The Physiological Principle of Minimum Work, {subtitle}",
                    "authors": ["Cecil D. Murray"],
                    "first_author_lastname": "Murray",
                    "year": 1926,
                    "paper_type": "journal-article",
                },
            )

        keys = _cite_keys(export_bibtex(papers_dir))

        assert len(keys) == 2
        assert len(set(keys)) == 2
        assert sorted(keys) == ["Murray1926Physiologicala", "Murray1926Physiologicalb"]

    def test_non_latin_names_do_not_collapse_to_the_bare_year(self, tmp_path: Path):
        papers_dir = tmp_path / "papers"
        papers_dir.mkdir()
        for n, (title, author) in enumerate(
            (("基于等效孔隙网络模型的水动力弥散数值模拟", "张兴昊"), ("中国脑科学计划进展", "陆林")),
        ):
            _write_paper(
                papers_dir,
                f"CJK-2022-{n}",
                {
                    "title": title,
                    "authors": [author],
                    "first_author_lastname": author,
                    "year": 2022,
                    "paper_type": "journal-article",
                },
            )

        keys = _cite_keys(export_bibtex(papers_dir))

        assert len(set(keys)) == 2
        # A bare year is what the old key builder produced once the non-Latin
        # characters were stripped away.
        assert not any(key.strip("ab") == "2022" for key in keys)

    def test_keys_that_were_already_unique_are_left_alone(self, tmp_papers: Path):
        keys = _cite_keys(export_bibtex(tmp_papers))

        assert len(set(keys)) == len(keys)
        assert not any(key.endswith(("a", "b")) and key[:-1] in keys for key in keys)

    def test_export_is_reproducible(self, tmp_papers: Path):
        assert export_bibtex(tmp_papers) == export_bibtex(tmp_papers)
