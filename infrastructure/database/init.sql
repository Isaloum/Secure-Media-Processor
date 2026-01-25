-- Database initialization script for Secure Media Processor
-- PostgreSQL 15+
-- Run this script after RDS instance is created

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    storage_used_bytes BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    s3_key VARCHAR(512) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    encryption_algorithm VARCHAR(50),
    checksum_sha256 VARCHAR(64),
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    malware_scan_status VARCHAR(50) DEFAULT 'pending',
    malware_scan_result JSONB,
    metadata JSONB,
    CONSTRAINT file_size_positive CHECK (file_size > 0)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    ip_address INET,
    timestamp TIMESTAMP DEFAULT NOW(),
    details JSONB
);

-- API keys table (for future use)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_upload_timestamp ON files(upload_timestamp);
CREATE INDEX IF NOT EXISTS idx_files_malware_scan_status ON files(malware_scan_status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- Function to update storage usage
CREATE OR REPLACE FUNCTION update_user_storage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE users
        SET storage_used_bytes = storage_used_bytes + NEW.file_size
        WHERE id = NEW.user_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE users
        SET storage_used_bytes = storage_used_bytes - OLD.file_size
        WHERE id = OLD.user_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update storage usage
CREATE TRIGGER trigger_update_user_storage
AFTER INSERT OR DELETE ON files
FOR EACH ROW
EXECUTE FUNCTION update_user_storage();

-- Function to log file operations
CREATE OR REPLACE FUNCTION log_file_operation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES (NEW.user_id, 'file_upload', 'file', NEW.id, jsonb_build_object(
            'filename', NEW.original_filename,
            'file_size', NEW.file_size
        ));
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES (OLD.user_id, 'file_delete', 'file', OLD.id, jsonb_build_object(
            'filename', OLD.original_filename
        ));
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically log file operations
CREATE TRIGGER trigger_log_file_operation
AFTER INSERT OR DELETE ON files
FOR EACH ROW
EXECUTE FUNCTION log_file_operation();

-- Grant permissions (adjust as needed)
GRANT CONNECT ON DATABASE securemedia TO postgres;
GRANT USAGE ON SCHEMA public TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Sample data (optional, for testing)
-- INSERT INTO users (email, password_hash, subscription_tier)
-- VALUES ('test@example.com', '$2b$12$KIXxLVQZ8Z8Z8Z8Z8Z8Z8u', 'free');

-- Display table summary
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public';

    RAISE NOTICE 'Database initialization complete!';
    RAISE NOTICE 'Total tables created: %', table_count;
END $$;
