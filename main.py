import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response

from config import load_config
from monitoring_service import get_service_status
from content_service import get_public_notes, get_note_by_slug, get_reviews, get_embedded_attachments
from github_service import fetch_github_parallel, warm_github_cache
from skeletons import SKELETONS
from dataclasses import asdict
from markdown_utils import render_markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = load_config()


def md():
    """Markdown directory + tag settings."""
    return CONFIG.get("markdown", {})


app = FastAPI(on_startup=[lambda: warm_github_cache(CONFIG)])
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["site_name"] = CONFIG.get("site", {}).get("name", "Homelab")

# Static / attachments — the attachment route below must be registered BEFORE
# this mount, otherwise the mount (matched first) shadows it and attachments 404.


# ── PWA endpoints ──

@app.get("/manifest.json")
async def manifest():
    """Serve PWA manifest with correct Content-Type for Firefox"""
    import json as _json
    path = os.path.join(BASE_DIR, "static", "manifest.json")
    with open(path) as f:
        content = _json.load(f)
    return Response(content=_json.dumps(content, indent=2), media_type="application/manifest+json")


@app.get("/sw.js")
async def service_worker():
    """Serve service worker at root scope for PWA"""
    path = os.path.join(BASE_DIR, "static", "sw.js")
    with open(path) as f:
        content = f.read()
    return Response(content=content, media_type="text/javascript",
                    headers={"Service-Worker-Allowed": "/",
                             "Cache-Control": "no-cache"})


@app.get("/static/attachments/{filename}")
def serve_attachment(filename: str):
    """Only serve vault files that are embedded (![[...]]) in viewable notes."""
    tags = (md().get("public_tag", "public"), md().get("private_tag", "private"))
    allowed = get_embedded_attachments(md().get("notes_dir") or "", tags)
    low = filename.lower()
    if filename not in allowed and not any(a.lower() == low for a in allowed):
        raise HTTPException(status_code=404, detail="Attachment not found")
    dir_ = md().get("attachments_dir") or ""
    path = os.path.join(dir_, filename)
    if not os.path.exists(path):
        try:
            for f in os.listdir(dir_):
                if f.lower() == filename.lower():
                    path = os.path.join(dir_, f)
                    break
        except OSError:
            pass
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Attachment not found")

@app.get("/resume")
def resume():
    """Serve the resume PDF from resume_path in config.yaml."""
    path = CONFIG.get("resume_path", "")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(path, headers={"Content-Disposition": 'inline; filename="Anthony_Dayrit_Resume.pdf"'})

# Mount static files AFTER the attachment route so /static/attachments isn't shadowed
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# ── API endpoints for async data ──

@app.get("/api/github")
async def api_github(refresh: bool = False):
    profile, repos, contribs, contributed = await fetch_github_parallel(CONFIG, refresh=refresh)
    return {"profile": profile, "repos": repos, "contributions": contribs, "contributed": contributed}


@app.get("/api/services")
def api_services():
    return get_service_status(CONFIG)


# ── Skeleton API — returns just the skeleton HTML for preloading ──

@app.get("/api/skeleton/__root__", response_class=HTMLResponse)
async def skeleton_root():
    """Home page skeleton at clean path."""
    return SKELETONS.get("", "")


@app.get("/api/skeleton/{page}", response_class=HTMLResponse)
async def skeleton(page: str):
    skeleton_html = SKELETONS.get(page)
    if skeleton_html is None:
        raise HTTPException(status_code=404, detail=f"No skeleton for page: {page}")
    return skeleton_html


# ── Pages ──


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    t = CONFIG.get("terminal", {})
    return templates.TemplateResponse(request, "index.html", {
        "services": get_service_status(CONFIG),
        "term": {
            "user": t.get("user", "user"),
            "host": t.get("host", "localhost"),
            "cow_message": t.get("cow_message", "Welcome to my homelab"),
            "shell": t.get("shell", "bash"),
            "type_duration_ms": t.get("type_duration_ms", 2000),
        },
    })


@app.get("/notes", response_class=HTMLResponse)
def notes(request: Request, tag: str = None, sort: str = "date", sort_dir: str = "desc", search: str = None):
    notes_list, tags = get_public_notes(md().get("notes_dir") or "", md().get("public_tag", "public"))

    # Count tag usage from the full unfiltered list (single pass)
    tag_counts: dict[str, int] = {}
    for n in notes_list:
        for t in n.tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    sorted_tags = sorted(tag_counts.keys(), key=lambda t: (-tag_counts[t], t.lower()))
    total_count = len(notes_list)

    # Filter by tag
    if tag:
        tag_lower = tag.lower()
        notes_list = [n for n in notes_list if tag_lower in (t.lower() for t in n.all_tags)]

    # Filter by search query (title match)
    if search:
        q = search.strip().lower()
        notes_list = [n for n in notes_list if q in n.title.lower() or q in n.display_title.lower()]

    return templates.TemplateResponse(request, "notes.html", {
        "notes": notes_list,
        "tags": sorted_tags,
        "tag_param": tag,
        "sort_param": sort,
        "sort_dir_param": sort_dir,
        "search_param": search or "",
        "tag_counts": tag_counts,
        "notes_count_all": total_count,
    })


@app.get("/note/{slug}", response_class=HTMLResponse)
def note_view(request: Request, slug: str):
    note = get_note_by_slug(md().get("notes_dir") or "", slug)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Access control: viewable tags from config
    viewable = (md().get("public_tag", "public"), md().get("private_tag", "private"))
    if not any(t.lower() in (v.lower() for v in viewable) for t in note.all_tags):
        raise HTTPException(status_code=403, detail="Access Denied")

    note.content_html = render_markdown(note.content)
    return templates.TemplateResponse(request, "note.html", asdict(note))


@app.get("/reviews", response_class=HTMLResponse)
def reviews(request: Request, sort: str = "date", sort_dir: str = "desc", cat: str = "movies", search: str = None):
    return templates.TemplateResponse(request, "reviews.html", {
        "reviews": get_reviews(md().get("contents_dir") or ""),
        "sort_param": sort,
        "sort_dir_param": sort_dir,
        "cat_param": cat,
        "search_param": search or "",
    })


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    """Skeleton loads immediately; JS fetches GitHub async. Resume embeds via /resume."""
    t = CONFIG.get("terminal", {})
    resume_path = CONFIG.get("resume_path") or ""
    return templates.TemplateResponse(request, "about.html", {
        "resume_url": "/resume" if resume_path and os.path.exists(resume_path) else None,
        "term": {
            "user": t.get("user", "user"),
            "host": t.get("host", "localhost"),
            "shell": t.get("shell", "bash"),
            "type_duration_ms": t.get("type_duration_ms", 2000),
        },
        "contact": CONFIG.get("profile", {}),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
