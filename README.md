# guidectl

A tiny command-line tool (and Python SDK) for querying the **[DevOps AI ToolKit](https://devopsaitoolkit.com) guides library** — search DevOps guides and **error guides** (OpenStack, Kubernetes, Terraform, Linux, and more) from your terminal, then jump straight to the full write-up.

- **Zero dependencies** — pure Python standard library. `pip install guidectl` pulls nothing else.
- **Fast + offline-friendly** — the API is static JSON; responses are cached locally with a TTL, so repeat queries are instant and work offline after the first fetch.
- **Errors-first** — filter to error guides with `--errors`, or general guides with `--type guide`.
- **Scriptable** — every command supports `--json` for piping into `jq`.

It talks to the public read-only API at `https://devopsaitoolkit.com/api/v1`.

> Looking for reusable AI prompts instead of guides? See the companion tool [**promptctl**](https://github.com/devopsaitoolkit/promptctl).

## Install

```bash
pip install guidectl                     # once published to PyPI
pip install git+https://github.com/devopsaitoolkit/guidectl   # latest from GitHub
```

From source:

```bash
git clone https://github.com/devopsaitoolkit/guidectl && cd guidectl
pip install -e .
```

Requires Python 3.8+.

## Usage

```bash
# Search (all words must match title, description, tags, or category)
guidectl search openstack 504 --errors            # error guides only
guidectl search kubernetes crashloopbackoff
guidectl search gitops --type guide               # general guides only

# List
guidectl list --category kubernetes-helm --errors --limit 10
guidectl categories                               # guide + error-guide counts per stack

# Open a guide
guidectl show openstack-error-messaging-timeout            # details + link
guidectl show openstack-error-messaging-timeout --open     # open in browser
guidectl show openstack-error-messaging-timeout --url      # print only the URL

# API metadata / counts
guidectl meta
```

### Global options

| Flag | Meaning |
|---|---|
| `--json` | Machine-readable JSON output (per command) |
| `--refresh` | Bypass the local cache for this call |
| `--no-cache` | Don't read or write the cache at all |
| `--base-url URL` | Point at a different API base |
| `--version` | Print the version |

### Filters

| Flag | Meaning |
|---|---|
| `--errors` | Error guides only (shortcut for `--type error_guide`) |
| `--type {error_guide,guide}` | Filter by guide type |
| `--category, -c SLUG` | Filter by category (e.g. `openstack`, `kubernetes-helm`) |
| `--tag TAG` | Filter by tag |
| `--limit, -n N` | Max results |

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `GUIDECTL_BASE_URL` | `https://devopsaitoolkit.com/api/v1` | API base URL |
| `GUIDECTL_CACHE_DIR` | `~/.cache/guidectl` | Where cached JSON lives |
| `GUIDECTL_CACHE_TTL` | `3600` | Cache freshness, in seconds |

### Pipe-friendly examples

```bash
guidectl search openstack --errors --json | jq -r '.[].url'
open "$(guidectl show kubernetes-error-crashloopbackoff --url)"
```

## SDK

```python
from guidectl import GuideClient

client = GuideClient()
hits = client.search("504 gateway timeout", category="openstack", guide_type="error_guide")
for g in hits:
    print(g["id"], "-", g["url"])
```

## The API

`guidectl` is a thin client over the public guides API:

| Endpoint | Returns |
|---|---|
| `GET /api/v1/meta.json` | index: counts, categories (guide + error-guide counts), endpoint list |
| `GET /api/v1/guides.json` | every guide + error guide (metadata + link) |
| `GET /api/v1/guides/{category}.json` | guides in one category |

Each guide record: `id`, `title`, `category`, `type` (`error_guide` \| `guide`), `tags`, `description`, `readingTime`, `url`, `pubDate`. The full article lives on the website at `url`.

## Development

```bash
python -m unittest discover -s tests -v     # tests are offline (no network)
python -m guidectl search openstack --errors  # run without installing
```

## License

MIT © DevOps AI ToolKit. Guide content is © DevOps AI ToolKit — free to query for personal and internal use; please attribute with a link back.
