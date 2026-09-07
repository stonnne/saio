"""Incremental refresh must remove deleted papers without re-embedding survivors."""

from __future__ import annotations

import json
import shutil
import sqlite3

import pytest

from scholaraio.services import index, vectors


@pytest.fixture()
def embedded_library(tmp_papers, tmp_db, monkeypatch):
    calls = []

    def embed(texts, cfg=None):
        calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(vectors, "_embed_batch", embed)
    index.build_index(tmp_papers, tmp_db)
    vectors.build_vectors(tmp_papers, tmp_db)
    vectors._build_faiss_index(tmp_db)
    calls.clear()
    return calls


@pytest.mark.parametrize("add_paper", [False, True])
def test_refresh_prunes_deleted_papers_and_preserves_survivor_vectors(tmp_papers, tmp_db, embedded_library, add_paper):
    with sqlite3.connect(tmp_db) as conn:
        surviving_vector = conn.execute("SELECT embedding FROM paper_vectors WHERE paper_id = 'bbbb-2222'").fetchone()[
            0
        ]
    shutil.rmtree(tmp_papers / "Smith-2023-Turbulence")
    expected_ids = {"bbbb-2222"}
    if add_paper:
        new = tmp_papers / "New-Paper"
        new.mkdir()
        (new / "meta.json").write_text(json.dumps({"id": "new-paper", "title": "New paper"}))
        expected_ids.add("new-paper")

    assert index.build_index(tmp_papers, tmp_db) == int(add_paper)
    assert vectors.build_vectors(tmp_papers, tmp_db) == int(add_paper)
    assert embedded_library == ([["New paper"]] if add_paper else [])
    assert index.search("turbulence", tmp_db) == []
    assert index.search("deep learning", tmp_db)[0]["paper_id"] == "bbbb-2222"
    _, faiss_ids = vectors._build_faiss_index(tmp_db)
    assert set(faiss_ids) == expected_ids
    with sqlite3.connect(tmp_db) as conn:
        for table, key in [
            ("papers", "paper_id"),
            ("papers_hash", "paper_id"),
            ("papers_registry", "id"),
            ("paper_vectors", "paper_id"),
        ]:
            assert {r[0] for r in conn.execute(f"SELECT {key} FROM {table}")} == expected_ids
        assert (
            conn.execute("SELECT embedding FROM paper_vectors WHERE paper_id = 'bbbb-2222'").fetchone()[0]
            == surviving_vector
        )


def test_refresh_reconciles_citation_sources_and_targets(tmp_papers, tmp_db):
    first = tmp_papers / "Smith-2023-Turbulence" / "meta.json"
    second = tmp_papers / "Wang-2024-DeepLearning" / "meta.json"
    a, b = json.loads(first.read_text()), json.loads(second.read_text())
    a["references"] = ["10.1234/outside"]
    b["references"] = [a["doi"]]
    first.write_text(json.dumps(a))
    second.write_text(json.dumps(b))
    index.build_index(tmp_papers, tmp_db)
    shutil.rmtree(first.parent)
    index.build_index(tmp_papers, tmp_db)
    with sqlite3.connect(tmp_db) as conn:
        assert conn.execute("SELECT source_id, target_doi, target_id FROM citations").fetchall() == [
            ("bbbb-2222", a["doi"], None)
        ]
    b["references"] = []
    second.write_text(json.dumps(b))
    index.build_index(tmp_papers, tmp_db)
    with sqlite3.connect(tmp_db) as conn:
        assert conn.execute("SELECT count(*) FROM citations").fetchone()[0] == 0


@pytest.mark.parametrize("builder,table", [(index.build_index, "papers"), (vectors.build_vectors, "paper_vectors")])
def test_unreadable_metadata_does_not_prune_existing_entries(tmp_papers, tmp_db, embedded_library, builder, table):
    (tmp_papers / "Smith-2023-Turbulence" / "meta.json").write_text("{broken")
    builder(tmp_papers, tmp_db)
    with sqlite3.connect(tmp_db) as conn:
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 2
    assert embedded_library == []


@pytest.mark.parametrize("builder,table", [(index.build_index, "papers"), (vectors.build_vectors, "paper_vectors")])
def test_missing_root_does_not_clear_existing_index(tmp_papers, tmp_db, embedded_library, builder, table):
    with pytest.raises(FileNotFoundError):
        builder(tmp_papers / "missing", tmp_db)
    with sqlite3.connect(tmp_db) as conn:
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 2


def test_empty_library_clears_vectors_without_embedding(tmp_papers, tmp_db, embedded_library):
    for paper in tmp_papers.iterdir():
        shutil.rmtree(paper)
    assert vectors.build_vectors(tmp_papers, tmp_db) == 0
    assert embedded_library == []
    assert all(not path.exists() for path in vectors._faiss_paths(tmp_db))
    with sqlite3.connect(tmp_db) as conn:
        assert conn.execute("SELECT count(*) FROM paper_vectors").fetchone()[0] == 0
