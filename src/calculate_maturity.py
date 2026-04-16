#!/usr/bin/env python3
"""Standalone CLI script: classify Copilot users by AI Maturity level.

Reads 28-day per-user metrics from the GitHub Copilot API and assigns each
licensed developer to one of 5 maturity levels:

  L5 ELITE AGENTIC   — agent_turns > 150 | cli_turns > 20 | autonomy > 30%
  L4 ADVANCED PILOT  — agent_turns [50–150] & chat_turns > 50
  L3 HYBRID EXPLORER — completions > 1000 & agent_turns [10–50)
  L2 TRADITIONALIST  — completions > 500   & agent_turns < 5
  L1 PASSIVE USER    — active_days < 3    | lines_accepted < 50

Usage:
    python src/calculate_maturity.py
    python src/calculate_maturity.py --output maturity.csv
    python src/calculate_maturity.py --days 28 --output /tmp/maturity.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path

# Allow running from either repo root or src/
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent if _HERE.name == "src" else _HERE
sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv  # type: ignore[import]
load_dotenv(_REPO / ".env", override=False)


def _classify(agent: int, cli: int, chat: int, completions: int,
              lines_accepted: int, active_days: int) -> int:
    """Return maturity level 1–5 (sequential, first match wins)."""
    total = agent + completions + chat + cli
    autonomy = agent / total if total else 0.0
    if agent > 150 or cli > 20 or autonomy > 0.30:
        return 5
    if 50 <= agent <= 150 and chat > 50:
        return 4
    if completions > 1000 and 10 <= agent < 50:
        return 3
    if completions > 500 and agent < 5:
        return 2
    return 1


_LEVEL_NAMES = {
    5: "L5 Elite Agentic",
    4: "L4 Advanced Pilot",
    3: "L3 Hybrid Explorer",
    2: "L2 Traditionalist",
    1: "L1 Passive User",
}


async def _run(output: str | None, days: int) -> None:  # noqa: ARG001 (days unused for now)
    from src.config import AppConfig
    from src.github_client.auth import build_github_auth
    from src.github_client.base_client import GitHubBaseClient
    from src.github_client.models import ReportDownloadResponse
    from src.github_client.usage_metrics_api import _unwrap_day_totals

    # Load config from environment
    config = AppConfig(
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        github_org=os.environ.get("GITHUB_ORG", ""),
        github_enterprise=os.environ.get("GITHUB_ENTERPRISE", ""),
    )
    if not config.github_token or not config.github_org:
        print("ERROR: GITHUB_TOKEN and GITHUB_ORG must be set in .env or environment.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching 28-day user metrics for org: {config.github_org} …")

    auth = build_github_auth(config)
    client = GitHubBaseClient(auth)
    try:
        resp = await client.get(
            f"/orgs/{config.github_org}/copilot/metrics/reports/users-28-day/latest"
        )
        dr = ReportDownloadResponse(**resp.json())
        raw: list[dict] = []
        for url in dr.download_links:
            raw.extend(await client.download_ndjson(url))
        records = _unwrap_day_totals(raw)
    finally:
        await client.close()

    print(f"  → {len(records)} per-user daily records fetched.")

    # Aggregate per login
    agg: dict[str, dict] = {}
    for rec in records:
        login = (
            rec.get("user_login") or rec.get("github_login") or rec.get("login") or ""
        ).lower()
        if not login:
            continue
        if login not in agg:
            agg[login] = {
                "agent": 0, "cli": 0, "chat": 0,
                "completions": 0, "lines_accepted": 0, "dates": set(),
            }
        u = agg[login]
        day = rec.get("date") or rec.get("day", "")
        if day:
            u["dates"].add(day)

        agent_val = rec.get("agent_turns", 0) or 0
        cli_val   = rec.get("cli_turns", 0) or 0
        chat_val  = rec.get("chat_turns", 0) or 0
        comp_val  = rec.get("completions_acceptances", 0) or 0
        lines_val = rec.get("completions_lines_accepted", 0) or 0

        for feat in rec.get("totals_by_feature", []):
            fname = feat.get("feature", "")
            if fname == "agent_edit":
                agent_val += feat.get("code_generation_activity_count", 0)
            elif fname == "code_completion":
                comp_val  += feat.get("code_acceptance_activity_count", 0)
                lines_val += feat.get("loc_added_sum", 0)
            elif "chat" in fname:
                chat_val += feat.get("user_initiated_interaction_count", 0)
        for cli_rec in rec.get("totals_by_cli", []):
            cli_val += cli_rec.get("session_count", 0)

        u["agent"]         += agent_val
        u["cli"]           += cli_val
        u["chat"]          += chat_val
        u["completions"]   += comp_val
        u["lines_accepted"] += lines_val

    # Classify and build rows
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    rows: list[dict] = []
    for login, u in sorted(agg.items()):
        active_days = len(u["dates"])
        lvl = _classify(
            agent=u["agent"], cli=u["cli"], chat=u["chat"],
            completions=u["completions"], lines_accepted=u["lines_accepted"],
            active_days=active_days,
        )
        distribution[lvl] += 1
        total = u["agent"] + u["completions"] + u["chat"] + u["cli"]
        autonomy = round(u["agent"] / total, 4) if total else 0.0
        rows.append({
            "github_login":          login,
            "active_days":           active_days,
            "agent_turns":           u["agent"],
            "cli_turns":             u["cli"],
            "chat_turns":            u["chat"],
            "completions_acceptances": u["completions"],
            "lines_accepted":        u["lines_accepted"],
            "autonomy_ratio":        autonomy,
            "level":                 lvl,
            "level_name":            _LEVEL_NAMES[lvl],
        })

    # Print summary
    total_users = len(rows)
    print(f"\n{'─'*46}")
    print(f"{'AI Maturity Distribution':^46}")
    print(f"{'─'*46}")
    for lvl in [5, 4, 3, 2, 1]:
        c = distribution[lvl]
        pct = c / total_users * 100 if total_users else 0
        bar = "█" * int(pct / 2)
        print(f"  {_LEVEL_NAMES[lvl]:<22} {c:>4}  {pct:5.1f}%  {bar}")
    print(f"{'─'*46}")
    print(f"  {'Total':22} {total_users:>4}")
    skill_gap = (distribution[1] + distribution[2]) / total_users * 100 if total_users else 0
    champion  = distribution[5] / total_users * 100 if total_users else 0
    print(f"\n  Skill Gap Index (L1+L2): {skill_gap:.1f}%")
    print(f"  Champion Density  (L5):  {champion:.1f}%\n")

    # Write CSV
    if not output:
        from datetime import date
        output = f"maturity-{date.today().isoformat()}.csv"

    fieldnames = list(rows[0].keys()) if rows else []
    with open(output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV written to: {output}  ({len(rows)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate Copilot user maturity levels.")
    parser.add_argument("--output", "-o", default=None, help="Output CSV path (default: maturity-YYYY-MM-DD.csv)")
    parser.add_argument("--days",   "-d", type=int, default=28, help="Look-back window in days (default: 28)")
    args = parser.parse_args()
    asyncio.run(_run(args.output, args.days))


if __name__ == "__main__":
    main()
