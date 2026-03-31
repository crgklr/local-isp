"""Ahrefs MCP tool server - 8 Ahrefs API v3 endpoints as Agent SDK tools.

These tools are automatically available to any subagent that has "ahrefs"
in its tool list. The SDK handles the tool-use loop.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
from claude_agent_sdk import tool, create_sdk_mcp_server

from config.settings import AHREFS_API_KEY

BASE_URL = "https://api.ahrefs.com/v3"


def _headers() -> dict:
    return {"Authorization": f"Bearer {AHREFS_API_KEY}", "Accept": "application/json"}


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _ok(data: Any) -> dict:
    import json
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2, default=str)}]}


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}


def _get(path: str, params: dict) -> dict:
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{BASE_URL}/{path}", headers=_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


@tool(
    "keywords_overview",
    "Get search volume, keyword difficulty, CPC, traffic potential, SERP features, "
    "and parent topic for a comma-separated list of keywords. CPC is in USD cents.",
    {"keywords": str, "country": str},
)
async def keywords_overview(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("keywords-explorer/overview", {
            "keywords": args["keywords"], "country": args.get("country", "us"),
            "select": "keyword,volume,difficulty,cpc,traffic_potential,parent_topic,serp_features",
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "related_keywords",
    "Find related keyword opportunities that top-ranking pages also rank for. "
    "Filter by min_volume and max_difficulty.",
    {"keywords": str, "country": str, "min_volume": int, "max_difficulty": int, "limit": int},
)
async def related_keywords(args: dict[str, Any]) -> dict:
    min_vol = args.get("min_volume", 50)
    max_diff = args.get("max_difficulty", 50)
    try:
        return _ok(_get("keywords-explorer/related-terms", {
            "keywords": args["keywords"], "country": args.get("country", "us"),
            "terms": "also_rank_for",
            "select": "keyword,volume,difficulty,traffic_potential,cpc,parent_topic",
            "order_by": "volume:desc", "limit": args.get("limit", 30),
            "where": f'{{"and":[{{"field":"volume","is":["gte",{min_vol}]}},{{"field":"difficulty","is":["lte",{max_diff}]}}]}}',
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "search_suggestions",
    "Get autocomplete/search suggestions for seed keywords. "
    "Returns real suggestions with volume, difficulty, CPC.",
    {"keywords": str, "country": str, "limit": int},
)
async def search_suggestions(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("keywords-explorer/search-suggestions", {
            "keywords": args["keywords"], "country": args.get("country", "us"),
            "select": "keyword,volume,difficulty,cpc,traffic_potential",
            "order_by": "volume:desc", "limit": args.get("limit", 20),
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "serp_overview",
    "Get the full SERP for a keyword. Returns ranking URLs with DR, traffic, "
    "backlinks, refdomains, page type, title, position type (organic, snippet, ai_overview).",
    {"keyword": str, "country": str},
)
async def serp_overview(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("serp-overview", {
            "keyword": args["keyword"], "country": args.get("country", "us"),
            "select": "url,domain_rating,title,traffic,keywords,refdomains,type,position",
            "top_positions": 15,
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "organic_keywords",
    "Get organic keywords a domain ranks for. Returns keyword, position, volume, traffic, URL.",
    {"target": str, "country": str, "limit": int},
)
async def organic_keywords(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("site-explorer/organic-keywords", {
            "target": args["target"], "country": args.get("country", "us"),
            "mode": "subdomains",
            "select": "keyword,best_position,volume,sum_traffic,best_position_url",
            "order_by": "sum_traffic:desc", "limit": args.get("limit", 30),
            "date": _yesterday(),
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "domain_metrics",
    "Get high-level SEO metrics: total organic keywords, traffic, traffic value, paid keywords, top-3 count.",
    {"target": str, "country": str},
)
async def domain_metrics(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("site-explorer/metrics", {
            "target": args["target"], "country": args.get("country", "us"),
            "mode": "subdomains", "date": _yesterday(),
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "top_pages",
    "Get top-performing pages for a domain by traffic. Returns URL, traffic, top keyword, volume, total keywords.",
    {"target": str, "country": str, "limit": int},
)
async def top_pages(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("site-explorer/top-pages", {
            "target": args["target"], "country": args.get("country", "us"),
            "mode": "subdomains",
            "select": "url,sum_traffic,top_keyword,top_keyword_volume,keywords",
            "order_by": "sum_traffic:desc", "limit": args.get("limit", 20),
            "date": _yesterday(),
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


@tool(
    "organic_competitors",
    "Find organic competitors by keyword overlap. Returns competitor domain, common/unique keywords, traffic, DR, share.",
    {"target": str, "country": str, "limit": int},
)
async def organic_competitors(args: dict[str, Any]) -> dict:
    try:
        return _ok(_get("site-explorer/organic-competitors", {
            "target": args["target"], "country": args.get("country", "us"),
            "mode": "subdomains",
            "select": "competitor_domain,keywords_common,keywords_competitor,traffic,domain_rating,share",
            "order_by": "share:desc", "limit": args.get("limit", 15),
            "date": _yesterday(),
        }))
    except Exception as e:
        return _err(f"Ahrefs error: {e}")


ahrefs_server = create_sdk_mcp_server(
    name="ahrefs", version="1.0.0",
    tools=[keywords_overview, related_keywords, search_suggestions, serp_overview,
           organic_keywords, domain_metrics, top_pages, organic_competitors],
)
