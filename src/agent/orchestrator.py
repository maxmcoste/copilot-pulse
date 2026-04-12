"""Main conversational agent orchestrator with pluggable LLM providers."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ..cache.store import CacheStore
from ..config import AppConfig
from ..github_client.base_client import GitHubBaseClient, GitHubAPIError
from ..github_client.metrics_api import LegacyMetricsAPI
from ..github_client.models import UserUsageRecord
from ..github_client.usage_metrics_api import UsageMetricsAPI
from ..github_client.user_management_api import UserManagementAPI
from ..orgdata.database import OrgDatabase
from .data_analyzer import DataAnalyzer
from .llm_provider import LLMResponse
from .providers import create_provider
from .response_composer import ResponseComposer
from .tools_schema import TOOLS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Sei "Copilot Pulse", un analista esperto di metriche GitHub Copilot. Il tuo compito è aiutare \
l'utente a comprendere come la propria organizzazione utilizza GitHub Copilot.

CAPACITÀ:
- Recuperare metriche a livello enterprise, organizzazione, team e singolo utente
- Analizzare trend di adozione, engagement, acceptance rate, linee di codice
- Confrontare team, linguaggi, editor e modelli
- Identificare utenti top performer e quelli inattivi
- Generare grafici e report esportabili
- Calcolare metriche derivate e insight azionabili

COMPORTAMENTO:
- Rispondi in italiano a meno che l'utente non scriva in inglese
- Quando l'utente fa una domanda, pianifica quali tool invocare in sequenza
- Prima recupera i dati (get_*), poi analizzali (analyze_data), poi visualizza (generate_chart) \
e se richiesto esporta (export_report)
- Fornisci sempre insight interpretativi, non solo numeri grezzi
- Se i dati sono insufficienti, spiega perché e suggerisci alternative
- Proponi follow-up interessanti ("Vuoi anche vedere il breakdown per linguaggio?")
- Quando mostri percentuali, arrotonda a 1 decimale
- Segnala anomalie o trend significativi proattivamente

METRICHE CHIAVE CHE CONOSCI:
- DAU/WAU (Daily/Weekly Active Users): utenti unici che hanno interagito con Copilot
- Acceptance Rate: rapporto tra suggerimenti accettati e suggerimenti totali
- LoC (Lines of Code): righe suggerite, aggiunte, cancellate
- Feature adoption: distribuzione utilizzo tra completions, chat, agent, CLI
- PR impact: come l'attività Copilot correla con il ciclo PR
- Seat utilization: rapporto tra seat assegnati e effettivamente utilizzati

LIMITAZIONI DA COMUNICARE:
- I dati hanno un ritardo di ~2 giorni lavorativi rispetto all'attività reale
- Le metriche richiedono che la telemetria sia abilitata nell'IDE dell'utente
- Le metriche per team richiedono almeno 5 membri con licenza attiva
- Le API legacy (endpoint /metrics senza /reports/) verranno dismesse il 2 aprile 2026

CONTESTO CONFIGURAZIONE:
- Enterprise: {enterprise}
- Organization: {org}
- API: {api_label}
- Auth: {auth_mode}

NOTA IMPORTANTE SULL'AUTENTICAZIONE:
- Se auth_mode è "app" (GitHub App), usa SEMPRE i tool a livello organizzazione
  (get_organization_metrics, get_user_metrics con scope=organization) perché le
  enterprise API non sono accessibili con un'installazione App a livello org.
- Preferisci i dati a 28 giorni (/28-day/latest) quando l'utente chiede dati recenti
  senza una data precisa. Per date specifiche usa period=1-day con day=YYYY-MM-DD.
- I dati 1-day richiedono il parametro 'day' (data specifica). Se l'utente chiede
  "gli ultimi N giorni", fai N chiamate separate con period=1-day per ogni giorno,
  oppure usa 28-day se N è grande.
"""

MAX_HISTORY_MESSAGES = 40
MAX_TOOL_ITERATIONS = 10
# Maximum characters of a single tool result stored in conversation history.
# Full data is always retained in self.analyzer / self.cache — this limit only
# controls what the LLM sees to stay within the 200k-token context window.
MAX_TOOL_RESULT_CHARS = 30_000


class Orchestrator:
    """Main agent orchestrator managing the conversation loop.

    Args:
        config: Validated application configuration.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.console = Console()
        self.composer = ResponseComposer(self.console)
        # Optional callback for streaming log entries to the web dashboard.
        # When set, console output is suppressed and logs go to this callback.
        # Signature: async (message: str) -> None
        self._log_callback: Any = None
        self.analyzer = DataAnalyzer()
        self.cache = CacheStore(ttl_hours=config.cache_ttl_hours)

        self._provider = create_provider(config)
        from ..github_client import build_github_auth

        self._gh_client = GitHubBaseClient(
            build_github_auth(config), config.github_api_version
        )
        self._usage_api = UsageMetricsAPI(self._gh_client)
        self._user_mgmt_api = UserManagementAPI(self._gh_client)
        self._legacy_api: LegacyMetricsAPI | None = None
        if config.use_legacy_api:
            self._legacy_api = LegacyMetricsAPI(self._gh_client)

        # Connect to org database (SQLite)
        self._orgdb: OrgDatabase | None = None
        try:
            self._orgdb = OrgDatabase()
            emp_count = self._orgdb.employee_count()
            if emp_count > 0:
                mapped = self._orgdb.mapped_count()
                logger.info(
                    "Org database connected: %d employees, %d with GitHub ID",
                    emp_count, mapped,
                )
            else:
                logger.info("Org database connected but empty. Run 'copilot-pulse import-org' to load data.")
        except Exception as e:
            logger.warning("Could not connect to org database: %s", e)

        self._history: list[dict[str, Any]] = []
        api_label = "legacy" if config.use_legacy_api else "Usage Metrics API (nuova)"
        org_info = ""
        if self._orgdb and self._orgdb.employee_count() > 0:
            emp_count = self._orgdb.employee_count()
            mapped = self._orgdb.mapped_count()
            org_info = (
                f"\n\nSTRUTTURA ORGANIZZATIVA CARICATA (SQLite):\n"
                f"- {emp_count} dipendenti nel database\n"
                f"- {mapped} con GitHub ID associato\n"
                f"- Campi disponibili per analisi incrociate: fascia d'età, genere, location, "
                f"job family, job level, management level, Sup Org Level 2-10\n"
                f"- Usa get_org_structure_summary per vedere la distribuzione\n"
                f"- Usa analyze_org_copilot_usage per incrociare dati Copilot con struttura org"
            )
        self._system_prompt = SYSTEM_PROMPT.format(
            enterprise=config.github_enterprise or "(non configurata)",
            org=config.github_org or "(non configurata)",
            api_label=api_label,
            auth_mode=config.auth_mode,
        ) + org_info

    async def run_interactive(self) -> None:
        """Run the interactive conversational loop."""
        self.console.print(
            Panel(
                "[bold cyan]Copilot Pulse[/] — Il tuo analista Copilot AI\n\n"
                "Chiedimi qualsiasi cosa sull'utilizzo di Copilot nella tua organizzazione.\n"
                "Comandi: [bold]/dashboard[/] · [bold]/export[/] <formato> · "
                "[bold]/cache clear[/] · [bold]/quit[/]",
                border_style="cyan",
            )
        )

        while True:
            try:
                user_input = Prompt.ask("\n[bold green]Tu[/]")
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]Arrivederci![/]")
                break

            if not user_input.strip():
                continue

            if user_input.strip().startswith("/"):
                should_continue = await self._handle_command(user_input.strip())
                if not should_continue:
                    break
                continue

            await self.ask(user_input)

        await self._cleanup()

    async def _emit_log(self, message: str) -> None:
        """Send a log entry to the web dashboard (if connected) or console."""
        if self._log_callback is not None:
            await self._log_callback(message)
        else:
            self.composer.display_status(message)

    async def ask(self, question: str) -> str:
        """Process a single question and return the text response.

        Args:
            question: User's natural language question.

        Returns:
            Agent's text response.
        """
        self._history.append({"role": "user", "content": question})
        self._trim_history()

        await self._emit_log("Analizzo la tua richiesta...")
        if self._log_callback is None:
            with self.console.status("[cyan]Analizzo la tua richiesta...[/]"):
                response = self._call_llm()
        else:
            response = self._call_llm()

        # Tool use loop
        iterations = 0
        while response.has_tool_calls and iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            tool_results = await self._execute_tools(response)

            self._history.append(self._provider.serialize_assistant(response))
            self._history.append(self._provider.format_tool_results(tool_results))

            await self._emit_log(f"Elaboro i risultati... (step {iterations})")
            if self._log_callback is None:
                with self.console.status(f"[cyan]Elaboro i risultati... (step {iterations})[/]"):
                    response = self._call_llm()
            else:
                response = self._call_llm()

        # Display final text
        final_text = response.text
        self._history.append({"role": "assistant", "content": final_text})
        if self._log_callback is None:
            self.composer.display_text(final_text)

        return final_text

    def _call_llm(self) -> LLMResponse:
        """Call the configured LLM provider with current history and tools."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        date_context = (
            f"\n\nDATA CORRENTE: {today.isoformat()} "
            f"(ieri: {yesterday.isoformat()}). "
            f"Usa sempre queste date quando l'utente menziona 'oggi', 'ieri', 'questa settimana', ecc."
        )
        return self._provider.call(
            system_prompt=self._system_prompt + date_context,
            messages=self._history,
            tools=TOOLS,
        )

    async def _execute_tools(self, response: LLMResponse) -> list[dict[str, Any]]:
        """Execute tool calls from the LLM response.

        Args:
            response: Normalized LLM response with tool calls.

        Returns:
            List of tool result dicts with tool_call_id and content.
        """
        results: list[dict[str, Any]] = []

        for tc in response.tool_calls:
            await self._emit_log(f"→ Eseguo: {tc.name}")

            try:
                result = await self._dispatch_tool(tc.name, tc.arguments)
                content = json.dumps(result, default=str)
                # Truncate overly large tool results so the conversation
                # stays within the LLM context window.  The full data is
                # already loaded into self.analyzer / self.cache.
                content = self._truncate_tool_result(content)
                results.append({
                    "tool_call_id": tc.id,
                    "content": content,
                })
            except Exception as exc:
                logger.error("Tool %s failed: %s", tc.name, exc)
                results.append({
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": str(exc)}),
                    "is_error": True,
                })

        return results

    async def _dispatch_tool(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Route a tool call to the appropriate handler.

        Args:
            name: Tool name.
            input_data: Tool input parameters.

        Returns:
            Tool result as a dict.
        """
        match name:
            case "get_enterprise_metrics":
                return await self._tool_enterprise_metrics(input_data)
            case "get_organization_metrics":
                return await self._tool_org_metrics(input_data)
            case "get_team_metrics":
                return await self._tool_team_metrics(input_data)
            case "get_user_metrics":
                return await self._tool_user_metrics(input_data)
            case "get_seat_info":
                return await self._tool_seat_info(input_data)
            case "analyze_data":
                return self._tool_analyze(input_data)
            case "generate_chart":
                return self._tool_generate_chart(input_data)
            case "export_report":
                return await self._tool_export_report(input_data)
            case "get_org_structure_summary":
                return self._tool_org_summary(input_data)
            case "analyze_org_copilot_usage":
                return self._tool_org_copilot_analysis(input_data)
            case _:
                return {"error": f"Unknown tool: {name}"}

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _tool_enterprise_metrics(self, input_data: dict[str, Any]) -> dict[str, Any]:
        enterprise = self.config.github_enterprise
        if not enterprise:
            return {"error": "Enterprise non configurata. Imposta GITHUB_ENTERPRISE in .env"}

        day = input_data.get("day")
        period = input_data.get("period", "28-day")

        cache_key = f"enterprise_metrics:{enterprise}:{period}:{day or 'latest'}"
        cached = self.cache.get(cache_key)
        if cached:
            self.analyzer.load_metrics([
                self._dict_to_metrics(m) for m in cached
            ])
            return {"metrics": cached, "source": "cache", "count": len(cached)}

        try:
            if self.config.use_legacy_api and self._legacy_api:
                metrics = await self._legacy_api.get_enterprise_metrics(enterprise)
            else:
                metrics = await self._usage_api.get_enterprise_metrics(
                    enterprise, day=day, period=period
                )
        except GitHubAPIError as e:
            return {"error": e.message}

        self.analyzer.load_metrics(metrics)
        serialized = [m.model_dump(mode="json") for m in metrics]
        self.cache.set(cache_key, serialized)

        return {"metrics": serialized, "source": "api", "count": len(metrics)}

    async def _tool_org_metrics(self, input_data: dict[str, Any]) -> dict[str, Any]:
        org = input_data.get("org") or self.config.github_org
        if not org:
            return {"error": "Organizzazione non specificata. Passa 'org' o imposta GITHUB_ORG."}

        day = input_data.get("day")
        period = input_data.get("period", "28-day")

        cache_key = f"org_metrics:{org}:{period}:{day or 'latest'}"
        cached = self.cache.get(cache_key)
        if cached:
            self.analyzer.load_metrics([self._dict_to_metrics(m) for m in cached])
            return {"metrics": cached, "source": "cache", "count": len(cached)}

        try:
            if self.config.use_legacy_api and self._legacy_api:
                metrics = await self._legacy_api.get_org_metrics(org)
            else:
                metrics = await self._usage_api.get_org_metrics(org, day=day, period=period)
        except GitHubAPIError as e:
            return {"error": e.message}

        self.analyzer.load_metrics(metrics)
        serialized = [m.model_dump(mode="json") for m in metrics]
        self.cache.set(cache_key, serialized)

        return {"metrics": serialized, "source": "api", "count": len(metrics)}

    async def _tool_team_metrics(self, input_data: dict[str, Any]) -> dict[str, Any]:
        org = input_data.get("org") or self.config.github_org
        team_slug = input_data.get("team_slug")
        if not org or not team_slug:
            return {"error": "Specificare org e team_slug."}

        since = input_data.get("since")
        until = input_data.get("until")

        # Team metrics only available via legacy API
        if not self._legacy_api:
            self._legacy_api = LegacyMetricsAPI(self._gh_client)

        cache_key = f"team_metrics:{org}:{team_slug}:{since}:{until}"
        cached = self.cache.get(cache_key)
        if cached:
            self.analyzer.load_metrics([self._dict_to_metrics(m) for m in cached])
            return {"metrics": cached, "source": "cache", "count": len(cached)}

        try:
            metrics = await self._legacy_api.get_team_metrics(
                org, team_slug, since=since, until=until
            )
        except GitHubAPIError as e:
            return {"error": e.message}

        self.analyzer.load_metrics(metrics)
        serialized = [m.model_dump(mode="json") for m in metrics]
        self.cache.set(cache_key, serialized)

        return {"metrics": serialized, "source": "api", "count": len(metrics)}

    async def _tool_user_metrics(self, input_data: dict[str, Any]) -> dict[str, Any]:
        scope = input_data.get("scope", "organization")
        day = input_data.get("day")
        period = input_data.get("period", "28-day")

        if scope == "enterprise":
            enterprise = self.config.github_enterprise
            if not enterprise:
                return {"error": "Enterprise non configurata."}
            cache_key = f"user_metrics:enterprise:{enterprise}:{period}:{day or 'latest'}"
            cached = self.cache.get(cache_key)
            if cached:
                self.analyzer.load_users([UserUsageRecord(**u) for u in cached])
                return {"users": cached, "source": "cache", "count": len(cached)}
            try:
                users = await self._usage_api.get_enterprise_user_metrics(
                    enterprise, day=day, period=period
                )
            except GitHubAPIError as e:
                return {"error": e.message}
        else:
            org = input_data.get("org") or self.config.github_org
            if not org:
                return {"error": "Organizzazione non specificata."}
            cache_key = f"user_metrics:org:{org}:{period}:{day or 'latest'}"
            cached = self.cache.get(cache_key)
            if cached:
                self.analyzer.load_users([UserUsageRecord(**u) for u in cached])
                return {"users": cached, "source": "cache", "count": len(cached)}
            try:
                users = await self._usage_api.get_org_user_metrics(org, day=day, period=period)
            except GitHubAPIError as e:
                return {"error": e.message}

        self.analyzer.load_users(users)
        serialized = [u.model_dump(mode="json") for u in users]
        self.cache.set(cache_key, serialized)

        # Also store in org database for cross-dimensional queries
        if self._orgdb:
            self._orgdb.store_usage(serialized, period=period)

        return {"users": serialized, "source": "api", "count": len(users)}

    async def _tool_seat_info(self, input_data: dict[str, Any]) -> dict[str, Any]:
        org = input_data.get("org") or self.config.github_org
        if not org:
            return {"error": "Organizzazione non specificata."}

        cache_key = f"seat_info:{org}"
        cached = self.cache.get(cache_key)
        if cached:
            from ..github_client.models import SeatInfo
            self.analyzer.load_seats(SeatInfo(**cached))
            return {"seat_info": cached, "source": "cache"}

        try:
            seat_info = await self._user_mgmt_api.get_seats(org)
        except GitHubAPIError as e:
            return {"error": e.message}

        self.analyzer.load_seats(seat_info)
        serialized = seat_info.model_dump(mode="json")
        self.cache.set(cache_key, serialized)

        return {"seat_info": serialized, "source": "api"}

    def _tool_analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        analysis_type = input_data.get("analysis_type", "custom")
        params = input_data.get("params", {})
        result = self.analyzer.analyze(analysis_type, params)

        if self._log_callback is None:
            self.composer.display_analysis(result)
        return result

    def _tool_generate_chart(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from ..reports.chart_engine import ChartEngine

        chart_type = input_data.get("chart_type", "bar")
        title = input_data.get("title", "Chart")
        data = input_data.get("data", {})
        output_format = input_data.get("output_format", "terminal")

        engine = ChartEngine()

        if output_format in ("terminal", "all") and self._log_callback is None:
            engine.render_terminal(chart_type, title, data, self.console)

        file_path = None
        if output_format in ("png", "all"):
            file_path = engine.render_png(chart_type, title, data)

        return {
            "chart_rendered": True,
            "output_format": output_format,
            "file_path": str(file_path) if file_path else None,
        }

    async def _tool_export_report(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from ..reports.export_engine import ExportEngine

        fmt = input_data.get("format", "csv")
        title = input_data.get("title", "Copilot Pulse Report")
        sections = input_data.get("sections", [])
        filename = input_data.get("filename", "copilot_report")

        engine = ExportEngine()
        file_path = engine.export(fmt, title, sections, filename)

        return {
            "exported": True,
            "format": fmt,
            "file_path": str(file_path),
        }

    # ------------------------------------------------------------------
    # Org structure tools
    # ------------------------------------------------------------------

    def _tool_org_summary(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if not self._orgdb or self._orgdb.employee_count() == 0:
            return {"error": "Database org vuoto. Esegui 'copilot-pulse import-org <file.xlsx>' per importare i dati."}
        summary = self._orgdb.org_summary()
        if self._log_callback is None:
            self.composer.display_analysis({"type": "org_summary", **summary})
        return summary

    def _tool_org_copilot_analysis(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if not self._orgdb or self._orgdb.employee_count() == 0:
            return {"error": "Database org vuoto. Esegui 'copilot-pulse import-org <file.xlsx>' per importare i dati."}

        # Check if we have usage data in the DB
        usage_count = self._orgdb._conn.execute(
            "SELECT COUNT(*) FROM copilot_usage"
        ).fetchone()[0]
        if usage_count == 0:
            return {"error": "Nessun dato di utilizzo Copilot nel database. Usa prima get_user_metrics per recuperare i dati."}

        group_by = input_data.get("group_by", "age_range")
        metric = input_data.get("metric", "active_users")
        filter_field = input_data.get("filter_field")
        filter_value = input_data.get("filter_value")

        result = self._orgdb.analyze_copilot_by(
            group_by=group_by,
            metric=metric,
            filter_field=filter_field,
            filter_value=filter_value,
        )

        if self._log_callback is None:
            self.composer.display_analysis(result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dict_to_metrics(d: dict) -> Any:
        """Reconstruct CopilotDayMetrics from a serialized dict."""
        from ..github_client.models import CopilotDayMetrics
        return CopilotDayMetrics(**d)

    @staticmethod
    def _truncate_tool_result(content: str) -> str:
        """Truncate a serialized tool result that exceeds the size budget.

        For results containing large ``metrics`` or ``users`` arrays, the
        array is trimmed to a small sample with a count annotation so the
        LLM still understands the shape and magnitude of the data without
        consuming excessive context.
        """
        if len(content) <= MAX_TOOL_RESULT_CHARS:
            return content

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return content[:MAX_TOOL_RESULT_CHARS] + "\n... [truncated]"

        changed = False
        for key in ("metrics", "users", "seats"):
            if isinstance(data.get(key), list) and len(data[key]) > 5:
                total = len(data[key])
                data[key] = data[key][:5]
                data[f"_{key}_note"] = (
                    f"Showing first 5 of {total} records. "
                    f"Full data is loaded in memory for analysis — "
                    f"use the analyze_data tool to compute aggregates."
                )
                changed = True

        if changed:
            return json.dumps(data, default=str)

        # Fallback: hard-truncate for result shapes we didn't anticipate.
        return content[:MAX_TOOL_RESULT_CHARS] + "\n... [truncated]"

    def _trim_history(self) -> None:
        """Keep conversation history within context limits."""
        if len(self._history) > MAX_HISTORY_MESSAGES:
            # Keep system context and recent messages
            self._history = self._history[-MAX_HISTORY_MESSAGES:]
            # Ensure first message is from user
            while self._history and self._history[0].get("role") != "user":
                self._history.pop(0)

    async def _handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns False to exit."""
        parts = cmd.split()
        command = parts[0].lower()

        match command:
            case "/quit" | "/exit" | "/q":
                self.console.print("[dim]Arrivederci![/]")
                return False
            case "/cache":
                if len(parts) > 1 and parts[1] == "clear":
                    count = self.cache.clear()
                    self.console.print(f"[green]Cache svuotata ({count} entries rimosse)[/]")
                else:
                    stats = self.cache.stats()
                    self.console.print(f"Cache: {stats['valid_entries']} entries valide, "
                                       f"{stats['expired_entries']} scadute")
            case "/dashboard":
                self.console.print(
                    f"[cyan]Avvia la dashboard con:[/] copilot-pulse dashboard\n"
                    f"[dim]http://localhost:{self.config.web_port}[/]"
                )
            case "/export":
                fmt = parts[1] if len(parts) > 1 else "pdf"
                self.console.print(f"[cyan]Export in formato {fmt}...[/]")
                await self.ask(f"Genera un report completo in formato {fmt}")
            case "/help":
                self.console.print(
                    Panel(
                        "[bold]/exit[/] · [bold]/quit[/] · [bold]/q[/] — Esci\n"
                        "[bold]/cache clear[/] — Svuota la cache\n"
                        "[bold]/dashboard[/] — Info sulla dashboard web\n"
                        "[bold]/export[/] <csv|excel|pdf> — Esporta report\n"
                        "[bold]/help[/] — Questo messaggio",
                        title="Comandi disponibili",
                        border_style="cyan",
                    )
                )
            case _:
                self.console.print(f"[yellow]Comando sconosciuto: {command}[/]")

        return True

    async def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self._gh_client.close()
        except Exception:
            pass
        self.cache.close()
        if self._orgdb:
            self._orgdb.close()
