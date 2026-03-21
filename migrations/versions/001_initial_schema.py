"""Initial schema for benchmark database.

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Providers table
    op.create_table(
        'providers',
        sa.Column('provider_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('route_name', sa.String(255), nullable=False),
        sa.Column('protocol_surface', sa.String(100), nullable=False),
        sa.Column('upstream_base_url', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Harness profiles table
    op.create_table(
        'harness_profiles',
        sa.Column('harness_profile_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('protocol_surface', sa.String(100), nullable=False),
        sa.Column('base_url_env', sa.String(100), nullable=False),
        sa.Column('api_key_env', sa.String(100), nullable=False),
        sa.Column('model_env', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Experiments table
    op.create_table(
        'experiments',
        sa.Column('experiment_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Task cards table
    op.create_table(
        'task_cards',
        sa.Column('task_card_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('repo_path', sa.String(500)),
        sa.Column('goal', sa.Text),
        sa.Column('stop_condition', sa.Text),
        sa.Column('session_timebox_minutes', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Variants table
    op.create_table(
        'variants',
        sa.Column('variant_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('provider_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('providers.provider_id'), nullable=False),
        sa.Column('model_alias', sa.String(255), nullable=False),
        sa.Column('harness_profile_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('harness_profiles.harness_profile_id'), nullable=False),
        sa.Column('config_fingerprint', sa.String(64)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('experiments.experiment_id'), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('variants.variant_id'), nullable=False),
        sa.Column('task_card_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('task_cards.task_card_id'), nullable=False),
        sa.Column('harness_profile_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('harness_profiles.harness_profile_id'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'COMPLETED', 'ABORTED', 'INVALID', name='session_status'), nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('operator_label', sa.String(255)),
        sa.Column('repo_root', sa.String(500)),
        sa.Column('git_branch', sa.String(255)),
        sa.Column('git_commit_sha', sa.String(40)),
        sa.Column('git_dirty', sa.Boolean),
        sa.Column('proxy_key_alias', sa.String(255), unique=True),
        sa.Column('proxy_virtual_key_id', sa.String(255)),
    )
    op.create_index('ix_sessions_experiment_variant', 'sessions', ['experiment_id', 'variant_id'])
    op.create_index('ix_sessions_status', 'sessions', ['status'])
    
    # Requests table
    op.create_table(
        'requests',
        sa.Column('request_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('sessions.session_id')),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('experiments.experiment_id')),
        sa.Column('variant_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('variants.variant_id')),
        sa.Column('provider_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('providers.provider_id')),
        sa.Column('provider_route', sa.String(255)),
        sa.Column('model', sa.String(255)),
        sa.Column('harness_profile_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('harness_profiles.harness_profile_id')),
        sa.Column('litellm_call_id', sa.String(255), unique=True),
        sa.Column('provider_request_id', sa.String(255)),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.Column('latency_ms', sa.Float),
        sa.Column('ttft_ms', sa.Float),
        sa.Column('proxy_overhead_ms', sa.Float),
        sa.Column('provider_latency_ms', sa.Float),
        sa.Column('input_tokens', sa.Integer),
        sa.Column('output_tokens', sa.Integer),
        sa.Column('cached_input_tokens', sa.Integer),
        sa.Column('cache_write_tokens', sa.Integer),
        sa.Column('status', sa.Enum('SUCCESS', 'ERROR', 'TIMEOUT', 'CANCELLED', name='request_status'), nullable=False, server_default='SUCCESS'),
        sa.Column('error_code', sa.String(100)),
    )
    op.create_index(op.f('ix_requests_session_id'), 'requests', ['session_id'])
    op.create_index(op.f('ix_requests_experiment_id'), 'requests', ['experiment_id'])
    op.create_index(op.f('ix_requests_variant_id'), 'requests', ['variant_id'])
    op.create_index(op.f('ix_requests_provider_id'), 'requests', ['provider_id'])
    op.create_index('ix_requests_session_started', 'requests', ['session_id', 'started_at'])
    op.create_index('ix_requests_started_at', 'requests', ['started_at'])
    
    # Metric rollups table
    op.create_table(
        'metric_rollups',
        sa.Column('rollup_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('scope_type', sa.Enum('REQUEST', 'SESSION', 'VARIANT', 'EXPERIMENT', name='rollup_scope_type'), nullable=False),
        sa.Column('scope_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('window_start', sa.DateTime(timezone=True)),
        sa.Column('window_end', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('scope_type', 'scope_id', 'metric_name', name='uq_rollup_scope_metric'),
    )
    op.create_index('ix_rollups_scope', 'metric_rollups', ['scope_type', 'scope_id'])
    
    # Artifacts table
    op.create_table(
        'artifacts',
        sa.Column('artifact_id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('sessions.session_id')),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('experiments.experiment_id')),
        sa.Column('artifact_type', sa.String(100), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )


def downgrade() -> None:
    op.drop_table('artifacts')
    op.drop_table('metric_rollups')
    op.drop_index('ix_requests_started_at', table_name='requests')
    op.drop_index('ix_requests_session_started', table_name='requests')
    op.drop_index(op.f('ix_requests_provider_id'), table_name='requests')
    op.drop_index(op.f('ix_requests_variant_id'), table_name='requests')
    op.drop_index(op.f('ix_requests_experiment_id'), table_name='requests')
    op.drop_index(op.f('ix_requests_session_id'), table_name='requests')
    op.drop_table('requests')
    op.drop_index('ix_sessions_status', table_name='sessions')
    op.drop_index('ix_sessions_experiment_variant', table_name='sessions')
    op.drop_table('sessions')
    op.drop_table('variants')
    op.drop_table('task_cards')
    op.drop_table('experiments')
    op.drop_table('harness_profiles')
    op.drop_table('providers')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS request_status')
    op.execute('DROP TYPE IF EXISTS session_status')
    op.execute('DROP TYPE IF EXISTS rollup_scope_type')
