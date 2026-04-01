"""Main conversational agent orchestrator using Anthropic tool use."""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
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
from .data_analyzer import DataAnalyzer
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
"""

MAX_HISTORY_MESSAGES = 40
MAX_TOOL_ITERATIONS = 10


class Orchestrator:
    """Main agent orchestrator managing the conversation loop.

    Args:
        config: Validated application configuration.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.console = Console()
        self.composer = ResponseComposer(self.console)
        self.analyzer = DataAnalyzer()
        self.cache = CacheStore(ttl_hours=config.cache_ttl_hours)

        self._anthropic = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self._gh_client = GitHubBaseClient(config.github_token, config.github_api_version)
        self._usage_api = UsageMetricsAPI(self._gh_client)
        self._user_mgmt_api = UserManagementAPI(self._gh_client)
        self._legacy_api: LegacyMetricsAPI | None = None
        if config.use_legacy_api:
            self._legacy_api = LegacyMetricsAPI(self._gh_client)

        self._history: list[dict[str, Any]] = []
        api_label = "legacy" if config.use_legacy_api else "Usage Metrics API (nuova)"
        self._system_prompt = SYSTEM_PROMPT.format(
            enterprise=config.github_enterprise or "(non configurata)",
            org=config.github_org or "(non configurata)",
            api_label=api_label,
        )

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

    async def ask(self, question: str) -> str:
        """Process a single question and return the text response.

        Args:
            question: User's natural language question.

        Returns:
            Agent's text response.
        """
        self._history.append({"role": "user", "content": question})
        self._trim_history()

        with self.console.status("[cyan]Analizzo la tua richiesta...[/]"):
            response = self._call_claude()

        # Tool use loop
        iterations = 0
        while response.stop_reason == "tool_use" and iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            tool_results = await self._execute_tools(response.content)

            self._history.append({"role": "assistant", "content": self._serialize_content(response.content)})
            self._history.append({"role": "user", "content": tool_results})

            with self.console.status(f"[cyan]Elaboro i risultati... (step {iterations})[/]"):
                response = self._call_claude()

        # Extract and display final text
        final_text = self._extract_text(response.content)
        self._history.append({"role": "assistant", "content": final_text})
        self.composer.display_text(final_text)

        return final_text

    def _call_claude(self) -> Any:
        """Call the Anthropic API with current history and tools."""
        return self._anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=self._system_prompt,
            messages=self._history,
            tools=TOOLS,
        )

    async def _execute_tools(self, content: list) -> list[dict[str, Any]]:
        """Execute tool calls from Claude's response.

        Args:
            content: Response content blocks that may contain tool_use blocks.

        Returns:
            List of tool_result message blocks.
        """
        results: list[dict[str, Any]] = []

        for block in content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                self.composer.display_status(f"  → Eseguo: {tool_name}")

                try:
                    result = await self._dispatch_tool(tool_name, tool_input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result, default=str),
                    })
                except Exception as exc:
                    logger.error("Tool %s failed: %s", tool_name, exc)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
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

        # Also display in terminal
        self.composer.display_analysis(result)
        return result

    def _tool_generate_chart(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from ..reports.chart_engine import ChartEngine

        chart_type = input_data.get("chart_type", "bar")
        title = input_data.get("title", "Chart")
        data = input_data.get("data", {})
        output_format = input_data.get("output_format", "terminal")

        engine = ChartEngine()

        if output_format in ("terminal", "all"):
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
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dict_to_metrics(d: dict) -> Any:
        """Reconstruct CopilotDayMetrics from a serialized dict."""
        from ..github_client.models import CopilotDayMetrics
        return CopilotDayMetrics(**d)

    @staticmethod
    def _serialize_content(content: list) -> list[dict[str, Any]]:
        """Serialize anthropic content blocks for history."""
        serialized = []
        for block in content:
            if hasattr(block, "type"):
                if block.type == "text":
                    serialized.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    serialized.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
        return serialized

    @staticmethod
    def _extract_text(content: list) -> str:
        """Extract text from response content blocks."""
        texts = []
        for block in content:
            if hasattr(block, "type") and block.type == "text":
                texts.append(block.text)
        return "\n".join(texts) if texts else ""

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
                        "[bold]/quit[/] — Esci\n"
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
        await self._gh_client.close()
        self.cache.close()
