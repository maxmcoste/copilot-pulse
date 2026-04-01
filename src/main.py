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
    asyncio.run(orchestrator.run_interactive())


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

    from .config import load_config
    from .agent.orchestrator import Orchestrator
    from .reports.web_dashboard import create_app

    config = load_config()
    port = port or config.web_port

    app = create_app(config)

    # Initialize orchestrator for the web app
    orchestrator = Orchestrator(config)
    app.state.orchestrator = orchestrator

    console.print(
        Panel(
            f"[bold cyan]Copilot Pulse Dashboard[/]\n\n"
            f"URL: http://localhost:{port}\n"
            f"Enterprise: {config.github_enterprise or 'N/A'}\n"
            f"Organization: {config.github_org or 'N/A'}",
            border_style="cyan",
        )
    )

    uvicorn.run(app, host=host, port=port, log_level=config.log_level.lower())


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
    from .github_client.auth import verify_token

    config = load_config()

    console.print(Panel("[bold]Configuration Status[/]", border_style="cyan"))
    console.print(f"  Enterprise: {config.github_enterprise or '[yellow]not set[/]'}")
    console.print(f"  Organization: {config.github_org or '[yellow]not set[/]'}")
    console.print(f"  API Version: {config.github_api_version}")
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
        client = GitHubBaseClient(config.github_token, config.github_api_version)
        try:
            info = await verify_token(client._client)
            console.print(f"  GitHub: [green]✓[/] Authenticated as {info['login']}")
            console.print(f"  Scopes: {info['scopes']}")
        except Exception as e:
            console.print(f"  GitHub: [red]✗[/] {e}")
        finally:
            await client.close()

    asyncio.run(_check())

    # Anthropic key check
    if config.anthropic_api_key and not config.anthropic_api_key.startswith("sk-ant-xxx"):
        console.print("  Anthropic: [green]✓[/] API key configured")
    else:
        console.print("  Anthropic: [red]✗[/] API key not configured")


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
