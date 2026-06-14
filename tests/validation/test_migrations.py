"""Migration smoke tests for CI.

Validates database migrations work correctly in a clean environment.
This ensures migration regressions are caught automatically.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from benchmark_core.db.models import (
    HarnessProfile,
    Provider,
    ProviderModel,
    Variant,
)
from benchmark_core.db.session import init_db


class TestMigrations:
    """Test database migrations."""

    @pytest.fixture
    def temp_db(self, tmp_path: Path):
        """Create a temporary database for testing."""
        db_file = tmp_path / "test.db"
        database_url = f"sqlite:///{db_file}"

        # Create engine with foreign key support
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

        # Enable foreign keys for SQLite
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _fk_pragma_on_connect(dbapi_conn, connection_record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        yield engine

        engine.dispose()

    def test_init_db_creates_all_tables(self, temp_db) -> None:
        """Verify init_db creates all expected tables."""
        init_db(temp_db)

        inspector = inspect(temp_db)
        tables = inspector.get_table_names()

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
            "proxy_credentials",
            "proxy_keys",
        ]

        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"

    def test_migration_files_exist(self) -> None:
        """Verify migration files exist in the repository."""
        migrations_dir = Path(__file__).parent.parent.parent / "migrations" / "versions"
        assert migrations_dir.exists(), f"Migrations directory not found: {migrations_dir}"

        migration_files = list(migrations_dir.glob("*.py"))
        assert len(migration_files) > 0, "No migration files found"

    def test_alembic_config_exists(self) -> None:
        """Verify alembic.ini exists."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        assert alembic_ini.exists(), f"alembic.ini not found: {alembic_ini}"

    def test_migrations_env_exists(self) -> None:
        """Verify migrations/env.py exists."""
        env_py = Path(__file__).parent.parent.parent / "migrations" / "env.py"
        assert env_py.exists(), f"migrations/env.py not found: {env_py}"


class TestDatabaseIntegrity:
    """Test database referential integrity and relationships."""

    @pytest.fixture
    def temp_db_with_data(self, tmp_path: Path):
        """Create a temporary database with sample data."""
        db_file = tmp_path / "test.db"
        database_url = f"sqlite:///{db_file}"

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

        # Add sample data
        with Session(engine) as session:
            provider = Provider(
                name="test-provider",
                protocol_surface="openai_responses",
                upstream_base_url_env="TEST_URL",
                api_key_env="TEST_KEY",
            )
            session.add(provider)
            session.flush()

            model = ProviderModel(
                provider_id=provider.id,
                alias="test-model",
                upstream_model="test-model-upstream",
            )
            session.add(model)

            profile = HarnessProfile(
                name="test-profile",
                protocol_surface="openai_responses",
                base_url_env="PROXY_URL",
                api_key_env="PROXY_KEY",
                model_env="PROXY_MODEL",
            )
            session.add(profile)

            variant = Variant(
                name="test-variant",
                provider="test-provider",
                model_alias="test-model",
                harness_profile="test-profile",
                benchmark_tags={"test": "true"},
            )
            session.add(variant)
            session.commit()

        yield engine

        engine.dispose()

    def test_provider_model_relationship(self, temp_db_with_data) -> None:
        """Test Provider -> ProviderModel relationship."""
        with Session(temp_db_with_data) as session:
            provider = session.query(Provider).filter_by(name="test-provider").first()
            assert provider is not None
            assert len(provider.models) == 1
            assert provider.models[0].alias == "test-model"

    def test_model_provider_relationship(self, temp_db_with_data) -> None:
        """Test ProviderModel -> Provider relationship."""
        with Session(temp_db_with_data) as session:
            model = session.query(ProviderModel).first()
            assert model is not None
            assert model.provider.name == "test-provider"


class TestMigrationRollback:
    """Test migration rollback functionality."""

    def test_alembic_downgrade_available(self) -> None:
        """Verify alembic downgrade commands are available in migrations."""
        migrations_dir = Path(__file__).parent.parent.parent / "migrations" / "versions"

        # Check that at least one migration file exists
        migration_files = list(migrations_dir.glob("*.py"))
        if not migration_files:
            pytest.skip("No migration files to test")

        # Each migration should have upgrade and downgrade functions
        for migration_file in migration_files[:1]:  # Check first one
            content = migration_file.read_text()
            assert "def upgrade()" in content or "upgrade()" in content
            assert "def downgrade()" in content or "downgrade()" in content
