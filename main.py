import os
import yaml

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response

from monitoring_service import get_service_status
from content_service import get_public_notes, get_note_by_slug, get_reviews
from github_service import get_github_profile, get_github_repos, get_github_contributions, fetch_github_parallel, warm_github_cache
from linkedin_service import load_linkedin_profile
from skeletons import SKELETONS
from dataclasses import asdict
from markdown_utils import render_markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_CONFIG_PATH = os.environ.get("SERVER_DASHBOARD_CONFIG", os.path.join(BASE_DIR, "config.yaml"))
with open(_CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

app = FastAPI(on_startup=[lambda: warm_github_cache(CONFIG)])
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Static / attachments
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


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
async def serve_attachment(filename: str):
    dir_ = os.path.join(CONFIG["vault_root"], "4 Files")
    path = os.path.join(dir_, filename)
    if os.path.exists(path):
        return FileResponse(path)
    try:
        for f in os.listdir(dir_):
            if f.lower() == filename.lower():
                return FileResponse(os.path.join(dir_, f))
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Attachment not found")


@app.get("/debug/attachments")
async def debug_attachments():
    dir_ = os.path.join(CONFIG["vault_root"], "4 Files")
    exists = os.path.exists(dir_)
    files = []
    if exists:
        try:
            files = os.listdir(dir_)
        except Exception as e:
            files = [f"Error: {e}"]
    return {"vault_root": CONFIG["vault_root"], "dir": dir_, "exists": exists, "files": files}


# ── API endpoints for async data ──

@app.get("/api/github")
async def api_github(refresh: bool = False):
    profile, repos, contribs = await fetch_github_parallel(CONFIG, refresh=refresh)
    return {"profile": profile, "repos": repos, "contributions": contribs}


@app.get("/api/linkedin")
async def api_linkedin():
    return load_linkedin_profile(CONFIG)


@app.get("/api/services")
async def api_services():
    return get_service_status()


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
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "services": get_service_status(),
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {
        "services": get_service_status(),
    })


@app.get("/notes", response_class=HTMLResponse)
async def notes(request: Request, tag: str = None, sort: str = "date", search: str = None):
    notes_list, tags = get_public_notes(CONFIG["vault_root"], CONFIG["notes_dir"])

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
        "search_param": search or "",
        "tag_counts": tag_counts,
        "notes_count_all": total_count,
    })


@app.get("/note/{slug}", response_class=HTMLResponse)
async def note_view(request: Request, slug: str):
    note = get_note_by_slug(CONFIG["vault_root"], CONFIG["notes_dir"], slug)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Access control: only public / private
    if not any(t.lower() in ("public", "private") for t in note.all_tags):
        raise HTTPException(status_code=403, detail="Access Denied")

    note.content_html = render_markdown(note.content)
    return templates.TemplateResponse(request, "note.html", asdict(note))


@app.get("/reviews", response_class=HTMLResponse)
async def reviews(request: Request):
    return templates.TemplateResponse(request, "reviews.html", {
        "reviews": get_reviews(CONFIG["vault_root"], CONFIG["contents_dir"]),
    })


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Skeleton loads immediately; JS fetches GitHub + LinkedIn async."""
    return templates.TemplateResponse(request, "about.html", {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
