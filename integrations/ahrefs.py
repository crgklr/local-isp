"""Ahrefs API v3 integration for real-time SEO research via tool use.

This module defines Ahrefs endpoints as Claude tool-use schemas and provides
the execution layer that routes tool calls to the Ahrefs API. The SEO agent
uses these tools autonomously during its research loop.
"""

from __future__ import annotations

from datetime import date, timedelta
import httpx
from config.settings import AHREFS_API_KEY

BASE_URL = "https://api.ahrefs.com/v3"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {AHREFS_API_KEY}",
        "Accept": "application/json",
    }


def _today() -> str:
    return date.today().isoformat()


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------------
# Tool definitions (Claude tool-use format)
# ---------------------------------------------------------------------------

AHREFS_TOOLS = [
    {
        "name": "ahrefs_keywords_overview",
        "description": (
            "Get search volume, keyword difficulty, CPC, traffic potential, "
            "SERP features, search intent, and parent topic for a list of keywords. "
            "Use this to evaluate keyword opportunities and understand search intent. "
            "CPC is returned in USD cents. SERP features include ai_overview, snippet, "
            "question, video, image, local_pack, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Comma-separated list of keywords to analyze (max 100).",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "ahrefs_related_keywords",
        "description": (
            "Find related keyword opportunities that top-ranking pages also rank for. "
            "Returns keywords with volume, difficulty, traffic potential, and CPC. "
            "Use this to discover secondary and long-tail keywords for a topic. "
            "You can filter by minimum volume and maximum difficulty."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Comma-separated seed keywords to find related terms for.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
                "min_volume": {
                    "type": "integer",
                    "description": "Minimum monthly search volume (default: 50).",
                    "default": 50,
                },
                "max_difficulty": {
                    "type": "integer",
                    "description": "Maximum keyword difficulty 0-100 (default: 50).",
                    "default": 50,
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default: 30).",
                    "default": 30,
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "ahrefs_search_suggestions",
        "description": (
            "Get autocomplete/search suggestions for seed keywords. "
            "Returns real search suggestions with volume, difficulty, and CPC. "
            "Use this to find long-tail keyword variations and question-based queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Comma-separated seed keywords to get suggestions for.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default: 20).",
                    "default": 20,
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "ahrefs_serp_overview",
        "description": (
            "Get the full SERP (Search Engine Results Page) for a keyword. "
            "Returns all ranking URLs with their domain rating, traffic, backlinks, "
            "referring domains, page type, title, and position type (organic, snippet, "
            "ai_overview, etc.). Use this to analyze competition for a specific keyword."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The keyword to get SERP results for.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "ahrefs_organic_keywords",
        "description": (
            "Get the organic keywords a domain or URL currently ranks for. "
            "Returns keyword, position, volume, traffic, and ranking URL. "
            "Use this to see what DWC or a competitor currently ranks for."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Domain or URL to analyze (e.g., 'distributorwire.com' or a competitor domain).",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default: 30).",
                    "default": 30,
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "ahrefs_domain_metrics",
        "description": (
            "Get high-level SEO metrics for a domain: total organic keywords, "
            "organic traffic, traffic value, paid keywords, and top-3 keyword count. "
            "Use this to quickly assess a domain's organic strength."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Domain to analyze.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "ahrefs_top_pages",
        "description": (
            "Get the top-performing pages for a domain ranked by traffic. "
            "Returns URL, traffic, top keyword, keyword volume, and total keywords. "
            "Use this to identify what content is working for a competitor."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Domain to analyze.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default: 20).",
                    "default": 20,
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "ahrefs_organic_competitors",
        "description": (
            "Find organic competitors for a domain based on keyword overlap. "
            "Returns competitor domain, common keywords, their unique keywords, "
            "traffic, domain rating, and keyword share percentage. "
            "Use this to identify who competes with DWC in search results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Domain to find competitors for.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code (default: us).",
                    "default": "us",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default: 15).",
                    "default": 15,
                },
            },
            "required": ["target"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution layer
# ---------------------------------------------------------------------------

def execute_tool(name: str, inputs: dict) -> dict:
    """Execute an Ahrefs tool call and return the result."""
    handlers = {
        "ahrefs_keywords_overview": _exec_keywords_overview,
        "ahrefs_related_keywords": _exec_related_keywords,
        "ahrefs_search_suggestions": _exec_search_suggestions,
        "ahrefs_serp_overview": _exec_serp_overview,
        "ahrefs_organic_keywords": _exec_organic_keywords,
        "ahrefs_domain_metrics": _exec_domain_metrics,
        "ahrefs_top_pages": _exec_top_pages,
        "ahrefs_organic_competitors": _exec_organic_competitors,
    }

    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}

    try:
        return handler(inputs)
    except httpx.HTTPStatusError as e:
        return {"error": f"Ahrefs API error {e.response.status_code}: {e.response.text[:500]}"}
    except Exception as e:
        return {"error": f"Tool execution error: {str(e)}"}


def _exec_keywords_overview(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    keywords = inputs["keywords"]
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/keywords-explorer/overview",
            headers=_headers(),
            params={
                "keywords": keywords,
                "country": country,
                "select": "keyword,volume,difficulty,cpc,traffic_potential,parent_topic,serp_features",
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_related_keywords(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    min_vol = inputs.get("min_volume", 50)
    max_diff = inputs.get("max_difficulty", 50)
    limit = inputs.get("limit", 30)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/keywords-explorer/related-terms",
            headers=_headers(),
            params={
                "keywords": inputs["keywords"],
                "country": country,
                "terms": "also_rank_for",
                "select": "keyword,volume,difficulty,traffic_potential,cpc,parent_topic",
                "order_by": "volume:desc",
                "limit": limit,
                "where": f'{{"and":[{{"field":"volume","is":["gte",{min_vol}]}},{{"field":"difficulty","is":["lte",{max_diff}]}}]}}',
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_search_suggestions(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    limit = inputs.get("limit", 20)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/keywords-explorer/search-suggestions",
            headers=_headers(),
            params={
                "keywords": inputs["keywords"],
                "country": country,
                "select": "keyword,volume,difficulty,cpc,traffic_potential",
                "order_by": "volume:desc",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_serp_overview(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/serp-overview",
            headers=_headers(),
            params={
                "keyword": inputs["keyword"],
                "country": country,
                "select": "url,domain_rating,title,traffic,keywords,refdomains,type,position",
                "top_positions": 15,
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_organic_keywords(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    limit = inputs.get("limit", 30)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/site-explorer/organic-keywords",
            headers=_headers(),
            params={
                "target": inputs["target"],
                "country": country,
                "mode": "subdomains",
                "select": "keyword,best_position,volume,sum_traffic,best_position_url",
                "order_by": "sum_traffic:desc",
                "limit": limit,
                "date": _yesterday(),
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_domain_metrics(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/site-explorer/metrics",
            headers=_headers(),
            params={
                "target": inputs["target"],
                "country": country,
                "mode": "subdomains",
                "date": _yesterday(),
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_top_pages(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    limit = inputs.get("limit", 20)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/site-explorer/top-pages",
            headers=_headers(),
            params={
                "target": inputs["target"],
                "country": country,
                "mode": "subdomains",
                "select": "url,sum_traffic,top_keyword,top_keyword_volume,keywords",
                "order_by": "sum_traffic:desc",
                "limit": limit,
                "date": _yesterday(),
            },
        )
        resp.raise_for_status()
        return resp.json()


def _exec_organic_competitors(inputs: dict) -> dict:
    country = inputs.get("country", "us")
    limit = inputs.get("limit", 15)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/site-explorer/organic-competitors",
            headers=_headers(),
            params={
                "target": inputs["target"],
                "country": country,
                "mode": "subdomains",
                "select": "competitor_domain,keywords_common,keywords_competitor,traffic,domain_rating,share",
                "order_by": "share:desc",
                "limit": limit,
                "date": _yesterday(),
            },
        )
        resp.raise_for_status()
        return resp.json()
