"""
GitHub service — pulls profile + repo + contribution data from api.github.com.
Uses in-memory cache with ?refresh=1 bypass for developers.
"""
import json
import asyncio
import time
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE: dict = {}  # {key: (timestamp, data)}
_DEFAULT_TTL = 300  # 5 min fallback


def _github_get(path: str, ttl: int = _DEFAULT_TTL, refresh: bool = False) -> Optional[dict]:
    """Fetch `path` from api.github.com with cache. Pass refresh=True to skip cache."""
    now = time.time()
    key = f"gh:{path}"
    if not refresh and key in _CACHE:
        ts, data = _CACHE[key]
        if now - ts < ttl:
            return data

    url = f"https://api.github.com/{path}"
    try:
        r = httpx.get(url, headers={"User-Agent": "thonystank-homelab/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            _CACHE[key] = (now, data)
            return data
        logger.warning("GitHub API %s → %d", url, r.status_code)
    except Exception as e:
        logger.warning("GitHub API error: %s", e)
    return None


async def _fetch_all_github(cfg: dict, refresh: bool = False):
    """Run all 3 GitHub fetches in parallel via thread pool."""
    loop = asyncio.get_running_loop()

    # Use the formatting functions (not raw _github_get) so repos are properly structured
    profile = loop.run_in_executor(None, get_github_profile, cfg, refresh)
    repos = loop.run_in_executor(None, get_github_repos, cfg, refresh)
    contribs = loop.run_in_executor(None, get_github_contributions, cfg, refresh)
    return await asyncio.gather(profile, repos, contribs)


def get_github_profile(cfg: dict, refresh: bool = False) -> Optional[dict]:
    username = cfg["github"]["username"]
    ttl = cfg["github"].get("cache_ttl_minutes", 15) * 60
    return _github_get(f"users/{username}", ttl, refresh)


def get_github_repos(cfg: dict, refresh: bool = False) -> list[dict]:
    username = cfg["github"]["username"]
    ttl = cfg["github"].get("cache_ttl_minutes", 15) * 60
    data = _github_get(f"users/{username}/repos?sort=updated&per_page=30", ttl, refresh)
    if not data:
        return []
    repos = []
    for r in data:
        repos.append({
            "name": r.get("name", ""),
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "stars": r.get("stargazers_count", 0),
            "url": r.get("html_url", ""),
            "homepage": r.get("homepage") or "",
            "fork": r.get("fork", False),
            "updated_at": (r.get("updated_at") or "")[:10],
        })
    return repos


def _get_github_contributions_sync(cfg: dict, ttl: int, refresh: bool = False) -> Optional[dict]:
    """Synchronous contributions fetch via gh CLI."""
    import subprocess
    username = cfg["github"]["username"]
    now = time.time()
    key = f"gh:contributions:{username}"

    if not refresh and key in _CACHE:
        ts, data = _CACHE[key]
        if now - ts < ttl:
            return data

    query = (
        'query { user(login:"%s") { contributionsCollection '
        '{ contributionCalendar { totalContributions weeks '
        '{ contributionDays { contributionCount date color } } } } } }'
        % username
    )
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            logger.warning("gh CLI contributions error: %s", result.stderr)
            return None
        raw = json.loads(result.stdout)
        cal = raw["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        data = {
            "total": cal["totalContributions"],
            "weeks": [
                {
                    "days": [
                        {
                            "count": d["contributionCount"],
                            "date": d["date"],
                            "color": d["color"],
                        }
                        for d in w["contributionDays"]
                    ]
                }
                for w in cal["weeks"]
            ],
        }
        _CACHE[key] = (now, data)
        return data
    except Exception as e:
        logger.warning("Contributions fetch error: %s", e)
        return None


def get_github_contributions(cfg: dict, refresh: bool = False) -> Optional[dict]:
    ttl = cfg["github"].get("cache_ttl_minutes", 15) * 60
    return _get_github_contributions_sync(cfg, ttl, refresh)


async def fetch_github_parallel(cfg: dict, refresh: bool = False):
    """Fetch profile + repos + contributions in parallel. Fast path for /about."""
    return await _fetch_all_github(cfg, refresh)


def warm_github_cache(cfg: dict):
    """Prefetch all GitHub data at startup so first visitor doesn't hit cold cache."""
    logger.info("Warming GitHub cache...")
    get_github_profile(cfg)
    get_github_repos(cfg)
    get_github_contributions(cfg)
    logger.info("GitHub cache warm")