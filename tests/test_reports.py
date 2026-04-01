"""Tests for the reports layer (rendering, charts, export)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from rich.console import Console

from src.reports.chart_engine import ChartEngine
from src.reports.export_engine import ExportEngine
from src.reports.terminal_renderer import TerminalRenderer


class TestTerminalRenderer:
    """Test Rich terminal rendering."""

    def test_render_kpi_cards(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        renderer = TerminalRenderer(console)
        # Should not raise
        renderer.render_kpi_cards({
            "Active Users": 142,
            "Acceptance Rate": "32.2%",
            "Total Seats": 200,
        })

    def test_render_metrics_table(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        renderer = TerminalRenderer(console)
        renderer.render_metrics_table(
            title="Test Table",
            headers=["Language", "Rate", "Suggestions"],
            rows=[
                ["Python", 35.0, 18000],
                ["TypeScript", 35.0, 15200],
                ["Go", 25.0, 4800],
            ],
            highlight_col=1,
        )

    def test_render_sparkline(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        renderer = TerminalRenderer(console)
        renderer.render_sparkline("Active Users", [100, 120, 115, 130, 142, 148])

    def test_render_sparkline_empty(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        renderer = TerminalRenderer(console)
        renderer.render_sparkline("Empty", [])

    def test_render_hierarchy(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        renderer = TerminalRenderer(console)
        renderer.render_hierarchy("Enterprise", {
            "org-1": {
                "team-a": {"users": 25, "acceptance_rate": "34%"},
                "team-b": {"users": 18, "acceptance_rate": "29%"},
            },
        })


class TestChartEngine:
    """Test chart generation."""

    def test_render_terminal_bar(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        engine = ChartEngine()
        engine.render_terminal(
            "bar",
            "Test Bar Chart",
            {"labels": ["Python", "TS", "Java"], "values": [35, 30, 25]},
            console,
        )

    def test_render_terminal_pie(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        engine = ChartEngine()
        engine.render_terminal(
            "pie",
            "Feature Distribution",
            {"labels": ["Completions", "Chat", "CLI"], "values": [60, 30, 10]},
            console,
        )

    def test_render_terminal_table(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        engine = ChartEngine()
        engine.render_terminal(
            "table",
            "Users Table",
            {"headers": ["User", "Score"], "rows": [["alice", 100], ["bob", 80]]},
            console,
        )

    def test_render_terminal_empty_data(self) -> None:
        console = Console(file=None, force_terminal=True, width=100)
        engine = ChartEngine()
        engine.render_terminal("bar", "Empty", {"labels": [], "values": []}, console)

    def test_render_png(self) -> None:
        engine = ChartEngine()
        path = engine.render_png(
            "bar",
            "Test PNG",
            {"labels": ["A", "B", "C"], "values": [10, 20, 30]},
        )
        assert path.exists()
        assert path.suffix == ".png"
        # Cleanup
        path.unlink(missing_ok=True)

    def test_render_plotly_html(self) -> None:
        engine = ChartEngine()
        path = engine.render_plotly(
            "line",
            "Test Plotly Line",
            {"labels": ["Day1", "Day2", "Day3"], "values": [10, 15, 12]},
        )
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "plotly" in content.lower()
        # Cleanup
        Path(path).unlink(missing_ok=True)


class TestExportEngine:
    """Test file export."""

    def test_export_csv(self) -> None:
        engine = ExportEngine()
        path = engine.export(
            "csv",
            "Test Report",
            [
                {
                    "title": "Overview",
                    "data": {"Active Users": 142, "Acceptance Rate": "32.2%"},
                },
                {
                    "title": "By Language",
                    "headers": ["Language", "Rate"],
                    "rows": [["Python", "35%"], ["TypeScript", "35%"]],
                },
            ],
            "test_report",
        )
        assert path.exists()
        assert path.suffix == ".csv"
        content = path.read_text()
        assert "Test Report" in content
        assert "Python" in content
        path.unlink(missing_ok=True)

    def test_export_excel(self) -> None:
        engine = ExportEngine()
        path = engine.export(
            "excel",
            "Test Excel Report",
            [
                {
                    "title": "Overview",
                    "data": {"Active Users": 142, "Seats": 200},
                },
                {
                    "title": "Details",
                    "headers": ["User", "Score"],
                    "rows": [["alice", 100], ["bob", 80]],
                },
            ],
            "test_excel_report",
        )
        assert path.exists()
        assert path.suffix == ".xlsx"
        path.unlink(missing_ok=True)

    def test_export_pdf(self) -> None:
        engine = ExportEngine()
        path = engine.export(
            "pdf",
            "Test PDF Report",
            [
                {
                    "title": "Summary",
                    "data": {"Active Users": 142, "Rate": "32%"},
                },
                {
                    "title": "Language Breakdown",
                    "headers": ["Language", "Acceptance Rate", "Suggestions"],
                    "rows": [["Python", "35%", "18000"], ["TS", "35%", "15200"]],
                    "notes": "Data from the last 28 days.",
                },
            ],
            "test_pdf_report",
        )
        assert path.exists()
        assert path.suffix == ".pdf"
        path.unlink(missing_ok=True)

    def test_export_unsupported_format(self) -> None:
        engine = ExportEngine()
        with pytest.raises(ValueError, match="Unsupported format"):
            engine.export("docx", "Test", [], "test")


class TestCacheStore:
    """Test the SQLite cache store."""

    def test_set_and_get(self) -> None:
        from src.cache.store import CacheStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = CacheStore(ttl_hours=1, db_path=db_path)

            cache.set("test_key", {"value": 42})
            result = cache.get("test_key")
            assert result == {"value": 42}
            cache.close()

    def test_cache_miss(self) -> None:
        from src.cache.store import CacheStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = CacheStore(ttl_hours=1, db_path=db_path)

            result = cache.get("nonexistent")
            assert result is None
            cache.close()

    def test_clear(self) -> None:
        from src.cache.store import CacheStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = CacheStore(ttl_hours=1, db_path=db_path)

            cache.set("key1", "val1")
            cache.set("key2", "val2")
            count = cache.clear()
            assert count == 2
            assert cache.get("key1") is None
            cache.close()

    def test_stats(self) -> None:
        from src.cache.store import CacheStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = CacheStore(ttl_hours=1, db_path=db_path)

            cache.set("key1", "val1")
            stats = cache.stats()
            assert stats["total_entries"] == 1
            assert stats["valid_entries"] == 1
            assert stats["ttl_hours"] == 1
            cache.close()
