# tests/test_routes.py
import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# ----------------------------------------------------------------------
# Helper: build a tiny markdown note with front‑matter
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
# Pytest fixture: temporary Obsidian vault with a couple of notes
# ----------------------------------------------------------------------
@pytest.fixture(scope="function")
def temp_vault():
    """
    Creates a temporary directory that mimics the structure of the real vault:

        <tmp>/1 Everything/0 Notes/
        <tmp>/1 Everything/2 Contents/books/
        <tmp>/1 Everything/2 Contents/movies/
        <tmp>/1 Everything/2 Contents/series/

    Returns a dict with the paths so the test can monkey‑patch the module.
    """
    base = Path(tempfile.mkdtemp())
    notes_dir = base / "1 Everything/0 Notes"
    contents_dir = base / "1 Everything/2 Contents"

    # create required sub‑folders
    notes_dir.mkdir(parents=True)
    (contents_dir / "books").mkdir(parents=True)
    (contents_dir / "movies").mkdir(parents=True)
    (contents_dir / "series").mkdir(parents=True)

    # ---- two public notes ------------------------------------------------
    note1 = NOTE_TEMPLATE.format(
        title="Public Note One",
        extra_tag="demo",
        created="2026-04-16 23:00:38+08:00",
    )
    note2 = NOTE_TEMPLATE.format(
        title="Public Note Two",
        extra_tag="example",
        created="2026-01-22 16:03:43+08:00",
    )
    (notes_dir / "public_note_one.md").write_text(note1, encoding="utf-8")
    (notes_dir / "public_note_two.md").write_text(note2, encoding="utf-8")

    # ---- one review file (books) ----------------------------------------
    review_md = """---
title: Book Review Sample
author: Jane Doe
personalRating: 8.5
created: 2026-02-01 12:00:00+08:00
year: 2020
---
This is a dummy review.
"""
    (contents_dir / "books" / "book_review_sample.md").write_text(review_md, encoding="utf-8")

    yield {
        "BASE": str(base),
        "NOTES_DIR": str(notes_dir),
        "CONTENTS_DIR": str(contents_dir),
    }

    # Cleanup after the test
    shutil.rmtree(str(base))

# ----------------------------------------------------------------------
# Import the FastAPI app **after** the fixture is defined – we will monkey‑patch
# the module‑level constants before instantiating the client.
# ----------------------------------------------------------------------
@pytest.fixture(scope="function")
def client(temp_vault, monkeypatch):
    """Patch paths in `server_dashboard.main` and return a TestClient."""
    import importlib
    # Import the module *first* to get a handle, then reload so that the module-level constants are re‑evaluated.
    import server_dashboard.main as main_mod
    importlib.reload(main_mod)
    # Now patch the absolute paths the module uses.
    monkeypatch.setattr(main_mod, "NOTES_DIR", temp_vault["NOTES_DIR"])
    monkeypatch.setattr(main_mod, "CONTENTS_DIR", temp_vault["CONTENTS_DIR"])
    # Return a TestClient bound to the patched app instance.
    return TestClient(main_mod.app)

# Actual tests
# ----------------------------------------------------------------------
def test_root_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text

def test_notes_page_lists_public_notes(client):
    resp = client.get("/notes")
    assert resp.status_code == 200
    html = resp.text
    # Titles must appear (display titles are derived from filenames)
    assert "public_note_one" in html
    assert "public_note_two" in html

    assert "April 16, 2026, 11:00 PM +0800" in html
    assert "January 22, 2026, 04:03 PM +0800" in html

def test_individual_note_page(client):
    # discover a slug from the notes list
    notes_resp = client.get("/notes")
    assert notes_resp.status_code == 200
    import re
    m = re.search(r'href="/note/([^\"]+)"', notes_resp.text)
    assert m, "No note slug found"
    slug = m.group(1)
    detail = client.get(f"/note/{slug}")
    assert detail.status_code == 200
    html = detail.text
    # body content
    assert "Item 1" in html and "Item 2" in html
    # date appears
    assert "January 22, 2026, 04:03 PM +0800" in html or "April 16, 2026, 11:00 PM +0800" in html

def test_reviews_page_returns_200(client):
    resp = client.get("/reviews")
    assert resp.status_code == 200
    html = resp.text
    assert "Book Review Sample" in html
    # Title appears (already asserted above)
    # assert "2026-02-01 12:00:00+08:00" in html

