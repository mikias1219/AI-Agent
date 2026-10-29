"""CLI interface — thin: reads input, calls services, prints results.
Zero business logic here; all orchestration, tool gating, persistence, and model
access happen beneath `bootstrap.AppContainer` services.
"""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from personal_agent.bootstrap import build_app
from personal_agent.config import Settings
from personal_agent.core.errors import AgentError, StorageError
from personal_agent.core.types import TaskStatus

app = typer.Typer(help="Personal AI agent console: chat, tasks, and task states.")

console = Console()
logger = logging.getLogger(__name__)
_tasks = typer.Typer(help="Manage tracked tasks")
app.add_typer(_tasks, name="tasks")

_HELP_TEXT = Panel(
    "Commands:\n"
    "  /exit  quit chat\n"
    "  /new   start a new conversation session\n"
    "\nAnything else is a normal chat message sent to the agent.",
    title="personal-agent",
    border_style="blue",
)


def _cli_approval_notifier(prompt: str, _details) -> str:
    """Interactive approval: map confirm to the ApprovalDecision vocabulary."""
    return "approved" if typer.confirm(prompt, default=False) else "denied"


@app.command()
def chat(
    provider: str | None = typer.Option(None, help="Override provider: fake | ollama."),
) -> None:
    """Interactive chat; every message flows through the same pipeline as the API."""
    settings: Settings | None = None
    if provider:
        if provider not in ("fake", "ollama"):
            typer.secho(
                f"Unknown provider '{provider}'; choose fake or ollama.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=2)
        settings = _settings_with(provider)

    container = build_app(
        settings=settings,
        approval_notifier=_cli_approval_notifier,
    )
    session_id: str | None = None
    console.print(_HELP_TEXT)

    while True:
        try:
            text = console.input("\n[bold cyan]you ▸ [/]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/exit":
            break
        if text == "/new":
            session_id = None
            console.print("[dim]Started a new session.[/]")
            continue

        try:
            session_id, reply = container.chat.turn(session_id=session_id, text=text)
        except AgentError as exc:
            console.print(f"[red]Agent error:[/] {exc}")
            continue

        console.print(Panel(reply, title=f"agent · session {session_id[:8]}", border_style="green"))
        logger.debug("Replied for session %s.", session_id)


def _settings_with(provider: str) -> Settings:
    """Override the provider key while keeping the rest of `.env` intact."""
    base = Settings.from_env({})
    base.provider = provider
    return base


@_tasks.command("add")
def tasks_add(
    title: str = typer.Argument(..., help="Short title for the task."),
    description: str = typer.Option("", "--desc", help="Optional details."),
) -> None:
    """Create a task."""
    task_id = build_app().tasks.create(title=title, description=description)
    console.print(f"[green]Created task[/] {task_id}")


@_tasks.command("list")
def tasks_list(
    status: str | None = typer.Option(
        None, help="Filter: planned | in_progress | blocked | done | cancelled."
    ),
) -> None:
    """List tasks, newest first."""
    status_filter = TaskStatus(status) if status else None
    table = Table(title="Tasks")
    table.add_column("status", style="bold")
    table.add_column("id", style="dim")
    table.add_column("title")
    for task in build_app().tasks.list(status_filter):
        table.add_row(task.status.value, task.id[:8], task.title)
    console.print(table)


@_tasks.command("advance")
def tasks_advance(
    task_id: str = typer.Argument(..., help="Task id (prefix ok if unique)."),
    status: str = typer.Argument(..., help="planned | in_progress | blocked | done | cancelled."),
) -> None:
    """Progress a task via a controlled status transition."""
    container = build_app()
    match = [
        task
        for task in container.tasks.list()
        if task.id.startswith(task_id) or task.id == task_id
    ]
    if len(match) != 1:
        console.print(f"[red]Expected 1 match for '{task_id}', found {len(match)}.[/]")
        raise typer.Exit(code=1)
    try:
        container.tasks.advance(match[0].id, TaskStatus(status))
    except (StorageError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Task {task_id} → {status}[/]")


def main() -> None:
    """Entry point registered in pyproject under `personal-agent`."""
    from personal_agent.core.errors import ConfigurationError

    try:
        app()
    except ConfigurationError as exc:
        typer.secho(f"Configuration error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


if __name__ == "__main__":
    main()
