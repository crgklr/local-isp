#!/usr/bin/env python3
"""DWC Content Pipeline - Agent swarm for wire & cable content strategy.

Usage:
    python main.py "topic seed phrase"
    python main.py "topic seed phrase" --verbose
    python main.py --suggest

Examples:
    python main.py "THHN vs XHHW wire: which should distributors stock?"
    python main.py "Understanding medium voltage cable for utility applications"
    python main.py "Tray cable types and applications for industrial projects"
    python main.py --suggest
"""

import argparse
import json
import sys

from config.settings import ANTHROPIC_API_KEY, KEYWORD_OPPORTUNITIES, DWC_EXISTING_CONTENT


def suggest_topics() -> list[str]:
    """Suggest content topics based on keyword gaps and opportunities."""
    existing_keywords = {c["keyword"].lower() for c in DWC_EXISTING_CONTENT}

    suggestions = []
    for kw in KEYWORD_OPPORTUNITIES:
        if kw["keyword"].lower() not in existing_keywords:
            vol = kw.get("volume", 0) or 0
            diff = kw.get("difficulty")
            diff_str = str(diff) if diff is not None else "?"
            suggestions.append({
                "keyword": kw["keyword"],
                "volume": vol,
                "difficulty": diff_str,
            })

    suggestions.sort(key=lambda x: x["volume"], reverse=True)
    return suggestions


def main():
    parser = argparse.ArgumentParser(
        description="DWC Content Pipeline - Wire & Cable Content Agent Swarm"
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="The topic seed for the content pipeline",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output from each agent",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Show suggested topics based on keyword opportunities",
    )

    args = parser.parse_args()

    if args.suggest:
        suggestions = suggest_topics()
        print("\nSuggested Content Topics (based on keyword gaps):\n")
        print(f"{'Keyword':<40} {'Volume':>8} {'Difficulty':>12}")
        print("-" * 62)
        for s in suggestions:
            print(f"{s['keyword']:<40} {s['volume']:>8} {s['difficulty']:>12}")
        print(f"\nTotal opportunities: {len(suggestions)}")
        print("\nRun with a topic to start the pipeline:")
        print('  python main.py "your topic here"')
        return

    if not args.topic:
        parser.print_help()
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    from pipeline import run_pipeline
    result = run_pipeline(args.topic, verbose=args.verbose)

    sys.exit(0)


if __name__ == "__main__":
    main()
