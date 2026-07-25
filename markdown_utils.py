import datetime
import os
import re
from typing import Tuple

import markdown
import yaml


def parse_frontmatter(path: str) -> Tuple[dict, str]:
    """Parse YAML frontmatter from an Obsidian markdown file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return {}, ""

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1])
                return meta if meta else {}, parts[2]
            except Exception:
                pass
    return {}, content


def slug_from_filename(filename: str) -> str:
    return filename[:-3].replace(" ", "-").replace(",", "").replace("'", "").lower()


def parse_created_ts(value) -> int:
    if not value:
        return 0
    try:
        dt = datetime.datetime.fromisoformat(str(value))
        return int(dt.timestamp())
    except Exception:
        return 0


def format_created(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(str(date_str))
        return dt.strftime("%B %d, %Y, %I:%M %p %z")
    except Exception:
        return str(date_str)


def render_markdown(text: str, vault_root: str = None, notes_dir: str = None) -> str:
    """Render markdown with Obsidian wikilinks [[Note]] and embeds ![[Image]]."""
    if not text:
        return ""

    # Embeds ![[Attachment]]
    def replace_embed(m):
        target = m.group(1).strip()
        if "|" in target:
            target = target.split("|", 1)[0].strip()
        fn = os.path.basename(target)
        if any(fn.lower().endswith(e) for e in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
            return f'<img src="/static/attachments/{fn}" class="max-w-full h-auto rounded-lg my-4" alt="{fn}">'
        return f'<a href="/static/attachments/{fn}" class="text-blue-400 hover:underline">{fn}</a>'

    text = re.sub(r"!\[\[([^\]]+)\]\]", replace_embed, text)

    # Wikilinks [[Note Name]]
    def replace_wikilink(m):
        target = m.group(1).strip()
        if "|" in target:
            link_target, display_text = target.split("|", 1)
            link_target = link_target.strip()
        else:
            link_target = target
            display_text = target
        slug = slug_from_filename(link_target + ".md")
        return f'<a href="/note/{slug}" class="text-blue-400 hover:underline">{display_text}</a>'

    text = re.sub(r"(?<!!)\[\[([^\]]+)\]\]", replace_wikilink, text)
    return markdown.markdown(text, extensions=["extra", "nl2br", "sane_lists"])
