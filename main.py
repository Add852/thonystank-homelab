import os
import yaml

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from monitoring_service import get_service_status
from content_service import get_public_notes, get_note_by_slug, get_reviews
from dataclasses import asdict
from markdown_utils import render_markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_CONFIG_PATH = os.environ.get("SERVER_DASHBOARD_CONFIG", os.path.join(BASE_DIR, "config.yaml"))
with open(_CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Static / attachments
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


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


# ── Pages ──


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "services": get_service_status(),
        "active_page": "dashboard",
    })


@app.get("/notes", response_class=HTMLResponse)
async def notes(request: Request, tag: str = None):
    notes_list, tags = get_public_notes(CONFIG["vault_root"], CONFIG["notes_dir"])
    return templates.TemplateResponse(request, "notes.html", {
        "notes": notes_list,
        "tags": tags,
        "tag_param": tag,
        "active_page": "notes",
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
        "active_page": "reviews",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
