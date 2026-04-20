"""Query utility for the analog books metadata catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog" / "analog_books_index.json"


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def search_items(catalog: dict, query: str) -> list[dict]:
    q = query.lower().strip()
    results: list[dict] = []
    for category in catalog.get("categories", []):
        cname = category.get("name", "")
        for item in category.get("items", []):
            hay = " ".join([
                item.get("title", ""),
                " ".join(item.get("authors", [])),
                " ".join(item.get("tags", [])),
                item.get("notes", ""),
                cname,
            ]).lower()
            if q in hay:
                results.append({"category": cname, **item})
    return results


def list_all(catalog: dict) -> list[dict]:
    out: list[dict] = []
    for category in catalog.get("categories", []):
        cname = category.get("name", "")
        for item in category.get("items", []):
            out.append({"category": cname, **item})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Query analog books metadata catalog")
    parser.add_argument("--query", "-q", default="", help="Search term")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    catalog = load_catalog()
    items = search_items(catalog, args.query) if args.query else list_all(catalog)

    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=True))
        return

    print(f"Catalog items: {len(items)}")
    for i, item in enumerate(items, start=1):
        authors = ", ".join(item.get("authors", []))
        tags = ", ".join(item.get("tags", []))
        print(f"{i:02d}. {item.get('title', 'Untitled')}")
        print(f"    Category: {item.get('category', 'Unknown')}")
        print(f"    Authors: {authors}")
        if tags:
            print(f"    Tags: {tags}")
        if item.get("url"):
            print(f"    URL: {item['url']}")


if __name__ == "__main__":
    main()
