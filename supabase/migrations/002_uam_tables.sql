-- Login Monitor PRO - UAM (User Activity Monitoring) Tables
-- Run this in Supabase SQL Editor after 001_enterprise_tables.sql

-- ============================================
-- 1. SENSITIVE FILE RULES (Admin Configurable)
-- ============================================
CREATE TABLE IF NOT EXISTS sensitive_file_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  rule_type TEXT NOT NULL CHECK (rule_type IN (
    'path_pattern',      -- Match file paths (e.g., /Documents/Confidential/*)
    'extension',         -- Match extensions (.docx, .xlsx, .pdf)
    'filename_pattern',  -- Match filenames (e.g., *password*, *secret*)
    'content_keyword'    -- Match content (requires OCR/text extraction)
  )),
  pattern TEXT NOT NULL,
  severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  action TEXT DEFAULT 'alert' CHECK (action IN ('alert', 'alert_screenshot', 'block', 'log_only')),
  enabled BOOLEAN DEFAULT true,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sensitive_file_rules_org ON sensitive_file_rules(org_id);
CREATE INDEX idx_sensitive_file_rules_enabled ON sensitive_file_rules(enabled, rule_type);

-- Default sensitive file rules
INSERT INTO sensitive_file_rules (org_id, name, description, rule_type, pattern, severity, action) VALUES
  (NULL, 'Password Files', 'Files containing password in name', 'filename_pattern', '*password*', 'critical', 'alert_screenshot'),
  (NULL, 'Secret Keys', 'Files containing secret or key in name', 'filename_pattern', '*secret*,*key*,*.pem,*.key', 'critical', 'alert_screenshot'),
  (NULL, 'Financial Documents', 'Excel and financial files', 'extension', '.xlsx,.xls,.csv', 'medium', 'alert'),
  (NULL, 'Confidential Folders', 'Access to Confidential folder', 'path_pattern', '*/Confidential/*,*/Private/*,*/Sensitive/*', 'high', 'alert_screenshot'),
  (NULL, 'Source Code', 'Programming source files', 'extension', '.py,.js,.ts,.java,.go,.rs', 'low', 'log_only'),
  (NULL, 'Database Files', 'Database and backup files', 'extension', '.sql,.db,.sqlite,.bak', 'high', 'alert');

-- ============================================
-- 2. FILE ACCESS EVENTS
-- ============================================
CREATE TABLE IF NOT EXISTS file_access_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  rule_id UUID REFERENCES sensitive_file_rules(id) ON DELETE SET NULL,
  file_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_extension TEXT,
  file_size_bytes BIGINT,
  access_type TEXT NOT NULL CHECK (access_type IN (
    'open', 'read', 'modify', 'create', 'delete',
    'copy', 'move', 'rename', 'print', 'upload', 'download'
  )),
  destination TEXT,  -- For copy/move/upload: where it went
  app_name TEXT,     -- Which app accessed the file
  bundle_id TEXT,
  user_name TEXT,
  screenshot_url TEXT,
  triggered_alert BOOLEAN DEFAULT false,
  alert_severity TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_file_access_device ON file_access_events(device_id, created_at DESC);
CREATE INDEX idx_file_access_alert ON file_access_events(triggered_alert, created_at DESC);
CREATE INDEX idx_file_access_type ON file_access_events(access_type, created_at DESC);

-- ============================================
-- 3. URL RULES (Admin Configurable)
-- ============================================
CREATE TABLE IF NOT EXISTS url_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  rule_type TEXT NOT NULL CHECK (rule_type IN (
    'domain_block',      -- Block specific domains
    'domain_alert',      -- Alert on specific domains
    'domain_allow',      -- Whitelist domains
    'category_block',    -- Block categories
    'category_alert',    -- Alert on categories
    'keyword_alert'      -- Alert on URL keywords
  )),
  pattern TEXT NOT NULL,  -- Domain, category name, or keyword
  category TEXT,
  severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  action TEXT DEFAULT 'alert' CHECK (action IN ('alert', 'alert_screenshot', 'block', 'log_only')),
  enabled BOOLEAN DEFAULT true,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_url_rules_org ON url_rules(org_id);
CREATE INDEX idx_url_rules_enabled ON url_rules(enabled, rule_type);

-- Default URL rules
INSERT INTO url_rules (org_id, name, description, rule_type, pattern, severity, action) VALUES
  (NULL, 'Job Sites', 'Job hunting websites', 'domain_alert', 'linkedin.com/jobs,indeed.com,glassdoor.com,monster.com', 'medium', 'alert'),
  (NULL, 'Cloud Storage', 'Personal cloud storage', 'domain_alert', 'dropbox.com,drive.google.com,onedrive.live.com,mega.nz', 'high', 'alert_screenshot'),
  (NULL, 'File Sharing', 'File sharing sites', 'domain_alert', 'wetransfer.com,sendspace.com,mediafire.com', 'high', 'alert_screenshot'),
  (NULL, 'Social Media', 'Social media platforms', 'category_alert', 'social_media', 'low', 'log_only'),
  (NULL, 'Streaming', 'Video streaming sites', 'category_alert', 'streaming', 'low', 'log_only'),
  (NULL, 'Gambling', 'Gambling websites', 'category_block', 'gambling', 'critical', 'alert_screenshot'),
  (NULL, 'Competitor Sites', 'Competitor domains (customize)', 'domain_alert', 'competitor1.com,competitor2.com', 'high', 'alert');

-- ============================================
-- 4. URL VISITS (Browser History Tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS url_visits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  domain TEXT,
  title TEXT,
  browser TEXT,          -- Chrome, Safari, Firefox, Edge
  source_app TEXT,       -- App that opened the URL (Mail, Slack, etc.)
  source_bundle_id TEXT,
  category TEXT CHECK (category IN (
    'productive', 'unproductive', 'social', 'news',
    'shopping', 'entertainment', 'communication', 'neutral'
  )),
  duration_seconds INTEGER DEFAULT 0,
  is_incognito BOOLEAN DEFAULT false,
  triggered_rule_id UUID REFERENCES url_rules(id),
  screenshot_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_url_visits_device ON url_visits(device_id, created_at DESC);
CREATE INDEX idx_url_visits_domain ON url_visits(domain, created_at DESC);
CREATE INDEX idx_url_visits_category ON url_visits(category, created_at DESC);

-- ============================================
-- 5. SUSPICIOUS ACTIVITY RULES (Admin Configurable)
-- ============================================
CREATE TABLE IF NOT EXISTS suspicious_activity_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  rule_type TEXT NOT NULL CHECK (rule_type IN (
    'unusual_time',           -- Access outside work hours
    'high_file_activity',     -- Many file operations in short time
    'sensitive_app_launch',   -- Remote desktop, FTP clients, etc.
    'usb_activity',           -- USB device connected
    'large_data_transfer',    -- Uploading/copying large amounts
    'repeated_failed_access', -- Multiple failed file access attempts
    'screen_capture_tool',    -- Screenshot/recording apps
    'vpn_connection',         -- VPN or proxy usage
    'printer_activity',       -- Printing sensitive docs
    'email_attachment'        -- Sending attachments externally
  )),
  config JSONB DEFAULT '{}',
  -- Example configs:
  -- unusual_time: {"start_hour": 0, "end_hour": 6, "weekends": true}
  -- high_file_activity: {"threshold": 50, "window_minutes": 5}
  -- large_data_transfer: {"threshold_mb": 100, "window_minutes": 10}
  -- sensitive_app_launch: {"apps": ["TeamViewer", "AnyDesk", "FileZilla"]}
  severity TEXT DEFAULT 'high' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  action TEXT DEFAULT 'alert_screenshot' CHECK (action IN ('alert', 'alert_screenshot', 'lock', 'notify_admin')),
  auto_screenshot BOOLEAN DEFAULT true,
  notify_immediately BOOLEAN DEFAULT true,
  enabled BOOLEAN DEFAULT true,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_suspicious_rules_org ON suspicious_activity_rules(org_id);
CREATE INDEX idx_suspicious_rules_enabled ON suspicious_activity_rules(enabled, rule_type);

-- Default suspicious activity rules
INSERT INTO suspicious_activity_rules (org_id, name, description, rule_type, config, severity, action) VALUES
  (NULL, 'After Hours Access', 'Login between midnight and 6 AM', 'unusual_time',
   '{"start_hour": 0, "end_hour": 6, "weekends": false}', 'high', 'alert_screenshot'),
  (NULL, 'Weekend Access', 'Any activity on weekends', 'unusual_time',
   '{"start_hour": 0, "end_hour": 24, "weekends": true, "weekdays": false}', 'medium', 'alert'),
  (NULL, 'Mass File Operations', 'More than 50 file operations in 5 minutes', 'high_file_activity',
   '{"threshold": 50, "window_minutes": 5}', 'critical', 'alert_screenshot'),
  (NULL, 'Remote Access Tools', 'TeamViewer, AnyDesk, VNC launched', 'sensitive_app_launch',
   '{"apps": ["TeamViewer", "AnyDesk", "VNC Viewer", "Remote Desktop", "LogMeIn"]}', 'high', 'alert_screenshot'),
  (NULL, 'USB Device Connected', 'External storage connected', 'usb_activity',
   '{"alert_on_connect": true, "alert_on_file_copy": true}', 'high', 'alert_screenshot'),
  (NULL, 'Large Data Transfer', 'More than 100MB transferred in 10 minutes', 'large_data_transfer',
   '{"threshold_mb": 100, "window_minutes": 10}', 'critical', 'alert_screenshot'),
  (NULL, 'Screen Recording Apps', 'Screen capture software detected', 'screen_capture_tool',
   '{"apps": ["OBS", "QuickTime Player", "Loom", "ScreenFlow", "Camtasia"]}', 'medium', 'alert');

-- ============================================
-- 6. ACTIVITY TIMELINE (Per-Minute Tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS activity_timeline (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  minute_timestamp TIMESTAMPTZ NOT NULL,  -- Rounded to minute
  status TEXT NOT NULL CHECK (status IN ('active', 'idle', 'away', 'locked', 'offline')),
  active_app TEXT,
  active_app_bundle TEXT,
  active_window_title TEXT,
  active_url TEXT,
  active_domain TEXT,
  keyboard_events INTEGER DEFAULT 0,
  mouse_events INTEGER DEFAULT 0,
  category TEXT CHECK (category IN ('productive', 'unproductive', 'communication', 'neutral')),
  UNIQUE(device_id, minute_timestamp)
);

CREATE INDEX idx_activity_timeline_device ON activity_timeline(device_id, minute_timestamp DESC);
CREATE INDEX idx_activity_timeline_status ON activity_timeline(status, minute_timestamp DESC);

-- ============================================
-- 7. PRODUCTIVITY TRENDS (Weekly Aggregates)
-- ============================================
CREATE TABLE IF NOT EXISTS productivity_trends (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  avg_productivity_score DECIMAL(5,2),
  total_active_hours DECIMAL(6,2),
  total_idle_hours DECIMAL(6,2),
  total_unproductive_hours DECIMAL(6,2),
  top_productive_apps JSONB,  -- [{app: "VSCode", hours: 12.5}, ...]
  top_unproductive_apps JSONB,
  top_domains JSONB,
  total_files_accessed INTEGER DEFAULT 0,
  sensitive_files_accessed INTEGER DEFAULT 0,
  login_count INTEGER DEFAULT 0,
  avg_first_login TIME,
  avg_last_activity TIME,
  alerts_triggered INTEGER DEFAULT 0,
  trend_vs_prev_week DECIMAL(5,2),  -- +5.2 means 5.2% improvement
  trend_direction TEXT CHECK (trend_direction IN ('improving', 'declining', 'stable')),
  UNIQUE(device_id, week_start)
);

CREATE INDEX idx_productivity_trends_device ON productivity_trends(device_id, week_start DESC);

-- ============================================
-- 8. BULK COMMAND JOBS
-- ============================================
CREATE TABLE IF NOT EXISTS bulk_command_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT,
  command TEXT NOT NULL,
  args JSONB DEFAULT '{}',
  target_type TEXT NOT NULL CHECK (target_type IN ('all', 'group', 'selected', 'online_only')),
  target_ids UUID[],  -- Device IDs or Group IDs
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executing', 'completed', 'partial', 'failed', 'cancelled')),
  total_devices INTEGER DEFAULT 0,
  completed_devices INTEGER DEFAULT 0,
  failed_devices INTEGER DEFAULT 0,
  results JSONB DEFAULT '[]',  -- [{device_id, status, result}, ...]
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_bulk_jobs_org ON bulk_command_jobs(org_id, created_at DESC);
CREATE INDEX idx_bulk_jobs_status ON bulk_command_jobs(status, created_at DESC);

-- ============================================
-- 9. URL CATEGORIES (Domain Classification)
-- ============================================
CREATE TABLE IF NOT EXISTS url_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL CHECK (category IN (
    'productive', 'unproductive', 'social', 'news',
    'shopping', 'entertainment', 'communication',
    'education', 'finance', 'health', 'gambling',
    'adult', 'malware', 'neutral'
  )),
  subcategory TEXT,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_url_categories_domain ON url_categories(domain);
CREATE INDEX idx_url_categories_category ON url_categories(category);

-- Default URL categories
INSERT INTO url_categories (domain, category, subcategory, is_default) VALUES
  -- Productive
  ('github.com', 'productive', 'development', true),
  ('gitlab.com', 'productive', 'development', true),
  ('stackoverflow.com', 'productive', 'development', true),
  ('docs.google.com', 'productive', 'documents', true),
  ('notion.so', 'productive', 'documents', true),
  ('figma.com', 'productive', 'design', true),
  ('slack.com', 'communication', 'work', true),
  ('teams.microsoft.com', 'communication', 'work', true),
  ('zoom.us', 'communication', 'meetings', true),

  -- Unproductive
  ('facebook.com', 'social', 'social_network', true),
  ('instagram.com', 'social', 'social_network', true),
  ('twitter.com', 'social', 'social_network', true),
  ('x.com', 'social', 'social_network', true),
  ('tiktok.com', 'entertainment', 'video', true),
  ('youtube.com', 'entertainment', 'video', true),
  ('netflix.com', 'entertainment', 'streaming', true),
  ('reddit.com', 'social', 'forum', true),
  ('twitch.tv', 'entertainment', 'streaming', true),

  -- Shopping
  ('amazon.com', 'shopping', 'ecommerce', true),
  ('ebay.com', 'shopping', 'ecommerce', true),
  ('flipkart.com', 'shopping', 'ecommerce', true),

  -- News
  ('news.google.com', 'news', 'aggregator', true),
  ('cnn.com', 'news', 'media', true),
  ('bbc.com', 'news', 'media', true);

-- ============================================
-- 10. ENABLE RLS FOR NEW TABLES
-- ============================================
ALTER TABLE sensitive_file_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_access_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE url_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE url_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE suspicious_activity_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE productivity_trends ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulk_command_jobs ENABLE ROW LEVEL SECURITY;

-- RLS Policies (using service key bypasses these)
CREATE POLICY "Service role full access to sensitive_file_rules"
  ON sensitive_file_rules FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to file_access_events"
  ON file_access_events FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to url_rules"
  ON url_rules FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to url_visits"
  ON url_visits FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to suspicious_activity_rules"
  ON suspicious_activity_rules FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to activity_timeline"
  ON activity_timeline FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to productivity_trends"
  ON productivity_trends FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to bulk_command_jobs"
  ON bulk_command_jobs FOR ALL
  USING (auth.role() = 'service_role');

-- ============================================
-- 11. FUNCTIONS FOR ANALYTICS
-- ============================================

-- Function to calculate productivity score for a time range
CREATE OR REPLACE FUNCTION calculate_productivity_score(
  p_device_id UUID,
  p_start_time TIMESTAMPTZ,
  p_end_time TIMESTAMPTZ
) RETURNS DECIMAL AS $$
DECLARE
  productive_minutes INTEGER;
  unproductive_minutes INTEGER;
  total_active_minutes INTEGER;
  score DECIMAL;
BEGIN
  SELECT
    COALESCE(SUM(CASE WHEN category = 'productive' THEN 1 ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN category = 'unproductive' THEN 1 ELSE 0 END), 0),
    COALESCE(COUNT(*), 0)
  INTO productive_minutes, unproductive_minutes, total_active_minutes
  FROM activity_timeline
  WHERE device_id = p_device_id
    AND minute_timestamp BETWEEN p_start_time AND p_end_time
    AND status = 'active';

  IF total_active_minutes = 0 THEN
    RETURN 0;
  END IF;

  -- Score = (productive - unproductive*0.5) / total * 100
  score := ((productive_minutes - (unproductive_minutes * 0.5))::DECIMAL / total_active_minutes) * 100;

  -- Clamp between 0 and 100
  RETURN GREATEST(0, LEAST(100, score));
END;
$$ LANGUAGE plpgsql;

-- Function to get activity summary for a device
CREATE OR REPLACE FUNCTION get_activity_summary(
  p_device_id UUID,
  p_date DATE
) RETURNS JSONB AS $$
DECLARE
  result JSONB;
BEGIN
  SELECT jsonb_build_object(
    'total_active_minutes', COALESCE(SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END), 0),
    'total_idle_minutes', COALESCE(SUM(CASE WHEN status = 'idle' THEN 1 ELSE 0 END), 0),
    'productive_minutes', COALESCE(SUM(CASE WHEN category = 'productive' THEN 1 ELSE 0 END), 0),
    'unproductive_minutes', COALESCE(SUM(CASE WHEN category = 'unproductive' THEN 1 ELSE 0 END), 0),
    'first_activity', MIN(minute_timestamp),
    'last_activity', MAX(minute_timestamp)
  ) INTO result
  FROM activity_timeline
  WHERE device_id = p_device_id
    AND DATE(minute_timestamp) = p_date;

  RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- DONE
-- ============================================
-- Run this migration after 001_enterprise_tables.sql
-- Then proceed with implementing the monitoring agents
