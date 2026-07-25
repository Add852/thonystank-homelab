# Server Dashboard

Personal homelab dashboard and content site. Serves service status cards, public notes, and reviews from an Obsidian markdown vault.

**URL:** `http://192.168.1.17:8080` (LAN)  
**Stack:** FastAPI + Jinja2 + Tailwind CDN + Font Awesome 6  
**Python:** 3.12+ (venv at `venv/`)

## Project Structure

```
server_dashboard/
├── main.py                  # FastAPI app, routes, startup
├── models.py                # Dataclasses: Note, Review
├── monitoring_service.py    # Service status from config.yaml
├── content_service.py       # Obsidian markdown parsing and caching
├── markdown_utils.py        # Frontmatter, wikilinks, markdown→HTML
├── config.yaml              # Service definitions, vault paths
├── requirements.txt         # Python dependencies
├── static/
│   ├── favicon.svg
│   └── css/output.css       # Tailwind build (optional)
├── templates/
│   ├── base.html            # Shell: meta, nav, scripts
│   ├── index.html           # Service dashboard grid
│   ├── notes.html           # Public notes listing with tag filter
│   ├── note.html            # Individual note with wikilinks
│   ├── reviews.html         # Tabbed reviews grid with modal
│   ├── terminal.html        # iframe to ttyd terminal (port 7681)
│   └── partials/
│       ├── nav.html         # Sticky nav bar, mobile hamburger
│       └── scripts.html     # Mobile menu JS
└── tests/
    └── test_routes.py       # pytest integration tests

```

## How It Works

- **Services:** `config.yaml` `services:` block defines each card. `monitoring_service.py` reads it and checks port liveness via TCP connect. The template renders each entry as a card.
- **Notes:** Scans `{vault_root}/{notes_dir}/` for `.md` files tagged `public`. Renders Obsidian wikilinks (`[[Note]]`) and embeds (`![[image]]`) to HTML.
- **Reviews:** Scans categories under `{vault_root}/{contents_dir}/` (books, movies, series). Parses YAML frontmatter for ratings, creators, genres.
- **Caching:** `content_service.py` caches parsed content by mtime — no re-parse on every request.

## Configuration

All settings live in `config.yaml`:

| Key | Purpose |
|-----|---------|
| `vault_root` | Absolute path to Obsidian vault |
| `notes_dir` | Subdirectory for notes, relative to vault root |
| `contents_dir` | Subdirectory for reviews, relative to vault root |
| `services` | Dict of services — each with `port`, `url`, `icon_url` (optional), `description`, etc. |

### Adding a Service

Add an entry to the `services:` block in `config.yaml`:

```yaml
  My New Service:
    port: 3000
    url: http://192.168.1.17:3000
    icon: fa-globe               # Font Awesome class (fallback)
    icon_url: https://.../icon.svg  # Official logo (preferred)
    description: What this service does
```

No code changes needed — the monitoring service reads the config and picks it up automatically.

## Running

```bash
cd server_dashboard
source venv/bin/activate
python3 main.py
# → http://localhost:8080
```

Or:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Testing

```bash
cd server_dashboard
source venv/bin/activate
pip install pytest
python -m pytest tests/
```

Tests use `FastAPI.testclient` with a temp Obsidian vault fixture — no real vault needed.

## Notes

- `terminal.html` is a standalone page embedding a ttyd terminal on port 7681. Not linked from the nav bar.
- Service icons use a two-tier system: `icon_url` for official SVG/PNG logos, falling back to Font Awesome `fa-*` classes. Services without official icons (Mnemosyne, 9Router) use Font Awesome exclusively.
- The project home is `/home/tony/server_dashboard`. The vault lives at `/home/tony/SyncProxmox/ObsidianVaults/GroundZero`.