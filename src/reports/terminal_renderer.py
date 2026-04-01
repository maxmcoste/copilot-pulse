"""Rich terminal rendering utilities for Copilot metrics."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree


class TerminalRenderer:
    """Renders Copilot metrics data as rich terminal output.

    Args:
        console: Rich Console instance.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render_kpi_cards(self, metrics: dict[str, Any]) -> None:
        """Display KPI summary cards.

        Args:
            metrics: Dict with KPI values.
        """
        cards = []
        for label, value in metrics.items():
            style = "green" if isinstance(value, (int, float)) and value > 0 else "yellow"
            cards.append(f"[bold {style}]{value}[/]\n[dim]{label}[/]")

        row = " │ ".join(cards)
        self.console.print(Panel(row, title="KPI Summary", border_style="cyan"))

    def render_metrics_table(
        self,
        title: str,
        headers: list[str],
        rows: list[list[Any]],
        highlight_col: int | None = None,
    ) -> None:
        """Render a data table with optional column highlighting.

        Args:
            title: Table title.
            headers: Column headers.
            rows: Row data.
            highlight_col: Column index to highlight with conditional colors.
        """
        table = Table(title=title, show_lines=True)
        for i, header in enumerate(headers):
            style = "bold cyan" if i == highlight_col else "cyan"
            table.add_column(header, style=style)

        for row in rows:
            str_row = []
            for i, val in enumerate(row):
                if i == highlight_col and isinstance(val, (int, float)):
                    color = "green" if val >= 30 else "yellow" if val >= 20 else "red"
                    str_row.append(f"[{color}]{val}[/]")
                else:
                    str_row.append(str(val))
            table.add_row(*str_row)

        self.console.print(table)

    def render_hierarchy(self, title: str, data: dict[str, Any]) -> None:
        """Render a hierarchical tree view.

        Args:
            title: Root label.
            data: Nested dict to render as tree.
        """
        tree = Tree(f"[bold cyan]{title}[/]")
        self._add_tree_nodes(tree, data)
        self.console.print(tree)

    def _add_tree_nodes(self, parent: Tree, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                branch = parent.add(f"[bold]{key}[/]")
                self._add_tree_nodes(branch, value)
            else:
                parent.add(f"{key}: [green]{value}[/]")

    def render_sparkline(self, label: str, values: list[int | float]) -> None:
        """Render an inline sparkline.

        Args:
            label: Label for the sparkline.
            values: Numeric values to plot.
        """
        if not values:
            return

        blocks = " ▁▂▃▄▅▆▇█"
        min_val = min(values)
        max_val = max(values)
        span = max_val - min_val or 1

        spark = ""
        for v in values:
            idx = int((v - min_val) / span * (len(blocks) - 1))
            spark += blocks[idx]

        self.console.print(f"  {label}: [cyan]{spark}[/]  ({min_val}–{max_val})")
