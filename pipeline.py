"""Content Pipeline Orchestrator - Agent SDK powered.

Uses query() with subagent delegation for the full content pipeline.
Includes Distributor Value Analyst for scoring content impact.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

from agents.definitions import (
    DOMAIN_RESEARCHER, SEO_RESEARCHER, OUTLINE_ARCHITECT,
    WRITER, FACT_CHECKER, EDITOR_IN_CHIEF, CANARY,
    DISTRIBUTOR_VALUE_ANALYST,
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
            "value-analyst": AgentDefinition(**DISTRIBUTOR_VALUE_ANALYST),
            "outline-architect": AgentDefinition(**OUTLINE_ARCHITECT),
            "writer": AgentDefinition(**WRITER),
            "fact-checker": AgentDefinition(**FACT_CHECKER),
            "editor-in-chief": AgentDefinition(**EDITOR_IN_CHIEF),
            "canary": AgentDefinition(**CANARY),
        },
        max_turns=70,
    )


async def run_pipeline_async(topic: str, verbose: bool = False) -> dict:
    console.print(Panel(f"[bold]Topic:[/bold] {topic}", title="Content Pipeline", border_style="blue"))

    orchestrator_prompt = f"""You are the content pipeline orchestrator for Distributor Wire & Cable. Execute these steps in order:

TOPIC: {topic}

## Step 1: Domain Research
Use domain-researcher agent. Pass the topic. It will check Contentful for existing content and research the topic. If this topic already exists in Contentful, the researcher should identify what's already covered and suggest a complementary angle that hasn't been written yet. Do NOT stop the pipeline. Instead, refine the topic to something unique and complementary.

## Step 2: SEO/GEO Research
Use seo-researcher agent. Pass the (potentially refined) topic AND domain brief. It will query Ahrefs live for keywords, SERPs, and cannibalization checks.

## Step 3: Value Analysis
Use value-analyst agent. Pass the topic, domain brief, and SEO brief. It will score the content opportunity on four dimensions: deal impact, sales enablement, contractor question frequency, and strategic value to DWC. If the total score is below 50, note the analyst's suggested angle adjustment and consider refining the topic before proceeding. If below 30, report back that this topic isn't worth pursuing and suggest the analyst's alternative.

## Step 4: Content Brief
Combine the domain research, SEO research, and value analysis into a content brief. Include the value analyst's angle recommendations.

## Step 5: Outline
Use outline-architect agent. Pass the full content brief.

## Step 6: Write
Use writer agent. Pass the outline AND content brief.

## Step 7: Fact Check
Use fact-checker agent. Pass the article and content brief. Note if accuracy < 80.

## Step 8: Edit
Use editor-in-chief agent. Pass the fact-checked article.

## Step 9: Publish
Use canary agent. Pass the final article (title, slug, body_markdown, meta_description, word_count). It will check the slug doesn't already exist in Contentful before publishing.

Pass FULL output from each agent to the next. Report final title, slug, word count, value score, and Contentful status."""

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
