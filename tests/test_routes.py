# tests/test_routes.py
import os
import shutil
import tempfile
from pathlib import Path
import pytest

# ----------------------------------------------------------------------
# Helper
# ----------------------------------------------------------------------
NOTE_TEMPLATE = """---
title: {title}
tags: [public, {extra_tag}]
created: {created}
---

# {title}

This is a test note. It contains **bold** text and a list:

- Item 1
- Item 2
"""


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(scope="function")
def temp_vault():
    """Create a temp vault directory structure."""
    base = Path(tempfile.mkdtemp())
    notes_dir = base / "1 Everything/0 Notes"
    contents_dir = base / "1 Everything/2 Contents"

    notes_dir.mkdir(parents=True)
    (contents_dir / "books").mkdir(parents=True)
    (contents_dir / "movies").mkdir(parents=True)
    (contents_dir / "series").mkdir(parents=True)

    note1 = NOTE_TEMPLATE.format(title="Public Note One", extra_tag="demo", created="2026-04-16 23:00:38+08:00")
    note2 = NOTE_TEMPLATE.format(title="Public Note Two", extra_tag="example", created="2026-01-22 16:03:43+08:00")
    (notes_dir / "public_note_one.md").write_text(note1, encoding="utf-8")
    (notes_dir / "public_note_two.md").write_text(note2, encoding="utf-8")

    review = """---
title: Book Review Sample
author: Jane Doe
personalRating: 8.5
created: 2026-02-01 12:00:00+08:00
---
This is a dummy review.
"""
    (contents_dir / "books" / "book_review_sample.md").write_text(review, encoding="utf-8")

    yield {"VAULT_ROOT": str(base)}

    shutil.rmtree(str(base))


@pytest.fixture(scope="function")
def client(temp_vault, monkeypatch):
    """Build TestClient with a temp config pointing to the temp vault."""
    import yaml
    from fastapi.testclient import TestClient

    cfg_path = Path(tempfile.mkdtemp()) / "config.yaml"
    cfg = {
        "vault_root": temp_vault["VAULT_ROOT"],
        "notes_dir": "1 Everything/0 Notes",
        "contents_dir": "1 Everything/2 Contents",
        "services": {},
    }
    cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

    monkeypatch.setenv("SERVER_DASHBOARD_CONFIG", str(cfg_path))

    # Clear content cache before each test
    import server_dashboard.content_service as cs
    cs._CONTENT_CACHE.clear()

    # Import main AFTER env var is set
    import importlib
    import server_dashboard.main as main_mod
    importlib.reload(main_mod)

    return TestClient(main_mod.app)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_root_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text


def test_notes_page_lists_public_notes(client):
    resp = client.get("/notes")
    assert resp.status_code == 200
    html = resp.text
    assert "public_note_one" in html
    assert "public_note_two" in html


def test_individual_note_page(client):
    notes_resp = client.get("/notes")
    assert notes_resp.status_code == 200
    import re
    m = re.search(r'href="/note/([^\"]+)"', notes_resp.text)
    assert m, "No note slug found"
    slug = m.group(1)
    detail = client.get(f"/note/{slug}")
    assert detail.status_code == 200
    html = detail.text
    assert "Item 1" in html and "Item 2" in html


def test_reviews_page_returns_200(client):
    resp = client.get("/reviews")
    assert resp.status_code == 200
    html = resp.text
    assert "Book Review Sample" in html