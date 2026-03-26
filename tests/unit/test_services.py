"""Unit tests for benchmark_core services."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from benchmark_core.db.models import (
    Base,
    Experiment,
    HarnessProfile,
    Provider,
    TaskCard,
    Variant,
)
from benchmark_core.services.benchmark_metadata_service import BenchmarkMetadataService
from benchmark_core.services.credential_service import CredentialService
from benchmark_core.services.experiment_service import (
    ExperimentService,
)
from benchmark_core.services.harness_profile_service import (
    HarnessProfileService,
    HarnessProfileServiceError,
)
from benchmark_core.services.provider_service import ProviderService, ProviderServiceError
from benchmark_core.services.session_service import SessionService, SessionValidationError
from benchmark_core.services.task_card_service import TaskCardService
from benchmark_core.services.variant_service import VariantService, VariantServiceError


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    yield session
    session.close()


@pytest.fixture
def provider_service(db_session):
    """Create a provider service."""
    return ProviderService(db_session)


@pytest.fixture
def variant_service(db_session):
    """Create a variant service."""
    return VariantService(db_session)


@pytest.fixture
def experiment_service(db_session):
    """Create an experiment service."""
    return ExperimentService(db_session)


@pytest.fixture
def task_card_service(db_session):
    """Create a task card service."""
    return TaskCardService(db_session)


@pytest.fixture
def harness_profile_service(db_session):
    """Create a harness profile service."""
    return HarnessProfileService(db_session)


@pytest.fixture
def session_service(db_session):
    """Create a session service."""
    return SessionService(db_session)


@pytest.fixture
def credential_service():
    """Create a credential service."""
    return CredentialService()


@pytest.fixture
def metadata_service(db_session):
    """Create a benchmark metadata service."""
    return BenchmarkMetadataService(db_session)


class TestProviderService:
    """Tests for ProviderService."""

    async def test_create_provider(self, provider_service, db_session):
        """Test creating a provider."""
        provider = await provider_service.create_provider(
            name="test-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
            models=[
                {"alias": "gpt-4o", "upstream_model": "gpt-4o"},
                {"alias": "gpt-4", "upstream_model": "gpt-4-turbo"},
            ],
        )
        db_session.commit()

        assert provider.id is not None
        assert provider.name == "test-provider"
        assert len(provider.models) == 2

    async def test_create_provider_invalid_protocol(self, provider_service):
        """Test that invalid protocol surface is rejected."""
        with pytest.raises(ProviderServiceError) as exc_info:
            await provider_service.create_provider(
                name="bad-provider",
                protocol_surface="invalid_protocol",
                upstream_base_url_env="TEST_URL",
                api_key_env="TEST_KEY",
            )
        assert "Invalid protocol_surface" in str(exc_info.value)

    async def test_create_duplicate_provider(self, provider_service, db_session):
        """Test that duplicate provider names are rejected."""
        await provider_service.create_provider(
            name="unique-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="URL1",
            api_key_env="KEY1",
        )

        with pytest.raises(ProviderServiceError) as exc_info:
            await provider_service.create_provider(
                name="unique-provider",
                protocol_surface="anthropic_messages",
                upstream_base_url_env="URL2",
                api_key_env="KEY2",
            )
        assert "already exists" in str(exc_info.value)

    async def test_get_model_upstream(self, provider_service, db_session):
        """Test retrieving upstream model for an alias."""
        await provider_service.create_provider(
            name="model-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
            models=[{"alias": "gpt-4o", "upstream_model": "gpt-4o-2024-08-06"}],
        )
        db_session.commit()

        upstream = await provider_service.get_model_upstream("model-provider", "gpt-4o")
        assert upstream == "gpt-4o-2024-08-06"


class TestHarnessProfileService:
    """Tests for HarnessProfileService."""

    async def test_create_harness_profile(self, harness_profile_service, db_session):
        """Test creating a harness profile."""
        profile = await harness_profile_service.create_harness_profile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="BASE_URL",
            api_key_env="API_KEY",
            model_env="MODEL",
        )
        db_session.commit()

        assert profile.id is not None
        assert profile.name == "test-profile"

    async def test_create_profile_invalid_protocol(self, harness_profile_service):
        """Test that invalid protocol surface is rejected."""
        with pytest.raises(HarnessProfileServiceError) as exc_info:
            await harness_profile_service.create_harness_profile(
                name="bad-profile",
                protocol_surface="invalid",
                base_url_env="BASE_URL",
                api_key_env="API_KEY",
                model_env="MODEL",
            )
        assert "Invalid protocol_surface" in str(exc_info.value)

    async def test_create_profile_invalid_format(self, harness_profile_service):
        """Test that invalid render format is rejected."""
        with pytest.raises(HarnessProfileServiceError) as exc_info:
            await harness_profile_service.create_harness_profile(
                name="bad-profile",
                protocol_surface="openai_responses",
                base_url_env="BASE_URL",
                api_key_env="API_KEY",
                model_env="MODEL",
                render_format="yaml",
            )
        assert "Invalid render_format" in str(exc_info.value)

    async def test_render_env_snippet(self, harness_profile_service, db_session):
        """Test rendering environment snippet."""
        profile = await harness_profile_service.create_harness_profile(
            name="render-profile",
            protocol_surface="openai_responses",
            base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
            extra_env={"EXTRA_VAR": "extra_value"},
        )
        db_session.commit()

        env = await harness_profile_service.render_env_snippet(
            profile_id=profile.id,
            credential="sk-test",
            proxy_base_url="http://localhost:4000",
            model="gpt-4o",
        )

        assert env["OPENAI_BASE_URL"] == "http://localhost:4000"
        assert env["OPENAI_API_KEY"] == "sk-test"
        assert env["OPENAI_MODEL"] == "gpt-4o"
        assert env["EXTRA_VAR"] == "extra_value"


class TestVariantService:
    """Tests for VariantService."""

    async def test_create_variant(self, variant_service, db_session):
        """Test creating a variant."""
        variant = await variant_service.create_variant(
            name="test-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
            benchmark_tags={"harness": "test", "priority": "high"},
        )
        db_session.commit()

        assert variant.id is not None
        assert variant.name == "test-variant"
        assert variant.benchmark_tags == {"harness": "test", "priority": "high"}

    async def test_create_variant_validation(self, variant_service):
        """Test that required fields are validated."""
        with pytest.raises(VariantServiceError) as exc_info:
            await variant_service.create_variant(
                name="",
                provider="test-provider",
                model_alias="gpt-4o",
                harness_profile="default",
            )
        assert "name is required" in str(exc_info.value)

    async def test_update_variant_tags(self, variant_service, db_session):
        """Test updating variant tags."""
        variant = await variant_service.create_variant(
            name="tag-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
            benchmark_tags={"initial": "tag"},
        )
        db_session.commit()

        updated = await variant_service.update_variant_tags(variant.id, {"new": "tags", "count": 2})
        db_session.commit()

        assert updated.benchmark_tags == {"new": "tags", "count": 2}


class TestTaskCardService:
    """Tests for TaskCardService."""

    async def test_create_task_card(self, task_card_service, db_session):
        """Test creating a task card."""
        task_card = await task_card_service.create_task_card(
            name="test-task",
            goal="Test the benchmark system",
            starting_prompt="Run the test",
            stop_condition="Test completes",
            session_timebox_minutes=30,
            notes=["Note 1", "Note 2"],
        )
        db_session.commit()

        assert task_card.id is not None
        assert task_card.name == "test-task"
        assert task_card.session_timebox_minutes == 30
        assert task_card.notes == ["Note 1", "Note 2"]

    async def test_add_note_to_task_card(self, task_card_service, db_session):
        """Test adding a note to a task card."""
        task_card = await task_card_service.create_task_card(
            name="note-task",
            goal="Test notes",
            starting_prompt="Start",
            stop_condition="Stop",
            notes=["Initial note"],
        )
        db_session.commit()

        updated = await task_card_service.add_note_to_task_card(task_card.id, "Added note")
        db_session.commit()

        assert len(updated.notes) == 2
        assert "Added note" in updated.notes


class TestExperimentService:
    """Tests for ExperimentService."""

    async def test_create_experiment(self, experiment_service, db_session):
        """Test creating an experiment."""
        experiment = await experiment_service.create_experiment(
            name="test-experiment",
            description="A test experiment",
        )
        db_session.commit()

        assert experiment.id is not None
        assert experiment.name == "test-experiment"
        assert experiment.description == "A test experiment"

    async def test_create_experiment_with_variants(self, experiment_service, db_session):
        """Test creating an experiment with variants."""
        # Create variants first
        variants = []
        for i in range(2):
            variant = Variant(
                name=f"exp-variant-{i}",
                provider="test-provider",
                model_alias="gpt-4o",
                harness_profile="default",
            )
            db_session.add(variant)
            db_session.flush()
            variants.append(variant)

        db_session.commit()

        experiment = await experiment_service.create_experiment(
            name="exp-with-variants",
            description="Has variants",
            variant_ids=[v.id for v in variants],
        )
        db_session.commit()

        # Check variant associations
        variant_ids = await experiment_service.get_experiment_variant_ids(experiment.id)
        assert len(variant_ids) == 2

    async def test_validate_experiment_has_variants(self, experiment_service, db_session):
        """Test validation of experiment with variants."""
        # Create experiment without variants
        experiment = await experiment_service.create_experiment(
            name="empty-experiment",
            description="No variants",
        )
        db_session.commit()

        # Should not validate
        assert not await experiment_service.validate_experiment_has_variants(experiment.id)


class TestSessionService:
    """Tests for SessionService."""

    @pytest.fixture
    async def setup_entities(self, db_session):
        """Create prerequisite entities for session tests."""
        # Create experiment
        experiment = Experiment(name="session-test-exp")
        db_session.add(experiment)
        db_session.flush()

        # Create variant
        variant = Variant(
            name="session-test-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
        )
        db_session.add(variant)
        db_session.flush()

        # Create task card
        task_card = TaskCard(
            name="session-test-task",
            goal="Test session",
            starting_prompt="Start",
            stop_condition="Stop",
        )
        db_session.add(task_card)
        db_session.flush()

        db_session.commit()

        return experiment, variant, task_card

    async def test_create_session(self, session_service, db_session, setup_entities):
        """Test creating a session safely."""
        experiment, variant, task_card = setup_entities

        session = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test",
            git_branch="main",
            git_commit="abc1234",
            operator_label="test-session-1",
        )
        db_session.commit()

        assert session.id is not None
        assert session.status == "active"
        assert session.operator_label == "test-session-1"

    async def test_create_session_validation(self, session_service, setup_entities):
        """Test that session creation validates required fields."""
        experiment, variant, task_card = setup_entities

        with pytest.raises(SessionValidationError) as exc_info:
            await session_service.create_session(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc1234",
            )
        assert "harness_profile is required" in str(exc_info.value)

    async def test_create_session_invalid_git_commit(self, session_service, setup_entities):
        """Test that invalid git commit format is rejected."""
        experiment, variant, task_card = setup_entities

        with pytest.raises(SessionValidationError) as exc_info:
            await session_service.create_session(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc",  # Too short
            )
        assert "git_commit must be between" in str(exc_info.value)

    async def test_create_session_duplicate_label(
        self, session_service, db_session, setup_entities
    ):
        """Test that duplicate session identifiers are rejected."""
        experiment, variant, task_card = setup_entities

        # Create first session
        await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test1",
            git_branch="main",
            git_commit="abc1234",
            operator_label="duplicate-label",
        )
        db_session.commit()

        # Try to create second session with same label
        with pytest.raises(SessionValidationError) as exc_info:
            await session_service.create_session(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path="/tmp/test2",
                git_branch="main",
                git_commit="def5678",
                operator_label="duplicate-label",
            )
        assert "Duplicate session identifier" in str(exc_info.value)

    async def test_finalize_session(self, session_service, db_session, setup_entities):
        """Test finalizing a session."""
        experiment, variant, task_card = setup_entities

        session = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test",
            git_branch="main",
            git_commit="abc1234",
        )
        db_session.commit()

        finalized = await session_service.finalize_session(session.id)
        db_session.commit()

        assert finalized is not None
        assert finalized.status == "completed"
        assert finalized.ended_at is not None

    async def test_finalize_already_finalized_session(
        self, session_service, db_session, setup_entities
    ):
        """Test that finalizing an already-finalized session is rejected."""
        experiment, variant, task_card = setup_entities

        session = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test",
            git_branch="main",
            git_commit="abc1234",
        )
        db_session.commit()

        # Finalize once
        await session_service.finalize_session(session.id)
        db_session.commit()

        # Try to finalize again
        with pytest.raises(SessionValidationError) as exc_info:
            await session_service.finalize_session(session.id)
        assert "already finalized" in str(exc_info.value)

    async def test_get_session_summary(self, session_service, db_session, setup_entities):
        """Test getting session summary."""
        experiment, variant, task_card = setup_entities

        session = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test",
            git_branch="main",
            git_commit="abc1234",
            operator_label="summary-test",
        )
        db_session.commit()

        summary = await session_service.get_session_summary(session.id)

        assert summary is not None
        assert summary["status"] == "active"
        assert summary["operator_label"] == "summary-test"
        assert summary["git_branch"] == "main"


class TestCredentialService:
    """Tests for CredentialService."""

    async def test_issue_credential(self, credential_service):
        """Test issuing a credential."""
        session_id = uuid4()
        credential = await credential_service.issue_credential(
            session_id=session_id,
            experiment_id="test-experiment",
            variant_id="test-variant",
            harness_profile="default",
        )

        assert credential.startswith("sk-benchmark-")
        assert str(session_id) in credential

    def test_render_env_snippet(self, credential_service):
        """Test rendering environment snippet."""
        env = credential_service.render_env_snippet(
            credential="sk-test",
            proxy_base_url="http://localhost:4000",
            model="gpt-4o",
            harness_profile="default",
        )

        assert env["OPENAI_API_BASE"] == "http://localhost:4000"
        assert env["OPENAI_API_KEY"] == "sk-test"
        assert env["OPENAI_MODEL"] == "gpt-4o"

    def test_render_shell_snippet(self, credential_service):
        """Test rendering shell snippet."""
        snippet = credential_service.render_shell_snippet(
            credential="sk-test",
            proxy_base_url="http://localhost:4000",
            model="gpt-4o",
        )

        assert 'export OPENAI_API_BASE="http://localhost:4000"' in snippet
        assert 'export OPENAI_API_KEY="sk-test"' in snippet

    def test_render_dotenv_snippet(self, credential_service):
        """Test rendering dotenv snippet."""
        snippet = credential_service.render_dotenv_snippet(
            credential="sk-test",
            proxy_base_url="http://localhost:4000",
            model="gpt-4o",
        )

        assert 'OPENAI_API_BASE="http://localhost:4000"' in snippet
        assert 'OPENAI_API_KEY="sk-test"' in snippet


class TestBenchmarkMetadataService:
    """Tests for BenchmarkMetadataService."""

    @pytest.fixture
    async def setup_full_config(self, db_session):
        """Create a full benchmark configuration."""
        # Create provider
        provider = Provider(
            name="full-config-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
        )
        db_session.add(provider)
        db_session.flush()

        # Create harness profile
        harness = HarnessProfile(
            name="full-config-harness",
            protocol_surface="openai_responses",
            base_url_env="BASE_URL",
            api_key_env="API_KEY",
            model_env="MODEL",
        )
        db_session.add(harness)
        db_session.flush()

        # Create variant
        variant = Variant(
            name="full-config-variant",
            provider="full-config-provider",
            model_alias="gpt-4o",
            harness_profile="full-config-harness",
        )
        db_session.add(variant)
        db_session.flush()

        # Create task card
        task_card = TaskCard(
            name="full-config-task",
            goal="Test full config",
            starting_prompt="Start",
            stop_condition="Stop",
        )
        db_session.add(task_card)
        db_session.flush()

        # Create experiment
        experiment = Experiment(
            name="full-config-experiment",
            description="Full configuration test",
        )
        db_session.add(experiment)
        db_session.flush()

        # Link variant to experiment
        from benchmark_core.db.models import ExperimentVariant

        link = ExperimentVariant(
            experiment_id=experiment.id,
            variant_id=variant.id,
        )
        db_session.add(link)
        db_session.commit()

        return provider, harness, variant, task_card, experiment

    async def test_create_complete_setup(self, metadata_service, db_session):
        """Test creating a complete benchmark setup."""
        # Create provider with models
        provider = await metadata_service.create_provider_with_models(
            name="complete-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="URL",
            api_key_env="KEY",
            models=[
                {"alias": "gpt-4o", "upstream_model": "gpt-4o"},
                {"alias": "gpt-4", "upstream_model": "gpt-4-turbo"},
            ],
        )

        # Create harness profile
        harness = await metadata_service.create_harness_profile(
            name="complete-harness",
            protocol_surface="openai_responses",
            base_url_env="BASE",
            api_key_env="KEY",
            model_env="MODEL",
        )

        # Create variant
        variant = await metadata_service.create_variant(
            name="complete-variant",
            provider="complete-provider",
            model_alias="gpt-4o",
            harness_profile="complete-harness",
        )

        # Create task card
        task_card = await metadata_service.create_task_card(
            name="complete-task",
            goal="Complete test",
            starting_prompt="Start",
            stop_condition="Stop",
        )

        # Create experiment with variant
        experiment = await metadata_service.create_experiment(
            name="complete-experiment",
            description="Complete setup",
            variant_ids=[variant.id],
        )

        db_session.commit()

        assert provider.id is not None
        assert harness.id is not None
        assert variant.id is not None
        assert task_card.id is not None
        assert experiment.id is not None

    async def test_validate_benchmark_configuration(
        self, metadata_service, setup_full_config, db_session
    ):
        """Test validating a complete benchmark configuration."""
        _, _, variant, task_card, experiment = setup_full_config

        result = await metadata_service.validate_benchmark_configuration(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_benchmark_configuration_invalid_experiment(
        self, metadata_service, setup_full_config
    ):
        """Test validation with invalid experiment."""
        _, _, variant, task_card, _ = setup_full_config

        result = await metadata_service.validate_benchmark_configuration(
            experiment_id=uuid4(),  # Invalid
            variant_id=variant.id,
            task_card_id=task_card.id,
        )

        assert result["valid"] is False
        assert any("Experiment" in err for err in result["errors"])

    async def test_get_benchmark_summary(self, metadata_service, setup_full_config, db_session):
        """Test getting benchmark summary."""
        _, _, _, _, experiment = setup_full_config

        summary = await metadata_service.get_benchmark_summary(experiment.id)

        assert summary is not None
        assert summary["name"] == "full-config-experiment"
        assert summary["variant_count"] == 1

    async def test_list_all_configurations(self, metadata_service, setup_full_config):
        """Test listing all configurations."""
        all_configs = await metadata_service.list_all_configurations()

        assert "providers" in all_configs
        assert "harness_profiles" in all_configs
        assert "variants" in all_configs
        assert "experiments" in all_configs
        assert "task_cards" in all_configs

        # Should find our setup entities
        assert len(all_configs["providers"]) >= 1
        assert len(all_configs["experiments"]) >= 1
