#!/usr/bin/env python3
"""DWC Content Pipeline - Agent SDK powered content swarm.

Usage:
    python main.py "topic"               # Run the full pipeline
    python main.py "topic" --verbose      # Verbose output
    python main.py --seed                 # Seed memory with existing DWC content (run once)
    python main.py --suggest              # Show keyword opportunities from memory
    python main.py --scout               # Run competitive scan now
    python main.py --daemon              # Start the daily scheduler
"""

import argparse
import sys

from config.settings import ANTHROPIC_API_KEY


def main():
    parser = argparse.ArgumentParser(description="DWC Content Pipeline")
    parser.add_argument("topic", nargs="?", help="Topic seed for the content pipeline")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--seed", action="store_true", help="Seed memory with existing DWC content (run once)")
    parser.add_argument("--suggest", action="store_true", help="Show keyword opportunities from memory")
    parser.add_argument("--scout", action="store_true", help="Run competitive scan now")
    parser.add_argument("--daemon", action="store_true", help="Start the daily scheduler")

    args = parser.parse_args()

    if not ANTHROPIC_API_KEY and not args.seed and not args.suggest:
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    if args.seed:
        from memory.seed import seed
        seed()
        return

    if args.suggest:
        from memory.store import get_published_content, get_cluster_map
        published = get_published_content()
        clusters = get_cluster_map()

        print(f"\nPublished articles: {len(published)}")
        for p in published:
            print(f"  - {p['title']} ({p['primary_keyword']})")

        print(f"\nTopical clusters: {len(clusters)}")
        for c in clusters:
            opportunities = [k for k in c.get("keywords", []) if k.get("status") == "opportunity"]
            published_kw = [k for k in c.get("keywords", []) if k.get("status") == "published"]
            print(f"  {c['name']}: {len(published_kw)} published, {len(opportunities)} opportunities")
            for opp in opportunities[:3]:
                print(f"    - {opp['keyword']} (vol: {opp.get('volume', '?')}, KD: {opp.get('difficulty', '?')})")
        return

    if args.scout:
        from scheduler import run_daily_scout
        run_daily_scout()
        return

    if args.daemon:
        from scheduler import main as scheduler_main
        scheduler_main()
        return

    if not args.topic:
        parser.print_help()
        sys.exit(1)

    from pipeline import run_pipeline
    result = run_pipeline(args.topic, verbose=args.verbose)

    if result.get("status") == "success":
        print("\nPipeline complete.")
    else:
        print(f"\nPipeline finished with status: {result.get('status')}")
        if result.get("error"):
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
