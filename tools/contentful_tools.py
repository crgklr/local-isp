"""Contentful MCP tool server - the source of truth for all DWC content.

Since Contentful is API-driven, agents query it directly to know what
articles exist, what topics are covered, and what's in draft vs published.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from claude_agent_sdk import tool, create_sdk_mcp_server

from config.settings import (
    CONTENTFUL_SPACE_ID, CONTENTFUL_MANAGEMENT_TOKEN,
    CONTENTFUL_ENVIRONMENT, CONTENTFUL_CONTENT_TYPE_ID,
)

BASE_URL = f"https://api.contentful.com/spaces/{CONTENTFUL_SPACE_ID}/environments/{CONTENTFUL_ENVIRONMENT}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {CONTENTFUL_MANAGEMENT_TOKEN}",
        "Content-Type": "application/vnd.contentful.management.v1+json",
    }


def _ok(data: Any) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2, default=str)}]}


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}


@tool(
    "publish_draft",
    "Create a draft entry in Contentful. Does NOT publish, leaves as draft. Returns entry ID.",
    {"title": str, "slug": str, "body": str, "meta_description": str},
)
async def publish_draft(args: dict[str, Any]) -> dict:
    payload = {
        "fields": {
            "title": {"en-US": args["title"]},
            "slug": {"en-US": args["slug"]},
            "body": {"en-US": args["body"]},
            "metaDescription": {"en-US": args["meta_description"]},
        }
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{BASE_URL}/entries",
                headers={**_headers(), "X-Contentful-Content-Type": CONTENTFUL_CONTENT_TYPE_ID},
                json=payload,
            )
            resp.raise_for_status()
            entry = resp.json()
        return _ok({"entry_id": entry["sys"]["id"], "space_id": CONTENTFUL_SPACE_ID, "status": "draft"})
    except Exception as e:
        return _err(f"Contentful error: {e}")


@tool(
    "list_all_content",
    "Get ALL existing content from Contentful. Returns every article's title, slug, "
    "status (draft/published), and dates. This is the source of truth for what topics "
    "DWC has already covered. Use BEFORE suggesting new topics.",
    {"limit": int},
)
async def list_all_content(args: dict[str, Any]) -> dict:
    try:
        all_entries = []
        skip = 0
        limit = min(args.get("limit", 100), 100)

        with httpx.Client(timeout=30) as client:
            while True:
                resp = client.get(
                    f"{BASE_URL}/entries", headers=_headers(),
                    params={"content_type": CONTENTFUL_CONTENT_TYPE_ID, "limit": limit,
                            "skip": skip, "order": "-sys.createdAt"},
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    fields = item.get("fields", {})
                    sys_data = item.get("sys", {})
                    published_at = sys_data.get("publishedAt")
                    all_entries.append({
                        "id": sys_data.get("id", ""),
                        "title": fields.get("title", {}).get("en-US", ""),
                        "slug": fields.get("slug", {}).get("en-US", ""),
                        "meta_description": fields.get("metaDescription", {}).get("en-US", ""),
                        "status": "published" if published_at else "draft",
                        "created_at": sys_data.get("createdAt", ""),
                        "updated_at": sys_data.get("updatedAt", ""),
                        "published_at": published_at or "",
                    })

                total = data.get("total", 0)
                skip += limit
                if skip >= total:
                    break

        return _ok({"total": len(all_entries), "entries": all_entries})
    except Exception as e:
        return _err(f"Contentful error: {e}")


@tool(
    "get_entry_content",
    "Get the full content of a specific Contentful entry by ID. "
    "Returns title, slug, body, and meta description.",
    {"entry_id": str},
)
async def get_entry_content(args: dict[str, Any]) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/entries/{args['entry_id']}", headers=_headers())
            resp.raise_for_status()
            item = resp.json()
        fields = item.get("fields", {})
        return _ok({
            "id": item["sys"]["id"],
            "title": fields.get("title", {}).get("en-US", ""),
            "slug": fields.get("slug", {}).get("en-US", ""),
            "body": fields.get("body", {}).get("en-US", ""),
            "meta_description": fields.get("metaDescription", {}).get("en-US", ""),
            "status": "published" if item["sys"].get("publishedAt") else "draft",
        })
    except Exception as e:
        return _err(f"Contentful error: {e}")


@tool(
    "search_content_by_slug",
    "Check if an article with a specific slug already exists in Contentful.",
    {"slug": str},
)
async def search_content_by_slug(args: dict[str, Any]) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{BASE_URL}/entries", headers=_headers(),
                params={"content_type": CONTENTFUL_CONTENT_TYPE_ID, "fields.slug": args["slug"], "limit": 1},
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("total", 0) == 0:
            return _ok({"exists": False, "slug": args["slug"]})
        item = data["items"][0]
        fields = item.get("fields", {})
        return _ok({
            "exists": True, "id": item["sys"]["id"],
            "title": fields.get("title", {}).get("en-US", ""),
            "slug": fields.get("slug", {}).get("en-US", ""),
            "status": "published" if item["sys"].get("publishedAt") else "draft",
        })
    except Exception as e:
        return _err(f"Contentful error: {e}")


contentful_server = create_sdk_mcp_server(
    name="contentful", version="1.0.0",
    tools=[publish_draft, list_all_content, get_entry_content, search_content_by_slug],
)
