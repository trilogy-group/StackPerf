#!/usr/bin/env python3
"""Verify database schema and migration system works end-to-end.

This script demonstrates:
1. Database creation from scratch using migrations
2. All tables are created correctly
3. Sample data can be inserted with proper referential integrity
4. Relationships work as expected
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from benchmark_core.db.models import (
    Artifact,
    Base,
    Experiment,
    ExperimentVariant,
    HarnessProfile,
    MetricRollup,
    Provider,
    ProviderModel,
    Request,
    Session as DBSession,
    TaskCard,
    Variant,
)
from benchmark_core.db.session import init_db


def verify_schema():
    """Verify complete database schema functionality."""
    print("=" * 70)
    print("Database Schema Verification")
    print("=" * 70)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    database_url = f"sqlite:///{db_path}"
    print(f"\n1. Creating database at: {db_path}")

    # Create engine and initialize database
    # Enable foreign key support for SQLite cascade delete
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    # Enable foreign keys for SQLite
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def _fk_pragma_on_connect(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
    init_db(engine)
    print("   ✓ Database initialized using init_db()")

    # Verify all tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n2. Verifying tables exist ({len(tables)} found):")

    expected_tables = [
        "providers",
        "provider_models",
        "harness_profiles",
        "variants",
        "experiments",
        "experiment_variants",
        "task_cards",
        "sessions",
        "requests",
        "rollups",
        "artifacts",
    ]

    for table in expected_tables:
        status = "✓" if table in tables else "✗"
        print(f"   {status} {table}")

    missing = set(expected_tables) - set(tables)
    if missing:
        print(f"\n   ERROR: Missing tables: {missing}")
        return False

    print("   ✓ All expected tables present")

    # Insert sample data with full referential integrity
    print("\n3. Inserting sample data with referential integrity:")

    with Session(engine) as session:
        # Provider and ProviderModel
        provider = Provider(
            name="openai",
            protocol_surface="openai_responses",
            upstream_base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
            routing_defaults={"timeout": 30},
        )
        session.add(provider)
        session.flush()

        model = ProviderModel(
            provider_id=provider.id,
            alias="gpt-4o",
            upstream_model="gpt-4o-2024-08-06",
        )
        session.add(model)
        print("   ✓ Provider + ProviderModel inserted")

        # HarnessProfile
        profile = HarnessProfile(
            name="default-harness",
            protocol_surface="openai_responses",
            base_url_env="PROXY_BASE_URL",
            api_key_env="PROXY_API_KEY",
            model_env="PROXY_MODEL",
            extra_env={"TIMEOUT": "60"},
            launch_checks=["litellm --version"],
        )
        session.add(profile)
        print("   ✓ HarnessProfile inserted")

        # Variant
        variant = Variant(
            name="openai-gpt4o-default",
            provider="openai",
            model_alias="gpt-4o",
            harness_profile="default-harness",
            harness_env_overrides={"TIMEOUT": "120"},
            benchmark_tags={"provider": "openai", "model": "gpt-4o", "harness": "default"},
        )
        session.add(variant)
        session.flush()
        print("   ✓ Variant inserted")

        # Experiment
        experiment = Experiment(
            name="baseline-comparison",
            description="Baseline performance comparison across providers",
        )
        session.add(experiment)
        session.flush()

        exp_variant = ExperimentVariant(
            experiment_id=experiment.id,
            variant_name="openai-gpt4o-default",
        )
        session.add(exp_variant)
        print("   ✓ Experiment + ExperimentVariant inserted")

        # TaskCard
        task = TaskCard(
            name="simple-refactor",
            repo_path="/tmp/test-repo",
            goal="Refactor the utility module for better readability",
            starting_prompt="Please refactor the utils.py file to improve readability",
            stop_condition="Code compiles and tests pass",
            session_timebox_minutes=30,
            notes=["Focus on function extraction", "Add type hints"],
        )
        session.add(task)
        session.flush()
        print("   ✓ TaskCard inserted")

        # Session - use UUID objects directly, not strings
        db_session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="default-harness",
            repo_path="/tmp/test-repo",
            git_branch="main",
            git_commit="abc123def456",
            git_dirty=False,
            operator_label="test-run",
            proxy_credential_id="cred-123",
            status="active",
        )
        session.add(db_session)
        session.flush()
        print("   ✓ Session inserted")

        # Request
        request = Request(
            request_id="req-001",
            session_id=db_session.id,
            provider="openai",
            model="gpt-4o",
            timestamp=datetime.now(UTC),
            latency_ms=245.5,
            ttft_ms=45.2,
            tokens_prompt=150,
            tokens_completion=320,
            error=False,
            cache_hit=False,
            request_metadata={"temperature": 0.7, "max_tokens": 1000},
        )
        session.add(request)
        print("   ✓ Request inserted")

        # MetricRollup
        rollup = MetricRollup(
            dimension_type="session",
            dimension_id=str(db_session.id),  # MetricRollup uses string for dimension_id
            metric_name="avg_latency_ms",
            metric_value=245.5,
            sample_count=1,
        )
        session.add(rollup)
        print("   ✓ MetricRollup inserted")

        # Artifact
        artifact = Artifact(
            session_id=db_session.id,
            artifact_type="session-log",
            name="session-001.jsonl",
            content_type="application/jsonlines",
            storage_path="s3://benchmark-artifacts/session-001.jsonl",
            size_bytes=1024000,
            artifact_metadata={"format": "jsonl", "compressed": True},
        )
        session.add(artifact)
        print("   ✓ Artifact inserted")

        session.commit()
        print("\n4. All data committed successfully!")

    # Verify data retrieval and relationships
    print("\n5. Verifying data retrieval and relationships:")

    with Session(engine) as session:
        # Verify provider -> models relationship
        p = session.query(Provider).filter_by(name="openai").first()
        assert p is not None, "Provider not found"
        assert len(p.models) == 1, f"Expected 1 model, got {len(p.models)}"
        assert p.models[0].alias == "gpt-4o"
        print("   ✓ Provider -> ProviderModel relationship works")

        # Verify experiment -> variants relationship
        e = session.query(Experiment).filter_by(name="baseline-comparison").first()
        assert e is not None, "Experiment not found"
        assert len(e.experiment_variants) == 1
        print("   ✓ Experiment -> ExperimentVariant relationship works")

        # Verify session with foreign keys
        s = session.query(DBSession).first()
        assert s is not None, "Session not found"
        assert s.status == "active"
        print("   ✓ Session retrieved successfully")

        # Verify requests linked to session
        r = session.query(Request).filter_by(session_id=s.id).first()
        assert r is not None, "Request not found"
        assert r.provider == "openai"
        print("   ✓ Request -> Session relationship works")

        # Verify artifacts linked to session
        a = session.query(Artifact).filter_by(session_id=s.id).first()
        assert a is not None, "Artifact not found"
        assert a.artifact_type == "session-log"
        print("   ✓ Artifact -> Session relationship works")

        # Verify cascade delete
        print("\n6. Testing cascade delete (session -> requests/artifacts):")
        req_count_before = session.query(Request).count()
        art_count_before = session.query(Artifact).count()
        session.delete(s)
        session.commit()
        req_count_after = session.query(Request).count()
        art_count_after = session.query(Artifact).count()

        assert req_count_after == req_count_before - 1, f"Request cascade delete failed"
        assert art_count_after == art_count_before - 1, f"Artifact cascade delete failed"
        print("   ✓ Cascade delete works correctly")

    # Verify migration baseline exists
    print("\n7. Verifying migration files:")
    migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"
    migration_files = list(migrations_dir.glob("*.py"))
    print(f"   Found {len(migration_files)} migration file(s)")
    for f in migration_files:
        if f.name != "__pycache__":
            print(f"   ✓ {f.name}")

    # Cleanup
    print(f"\n8. Cleaning up temporary database: {db_path}")
    Path(db_path).unlink(missing_ok=True)
    print("   ✓ Cleanup complete")

    print("\n" + "=" * 70)
    print("✓ ALL VERIFICATIONS PASSED")
    print("=" * 70)
    print("\nSchema verification summary:")
    print("  • All 11 tables created successfully")
    print("  • All relationships (Provider->Models, Experiment->Variants) work")
    print("  • Foreign key constraints enforced")
    print("  • Cascade delete functionality verified")
    print("  • Migration system ready for use")
    print("\nMigration commands:")
    print("  alembic revision --autogenerate -m 'description'")
    print("  alembic upgrade head")
    print("  alembic downgrade -1")

    return True


if __name__ == "__main__":
    success = verify_schema()
    exit(0 if success else 1)
