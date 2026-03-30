"""SQLAlchemy ORM models for benchmark database schema."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Provider(Base):
    """Upstream inference provider definition."""

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    route_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    protocol_surface: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # anthropic_messages or openai_responses
    upstream_base_url_env: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_env: Mapped[str] = mapped_column(String(255), nullable=False)
    routing_defaults: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    models: Mapped[list["ProviderModel"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class ProviderModel(Base):
    """Model alias definition within a provider config."""

    __tablename__ = "provider_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    upstream_model: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    provider: Mapped["Provider"] = relationship(back_populates="models")


class HarnessProfile(Base):
    """How a harness is configured to talk to the proxy."""

    __tablename__ = "harness_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    protocol_surface: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # anthropic_messages or openai_responses
    base_url_env: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_env: Mapped[str] = mapped_column(String(255), nullable=False)
    model_env: Mapped[str] = mapped_column(String(255), nullable=False)
    extra_env: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    render_format: Mapped[str] = mapped_column(String(20), default="shell")  # shell or dotenv
    launch_checks: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Variant(Base):
    """A benchmarkable combination of provider route, model, harness profile, and settings."""

    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_route: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    harness_profile: Mapped[str] = mapped_column(String(255), nullable=False)
    harness_env_overrides: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    benchmark_tags: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    experiment_variants: Mapped[list["ExperimentVariant"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )


class Experiment(Base):
    """A named comparison grouping that contains one or more variants."""

    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    experiment_variants: Mapped[list["ExperimentVariant"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentVariant(Base):
    """Link table between experiments and variants."""

    __tablename__ = "experiment_variants"

    # Ensure unique experiment-variant pairs
    __table_args__ = (
        UniqueConstraint("experiment_id", "variant_id", name="uq_experiment_variant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship(back_populates="experiment_variants")
    variant: Mapped["Variant"] = relationship(back_populates="experiment_variants")


class TaskCard(Base):
    """The benchmark task definition used for comparable sessions."""

    __tablename__ = "task_cards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    repo_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    starting_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    stop_condition: Mapped[str] = mapped_column(Text, nullable=False)
    session_timebox_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="task_card", cascade="all, delete-orphan"
    )


class ProxyCredential(Base):
    """Session-scoped proxy credential metadata (secrets managed by LiteLLM)."""

    __tablename__ = "proxy_credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    key_alias: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Note: api_key is NOT stored here - only in LiteLLM
    experiment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    harness_profile: Mapped[str] = mapped_column(String(255), nullable=False)
    litellm_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships - specify foreign_keys to disambiguate
    session: Mapped["Session"] = relationship(
        back_populates="proxy_credential",
        foreign_keys="ProxyCredential.session_id",
    )


class Session(Base):
    """One interactive benchmark session under one variant and one task card."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("variants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_cards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    harness_profile: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    git_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    git_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    operator_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    proxy_credential_alias: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proxy_credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    outcome_state: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship(back_populates="sessions")
    variant: Mapped["Variant"] = relationship(back_populates="sessions")
    task_card: Mapped["TaskCard"] = relationship(back_populates="sessions")
    # One-to-one with ProxyCredential via session_id FK (parent side)
    proxy_credential: Mapped["ProxyCredential"] = relationship(
        back_populates="session",
        uselist=False,
        foreign_keys="ProxyCredential.session_id",
        lazy="selectin",  # Works better with async sessions
    )


class Request(Base):
    """One normalized LLM call observed through LiteLLM."""

    __tablename__ = "requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ttft_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_prompt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_completion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cache_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MetricRollup(Base):
    """Derived latency, throughput, error, and cache metrics."""

    __tablename__ = "rollups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dimension_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # request, session, variant, or experiment
    dimension_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=1)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Artifact(Base):
    """Arbitrary files/data produced during a benchmark session or experiment."""

    __tablename__ = "artifacts"

    __table_args__ = (
        # Ensure at least one of session_id or experiment_id is provided
        CheckConstraint(
            "session_id IS NOT NULL OR experiment_id IS NOT NULL", name="ck_artifact_scope"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
