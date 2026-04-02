"""Session lifecycle commands."""

import asyncio
from uuid import UUID

import typer
from rich.console import Console
from rich.syntax import Syntax
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.config import HarnessProfile as HarnessProfileConfig
from benchmark_core.config import Variant as VariantConfig
from benchmark_core.db.models import (
    Experiment as DBExperiment,
)
from benchmark_core.db.models import HarnessProfile as DBHarnessProfile
from benchmark_core.db.models import (
    Session as DBSession,
)
from benchmark_core.db.models import (
    TaskCard as DBTaskCard,
)
from benchmark_core.db.models import (
    Variant as DBVariant,
)
from benchmark_core.db.session import get_db_session
from benchmark_core.git import get_git_metadata
from benchmark_core.models import SessionOutcomeState
from benchmark_core.repositories.session_repository import SQLSessionRepository
from benchmark_core.services.rendering import EnvRenderingService
from benchmark_core.services.session_service import SessionService

app = typer.Typer(help="Manage benchmark sessions")
console = Console()

# CLI choice values for outcome states
OUTCOME_CHOICES = [state.value for state in SessionOutcomeState]


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


def _check_active_session_exists(
    db: SQLAlchemySession, experiment_id: UUID, variant_id: UUID
) -> bool:
    """Check if there's an active session for the given experiment and variant."""
    existing = (
        db.query(DBSession)
        .filter_by(
            experiment_id=experiment_id,
            variant_id=variant_id,
            status="active",
        )
        .first()
    )
    return existing is not None


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
    notes: str | None = typer.Option(None, "--notes", "-n", help="Initial session notes"),
    repo_path: str | None = typer.Option(
        None, "--repo", "-r", help="Repository path (default: current directory)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompts (use with caution)",
    ),
) -> None:
    """Create a new benchmark session with git metadata capture and optional notes.

    This command creates a benchmark session and captures git metadata from the
    active repository. It will warn if there are uncommitted changes and will
    prompt for confirmation if an active session already exists for this
    experiment and variant combination.
    """
    console.print("[bold blue]Creating benchmark session...[/bold blue]")
    console.print()

    # Capture git metadata from active repository
    git_metadata = get_git_metadata(repo_path)
    if git_metadata is None:
        console.print("[yellow]Warning: Not in a git repository or git not available[/yellow]")
        git_metadata = None
    else:
        console.print(f"  Git branch: {git_metadata.branch}")
        console.print(f"  Git commit: {git_metadata.commit[:8]}")
        if git_metadata.dirty:
            console.print("[yellow]  Working directory has uncommitted changes[/yellow]")

    console.print()

    # Create session in database
    with get_db_session() as db:
        try:
            # Resolve IDs
            exp_id = _resolve_experiment_id(db, experiment)
            var_id = _resolve_variant_id(db, variant)
            task_id = _resolve_task_card_id(db, task_card)

            # Get experiment and variant details for display
            exp_record = db.query(DBExperiment).filter_by(id=exp_id).first()
            var_record = db.query(DBVariant).filter_by(id=var_id).first()
            task_record = db.query(DBTaskCard).filter_by(id=task_id).first()

            # Display selected configuration
            console.print("[bold]Configuration Summary:[/bold]")
            console.print(f"  Experiment: {exp_record.name if exp_record else experiment}")
            console.print(f"  Variant: {var_record.name if var_record else variant}")
            if var_record and var_record.model_alias:
                console.print(f"  Model: {var_record.model_alias}")
            if var_record and var_record.provider:
                console.print(f"  Provider: {var_record.provider}")
            console.print(f"  Task Card: {task_record.name if task_record else task_card}")
            console.print(f"  Harness Profile: {harness_profile}")
            if label:
                console.print(f"  Operator Label: {label}")
            console.print()

            # Check for existing active session
            if _check_active_session_exists(db, exp_id, var_id):
                console.print(
                    "[yellow]Warning: An active session already exists for this experiment and variant.[/yellow]"
                )
                console.print("Creating a new session may affect benchmark comparisons.")
                console.print()

                if not force:
                    confirmed = typer.confirm("Do you want to proceed with creating a new session?")
                    if not confirmed:
                        console.print("[yellow]Session creation cancelled.[/yellow]")
                        raise typer.Exit(0)
                    console.print()

            # Create repository and service
            repository = SQLSessionRepository(db)
            service = SessionService(repository)

            # Create session with git metadata and notes
            session = asyncio.run(
                service.create_session(
                    experiment_id=exp_id,
                    variant_id=var_id,
                    task_card_id=task_id,
                    harness_profile=harness_profile,
                    repo_path=git_metadata.repo_path if git_metadata else (repo_path or "."),
                    git_branch=git_metadata.branch if git_metadata else "unknown",
                    git_commit=git_metadata.commit if git_metadata else "unknown",
                    git_dirty=git_metadata.dirty if git_metadata else False,
                    operator_label=label,
                    notes=notes,
                )
            )

            console.print(f"[green]Session created successfully: {session.session_id}[/green]")
            console.print(f"  Status: {session.status}")
            if notes:
                console.print(f"  Notes: {notes[:50]}...")
            console.print()
            console.print("Next steps:")
            console.print(
                f"  1. Run [bold]benchmark session env {session.session_id}[/bold] to get environment variables"
            )
            console.print("  2. Launch your harness with the provided environment")
            console.print(
                f"  3. Run [bold]benchmark session finalize {session.session_id}[/bold] when done"
            )

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
        "completed",
        "--status",
        "-s",
        help="Final status (completed, failed, cancelled)",
    ),
    outcome: str | None = typer.Option(
        None,
        "--outcome",
        "-o",
        help="Outcome state (valid, invalid, aborted). If not specified, defaults to 'valid' for completed status.",
        case_sensitive=False,
    ),
) -> None:
    """Finalize a benchmark session with status and optional outcome state.

    Status values:
    - completed: Session finished normally (default)
    - failed: Session encountered errors
    - cancelled: Session was manually cancelled

    Outcome states (optional):
    - valid: Session data is valid for comparisons (default for completed status)
    - invalid: Session completed but data should be excluded from comparisons
    - aborted: Session was terminated before completion
    """
    # Validate status
    valid_statuses = ["completed", "failed", "cancelled"]
    if status not in valid_statuses:
        console.print(f"[red]Invalid status: {status}[/red]")
        console.print(f"Valid options: {', '.join(valid_statuses)}")
        raise typer.Exit(1)

    # Validate outcome if provided
    if outcome is not None and outcome not in OUTCOME_CHOICES:
        console.print(f"[red]Invalid outcome state: {outcome}[/red]")
        console.print(f"Valid options: {', '.join(OUTCOME_CHOICES)}")
        raise typer.Exit(1)

    # Default outcome to 'valid' if not specified for completed status
    if outcome is None:
        outcome = "valid"

    console.print(f"[bold blue]Finalizing session {session_id}...[/bold blue]")
    console.print(f"  Status: {status}")
    console.print(f"  Outcome: {outcome}")

    with get_db_session() as db:
        try:
            # Resolve session ID
            try:
                sess_uuid = UUID(session_id)
            except ValueError as err:
                raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

            # Create repository and service
            repository = SQLSessionRepository(db)
            service = SessionService(repository)

            # Get current session
            session = asyncio.run(service.get_session(sess_uuid))
            if session is None:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)

            # Finalize with status, outcome state, and end time
            from benchmark_core.models import SessionOutcomeState

            outcome_enum = SessionOutcomeState(outcome)
            updated = asyncio.run(
                service.finalize_session(
                    sess_uuid,
                    status=status,
                    outcome_state=outcome_enum,
                )
            )
            if updated is None:
                console.print(f"[red]Failed to finalize session: {session_id}[/red]")
                raise typer.Exit(1)

            console.print("[green]Session finalized successfully[/green]")
            console.print(f"  Status: {updated.status}")
            console.print(f"  Outcome: {updated.outcome_state}")
            console.print(f"  Ended at: {updated.ended_at}")

        except typer.BadParameter:
            raise
        except ValueError as e:
            console.print(f"[red]Invalid value: {e}[/red]")
            raise typer.Exit(1) from e
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
            db_session = db.query(DBSession).filter_by(id=sess_uuid).first()
            if db_session is None:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)

            profile_row = (
                db.query(DBHarnessProfile).filter_by(name=db_session.harness_profile).first()
            )
            if profile_row is None:
                console.print(
                    f"[red]Harness profile not found for session: {db_session.harness_profile}[/red]"
                )
                raise typer.Exit(1)

            variant_row = db.query(DBVariant).filter_by(id=db_session.variant_id).first()
            if variant_row is None:
                console.print(f"[red]Variant not found for session: {db_session.variant_id}[/red]")
                raise typer.Exit(1)

            profile = HarnessProfileConfig(
                name=profile_row.name,
                protocol_surface=profile_row.protocol_surface,
                base_url_env=profile_row.base_url_env,
                api_key_env=profile_row.api_key_env,
                model_env=profile_row.model_env,
                extra_env=profile_row.extra_env,
                render_format=profile_row.render_format,
                launch_checks=profile_row.launch_checks,
            )
            variant = VariantConfig(
                name=variant_row.name,
                provider=variant_row.provider,
                provider_route=variant_row.provider_route,
                model_alias=variant_row.model_alias,
                harness_profile=variant_row.harness_profile,
                harness_env_overrides=variant_row.harness_env_overrides,
                benchmark_tags=variant_row.benchmark_tags,
            )

            rendering = EnvRenderingService()
            credential = db_session.proxy_credential_alias or f"sk-benchmark-{db_session.id}"
            snippet = rendering.render_env_snippet(
                harness_profile=profile,
                variant=variant,
                credential=credential,
                include_secrets=True,
            )

            console.print(f"[bold blue]Environment for session {session_id}:[/bold blue]")
            console.print(f"# Session: {db_session.id}")
            console.print(f"# Harness Profile: {db_session.harness_profile}")
            console.print(f"# Model Alias: {variant.model_alias}")
            language = {
                "shell": "bash",
                "dotenv": "sh",
                "json": "json",
                "toml": "toml",
            }[snippet.format]
            syntax = Syntax(snippet.content, language, theme="monokai", line_numbers=False)
            console.print(syntax)

        except typer.BadParameter:
            raise
        except Exception as e:
            console.print(f"[red]Error rendering environment: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def add_notes(
    session_id: str,
    notes: str = typer.Option(..., "--notes", "-n", help="Notes to add to session"),
    append: bool = typer.Option(
        False,
        "--append",
        "-a",
        help="Append to existing notes instead of replacing",
    ),
) -> None:
    """Add or update notes for a benchmark session."""
    console.print(f"[bold blue]Updating notes for session {session_id}...[/bold blue]")

    with get_db_session() as db:
        try:
            # Resolve session ID
            try:
                sess_uuid = UUID(session_id)
            except ValueError as err:
                raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

            # Create repository and service
            repository = SQLSessionRepository(db)
            service = SessionService(repository)

            # Get current session
            session = asyncio.run(service.get_session(sess_uuid))
            if session is None:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)

            # Build new notes
            new_notes = f"{session.notes}\n{notes}" if append and session.notes else notes

            # Update notes
            updated = asyncio.run(service.update_session_notes(sess_uuid, new_notes))
            if updated is None:
                console.print(f"[red]Failed to update notes for session: {session_id}[/red]")
                raise typer.Exit(1)

            console.print("[green]Session notes updated successfully[/green]")
            if append:
                console.print("[dim](appended to existing notes)[/dim]")

        except typer.BadParameter:
            raise
        except Exception as e:
            console.print(f"[red]Error updating notes: {e}[/red]")
            raise typer.Exit(1) from e
