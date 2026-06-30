#!/usr/bin/env python3

# /// script
# dependencies = [
#     "python-dotenv",
#     "requests",
# ]
# ///

"""OpenRouter Real-Time Infrastructure Endpoint Tracker.

This script queries OpenRouter's backend provider-level endpoint data
(incorporating ZDR state analytics) to discover, filter, and monitor active
coding and reasoning models by their actual live host processing rates.

Downselects models based on:
    - intended use as code assistant
    - inclusion of reasoning capabilites
    - age, i.e., modles that have been released "recently"

Usage:
    # Create a .env file with:
    #   OPENROUTER_API_KEY="your-sk-or-key-here"
    uv run openrouter_tracker.py [--months 6] [--limit]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

# Load environment variables from .env file at project root or CWD
load_dotenv()

# Snapshot Ledger Configuration
SNAPSHOT_DIR = os.path.expanduser("~/.config/openrouter_tracker")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
SNAPSHOT_PATH = os.path.join(SNAPSHOT_DIR, f"models_{TODAY_STR}.json")


def parse_arguments():
    """Parses optional pipeline constraint flags from execution context."""
    parser = argparse.ArgumentParser(
        description="OpenRouter Real-Time Infrastructure Tracker"
    )
    parser.add_argument(
        "-m",
        "--months",
        type=int,
        default=6,
        help="Number of months back to evaluate for model recency (default: 6)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        help="Maximum sorted rows to display. If omitted, spits out all matches.",
    )
    return parser.parse_args()


def fetch_and_filter_endpoints(months_back, limit_count):
    """Queries live endpoint configurations using explicit Bearer token context."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "[!] Execution Error: OPENROUTER_API_KEY environment variable is missing.",
            file=sys.stderr,
        )
        print(
            "    Ensure OPENROUTER_API_KEY is set in a .env file, or export it.",
            file=sys.stderr,
        )
        sys.exit(1)

    url = "https://openrouter.ai/api/v1/endpoints/zdr"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json().get("data", [])
    except Exception as e:
        print(
            f"Error fetching data from OpenRouter infrastructure feed: {e}",
            file=sys.stderr,
        )
        return []

    filtered_models = {}
    recency_threshold = datetime.now() - timedelta(days=months_back * 30)

    for ep in data:
        model_id = ep.get("model_id")
        pricing = ep.get("pricing", {}) or {}
        params = ep.get("supported_parameters", []) or []

        if not model_id:
            continue

        # 1. Evaluate True Token Pricing Structure
        try:
            out_price_raw = float(pricing.get("completion", 0))
            in_price_raw = float(pricing.get("prompt", 0))
        except (ValueError, TypeError):
            continue

        # Standardize micro-fractions to standard Cost Per Million (1M) Tokens
        out_price_m = out_price_raw * 1_000_000
        in_price_m = in_price_raw * 1_000_000

        # Exclude completely subsidized / broken placeholder entries
        if out_price_m <= 0:
            continue

        # 2. Reasoning Core Validation
        has_reasoning = "reasoning" in params or "include_reasoning" in params
        if not has_reasoning:
            continue

        # 3. Context Keyword Filter
        id_lower = model_id.lower()
        model_name_lower = ep.get("model_name", "").lower()
        is_coding = any(
            k in id_lower or k in model_name_lower
            for k in [
                "code",
                "coder",
                "instruct",
                "preview",
                "pro",
                "deepseek",
                "qwen",
                "flash",
                "llama-3",
            ]
        )
        if not is_coding:
            continue

        # 4. Recency Filter Evaluation
        # Note: If the creation timestamp isn't explicitly on the endpoint payload,
        # fallback allows processing to prevent filtering out newly launched routes.
        created_timestamp = ep.get("created")
        if created_timestamp:
            try:
                created_dt = datetime.fromtimestamp(int(created_timestamp))
                if created_dt < recency_threshold:
                    continue
            except (ValueError, TypeError):
                pass

        # Check for explicit pricing fields in the endpoint object
        pricing_keys = pricing.keys() if isinstance(pricing, dict) else []
        has_explicit_caching = (
            "input_cache_read" in pricing_keys or "input_cache_write" in pricing_keys
        )

        # Check if the provider flags implicit caching support directly
        has_implicit_caching = ep.get("supports_implicit_caching") is True

        # Fallback: Is it an industry-standard architecture known for native caching?
        known_caching_family = any(
            fam in id_lower
            for fam in ["deepseek", "qwen", "claude", "anthropic", "openai", "o3"]
        )

        # Combine checks to guarantee you don't drop viable options
        if not (has_explicit_caching or has_implicit_caching or known_caching_family):
            continue

        # De-duplicate models by selecting the absolute lowest hosting fee variant available
        if (
            model_id not in filtered_models
            or out_price_m < filtered_models[model_id]["output_price"]
        ):
            filtered_models[model_id] = {
                "id": model_id,
                "name": ep.get("model_name", model_id),
                "output_price": out_price_m,
                "input_price": in_price_m,
                "provider": ep.get("provider_name", "Unknown"),
            }

    # Sort the filtered selection by lowest completion cost
    sorted_models = sorted(filtered_models.values(), key=lambda x: x["output_price"])

    # Return slice if limit is specified, else return entire matching catalog
    return sorted_models[:limit_count] if limit_count else sorted_models


def get_yesterday_snapshot():
    """Reads snapshot index from the previous calendar date."""
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_path = os.path.join(SNAPSHOT_DIR, f"models_{yesterday_str}.json")
    if os.path.exists(yesterday_path):
        with open(yesterday_path, "r") as f:
            return json.load(f)
    return None


def generate_diff_report(current, previous):
    """Compares snapshots and logs structural additions, removals, and cost ranking shifts."""
    if not previous:
        print(
            "\n[!] Initial baseline stored. Tomorrow's execution will generate tracking diffs."
        )
        return

    curr_ids = [m["id"] for m in current]
    prev_ids = [m["id"] for m in previous]

    added = [i for i in curr_ids if i not in prev_ids]
    removed = [i for i in prev_ids if i not in curr_ids]

    print("\n" + "=" * 50)
    print(f" DAILY INFRASTRUCTURE REPORT: {TODAY_STR}")
    print("=" * 50)

    if added:
        print("\n✨ NEW ENTRY DISCOVERED IN RANKINGS:")
        for idx in added:
            print(f"  + {idx}")
    if removed:
        print("\n❌ REMOVED FROM RANKINGS:")
        for idx in removed:
            print(f"  - {idx}")

    print("\n📈 RANKING CHANGES (By Provider Output Price):")
    has_shifts = False
    for curr_idx, m in enumerate(current):
        m_id = m["id"]
        if m_id in prev_ids:
            prev_idx = prev_ids.index(m_id)
            if curr_idx < prev_idx:
                print(f"  ▲ {m_id} moved UP (Rank {prev_idx + 1} ➔ {curr_idx + 1})")
                has_shifts = True
            elif curr_idx > prev_idx:
                print(f"  ▼ {m_id} moved DOWN (Rank {prev_idx + 1} ➔ {curr_idx + 1})")
                has_shifts = True

    if not added and not removed and not has_shifts:
        print(
            "  No architectural shifts or provider price updates detected since yesterday."
        )


def main():
    """Execution entry point."""
    args = parse_arguments()

    current_catalog = fetch_and_filter_endpoints(
        months_back=args.months, limit_count=args.limit
    )

    # Cache today's snapshot file locally
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(current_catalog, f, indent=2)

    limit_label = f"TOP {args.limit}" if args.limit else "FULL"
    print(
        f"\n--- {limit_label} REASONING & CODING ENDPOINT DISCOVERY ({TODAY_STR}) ---"
    )
    for i, m in enumerate(current_catalog, 1):
        print(
            f"{i:2d}. {m['id']:<45} | Out: ${m['output_price']:.2f}/M | In: ${m['input_price']:.2f}/M via {m['provider']}"
        )

    yesterday_data = get_yesterday_snapshot()
    generate_diff_report(current_catalog, yesterday_data)


if __name__ == "__main__":
    main()
