"""Daily scheduler - competitive scout + email-driven content workflow.

Uses Agent SDK for the scout agent and pipeline execution.

Usage:
    python scheduler.py              # Run both loops
    python scheduler.py --scout-now  # Scout scan immediately
    python scheduler.py --poll-now   # Check for replies immediately
"""

from __future__ import annotations

import asyncio
import argparse
import json
import signal
import threading
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

from agents.definitions import COMPETITIVE_SCOUT
from tools.ahrefs_tools import ahrefs_server
from tools.memory_tools import memory_server
from integrations.email_service import (
    send_suggestions_email, send_completion_email, poll_for_reply,
)
from pipeline import run_pipeline
from config.settings import (
    SCOUT_SCHEDULE_HOUR, SCOUT_SCHEDULE_MINUTE,
    REPLY_POLL_INTERVAL_MINUTES, EMAIL_TO,
)

console = Console()
STATE_FILE = Path("output/scheduler_state.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_scan": None, "last_report": None, "pending_suggestions": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


async def run_scout_async() -> dict:
    console.print("\n[bold blue]Running competitive scan via Agent SDK...[/bold blue]")

    options = ClaudeAgentOptions(
        mcp_servers={"ahrefs": ahrefs_server, "memory": memory_server},
        allowed_tools=["Agent"],
        agents={"competitive-scout": AgentDefinition(**COMPETITIVE_SCOUT)},
        max_turns=30,
    )

    prompt = f"""Use the competitive-scout agent to run a full scan for {datetime.now().strftime('%Y-%m-%d')}.
The scout should check DWC's keywords, scan competitors for gaps, find low-hanging fruit,
group into clusters, and update memory with results. Return the report as JSON."""

    report = {}
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            text = message.result
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    report = json.loads(text[start:end])
            except json.JSONDecodeError:
                report = {"raw_result": text}

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"scout_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    console.print(f"  Report: {report_path}")
    clusters = report.get("clusters", [])
    console.print(f"  Clusters: {len(clusters)}")
    for i, c in enumerate(clusters, 1):
        rec = c.get("recommended_topic", {})
        console.print(f"    {i}. [{c.get('cluster_name', '?')}] {rec.get('title', '?')}")

    return report


def run_daily_scout() -> dict:
    report = asyncio.run(run_scout_async())
    if EMAIL_TO:
        console.print(f"\n  Emailing to {EMAIL_TO}...")
        result = send_suggestions_email(report)
        console.print(f"  Email: {result.get('status', 'unknown')}")
    state = load_state()
    state["last_scan"] = datetime.now().isoformat()
    state["pending_suggestions"] = report
    save_state(state)
    return report


def check_for_reply() -> bool:
    state = load_state()
    pending = state.get("pending_suggestions")
    if not pending:
        return False
    reply = poll_for_reply(since_minutes=REPLY_POLL_INTERVAL_MINUTES + 2)
    if not reply:
        return False

    selection = reply["selection"]
    notes = reply.get("notes", "")
    clusters = pending.get("clusters", [])
    if selection < 1 or selection > len(clusters):
        console.print(f"  [yellow]#{selection} out of range ({len(clusters)} options)[/yellow]")
        return False

    cluster = clusters[selection - 1]
    rec = cluster["recommended_topic"]
    topic = rec.get("title", rec.get("primary_keyword", ""))
    if notes:
        topic = f"{topic} ({notes})"

    console.print(f"\n[bold green]Reply #{selection}:[/bold green] {topic}")
    result = run_pipeline(topic)

    if EMAIL_TO:
        send_completion_email(result.get("title", topic), result.get("slug", ""), result.get("contentful", {}))
        console.print(f"  Completion email sent to {EMAIL_TO}")

    state["pending_suggestions"] = None
    state["last_pipeline_run"] = datetime.now().isoformat()
    state["last_topic"] = topic
    save_state(state)
    return True


def _seconds_until(hour: int, minute: int) -> int:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return int((target - now).total_seconds())


def run_scout_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        wait = _seconds_until(SCOUT_SCHEDULE_HOUR, SCOUT_SCHEDULE_MINUTE)
        console.print(f"[dim]Next scan: {SCOUT_SCHEDULE_HOUR:02d}:{SCOUT_SCHEDULE_MINUTE:02d} ({wait // 3600}h {(wait % 3600) // 60}m)[/dim]")
        if stop_event.wait(timeout=wait):
            break
        try:
            run_daily_scout()
        except Exception as e:
            console.print(f"[red]Scout error: {e}[/red]")


def run_reply_loop(stop_event: threading.Event) -> None:
    interval = REPLY_POLL_INTERVAL_MINUTES * 60
    while not stop_event.is_set():
        try:
            if check_for_reply():
                console.print("[green]Pipeline complete.[/green]")
        except Exception as e:
            console.print(f"[red]Reply error: {e}[/red]")
        if stop_event.wait(timeout=interval):
            break


def main():
    parser = argparse.ArgumentParser(description="DWC Content Agent Scheduler")
    parser.add_argument("--scout-now", action="store_true")
    parser.add_argument("--poll-now", action="store_true")
    args = parser.parse_args()

    if args.scout_now:
        run_daily_scout()
        return
    if args.poll_now:
        if not check_for_reply():
            console.print("No reply found.")
        return

    console.print("[bold]DWC Content Agent Scheduler[/bold]")
    console.print(f"  Scout: daily at {SCOUT_SCHEDULE_HOUR:02d}:{SCOUT_SCHEDULE_MINUTE:02d}")
    console.print(f"  Reply poll: every {REPLY_POLL_INTERVAL_MINUTES}m")
    console.print(f"  Email: {EMAIL_TO or '(not set)'}")
    console.print("  Ctrl+C to stop.\n")

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: (console.print("\n[yellow]Stopping...[/yellow]"), stop.set()))
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    for t in [threading.Thread(target=run_scout_loop, args=(stop,), daemon=True),
              threading.Thread(target=run_reply_loop, args=(stop,), daemon=True)]:
        t.start()
    for t in threading.enumerate():
        if t.daemon:
            t.join()


if __name__ == "__main__":
    main()
