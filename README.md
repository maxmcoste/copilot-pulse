# Copilot Pulse

AI-powered conversational agent for GitHub Copilot usage analytics. Ask questions in natural language about your organization's Copilot adoption and get instant reports, charts, and insights.

## Features

- **Conversational AI agent** — Ask questions in natural language (Italian or English) and get detailed analytics powered by Claude or GitHub Copilot
- **GitHub Copilot Metrics** — Fetches data from both the new Usage Metrics API (GA) and legacy Metrics API
- **Rich terminal output** — Tables, charts, sparklines, and color-coded insights via Rich
- **Web dashboard** — FastAPI + HTMX dark-themed dashboard with Plotly interactive charts
- **Export reports** — Generate CSV, Excel (with formatting), and PDF reports
- **Smart caching** — SQLite-based local cache with configurable TTL
- **Multi-level analysis** — Enterprise, organization, team, and individual user metrics
- **GitHub App auth** — Supports both PAT and GitHub App installation tokens
- **i18n** — English and Italian UI with language switcher

## Architecture

```
copilot-pulse/
├── src/
│   ├── main.py                    # CLI entry point (Click)
│   ├── config.py                  # Environment config with validation
│   ├── github_client/             # GitHub API layer
│   │   ├── auth.py                # PAT + GitHub App authentication
│   │   ├── base_client.py         # HTTP client with retry + rate limiting
│   │   ├── usage_metrics_api.py   # New Usage Metrics API (primary)
│   │   ├── metrics_api.py         # Legacy Metrics API (deprecated fallback)
│   │   ├── user_management_api.py # Seat/billing management
│   │   └── models.py              # Pydantic v2 data models
│   ├── agent/                     # AI agent core
│   │   ├── orchestrator.py        # Conversation loop + tool dispatch
│   │   ├── llm_provider.py        # LLM provider abstraction
│   │   ├── providers/             # Anthropic + GitHub Copilot providers
│   │   ├── tools_schema.py        # Tool definitions
│   │   ├── intent_parser.py       # Local intent pre-processing
│   │   ├── query_planner.py       # API call planning
│   │   ├── data_analyzer.py       # Metrics analysis engine
│   │   └── response_composer.py   # Rich terminal formatting
│   ├── reports/                   # Output generation
│   │   ├── terminal_renderer.py   # Rich tables, sparklines, trees
│   │   ├── chart_engine.py        # Plotly + Matplotlib charts
│   │   ├── export_engine.py       # CSV, Excel, PDF export
│   │   └── web_dashboard.py       # FastAPI dashboard + API endpoints
│   ├── orgdata/                   # Org structure module
│   │   ├── database.py            # SQLite org database
│   │   ├── loader.py              # Excel/CSV import
│   │   ├── models.py              # Employee model
│   │   └── registry.py            # Org lookup helpers
│   ├── cache/
│   │   └── store.py               # SQLite cache with TTL
│   └── web/                       # Dashboard assets
│       ├── i18n.py                # EN/IT translations
│       ├── templates/             # Jinja2 templates
│       └── static/                # CSS + JS + favicon
└── tests/                         # pytest test suite with fixtures
```

## Setup

### Prerequisites

- Python 3.11+
- A GitHub token with `read:org` or `read:enterprise` scope, or a GitHub App with Copilot metrics permission
- An Anthropic API key (or GitHub Copilot subscription for the LLM)

### Installation

```bash
cd copilot-pulse

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install the project
pip install -e ".[dev]"
```

### Configuration

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` — choose one authentication method:

```env
# Option A: Personal Access Token
GITHUB_TOKEN=ghp_your_token_here

# Option B: GitHub App (recommended for Copilot metrics)
GITHUB_APP_ID=123456
GITHUB_APP_INSTALLATION_ID=7890123
GITHUB_APP_PRIVATE_KEY_PATH=./your-app.private-key.pem

# Required
GITHUB_ENTERPRISE=your-enterprise-slug
GITHUB_ORG=your-org-name
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

### Verify setup

```bash
copilot-pulse status
```

## Usage

### Interactive chat

```bash
copilot-pulse chat
```

Start a conversation with the AI agent. Example questions:

```
"Quanti utenti attivi abbiamo avuto questa settimana?"
"Mostrami il trend di adoption degli ultimi 28 giorni"
"Qual è l'acceptance rate per linguaggio?"
"Confronta il team backend con il team frontend"
"Chi sono i top 10 utenti per utilizzo di Copilot?"
"Quanti seat abbiamo assegnati ma mai utilizzati?"
"Generami un report PDF completo per il management"
"Esporta le metriche dell'ultimo mese in Excel"
```

In-chat commands: `/dashboard`, `/export <csv|excel|pdf>`, `/cache clear`, `/help`, `/quit`

### Single question

```bash
copilot-pulse ask "Quanti utenti attivi abbiamo oggi?"
```

### Web dashboard

```bash
copilot-pulse dashboard
# Opens at http://localhost:8501
```

### Generate reports

```bash
copilot-pulse report --format pdf --period 28d
copilot-pulse report --format excel --period 28d
copilot-pulse report --format csv --period 1d
```

### Import org structure

```bash
copilot-pulse import-org org-structure.xlsx
```

### Cache management

```bash
copilot-pulse cache stats
copilot-pulse cache clear
```

## Dashboard Metrics Reference

The web dashboard displays real-time Copilot usage analytics organized into KPI cards, interactive charts, and detail widgets. All data comes from the GitHub Copilot Usage Metrics API (GA) via NDJSON reports.

### KPI Cards

Four headline metrics shown at the top of the dashboard:

| KPI | Description | Source |
|-----|-------------|--------|
| **Active Users** | Users who had at least one Copilot interaction (completion, chat, or CLI) on the latest reported day | `total_active_users` from latest day in 28-day report |
| **Engaged Users** | Users who used Copilot at least once in the rolling 28-day window | `total_engaged_users` from latest day |
| **Acceptance Rate** | Percentage of code suggestions that developers accepted | `total_code_acceptances / total_code_suggestions * 100` |
| **Active Seats** | Total licensed Copilot seats in the organization | Seat management API |

### Charts

#### Adoption Trend (28 days)

Dual-line chart tracking daily active users and engaged users over the 28-day reporting window. Shows whether adoption is growing, stable, or declining.

- **Active Users line** (blue) — daily active count
- **Engaged Users line** (green) — 28-day rolling active count

#### Feature Usage Distribution

Donut chart showing how Copilot usage breaks down across all features. Each slice represents the total activity count over 28 days for a specific feature:

| Feature | Metric Used |
|---------|------------|
| Code Completions | `code_generation_activity_count` |
| Agent Mode | `user_initiated_interaction_count` |
| Agent Edits | `code_generation_activity_count` |
| Chat — Ask | `user_initiated_interaction_count` |
| Chat — Custom | `user_initiated_interaction_count` |
| Chat — Edit | `user_initiated_interaction_count` |
| Chat — Plan | `user_initiated_interaction_count` |
| Chat — Other | `user_initiated_interaction_count` |
| Inline Chat | `user_initiated_interaction_count` |
| Pull Requests | `pull_requests.total_created` |
| CLI Sessions | `totals_by_cli.session_count` |

Features with zero usage are automatically hidden.

#### Top 10 Active Users (28 days)

Horizontal bar chart ranking the most active Copilot users by a composite interaction score:

```
Score = code_suggestions + chat_turns + cli_turns
```

Aggregated per user across all days in the reporting period.

#### Suggested vs Accepted Code (14 days)

Dual-area chart comparing the volume of code suggestions generated by Copilot against how many were accepted by developers, over the most recent 14 days. The gap between the two lines represents rejected or ignored suggestions.

#### 28-Day Usage Trend (Composite Score)

Single-line area chart showing a composite daily usage score that combines all Copilot interaction types:

```
Usage Score = code_suggestions + ide_chats + dotcom_chats + PR_summaries + cli_chats
```

Useful for spotting overall usage trends, weekday/weekend patterns, and the impact of events like holidays or policy changes.

#### Agent Edits / User — Week over Week (13 weeks)

Bar chart showing the weekly ratio of autonomous agent edits per user, sampled every Wednesday for the past 13 weeks. Each bar is color-coded by adoption maturity:

| Weekly Threshold | Monthly Equivalent | Color | Label |
|------------------|--------------------|-------|-------|
| < 2.5 | < 10 | Red | Cautious |
| 2.5 – 12.5 | 10 – 50 | Yellow | Standard |
| 12.5 – 25 | 50 – 100 | Green | Advanced |
| > 25 | > 100 | Blue | Agent-First |

Reference lines on the chart mark each threshold. Data is fetched by querying the 1-day metrics endpoint for each Wednesday independently.

### ROI Calculator

Interactive widget that estimates the economic return on Copilot investment over the 28-day period. All calculations happen client-side for instant feedback when parameters change.

**Adjustable parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| Hourly Rate | 60 EUR | Average developer hourly cost |
| License Cost | 39 EUR/mo | Copilot license cost per seat per month |
| Minutes Saved Per Edit | 10 min | Estimated time saved per autonomous agent edit |
| Human Review Overhead | 20% | Time spent reviewing AI-generated code |

**Formulas:**

```
Value Per Edit   = (min_per_edit / 60) * (1 - review_overhead / 100) * hourly_rate
Total Value      = agent_edits_28d * value_per_edit
License Cost     = total_seats * monthly_license * (days / 30)
Net Value        = total_value - license_cost
ROI Multiplier   = total_value / license_cost
Value Per Seat   = total_value / total_seats
```

**Displayed KPIs:** ROI (28d) multiplier, Estimated Value, License Cost, Net Value, Value Per Seat, Total Agent Edits.

### CLI & Agent Adoption

Five metric cards showing the depth of CLI and autonomous agent usage:

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **CLI Users** | Developers who used `gh copilot` on the latest day | `daily_active_cli_users` + percentage of total users |
| **CLI Sessions** | Terminal sessions started with `gh copilot` over 28 days | Sum of `totals_by_cli.session_count` |
| **Coding Agent Users** | Developers who used Copilot Agent for autonomous coding | `monthly_active_agent_users` (28-day rolling) + percentage |
| **CLI Tokens** | Total tokens exchanged in CLI sessions (prompt + output) | Sum of `prompt_tokens_sum + output_tokens_sum` over 28 days |
| **Agent Edits / User** | Average autonomous code edits per active user | `total_agent_edits / total_users` with color-coded scale |

The Agent Edits / User card includes an interpretation scale:
- **< 10** (Red) — Cautious / Legacy
- **10 – 50** (Yellow) — Standard Adopters
- **50 – 100** (Green) — Advanced
- **> 100** (Blue) — Agent-First (Power Users)

### Quick Insights

Five auto-generated insight cards providing at-a-glance context:

| Insight | Description |
|---------|-------------|
| **Top 5 Languages** | Most active programming languages by code generation activity, excluding "other"/"unknown" |
| **Top IDE** | Most frequently used IDE across the reporting period |
| **Acceptance Rate Trend** | Last 7 days acceptance rate with week-over-week delta (e.g., "67.3% ↑ 2.1pp") |
| **Peak Day** | Day with the highest number of active users and the count |
| **Seat Utilization** | Active seats vs total seats with utilization percentage |

## How it works

1. You ask a question in natural language
2. The orchestrator sends your question to Claude (or GitHub Copilot) with a set of defined tools
3. The LLM decides which tools to invoke (fetch metrics, analyze data, generate charts, export)
4. Tools execute against the GitHub API (with caching) and run local analysis
5. The LLM synthesizes the results into an insightful, human-readable response
6. Output is rendered with Rich formatting in the terminal, or as interactive charts on the web dashboard

### Available tools (used by the AI agent)

| Tool | Description |
|------|-------------|
| `get_enterprise_metrics` | Enterprise-level aggregated Copilot metrics |
| `get_organization_metrics` | Organization-level metrics |
| `get_team_metrics` | Team-level metrics (requires 5+ licensed members) |
| `get_user_metrics` | Per-user usage breakdown |
| `get_seat_info` | Seat assignments and utilization |
| `analyze_data` | Compute derived metrics (trends, rankings, comparisons) |
| `generate_chart` | Create bar, line, pie, heatmap charts |
| `export_report` | Export to CSV, Excel, or PDF |
| `get_org_structure_summary` | Org hierarchy summary (requires imported org data) |
| `analyze_org_copilot_usage` | Cross-reference Copilot usage with org structure |

## API Support

### Primary: Copilot Usage Metrics API (GA)

Uses `X-GitHub-Api-Version: 2026-03-10`. Returns NDJSON reports via signed download URLs.

Supports:
- **28-day reports** — Rolling window with daily granularity
- **1-day reports** — Single-day snapshots, queryable up to 90+ days back via `?day=YYYY-MM-DD`

### Fallback: Legacy Copilot Metrics API

Set `USE_LEGACY_API=true` in `.env`. Note: these endpoints are deprecated and scheduled for retirement on 2026-04-02.

## Running tests

```bash
pytest tests/ -v
```

All tests use JSON fixtures — no real API calls are made.

## Notes

- Metrics have a ~2 business day delay from actual activity
- Team metrics require at least 5 members with active Copilot licenses
- Telemetry must be enabled in the user's IDE for metrics to be collected
- Export files are saved to `~/.copilot-pulse/exports/`
- Chart images are saved to `~/.copilot-pulse/charts/`
- Cache database is stored at `~/.copilot-pulse/cache.db`
- The dashboard supports EN/IT language switching via the navbar
