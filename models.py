from dataclasses import dataclass, field
from typing import List


@dataclass
class Note:
    title: str
    display_title: str
    url_slug: str
    preview_body: str
    content_html: str
    content: str
    created: str
    created_ts: int = 0
    tags: List[str] = field(default_factory=list)
    all_tags: List[str] = field(default_factory=list)


@dataclass
class Review:
    category: str
    title: str
    rating: float
    creator: str
    image: str
    preview_body_html: str
    description_html: str
    comment_html: str
    genres: str
    created_ts: int
    created: str
    description: str = ""
    comment: str = ""
