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

    yield {
        "NOTES_DIR": str(notes_dir),
        "CONTENTS_DIR": str(contents_dir),
        "FILES_DIR": str(base / "4 Files"),
    }

    shutil.rmtree(str(base))


@pytest.fixture(scope="function")
def client(temp_vault, monkeypatch):
    """Build TestClient with a temp config pointing to the temp vault."""
    import yaml
    from fastapi.testclient import TestClient

    cfg_path = Path(tempfile.mkdtemp()) / "config.yaml"
    cfg = {
        "site": {"name": "Test Homelab"},
        "markdown": {
            "notes_dir": temp_vault["NOTES_DIR"],
            "contents_dir": temp_vault["CONTENTS_DIR"],
            "attachments_dir": temp_vault["FILES_DIR"],
            "public_tag": "public",
            "private_tag": "private",
        },
        "services": {},
        "profile": {
            "github": {"username": "tony", "hide_repos": []},
            "email": "tony@example.com",
            "linkedin": "https://linkedin.com/in/tony",
            "messenger": "https://m.me/tony",
            "phone": "+63 900 000 0000",
        },
        "terminal": {"user": "tony", "host": "linux", "cow_message": "howdy",
                     "shell": "fish", "type_duration_ms": 1500},
    }
    cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")

    monkeypatch.setenv("SERVER_DASHBOARD_CONFIG", str(cfg_path))

    # Import from project root (directory has hyphen — Python can't import
    # 'thonystank-homelab' as a package, so we add project root to path)
    import sys
    import os
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    import content_service as cs
    cs._CONTENT_CACHE.clear()

    import monitoring_service as ms
    ms._status_cache["data"] = None
    ms._status_cache["ts"] = 0.0

    import importlib
    import main as main_mod
    importlib.reload(main_mod)

    return TestClient(main_mod.app)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_root_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Services" in resp.text and "Explore" in resp.text
    assert "Test Homelab" in resp.text               # site name from config
    assert "tony@linux — fish" in resp.text          # terminal identity from config
    assert "\\uf31a" in resp.text                   # Tux OS icon (JS escape in source)
    assert '"cow_message": "howdy"' in resp.text    # cowsay text from config
    assert '"type_duration_ms": 1500' in resp.text  # typing duration from config

def test_dashboard_route_removed(client):
    assert client.get("/dashboard").status_code == 404

def test_resume_missing_returns_404(client):
    """Temp config has no resume_path → /resume 404s and about hides the section."""
    assert client.get("/resume").status_code == 404
    assert "<iframe" not in client.get("/about").text


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

def test_debug_attachments_route_removed(client):
    assert client.get("/debug/attachments").status_code == 404

def test_linkedin_api_removed(client):
    assert client.get("/api/linkedin").status_code == 404

def test_about_page_renders(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    assert 'id="ff-panel-body"' in resp.text          # fastfetch profile panel container
    assert "tony@linux" in resp.text                  # panel title from terminal config
    assert "More active on GitHub" not in resp.text   # note bubble removed
    assert "tony@example.com" in resp.text            # email from contact config

def test_hide_repos_normalization():
    from github_service import _normalize_repo_filters, _repo_hidden
    assert _normalize_repo_filters(["https://github.com/Add852/thonystank-homelab", "Other-Repo/"]) == {"thonystank-homelab", "other-repo"}
    assert _repo_hidden("thonystank-homelab", {"thonystank-homelab"})
    assert _repo_hidden("someuser/thonystank-homelab", {"thonystank-homelab"})
    assert not _repo_hidden("other-name", {"thonystank-homelab"})

def test_attachments_gated_by_embeds(client, temp_vault):
    """Only files embedded (![[...]]) in public/private notes may be served."""
    files_dir = Path(temp_vault["FILES_DIR"])
    files_dir.mkdir(parents=True, exist_ok=True)
    (files_dir / "secret.txt").write_text("private stuff", encoding="utf-8")
    (files_dir / "public-pic.png").write_text("fake png", encoding="utf-8")
    (files_dir / "private-pic.png").write_text("fake png", encoding="utf-8")

    # Exists on disk but not embedded anywhere → 404
    assert client.get("/static/attachments/secret.txt").status_code == 404

    notes_dir = Path(temp_vault["NOTES_DIR"])
    (notes_dir / "with_pic.md").write_text(
        "---\ntags: [public]\ncreated: 2026-01-01 10:00:00+08:00\n---\n![[public-pic.png]]\n",
        encoding="utf-8",
    )
    (notes_dir / "private_pic.md").write_text(
        "---\ntags: [private]\ncreated: 2026-01-02 10:00:00+08:00\n---\n![[private-pic.png]]\n",
        encoding="utf-8",
    )

    assert client.get("/static/attachments/public-pic.png").status_code == 200
    assert client.get("/static/attachments/private-pic.png").status_code == 200

def test_service_status_cached(client):
    """Second call within TTL returns the cached dict (same object)."""
    import monitoring_service as ms
    first = ms.get_service_status({"services": {}})
    second = ms.get_service_status({"services": {"whatever": {"port": 1}}})
    assert first is second  # TTL cache wins over the new cfg within 30s