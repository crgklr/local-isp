"""Content Pipeline Orchestrator - Runs the full agent swarm."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.domain_researcher import DomainResearcherAgent
from agents.seo_researcher import SEOResearcherAgent
from agents.outline_agent import OutlineAgent
from agents.writer import WriterAgent
from agents.fact_checker import FactCheckerAgent
from agents.editor import EditorInChiefAgent
from agents.canary import CanaryAgent
from models.content import PipelineStage, PipelineState

console = Console()


def run_pipeline(topic: str, verbose: bool = False) -> dict:
    """Execute the full content pipeline for a given topic.

    Stages:
    1. Domain Research + SEO Research (domain runs first, SEO uses its output)
    2. Outline creation from combined brief
    3. Article writing from outline
    4. Fact checking
    5. Editorial polish
    6. Publish to Contentful as draft + notify
    """
    state = PipelineState(topic_seed=topic)

    console.print(Panel(
        f"[bold]Topic:[/bold] {topic}",
        title="Content Pipeline Started",
        border_style="blue",
    ))

    # Stage 1: Domain Expert Research
    console.print("\n[bold cyan]Stage 1/6:[/bold cyan] Domain Expert Research")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Domain expert analyzing topic...", total=None)
        domain_agent = DomainResearcherAgent()
        domain_brief = domain_agent.research(topic)
        state.stage = PipelineStage.SEO_RESEARCH
        progress.update(task, description="[green]Domain research complete")

    if verbose:
        console.print_json(json.dumps(domain_brief, indent=2))

    console.print(f"  Key concepts identified: {len(domain_brief.get('key_concepts', []))}")
    console.print(f"  Pain points found: {len(domain_brief.get('distributor_pain_points', []))}")

    # Stage 2: SEO/GEO Research (informed by domain research, live Ahrefs data)
    console.print("\n[bold cyan]Stage 2/6:[/bold cyan] SEO/GEO Research [dim](live Ahrefs queries)[/dim]")
    console.print("  [dim]Agent will autonomously query Ahrefs for keyword data, SERP analysis,[/dim]")
    console.print("  [dim]competitor intel, and content gap opportunities...[/dim]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("SEO strategist querying Ahrefs...", total=None)
        seo_agent = SEOResearcherAgent()
        seo_brief = seo_agent.research(topic, domain_brief)
        state.stage = PipelineStage.OUTLINE
        progress.update(task, description="[green]SEO research complete (live Ahrefs data)")

    if verbose:
        console.print_json(json.dumps(seo_brief, indent=2))

    console.print(f"  Primary keyword: {seo_brief.get('primary_keyword', 'N/A')}")
    console.print(f"  Secondary keywords: {len(seo_brief.get('secondary_keywords', []))}")
    console.print(f"  Keyword data points: {len(seo_brief.get('keyword_data', []))}")
    console.print(f"  Recommended word count: {seo_brief.get('recommended_word_count', 'N/A')}")
    if seo_brief.get("ahrefs_data_summary"):
        console.print(f"  [dim]Ahrefs summary: {seo_brief['ahrefs_data_summary'][:120]}...[/dim]")

    # Combine into content brief
    content_brief = {
        "domain_research": domain_brief,
        "seo_research": seo_brief,
        "combined_recommendations": (
            f"Write a {seo_brief.get('recommended_word_count', 2000)}-word article targeting "
            f"'{seo_brief.get('primary_keyword', topic)}' for electrical distributors. "
            f"The content should address these distributor pain points: "
            f"{', '.join(domain_brief.get('distributor_pain_points', [])[:3])}. "
            f"Optimize for both traditional search and AI discoverability."
        ),
    }

    # Stage 3: Outline Creation
    console.print("\n[bold cyan]Stage 3/6:[/bold cyan] Outline Creation")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Outline architect structuring content...", total=None)
        outline_agent = OutlineAgent()
        outline = outline_agent.create_outline(content_brief)
        state.stage = PipelineStage.WRITING
        progress.update(task, description="[green]Outline complete")

    if verbose:
        console.print_json(json.dumps(outline, indent=2))

    console.print(f"  Title: {outline.get('title', 'N/A')}")
    console.print(f"  Sections: {len(outline.get('sections', []))}")
    console.print(f"  Target words: {outline.get('target_word_count', 'N/A')}")

    # Stage 4: Writing
    console.print("\n[bold cyan]Stage 4/6:[/bold cyan] Writing")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Writer crafting the article...", total=None)
        writer = WriterAgent()
        article = writer.write(outline, content_brief)
        state.stage = PipelineStage.FACT_CHECK
        progress.update(task, description="[green]Draft complete")

    if verbose:
        console.print_json(json.dumps({k: v for k, v in article.items() if k != "body_markdown"}, indent=2))

    console.print(f"  Word count: {article.get('word_count', 'N/A')}")
    console.print(f"  Slug: {article.get('slug', 'N/A')}")

    # Stage 5: Fact Checking
    console.print("\n[bold cyan]Stage 5/6:[/bold cyan] Fact Checking")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Fact checker reviewing article...", total=None)
        fact_checker = FactCheckerAgent()
        fact_check_result = fact_checker.check(article, content_brief)
        state.stage = PipelineStage.EDITING
        progress.update(task, description="[green]Fact check complete")

    corrections = fact_check_result.get("corrections_made", [])
    console.print(f"  Corrections made: {len(corrections)}")
    console.print(f"  Accuracy score: {fact_check_result.get('accuracy_score', 'N/A')}/100")
    console.print(f"  Alignment score: {fact_check_result.get('alignment_score', 'N/A')}/100")
    console.print(f"  Audience score: {fact_check_result.get('audience_score', 'N/A')}/100")

    if corrections and verbose:
        for c in corrections[:5]:
            console.print(f"  [yellow]Fixed:[/yellow] {c.get('reason', '')}")

    checked_article = fact_check_result.get("corrected_article", article)

    # Stage 6: Editorial Polish
    console.print("\n[bold cyan]Stage 6/6:[/bold cyan] Editor in Chief Review")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Editor in Chief polishing article...", total=None)
        editor = EditorInChiefAgent()
        editor_result = editor.edit(checked_article)
        state.stage = PipelineStage.PUBLISHING
        progress.update(task, description="[green]Editing complete")

    edits = editor_result.get("edits_made", [])
    console.print(f"  Edits made: {len(edits)}")
    console.print(f"  Assessment: {editor_result.get('overall_assessment', 'N/A')}")

    final_article = editor_result.get("final_article", checked_article)

    # Publish
    console.print("\n[bold cyan]Publishing:[/bold cyan] Contentful Draft + Local Backup")
    canary = CanaryAgent()
    publish_result = canary.publish_and_notify(final_article)

    state.stage = PipelineStage.COMPLETE

    # Save full pipeline state
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    state_path = output_dir / f"pipeline_state_{final_article.get('slug', 'article')}.json"
    with open(state_path, "w") as f:
        json.dump({
            "topic": topic,
            "domain_brief": domain_brief,
            "seo_brief": seo_brief,
            "outline": outline,
            "draft_article": article,
            "fact_check_result": {
                "corrections_made": corrections,
                "accuracy_score": fact_check_result.get("accuracy_score"),
                "alignment_score": fact_check_result.get("alignment_score"),
                "audience_score": fact_check_result.get("audience_score"),
            },
            "editor_result": {
                "edits_made": edits,
                "overall_assessment": editor_result.get("overall_assessment"),
            },
            "final_article": final_article,
            "publish_result": publish_result,
        }, f, indent=2)

    console.print(f"\n[dim]Full pipeline state saved to: {state_path}[/dim]")

    return publish_result
