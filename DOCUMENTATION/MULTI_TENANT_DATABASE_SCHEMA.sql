-- Multi-Tenant Database Schema
-- PostgreSQL 14+ with Row-Level Security (RLS)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Clients/Tenants
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL, -- URL-friendly identifier
    email VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active', -- active, suspended, cancelled
    subscription_tier VARCHAR(50) DEFAULT 'basic', -- basic, pro, enterprise
    max_jobs_per_month INTEGER DEFAULT 1000,
    max_file_size_mb INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL
);

CREATE INDEX idx_clients_slug ON clients(slug);
CREATE INDEX idx_clients_status ON clients(status);

-- Users (client-specific)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user', -- admin, user, viewer
    status VARCHAR(50) DEFAULT 'active', -- active, inactive, suspended
    last_login TIMESTAMP,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL,
    UNIQUE(client_id, email)
);

CREATE INDEX idx_users_client_id ON users(client_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);

-- Refresh Tokens
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP NULL
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- Jobs (client-specific)
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- 'classification', 'correction'
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    input_file_name VARCHAR(255),
    input_file_size BIGINT,
    input_file_path TEXT,
    output_files JSONB, -- {good_data: path, bad_data: path, reject_data: path, ...}
    statistics JSONB,
    error_message TEXT,
    progress FLOAT DEFAULT 0.0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL
);

CREATE INDEX idx_jobs_client_id ON jobs(client_id);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_job_type ON jobs(job_type);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_client_created ON jobs(client_id, created_at DESC);

-- Fingerprints (client-specific, fresh per file but cached)
CREATE TABLE fingerprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    workflow VARCHAR(50) NOT NULL,
    subtype VARCHAR(50) NOT NULL,
    method VARCHAR(50) NOT NULL,
    fingerprint_data JSONB NOT NULL,
    detection_confidence FLOAT,
    clustering_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, job_id, column_name)
);

CREATE INDEX idx_fingerprints_client_id ON fingerprints(client_id);
CREATE INDEX idx_fingerprints_job_id ON fingerprints(job_id);
CREATE INDEX idx_fingerprints_client_job ON fingerprints(client_id, job_id);

-- Detection Cache (client-specific)
CREATE TABLE detection_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    sample_hash VARCHAR(64) NOT NULL, -- SHA256 hash of sample data
    workflow VARCHAR(50) NOT NULL,
    subtype VARCHAR(50) NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- TTL for cache entries
    UNIQUE(client_id, column_name, sample_hash)
);

CREATE INDEX idx_detection_cache_client_id ON detection_cache(client_id);
CREATE INDEX idx_detection_cache_column_name ON detection_cache(column_name);
CREATE INDEX idx_detection_cache_expires_at ON detection_cache(expires_at);
CREATE INDEX idx_detection_cache_last_used ON detection_cache(last_used);

-- Correction Cache (client-specific)
CREATE TABLE correction_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    value_hash VARCHAR(64) NOT NULL,
    subtype VARCHAR(50) NOT NULL,
    original_value TEXT NOT NULL,
    corrected_value TEXT NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    UNIQUE(client_id, value_hash, subtype)
);

CREATE INDEX idx_correction_cache_client_id ON correction_cache(client_id);
CREATE INDEX idx_correction_cache_subtype ON correction_cache(subtype);
CREATE INDEX idx_correction_cache_expires_at ON correction_cache(expires_at);
CREATE INDEX idx_correction_cache_last_used ON correction_cache(last_used);

-- Audit Logs (for compliance)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- login, logout, file_upload, job_create, etc.
    resource_type VARCHAR(50), -- job, user, client, etc.
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_client_id ON audit_logs(client_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all tenant-specific tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE detection_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE correction_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Function to get current client_id from JWT
CREATE OR REPLACE FUNCTION get_current_client_id() RETURNS UUID AS $$
BEGIN
    RETURN current_setting('app.current_client_id', TRUE)::UUID;
END;
$$ LANGUAGE plpgsql STABLE;

-- RLS Policies: Users can only see their client's data
CREATE POLICY users_client_isolation ON users
    FOR ALL
    USING (client_id = get_current_client_id());

CREATE POLICY jobs_client_isolation ON jobs
    FOR ALL
    USING (client_id = get_current_client_id());

CREATE POLICY fingerprints_client_isolation ON fingerprints
    FOR ALL
    USING (client_id = get_current_client_id());

CREATE POLICY detection_cache_client_isolation ON detection_cache
    FOR ALL
    USING (client_id = get_current_client_id());

CREATE POLICY correction_cache_client_isolation ON correction_cache
    FOR ALL
    USING (client_id = get_current_client_id());

CREATE POLICY refresh_tokens_client_isolation ON refresh_tokens
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = refresh_tokens.user_id
            AND users.client_id = get_current_client_id()
        )
    );

CREATE POLICY audit_logs_client_isolation ON audit_logs
    FOR SELECT
    USING (client_id = get_current_client_id());

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Cleanup expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM detection_cache
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    
    DELETE FROM correction_cache
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    
    DELETE FROM refresh_tokens
    WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (run daily via cron or pg_cron)
-- SELECT cron.schedule('cleanup-cache', '0 2 * * *', 'SELECT cleanup_expired_cache()');

-- ============================================================================
-- VIEWS (for easier querying)
-- ============================================================================

-- Jobs with user info
CREATE VIEW jobs_with_user AS
SELECT 
    j.*,
    u.email as user_email,
    u.first_name || ' ' || u.last_name as user_name,
    c.name as client_name
FROM jobs j
JOIN users u ON j.user_id = u.id
JOIN clients c ON j.client_id = c.id;

-- Client statistics
CREATE VIEW client_statistics AS
SELECT 
    c.id as client_id,
    c.name as client_name,
    COUNT(DISTINCT u.id) as total_users,
    COUNT(j.id) as total_jobs,
    COUNT(CASE WHEN j.status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN j.status = 'failed' THEN 1 END) as failed_jobs,
    SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END)::FLOAT / NULLIF(COUNT(j.id), 0) as success_rate
FROM clients c
LEFT JOIN users u ON c.id = u.client_id
LEFT JOIN jobs j ON c.id = j.client_id
GROUP BY c.id, c.name;

-- ============================================================================
-- INITIAL DATA (Optional)
-- ============================================================================

-- Create a default admin client (for testing)
-- INSERT INTO clients (name, slug, email, subscription_tier)
-- VALUES ('Default Admin', 'admin', 'admin@example.com', 'enterprise')
-- RETURNING id;

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. All queries must set app.current_client_id before execution
--    Example: SET app.current_client_id = 'client-uuid';
--
-- 2. Cache entries should have TTL (expires_at)
--    Default: 30 days for detection_cache, 7 days for correction_cache
--
-- 3. Soft deletes (deleted_at) for compliance
--    Hard deletes only after retention period
--
-- 4. Partitioning for large tables (optional):
--    CREATE TABLE jobs_2024_01 PARTITION OF jobs
--    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
--
-- 5. Backup strategy:
--    - Daily full backups
--    - Point-in-time recovery (PITR)
--    - Client data export capability
