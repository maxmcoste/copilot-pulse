"""Chart generation engine using Plotly and Matplotlib."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path.home() / ".copilot-pulse" / "charts"


class ChartEngine:
    """Generate charts in multiple formats: terminal ASCII, Plotly HTML, PNG."""

    def __init__(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def render_terminal(
        self,
        chart_type: str,
        title: str,
        data: dict[str, Any],
        console: Console,
    ) -> None:
        """Render a chart as ASCII art in the terminal.

        Args:
            chart_type: Type of chart (bar, line, pie, table, etc.).
            title: Chart title.
            data: Chart data with 'labels' and 'values' keys.
            console: Rich Console for output.
        """
        labels = data.get("labels", [])
        values = data.get("values", [])

        if chart_type == "table":
            self._render_table(title, data, console)
            return

        if not labels or not values:
            console.print(f"[dim]No data to render for: {title}[/]")
            return

        console.print(f"\n[bold]{title}[/]")

        max_val = max(values) if values else 1
        bar_width = 40

        for label, value in zip(labels, values):
            bar_len = int(value / max_val * bar_width) if max_val else 0
            bar = "█" * bar_len

            if chart_type == "pie":
                total = sum(values)
                pct = round(value / total * 100, 1) if total else 0
                console.print(f"  {label:<25} [cyan]{bar}[/] {value} ({pct}%)")
            else:
                console.print(f"  {label:<25} [cyan]{bar}[/] {value}")

        console.print()

    def render_plotly(
        self,
        chart_type: str,
        title: str,
        data: dict[str, Any],
    ) -> str:
        """Render an interactive Plotly chart and save as HTML.

        Args:
            chart_type: Type of chart.
            title: Chart title.
            data: Chart data.

        Returns:
            Path to the saved HTML file.
        """
        import plotly.graph_objects as go

        labels = data.get("labels", [])
        values = data.get("values", [])

        fig = go.Figure()
        fig.update_layout(
            title=title,
            template="plotly_dark",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#161b22",
            font=dict(color="#c9d1d9"),
        )

        match chart_type:
            case "bar":
                fig.add_trace(go.Bar(x=labels, y=values, marker_color="#58a6ff"))
            case "line":
                fig.add_trace(go.Scatter(
                    x=labels, y=values, mode="lines+markers", line=dict(color="#58a6ff")
                ))
            case "pie":
                fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
                fig.update_layout(title=title, template="plotly_dark")
            case "heatmap":
                z = data.get("z", [values])
                fig.add_trace(go.Heatmap(z=z, x=labels, colorscale="Blues"))
            case "stacked_bar":
                series = data.get("series", {})
                for name, vals in series.items():
                    fig.add_trace(go.Bar(name=name, x=labels, y=vals))
                fig.update_layout(barmode="stack")
            case "scatter":
                x_vals = data.get("x", labels)
                y_vals = data.get("y", values)
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="markers"))
            case _:
                fig.add_trace(go.Bar(x=labels, y=values, marker_color="#58a6ff"))

        file_path = OUTPUT_DIR / f"{title.replace(' ', '_').lower()}.html"
        fig.write_html(str(file_path))
        logger.info("Plotly chart saved to %s", file_path)
        return str(file_path)

    def render_png(
        self,
        chart_type: str,
        title: str,
        data: dict[str, Any],
    ) -> Path:
        """Render a chart as PNG using Matplotlib.

        Args:
            chart_type: Type of chart.
            title: Chart title.
            data: Chart data.

        Returns:
            Path to the saved PNG file.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = data.get("labels", [])
        values = data.get("values", [])

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#c9d1d9")
        ax.set_title(title, color="#c9d1d9", fontsize=14)

        match chart_type:
            case "bar":
                ax.bar(labels, values, color="#58a6ff")
                plt.xticks(rotation=45, ha="right")
            case "line":
                ax.plot(labels, values, marker="o", color="#58a6ff")
                plt.xticks(rotation=45, ha="right")
            case "pie":
                ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            case _:
                ax.bar(labels, values, color="#58a6ff")
                plt.xticks(rotation=45, ha="right")

        for spine in ax.spines.values():
            spine.set_color("#30363d")

        file_path = OUTPUT_DIR / f"{title.replace(' ', '_').lower()}.png"
        plt.tight_layout()
        plt.savefig(str(file_path), dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        logger.info("PNG chart saved to %s", file_path)
        return file_path

    def _render_table(self, title: str, data: dict[str, Any], console: Console) -> None:
        """Render data as a Rich table."""
        headers = data.get("headers", [])
        rows = data.get("rows", [])

        table = Table(title=title, show_lines=True)
        for header in headers:
            table.add_column(header, style="cyan")
        for row in rows:
            table.add_row(*[str(v) for v in row])

        console.print(table)
