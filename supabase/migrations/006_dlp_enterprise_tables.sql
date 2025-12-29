-- CyVigil Enterprise DLP Tables
-- ================================
-- Run this in Supabase SQL Editor

-- 1. USB/Device Events
CREATE TABLE IF NOT EXISTS usb_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- 'connected', 'disconnected', 'file_copied', 'blocked'
    usb_name TEXT,
    usb_vendor TEXT,
    usb_serial TEXT,
    usb_type TEXT, -- 'storage', 'keyboard', 'mouse', 'other'
    file_path TEXT,
    file_name TEXT,
    file_size BIGINT,
    file_hash TEXT,
    action_taken TEXT DEFAULT 'logged', -- 'logged', 'blocked', 'alerted'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. USB Rules (Allow/Block policies)
CREATE TABLE IF NOT EXISTS usb_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL, -- 'allow', 'block', 'log_only'
    match_type TEXT NOT NULL, -- 'vendor', 'serial', 'name', 'all_storage'
    match_value TEXT,
    action TEXT DEFAULT 'block', -- 'block', 'alert', 'log'
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Clipboard Events
CREATE TABLE IF NOT EXISTS clipboard_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL, -- 'text', 'file', 'image'
    content_preview TEXT, -- First 500 chars
    content_hash TEXT,
    content_length INTEGER,
    source_app TEXT,
    destination_app TEXT,
    sensitive_data_detected BOOLEAN DEFAULT false,
    sensitive_type TEXT, -- 'pii', 'credit_card', 'ssn', 'api_key', 'password', 'code'
    action_taken TEXT DEFAULT 'logged',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Clipboard Rules
CREATE TABLE IF NOT EXISTS clipboard_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    pattern TEXT NOT NULL, -- Regex pattern
    pattern_type TEXT NOT NULL, -- 'credit_card', 'ssn', 'api_key', 'custom'
    action TEXT DEFAULT 'alert', -- 'block', 'alert', 'log'
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Keystroke Logs
CREATE TABLE IF NOT EXISTS keystroke_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    app_name TEXT,
    window_title TEXT,
    keystrokes TEXT, -- Encrypted or hashed
    keystroke_count INTEGER,
    special_keys JSONB, -- {ctrl: 5, alt: 2, etc}
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Shadow IT/Unauthorized Apps
CREATE TABLE IF NOT EXISTS shadow_it_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    app_name TEXT NOT NULL,
    app_bundle_id TEXT,
    app_category TEXT, -- 'ai_chatbot', 'file_sharing', 'vpn', 'messaging', 'other'
    url_accessed TEXT,
    is_approved BOOLEAN DEFAULT false,
    risk_level TEXT DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    data_sent_preview TEXT, -- For AI tools, what was pasted
    first_detected TIMESTAMPTZ DEFAULT NOW(),
    last_detected TIMESTAMPTZ DEFAULT NOW(),
    detection_count INTEGER DEFAULT 1
);

-- 7. Shadow IT Rules (Approved/Blocked apps)
CREATE TABLE IF NOT EXISTS shadow_it_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    app_name TEXT,
    app_bundle_id TEXT,
    url_pattern TEXT,
    category TEXT,
    status TEXT DEFAULT 'blocked', -- 'approved', 'blocked', 'monitor'
    risk_level TEXT DEFAULT 'medium',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. OCR Extracted Text (from screenshots)
CREATE TABLE IF NOT EXISTS ocr_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    screenshot_url TEXT,
    extracted_text TEXT,
    text_hash TEXT,
    sensitive_detected BOOLEAN DEFAULT false,
    sensitive_types TEXT[], -- Array of detected types
    app_name TEXT,
    window_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. SIEM/Webhook Integrations
CREATE TABLE IF NOT EXISTS siem_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    integration_type TEXT NOT NULL, -- 'splunk', 'sentinel', 'elastic', 'webhook', 'slack', 'teams'
    name TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    auth_type TEXT, -- 'bearer', 'basic', 'api_key', 'none'
    auth_token TEXT, -- Encrypted
    event_types TEXT[], -- Which events to send
    enabled BOOLEAN DEFAULT true,
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. SIEM Export Log
CREATE TABLE IF NOT EXISTS siem_export_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID REFERENCES siem_integrations(id) ON DELETE CASCADE,
    event_type TEXT,
    event_id UUID,
    status TEXT, -- 'sent', 'failed', 'pending'
    response_code INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. File Transfer Events (enhanced)
CREATE TABLE IF NOT EXISTS file_transfer_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    transfer_type TEXT NOT NULL, -- 'upload', 'download', 'copy', 'move', 'delete', 'email_attachment'
    source_path TEXT,
    destination TEXT, -- URL, path, or email recipient
    destination_type TEXT, -- 'cloud', 'usb', 'network', 'email', 'airdrop', 'local'
    file_name TEXT,
    file_extension TEXT,
    file_size BIGINT,
    file_hash TEXT,
    app_name TEXT,
    sensitive_detected BOOLEAN DEFAULT false,
    action_taken TEXT DEFAULT 'logged',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Sensitive Data Patterns (configurable)
CREATE TABLE IF NOT EXISTS sensitive_data_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL, -- 'regex', 'keyword', 'file_extension'
    pattern_value TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default sensitive data patterns
INSERT INTO sensitive_data_patterns (org_id, pattern_name, pattern_type, pattern_value, severity) VALUES
(NULL, 'Credit Card', 'regex', '\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b', 'critical'),
(NULL, 'SSN', 'regex', '\b\d{3}-\d{2}-\d{4}\b', 'critical'),
(NULL, 'API Key', 'regex', '\b(?:api[_-]?key|apikey|api_secret)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?\b', 'high'),
(NULL, 'AWS Key', 'regex', '\bAKIA[0-9A-Z]{16}\b', 'critical'),
(NULL, 'Private Key', 'regex', '-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----', 'critical'),
(NULL, 'Password Field', 'regex', '\b(?:password|passwd|pwd)["\s:=]+["\']?([^\s"'']{6,})["\']?\b', 'high'),
(NULL, 'Email Address', 'regex', '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'low'),
(NULL, 'Phone Number', 'regex', '\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', 'low'),
(NULL, 'IP Address', 'regex', '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', 'low'),
(NULL, 'JWT Token', 'regex', '\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b', 'high')
ON CONFLICT DO NOTHING;

-- Default Shadow IT rules (blocked by default)
INSERT INTO shadow_it_rules (org_id, app_name, url_pattern, category, status, risk_level) VALUES
(NULL, 'ChatGPT', 'chat.openai.com', 'ai_chatbot', 'monitor', 'high'),
(NULL, 'Claude', 'claude.ai', 'ai_chatbot', 'monitor', 'high'),
(NULL, 'Gemini', 'gemini.google.com', 'ai_chatbot', 'monitor', 'high'),
(NULL, 'Perplexity', 'perplexity.ai', 'ai_chatbot', 'monitor', 'medium'),
(NULL, 'Personal Dropbox', 'dropbox.com', 'file_sharing', 'monitor', 'medium'),
(NULL, 'Personal Google Drive', 'drive.google.com', 'file_sharing', 'monitor', 'medium'),
(NULL, 'WeTransfer', 'wetransfer.com', 'file_sharing', 'blocked', 'high'),
(NULL, 'Mega', 'mega.nz', 'file_sharing', 'blocked', 'high'),
(NULL, 'Personal Gmail', 'mail.google.com', 'email', 'monitor', 'medium'),
(NULL, 'ProtonMail', 'proton.me', 'email', 'blocked', 'high'),
(NULL, 'Telegram Web', 'web.telegram.org', 'messaging', 'blocked', 'high'),
(NULL, 'WhatsApp Web', 'web.whatsapp.com', 'messaging', 'monitor', 'medium'),
(NULL, 'Discord', 'discord.com', 'messaging', 'monitor', 'medium'),
(NULL, 'NordVPN', 'nordvpn.com', 'vpn', 'blocked', 'high'),
(NULL, 'ExpressVPN', 'expressvpn.com', 'vpn', 'blocked', 'high')
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_usb_events_device ON usb_events(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clipboard_events_device ON clipboard_events(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clipboard_sensitive ON clipboard_events(sensitive_data_detected, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_keystroke_device ON keystroke_logs(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shadow_it_device ON shadow_it_detections(device_id, last_detected DESC);
CREATE INDEX IF NOT EXISTS idx_ocr_device ON ocr_extractions(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_transfer_device ON file_transfer_events(device_id, created_at DESC);

-- RLS Policies
ALTER TABLE usb_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE clipboard_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE keystroke_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE shadow_it_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_extractions ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_transfer_events ENABLE ROW LEVEL SECURITY;

-- Allow anon insert (from devices)
CREATE POLICY "Devices can insert USB events" ON usb_events FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Devices can insert clipboard events" ON clipboard_events FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Devices can insert keystroke logs" ON keystroke_logs FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Devices can insert shadow IT" ON shadow_it_detections FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Devices can insert OCR" ON ocr_extractions FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Devices can insert file transfers" ON file_transfer_events FOR INSERT TO anon WITH CHECK (true);

-- Allow authenticated read (dashboard)
CREATE POLICY "Dashboard can read USB events" ON usb_events FOR SELECT TO authenticated USING (true);
CREATE POLICY "Dashboard can read clipboard events" ON clipboard_events FOR SELECT TO authenticated USING (true);
CREATE POLICY "Dashboard can read keystroke logs" ON keystroke_logs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Dashboard can read shadow IT" ON shadow_it_detections FOR SELECT TO authenticated USING (true);
CREATE POLICY "Dashboard can read OCR" ON ocr_extractions FOR SELECT TO authenticated USING (true);
CREATE POLICY "Dashboard can read file transfers" ON file_transfer_events FOR SELECT TO authenticated USING (true);

-- Service role can do everything (for SIEM export)
CREATE POLICY "Service can manage USB events" ON usb_events FOR ALL TO service_role USING (true);
CREATE POLICY "Service can manage clipboard events" ON clipboard_events FOR ALL TO service_role USING (true);
CREATE POLICY "Service can manage keystroke logs" ON keystroke_logs FOR ALL TO service_role USING (true);
CREATE POLICY "Service can manage shadow IT" ON shadow_it_detections FOR ALL TO service_role USING (true);
CREATE POLICY "Service can manage OCR" ON ocr_extractions FOR ALL TO service_role USING (true);
CREATE POLICY "Service can manage file transfers" ON file_transfer_events FOR ALL TO service_role USING (true);

COMMENT ON TABLE usb_events IS 'Tracks all USB device connections and file operations';
COMMENT ON TABLE clipboard_events IS 'Monitors copy/paste operations for sensitive data';
COMMENT ON TABLE keystroke_logs IS 'Stores keystroke data for investigation (privacy-respecting)';
COMMENT ON TABLE shadow_it_detections IS 'Detects unauthorized apps and AI tools';
COMMENT ON TABLE ocr_extractions IS 'Stores OCR text from screenshots for search';
COMMENT ON TABLE file_transfer_events IS 'Tracks file uploads, downloads, and transfers';
