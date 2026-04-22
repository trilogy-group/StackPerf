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
from benchmark_core.repositories.artifact_repository import SQLArtifactRepository
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
from benchmark_core.repositories.usage_request_repository import SQLUsageRequestRepository
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

    async def test_create_credential(
        self, credential_repo, db_session, setup_session_with_credential
    ):
        """Test creating a credential metadata record."""
        from datetime import UTC, datetime, timedelta

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
        from datetime import UTC, datetime, timedelta

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
        from datetime import UTC, datetime, timedelta

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

    async def test_revoke_credential(
        self, credential_repo, db_session, setup_session_with_credential
    ):
        """Test revoking a credential."""
        from datetime import UTC, datetime, timedelta

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


class TestProxyKeyRepository:
    """Tests for SQLProxyKeyRepository."""

    @pytest.fixture
    def proxy_key_repo(self, db_session):
        """Create a proxy key repository."""
        from benchmark_core.repositories.proxy_key_repository import SQLProxyKeyRepository

        return SQLProxyKeyRepository(db_session)

    async def test_create_proxy_key(self, proxy_key_repo, db_session):
        """Test creating a proxy key registry entry."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="test-key-001",
            litellm_key_id="litellm-key-001",
            owner="dev-team",
            team="platform",
            customer="internal",
            purpose="benchmark sessions",
            allowed_models=["gpt-4o", "gpt-4"],
            budget_duration="monthly",
            budget_amount=100.0,
            budget_currency="USD",
            status="active",
        )

        created = await proxy_key_repo.create(proxy_key)
        db_session.commit()

        assert created.id is not None
        assert created.key_alias == "test-key-001"
        assert created.litellm_key_id == "litellm-key-001"
        assert created.owner == "dev-team"
        assert created.team == "platform"
        assert created.customer == "internal"
        assert created.status == "active"
        assert created.budget_currency == "USD"
        # Ensure no secret column exists
        assert not hasattr(created, "api_key")
        assert not hasattr(created, "secret")

    async def test_get_by_alias(self, proxy_key_repo, db_session):
        """Test retrieving a proxy key by alias."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="alias-lookup-key",
            litellm_key_id="litellm-lookup-123",
            owner="qa-team",
            status="active",
        )
        await proxy_key_repo.create(proxy_key)
        db_session.commit()

        found = await proxy_key_repo.get_by_alias("alias-lookup-key")
        assert found is not None
        assert found.key_alias == "alias-lookup-key"
        assert found.litellm_key_id == "litellm-lookup-123"

    async def test_get_by_litellm_key_id(self, proxy_key_repo, db_session):
        """Test retrieving a proxy key by LiteLLM key ID."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="litellm-lookup-key",
            litellm_key_id="sk-litellm-abc-789",
            owner="ops-team",
            status="active",
        )
        await proxy_key_repo.create(proxy_key)
        db_session.commit()

        found = await proxy_key_repo.get_by_litellm_key_id("sk-litellm-abc-789")
        assert found is not None
        assert found.litellm_key_id == "sk-litellm-abc-789"
        assert found.key_alias == "litellm-lookup-key"

    async def test_list_by_owner(self, proxy_key_repo, db_session):
        """Test listing proxy keys by owner."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        for i in range(3):
            proxy_key = ProxyKeyORM(
                key_alias=f"owner-key-{i}",
                litellm_key_id=f"litellm-owner-{i}",
                owner="shared-owner",
                team=f"team-{i}",
                status="active",
            )
            await proxy_key_repo.create(proxy_key)

        # Different owner
        other = ProxyKeyORM(
            key_alias="other-owner-key",
            litellm_key_id="litellm-other",
            owner="different-owner",
            status="active",
        )
        await proxy_key_repo.create(other)
        db_session.commit()

        results = await proxy_key_repo.list_by_owner("shared-owner")
        assert len(results) == 3
        for r in results:
            assert r.owner == "shared-owner"

    async def test_list_by_team(self, proxy_key_repo, db_session):
        """Test listing proxy keys by team."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        for i in range(2):
            proxy_key = ProxyKeyORM(
                key_alias=f"team-key-{i}",
                litellm_key_id=f"litellm-team-{i}",
                team="ml-platform",
                status="active",
            )
            await proxy_key_repo.create(proxy_key)
        db_session.commit()

        results = await proxy_key_repo.list_by_team("ml-platform")
        assert len(results) == 2

    async def test_list_by_customer(self, proxy_key_repo, db_session):
        """Test listing proxy keys by customer."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="customer-key",
            litellm_key_id="litellm-customer-1",
            customer="acme-corp",
            status="active",
        )
        await proxy_key_repo.create(proxy_key)
        db_session.commit()

        results = await proxy_key_repo.list_by_customer("acme-corp")
        assert len(results) == 1
        assert results[0].customer == "acme-corp"

    async def test_list_active(self, proxy_key_repo, db_session):
        """Test listing only active proxy keys."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        active = ProxyKeyORM(
            key_alias="active-key",
            litellm_key_id="litellm-active",
            status="active",
        )
        revoked = ProxyKeyORM(
            key_alias="revoked-key",
            litellm_key_id="litellm-revoked",
            status="revoked",
        )
        await proxy_key_repo.create(active)
        await proxy_key_repo.create(revoked)
        db_session.commit()

        results = await proxy_key_repo.list_active()
        aliases = {r.key_alias for r in results}
        assert "active-key" in aliases
        assert "revoked-key" not in aliases

    async def test_revoke_proxy_key(self, proxy_key_repo, db_session):
        """Test revoking a proxy key."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="revocable-key",
            litellm_key_id="litellm-revoke-me",
            status="active",
        )
        created = await proxy_key_repo.create(proxy_key)
        db_session.commit()

        revoked = await proxy_key_repo.revoke(created.id)
        db_session.commit()

        assert revoked is not None
        assert revoked.status == "revoked"
        assert revoked.revoked_at is not None

    async def test_revoke_idempotent(self, proxy_key_repo, db_session):
        """Test that revoking an already-revoked key is a no-op."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="idempotent-revoke-key",
            litellm_key_id="litellm-idempotent",
            status="active",
        )
        created = await proxy_key_repo.create(proxy_key)
        db_session.commit()

        await proxy_key_repo.revoke(created.id)
        db_session.commit()

        # Re-read from DB to get the same tz-naive representation used by second_revoke
        refreshed = await proxy_key_repo.get_by_id(created.id)
        first_timestamp = refreshed.revoked_at

        second_revoke = await proxy_key_repo.revoke(created.id)
        db_session.commit()

        assert second_revoke is not None
        assert second_revoke.status == "revoked"
        assert second_revoke.revoked_at is not None
        # Verify the revoked_at timestamp was preserved (not overwritten)
        assert second_revoke.revoked_at == first_timestamp

    async def test_list_by_proxy_credential_id(self, proxy_key_repo, db_session):
        """Test listing proxy keys by proxy credential ID."""
        from uuid import UUID

        from benchmark_core.db.models import (
            Experiment,
            ProxyCredential,
            TaskCard,
            Variant,
        )
        from benchmark_core.db.models import (
            ProxyKey as ProxyKeyORM,
        )
        from benchmark_core.db.models import (
            Session as SessionORM,
        )

        # Build minimum required chain to create a ProxyCredential
        experiment = Experiment(name="proxy-key-test-exp")
        db_session.add(experiment)
        db_session.flush()

        variant = Variant(
            name="proxy-key-test-variant",
            provider="litellm",
            model_alias="gpt-4",
            harness_profile="default",
        )
        db_session.add(variant)
        db_session.flush()

        task_card = TaskCard(
            name="proxy-key-test-task",
            goal="Test proxy key link",
            starting_prompt="Start",
            stop_condition="Stop",
        )
        db_session.add(task_card)
        db_session.flush()

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

        credential = ProxyCredential(
            session_id=session.id,
            key_alias="cred-for-proxy-keys",
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            harness_profile="default",
        )
        db_session.add(credential)
        db_session.flush()

        proxy_key = ProxyKeyORM(
            key_alias="linked-key-1",
            litellm_key_id="litellm-linked-1",
            status="active",
            proxy_credential_id=credential.id,
        )
        created = await proxy_key_repo.create(proxy_key)
        db_session.commit()

        results = await proxy_key_repo.list_by_proxy_credential_id(credential.id)
        assert len(results) == 1
        assert results[0].id == created.id

        other_results = await proxy_key_repo.list_by_proxy_credential_id(
            UUID("00000000-0000-0000-0000-000000000001"), limit=5, offset=0
        )
        assert other_results == []

    async def test_get_nonexistent_proxy_key(self, proxy_key_repo):
        """Test retrieving proxy keys that don't exist."""
        from uuid import uuid4

        result = await proxy_key_repo.get_by_id(uuid4())
        assert result is None

        result = await proxy_key_repo.get_by_alias("nonexistent-alias")
        assert result is None

        result = await proxy_key_repo.get_by_litellm_key_id("nonexistent-litellm-id")
        assert result is None

    async def test_create_duplicate_alias(self, proxy_key_repo):
        """Test that duplicate key aliases are rejected."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        key1 = ProxyKeyORM(key_alias="unique-alias", status="active")
        key2 = ProxyKeyORM(key_alias="unique-alias", status="active")

        await proxy_key_repo.create(key1)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await proxy_key_repo.create(key2)


class TestSQLArtifactRepository:
    """Tests for SQLArtifactRepository."""

    @pytest.fixture
    def artifact_repo(self, db_session):
        """Create an artifact repository."""
        return SQLArtifactRepository(db_session)

    @pytest.fixture
    def setup_experiment_and_session(self, db_session):
        """Create experiment, variant, task, and session for artifact tests."""
        experiment = Experiment(name="artifact-test-exp", description="Test")
        variant = Variant(
            name="artifact-test-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = TaskCard(
            name="artifact-test-task",
            goal="Test",
            starting_prompt="Test",
            stop_condition="Test",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session = SessionORM(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="default",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc1234",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        return experiment, session

    @pytest.mark.asyncio
    async def test_create_artifact_with_session(
        self, db_session, artifact_repo, setup_experiment_and_session
    ):
        """Test creating an artifact linked to a session."""
        experiment, session = setup_experiment_and_session

        from benchmark_core.db.models import Artifact as ArtifactORM

        artifact = ArtifactORM(
            name="test_export.json",
            artifact_type="export",
            content_type="application/json",
            storage_path="/storage/test_export.json",
            session_id=session.id,
            size_bytes=1024,
        )

        created = await artifact_repo.create(artifact)
        assert created.id is not None
        assert created.name == "test_export.json"
        assert created.session_id == session.id
        assert created.experiment_id is None

    @pytest.mark.asyncio
    async def test_create_artifact_with_experiment(
        self, db_session, artifact_repo, setup_experiment_and_session
    ):
        """Test creating an artifact linked to an experiment."""
        experiment, _ = setup_experiment_and_session

        from benchmark_core.db.models import Artifact as ArtifactORM

        artifact = ArtifactORM(
            name="report.html",
            artifact_type="report",
            content_type="text/html",
            storage_path="/storage/report.html",
            experiment_id=experiment.id,
            size_bytes=5120,
        )

        created = await artifact_repo.create(artifact)
        assert created.experiment_id == experiment.id
        assert created.session_id is None

    @pytest.mark.asyncio
    async def test_get_artifact_by_id(
        self, db_session, artifact_repo, setup_experiment_and_session
    ):
        """Test retrieving an artifact by ID."""
        experiment, session = setup_experiment_and_session

        from benchmark_core.db.models import Artifact as ArtifactORM

        artifact = ArtifactORM(
            name="find_me.json",
            artifact_type="export",
            content_type="application/json",
            storage_path="/storage/find_me.json",
            session_id=session.id,
        )
        db_session.add(artifact)
        db_session.commit()

        found = await artifact_repo.get_by_id(artifact.id)
        assert found is not None
        assert found.name == "find_me.json"

    @pytest.mark.asyncio
    async def test_list_by_session(self, db_session, artifact_repo, setup_experiment_and_session):
        """Test listing artifacts by session."""
        experiment, session = setup_experiment_and_session

        from benchmark_core.db.models import Artifact as ArtifactORM

        # Create multiple artifacts for the session
        for i in range(3):
            artifact = ArtifactORM(
                name=f"export_{i}.json",
                artifact_type="export",
                content_type="application/json",
                storage_path=f"/storage/export_{i}.json",
                session_id=session.id,
            )
            db_session.add(artifact)

        # Create an artifact for the experiment (not the session)
        exp_artifact = ArtifactORM(
            name="exp_report.html",
            artifact_type="report",
            content_type="text/html",
            storage_path="/storage/exp_report.html",
            experiment_id=experiment.id,
        )
        db_session.add(exp_artifact)
        db_session.commit()

        results = await artifact_repo.list_by_session(session.id)
        assert len(results) == 3
        for result in results:
            assert result.session_id == session.id

    @pytest.mark.asyncio
    async def test_list_by_experiment(
        self, db_session, artifact_repo, setup_experiment_and_session
    ):
        """Test listing artifacts by experiment."""
        experiment, session = setup_experiment_and_session

        from benchmark_core.db.models import Artifact as ArtifactORM

        # Create artifacts for the experiment
        for i in range(2):
            artifact = ArtifactORM(
                name=f"exp_report_{i}.html",
                artifact_type="report",
                content_type="text/html",
                storage_path=f"/storage/exp_report_{i}.html",
                experiment_id=experiment.id,
            )
            db_session.add(artifact)

        db_session.commit()

        results = await artifact_repo.list_by_experiment(experiment.id)
        assert len(results) == 2
        for result in results:
            assert result.experiment_id == experiment.id

    @pytest.mark.asyncio
    async def test_delete_artifact(self, db_session, artifact_repo, setup_experiment_and_session):
        """Test deleting an artifact."""
        experiment, _ = setup_experiment_and_session

        from benchmark_core.db.models import Artifact as ArtifactORM

        artifact = ArtifactORM(
            name="to_delete.json",
            artifact_type="export",
            content_type="application/json",
            storage_path="/storage/to_delete.json",
            experiment_id=experiment.id,
        )
        db_session.add(artifact)
        db_session.commit()

        deleted = await artifact_repo.delete(artifact.id)
        assert deleted is True

        # Verify it's gone
        not_found = await artifact_repo.get_by_id(artifact.id)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_artifact(self, db_session, artifact_repo):
        """Test deleting a non-existent artifact."""
        fake_id = uuid4()
        deleted = await artifact_repo.delete(fake_id)
        assert deleted is False


@pytest.fixture
def usage_request_repo(db_session):
    """Create a usage request repository."""
    return SQLUsageRequestRepository(db_session)


class TestUsageRequestRepository:
    """Tests for SQLUsageRequestRepository."""

    @pytest.fixture
    async def setup_experiment_variant_task(self, db_session):
        """Create prerequisite entities for usage request tests."""
        experiment = Experiment(name="usage-test-exp")
        db_session.add(experiment)
        db_session.flush()

        variant = Variant(
            name="usage-test-variant",
            provider="test-provider",
            model_alias="gpt-4o",
            harness_profile="default",
        )
        db_session.add(variant)
        db_session.flush()

        task_card = TaskCard(
            name="usage-test-task",
            goal="Test usage request",
            starting_prompt="Start",
            stop_condition="Stop",
        )
        db_session.add(task_card)
        db_session.flush()

        db_session.commit()
        return experiment, variant, task_card

    @pytest.fixture
    async def setup_benchmark_session(self, db_session, setup_experiment_variant_task):
        """Create a benchmark session for linkage tests."""
        experiment, variant, task_card = setup_experiment_variant_task

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
        db_session.commit()
        return session

    @pytest.fixture
    async def setup_proxy_key(self, db_session):
        """Create a proxy key for linkage tests."""
        from benchmark_core.db.models import ProxyKey as ProxyKeyORM

        proxy_key = ProxyKeyORM(
            key_alias="usage-test-key",
            litellm_key_id="litellm-test-123",
            status="active",
        )
        db_session.add(proxy_key)
        db_session.commit()
        return proxy_key

    async def test_create_without_session(self, usage_request_repo, db_session):
        """Usage rows can be persisted without a benchmark session."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        usage = UsageRequestORM(
            litellm_call_id="call-no-session-001",
            key_alias="standalone-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            input_tokens=10,
            output_tokens=20,
            latency_ms=500.0,
        )
        created = await usage_request_repo.create(usage)
        db_session.commit()

        assert created.id is not None
        assert created.litellm_call_id == "call-no-session-001"
        assert created.benchmark_session_id is None
        assert created.key_alias == "standalone-key"

    async def test_create_with_session(
        self, usage_request_repo, db_session, setup_benchmark_session
    ):
        """Usage rows can optionally link to a benchmark session."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        session = setup_benchmark_session
        usage = UsageRequestORM(
            litellm_call_id="call-with-session-001",
            key_alias="session-key",
            benchmark_session_id=session.id,
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            input_tokens=10,
            output_tokens=20,
        )
        created = await usage_request_repo.create(usage)
        db_session.commit()

        assert created.benchmark_session_id == session.id

    async def test_duplicate_litellm_call_id(self, usage_request_repo, db_session):
        """Duplicate LiteLLM request IDs do not create duplicate usage rows."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        usage1 = UsageRequestORM(
            litellm_call_id="duplicate-call-001",
            key_alias="key-1",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            input_tokens=10,
            output_tokens=20,
        )
        await usage_request_repo.create(usage1)
        db_session.commit()

        usage2 = UsageRequestORM(
            litellm_call_id="duplicate-call-001",
            key_alias="key-2",
            provider="anthropic",
            resolved_model="claude-3",
            status="failure",
            input_tokens=5,
            output_tokens=0,
        )
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await usage_request_repo.create(usage2)
            db_session.commit()

        # Rollback the failed transaction so the session is clean
        db_session.rollback()

        # Verify only the first row exists
        found = await usage_request_repo.get_by_litellm_call_id("duplicate-call-001")
        assert found is not None
        assert found.provider == "openai"
        assert found.resolved_model == "gpt-4o"

    async def test_no_content_fields_stored(self, usage_request_repo, db_session):
        """No prompt/response content fields are stored by default."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        usage = UsageRequestORM(
            litellm_call_id="content-check-001",
            key_alias="key-1",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            request_metadata={"stream": False},
        )
        created = await usage_request_repo.create(usage)
        db_session.commit()

        # Verify the model does not have prompt/response columns
        from benchmark_core.db.models import UsageRequest

        columns = {col.name for col in UsageRequest.__table__.columns}
        assert "prompt" not in columns
        assert "response" not in columns
        assert "prompt_text" not in columns
        assert "response_text" not in columns
        assert "messages" not in columns
        assert created.request_metadata == {"stream": False}

    async def test_create_many_idempotent(self, usage_request_repo, db_session):
        """Idempotent create_many skips duplicates."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        req1 = UsageRequestORM(
            litellm_call_id="batch-001",
            key_alias="batch-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
        )
        req2 = UsageRequestORM(
            litellm_call_id="batch-002",
            key_alias="batch-key",
            provider="openai",
            resolved_model="gpt-4o-mini",
            status="success",
        )
        req3 = UsageRequestORM(
            litellm_call_id="batch-001",  # duplicate of req1
            key_alias="batch-key",
            provider="anthropic",
            resolved_model="claude-3",
            status="failure",
        )

        created, skipped = await usage_request_repo.create_many([req1, req2, req3])
        db_session.commit()

        assert len(created) == 2
        assert skipped == 1

        all_by_alias = await usage_request_repo.list_by_key_alias("batch-key")
        assert len(all_by_alias) == 2
        call_ids = {r.litellm_call_id for r in all_by_alias}
        assert "batch-001" in call_ids
        assert "batch-002" in call_ids

    async def test_get_by_litellm_call_id(self, usage_request_repo, db_session):
        """Retrieve usage request by LiteLLM call ID."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        usage = UsageRequestORM(
            litellm_call_id="find-me-001",
            key_alias="find-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
        )
        await usage_request_repo.create(usage)
        db_session.commit()

        found = await usage_request_repo.get_by_litellm_call_id("find-me-001")
        assert found is not None
        assert found.litellm_call_id == "find-me-001"

        not_found = await usage_request_repo.get_by_litellm_call_id("does-not-exist")
        assert not_found is None

    async def test_list_by_key_alias(self, usage_request_repo, db_session):
        """List usage requests by key alias."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        for i in range(3):
            usage = UsageRequestORM(
                litellm_call_id=f"alias-list-{i}",
                key_alias="shared-alias",
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)
        db_session.commit()

        results = await usage_request_repo.list_by_key_alias("shared-alias")
        assert len(results) == 3

    async def test_list_by_model(self, usage_request_repo, db_session):
        """List usage requests by resolved model."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        for i in range(2):
            usage = UsageRequestORM(
                litellm_call_id=f"model-gpt-{i}",
                key_alias="model-key",
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)

        usage_other = UsageRequestORM(
            litellm_call_id="model-claude-001",
            key_alias="model-key",
            provider="anthropic",
            resolved_model="claude-3",
            status="success",
        )
        await usage_request_repo.create(usage_other)
        db_session.commit()

        results = await usage_request_repo.list_by_model("gpt-4o")
        assert len(results) == 2

    async def test_list_by_provider(self, usage_request_repo, db_session):
        """List usage requests by provider."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        for i in range(2):
            usage = UsageRequestORM(
                litellm_call_id=f"prov-openai-{i}",
                key_alias="prov-key",
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)

        usage_other = UsageRequestORM(
            litellm_call_id="prov-fireworks-001",
            key_alias="prov-key",
            provider="fireworks",
            resolved_model="kimi-k2-5",
            status="success",
        )
        await usage_request_repo.create(usage_other)
        db_session.commit()

        results = await usage_request_repo.list_by_provider("openai")
        assert len(results) == 2

    async def test_list_by_benchmark_session(
        self, usage_request_repo, db_session, setup_benchmark_session
    ):
        """List usage requests linked to a benchmark session."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        session = setup_benchmark_session
        for i in range(2):
            usage = UsageRequestORM(
                litellm_call_id=f"session-link-{i}",
                key_alias="session-key",
                benchmark_session_id=session.id,
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)
        db_session.commit()

        results = await usage_request_repo.list_by_benchmark_session(session.id)
        assert len(results) == 2
        for r in results:
            assert r.benchmark_session_id == session.id

    async def test_list_by_time_range(self, usage_request_repo, db_session):
        """List usage requests within a time range."""
        from datetime import UTC, datetime

        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        usage1 = UsageRequestORM(
            litellm_call_id="time-001",
            key_alias="time-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            started_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        )
        usage2 = UsageRequestORM(
            litellm_call_id="time-002",
            key_alias="time-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            started_at=datetime(2025, 1, 16, 10, 0, 0, tzinfo=UTC),
        )
        usage3 = UsageRequestORM(
            litellm_call_id="time-003",
            key_alias="time-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
            started_at=datetime(2025, 1, 17, 10, 0, 0, tzinfo=UTC),
        )
        await usage_request_repo.create(usage1)
        await usage_request_repo.create(usage2)
        await usage_request_repo.create(usage3)
        db_session.commit()

        results = await usage_request_repo.list_by_time_range(
            "2025-01-15T00:00:00+00:00",
            "2025-01-16T23:59:59+00:00",
        )
        assert len(results) == 2
        call_ids = {r.litellm_call_id for r in results}
        assert "time-001" in call_ids
        assert "time-002" in call_ids

    async def test_list_by_status(self, usage_request_repo, db_session):
        """List usage requests by status."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        success = UsageRequestORM(
            litellm_call_id="status-success-001",
            key_alias="status-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
        )
        failure = UsageRequestORM(
            litellm_call_id="status-failure-001",
            key_alias="status-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="failure",
        )
        await usage_request_repo.create(success)
        await usage_request_repo.create(failure)
        db_session.commit()

        results = await usage_request_repo.list_by_status("success")
        assert len(results) == 1
        assert results[0].litellm_call_id == "status-success-001"

    async def test_list_by_error_code(self, usage_request_repo, db_session):
        """List usage requests by error code."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        rate_limited = UsageRequestORM(
            litellm_call_id="error-429-001",
            key_alias="error-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="failure",
            error_code="429",
        )
        server_error = UsageRequestORM(
            litellm_call_id="error-500-001",
            key_alias="error-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="failure",
            error_code="500",
        )
        await usage_request_repo.create(rate_limited)
        await usage_request_repo.create(server_error)
        db_session.commit()

        results = await usage_request_repo.list_by_error_code("429")
        assert len(results) == 1
        assert results[0].litellm_call_id == "error-429-001"

    async def test_count_by_key_alias(self, usage_request_repo, db_session):
        """Count usage requests by key alias."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        for i in range(5):
            usage = UsageRequestORM(
                litellm_call_id=f"count-{i}",
                key_alias="countable-alias",
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)
        db_session.commit()

        count = await usage_request_repo.count_by_key_alias("countable-alias")
        assert count == 5

    async def test_count_by_model(self, usage_request_repo, db_session):
        """Count usage requests by model."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        for i in range(3):
            usage = UsageRequestORM(
                litellm_call_id=f"model-count-{i}",
                key_alias="count-key",
                provider="openai",
                resolved_model="gpt-4o-mini",
                status="success",
            )
            await usage_request_repo.create(usage)
        db_session.commit()

        count = await usage_request_repo.count_by_model("gpt-4o-mini")
        assert count == 3

    async def test_delete_usage_request(self, usage_request_repo, db_session):
        """Delete a usage request by ID."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        usage = UsageRequestORM(
            litellm_call_id="delete-me-001",
            key_alias="delete-key",
            provider="openai",
            resolved_model="gpt-4o",
            status="success",
        )
        created = await usage_request_repo.create(usage)
        db_session.commit()

        deleted = await usage_request_repo.delete(created.id)
        db_session.commit()

        assert deleted is True
        not_found = await usage_request_repo.get_by_id(created.id)
        assert not_found is None

    async def test_delete_by_benchmark_session(
        self, usage_request_repo, db_session, setup_benchmark_session
    ):
        """Delete all usage requests linked to a benchmark session."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        session = setup_benchmark_session
        for i in range(3):
            usage = UsageRequestORM(
                litellm_call_id=f"batch-delete-{i}",
                key_alias="batch-delete-key",
                benchmark_session_id=session.id,
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)
        db_session.commit()

        deleted_count = await usage_request_repo.delete_by_benchmark_session(session.id)
        db_session.commit()

        assert deleted_count == 3
        results = await usage_request_repo.list_by_benchmark_session(session.id)
        assert len(results) == 0

    async def test_list_by_litellm_key_id(self, usage_request_repo, db_session):
        """List usage requests by LiteLLM key ID."""
        from benchmark_core.db.models import UsageRequest as UsageRequestORM

        for i in range(2):
            usage = UsageRequestORM(
                litellm_call_id=f"key-id-{i}",
                key_alias="key-id-alias",
                litellm_key_id="litellm-key-abc",
                provider="openai",
                resolved_model="gpt-4o",
                status="success",
            )
            await usage_request_repo.create(usage)
        db_session.commit()

        results = await usage_request_repo.list_by_litellm_key_id("litellm-key-abc")
        assert len(results) == 2
