"""SQLAlchemy ORM models for benchmark database."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benchmark_core.db.connection import Base
from benchmark_core.models import RequestStatus, RollupScopeType, SessionStatus


class ProviderModel(Base):
    """ORM model for providers table."""
    __tablename__ = "providers"

    provider_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    route_name: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol_surface: Mapped[str] = mapped_column(String(100), nullable=False)
    upstream_base_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class HarnessProfileModel(Base):
    """ORM model for harness_profiles table."""
    __tablename__ = "harness_profiles"

    harness_profile_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    protocol_surface: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url_env: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_env: Mapped[str] = mapped_column(String(100), nullable=False)
    model_env: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ExperimentModel(Base):
    """ORM model for experiments table."""
    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TaskCardModel(Base):
    """ORM model for task_cards table."""
    __tablename__ = "task_cards"

    task_card_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    repo_path: Mapped[Optional[str]] = mapped_column(String(500))
    goal: Mapped[Optional[str]] = mapped_column(Text)
    stop_condition: Mapped[Optional[str]] = mapped_column(Text)
    session_timebox_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class VariantModel(Base):
    """ORM model for variants table."""
    __tablename__ = "variants"

    variant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("providers.provider_id"), nullable=False)
    model_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    harness_profile_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("harness_profiles.harness_profile_id"), nullable=False)
    config_fingerprint: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    provider = relationship("ProviderModel", backref="variants")
    harness_profile = relationship("HarnessProfileModel", backref="variants")


class SessionModel(Base):
    """ORM model for sessions table."""
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    experiment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("experiments.experiment_id"), nullable=False)
    variant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("variants.variant_id"), nullable=False)
    task_card_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("task_cards.task_card_id"), nullable=False)
    harness_profile_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("harness_profiles.harness_profile_id"), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), nullable=False, default=SessionStatus.PENDING)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    operator_label: Mapped[Optional[str]] = mapped_column(String(255))
    repo_root: Mapped[Optional[str]] = mapped_column(String(500))
    git_branch: Mapped[Optional[str]] = mapped_column(String(255))
    git_commit_sha: Mapped[Optional[str]] = mapped_column(String(40))
    git_dirty: Mapped[Optional[bool]] = mapped_column(Boolean)
    proxy_key_alias: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    proxy_virtual_key_id: Mapped[Optional[str]] = mapped_column(String(255))

    experiment = relationship("ExperimentModel", backref="sessions")
    variant = relationship("VariantModel", backref="sessions")
    task_card = relationship("TaskCardModel", backref="sessions")
    harness_profile = relationship("HarnessProfileModel", backref="sessions")

    __table_args__ = (
        Index("ix_sessions_experiment_variant", "experiment_id", "variant_id"),
        Index("ix_sessions_status", "status"),
    )


class RequestModel(Base):
    """ORM model for requests table."""
    __tablename__ = "requests"

    request_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.session_id"), index=True)
    experiment_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("experiments.experiment_id"), index=True)
    variant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("variants.variant_id"), index=True)
    provider_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("providers.provider_id"), index=True)
    provider_route: Mapped[Optional[str]] = mapped_column(String(255))
    model: Mapped[Optional[str]] = mapped_column(String(255))
    harness_profile_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("harness_profiles.harness_profile_id"))
    litellm_call_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    provider_request_id: Mapped[Optional[str]] = mapped_column(String(255))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    ttft_ms: Mapped[Optional[float]] = mapped_column(Float)
    proxy_overhead_ms: Mapped[Optional[float]] = mapped_column(Float)
    provider_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    cached_input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    cache_write_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), nullable=False, default=RequestStatus.SUCCESS)
    error_code: Mapped[Optional[str]] = mapped_column(String(100))

    session = relationship("SessionModel", backref="requests")
    experiment = relationship("ExperimentModel", backref="requests")
    variant = relationship("VariantModel", backref="requests")
    provider = relationship("ProviderModel", backref="requests")
    harness_profile = relationship("HarnessProfileModel", backref="requests")

    __table_args__ = (
        Index("ix_requests_session_started", "session_id", "started_at"),
        Index("ix_requests_started_at", "started_at"),
    )


class MetricRollupModel(Base):
    """ORM model for metric_rollups table."""
    __tablename__ = "metric_rollups"

    rollup_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    scope_type: Mapped[RollupScopeType] = mapped_column(Enum(RollupScopeType), nullable=False)
    scope_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "metric_name", name="uq_rollup_scope_metric"),
        Index("ix_rollups_scope", "scope_type", "scope_id"),
    )


class ArtifactModel(Base):
    """ORM model for artifacts table."""
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.session_id"))
    experiment_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("experiments.experiment_id"))
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    session = relationship("SessionModel", backref="artifacts")
    experiment = relationship("ExperimentModel", backref="artifacts")
