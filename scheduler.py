"""Daily scheduler - competitive scout + email-driven content workflow.

Runs two loops:
1. Daily scout: scans competitors via Ahrefs, emails you suggestions
2. Reply poller: checks for your email reply, triggers the content pipeline

Usage:
    python scheduler.py              # Run both loops (scout + reply poller)
    python scheduler.py --scout-now  # Run the scout scan immediately
    python scheduler.py --poll-now   # Check for replies immediately
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console

from agents.competitive_scout import CompetitiveScoutAgent
from integrations.email_service import (
    send_suggestions_email,
    send_completion_email,
    poll_for_reply,
)
from pipeline import run_pipeline
from config.settings import (
    SCOUT_SCHEDULE_HOUR,
    SCOUT_SCHEDULE_MINUTE,
    REPLY_POLL_INTERVAL_MINUTES,
    EMAIL_TO,
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


def run_daily_scout() -> dict:
    """Execute the competitive scout and email the results."""
    console.print("\n[bold blue]Running daily competitive scan...[/bold blue]")

    scout = CompetitiveScoutAgent()
    report = scout.scan()

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"scout_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    console.print(f"  Scout report saved to: {report_path}")

    clusters = report.get("clusters", [])
    console.print(f"  Clusters found: {len(clusters)}")
    for i, c in enumerate(clusters, 1):
        rec = c.get("recommended_topic", {})
        console.print(f"    {i}. [{c.get('cluster_name', '?')}] {rec.get('title', '?')}")
        console.print(f"       KW: {rec.get('primary_keyword', '?')} | Vol: {rec.get('volume', '?')} | KD: {rec.get('difficulty', '?')}")

    if EMAIL_TO:
        console.print(f"\n  Emailing suggestions to {EMAIL_TO}...")
        email_result = send_suggestions_email(report)
        console.print(f"  Email: {email_result.get('status', 'unknown')}")
    else:
        console.print("  [yellow]No EMAIL_TO configured, skipping email.[/yellow]")

    state = load_state()
    state["last_scan"] = datetime.now().isoformat()
    state["last_report"] = str(report_path)
    state["pending_suggestions"] = report
    save_state(state)

    return report


def check_for_reply() -> bool:
    """Poll for an email reply and trigger the pipeline if found."""
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
        console.print(f"  [yellow]Reply selected #{selection} but only {len(clusters)} options exist. Ignoring.[/yellow]")
        return False

    cluster = clusters[selection - 1]
    rec = cluster["recommended_topic"]
    topic = rec.get("title", rec.get("primary_keyword", ""))
    if notes:
        topic = f"{topic} ({notes})"

    console.print(f"\n[bold green]Reply received! Selected #{selection}:[/bold green] {topic}")
    console.print("  Starting content pipeline...")

    result = run_pipeline(topic)

    if EMAIL_TO:
        article_title = result.get("title", topic)
        article_slug = result.get("slug", "")
        contentful = result.get("contentful", {})
        send_completion_email(article_title, article_slug, contentful)
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
        wait_seconds = _seconds_until(SCOUT_SCHEDULE_HOUR, SCOUT_SCHEDULE_MINUTE)
        console.print(
            f"[dim]Next scout scan at {SCOUT_SCHEDULE_HOUR:02d}:{SCOUT_SCHEDULE_MINUTE:02d} "
            f"({wait_seconds // 3600}h {(wait_seconds % 3600) // 60}m from now)[/dim]"
        )
        if stop_event.wait(timeout=wait_seconds):
            break
        try:
            run_daily_scout()
        except Exception as e:
            console.print(f"[red]Scout error: {e}[/red]")


def run_reply_loop(stop_event: threading.Event) -> None:
    interval = REPLY_POLL_INTERVAL_MINUTES * 60
    while not stop_event.is_set():
        try:
            processed = check_for_reply()
            if processed:
                console.print("[green]Pipeline complete. Waiting for next scout scan.[/green]")
        except Exception as e:
            console.print(f"[red]Reply poll error: {e}[/red]")
        if stop_event.wait(timeout=interval):
            break


def main():
    parser = argparse.ArgumentParser(description="DWC Content Agent Scheduler")
    parser.add_argument("--scout-now", action="store_true", help="Run scout scan immediately")
    parser.add_argument("--poll-now", action="store_true", help="Check for email replies now")
    args = parser.parse_args()

    if args.scout_now:
        run_daily_scout()
        return

    if args.poll_now:
        found = check_for_reply()
        if not found:
            console.print("No reply found.")
        return

    console.print("[bold]DWC Content Agent Scheduler[/bold]")
    console.print(f"  Scout schedule: daily at {SCOUT_SCHEDULE_HOUR:02d}:{SCOUT_SCHEDULE_MINUTE:02d}")
    console.print(f"  Reply polling: every {REPLY_POLL_INTERVAL_MINUTES} minutes")
    console.print(f"  Email to: {EMAIL_TO or '(not configured)'}")
    console.print("  Press Ctrl+C to stop.\n")

    stop_event = threading.Event()

    def handle_signal(sig, frame):
        console.print("\n[yellow]Shutting down...[/yellow]")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    scout_thread = threading.Thread(target=run_scout_loop, args=(stop_event,), daemon=True)
    reply_thread = threading.Thread(target=run_reply_loop, args=(stop_event,), daemon=True)

    scout_thread.start()
    reply_thread.start()

    scout_thread.join()
    reply_thread.join()


if __name__ == "__main__":
    main()
