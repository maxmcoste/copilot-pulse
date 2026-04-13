"""Copilot Pulse — CLI entry point and command definitions."""

from __future__ import annotations

import asyncio
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="copilot-pulse")
def cli() -> None:
    """Copilot Pulse — AI-powered GitHub Copilot usage analytics."""


@cli.command()
def chat() -> None:
    """Start the interactive conversational agent in the terminal."""
    from .config import load_config
    from .agent.orchestrator import Orchestrator

    config = load_config()
    orchestrator = Orchestrator(config)
    try:
        asyncio.run(orchestrator.run_interactive())
    except KeyboardInterrupt:
        console.print("\n[dim]Arrivederci![/]")


@cli.command()
@click.argument("question")
def ask(question: str) -> None:
    """Ask a single question and get the answer.

    QUESTION is the natural language query about Copilot usage.
    """
    from .config import load_config
    from .agent.orchestrator import Orchestrator

    config = load_config()
    orchestrator = Orchestrator(config)

    async def _ask():
        try:
            await orchestrator.ask(question)
        finally:
            await orchestrator._cleanup()

    asyncio.run(_ask())


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port (default from config)")
def dashboard(host: str, port: int | None) -> None:
    """Start the web dashboard."""
    import uvicorn
    from pathlib import Path

    from .config import load_config
    from .agent.orchestrator import Orchestrator
    from .reports.web_dashboard import create_app

    config = load_config()
    port = port or config.web_port

    # ── Redirect all logging to a file so the terminal stays clean ──
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "dashboard.log"

    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=1, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger = logging.getLogger()
    # Remove any existing handlers (e.g. the StreamHandler added by basicConfig in load_config)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(getattr(logging, config.log_level, logging.INFO))

    app = create_app(config)

    # Initialize orchestrator for the web app
    orchestrator = Orchestrator(config)
    app.state.orchestrator = orchestrator

    console.print(
        Panel(
            f"[bold cyan]Copilot Pulse Dashboard[/]\n\n"
            f"URL: http://localhost:{port}\n"
            f"Enterprise: {config.github_enterprise or 'N/A'}\n"
            f"Organization: {config.github_org or 'N/A'}\n"
            f"Logs: {log_file}",
            border_style="cyan",
        )
    )

    # Pass log_config=None to suppress uvicorn's default console logging;
    # uvicorn inherits the root logger configured above.
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=config.log_level.lower(),
        log_config=None,
    )


@cli.command()
@click.option(
    "--format", "fmt",
    type=click.Choice(["csv", "excel", "pdf"]),
    default="pdf",
    help="Export format",
)
@click.option("--period", default="28d", help="Period: 1d or 28d")
@click.option("--output", "output_dir", default="./reports", help="Output directory")
def report(fmt: str, period: str, output_dir: str) -> None:
    """Generate a report directly without interactive mode."""
    from pathlib import Path

    from .config import load_config
    from .agent.orchestrator import Orchestrator

    config = load_config()
    orchestrator = Orchestrator(config)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    period_label = "degli ultimi 28 giorni" if "28" in period else "di oggi"
    question = f"Genera un report completo {period_label} in formato {fmt}"

    async def _report():
        try:
            await orchestrator.ask(question)
        finally:
            await orchestrator._cleanup()

    console.print(f"[cyan]Generating {fmt.upper()} report...[/]")
    asyncio.run(_report())


@cli.command()
def status() -> None:
    """Show configuration status and connectivity check."""
    from .config import load_config
    from .cache.store import CacheStore
    from .github_client.base_client import GitHubBaseClient
    from .github_client.auth import build_github_auth, verify_token

    config = load_config()

    console.print(Panel("[bold]Configuration Status[/]", border_style="cyan"))
    console.print(f"  Auth Mode: {config.auth_mode.upper()}")
    console.print(f"  Enterprise: {config.github_enterprise or '[yellow]not set[/]'}")
    console.print(f"  Organization: {config.github_org or '[yellow]not set[/]'}")
    console.print(f"  API Version: {config.github_api_version}")
    console.print(f"  LLM Provider: {config.llm_provider}")
    console.print(f"  LLM Model: {config.llm_model or '(provider default)'}")
    console.print(f"  Legacy API: {'[yellow]enabled[/]' if config.use_legacy_api else 'disabled'}")
    console.print(f"  Cache TTL: {config.cache_ttl_hours}h")
    console.print(f"  Web Port: {config.web_port}")
    console.print(f"  Log Level: {config.log_level}")

    # Cache stats
    cache = CacheStore(ttl_hours=config.cache_ttl_hours)
    stats = cache.stats()
    console.print(f"\n  Cache entries: {stats['valid_entries']} valid, {stats['expired_entries']} expired")
    cache.close()

    # GitHub connectivity
    console.print("\n[bold]Connectivity Check[/]")

    async def _check():
        client = GitHubBaseClient(build_github_auth(config), config.github_api_version)
        try:
            info = await verify_token(client._client)
            if info.get("mode") == "app":
                console.print(
                    f"  GitHub: [green]✓[/] GitHub App installation "
                    f"(app={config.github_app_id}, "
                    f"installation={config.github_app_installation_id})"
                )
            else:
                console.print(f"  GitHub: [green]✓[/] Authenticated as {info['login']}")
            console.print(f"  Scopes: {info['scopes']}")
        except Exception as e:
            console.print(f"  GitHub: [red]✗[/] {e}")
        finally:
            await client.close()

    asyncio.run(_check())

    # LLM provider check
    if config.llm_provider == "anthropic":
        if config.anthropic_api_key and not config.anthropic_api_key.startswith("sk-ant-xxx"):
            console.print("  LLM: [green]✓[/] Anthropic API key configured")
        else:
            console.print("  LLM: [red]✗[/] Anthropic API key not configured")
    elif config.llm_provider == "github-copilot":
        console.print("  LLM: [green]✓[/] GitHub Copilot (using GITHUB_TOKEN)")
        if config.llm_endpoint:
            console.print(f"  Endpoint: {config.llm_endpoint}")


@cli.command("import-org")
@click.argument("xlsx_path", type=click.Path(exists=True))
def import_org(xlsx_path: str) -> None:
    """Import org structure from an Excel file into the SQLite database.

    XLSX_PATH is the path to the Org structure .xlsx file.
    """
    from .orgdata.loader import OrgDataLoader
    from .orgdata.database import OrgDatabase

    console.print(f"[cyan]Loading Excel file: {xlsx_path}[/]")
    loader = OrgDataLoader(xlsx_path)
    employees = loader.load()
    console.print(f"  Read {len(employees)} employees from Excel")

    db = OrgDatabase()
    dicts = [e.model_dump() for e in employees]
    count = db.import_employees(dicts)
    db.close()

    console.print(f"[green]✓ Imported {count} employees into {db.db_path}[/]")


@cli.command("map-users")
@click.option("--auto", "auto_map", is_flag=True, help="Auto-map by email pattern matching")
@click.option("--set", "manual_map", nargs=2, metavar="EMPLOYEE_ID GITHUB_LOGIN",
              help="Manually map an employee to a GitHub login")
@click.option("--stats", "show_stats", is_flag=True, help="Show mapping statistics")
@click.option("--unmatched", "show_unmatched", is_flag=True, help="Show unmatched GitHub users")
def map_users(auto_map: bool, manual_map: tuple | None, show_stats: bool, show_unmatched: bool) -> None:
    """Map employees to GitHub logins for cross-dimensional analysis."""
    from .orgdata.database import OrgDatabase

    db = OrgDatabase()

    if manual_map:
        employee_id, github_login = manual_map
        db.set_github_id(employee_id, github_login, method="manual")
        console.print(f"[green]✓ Mapped {employee_id} → {github_login}[/]")

    if auto_map:
        # Get all GitHub logins from usage data
        rows = db._conn.execute(
            "SELECT DISTINCT github_login FROM copilot_usage"
        ).fetchall()
        github_users = [r["github_login"] for r in rows]

        if not github_users:
            console.print("[yellow]No Copilot usage data found. Run a query first to populate usage data.[/]")
        else:
            console.print(f"[cyan]Attempting to auto-map {len(github_users)} GitHub users...[/]")
            matches = db.auto_map_by_email(github_users)
            if matches:
                from rich.table import Table
                table = Table(title="Auto-mapped users")
                table.add_column("Employee ID")
                table.add_column("GitHub Login")
                table.add_column("Email")
                table.add_column("Method")
                for m in matches:
                    table.add_row(
                        m["employee_id"],
                        m["github_login"],
                        m.get("email", ""),
                        m.get("matched_name", "email"),
                    )
                console.print(table)
            console.print(f"[green]✓ Auto-mapped {len(matches)} users[/]")

    if show_unmatched:
        unmatched = db.unmatched_github_users()
        if unmatched:
            console.print(f"\n[yellow]Unmatched GitHub users ({len(unmatched)}):[/]")
            for login in unmatched:
                console.print(f"  • {login}")
        else:
            console.print("[green]All GitHub users are matched![/]")

    if show_stats or not (auto_map or manual_map or show_unmatched):
        stats = db.mapping_stats()
        console.print(Panel(
            f"[bold]Employees:[/] {stats['total_employees']} total, "
            f"{stats['employees_with_github_id']} with GitHub ID\n"
            f"[bold]Copilot users:[/] {stats['total_copilot_users']} total, "
            f"{stats['matched_copilot_users']} matched ({stats['match_rate']}%)\n"
            f"[bold]Unmatched:[/] {stats['unmatched_copilot_users']} GitHub users, "
            f"{stats['employees_without_github_id']} employees\n"
            f"[bold]By method:[/] {stats['mappings_by_method'] or 'none yet'}",
            title="Mapping Statistics",
            border_style="cyan",
        ))

    db.close()


@cli.group()
def cache() -> None:
    """Manage the local cache."""


@cache.command("clear")
def cache_clear() -> None:
    """Clear all cached data."""
    from .config import load_config
    from .cache.store import CacheStore

    config = load_config()
    store = CacheStore(ttl_hours=config.cache_ttl_hours)
    count = store.clear()
    store.close()
    console.print(f"[green]Cache cleared: {count} entries removed[/]")


@cache.command("stats")
def cache_stats() -> None:
    """Show cache statistics."""
    from .config import load_config
    from .cache.store import CacheStore

    config = load_config()
    store = CacheStore(ttl_hours=config.cache_ttl_hours)
    stats = store.stats()
    store.close()

    console.print(f"  Valid entries: {stats['valid_entries']}")
    console.print(f"  Expired entries: {stats['expired_entries']}")
    console.print(f"  DB size: {stats['db_size_bytes'] / 1024:.1f} KB")
    console.print(f"  TTL: {stats['ttl_hours']}h")


if __name__ == "__main__":
    cli()
