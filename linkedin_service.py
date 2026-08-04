"""
LinkedIn service — loads profile data from scraped/cached JSON, falls back to YAML.

scraped format (from Browser Use / manual export):
  {
    "name": "...",
    "headline": "...",
    "about": "...",
    "experience": [{"title":..., "company":..., "date_range":..., "description":...}],
    "education": [{"school":..., "degree":..., "date_range":...}],
    "skills": ["skill1", "skill2", ...],
    "certifications": [{"name":..., "issuer":..., "date":...}],
    "profile_url": "...",
    "avatar_url": "...",
    "attachments": [{"type": "image", "url": "...", "description": "..."}]
  }

Config (config.yaml):
  linkedin:
    profile_url: "https://www.linkedin.com/in/anthony-dayrit-785284371"
    mode: "json"           # "json" or "yaml"
    json_path: "linkedin_profile.json"   # path to scraped JSON
    yaml_path: "linkedin_profile.yaml"   # fallback YAML
"""
import json
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CACHE = {}
_CACHE_MTIME = 0.0


def load_linkedin_profile(cfg: dict) -> dict:
    """Load LinkedIn profile from JSON (scraped) or YAML fallback."""
    import os

    mode = cfg.get("mode", "json")
    profile_url = cfg.get("profile_url", "")

    if mode == "json":
        json_path = cfg.get("json_path", "linkedin_profile.json")
        jp = Path(json_path)
        if jp.exists():
            with open(jp) as f:
                data = json.load(f)
            data["profile_url"] = profile_url
            return data
        logger.warning("linkedin_profile.json not found; loading YAML fallback")

    # YAML bust
    yaml_path = cfg.get("yaml_path", "linkedin_profile.yaml")
    yp = Path(yaml_path)
    if yp.exists():
        with open(yp) as f:
            data = yaml.safe_load(f) or {}
        data["profile_url"] = profile_url
        return data

    logger.warning("No LinkedIn profile data found (json or yaml)")
    return {"name": "", "profile_url": profile_url}