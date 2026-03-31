"""Contentful MCP tool server - publish drafts and read existing content."""

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
    return {"Authorization": f"Bearer {CONTENTFUL_MANAGEMENT_TOKEN}", "Content-Type": "application/vnd.contentful.management.v1+json"}


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
    payload = {"fields": {"title": {"en-US": args["title"]}, "slug": {"en-US": args["slug"]},
                           "body": {"en-US": args["body"]}, "metaDescription": {"en-US": args["meta_description"]}}}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{BASE_URL}/entries",
                               headers={**_headers(), "X-Contentful-Content-Type": CONTENTFUL_CONTENT_TYPE_ID}, json=payload)
            resp.raise_for_status()
            entry = resp.json()
        return _ok({"entry_id": entry["sys"]["id"], "space_id": CONTENTFUL_SPACE_ID, "status": "draft"})
    except Exception as e:
        return _err(f"Contentful error: {e}")


@tool(
    "list_entries",
    "List existing blog entries in Contentful. Returns titles, slugs, and IDs.",
    {"limit": int},
)
async def list_entries(args: dict[str, Any]) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/entries", headers=_headers(),
                              params={"content_type": CONTENTFUL_CONTENT_TYPE_ID, "limit": args.get("limit", 50),
                                      "select": "sys.id,fields.title,fields.slug"})
            resp.raise_for_status()
            data = resp.json()
        entries = [{"id": i["sys"]["id"], "title": i.get("fields", {}).get("title", {}).get("en-US", ""),
                    "slug": i.get("fields", {}).get("slug", {}).get("en-US", "")} for i in data.get("items", [])]
        return _ok({"total": data.get("total", 0), "entries": entries})
    except Exception as e:
        return _err(f"Contentful error: {e}")


contentful_server = create_sdk_mcp_server(name="contentful", version="1.0.0", tools=[publish_draft, list_entries])
