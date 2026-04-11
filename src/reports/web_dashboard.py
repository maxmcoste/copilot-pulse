"""FastAPI web dashboard with HTMX and WebSocket chat."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from starlette.responses import RedirectResponse

from ..config import AppConfig
from ..github_client.auth import build_github_auth
from ..github_client.base_client import GitHubBaseClient
from ..github_client.models import ReportDownloadResponse
from ..github_client.usage_metrics_api import _unwrap_day_totals
from ..orgdata.database import OrgDatabase
from ..web.i18n import get_translations

logger = logging.getLogger(__name__)

# In-memory cache for raw 28-day records (avoids re-fetching per chart).
_raw_cache: dict[str, Any] = {"data": None, "ts": 0.0}

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def create_app(config: AppConfig) -> FastAPI:
    """Create and configure the FastAPI dashboard application.

    Args:
        config: Application configuration.

    Returns:
        Configured FastAPI app.
    """
    app = FastAPI(title="Copilot Pulse Dashboard", version="0.1.0")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Store config and orchestrator reference on app state
    app.state.config = config
    app.state.orchestrator = None  # Set externally before startup

    import time as _time

    async def _get_raw_org_metrics() -> list[dict[str, Any]]:
        """Fetch raw (unparsed) 28-day org metrics with simple caching (5 min)."""
        now = _time.time()
        if _raw_cache["data"] is not None and now - _raw_cache["ts"] < 300:
            return _raw_cache["data"]

        auth = build_github_auth(config)
        client = GitHubBaseClient(auth)
        try:
            resp = await client.get(
                f"/orgs/{config.github_org}/copilot/metrics/reports/organization-28-day/latest"
            )
            dr = ReportDownloadResponse(**resp.json())
            raw_records: list[dict[str, Any]] = []
            for url in dr.download_links:
                raw_records.extend(await client.download_ndjson(url))
            unwrapped = _unwrap_day_totals(raw_records)
            _raw_cache["data"] = unwrapped
            _raw_cache["ts"] = now
            return unwrapped
        finally:
            await client.close()

    def _lang(request: Request) -> str:
        """Read language preference from cookie (default: en)."""
        return request.cookies.get("lang", "en")

    def _ctx(request: Request, **extra: Any) -> dict[str, Any]:
        """Build common template context with translations."""
        lang = _lang(request)
        return {
            "request": request,
            "enterprise": config.github_enterprise,
            "org": config.github_org,
            "lang": lang,
            "t": get_translations(lang),
            **extra,
        }

    @app.get("/set-lang", response_class=HTMLResponse)
    async def set_lang(request: Request, lang: str = "en"):
        """Switch UI language and redirect back."""
        if lang not in ("en", "it"):
            lang = "en"
        referer = request.headers.get("referer", "/")
        response = RedirectResponse(url=referer, status_code=302)
        response.set_cookie("lang", lang, max_age=365 * 86400, samesite="lax")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Main dashboard page with KPI cards and charts."""
        return templates.TemplateResponse(
            "dashboard.html",
            _ctx(request, title="Copilot Pulse Dashboard"),
        )

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page(request: Request):
        """Chat interface page."""
        return templates.TemplateResponse(
            "dashboard.html",
            _ctx(request, title="Copilot Pulse Chat", active_tab="chat"),
        )

    @app.get("/api/metrics", response_class=HTMLResponse)
    async def api_metrics(request: Request):
        """Return KPI cards as an HTML fragment for HTMX swap."""
        lang = _lang(request)
        t = get_translations(lang)
        orch = app.state.orchestrator
        if not orch:
            return HTMLResponse(
                f'<div class="kpi-card"><div class="kpi-value">!</div>'
                f'<div class="kpi-label">Agent not initialized</div></div>'
            )

        try:
            result = await orch._tool_org_metrics({
                "org": config.github_org,
                "period": "28-day",
            })
        except Exception as e:
            logger.error("API metrics error: %s", e)
            return HTMLResponse(
                f'<div class="kpi-card"><div class="kpi-value">!</div>'
                f'<div class="kpi-label">{e}</div></div>'
            )

        metrics_list = result.get("metrics", [])
        if not metrics_list:
            return HTMLResponse(
                f'<div class="kpi-card"><div class="kpi-value">0</div>'
                f'<div class="kpi-label">{t.get("dash_active_users", "Active Users")}</div></div>'
            )

        # Use the most recent day for the headline KPIs.
        latest = max(metrics_list, key=lambda m: m.get("date", ""))
        active = latest.get("total_active_users", 0)
        engaged = latest.get("total_engaged_users", 0)

        # Acceptance rate from completions.
        comp = latest.get("copilot_ide_code_completions") or {}
        sugg = comp.get("total_code_suggestions", 0)
        acc = comp.get("total_code_acceptances", 0)
        rate = f"{acc / sugg * 100:.1f}%" if sugg else "N/A"

        # Seat info — fetch in parallel context is tricky, just show N/A
        # unless we can grab cached seat data.
        seats_label = "N/A"
        try:
            seat_result = await orch._tool_seat_info({"org": config.github_org})
            seat_info = seat_result.get("seat_info", {})
            total = seat_info.get("total_seats", 0)
            if total:
                seats_label = str(total)
        except Exception:
            pass

        html = (
            f'<div class="kpi-card">'
            f'  <div class="kpi-value">{active:,}</div>'
            f'  <div class="kpi-label">{t.get("dash_active_users", "Active Users")} ({latest.get("date", "")})</div>'
            f'</div>'
            f'<div class="kpi-card">'
            f'  <div class="kpi-value">{engaged:,}</div>'
            f'  <div class="kpi-label">{t.get("dash_engaged_users", "Engaged Users")}</div>'
            f'</div>'
            f'<div class="kpi-card">'
            f'  <div class="kpi-value">{rate}</div>'
            f'  <div class="kpi-label">{t.get("dash_acceptance_rate", "Acceptance Rate")}</div>'
            f'</div>'
            f'<div class="kpi-card">'
            f'  <div class="kpi-value">{seats_label}</div>'
            f'  <div class="kpi-label">{t.get("dash_active_seats", "Seats")}</div>'
            f'</div>'
        )
        return HTMLResponse(html)

    @app.get("/api/charts/adoption")
    async def api_chart_adoption():
        """Return adoption-trend data for the Plotly line chart."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}
        try:
            result = await orch._tool_org_metrics({
                "org": config.github_org,
                "period": "28-day",
            })
            metrics_list = result.get("metrics", [])
            # Sort by date ascending for the chart.
            metrics_list.sort(key=lambda m: m.get("date", ""))
            dates = [m.get("date", "") for m in metrics_list]
            active = [m.get("total_active_users", 0) for m in metrics_list]
            engaged = [m.get("total_engaged_users", 0) for m in metrics_list]
            return {"dates": dates, "active_users": active, "engaged_users": engaged}
        except Exception as e:
            logger.error("Chart adoption error: %s", e)
            return {"error": str(e)}

    @app.get("/api/charts/features")
    async def api_chart_features():
        """Return granular feature-usage distribution (28 days).

        Each ``totals_by_feature`` entry becomes its own slice.
        Pull Requests and CLI (``totals_by_cli``) are added separately.

        Metric per feature:
        - ``code_completion`` → ``code_generation_activity_count``
        - all others → ``user_initiated_interaction_count``
          (falls back to ``code_generation_activity_count`` when 0)
        - Pull Requests → ``pull_requests.total_created``
        - CLI → ``totals_by_cli.session_count``
        """
        # Human-friendly labels for GA feature names
        _LABELS = {
            "code_completion": "Code Completions",
            "chat_panel_agent_mode": "Agent Mode",
            "agent_edit": "Agent Edits",
            "chat_panel_ask_mode": "Chat — Ask",
            "chat_panel_custom_mode": "Chat — Custom",
            "chat_panel_edit_mode": "Chat — Edit",
            "chat_panel_plan_mode": "Chat — Plan",
            "chat_panel_unknown_mode": "Chat — Other",
            "chat_inline": "Inline Chat",
            "copilot_cli": "Copilot CLI (feature)",
        }

        try:
            records = await _get_raw_org_metrics()
            if not records:
                return {"labels": [], "values": []}

            totals: dict[str, int] = {}

            for rec in records:
                for feat in rec.get("totals_by_feature", []):
                    fname = feat.get("feature", "")
                    if not fname:
                        continue
                    label = _LABELS.get(fname, fname)
                    if fname == "code_completion":
                        count = feat.get("code_generation_activity_count", 0)
                    else:
                        count = feat.get("user_initiated_interaction_count", 0)
                        if count == 0:
                            count = feat.get("code_generation_activity_count", 0)
                    totals[label] = totals.get(label, 0) + count

                pr_data = rec.get("pull_requests") or {}
                pr_count = pr_data.get("total_created", 0)
                if pr_count:
                    totals["Pull Requests"] = totals.get("Pull Requests", 0) + pr_count

                cli_data = rec.get("totals_by_cli")
                if isinstance(cli_data, dict):
                    cli_count = cli_data.get("session_count", 0)
                    if cli_count:
                        totals["CLI Sessions"] = totals.get("CLI Sessions", 0) + cli_count

            # Sort descending by value, filter zeros
            sorted_items = sorted(
                ((l, v) for l, v in totals.items() if v > 0),
                key=lambda x: x[1],
                reverse=True,
            )
            if not sorted_items:
                return {"labels": [], "values": []}
            labels, values = zip(*sorted_items)
            return {"labels": list(labels), "values": list(values)}
        except Exception as e:
            logger.error("Chart features error: %s", e)
            return {"error": str(e)}

    @app.get("/api/charts/top-users")
    async def api_chart_top_users():
        """Return top 10 active users for a horizontal bar chart."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}
        try:
            result = await orch._tool_user_metrics({
                "scope": "organization",
                "period": "28-day",
            })
            users = result.get("users", [])
            if not users:
                return {"logins": [], "scores": []}

            # Aggregate per user across all day records
            agg: dict[str, int] = {}
            for u in users:
                login = u.get("github_login", "")
                if not login:
                    continue
                score = (
                    u.get("completions_suggestions", 0)
                    + u.get("chat_turns", 0)
                    + u.get("cli_turns", 0)
                )
                agg[login] = agg.get(login, 0) + score

            # Sort descending, take top 10
            top = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:10]
            # Reverse for horizontal bar (Plotly draws bottom-up)
            top.reverse()
            return {
                "logins": [t[0] for t in top],
                "scores": [t[1] for t in top],
            }
        except Exception as e:
            logger.error("Chart top-users error: %s", e)
            return {"error": str(e)}

    @app.get("/api/charts/suggested-accepted")
    async def api_chart_suggested_accepted():
        """Return daily suggested vs accepted code lines for the last 14 days."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}
        try:
            result = await orch._tool_org_metrics({
                "org": config.github_org,
                "period": "28-day",
            })
            metrics_list = result.get("metrics", [])
            metrics_list.sort(key=lambda m: m.get("date", ""))
            # Take last 14 days
            metrics_list = metrics_list[-14:]

            dates = []
            suggested = []
            accepted = []
            for m in metrics_list:
                dates.append(m.get("date", ""))
                comp = m.get("copilot_ide_code_completions") or {}
                suggested.append(comp.get("total_code_suggestions", 0))
                accepted.append(comp.get("total_code_acceptances", 0))

            return {"dates": dates, "suggested": suggested, "accepted": accepted}
        except Exception as e:
            logger.error("Chart suggested-accepted error: %s", e)
            return {"error": str(e)}

    @app.get("/api/charts/usage-trend")
    async def api_chart_usage_trend():
        """Return 28-day composite usage score trend.

        Usage Score = code_suggestions + chat_messages + PR_summaries + CLI_interactions.
        """
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}
        try:
            result = await orch._tool_org_metrics({
                "org": config.github_org,
                "period": "28-day",
            })
            metrics_list = result.get("metrics", [])
            metrics_list.sort(key=lambda m: m.get("date", ""))

            dates = []
            scores = []
            for m in metrics_list:
                dates.append(m.get("date", ""))
                comp = m.get("copilot_ide_code_completions") or {}
                ide_chat = m.get("copilot_ide_chat") or {}
                dot_chat = m.get("copilot_dotcom_chat") or {}
                pr = m.get("copilot_dotcom_pull_requests") or {}
                cli = m.get("copilot_cli") or {}

                score = (
                    comp.get("total_code_suggestions", 0)
                    + ide_chat.get("total_chats", 0)
                    + dot_chat.get("total_chats", 0)
                    + pr.get("total_pr_summaries_created", 0)
                    + cli.get("total_chats", 0)
                )
                scores.append(score)

            return {"dates": dates, "scores": scores}
        except Exception as e:
            logger.error("Chart usage-trend error: %s", e)
            return {"error": str(e)}

    @app.get("/api/roi-data")
    async def api_roi_data():
        """Return raw data for the client-side ROI calculator."""
        try:
            records = await _get_raw_org_metrics()
            if not records:
                return {"agent_edits": 0, "total_seats": 0, "days": 0}

            agent_edits = 0
            for rec in records:
                for feat in rec.get("totals_by_feature", []):
                    if feat.get("feature") == "agent_edit":
                        agent_edits += feat.get("code_generation_activity_count", 0)

            latest = sorted(records, key=lambda r: r.get("day", ""))[-1]
            active_users = latest.get("monthly_active_users", 0)

            # Seat count
            total_seats = 0
            orch = app.state.orchestrator
            if orch:
                try:
                    seat_result = await orch._tool_seat_info({"org": config.github_org})
                    si = seat_result.get("seat_info", {})
                    total_seats = si.get("total_seats", 0)
                except Exception:
                    pass

            return {
                "agent_edits": agent_edits,
                "total_seats": total_seats,
                "active_users": active_users,
                "days": len(records),
            }
        except Exception as e:
            logger.error("ROI data error: %s", e)
            return {"error": str(e)}

    @app.get("/api/charts/agent-edits-wow")
    async def api_chart_agent_edits_wow():
        """Return weekly Agent Edits / User for the last 13 weeks.

        Fetches one representative day per week (Wednesday) via the
        1-day org metrics endpoint.  Each week's value is the sum of
        ``agent_edit.code_generation_activity_count`` across that day
        divided by ``monthly_active_users`` (28-day rolling count on
        that same day).

        Because a single day is a sample of the week, the numbers are
        per-day not per-week — but the week-over-week *trend* is valid.
        """
        from datetime import date as _date, timedelta as _td

        auth = build_github_auth(config)
        client = GitHubBaseClient(auth)

        # Pick Wednesdays going back 13 weeks from the most recent safe day
        base = _date.today() - _td(days=2)          # latest day with data
        # Align to the most recent Wednesday
        days_since_wed = (base.weekday() - 2) % 7   # 0=Mon … 6=Sun; Wed=2
        last_wed = base - _td(days=days_since_wed)
        weeks = [last_wed - _td(weeks=i) for i in range(12, -1, -1)]

        async def _fetch_day(day_str: str) -> dict[str, Any] | None:
            try:
                resp = await client.get(
                    f"/orgs/{config.github_org}/copilot/metrics/reports/organization-1-day",
                    params={"day": day_str},
                )
                dr = ReportDownloadResponse(**resp.json())
                if not dr.download_links:
                    return None
                raw = await client.download_ndjson(dr.download_links[0])
                recs = _unwrap_day_totals(raw)
                return recs[0] if recs else None
            except Exception as exc:
                logger.warning("agent-edits-wow: failed to fetch %s: %s", day_str, exc)
                return None

        try:
            results = await asyncio.gather(
                *[_fetch_day(w.isoformat()) for w in weeks]
            )

            labels: list[str] = []
            values: list[float] = []
            colors: list[str] = []

            for week_date, rec in zip(weeks, results):
                label = f"W{week_date.isocalendar()[1]} ({week_date.strftime('%d/%m')})"
                labels.append(label)
                if rec is None:
                    values.append(0)
                    colors.append("#30363d")
                    continue
                agent_edits = 0
                for feat in rec.get("totals_by_feature", []):
                    if feat.get("feature") == "agent_edit":
                        agent_edits += feat.get("code_generation_activity_count", 0)
                total_users = rec.get("monthly_active_users", 0)
                ratio = agent_edits / total_users if total_users else 0
                values.append(round(ratio, 1))
                # Color by weekly band (monthly thresholds / 4)
                if ratio < 2.5:
                    colors.append("#f85149")
                elif ratio <= 12.5:
                    colors.append("#d29922")
                elif ratio <= 25:
                    colors.append("#3fb950")
                else:
                    colors.append("#58a6ff")

            return {"labels": labels, "values": values, "colors": colors}
        except Exception as e:
            logger.error("Chart agent-edits-wow error: %s", e)
            return {"error": str(e)}
        finally:
            await client.close()

    @app.get("/api/adoption-kpis", response_class=HTMLResponse)
    async def api_adoption_kpis(request: Request):
        """Return CLI & Agent adoption KPIs as an HTML fragment."""
        lang = _lang(request)
        t = get_translations(lang)
        title = t.get("dash_adoption_title", "CLI & Agent Adoption")
        try:
            records = await _get_raw_org_metrics()
        except Exception as e:
            logger.error("Adoption KPIs error: %s", e)
            return HTMLResponse(
                f'<h3>{title}</h3>'
                f'<p style="color:var(--text-secondary)">{e}</p>'
            )

        if not records:
            return HTMLResponse(
                f'<h3>{title}</h3>'
                f'<p style="color:var(--text-secondary)">No data</p>'
            )

        sorted_recs = sorted(records, key=lambda r: r.get("day", ""))
        latest = sorted_recs[-1]
        total_users = latest.get("monthly_active_users", 0)

        # 1. CLI Users (28-day rolling from latest day)
        cli_users = latest.get("daily_active_cli_users", 0)
        cli_users_pct = f"({cli_users / total_users * 100:.0f}%)" if total_users else ""

        # 2. CLI Sessions (28-day total)
        cli_sessions = 0
        for rec in sorted_recs:
            c = rec.get("totals_by_cli")
            if isinstance(c, dict):
                cli_sessions += c.get("session_count", 0)

        # 3. Agent Users (28-day rolling from latest day)
        agent_users = latest.get("monthly_active_agent_users", 0)
        agent_users_pct = f"({agent_users / total_users * 100:.0f}%)" if total_users else ""

        # 4. CLI Total Tokens (28-day)
        total_prompt_tokens = 0
        total_output_tokens = 0
        for rec in sorted_recs:
            c = rec.get("totals_by_cli")
            if isinstance(c, dict):
                tu = c.get("token_usage", {})
                total_prompt_tokens += tu.get("prompt_tokens_sum", 0)
                total_output_tokens += tu.get("output_tokens_sum", 0)
        total_tokens = total_prompt_tokens + total_output_tokens

        # 5. Agent Edits per User (28-day)
        total_agent_edits = 0
        for rec in sorted_recs:
            for feat in rec.get("totals_by_feature", []):
                if feat.get("feature") == "agent_edit":
                    total_agent_edits += feat.get("code_generation_activity_count", 0)
        agent_edits_per_user = total_agent_edits / total_users if total_users else 0

        def _fmt(n: int) -> str:
            if n >= 1_000_000_000:
                return f"{n / 1_000_000_000:.1f}B"
            if n >= 1_000_000:
                return f"{n / 1_000_000:.1f}M"
            if n >= 1_000:
                return f"{n / 1_000:.1f}K"
            return str(n)

        html = (
            f'<h3>{title}</h3>'
            f'<div class="adoption-grid">'
            f'  <div class="adoption-card">'
            f'    <div class="adoption-icon">⌨</div>'
            f'    <div class="adoption-body">'
            f'      <div class="adoption-value">{cli_users:,} <span class="adoption-pct">{cli_users_pct}</span></div>'
            f'      <div class="adoption-label">{t.get("adopt_cli_users", "CLI Users")} <span class="adoption-period">({latest.get("day", "")})</span></div>'
            f'      <div class="adoption-desc">{t.get("adopt_cli_users_desc", "Developers who used gh copilot today")}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="adoption-card">'
            f'    <div class="adoption-icon">▶</div>'
            f'    <div class="adoption-body">'
            f'      <div class="adoption-value">{cli_sessions:,}</div>'
            f'      <div class="adoption-label">{t.get("adopt_cli_sessions", "CLI Sessions")} <span class="adoption-period">(28d)</span></div>'
            f'      <div class="adoption-desc">{t.get("adopt_cli_sessions_desc", "Terminal sessions started with gh copilot")}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="adoption-card">'
            f'    <div class="adoption-icon">🤖</div>'
            f'    <div class="adoption-body">'
            f'      <div class="adoption-value">{agent_users:,} <span class="adoption-pct">{agent_users_pct}</span></div>'
            f'      <div class="adoption-label">{t.get("adopt_agent_users", "Coding Agent Users")} <span class="adoption-period">(28d)</span></div>'
            f'      <div class="adoption-desc">{t.get("adopt_agent_users_desc", "Developers who used Copilot Agent for autonomous coding")}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="adoption-card">'
            f'    <div class="adoption-icon">⚡</div>'
            f'    <div class="adoption-body">'
            f'      <div class="adoption-value">{_fmt(total_tokens)}</div>'
            f'      <div class="adoption-label">{t.get("adopt_cli_tokens", "CLI Tokens")} <span class="adoption-period">(28d)</span></div>'
            f'      <div class="adoption-desc">{t.get("adopt_cli_tokens_desc", "Total tokens exchanged in CLI sessions — high volume indicates complex tasks")}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="adoption-card">'
            f'    <div class="adoption-icon">✏️</div>'
            f'    <div class="adoption-body">'
            f'      <div class="adoption-value">{agent_edits_per_user:.1f} <span class="adoption-pct">({total_agent_edits:,} / {total_users:,})</span></div>'
            f'      <div class="adoption-label">{t.get("adopt_agent_edits_per_user", "Agent Edits / User")} <span class="adoption-period">(28d)</span></div>'
            f'      <div class="adoption-desc">{t.get("adopt_agent_edits_per_user_desc", "Average autonomous code edits per active user")}</div>'
            f'      <div class="agent-scale">'
            f'        <div class="agent-scale-row{"  agent-scale-active" if agent_edits_per_user < 10 else ""}">'
            f'          <span class="agent-dot" style="background:#f85149"></span>'
            f'          <span>&lt; 10 — Cautious / Legacy</span></div>'
            f'        <div class="agent-scale-row{"  agent-scale-active" if 10 <= agent_edits_per_user <= 50 else ""}">'
            f'          <span class="agent-dot" style="background:#d29922"></span>'
            f'          <span>10–50 — Standard Adopters</span></div>'
            f'        <div class="agent-scale-row{"  agent-scale-active" if 50 < agent_edits_per_user <= 100 else ""}">'
            f'          <span class="agent-dot" style="background:#3fb950"></span>'
            f'          <span>50–100 — Advanced</span></div>'
            f'        <div class="agent-scale-row{"  agent-scale-active" if agent_edits_per_user > 100 else ""}">'
            f'          <span class="agent-dot" style="background:#58a6ff"></span>'
            f'          <span>&gt; 100 — Agent-First (Power Users)</span></div>'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )
        return HTMLResponse(html)

    @app.get("/api/insights", response_class=HTMLResponse)
    async def api_insights(request: Request):
        """Return Quick Insights as an HTML fragment for HTMX swap."""
        lang = _lang(request)
        t = get_translations(lang)
        try:
            records = await _get_raw_org_metrics()
        except Exception as e:
            logger.error("Insights error: %s", e)
            return HTMLResponse(
                f'<h3>{t.get("dash_insights_title", "Quick Insights")}</h3>'
                f'<p style="color:var(--text-secondary)">{e}</p>'
            )

        if not records:
            return HTMLResponse(
                f'<h3>{t.get("dash_insights_title", "Quick Insights")}</h3>'
                f'<p style="color:var(--text-secondary)">No data</p>'
            )

        # --- Top 5 languages (exclude "Other"/"Others"/"Unknown") ---
        _EXCLUDE_LANGS = {"other", "others", "unknown"}
        lang_counts: dict[str, int] = {}
        for rec in records:
            for lf in rec.get("totals_by_language_feature", []):
                name = lf.get("language", "")
                if name and name.lower() not in _EXCLUDE_LANGS:
                    lang_counts[name] = lang_counts.get(name, 0) + lf.get("code_generation_activity_count", 0)
        top5_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # --- Top IDE ---
        ide_counts: dict[str, int] = {}
        for rec in records:
            for ide in rec.get("totals_by_ide", []):
                name = ide.get("ide", "")
                if name:
                    ide_counts[name] = ide_counts.get(name, 0) + 1
        top_ide = max(ide_counts, key=ide_counts.get) if ide_counts else "N/A"

        # --- Acceptance rate (last 7 vs prev 7) ---
        sorted_recs = sorted(records, key=lambda r: r.get("day", ""))
        last7 = sorted_recs[-7:]
        prev7 = sorted_recs[-14:-7] if len(sorted_recs) >= 14 else []

        def _acc_rate(recs: list) -> float:
            sugg, acc = 0, 0
            for r in recs:
                for f in r.get("totals_by_feature", []):
                    if f.get("feature") == "code_completion":
                        sugg += f.get("code_generation_activity_count", 0)
                        acc += f.get("code_acceptance_activity_count", 0)
            return (acc / sugg * 100) if sugg else 0.0

        rate_last = _acc_rate(last7)
        rate_prev = _acc_rate(prev7)
        rate_delta = rate_last - rate_prev
        rate_arrow = "↑" if rate_delta > 0 else ("↓" if rate_delta < 0 else "→")
        rate_color = "var(--accent-green)" if rate_delta >= 0 else "#f85149"

        # --- Most active day ---
        day_activity: dict[str, int] = {}
        for rec in sorted_recs:
            day = rec.get("day", "")
            day_activity[day] = rec.get("daily_active_users", 0)
        best_day = max(day_activity, key=day_activity.get) if day_activity else "N/A"
        best_day_users = day_activity.get(best_day, 0)

        # --- Seat utilization ---
        seat_html = ""
        orch = app.state.orchestrator
        if orch:
            try:
                seat_result = await orch._tool_seat_info({"org": config.github_org})
                si = seat_result.get("seat_info", {})
                total = si.get("total_seats", 0)
                breakdown = si.get("seat_breakdown", {})
                active = breakdown.get("active_this_cycle", 0)
                if total > 0:
                    util_pct = active / total * 100
                    seat_html = (
                        f'<div class="insight-card">'
                        f'  <span class="insight-value">{active}/{total}</span>'
                        f'  <span class="insight-label">{t.get("insight_seat_util", "Seat utilization")} ({util_pct:.0f}%)</span>'
                        f'</div>'
                    )
            except Exception:
                pass

        # Build top-5 languages HTML
        if top5_langs:
            total_lang = sum(v for _, v in top5_langs)
            lang_rows = "".join(
                f'<div class="lang-row">'
                f'<span class="lang-name">{name}</span>'
                f'<span class="lang-pct">{count / total_lang * 100:.0f}%</span>'
                f'</div>'
                for name, count in top5_langs
            )
            lang_card = (
                f'<div class="insight-card insight-card-tall">'
                f'  <span class="insight-label">{t.get("insight_top_langs", "Top 5 languages")}</span>'
                f'  <div class="lang-list">{lang_rows}</div>'
                f'</div>'
            )
        else:
            lang_card = (
                f'<div class="insight-card">'
                f'  <span class="insight-value">N/A</span>'
                f'  <span class="insight-label">{t.get("insight_top_langs", "Top 5 languages")}</span>'
                f'</div>'
            )

        html = (
            f'<h3>{t.get("dash_insights_title", "Quick Insights")}</h3>'
            f'<div class="insights-grid">'
            f'  {lang_card}'
            f'  <div class="insight-card">'
            f'    <span class="insight-value">{top_ide}</span>'
            f'    <span class="insight-label">{t.get("insight_top_ide", "Top IDE")}</span>'
            f'  </div>'
            f'  <div class="insight-card">'
            f'    <span class="insight-value">{rate_last:.1f}% <span style="color:{rate_color};font-size:14px">{rate_arrow} {abs(rate_delta):.1f}pp</span></span>'
            f'    <span class="insight-label">{t.get("insight_acc_trend", "Acceptance rate (7d trend)")}</span>'
            f'  </div>'
            f'  <div class="insight-card">'
            f'    <span class="insight-value">{best_day_users}</span>'
            f'    <span class="insight-label">{t.get("insight_peak_day", "Peak day")} ({best_day})</span>'
            f'  </div>'
            f'  {seat_html}'
            f'</div>'
        )
        return HTMLResponse(html)

    @app.get("/api/metrics/json")
    async def api_metrics_json():
        """Raw JSON metrics endpoint (for programmatic access)."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}

        try:
            result = await orch._tool_org_metrics({
                "org": config.github_org,
                "period": "28-day",
            })
            return result
        except Exception as e:
            logger.error("API metrics error: %s", e)
            return {"error": str(e)}

    @app.get("/api/seat-info")
    async def api_seat_info():
        """API endpoint for seat information."""
        orch = app.state.orchestrator
        if not orch:
            return {"error": "Orchestrator not initialized"}

        try:
            result = await orch._tool_seat_info({"org": config.github_org})
            return result
        except Exception as e:
            logger.error("API seat info error: %s", e)
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Setup page — org structure import & GitHub ID mapping
    # ------------------------------------------------------------------

    def _get_orgdb() -> OrgDatabase:
        """Get or create the OrgDatabase instance."""
        if not hasattr(app.state, "orgdb") or app.state.orgdb is None:
            app.state.orgdb = OrgDatabase()
        return app.state.orgdb

    @app.get("/setup", response_class=HTMLResponse)
    async def setup_page(request: Request):
        """Setup page for org structure import and user mapping."""
        db = _get_orgdb()
        stats = db.mapping_stats()
        return templates.TemplateResponse(
            "setup.html",
            _ctx(request, title="Copilot Pulse — Setup", active_tab="setup", stats=stats),
        )

    @app.post("/api/import-org")
    async def api_import_org(file: UploadFile = File(...)):
        """Upload and import an Excel org structure file."""
        if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
            return JSONResponse(
                {"error": "Il file deve essere in formato .xlsx"},
                status_code=400,
            )

        # Save uploaded file to a temp location
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            from ..orgdata.loader import OrgDataLoader

            loader = OrgDataLoader(tmp_path)
            employees = loader.load()

            db = _get_orgdb()
            dicts = [e.model_dump() for e in employees]
            count = db.import_employees(dicts)

            # Also update orchestrator's orgdb reference
            orch = app.state.orchestrator
            if orch and not orch._orgdb:
                orch._orgdb = db

            stats = db.mapping_stats()
            return {
                "success": True,
                "imported": count,
                "stats": stats,
            }
        except Exception as e:
            logger.error("Import org error: %s", e)
            return JSONResponse({"error": str(e)}, status_code=500)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @app.get("/api/mapping-stats")
    async def api_mapping_stats():
        """Get current mapping statistics."""
        db = _get_orgdb()
        return db.mapping_stats()

    @app.get("/api/unmatched-users")
    async def api_unmatched_users():
        """Get list of unmatched GitHub users."""
        db = _get_orgdb()
        unmatched = db.unmatched_github_users()
        return {"unmatched": unmatched, "count": len(unmatched)}

    @app.post("/api/map-users/auto")
    async def api_auto_map(request: Request):
        """Run auto-mapping of GitHub users to employees."""
        db = _get_orgdb()
        rows = db._conn.execute(
            "SELECT DISTINCT github_login FROM copilot_usage"
        ).fetchall()
        github_users = [r["github_login"] for r in rows]

        if not github_users:
            return JSONResponse(
                {"error": "No Copilot usage data found. Use the Chat first to fetch user data."},
                status_code=400,
            )

        # Read optional pattern config from request body
        try:
            body = await request.json()
        except Exception:
            body = {}
        email_pattern = body.get("email_pattern", "{name}.{surname}")
        duplicate_strategy = body.get("duplicate_strategy", "skip")

        # Validate inputs
        allowed_patterns = ["{name}.{surname}", "{surname}.{name}", "{name1}.{surname}"]
        if email_pattern not in allowed_patterns:
            email_pattern = "{name}.{surname}"
        if duplicate_strategy not in ("skip", "seq2", "first"):
            duplicate_strategy = "skip"

        matches = db.auto_map_by_email(
            github_users,
            email_pattern=email_pattern,
            duplicate_strategy=duplicate_strategy,
        )
        stats = db.mapping_stats()
        return {
            "success": True,
            "new_matches": len(matches),
            "matches": matches,
            "stats": stats,
        }

    @app.post("/api/map-users/manual")
    async def api_manual_map(
        employee_id: str = Form(...),
        github_login: str = Form(...),
    ):
        """Manually map an employee to a GitHub login."""
        db = _get_orgdb()

        # Verify employee exists
        row = db._conn.execute(
            "SELECT employee_id, name, surname FROM employees WHERE employee_id = ?",
            (employee_id,),
        ).fetchone()
        if not row:
            return JSONResponse(
                {"error": f"Employee ID '{employee_id}' non trovato"},
                status_code=404,
            )

        db.set_github_id(employee_id, github_login, method="manual")
        stats = db.mapping_stats()
        return {
            "success": True,
            "mapped": f"{row['name']} {row['surname']} → {github_login}",
            "stats": stats,
        }

    @app.get("/api/employees/search")
    async def api_search_employees(q: str = ""):
        """Search employees by name, surname, or ID (for autocomplete)."""
        if len(q) < 2:
            return {"results": []}
        db = _get_orgdb()
        rows = db._conn.execute(
            """SELECT employee_id, name, surname, email_work, github_id
               FROM employees
               WHERE LOWER(name) LIKE LOWER(?) OR LOWER(surname) LIKE LOWER(?)
                  OR LOWER(employee_id) LIKE LOWER(?)
               LIMIT 20""",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
        return {
            "results": [
                {
                    "employee_id": r["employee_id"],
                    "name": r["name"],
                    "surname": r["surname"],
                    "email": r["email_work"],
                    "github_id": r["github_id"],
                }
                for r in rows
            ]
        }

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket):
        """WebSocket endpoint for real-time chat with the agent.

        Streams ``type="log"`` messages for each orchestrator step so the
        browser can show them in an expandable details section.
        """
        await websocket.accept()
        orch = app.state.orchestrator

        if not orch:
            await websocket.send_json({"type": "error", "message": "Agent not initialized"})
            await websocket.close()
            return

        async def _send_log(message: str) -> None:
            """Forward orchestrator log entries to the browser."""
            try:
                await websocket.send_json({"type": "log", "message": message})
            except Exception:
                pass  # Connection may have closed mid-processing.

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                question = message.get("question", "")

                if not question:
                    continue

                await websocket.send_json({"type": "status", "message": ""})

                # Attach log callback so the orchestrator streams steps to the
                # browser and suppresses terminal output for this request.
                orch._log_callback = _send_log
                try:
                    response = await orch.ask(question)
                    await websocket.send_json({
                        "type": "response",
                        "message": response,
                    })
                except Exception as e:
                    logger.error("Chat error: %s", e)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Errore: {e}",
                    })
                finally:
                    orch._log_callback = None

        except WebSocketDisconnect:
            orch._log_callback = None
            logger.info("WebSocket client disconnected")

    return app
