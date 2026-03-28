from __future__ import annotations

from typing import Any, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


# -- Tables -------------------------------------------------------------------

def print_table(
    title: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    caption: str | None = None,
) -> None:
    table = Table(title=title, caption=caption, show_lines=False)
    for col in columns:
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(*(str(v) for v in row))
    console.print(table)


def print_kv(title: str, data: dict[str, Any]) -> None:
    """Print a key-value panel (e.g. model details, db stats)."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(k, str(v))
    console.print(Panel(table, title=title, border_style="blue"))


# -- Status messages ----------------------------------------------------------

def success(msg: str) -> None:
    console.print(f"[bold green]OK[/]  {msg}")


def info(msg: str) -> None:
    console.print(f"[bold blue]--[/]  {msg}")


def warn(msg: str) -> None:
    error_console.print(f"[bold yellow]WARN[/]  {msg}")


def error(msg: str) -> None:
    error_console.print(f"[bold red]ERROR[/]  {msg}")


# -- Progress -----------------------------------------------------------------

def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def spinner(description: str = "Working...") -> Progress:
    """A simple indeterminate spinner for operations without a known total."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )
