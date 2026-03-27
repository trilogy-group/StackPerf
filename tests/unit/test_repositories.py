"""Unit tests for benchmark_core repositories."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from benchmark_core.db.models import (
    Base,
    Experiment,
    HarnessProfile,
    Provider,
    ProviderModel,
    TaskCard,
    Variant,
)
from benchmark_core.db.models import (
    Session as SessionORM,
)
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
)
from benchmark_core.repositories.experiment_repository import SQLExperimentRepository
from benchmark_core.repositories.harness_profile_repository import SQLHarnessProfileRepository
from benchmark_core.repositories.provider_repository import SQLProviderRepository
from benchmark_core.repositories.request_repository import SQLRequestRepository
from benchmark_core.repositories.session_repository import SQLSessionRepository
from benchmark_core.repositories.task_card_repository import SQLTaskCardRepository
from benchmark_core.repositories.variant_repository import SQLVariantRepository


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
def provider_repo(db_session):
    """Create a provider repository."""
    return SQLProviderRepository(db_session)


@pytest.fixture
def variant_repo(db_session):
    """Create a variant repository."""
    return SQLVariantRepository(db_session)


@pytest.fixture
def experiment_repo(db_session):
    """Create an experiment repository."""
    return SQLExperimentRepository(db_session)


@pytest.fixture
def task_card_repo(db_session):
    """Create a task card repository."""
    return SQLTaskCardRepository(db_session)


@pytest.fixture
def harness_profile_repo(db_session):
    """Create a harness profile repository."""
    return SQLHarnessProfileRepository(db_session)


@pytest.fixture
def session_repo(db_session):
    """Create a session repository."""
    return SQLSessionRepository(db_session)


@pytest.fixture
def request_repo(db_session):
    """Create a request repository."""
    return SQLRequestRepository(db_session)


class TestProviderRepository:
    """Tests for SQLProviderRepository."""

    async def test_create_provider(self, provider_repo, db_session):
        """Test creating a provider."""
        provider = Provider(
            name="test-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
        )

        created = await provider_repo.create(provider)
        db_session.commit()

        assert created.id is not None
        assert created.name == "test-provider"

    async def test_create_duplicate_provider(self, provider_repo):
        """Test that duplicate provider names are rejected."""
        provider1 = Provider(
            name="unique-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="URL1",
            api_key_env="KEY1",
        )
        provider2 = Provider(
            name="unique-provider",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="URL2",
            api_key_env="KEY2",
        )

        await provider_repo.create(provider1)

        with pytest.raises(DuplicateIdentifierError):
            await provider_repo.create(provider2)

    async def test_get_provider_by_name(self, provider_repo, db_session):
        """Test retrieving a provider by name."""
        provider = Provider(
            name="named-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
        )
        await provider_repo.create(provider)
        db_session.commit()

        found = await provider_repo.get_by_name("named-provider")
        assert found is not None
        assert found.name == "named-provider"

    async def test_get_provider_by_id(self, provider_repo, db_session):
        """Test retrieving a provider by ID."""
        provider = Provider(
            name="id-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
        )
        created = await provider_repo.create(provider)
        db_session.commit()

        found = await provider_repo.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    async def test_create_provider_with_models(self, provider_repo, db_session):
        """Test creating a provider with associated models."""
        provider = Provider(
            name="multi-model-provider",
            protocol_surface="openai_responses",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
        )
        models = [
            ProviderModel(alias="gpt-4o", upstream_model="gpt-4o"),
            ProviderModel(alias="gpt-4", upstream_model="gpt-4-turbo"),
        ]

        created = await provider_repo.create_with_models(provider, models)
        db_session.commit()

        assert len(created.models) == 2
        assert created.models[0].alias == "gpt-4o"


class TestVariantRepository:
    """Tests for SQLVariantRepository."""

    async def test_create_variant(self, variant_repo, db_session):
        """Test creating a variant."""
        variant = Variant(
            name="test-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
        )

        created = await variant_repo.create(variant)
        db_session.commit()

        assert created.id is not None
        assert created.name == "test-variant"

    async def test_create_duplicate_variant(self, variant_repo):
        """Test that duplicate variant names are rejected."""
        variant1 = Variant(
            name="unique-variant",
            provider="provider1",
            model_alias="model1",
            harness_profile="profile1",
        )
        variant2 = Variant(
            name="unique-variant",
            provider="provider2",
            model_alias="model2",
            harness_profile="profile2",
        )

        await variant_repo.create(variant1)

        with pytest.raises(DuplicateIdentifierError):
            await variant_repo.create(variant2)

    async def test_list_by_provider(self, variant_repo, db_session):
        """Test listing variants by provider."""
        for i in range(3):
            variant = Variant(
                name=f"prov-a-variant-{i}",
                provider="provider-a",
                model_alias=f"model-{i}",
                harness_profile="default",
            )
            await variant_repo.create(variant)

        # Create variant for different provider
        other_variant = Variant(
            name="prov-b-variant",
            provider="provider-b",
            model_alias="model-x",
            harness_profile="default",
        )
        await variant_repo.create(other_variant)
        db_session.commit()

        results = await variant_repo.list_by_provider("provider-a")
        assert len(results) == 3


class TestExperimentRepository:
    """Tests for SQLExperimentRepository."""

    async def test_create_experiment(self, experiment_repo, db_session):
        """Test creating an experiment."""
        experiment = Experiment(
            name="test-experiment",
            description="Test description",
        )

        created = await experiment_repo.create(experiment)
        db_session.commit()

        assert created.id is not None
        assert created.name == "test-experiment"

    async def test_create_experiment_with_variants(self, experiment_repo, db_session):
        """Test creating an experiment with variants."""
        # First create variants
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

        # Create experiment with variants
        experiment = Experiment(
            name="exp-with-variants",
            description="Has variants",
        )
        variant_ids = [v.id for v in variants]

        created = await experiment_repo.create_with_variants(experiment, variant_ids)
        db_session.commit()

        assert len(created.experiment_variants) == 2

    async def test_add_duplicate_variant_to_experiment(self, experiment_repo, db_session):
        """Test that adding duplicate variant to experiment is rejected."""
        # Create variant
        variant = Variant(
            name="single-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
        )
        db_session.add(variant)
        db_session.flush()

        # Create experiment
        experiment = Experiment(name="test-exp")
        db_session.add(experiment)
        db_session.flush()
        db_session.commit()

        # Add variant once
        await experiment_repo.add_variant(experiment.id, variant.id)

        # Try to add same variant again
        with pytest.raises(DuplicateIdentifierError):
            await experiment_repo.add_variant(experiment.id, variant.id)


class TestTaskCardRepository:
    """Tests for SQLTaskCardRepository."""

    async def test_create_task_card(self, task_card_repo, db_session):
        """Test creating a task card."""
        task_card = TaskCard(
            name="test-task",
            goal="Test the system",
            starting_prompt="Start here",
            stop_condition="Stop when done",
        )

        created = await task_card_repo.create(task_card)
        db_session.commit()

        assert created.id is not None
        assert created.name == "test-task"

    async def test_search_by_goal(self, task_card_repo, db_session):
        """Test searching task cards by goal text."""
        task_card = TaskCard(
            name="searchable-task",
            goal="This is a very specific search goal",
            starting_prompt="Start",
            stop_condition="Stop",
        )
        await task_card_repo.create(task_card)
        db_session.commit()

        results = await task_card_repo.search_by_goal("specific search")
        assert len(results) == 1
        assert results[0].name == "searchable-task"


class TestHarnessProfileRepository:
    """Tests for SQLHarnessProfileRepository."""

    async def test_create_harness_profile(self, harness_profile_repo, db_session):
        """Test creating a harness profile."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="BASE_URL",
            api_key_env="API_KEY",
            model_env="MODEL",
        )

        created = await harness_profile_repo.create(profile)
        db_session.commit()

        assert created.id is not None
        assert created.name == "test-profile"

    async def test_list_by_protocol(self, harness_profile_repo, db_session):
        """Test listing profiles by protocol surface."""
        for i in range(2):
            profile = HarnessProfile(
                name=f"openai-profile-{i}",
                protocol_surface="openai_responses",
                base_url_env="BASE_URL",
                api_key_env="API_KEY",
                model_env="MODEL",
            )
            await harness_profile_repo.create(profile)

        # Create anthropic profile
        anthropic_profile = HarnessProfile(
            name="anthropic-profile",
            protocol_surface="anthropic_messages",
            base_url_env="BASE_URL",
            api_key_env="API_KEY",
            model_env="MODEL",
        )
        await harness_profile_repo.create(anthropic_profile)
        db_session.commit()

        results = await harness_profile_repo.list_by_protocol("openai_responses")
        assert len(results) == 2


class TestSessionRepository:
    """Tests for SQLSessionRepository."""

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

    async def test_create_session_safe(self, session_repo, db_session, setup_entities):
        """Test safe session creation."""
        experiment, variant, task_card = setup_entities

        session = await session_repo.create_session_safe(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test",
            git_branch="main",
            git_commit="abc1234",
        )
        db_session.commit()

        assert session.id is not None
        assert session.experiment_id == experiment.id
        assert session.status == "active"

    async def test_create_session_duplicate_label(self, session_repo, db_session, setup_entities):
        """Test that duplicate session identifiers are rejected."""
        experiment, variant, task_card = setup_entities

        # Create first session
        await session_repo.create_session_safe(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test1",
            git_branch="main",
            git_commit="abc1234",
            operator_label="unique-session",
        )

        # Try to create second session with same label
        with pytest.raises(DuplicateIdentifierError):
            await session_repo.create_session_safe(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path="/tmp/test2",
                git_branch="main",
                git_commit="def5678",
                operator_label="unique-session",
            )

    async def test_create_session_invalid_experiment(
        self, session_repo, db_session, setup_entities
    ):
        """Test that sessions with invalid experiment references are rejected."""
        _, variant, task_card = setup_entities

        invalid_experiment_id = uuid4()

        with pytest.raises(ReferentialIntegrityError):
            await session_repo.create_session_safe(
                experiment_id=invalid_experiment_id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc1234",
            )

    async def test_finalize_session(self, session_repo, db_session, setup_entities):
        """Test session finalization."""
        experiment, variant, task_card = setup_entities

        # Create and commit session first
        session = SessionORM(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/test",
            git_branch="main",
            git_commit="abc1234",
            status="active",
        )
        db_session.add(session)
        db_session.flush()
        db_session.commit()

        # Now finalize it
        finalized = await session_repo.finalize_session(session.id, status="completed")
        db_session.commit()

        assert finalized is not None
        assert finalized.status == "completed"
        assert finalized.ended_at is not None

    async def test_list_by_experiment(self, session_repo, db_session, setup_entities):
        """Test listing sessions by experiment."""
        experiment, variant, task_card = setup_entities

        # Create multiple sessions
        for i in range(3):
            session = SessionORM(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path=f"/tmp/test{i}",
                git_branch="main",
                git_commit=f"abc{i}234",
                status="active",
            )
            db_session.add(session)

        db_session.commit()

        results = await session_repo.list_by_experiment(experiment.id)
        assert len(results) == 3


class TestProxyCredentialRepository:
    """Tests for ProxyCredentialRepository."""

    @pytest.fixture
    def credential_repo(self, db_session):
        """Create a credential repository."""
        from benchmark_core.db.repositories import ProxyCredentialRepository
        return ProxyCredentialRepository(db_session)

    @pytest.fixture
    async def setup_session_with_credential(self, db_session):
        """Create a session for credential tests."""
        from benchmark_core.db.models import ProxyCredential as ProxyCredentialORM

        # Create experiment
        experiment = Experiment(name="cred-test-exp")
        db_session.add(experiment)
        db_session.flush()

        # Create variant
        variant = Variant(
            name="cred-test-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
        )
        db_session.add(variant)
        db_session.flush()

        # Create task card
        task_card = TaskCard(
            name="cred-test-task",
            goal="Test credentials",
            starting_prompt="Start",
            stop_condition="Stop",
        )
        db_session.add(task_card)
        db_session.flush()

        # Create session
        session = SessionORM(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/cred-test",
            git_branch="main",
            git_commit="cred1234",
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        db_session.commit()

        return session, experiment, variant

    async def test_create_credential(self, credential_repo, db_session, setup_session_with_credential):
        """Test creating a credential metadata record."""
        from datetime import datetime, timedelta, UTC
        from pydantic import SecretStr
        from benchmark_core.models import ProxyCredential

        session, experiment, variant = setup_session_with_credential

        credential = ProxyCredential(
            session_id=session.id,
            key_alias=f"session-{str(session.id)[:8]}-{str(experiment.id)[:8]}-{str(variant.id)[:8]}",
            api_key=SecretStr("sk-test-secret-key"),
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            harness_profile="default",
            litellm_key_id="litellm-key-123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )

        created = await credential_repo.create(credential)
        db_session.commit()

        assert created.credential_id is not None
        assert created.key_alias.startswith("session-")
        # Verify secret is cleared for safety
        assert created.api_key.get_secret_value() == "[NOT_STORED_IN_DB]"

    async def test_get_by_session(self, credential_repo, db_session, setup_session_with_credential):
        """Test retrieving credential by session ID."""
        from datetime import datetime, timedelta, UTC
        from pydantic import SecretStr
        from benchmark_core.models import ProxyCredential

        session, experiment, variant = setup_session_with_credential

        # Create credential first
        credential = ProxyCredential(
            session_id=session.id,
            key_alias="test-alias-get-by-session",
            api_key=SecretStr("sk-test"),
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            harness_profile="default",
            litellm_key_id="litellm-456",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        await credential_repo.create(credential)
        db_session.commit()

        # Retrieve by session
        found = await credential_repo.get_by_session(session.id)

        assert found is not None
        assert found.session_id == session.id
        assert found.key_alias == "test-alias-get-by-session"

    async def test_get_by_alias(self, credential_repo, db_session, setup_session_with_credential):
        """Test retrieving credential by key alias."""
        from datetime import datetime, timedelta, UTC
        from pydantic import SecretStr
        from benchmark_core.models import ProxyCredential

        session, experiment, variant = setup_session_with_credential

        # Create credential with unique alias
        credential = ProxyCredential(
            session_id=session.id,
            key_alias="unique-test-alias-12345",
            api_key=SecretStr("sk-test"),
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            harness_profile="default",
            litellm_key_id="litellm-789",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        await credential_repo.create(credential)
        db_session.commit()

        # Retrieve by alias
        found = await credential_repo.get_by_alias("unique-test-alias-12345")

        assert found is not None
        assert found.key_alias == "unique-test-alias-12345"
        assert found.litellm_key_id == "litellm-789"

    async def test_revoke_credential(self, credential_repo, db_session, setup_session_with_credential):
        """Test revoking a credential."""
        from datetime import datetime, timedelta, UTC
        from pydantic import SecretStr
        from benchmark_core.models import ProxyCredential

        session, experiment, variant = setup_session_with_credential

        # Create active credential
        credential = ProxyCredential(
            session_id=session.id,
            key_alias="revoke-test-alias",
            api_key=SecretStr("sk-test"),
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            harness_profile="default",
            litellm_key_id="litellm-revoke",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )
        await credential_repo.create(credential)
        db_session.commit()

        # Revoke it
        revoked = await credential_repo.revoke(session.id)
        db_session.commit()

        assert revoked is not None
        assert revoked.is_active is False
        assert revoked.revoked_at is not None

    async def test_get_nonexistent_credential(self, credential_repo):
        """Test retrieving a credential that doesn't exist."""
        from uuid import uuid4

        result = await credential_repo.get_by_session(uuid4())
        assert result is None

        result = await credential_repo.get_by_alias("nonexistent-alias")
        assert result is None
