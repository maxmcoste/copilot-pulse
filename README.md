# Copilot Pulse

AI-powered conversational agent for GitHub Copilot usage analytics. Ask questions in natural language about your organization's Copilot adoption and get instant reports, charts, and insights.

## Features

- **Conversational AI agent** — Ask questions in natural language (Italian or English) and get detailed analytics powered by Claude
- **GitHub Copilot Metrics** — Fetches data from both the new Usage Metrics API (GA) and legacy Metrics API
- **Rich terminal output** — Tables, charts, sparklines, and color-coded insights via Rich
- **Web dashboard** — FastAPI + HTMX dark-themed dashboard with Plotly interactive charts
- **Export reports** — Generate CSV, Excel (with formatting), and PDF reports
- **Smart caching** — SQLite-based local cache with configurable TTL
- **Multi-level analysis** — Enterprise, organization, team, and individual user metrics

## Architecture

```
copilot-pulse/
├── src/
│   ├── main.py                    # CLI entry point (Click)
│   ├── config.py                  # Environment config with validation
│   ├── github_client/             # GitHub API layer
│   │   ├── auth.py                # Token authentication
│   │   ├── base_client.py         # HTTP client with retry + rate limiting
│   │   ├── usage_metrics_api.py   # New Usage Metrics API (primary)
│   │   ├── metrics_api.py         # Legacy Metrics API (deprecated fallback)
│   │   ├── user_management_api.py # Seat/billing management
│   │   └── models.py              # Pydantic v2 data models
│   ├── agent/                     # AI agent core
│   │   ├── orchestrator.py        # Conversation loop + tool dispatch
│   │   ├── tools_schema.py        # Claude tool definitions
│   │   ├── intent_parser.py       # Local intent pre-processing
│   │   ├── query_planner.py       # API call planning
│   │   ├── data_analyzer.py       # Metrics analysis engine
│   │   └── response_composer.py   # Rich terminal formatting
│   ├── reports/                   # Output generation
│   │   ├── terminal_renderer.py   # Rich tables, sparklines, trees
│   │   ├── chart_engine.py        # Plotly + Matplotlib charts
│   │   ├── export_engine.py       # CSV, Excel, PDF export
│   │   └── web_dashboard.py       # FastAPI dashboard
│   ├── cache/
│   │   └── store.py               # SQLite cache with TTL
│   └── web/                       # Dashboard assets
│       ├── templates/             # Jinja2 templates
│       └── static/                # CSS + JS
└── tests/                         # pytest test suite with fixtures
```

## Setup

### Prerequisites

- Python 3.11+
- A GitHub token with `read:org` or `read:enterprise` scope
- An Anthropic API key

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

Edit `.env`:

```env
GITHUB_TOKEN=ghp_your_token_here
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

### Cache management

```bash
copilot-pulse cache stats
copilot-pulse cache clear
```

## How it works

1. You ask a question in natural language
2. The orchestrator sends your question to Claude with a set of defined tools
3. Claude decides which tools to invoke (fetch metrics, analyze data, generate charts, export)
4. Tools execute against the GitHub API (with caching) and run local analysis
5. Claude synthesizes the results into an insightful, human-readable response
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

## API Support

### Primary: Copilot Usage Metrics API (GA)

Uses `X-GitHub-Api-Version: 2026-03-10`. Returns NDJSON reports via signed download URLs.

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
