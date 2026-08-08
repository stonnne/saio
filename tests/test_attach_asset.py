"""Tests for the attach-asset CLI command.

These cover the behavior that makes attach-asset distinct from attach-pdf:
supplementary assets merge *into* the shared images/ directory and must never
disturb the files paper.md already references.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scholaraio.interfaces.cli.attach_asset import (
    cmd_attach_asset,
    find_mineru_images_dir,
    merge_asset_images,
    rewrite_image_refs,
    sanitize_asset_name,
    unresolved_image_refs,
)


def _paper_dir(tmp_path: Path) -> Path:
    paper_d = tmp_path / "Ji-2021-Brain-microvasculature"
    (paper_d / "images").mkdir(parents=True)
    (paper_d / "paper.md").write_text("![](images/existing.jpg)\n", encoding="utf-8")
    (paper_d / "images" / "existing.jpg").write_bytes(b"paper-body-image")
    return paper_d


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(
        ingest=SimpleNamespace(
            mineru_endpoint="http://localhost:8000",
            mineru_backend_local="pipeline",
            mineru_model_version_cloud="pipeline",
            mineru_lang="en",
            mineru_parse_method="auto",
            mineru_enable_formula=True,
            mineru_enable_table=True,
            mineru_poll_timeout=900,
            chunk_page_limit=100,
            pdf_preferred_parser="mineru",
            pdf_fallback_order=None,
            pdf_fallback_auto_detect=True,
        ),
        resolved_mineru_api_key=lambda: "test-key",
    )


# --------------------------------------------------------------------------
#  merge_asset_images
# --------------------------------------------------------------------------


def test_merge_asset_images_copies_new_files_and_preserves_existing(tmp_path):
    paper_d = _paper_dir(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "abc123.jpg").write_bytes(b"new-asset-image")

    mapping = merge_asset_images(src, paper_d / "images")

    assert mapping == {"abc123.jpg": "abc123.jpg"}
    assert (paper_d / "images" / "abc123.jpg").read_bytes() == b"new-asset-image"
    # The paper body's own image must survive untouched.
    assert (paper_d / "images" / "existing.jpg").read_bytes() == b"paper-body-image"


def test_merge_asset_images_reuses_identical_existing_file(tmp_path):
    paper_d = _paper_dir(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "existing.jpg").write_bytes(b"paper-body-image")

    mapping = merge_asset_images(src, paper_d / "images")

    assert mapping == {"existing.jpg": "existing.jpg"}
    assert len(list((paper_d / "images").iterdir())) == 1


def test_merge_asset_images_never_overwrites_on_name_collision(tmp_path):
    """A same-name/different-bytes asset must land under a content-hash name.

    Overwriting here would silently corrupt an image paper.md already renders.
    """
    paper_d = _paper_dir(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "existing.jpg").write_bytes(b"different-asset-image")

    mapping = merge_asset_images(src, paper_d / "images")

    expected = hashlib.sha256(b"different-asset-image").hexdigest() + ".jpg"
    assert mapping == {"existing.jpg": expected}
    assert (paper_d / "images" / "existing.jpg").read_bytes() == b"paper-body-image"
    assert (paper_d / "images" / expected).read_bytes() == b"different-asset-image"


def test_merge_asset_images_handles_missing_source_dir(tmp_path):
    paper_d = _paper_dir(tmp_path)
    assert merge_asset_images(None, paper_d / "images") == {}


def test_find_mineru_images_dir_accepts_stem_prefixed_variants(tmp_path):
    md_path = tmp_path / "supplementary.md"
    md_path.write_text("x", encoding="utf-8")
    variant = tmp_path / "supplementary_mineru_images"
    variant.mkdir()
    (variant / "a.jpg").write_bytes(b"a")

    assert find_mineru_images_dir(md_path) == variant


# --------------------------------------------------------------------------
#  rewrite_image_refs / unresolved_image_refs
# --------------------------------------------------------------------------


def test_rewrite_image_refs_maps_known_names_and_leaves_others(tmp_path):
    md = "![Fig S1](images/abc.jpg)\n\n![Fig S2](other/unknown.jpg)\n"

    out = rewrite_image_refs(md, {"abc.jpg": "renamed.jpg"})

    assert "![Fig S1](images/renamed.jpg)" in out
    assert "![Fig S2](other/unknown.jpg)" in out


def test_unresolved_image_refs_reports_only_missing_files(tmp_path):
    paper_d = _paper_dir(tmp_path)
    md = "![](images/existing.jpg)\n![](images/gone.jpg)\n"

    assert unresolved_image_refs(md, paper_d) == ["images/gone.jpg"]


# --------------------------------------------------------------------------
#  sanitize_asset_name
# --------------------------------------------------------------------------


def test_sanitize_asset_name_normalizes_unsafe_characters():
    assert sanitize_asset_name("supplementary") == "supplementary"
    assert sanitize_asset_name("Supp Data (final)") == "Supp-Data-final"
    assert sanitize_asset_name("../../etc/passwd") == "etc-passwd"


@pytest.mark.parametrize("bad", ["", "   ", "---", "paper", "PAPER", "meta"])
def test_sanitize_asset_name_rejects_empty_and_reserved_names(bad):
    with pytest.raises(ValueError):
        sanitize_asset_name(bad)


# --------------------------------------------------------------------------
#  cmd_attach_asset
# --------------------------------------------------------------------------


def _args(paper_d: Path, asset: Path, **kw) -> SimpleNamespace:
    return SimpleNamespace(
        paper_id=paper_d.name,
        asset_path=str(asset),
        name=kw.get("name"),
        dry_run=kw.get("dry_run", False),
        force=kw.get("force", False),
    )


@pytest.fixture()
def ui_output(monkeypatch) -> list[str]:
    """Capture CLI user-facing output, which goes through compat.ui, not stdout."""
    messages: list[str] = []
    monkeypatch.setattr("scholaraio.interfaces.cli.compat.ui", lambda msg="": messages.append(str(msg)))
    return messages


@pytest.fixture()
def patched_resolve(monkeypatch):
    def _apply(paper_d: Path) -> None:
        monkeypatch.setattr(
            "scholaraio.interfaces.cli.attach_asset._resolve_paper",
            lambda _paper_id, _cfg: paper_d,
        )

    return _apply


def test_cmd_attach_asset_dry_run_writes_nothing(tmp_path, patched_resolve, ui_output):
    paper_d = _paper_dir(tmp_path)
    asset = tmp_path / "supplementary.pdf"
    asset.write_bytes(b"%PDF-1.4")
    patched_resolve(paper_d)
    before = sorted(p.name for p in paper_d.rglob("*"))

    cmd_attach_asset(_args(paper_d, asset, dry_run=True), _cfg())

    assert sorted(p.name for p in paper_d.rglob("*")) == before
    out = "\n".join(ui_output)
    assert "[dry-run]" in out
    assert "1 existing files are preserved" in out


def test_cmd_attach_asset_rejects_non_pdf(tmp_path, patched_resolve, ui_output):
    paper_d = _paper_dir(tmp_path)
    asset = tmp_path / "supplementary-data.xlsx"
    asset.write_bytes(b"PK\x03\x04")
    patched_resolve(paper_d)

    with pytest.raises(SystemExit) as exc:
        cmd_attach_asset(_args(paper_d, asset), _cfg())

    assert exc.value.code == 1
    assert "PDF only" in "\n".join(ui_output)


def test_cmd_attach_asset_refuses_existing_markdown_without_force(tmp_path, patched_resolve, ui_output):
    paper_d = _paper_dir(tmp_path)
    (paper_d / "supplementary.md").write_text("keep me", encoding="utf-8")
    asset = tmp_path / "supplementary.pdf"
    asset.write_bytes(b"%PDF-1.4")
    patched_resolve(paper_d)

    with pytest.raises(SystemExit) as exc:
        cmd_attach_asset(_args(paper_d, asset), _cfg())

    assert exc.value.code == 1
    assert "--force" in "\n".join(ui_output)
    assert (paper_d / "supplementary.md").read_text(encoding="utf-8") == "keep me"


def test_cmd_attach_asset_converts_and_merges_images(tmp_path, patched_resolve, monkeypatch, ui_output):
    paper_d = _paper_dir(tmp_path)
    asset = tmp_path / "supplementary.pdf"
    asset.write_bytes(b"%PDF-1.4")
    patched_resolve(paper_d)

    def fake_convert(pdf_path, out_dir, cfg):
        md_path = out_dir / "supplementary.md"
        md_path.write_text("![Fig S1](images/fig1.jpg)\n", encoding="utf-8")
        images = out_dir / "images"
        images.mkdir()
        (images / "fig1.jpg").write_bytes(b"supplement-figure")
        return SimpleNamespace(success=True, md_path=md_path, error=None)

    monkeypatch.setattr("scholaraio.interfaces.cli.attach_asset._convert_asset_pdf", fake_convert)

    cmd_attach_asset(_args(paper_d, asset), _cfg())

    out_md = paper_d / "supplementary.md"
    assert out_md.read_text(encoding="utf-8") == "![Fig S1](images/fig1.jpg)\n"
    assert (paper_d / "supplementary.pdf").exists()
    assert (paper_d / "images" / "fig1.jpg").read_bytes() == b"supplement-figure"
    # paper.md's asset is still intact — the core attach-pdf hazard.
    assert (paper_d / "images" / "existing.jpg").read_bytes() == b"paper-body-image"
    assert "Merged 1 images" in "\n".join(ui_output)


def test_cmd_attach_asset_does_not_reindex(tmp_path, patched_resolve, monkeypatch):
    """Assets are not search bodies; embedding/indexing must stay untouched."""
    paper_d = _paper_dir(tmp_path)
    asset = tmp_path / "supplementary.pdf"
    asset.write_bytes(b"%PDF-1.4")
    patched_resolve(paper_d)

    def fake_convert(pdf_path, out_dir, cfg):
        md_path = out_dir / "supplementary.md"
        md_path.write_text("no images\n", encoding="utf-8")
        return SimpleNamespace(success=True, md_path=md_path, error=None)

    monkeypatch.setattr("scholaraio.interfaces.cli.attach_asset._convert_asset_pdf", fake_convert)

    called: list[str] = []
    monkeypatch.setattr(
        "scholaraio.services.ingest.pipeline.step_embed",
        lambda *a, **k: called.append("embed"),
    )
    monkeypatch.setattr(
        "scholaraio.services.ingest.pipeline.step_index",
        lambda *a, **k: called.append("index"),
    )

    cmd_attach_asset(_args(paper_d, asset), _cfg())

    assert called == []
