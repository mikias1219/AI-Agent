"""CLI interface — thin: reads input, calls services, prints results.
Zero business logic here; all orchestration, tool gating, persistence, and model
access happen beneath `app.container.AppContainer` services.
"""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.domain.exceptions import AgentError, StorageError
from personal_agent.domain.models import TaskStatus

app = typer.Typer(
    help="Personal AI agent console: chat, dashboard, telegram, tasks, and task states."
)

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
        task for task in container.tasks.list() if task.id.startswith(task_id) or task.id == task_id
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


@app.command("telegram")
def telegram_bot() -> None:
    """Start the Telegram bot (long polling); Ctrl-C stops it."""
    from personal_agent.presentation.telegram.main import run as run_telegram

    run_telegram()


@app.command("init-dashboard")
def init_dashboard() -> None:
    """Initialize local dashboard signing configuration without displaying secrets."""
    from personal_agent.config.settings import initialize_dashboard_secret

    created = initialize_dashboard_secret()
    typer.echo(
        "Dashboard signing key created in .env."
        if created
        else "Dashboard signing key is already configured."
    )


@app.command("dashboard")
def dashboard(port: int = typer.Option(8000, min=1, max=65535)) -> None:
    """Run the local-only web dashboard at http://127.0.0.1:<port>."""
    import uvicorn

    from personal_agent.presentation.web.app import create_dashboard_app

    dashboard_app = create_dashboard_app()
    typer.echo(f"Dashboard running at http://127.0.0.1:{port} (Ctrl-C to stop)")
    uvicorn.run(
        dashboard_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


@app.command("reset-dashboard-password")
def reset_dashboard_password() -> None:
    """Recover a registered local owner account; invalidates existing dashboard sessions."""
    password = typer.prompt("New dashboard password", hide_input=True, confirmation_prompt=True)
    container = build_app()
    try:
        container.auth.reset_password(password)
    except (StorageError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    container.audit.record("workspace.password_reset", "local-cli", {})
    typer.echo("Password updated. Log in again using your registered email.")


def main() -> None:
    """Entry point registered in pyproject under `personal-agent`."""
    from personal_agent.domain.exceptions import ConfigurationError

    try:
        app()
    except ConfigurationError as exc:
        typer.secho(f"Configuration error: {exc}", fg=typer.colors.RED, err=True)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
