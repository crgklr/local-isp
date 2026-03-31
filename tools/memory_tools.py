"""Memory MCP tool server - gives agents access to persistent state."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

from memory.store import (
    get_published_content, record_published_content,
    get_keyword_positions, record_keyword_positions,
    get_cluster_map, update_cluster,
    record_scout_scan, get_recent_scans,
    record_competitor_snapshot, get_competitor_history,
)


def _ok(data: Any) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2, default=str)}]}


@tool("get_published_content",
      "Get all content DWC has published. Returns title, slug, primary keyword, cluster name, publish date. Use to avoid duplicating topics.", {})
async def tool_get_published(args: dict[str, Any]) -> dict:
    return _ok(get_published_content())


@tool("record_published_content",
      "Record a newly published article in memory. Call after Contentful publish so future scans know this topic is covered.",
      {"title": str, "slug": str, "primary_keyword": str, "cluster_name": str, "word_count": int, "contentful_entry_id": str, "meta_description": str})
async def tool_record_published(args: dict[str, Any]) -> dict:
    return _ok(record_published_content(**args))


@tool("get_keyword_positions",
      "Get historical keyword position data. Pass a keyword to filter, or leave empty for recent across all.", {"keyword": str, "limit": int})
async def tool_get_positions(args: dict[str, Any]) -> dict:
    return _ok(get_keyword_positions(args.get("keyword", ""), args.get("limit", 50)))


@tool("record_keyword_positions",
      "Record batch keyword position data from Ahrefs scan. keywords is a JSON array string with keyword, position, volume, traffic, url.", {"keywords": str})
async def tool_record_positions(args: dict[str, Any]) -> dict:
    keywords = json.loads(args["keywords"]) if isinstance(args["keywords"], str) else args["keywords"]
    return _ok(record_keyword_positions(keywords))


@tool("get_cluster_map",
      "Get the full topical cluster map with keywords (status: opportunity/published/in_progress) and published articles per cluster.", {})
async def tool_get_clusters(args: dict[str, Any]) -> dict:
    return _ok(get_cluster_map())


@tool("update_cluster",
      "Create or update a topical cluster. keywords is a JSON array string of objects with keyword, volume, difficulty, status.",
      {"name": str, "theme": str, "keywords": str})
async def tool_update_cluster(args: dict[str, Any]) -> dict:
    keywords = json.loads(args.get("keywords", "[]")) if isinstance(args.get("keywords"), str) else args.get("keywords", [])
    return _ok(update_cluster(args["name"], args.get("theme", ""), keywords))


@tool("record_scout_scan", "Record a competitive scout scan result. report is a JSON string.", {"report": str})
async def tool_record_scan(args: dict[str, Any]) -> dict:
    report = json.loads(args["report"]) if isinstance(args["report"], str) else args["report"]
    return _ok(record_scout_scan(report))


@tool("get_recent_scans", "Get recent competitive scout scan summaries showing DWC metrics trends.", {"limit": int})
async def tool_get_scans(args: dict[str, Any]) -> dict:
    return _ok(get_recent_scans(args.get("limit", 7)))


@tool("record_competitor_snapshot", "Record a competitor's current metrics for trend tracking.", {"domain": str, "traffic": int, "keywords": int, "domain_rating": float})
async def tool_record_competitor(args: dict[str, Any]) -> dict:
    return _ok(record_competitor_snapshot(args["domain"], args["traffic"], args["keywords"], args["domain_rating"]))


@tool("get_competitor_history", "Get historical metrics for a competitor domain.", {"domain": str, "limit": int})
async def tool_get_competitor_hist(args: dict[str, Any]) -> dict:
    return _ok(get_competitor_history(args["domain"], args.get("limit", 30)))


memory_server = create_sdk_mcp_server(
    name="memory", version="1.0.0",
    tools=[tool_get_published, tool_record_published, tool_get_positions, tool_record_positions,
           tool_get_clusters, tool_update_cluster, tool_record_scan, tool_get_scans,
           tool_record_competitor, tool_get_competitor_hist],
)
