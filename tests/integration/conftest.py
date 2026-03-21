"""Pytest fixtures for integration tests."""
import pytest
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from benchmark_core.db.connection import Base
from benchmark_core.db.models import (
    ProviderModel,
    HarnessProfileModel,
    VariantModel,
    ExperimentModel,
    TaskCardModel,
    SessionModel,
    RequestModel,
    MetricRollupModel,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with in-memory SQLite.
    
    Uses StaticPool to ensure the same connection is reused for the session,
    keeping the in-memory database alive throughout the test.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Critical: keeps single connection alive
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Yield session for test
    async with async_session_maker() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def sample_provider(db_session: AsyncSession) -> ProviderModel:
    """Create sample provider."""
    provider = ProviderModel(
        name="test-provider",
        route_name="test-route",
        protocol_surface="anthropic_messages",
    )
    db_session.add(provider)
    await db_session.flush()
    await db_session.refresh(provider)
    return provider


@pytest.fixture
async def sample_harness_profile(db_session: AsyncSession) -> HarnessProfileModel:
    """Create sample harness profile."""
    profile = HarnessProfileModel(
        name="test-harness",
        protocol_surface="anthropic_messages",
        base_url_env="ANTHROPIC_BASE_URL",
        api_key_env="ANTHROPIC_API_KEY",
        model_env="ANTHROPIC_MODEL",
    )
    db_session.add(profile)
    await db_session.flush()
    await db_session.refresh(profile)
    return profile


@pytest.fixture
async def sample_experiment(db_session: AsyncSession) -> ExperimentModel:
    """Create sample experiment."""
    exp = ExperimentModel(
        name="test-experiment",
        description="Test experiment for integration tests",
    )
    db_session.add(exp)
    await db_session.flush()
    await db_session.refresh(exp)
    return exp


@pytest.fixture
async def sample_task_card(db_session: AsyncSession) -> TaskCardModel:
    """Create sample task card."""
    tc = TaskCardModel(
        name="test-task",
        goal="Test goal",
        stop_condition="Test stop condition",
    )
    db_session.add(tc)
    await db_session.flush()
    await db_session.refresh(tc)
    return tc


@pytest.fixture
async def sample_variant(
    db_session: AsyncSession,
    sample_provider: ProviderModel,
    sample_harness_profile: HarnessProfileModel,
) -> VariantModel:
    """Create sample variant."""
    variant = VariantModel(
        name="test-variant",
        provider_id=sample_provider.provider_id,
        model_alias="test-model",
        harness_profile_id=sample_harness_profile.harness_profile_id,
    )
    db_session.add(variant)
    await db_session.flush()
    await db_session.refresh(variant)
    return variant


@pytest.fixture
async def sample_session(
    db_session: AsyncSession,
    sample_experiment: ExperimentModel,
    sample_variant: VariantModel,
    sample_task_card: TaskCardModel,
    sample_harness_profile: HarnessProfileModel,
) -> SessionModel:
    """Create sample session."""
    from benchmark_core.models import SessionStatus
    from datetime import datetime
    
    sess = SessionModel(
        experiment_id=sample_experiment.experiment_id,
        variant_id=sample_variant.variant_id,
        task_card_id=sample_task_card.task_card_id,
        harness_profile_id=sample_harness_profile.harness_profile_id,
        status=SessionStatus.PENDING,
        started_at=datetime.utcnow(),
    )
    db_session.add(sess)
    await db_session.flush()
    await db_session.refresh(sess)
    return sess
