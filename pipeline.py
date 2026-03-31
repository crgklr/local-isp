"""Content Pipeline Orchestrator - Agent SDK powered.

Uses query() with subagent delegation for the full content pipeline.
Each agent runs in its own context with specific MCP tool servers.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

from agents.definitions import (
    DOMAIN_RESEARCHER, SEO_RESEARCHER, OUTLINE_ARCHITECT,
    WRITER, FACT_CHECKER, EDITOR_IN_CHIEF, CANARY,
)
from tools.ahrefs_tools import ahrefs_server
from tools.contentful_tools import contentful_server
from tools.memory_tools import memory_server

from rich.console import Console
from rich.panel import Panel

console = Console()


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        mcp_servers={"ahrefs": ahrefs_server, "contentful": contentful_server, "memory": memory_server},
        allowed_tools=["Agent"],
        agents={
            "domain-researcher": AgentDefinition(**DOMAIN_RESEARCHER),
            "seo-researcher": AgentDefinition(**SEO_RESEARCHER),
            "outline-architect": AgentDefinition(**OUTLINE_ARCHITECT),
            "writer": AgentDefinition(**WRITER),
            "fact-checker": AgentDefinition(**FACT_CHECKER),
            "editor-in-chief": AgentDefinition(**EDITOR_IN_CHIEF),
            "canary": AgentDefinition(**CANARY),
        },
        max_turns=60,
    )


async def run_pipeline_async(topic: str, verbose: bool = False) -> dict:
    console.print(Panel(f"[bold]Topic:[/bold] {topic}", title="Content Pipeline", border_style="blue"))

    orchestrator_prompt = f"""You are the content pipeline orchestrator for Distributor Wire & Cable. Execute these steps in order:

TOPIC: {topic}

## Step 1: Domain Research
Use domain-researcher agent. Pass the topic. It will check Contentful for existing content (source of truth) and research the topic. Get a research brief covering technical details, distributor pain points, sales angles, DWC product relevance. If this exact topic already exists in Contentful, STOP and report that it's already covered.

## Step 2: SEO/GEO Research
Use seo-researcher agent. Pass the topic AND domain brief. It will query Ahrefs live for keywords, SERPs, and cannibalization checks.

## Step 3: Content Brief
Combine both briefs. Note target word count, primary keyword, top pain points.

## Step 4: Outline
Use outline-architect agent. Pass the full content brief.

## Step 5: Write
Use writer agent. Pass the outline AND content brief.

## Step 6: Fact Check
Use fact-checker agent. Pass the article and content brief. Note if accuracy < 80.

## Step 7: Edit
Use editor-in-chief agent. Pass the fact-checked article.

## Step 8: Publish
Use canary agent. Pass the final article (title, slug, body_markdown, meta_description, word_count). It will check the slug doesn't already exist in Contentful before publishing.

Pass FULL output from each agent to the next. Report final title, slug, word count, and Contentful status."""

    result_data = {"topic": topic, "status": "unknown"}

    async for message in query(prompt=orchestrator_prompt, options=_build_options()):
        if isinstance(message, ResultMessage):
            if message.subtype == "success":
                result_data["status"] = "success"
                result_data["result"] = message.result
                if hasattr(message, "total_cost_usd"):
                    result_data["cost_usd"] = message.total_cost_usd
            else:
                result_data["status"] = "error"
                result_data["error"] = str(message.result)
        elif verbose and hasattr(message, "message"):
            for block in message.message.content:
                if hasattr(block, "text") and block.text:
                    console.print(f"[dim]{block.text[:200]}[/dim]")
                elif block.type == "tool_use":
                    console.print(f"  [cyan]> {block.name}[/cyan]")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    state_path = output_dir / f"pipeline_{topic[:40].replace(' ', '_')}.json"
    with open(state_path, "w") as f:
        json.dump(result_data, f, indent=2, default=str)

    console.print(f"\n[dim]State saved: {state_path}[/dim]")
    if result_data.get("cost_usd"):
        console.print(f"[dim]Cost: ${result_data['cost_usd']:.4f}[/dim]")

    return result_data


def run_pipeline(topic: str, verbose: bool = False) -> dict:
    return asyncio.run(run_pipeline_async(topic, verbose=verbose))
