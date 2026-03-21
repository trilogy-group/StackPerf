-- StackPerf Database Initialization
-- This script runs on first container startup

-- Create litellm database for LiteLLM proxy internal use
CREATE DATABASE litellm;

-- Grant permissions to stackperf user on litellm database
GRANT ALL PRIVILEGES ON DATABASE litellm TO stackperf;

-- The stackperf database is already created by POSTGRES_DB env var
-- Add any benchmark-specific schema here in future migrations

-- Example: Sessions table (to be expanded in future issues)
-- CREATE TABLE IF NOT EXISTS sessions (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     experiment_id TEXT NOT NULL,
--     variant_id TEXT NOT NULL,
--     task_card_id TEXT NOT NULL,
--     status TEXT NOT NULL DEFAULT 'created',
--     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- );

-- Create schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Record initial migration
INSERT INTO schema_migrations (version) VALUES ('001_initial') ON CONFLICT DO NOTHING;
