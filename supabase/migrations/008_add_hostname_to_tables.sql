-- Add hostname column to tables that may be missing it
-- This ensures admin visibility across all DLP features

-- Add hostname to file_access_events (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'file_access_events') THEN
        ALTER TABLE file_access_events ADD COLUMN IF NOT EXISTS hostname TEXT;
    END IF;
END $$;

-- Add hostname/username to keystroke_logs
ALTER TABLE keystroke_logs ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE keystroke_logs ADD COLUMN IF NOT EXISTS username TEXT;

-- Create indexes for admin queries
CREATE INDEX IF NOT EXISTS idx_file_access_hostname ON file_access_events(hostname);
CREATE INDEX IF NOT EXISTS idx_keystroke_hostname ON keystroke_logs(hostname);
CREATE INDEX IF NOT EXISTS idx_keystroke_username ON keystroke_logs(username);

-- SIEM integrations table (if it doesn't exist)
CREATE TABLE IF NOT EXISTS siem_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    integration_type TEXT NOT NULL, -- splunk, sentinel, elastic, slack, teams, discord, webhook
    endpoint_url TEXT NOT NULL,
    auth_type TEXT DEFAULT 'none', -- none, bearer, basic, api_key
    auth_token TEXT,
    workspace_id TEXT, -- For Sentinel
    shared_key TEXT, -- For Sentinel
    index_name TEXT, -- For Elastic
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SIEM export log (for tracking what was sent)
CREATE TABLE IF NOT EXISTS siem_export_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID REFERENCES siem_integrations(id),
    event_type TEXT NOT NULL,
    event_id TEXT,
    status TEXT DEFAULT 'pending',
    response_code INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for export log queries
CREATE INDEX IF NOT EXISTS idx_siem_log_integration ON siem_export_log(integration_id);
CREATE INDEX IF NOT EXISTS idx_siem_log_created ON siem_export_log(created_at);
