# Copilot Pulse

AI-powered conversational agent for GitHub Copilot usage analytics. Ask questions in natural language about your organization's Copilot adoption and get instant reports, charts, and insights.

## Features

- **Conversational AI agent** — Ask questions in natural language (Italian or English) and get detailed analytics powered by Claude or GitHub Copilot
- **GitHub Copilot Metrics** — Fetches data from both the new Usage Metrics API (GA) and legacy Metrics API
- **Rich terminal output** — Tables, charts, sparklines, and color-coded insights via Rich
- **Web dashboard** — FastAPI + HTMX dark-themed dashboard with Plotly interactive charts
- **Org-level filtering** — Filter all dashboard metrics by org hierarchy levels (L4–L8) using an Apply button that batches API calls
- **Export Snapshot** — Download a fully self-contained static HTML file of the current filtered dashboard view
- **ROI Calculator** — Real-time economic value estimate of Copilot Agent investment over 28 days
- **Virtual FTE Analysis** — Monthly breakdown of virtual developer capacity added by IDE completions and Agent Edits combined
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
│   │   ├── loader.py              # Excel (.xls/.xlsx) / CSV import
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

Upload your org hierarchy file (`.xls` or `.xlsx`) via the **Setup** page in the web dashboard. The file is parsed and stored in a local SQLite database (`~/.copilot-pulse/orgdata.db`), which powers the org-level filters.

```bash
# Or via CLI
copilot-pulse import-org org-structure.xlsx
```

Required columns: `github_id` (login), plus org level columns such as `sup_org_level_4` through `sup_org_level_8`.

### Cache management

```bash
copilot-pulse cache stats
copilot-pulse cache clear
```

## Dashboard Metrics Reference

The web dashboard displays real-time Copilot usage analytics organized into KPI cards, interactive charts, and detail widgets. All data comes from the GitHub Copilot Usage Metrics API (GA) via NDJSON reports.

### Org-Level Filtering

When an org structure file has been imported, a filter bar appears at the top of the dashboard offering cascading dropdowns for **Level 4 → Level 5 → Level 6 → Level 7 → Level 8** of your org hierarchy.

- Selecting values in the dropdowns **does not immediately fire API calls** — this avoids redundant requests while navigating the hierarchy.
- The **Apply** button turns blue/highlighted when a pending selection differs from the currently applied filter. Click it once to refresh all dashboard metrics for the selected org scope.
- The **Reset (✕)** button clears the filter and immediately refreshes to the full unfiltered view.

All KPI cards, charts, adoption widgets, productivity insights, and ROI/FTE calculations respect the active org filter.

### Export Snapshot

The **Export Snapshot** button (top-right of the dashboard) generates a fully self-contained static HTML file of the current dashboard state:

- All 7 Plotly charts are rendered as embedded PNG images
- ROI and Virtual FTE parameters are captured as plain text values
- No server connection required to view the exported file
- File name includes the current date (e.g., `copilot-pulse-snapshot-2026-04-13.html`)

### KPI Cards

Four headline metrics shown at the top of the dashboard:

| KPI | Description | Source |
|-----|-------------|--------|
| **Active Users** | Unique users who had at least one Copilot interaction over the 28-day window | Unique `login` count across 28-day per-user report |
| **Engaged Users** | Users with at least one accepted code suggestion over 28 days | Users with `code_acceptance_activity_count > 0` |
| **Acceptance Rate** | Percentage of code suggestions that developers accepted | `total_code_acceptances / total_code_suggestions * 100` |
| **Active Seats** | Total licensed Copilot seats in the organization (or filtered group size) | Seat management API / filter set cardinality |

### Charts

#### Adoption Trend (28 days)

Dual-line chart tracking daily active users and engaged users over the 28-day reporting window.

- **Active Users line** (blue) — daily unique active count
- **Engaged Users line** (green) — users with at least one accepted suggestion per day

#### Feature Adoption (Unique Users)

Donut chart showing how many **unique users** engaged with each Copilot feature over 28 days. Each slice counts distinct developers — not raw event counts — so the chart reflects actual breadth of adoption per feature.

Features with zero usage are automatically hidden.

#### Top 10 Active Users (28 days)

Horizontal bar chart ranking the most active Copilot users by a composite interaction score:

```
Score = code_suggestions + chat_turns + cli_turns
```

Aggregated per user across all days in the reporting period.

#### Suggested vs Accepted Code (14 days)

Dual-area chart comparing the volume of code suggestions generated by Copilot against how many were accepted by developers over the most recent 14 days.

#### 28-Day Usage Trend (Composite Score)

Single-line area chart showing a composite daily usage score:

```
Usage Score = code_suggestions + ide_chats + dotcom_chats + PR_summaries + cli_chats
```

#### Agent Edits / User — Week over Week (13 weeks)

Bar chart showing the weekly ratio of autonomous agent edits per user, sampled every Wednesday for the past 13 weeks. Each bar is color-coded by adoption maturity:

| Weekly Threshold | Monthly Equivalent | Color | Label |
|------------------|--------------------|-------|-------|
| < 2.5 | < 10 | Red | Cautious |
| 2.5 – 12.5 | 10 – 50 | Yellow | Standard |
| 12.5 – 25 | 50 – 100 | Green | Advanced |
| > 25 | > 100 | Blue | Agent-First |

### ROI Calculator

Interactive widget estimating the economic return on Copilot Agent investment over 28 days.

**Adjustable parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| Hourly Rate | 33 EUR/h | Average developer hourly cost |
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

### Virtual FTE Analysis

Monthly table estimating the equivalent developer capacity that Copilot contributed, based on **both** IDE code completions and Agent Edits combined.

**Adjustable parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| Human lines/day (baseline) | 50 | Average lines of code a developer writes per day |
| Working days/month | 20 | Business days in the reference month |
| Human review overhead | 20% | Fraction deducted for code review |
| Developer hourly rate | 33 EUR/h | Average developer cost |
| Daily work hours | 8 h | Hours per working day |
| Lines per agent edit | 17 | Estimated lines of code per autonomous agent edit |

**Formula:**

```
VOLUME_IDE   = lines_accepted_week * 7          (scaled from Wednesday sample)
VOLUME_AGENT = agent_edits_week * 7 * lines_per_agent_edit
TOTAL_LINES  = (VOLUME_IDE + VOLUME_AGENT) * (1 - review_overhead)

Human Capacity = lines_per_day * working_days
Virtual FTE    = TOTAL_LINES / Human Capacity
Monthly Value  = Virtual_FTE * hourly_rate * daily_hours * working_days
```

The table shows one row per calendar month, with columns: Period, IDE Lines, Agent Lines, Total Lines (net), Human Capacity, Virtual FTE, Monthly Value.

**Summary KPIs:** Monthly ROI of the latest period and average Virtual FTE over 13 weeks.

### CLI & Agent Adoption

Five metric cards showing the depth of CLI and autonomous agent usage:

| Metric | Description |
|--------|-------------|
| **CLI Users** | Developers who used `gh copilot` on the latest day + % of total |
| **CLI Sessions** | Terminal sessions with `gh copilot` over 28 days |
| **Coding Agent Users** | Developers who used Copilot Agent (28-day rolling) + % |
| **CLI Tokens** | Total tokens exchanged in CLI sessions over 28 days |
| **Agent Edits / User** | Average autonomous code edits per active user (color-coded) |

The Agent Edits / User card includes an interpretation scale:
- **< 10** (Red) — Cautious / Legacy
- **10 – 50** (Yellow) — Standard Adopters
- **50 – 100** (Green) — Advanced
- **> 100** (Blue) — Agent-First (Power Users)

### Quick Insights

Five auto-generated insight cards:

| Insight | Description |
|---------|-------------|
| **Top 5 Languages** | Most active programming languages by code generation activity |
| **Top IDE** | Most frequently used IDE across the reporting period |
| **Acceptance Rate Trend** | Last 7 days acceptance rate with week-over-week delta |
| **Peak Day** | Day with the highest active user count |
| **Top 5 Models** | Most used Copilot models ranked by interaction count |

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

Set `USE_LEGACY_API=true` in `.env`. Note: these endpoints are deprecated and scheduled for retirement. The new Usage Metrics API is the recommended path.

## Running tests

```bash
pytest tests/ -v
```

All tests use JSON fixtures — no real API calls are made.

## Notes

- Metrics have a ~2 business day delay from actual activity
- Team metrics require at least 5 members with active Copilot licenses
- Telemetry must be enabled in the user's IDE for metrics to be collected
- Org structure is stored at `~/.copilot-pulse/orgdata.db` (SQLite)
- Export files are saved to `~/.copilot-pulse/exports/`
- Chart images are saved to `~/.copilot-pulse/charts/`
- Cache database is stored at `~/.copilot-pulse/cache.db`
- The dashboard supports EN/IT language switching via the navbar
