"""Canary Agent - Publishes to Contentful and notifies user."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from integrations.contentful import create_draft_entry


class CanaryAgent:
    """Handles publishing to Contentful as a draft and alerting the user."""

    name = "Canary"

    def publish_and_notify(self, article: dict) -> dict:
        """Publish the article to Contentful as a draft and return status."""
        title = article.get("title", "Untitled")
        slug = article.get("slug", "untitled")
        body = article.get("body_markdown", "")
        meta = article.get("meta_description", "")

        # Save local backup
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_path = output_dir / f"{slug}_{timestamp}.json"
        with open(backup_path, "w") as f:
            json.dump(article, f, indent=2)

        md_path = output_dir / f"{slug}_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(f"# {title}\n\n")
            f.write(f"*{meta}*\n\n")
            f.write(body)

        # Attempt Contentful publish
        contentful_result = None
        try:
            contentful_result = asyncio.run(
                create_draft_entry(
                    title=title,
                    slug=slug,
                    body=body,
                    meta_description=meta,
                )
            )
        except Exception as e:
            contentful_result = {
                "status": "failed",
                "error": str(e),
                "note": "Article saved locally. Configure Contentful credentials in .env to enable publishing.",
            }

        result = {
            "status": "complete",
            "title": title,
            "slug": slug,
            "word_count": article.get("word_count", 0),
            "local_backup": str(backup_path),
            "local_markdown": str(md_path),
            "contentful": contentful_result,
            "completed_at": datetime.now().isoformat(),
        }

        # Alert the user
        self._notify(result)

        return result

    def _notify(self, result: dict) -> None:
        """Print completion notification to stdout."""
        status = result["contentful"].get("status", "unknown")
        print("\n" + "=" * 60)
        print("  CONTENT PIPELINE COMPLETE")
        print("=" * 60)
        print(f"  Title:      {result['title']}")
        print(f"  Slug:       {result['slug']}")
        print(f"  Words:      {result['word_count']}")
        print(f"  Local file: {result['local_markdown']}")
        if status == "draft":
            entry_id = result["contentful"].get("entry_id", "")
            print(f"  Contentful: Draft created (ID: {entry_id})")
        else:
            print(f"  Contentful: {status}")
            if "note" in result["contentful"]:
                print(f"  Note:       {result['contentful']['note']}")
        print(f"  Completed:  {result['completed_at']}")
        print("=" * 60 + "\n")
