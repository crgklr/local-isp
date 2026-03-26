"""Contentful CMA integration for publishing draft articles."""

from __future__ import annotations

import httpx
from config.settings import (
    CONTENTFUL_ENVIRONMENT,
    CONTENTFUL_MANAGEMENT_TOKEN,
    CONTENTFUL_SPACE_ID,
    CONTENTFUL_CONTENT_TYPE_ID,
)

BASE_URL = f"https://api.contentful.com/spaces/{CONTENTFUL_SPACE_ID}/environments/{CONTENTFUL_ENVIRONMENT}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {CONTENTFUL_MANAGEMENT_TOKEN}",
        "Content-Type": "application/vnd.contentful.management.v1+json",
    }


async def create_draft_entry(
    title: str,
    slug: str,
    body: str,
    meta_description: str,
) -> dict:
    """Create a draft entry in Contentful. Does NOT publish - leaves as draft."""
    payload = {
        "fields": {
            "title": {"en-US": title},
            "slug": {"en-US": slug},
            "body": {"en-US": body},
            "metaDescription": {"en-US": meta_description},
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/entries",
            headers={
                **_headers(),
                "X-Contentful-Content-Type": CONTENTFUL_CONTENT_TYPE_ID,
            },
            json=payload,
        )
        resp.raise_for_status()
        entry = resp.json()

    return {
        "entry_id": entry["sys"]["id"],
        "space_id": CONTENTFUL_SPACE_ID,
        "status": "draft",
    }
