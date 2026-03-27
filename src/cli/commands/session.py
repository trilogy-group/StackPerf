"""Session lifecycle commands."""

from uuid import UUID

import typer
from rich.console import Console
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Experiment as DBExperiment,
)
from benchmark_core.db.models import (
    TaskCard as DBTaskCard,
)
from benchmark_core.db.models import (
    Variant as DBVariant,
)
from benchmark_core.db.repositories import SQLAlchemySessionRepository
from benchmark_core.db.session import get_db_session
from benchmark_core.git import get_git_metadata
from benchmark_core.services.session_service import SessionService

app = typer.Typer(help="Manage benchmark sessions")
console = Console()


def _get_db_session() -> SQLAlchemySession:
    """Get a database session for CLI commands."""
    # This is a generator, we need to use it in a context
    from benchmark_core.db.session import get_db

    return next(get_db())


def _resolve_experiment_id(db: SQLAlchemySession, experiment: str) -> UUID:
    """Resolve experiment identifier to UUID."""
    # Try as UUID first
    try:
        return UUID(experiment)
    except ValueError:
        pass

    # Try as name
    exp = db.query(DBExperiment).filter_by(name=experiment).first()
    if exp is None:
        raise typer.BadParameter(f"Experiment not found: {experiment}")
    return exp.id


def _resolve_variant_id(db: SQLAlchemySession, variant: str) -> UUID:
    """Resolve variant identifier to UUID."""
    # Try as UUID first
    try:
        return UUID(variant)
    except ValueError:
        pass

    # Try as name
    var = db.query(DBVariant).filter_by(name=variant).first()
    if var is None:
        raise typer.BadParameter(f"Variant not found: {variant}")
    return var.id


def _resolve_task_card_id(db: SQLAlchemySession, task_card: str) -> UUID:
    """Resolve task card identifier to UUID."""
    # Try as UUID first
    try:
        return UUID(task_card)
    except ValueError:
        pass

    # Try as name
    task = db.query(DBTaskCard).filter_by(name=task_card).first()
    if task is None:
        raise typer.BadParameter(f"Task card not found: {task_card}")
    return task.id


@app.command()
def create(
    experiment: str = typer.Option(..., "--experiment", "-e", help="Experiment ID or name"),
    variant: str = typer.Option(..., "--variant", "-v", help="Variant ID or name"),
    task_card: str = typer.Option(..., "--task-card", "-t", help="Task card ID or name"),
    harness_profile: str = typer.Option(
        ...,
        "--harness",
        "-H",
        help="Harness profile name",
    ),
    label: str | None = typer.Option(None, "--label", "-l", help="Operator label"),
    repo_path: str | None = typer.Option(
        None, "--repo", "-r", help="Repository path (default: current directory)"
    ),
) -> None:
    """Create a new benchmark session with git metadata capture."""
    console.print("[bold blue]Creating benchmark session...[/bold blue]")

    # Capture git metadata from active repository
    git_metadata = get_git_metadata(repo_path)
    if git_metadata is None:
        console.print("[yellow]Warning: Not in a git repository or git not available[/yellow]")
        git_metadata = None
    else:
        console.print(f"  Git branch: {git_metadata.branch}")
        console.print(f"  Git commit: {git_metadata.commit[:8]}")
        if git_metadata.dirty:
            console.print("[yellow]  Working directory is dirty[/yellow]")

    # Create session in database
    with get_db_session() as db:
        try:
            # Resolve IDs
            exp_id = _resolve_experiment_id(db, experiment)
            var_id = _resolve_variant_id(db, variant)
            task_id = _resolve_task_card_id(db, task_card)

            # Create repository and service
            repository = SQLAlchemySessionRepository(db)
            service = SessionService(repository)

            # Create session with git metadata
            import asyncio

            session = asyncio.run(
                service.create_session(
                    experiment_id=str(exp_id),
                    variant_id=str(var_id),
                    task_card_id=str(task_id),
                    harness_profile=harness_profile,
                    repo_path=git_metadata.repo_path if git_metadata else (repo_path or "."),
                    git_branch=git_metadata.branch if git_metadata else "unknown",
                    git_commit=git_metadata.commit if git_metadata else "unknown",
                    git_dirty=git_metadata.dirty if git_metadata else False,
                    operator_label=label,
                )
            )

            console.print(f"[green]Session created successfully: {session.session_id}[/green]")
            console.print(f"  Experiment: {experiment} ({exp_id})")
            console.print(f"  Variant: {variant} ({var_id})")
            console.print(f"  Task Card: {task_card} ({task_id})")
            console.print(f"  Harness: {harness_profile}")
            console.print(f"  Status: {session.status}")

        except typer.BadParameter:
            raise
        except Exception as e:
            console.print(f"[red]Error creating session: {e}[/red]")
            raise typer.Exit(1) from e


@app.command("list")
def list_sessions(
    experiment: str | None = typer.Option(
        None, "--experiment", "-e", help="Filter by experiment ID or name"
    ),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """List benchmark sessions."""
    with get_db_session() as db:
        try:
            from benchmark_core.db.models import Session as DBSession

            query = db.query(DBSession)

            # Apply filters
            if experiment:
                try:
                    exp_uuid = UUID(experiment)
                    query = query.filter_by(experiment_id=exp_uuid)
                except ValueError:
                    # Try as name
                    exp = db.query(DBExperiment).filter_by(name=experiment).first()
                    if exp:
                        query = query.filter_by(experiment_id=exp.id)
                    else:
                        console.print(
                            f"[yellow]Warning: Experiment not found: {experiment}[/yellow]"
                        )

            if status:
                query = query.filter_by(status=status)

            sessions = query.all()

            if not sessions:
                console.print("[yellow]No sessions found[/yellow]")
                return

            console.print(f"[bold blue]Sessions ({len(sessions)}):[/bold blue]")
            for sess in sessions:
                status_color = (
                    "green"
                    if sess.status == "active"
                    else "yellow"
                    if sess.status == "completed"
                    else "red"
                )
                console.print(
                    f"  [{status_color}]{sess.id}[/{status_color}] - {sess.status} - {sess.harness_profile}"
                )
                console.print(f"    Started: {sess.started_at}")
                if sess.ended_at:
                    console.print(f"    Ended: {sess.ended_at}")

        except Exception as e:
            console.print(f"[red]Error listing sessions: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def show(session_id: str) -> None:
    """Show session details."""
    with get_db_session() as db:
        try:
            # Resolve session ID
            try:
                sess_uuid = UUID(session_id)
            except ValueError as err:
                raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

            # Get session from database
            from benchmark_core.db.models import Session as DBSession

            db_session = db.query(DBSession).filter_by(id=sess_uuid).first()
            if db_session is None:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)

            # Display session details
            console.print(f"[bold]Session:[/bold] {db_session.id}")
            console.print(f"  Experiment ID: {db_session.experiment_id}")
            console.print(f"  Variant ID: {db_session.variant_id}")
            console.print(f"  Task Card ID: {db_session.task_card_id}")
            console.print(f"  Harness Profile: {db_session.harness_profile}")
            console.print(f"  Status: {db_session.status}")
            console.print(f"  Started: {db_session.started_at}")
            if db_session.ended_at:
                console.print(f"  Ended: {db_session.ended_at}")
            console.print(f"  Git Branch: {db_session.git_branch}")
            console.print(f"  Git Commit: {db_session.git_commit[:8]}")
            console.print(f"  Git Dirty: {db_session.git_dirty}")
            console.print(f"  Repo Path: {db_session.repo_path}")
            if db_session.operator_label:
                console.print(f"  Operator Label: {db_session.operator_label}")

        except typer.BadParameter:
            raise
        except Exception as e:
            console.print(f"[red]Error showing session: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def finalize(
    session_id: str = typer.Argument(..., help="Session ID to finalize"),
    status: str = typer.Option(
        "completed", "--status", "-s", help="Final status (completed, failed, cancelled)"
    ),
) -> None:
    """Finalize a benchmark session with status and end time."""
    console.print(f"[bold blue]Finalizing session {session_id}...[/bold blue]")

    with get_db_session() as db:
        try:
            # Resolve session ID
            try:
                sess_uuid = UUID(session_id)
            except ValueError as err:
                raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

            # Create repository and service
            repository = SQLAlchemySessionRepository(db)
            service = SessionService(repository)

            # Finalize session
            import asyncio
            from datetime import UTC, datetime

            # Get current session
            session = asyncio.run(service.get_session(sess_uuid))
            if session is None:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)

            # Finalize with status and end time
            ended_at = datetime.now(UTC)
            updated = asyncio.run(
                service.finalize_session(
                    sess_uuid,
                    status=status,
                    ended_at=ended_at,
                )
            )
            if updated is None:
                console.print(f"[red]Failed to finalize session: {session_id}[/red]")
                raise typer.Exit(1)

            console.print("[green]Session finalized successfully[/green]")
            console.print(f"  Status: {updated.status}")
            console.print(f"  Ended at: {updated.ended_at}")

        except typer.BadParameter:
            raise
        except Exception as e:
            console.print(f"[red]Error finalizing session: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def env(session_id: str) -> None:
    """Render harness environment snippet for a session."""
    with get_db_session() as db:
        try:
            # Resolve session ID
            try:
                sess_uuid = UUID(session_id)
            except ValueError as err:
                raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

            # Get session from database
            from benchmark_core.db.models import Session as DBSession

            db_session = db.query(DBSession).filter_by(id=sess_uuid).first()
            if db_session is None:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)

            console.print(f"[bold blue]Environment for session {session_id}:[/bold blue]")
            console.print(f"# Session: {db_session.id}")
            console.print(f"# Harness Profile: {db_session.harness_profile}")
            console.print("export OPENAI_API_BASE=http://localhost:4000")
            console.print(f"export OPENAI_API_KEY=sk-benchmark-{db_session.id}")

        except typer.BadParameter:
            raise
        except Exception as e:
            console.print(f"[red]Error rendering environment: {e}[/red]")
            raise typer.Exit(1) from e
