"""guidectl — a tiny CLI/SDK for the DevOps AI ToolKit guides API.

Queries https://devopsaitoolkit.com/api/v1 for DevOps guides and error guides:
search, list, and filter by stack or type (error guide vs. general guide), then
open the full write-up in your browser. Zero runtime dependencies (stdlib only).
"""

__version__ = "0.1.0"

from .client import GuideClient, APIError, DEFAULT_BASE_URL

__all__ = ["GuideClient", "APIError", "DEFAULT_BASE_URL", "__version__"]
