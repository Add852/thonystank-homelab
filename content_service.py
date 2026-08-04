import os
from typing import Dict, Any, Optional

from models import Note, Review
from markdown_utils import parse_frontmatter, render_markdown, slug_from_filename, parse_created_ts, format_created


# Global cache: { path: {"mtime": float, "data": Any} }
_CONTENT_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_cached(path: str, parser_fn):
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _CONTENT_CACHE.get(path)
    if cached and cached["mtime"] == mtime:
        return cached["data"]
    data = parser_fn(path)
    if data is not None:
        _CONTENT_CACHE[path] = {"mtime": mtime, "data": data}
    return data


def get_public_notes(vault_root: str, notes_dir: str) -> tuple[list[Note], list[str]]:
    notes_dir_path = os.path.join(vault_root, notes_dir)
    notes: list[Note] = []
    tags: set[str] = set()

    if not os.path.isdir(notes_dir_path):
        return notes, []

    for fn in sorted(os.listdir(notes_dir_path)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(notes_dir_path, fn)
        note = _get_cached(path, lambda p: _parse_note(p))
        if not note:
            continue
        # Only include public-tagged notes in listing
        if "public" not in [t.lower() for t in note.all_tags]:
            continue
        notes.append(note)
        tags.update(note.tags)

    notes.sort(key=lambda n: n.created or "", reverse=True)
    return notes, sorted(tags)


def _parse_note(path: str) -> Optional[Note]:
    meta, body = parse_frontmatter(path)
    raw_tags = meta.get("tags", [])
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    elif raw_tags is None:
        raw_tags = []

    all_tags = [t.strip().lstrip("#") for t in raw_tags]
    display_tags = [t for t in all_tags if t.lower() != "public"]
    preview = body[:500] + ("..." if len(body) > 500 else "")
    fn = os.path.basename(path)

    return Note(
        title=fn.replace(".md", ""),
        display_title=fn.replace(".md", ""),
        url_slug=slug_from_filename(fn),
        preview_body=preview,
        content_html=render_markdown(preview),
        content=body,
        created=format_created(meta.get("created", "")),
        created_ts=parse_created_ts(meta.get("created", "")),
        tags=display_tags,
        all_tags=all_tags,
    )


def get_note_by_slug(vault_root: str, notes_dir: str, slug: str) -> Optional[Note]:
    notes_dir_path = os.path.join(vault_root, notes_dir)
    if not os.path.isdir(notes_dir_path):
        return None
    for fn in os.listdir(notes_dir_path):
        if not fn.endswith(".md"):
            continue
        if slug_from_filename(fn) == slug:
            path = os.path.join(notes_dir_path, fn)
            return _get_cached(path, lambda p: _parse_note(p))
    return None


def _parse_review(path: str, category: str) -> Optional[Review]:
    meta, body = parse_frontmatter(path)

    def _clean(field: str) -> Optional[str]:
        val = meta.get(field)
        if val is None:
            return None
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        return str(val)

    if category.lower() in ("movies", "series"):
        creator = _clean("writer") or _clean("author")
    else:
        creator = _clean("author")
    if not creator:
        creator = "Unknown"

    raw_genres = meta.get("genres", "")
    if isinstance(raw_genres, (list, tuple)):
        clean_genres = ", ".join(str(g) for g in raw_genres)
    elif isinstance(raw_genres, str):
        clean_genres = raw_genres.strip("[]").replace("'", "").replace('"', "")
    else:
        clean_genres = str(raw_genres)

    created_ts = parse_created_ts(meta.get("created", ""))
    description = meta.get("description", body) or ""
    comment = meta.get("comment", "") or ""

    return Review(
        category=category,
        title=meta.get("title", os.path.basename(path).replace(".md", "")),
        rating=float(meta.get("personalRating", 0) or 0),
        creator=creator,
        image=meta.get("image", ""),
        preview_body_html=render_markdown((description or body)[:150]),
        description_html=render_markdown(description),
        comment_html=render_markdown(comment),
        genres=clean_genres,
        created_ts=created_ts,
        created=format_created(meta.get("created", "")),
        description=description,
        comment=comment,
    )


def get_reviews(vault_root: str, contents_dir: str) -> dict[str, list[Review]]:
    base = os.path.join(vault_root, contents_dir)
    categories = {
        "movies": os.path.join(base, "movies"),
        "series": os.path.join(base, "series"),
        "books": os.path.join(base, "books"),
    }
    result: dict[str, list[Review]] = {}
    for cat, dir_path in categories.items():
        items: list[Review] = []
        if os.path.isdir(dir_path):
            for fn in sorted(os.listdir(dir_path)):
                if not fn.endswith(".md"):
                    continue
                path = os.path.join(dir_path, fn)
                review = _get_cached(path, lambda p, c=cat: _parse_review(p, c))
                if review:
                    items.append(review)
        items.sort(key=lambda r: r.created_ts, reverse=True)
        result[cat] = items
    return result
