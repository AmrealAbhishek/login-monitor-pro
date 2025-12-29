-- Add device context columns to DLP tables for admin visibility
-- ================================================================
-- This allows admins to see WHO did each action without joining tables

-- 1. Add username column to devices table
ALTER TABLE devices ADD COLUMN IF NOT EXISTS username TEXT;

-- 2. Add hostname, username, and forensic content to clipboard_events
ALTER TABLE clipboard_events ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE clipboard_events ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE clipboard_events ADD COLUMN IF NOT EXISTS content_forensic TEXT;  -- Base64 encoded for admin reveal

-- 3. Add hostname and username to shadow_it_detections
ALTER TABLE shadow_it_detections ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE shadow_it_detections ADD COLUMN IF NOT EXISTS username TEXT;

-- 4. Add hostname and username to usb_events
ALTER TABLE usb_events ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE usb_events ADD COLUMN IF NOT EXISTS username TEXT;

-- 5. Add hostname and username to keystroke_logs
ALTER TABLE keystroke_logs ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE keystroke_logs ADD COLUMN IF NOT EXISTS username TEXT;

-- 6. Add hostname and username to file_transfer_events
ALTER TABLE file_transfer_events ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE file_transfer_events ADD COLUMN IF NOT EXISTS username TEXT;

-- 7. Add hostname and username to security_alerts
ALTER TABLE security_alerts ADD COLUMN IF NOT EXISTS hostname TEXT;
ALTER TABLE security_alerts ADD COLUMN IF NOT EXISTS username TEXT;

-- 8. Create indexes for faster queries by hostname/username
CREATE INDEX IF NOT EXISTS idx_clipboard_hostname ON clipboard_events(hostname);
CREATE INDEX IF NOT EXISTS idx_shadow_it_hostname ON shadow_it_detections(hostname);
CREATE INDEX IF NOT EXISTS idx_usb_hostname ON usb_events(hostname);
CREATE INDEX IF NOT EXISTS idx_alerts_hostname ON security_alerts(hostname);

-- 9. Create a view for easy admin querying (joins device info automatically)
CREATE OR REPLACE VIEW dlp_events_with_device AS
SELECT
    'clipboard' as event_type,
    c.id,
    c.device_id,
    COALESCE(c.hostname, d.hostname) as hostname,
    COALESCE(c.username, d.username) as username,
    c.sensitive_type as details,
    c.content_preview as preview,
    c.action_taken,
    c.created_at
FROM clipboard_events c
LEFT JOIN devices d ON c.device_id = d.id
UNION ALL
SELECT
    'shadow_it' as event_type,
    s.id,
    s.device_id,
    COALESCE(s.hostname, d.hostname) as hostname,
    COALESCE(s.username, d.username) as username,
    s.app_name || ' (' || s.app_category || ')' as details,
    s.url_accessed as preview,
    s.risk_level as action_taken,
    s.last_detected as created_at
FROM shadow_it_detections s
LEFT JOIN devices d ON s.device_id = d.id
UNION ALL
SELECT
    'usb' as event_type,
    u.id,
    u.device_id,
    COALESCE(u.hostname, d.hostname) as hostname,
    COALESCE(u.username, d.username) as username,
    u.usb_name || ' (' || u.usb_type || ')' as details,
    u.file_name as preview,
    u.action_taken,
    u.created_at
FROM usb_events u
LEFT JOIN devices d ON u.device_id = d.id
ORDER BY created_at DESC;

COMMENT ON VIEW dlp_events_with_device IS 'Combined view of all DLP events with device hostname and username for admin dashboard';
