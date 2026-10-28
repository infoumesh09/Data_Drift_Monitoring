-- DriftSense PostgreSQL Initialization Script
-- This script runs automatically on first container start

-- Ensure UUID extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create monitoring role (optional, for future use)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'driftsense_monitor') THEN
        CREATE ROLE driftsense_monitor WITH LOGIN PASSWORD 'monitor_only';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE driftsense TO driftsense_monitor;

COMMENT ON DATABASE driftsense IS 'DriftSense Data Pipeline Health Monitoring Database';
