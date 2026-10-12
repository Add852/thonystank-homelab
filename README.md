# Thonystank Homelab

Personal homelab dashboard and content site. Serves service status cards, public notes, and reviews from an Obsidian markdown vault.

**URL:** `http://192.168.1.17:8080` (LAN)  
**Stack:** FastAPI + Jinja2 + Tailwind CDN + Font Awesome 6  
**Python:** 3.12+ (venv at `venv/`)

## Project Structure

```
thonystank-homelab/
├── main.py                  # FastAPI app, routes, startup
├── models.py                # Dataclasses: Note, Review
├── monitoring_service.py    # Service status from config.yaml (port checks, 30s cache)
├── content_service.py       # Obsidian markdown parsing and caching
├── markdown_utils.py        # Frontmatter, wikilinks, markdown→HTML
├── github_service.py        # GitHub profile/repos/contributions (cached)
├── skeletons.py             # Static skeleton HTML fragments per page
├── config.yaml              # Site, profile, services, terminal config
├── config.py                # Config loader: .env + ${VAR} expansion
├── requirements.txt         # Python dependencies
├── static/
│   ├── favicon.svg
│   ├── manifest.json        # PWA manifest
│   ├── sw.js                # Service worker
│   ├── fonts/               # Self-hosted NerdFont (terminal glyphs)
│   ├── webfonts/            # Self-hosted Font Awesome webfonts
│   ├── js/                  # Self-hosted Tailwind + pdf.js (no external CDNs)
│   ├── icons/pwa/           # PWA icons
│   └── css/
│       ├── global.css       # Terminal theme, buttons, fastfetch panel
│       ├── fontawesome/     # Self-hosted Font Awesome CSS
│       ├── index.css        # Dashboard cards
│       ├── about.css        # About page, contribution graph
│       └── reviews.css      # Reviews tabs, modal, star ratings
├── templates/
│   ├── base.html            # Shell: meta, nav, scripts
│   ├── index.html           # Home: hero, services grid, explore cards
│   ├── about.html           # Portfolio (GitHub, resume, contact links)
│   ├── notes.html           # Public notes listing with tag filter
│   ├── note.html            # Individual note with wikilinks
│   ├── reviews.html         # Tabbed reviews grid with modal
│   └── partials/
│       ├── nav.html         # Sticky nav bar, mobile hamburger
│       ├── scripts.html     # Mobile menu, PWA, skeleton preloader JS
│       └── macros.html      # Shared Jinja macros (star ratings, etc.)
└── tests/
    └── test_routes.py       # pytest integration tests
```

## How It Works

- **Services:** `config.yaml` `services:` block defines each card on the home page. `monitoring_service.py` checks each service's `url`/`public_url` over HTTP (falls back to a TCP port probe, host derived from the URL), all concurrently with results cached for 30s.
- **Notes:** Scans the configured `notes_dir` for `.md` files with the `public` tag (or `private`). Renders Obsidian wikilinks (`[[Note]]`) and embeds (`![[image]]`) to HTML.
- **Attachments:** `/static/attachments/{filename}` only serves files embedded via `![[...]]` in viewable notes — other vault files 404.
- **Reviews:** Scans category folders under the configured `contents_dir` (books, movies, series). Parses YAML frontmatter for ratings, creators, genres.
- **Home:** Terminal window types `cowsay` with your greeting, then idles at a blinking prompt. Everything comes from the `terminal:` config block.
- **About:** Page shell renders instantly; JS fetches `/api/github`, types `fastfetch`, and renders the profile as a **fastfetch-style panel** (GitHub avatar as the logo, `user@host` header, bio/location/GitHub-follower rows, LinkedIn/email/phone links with open-in-new-tab indicators) in a single non-wrapping row that scrolls horizontally. Plus the contribution graph (auto-scrolled to the latest week), own repos, and a "Contributed to" section. Resume renders page 1 to a canvas via pdf.js.
- **About:** … Contact links (LinkedIn, Messenger, phone) sit in the profile card.
- **Caching:** `content_service.py` caches parsed content by mtime; `github_service.py` caches API responses (15 min TTL); service status cached 30s.

## Configuration

**`config.yaml`** holds everything portable (site name, profile/contact, services, tag names, terminal) — safe to push/pull between machines. **`.env`** (gitignored; copy from `.env.example`) holds device-specific absolute paths — `NOTES_DIR`, `CONTENTS_DIR`, `ATTACHMENTS_DIR`, `RESUME_PATH` — referenced from config.yaml as `${NOTES_DIR}` etc. Obsidian vault structure can differ per device; only `.env` cares. `SERVER_DASHBOARD_CONFIG` still overrides the config path (used by tests).

| Key | Purpose |
|-----|---------|
| `site.name` | Site title, nav brand, hero heading |
| `resume_path` | Resume PDF, served at `/resume` (section hides if unset/missing) — from `.env` |
| `profile.github` | `username`, `cache_ttl_minutes` (API cache; protects the 60 req/h unauthenticated limit), `hide_repos` (names or URLs excluded from /about) |
| `profile.linkedin` / `messenger` / `phone` / `email` | Contact rows on `/about` (a row hides if its key is unset) |
| `markdown` | `notes_dir`, `contents_dir`, `attachments_dir` — absolute paths from `.env`; `public_tag`, `private_tag` (which tags make notes listed/viewable) |
| `services` | Dict of services — see below |
| `terminal` | `user`, `host`, `cow_message`, `shell`, `type_duration_ms` — home terminal prompt + cowsay + title bar; each typed command takes `type_duration_ms` regardless of length |

### Adding a Service

Add an entry to the `services:` block in `config.yaml`:

```yaml
  My New Service:
    port: 3000
    url: http://192.168.1.17:3000
    host: 127.0.0.1               # optional, defaults to 127.0.0.1
    icon: fa-globe                # Font Awesome class (fallback)
    icon_url: https://.../icon.svg  # Official logo (preferred)
    description: What this service does
```

No code changes needed — the monitoring service reads the config and picks it up automatically.

## Running

```bash
cd thonystank-homelab
source venv/bin/activate
python3 main.py
# → http://localhost:8080
```

Or:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Deploying

```bash
git pull                      # on the server
cp .env.example .env          # once — then set the device's absolute paths
pip install -r requirements.txt  # into the venv
sudo systemctl restart <service> # or however uvicorn runs
```

The service worker is network-first, so new deploys show up on the next page load — no cache bumping needed. `static/` (Tailwind, Font Awesome, NerdFont, pdf.js) is fully self-hosted; the app needs no internet access.

The **contributions graph** and **"Contributed to"** sections need GitHub GraphQL access: either a `GITHUB_TOKEN` in `.env` (recommended for servers — create a no-scope token at github.com/settings/tokens) or an authenticated `gh` CLI (`gh auth login`) on the device. Without either, those two sections stay empty and the log explains why.

Behind a **Cloudflare tunnel**, purge the edge cache once after the first header-enabled deploy (dashboard → Caching → *Purge Everything*): static responses now send `Cache-Control: no-cache`, so the edge revalidates instead of holding stale CSS/fonts — but already-cached entries linger until purged or expired.

## Testing

```bash
cd thonystank-homelab
source venv/bin/activate
pip install pytest
python -m pytest tests/
```

Tests use `FastAPI.testclient` with a temp Obsidian vault fixture — no real vault needed.

## Notes

- The project home is `/home/tony/Projects/thonystank-homelab`. Vault folder paths live in `.env` (see `.env.example`).
