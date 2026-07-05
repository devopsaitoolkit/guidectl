"""Command-line interface for guidectl."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import webbrowser
from typing import Optional

from . import __version__
from .client import DEFAULT_BASE_URL, GUIDE_TYPES, APIError, GuideClient

# ---- tiny tty-aware styling (no dependencies) --------------------------------
_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def accent(t: str) -> str:
    return _c("36", t)


def err(msg: str) -> None:
    print(_c("31", "error:") + " " + msg, file=sys.stderr)


def _type_label(g: dict) -> str:
    return _c("33", "error guide") if g.get("type") == "error_guide" else "guide"


def _resolve_type(args: argparse.Namespace) -> Optional[str]:
    if getattr(args, "errors", False):
        return "error_guide"
    return getattr(args, "type", None)


# ---- rendering ---------------------------------------------------------------
def _print_row(g: dict) -> None:
    meta = " · ".join(x for x in [_type_label(g), accent(g.get("category", ""))] if x)
    print(f"{bold(g.get('id', ''))}  {meta}")
    if g.get("title"):
        print(f"  {g['title']}")
    if g.get("description"):
        print(dim("  " + textwrap.shorten(g["description"], width=100, placeholder="…")))
    print()


# ---- commands ----------------------------------------------------------------
def cmd_search(args: argparse.Namespace, client: GuideClient) -> int:
    results = client.search(
        query=" ".join(args.query),
        category=args.category,
        guide_type=_resolve_type(args),
        tag=args.tag,
        refresh=args.refresh,
    )
    if args.limit:
        results = results[: args.limit]
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    if not results:
        print("No matching guides.")
        return 0
    print(bold(f"{len(results)} guide(s):\n"))
    for g in results:
        _print_row(g)
    print(dim("Tip: guidectl show <id> --open  to read the full write-up."))
    return 0


def cmd_list(args: argparse.Namespace, client: GuideClient) -> int:
    items = client.guides(
        category=args.category, guide_type=_resolve_type(args), refresh=args.refresh
    )
    if args.limit:
        items = items[: args.limit]
    if args.json:
        print(json.dumps(items, indent=2))
        return 0
    for g in items:
        print(f"{bold(g.get('id',''))}  {_type_label(g)}  {accent(g.get('category',''))}  {g.get('title','')}")
    print(dim(f"\n{len(items)} guide(s)."))
    return 0


def cmd_show(args: argparse.Namespace, client: GuideClient) -> int:
    g = client.get(args.id, refresh=args.refresh)
    if not g:
        err(f"guide not found: {args.id}")
        return 1
    if args.json:
        print(json.dumps(g, indent=2))
        return 0
    if args.url:
        print(g.get("url", ""))
        return 0
    print(bold(g.get("title", "")))
    rt = f"{g['readingTime']} min read" if g.get("readingTime") else ""
    print(
        dim(
            " · ".join(
                x
                for x in [
                    g.get("id", ""),
                    "error guide" if g.get("type") == "error_guide" else "guide",
                    g.get("category", ""),
                    rt,
                ]
                if x
            )
        )
    )
    if g.get("description"):
        print("\n" + g["description"])
    if g.get("tags"):
        print(dim("\ntags: " + ", ".join(g["tags"])))
    if g.get("url"):
        print("\n" + bold("Read the full guide:"))
        print(g["url"])
    if args.open and g.get("url"):
        webbrowser.open(g["url"])
        print(dim("\n[opening in browser…]"))
    return 0


def cmd_categories(args: argparse.Namespace, client: GuideClient) -> int:
    cats = client.categories(refresh=args.refresh)
    if args.json:
        print(json.dumps(cats, indent=2))
        return 0
    width = max((len(c["slug"]) for c in cats), default=10)
    for c in sorted(cats, key=lambda c: c.get("guides", 0), reverse=True):
        print(
            f"  {bold(c['slug'].ljust(width))}  {str(c.get('guides',0)).rjust(4)} guides  "
            f"{str(c.get('errorGuides',0)).rjust(4)} error  {dim(c.get('name',''))}"
        )
    return 0


def cmd_meta(args: argparse.Namespace, client: GuideClient) -> int:
    m = client.meta(refresh=args.refresh)
    if args.json:
        print(json.dumps(m, indent=2))
        return 0
    print(bold(f"{m.get('name','DevOps AI ToolKit API')}  ({m.get('version','')})"))
    counts = m.get("counts", {})
    print(f"  guides: {counts.get('guides','?')}   error guides: {counts.get('errorGuides','?')}   prompts: {counts.get('prompts','?')}")
    print(dim(f"  base: {m.get('base','')}"))
    print(dim(f"  generated: {m.get('generatedAt','')}"))
    return 0


# ---- parser ------------------------------------------------------------------
def _add_type_flags(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--errors", action="store_true", help="error guides only")
    sp.add_argument("--type", choices=GUIDE_TYPES, help="filter by guide type")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="guidectl",
        description="Query the DevOps AI ToolKit guides + error guides from the command line.",
        epilog="Examples:\n"
        "  guidectl search openstack 504 --errors\n"
        "  guidectl list --category kubernetes-helm --errors --limit 10\n"
        "  guidectl show openstack-error-messaging-timeout --open\n"
        "  guidectl categories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"guidectl {__version__}")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    p.add_argument("--refresh", action="store_true", help="bypass the local cache")
    p.add_argument("--no-cache", action="store_true", help="do not read or write the cache")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("search", help="search guides by keyword + filters")
    s.add_argument("query", nargs="*", help="search words (all must match)")
    s.add_argument("--category", "-c", help="filter by category slug")
    _add_type_flags(s)
    s.add_argument("--tag", help="filter by tag")
    s.add_argument("--limit", "-n", type=int, help="max results")
    s.add_argument("--json", action="store_true", help="output raw JSON")
    s.set_defaults(func=cmd_search)

    ls = sub.add_parser("list", help="list guides (metadata)")
    ls.add_argument("--category", "-c", help="filter by category slug")
    _add_type_flags(ls)
    ls.add_argument("--limit", "-n", type=int, help="max results")
    ls.add_argument("--json", action="store_true", help="output raw JSON")
    ls.set_defaults(func=cmd_list)

    sh = sub.add_parser("show", help="show a guide's details + link by id")
    sh.add_argument("id", help="guide id (slug)")
    sh.add_argument("--open", action="store_true", help="open the full guide in a browser")
    sh.add_argument("--url", action="store_true", help="print only the guide URL")
    sh.add_argument("--json", action="store_true", help="output raw JSON")
    sh.set_defaults(func=cmd_show)

    ca = sub.add_parser("categories", help="list categories with guide counts")
    ca.add_argument("--json", action="store_true", help="output raw JSON")
    ca.set_defaults(func=cmd_categories)

    mt = sub.add_parser("meta", help="show API metadata")
    mt.add_argument("--json", action="store_true", help="output raw JSON")
    mt.set_defaults(func=cmd_meta)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    client = GuideClient(base_url=args.base_url, cache=not args.no_cache)
    try:
        return args.func(args, client)
    except APIError as exc:
        err(str(exc))
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
