"""Content Pipeline Orchestrator - Agent SDK powered.

Uses query() with subagent delegation for the full content pipeline.
Includes quality gates and feedback loops: the orchestrator sends work
back to agents for revision when quality checks fail.

Orchestrator runs on Opus 4.6 for best judgment on quality gates.
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
from config.settings import MODEL_ORCHESTRATOR
from tools.ahrefs_tools import ahrefs_server
from tools.contentful_tools import contentful_server
from tools.memory_tools import memory_server

from rich.console import Console
from rich.panel import Panel

console = Console()


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL_ORCHESTRATOR,
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
        max_turns=120,
    )


async def run_pipeline_async(topic: str, verbose: bool = False) -> dict:
    console.print(Panel(f"[bold]Topic:[/bold] {topic}", title="Content Pipeline", border_style="blue"))

    orchestrator_prompt = f"""You are the content pipeline orchestrator for Distributor Wire & Cable. You manage a team of specialist agents and are responsible for quality control. You do NOT just run agents in sequence and hope for the best. You review each agent's output and send work back for revision when it doesn't meet standards.

TOPIC: {topic}

## Step 1: Domain Research
Use domain-researcher agent. Pass the topic. It will check Contentful for existing content and research the topic. If this topic already exists in Contentful, the researcher should identify what's already covered and suggest a complementary angle that hasn't been written yet.

QUALITY CHECK: The brief must include at least 5 key_concepts, at least 3 distributor_pain_points, and specific DWC product relevance. If it's thin or generic, send it back with specific feedback on what's missing.

## Step 2: SEO/GEO Research
Use seo-researcher agent. Pass the (potentially refined) topic AND domain brief. It queries Ahrefs live for keywords, SERPs, and cannibalization checks.

QUALITY CHECK: The brief must include a primary_keyword with real volume data, at least 3 secondary_keywords, and fan_out_queries. If the primary keyword has KD > 50 and DWC's DR can't compete, send it back and ask for a lower-difficulty alternative.

## Step 3: Value Analysis
Use value-analyst agent. Pass the topic, domain brief, and SEO brief.

QUALITY GATE:
- Score >= 70: Proceed with confidence.
- Score 50-69: Note the analyst's suggested_angle. If the suggestion is materially different, re-run Step 1 and Step 2 with the refined topic before proceeding.
- Score 30-49: The analyst's suggested_angle becomes the new topic. Re-run Steps 1 and 2 with the new angle. Re-run the value analyst to confirm the new angle scores higher.
- Score < 30: STOP the pipeline. Report that this topic isn't worth pursuing and return the analyst's recommendation.

## Step 4: Content Brief
Combine the domain research, SEO research, and value analysis into a content brief. Include the value analyst's angle recommendations and distributor_perspective.

## Step 5: Outline
Use outline-architect agent. Pass the full content brief.

QUALITY CHECK: The outline must have at least 6 sections, a target word count >= 1500, and at least 2 internal link opportunities. If it's too shallow, send it back with the specific subtopics from the domain brief that it missed.

## Step 6: Write
Use writer agent. Pass the outline AND content brief.

QUALITY CHECK: Verify the article meets the target word count (within 20%). Check that it includes at least one table and an FAQ section. If it's short or missing key sections from the outline, send it back with specific instructions on what to add.

## Step 7: Fact Check
Use fact-checker agent. Pass the article and content brief.

QUALITY GATE:
- All scores >= 80: Proceed to editing.
- accuracy_score < 80: Send the corrected article BACK to the writer agent with the fact checker's corrections and ask the writer to revise (not just patch, but rewrite the problematic sections properly). Then re-run the fact checker on the revised version. Maximum 2 revision rounds.
- alignment_score < 80: The article references products DWC doesn't sell or targets contractors instead of distributors. Send it back to the writer with specific corrections needed.
- audience_score < 80: The tone is wrong. Send it back to the writer with the fact checker's notes on what needs to change.

## Step 8: Edit
Use editor-in-chief agent. Pass the fact-checked (and potentially revised) article.

QUALITY CHECK: If the editor reports more than 15 edits, the writing quality was poor. Note this for the final report but proceed (the editor has already fixed it).

## Step 9: Publish
Use canary agent. Pass the final article (title, slug, body_markdown, meta_description, word_count). It will check the slug doesn't already exist in Contentful before publishing.

## Revision Protocol
When sending work back to an agent for revision:
1. Include the ORIGINAL output that failed the quality check
2. Include the SPECIFIC feedback on what needs to improve
3. Include the quality check criteria that weren't met
4. Ask the agent to revise and return the complete updated output

Maximum 2 revision rounds per agent. If quality still doesn't pass after 2 rounds, proceed with the best version available and flag the issues in the final report.

## Final Report
Always end with a summary: title, slug, word count, value score, fact check scores, number of revisions needed, and Contentful status. If any quality gates required revisions, note which agents needed rework and why."""

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
