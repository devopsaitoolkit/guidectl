"""API client for the DevOps AI ToolKit guides API (stdlib only).

The API (https://devopsaitoolkit.com/api/v1) serves static, cacheable JSON:
  - meta.json                    — index, counts, categories
  - guides.json                  — every guide + error guide (metadata + link)
  - guides/{category}.json       — guides in one category

Each guide record carries a `type` of "error_guide" or "guide". The full article
lives on the website (the `url` field); this API exposes titles, descriptions,
tags, and links so a client can search and jump straight to the right page.

Responses are cached under ~/.cache/guidectl with a TTL, so repeated queries are
fast and work offline after the first fetch.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

__version__ = "0.1.0"

DEFAULT_BASE_URL = os.environ.get(
    "GUIDECTL_BASE_URL", "https://devopsaitoolkit.com/api/v1"
)
DEFAULT_TTL = int(os.environ.get("GUIDECTL_CACHE_TTL", "3600"))
CACHE_DIR = Path(
    os.environ.get("GUIDECTL_CACHE_DIR", str(Path.home() / ".cache" / "guidectl"))
)
USER_AGENT = f"guidectl/{__version__} (+https://github.com/devopsaitoolkit/guidectl)"

# Valid values for the `type` field / --type filter.
GUIDE_TYPES = ("error_guide", "guide")


class APIError(RuntimeError):
    """Raised when the API can't be reached or returns an error."""


class GuideClient:
    """Read-only client for the guides API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        ttl: int = DEFAULT_TTL,
        cache: bool = True,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.ttl = ttl
        self.cache = cache
        self.timeout = timeout

    # -- low-level fetch with caching -------------------------------------
    def _cache_path(self, path: str) -> Path:
        return CACHE_DIR / (path.replace("/", "__"))

    def _read_cache(self, path: str, allow_stale: bool = False) -> Optional[Any]:
        cp = self._cache_path(path)
        if not cp.exists():
            return None
        if not allow_stale and (time.time() - cp.stat().st_mtime) >= self.ttl:
            return None
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    def _write_cache(self, path: str, data: Any) -> None:
        if not self.cache:
            return
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self._cache_path(path).write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass  # cache is best-effort

    def fetch(self, path: str, refresh: bool = False) -> Any:
        """Fetch and decode a JSON resource (e.g. 'guides.json'), using the cache."""
        if self.cache and not refresh:
            cached = self._read_cache(path)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{path}"
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise APIError(f"HTTP {exc.code} fetching {url}") from exc
        except urllib.error.URLError as exc:
            stale = self._read_cache(path, allow_stale=True)
            if stale is not None:
                return stale  # offline: serve stale cache rather than fail
            raise APIError(f"Network error fetching {url}: {exc.reason}") from exc
        except ValueError as exc:
            raise APIError(f"Invalid JSON from {url}: {exc}") from exc

        self._write_cache(path, data)
        return data

    # -- high-level API ----------------------------------------------------
    def meta(self, refresh: bool = False) -> dict:
        """Return the API index (counts, categories, endpoints)."""
        return self.fetch("meta.json", refresh=refresh)

    def guides(
        self,
        category: Optional[str] = None,
        guide_type: Optional[str] = None,
        refresh: bool = False,
    ) -> list[dict]:
        """Return guides, optionally scoped to a category and/or type
        ('error_guide' or 'guide')."""
        path = f"guides/{category}.json" if category else "guides.json"
        items = self.fetch(path, refresh=refresh).get("items", [])
        if guide_type:
            items = [g for g in items if g.get("type") == guide_type]
        return items

    def get(self, guide_id: str, refresh: bool = False) -> Optional[dict]:
        """Return a single guide by id, or None if not found."""
        for guide in self.guides(refresh=refresh):
            if guide.get("id") == guide_id:
                return guide
        return None

    def categories(self, refresh: bool = False) -> list[dict]:
        """Return the category list with per-category guide/error-guide counts."""
        return self.meta(refresh=refresh).get("categories", [])

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        guide_type: Optional[str] = None,
        tag: Optional[str] = None,
        refresh: bool = False,
    ) -> list[dict]:
        """Search guides. All words in `query` must match somewhere in the title,
        description, tags, or category. Filters are ANDed with the query."""
        items = self.guides(category=category, guide_type=guide_type, refresh=refresh)
        terms = [t for t in query.lower().split() if t]

        def matches(g: dict) -> bool:
            if tag and tag.lower() not in [t.lower() for t in g.get("tags", [])]:
                return False
            if not terms:
                return True
            blob = " ".join(
                [
                    g.get("title", ""),
                    g.get("description", ""),
                    " ".join(g.get("tags", [])),
                    g.get("category", ""),
                ]
            ).lower()
            return all(term in blob for term in terms)

        return [g for g in items if matches(g)]
