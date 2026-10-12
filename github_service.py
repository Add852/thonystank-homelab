"""
GitHub service — pulls profile + repo + contribution data from api.github.com.
Uses in-memory cache with ?refresh=1 bypass for developers.
"""
import json
import asyncio
import time
import logging
import os
import subprocess
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE: dict = {}  # {key: (timestamp, data)}
_DEFAULT_TTL = 300  # 5 min fallback

def _github_cfg(cfg: dict) -> dict:
    """GitHub settings live under profile.github (fallback: legacy github key)."""
    return (cfg.get("profile") or {}).get("github") or cfg.get("github") or {}


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
    contributed = loop.run_in_executor(None, get_github_contributed, cfg, refresh)
    return await asyncio.gather(profile, repos, contribs, contributed)


def get_github_profile(cfg: dict, refresh: bool = False) -> Optional[dict]:
    gh = _github_cfg(cfg)
    ttl = gh.get("cache_ttl_minutes", 15) * 60
    return _github_get(f"users/{gh.get('username', '')}", ttl, refresh)


def _normalize_repo_filters(entries) -> set:
    """'https://github.com/user/name' or 'name' → {'name'} (lowercased)."""
    return {str(e).rstrip('/').rsplit('/', 1)[-1].lower() for e in (entries or [])}

def _repo_hidden(name: str, hide: set) -> bool:
    n = name.lower()
    return any(n == h or n.endswith('/' + h) for h in hide)

def get_github_repos(cfg: dict, refresh: bool = False) -> list[dict]:
    gh = _github_cfg(cfg)
    ttl = gh.get("cache_ttl_minutes", 15) * 60
    data = _github_get(f"users/{gh.get('username', '')}/repos?sort=updated&per_page=30", ttl, refresh)
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
    hide = _normalize_repo_filters(gh.get("hide_repos"))
    return [r for r in repos if not _repo_hidden(r["name"], hide)]

def get_github_contributed(cfg: dict, refresh: bool = False) -> list[dict]:
    """Public repos the user contributed to but doesn't own (via GraphQL)."""
    gh = _github_cfg(cfg)
    username = gh.get("username", "")
    ttl = gh.get("cache_ttl_minutes", 15) * 60
    now = time.time()
    key = f"gh:contributed:{username}"
    if not refresh and key in _CACHE:
        ts, data = _CACHE[key]
        if now - ts < ttl:
            return data

    query = (
        'query { user(login:"%s") { repositoriesContributedTo(first: 100, '
        'includeUserRepositories: false) { nodes { name owner { login } '
        'description primaryLanguage { name } stargazerCount url updatedAt isFork } } } }'
        % username
    )
    raw = _graphql(query)
    if not raw:
        return []
    try:
        nodes = raw["data"]["user"]["repositoriesContributedTo"]["nodes"]
    except (KeyError, TypeError) as e:
        logger.warning("Contributed repos parse error: %s", e)
        return []
    repos = [
        {
            "name": f"{n['owner']['login']}/{n['name']}",
            "description": n.get("description") or "",
            "language": (n.get("primaryLanguage") or {}).get("name") or "",
            "stars": n.get("stargazerCount", 0),
            "url": n.get("url", ""),
            "homepage": "",
            "fork": n.get("isFork", False),
            "updated_at": (n.get("updatedAt") or "")[:10],
        }
        for n in nodes
    ]
    hide = _normalize_repo_filters(gh.get("hide_repos"))
    repos = [r for r in repos if not _repo_hidden(r["name"], hide)]
    repos.sort(key=lambda r: r["updated_at"], reverse=True)
    _CACHE[key] = (now, repos)
    return repos


def _get_github_contributions_sync(cfg: dict, ttl: int, refresh: bool = False) -> Optional[dict]:
    """Contribution calendar via GitHub GraphQL."""
    username = _github_cfg(cfg).get("username", "")
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
    raw = _graphql(query)
    if not raw:
        return None
    try:
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
    except (KeyError, TypeError) as e:
        logger.warning("Contributions parse error: %s", e)
        return None


def _graphql(query: str) -> Optional[dict]:
    """Run a GitHub GraphQL query via GITHUB_TOKEN (httpx) or the gh CLI.
    Returns parsed JSON, or None when neither is available/authenticated."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        try:
            r = httpx.post("https://api.github.com/graphql",
                           json={"query": query},
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=15)
            if r.status_code == 200:
                return r.json()
            logger.warning("GitHub GraphQL via token -> HTTP %d", r.status_code)
        except Exception as e:
            logger.warning("GitHub GraphQL via token error: %s", e)
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        logger.warning("gh CLI graphql error: %s", result.stderr.strip())
    except FileNotFoundError:
        logger.warning("No GITHUB_TOKEN set and gh CLI not installed — GraphQL data unavailable")
    except Exception as e:
        logger.warning("gh CLI error: %s", e)
    return None

def get_github_contributions(cfg: dict, refresh: bool = False) -> Optional[dict]:
    gh = _github_cfg(cfg)
    ttl = gh.get("cache_ttl_minutes", 15) * 60
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
    get_github_contributed(cfg)
    logger.info("GitHub cache warm")