-- Login Monitor PRO - Enterprise Tables Migration
-- Run this in Supabase SQL Editor

-- ============================================
-- 1. ORGANIZATIONS (Multi-tenant support)
-- ============================================
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  plan TEXT DEFAULT 'pro' CHECK (plan IN ('free', 'pro', 'enterprise')),
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. ORGANIZATION MEMBERS (Roles & Access)
-- ============================================
CREATE TABLE IF NOT EXISTS org_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'manager', 'member')),
  invited_by UUID REFERENCES auth.users(id),
  invited_at TIMESTAMPTZ DEFAULT NOW(),
  joined_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id);

-- ============================================
-- 3. DEVICE GROUPS (Departments/Teams)
-- ============================================
CREATE TABLE IF NOT EXISTS device_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  color TEXT DEFAULT '#FF0000',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_groups_org ON device_groups(org_id);

-- Device to Group mapping
CREATE TABLE IF NOT EXISTS device_group_members (
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  group_id UUID REFERENCES device_groups(id) ON DELETE CASCADE,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (device_id, group_id)
);

-- ============================================
-- 4. SECURITY RULES (Threat Detection Config)
-- ============================================
CREATE TABLE IF NOT EXISTS security_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE, -- NULL for org-wide
  rule_type TEXT NOT NULL CHECK (rule_type IN (
    'unusual_time', 'new_location', 'after_hours',
    'failed_logins', 'sensitive_file', 'usb_connect'
  )),
  enabled BOOLEAN DEFAULT true,
  config JSONB DEFAULT '{}',
  -- Example configs:
  -- unusual_time: {"alert_hours": [0,1,2,3,4,5], "timezone": "Asia/Kolkata"}
  -- new_location: {"notify_first_time": true}
  -- after_hours: {"start": "18:00", "end": "09:00", "weekends": true}
  -- failed_logins: {"threshold": 3, "window_minutes": 5}
  severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  action TEXT DEFAULT 'alert' CHECK (action IN ('alert', 'screenshot', 'lock', 'alert_screenshot')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_rules_org ON security_rules(org_id);
CREATE INDEX IF NOT EXISTS idx_security_rules_device ON security_rules(device_id);

-- ============================================
-- 5. SECURITY ALERTS (Threat Detections)
-- ============================================
CREATE TABLE IF NOT EXISTS security_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  rule_id UUID REFERENCES security_rules(id) ON DELETE SET NULL,
  event_id UUID REFERENCES events(id) ON DELETE SET NULL,
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  title TEXT NOT NULL,
  description TEXT,
  metadata JSONB DEFAULT '{}',
  acknowledged BOOLEAN DEFAULT false,
  acknowledged_by UUID REFERENCES auth.users(id),
  acknowledged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_alerts_org ON security_alerts(org_id);
CREATE INDEX IF NOT EXISTS idx_security_alerts_device ON security_alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_security_alerts_created ON security_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_alerts_unack ON security_alerts(acknowledged) WHERE acknowledged = false;

-- ============================================
-- 6. KNOWN LOCATIONS (For New Location Detection)
-- ============================================
CREATE TABLE IF NOT EXISTS known_locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  name TEXT, -- 'Home', 'Office', etc.
  ip_address TEXT,
  city TEXT,
  region TEXT,
  country TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  is_trusted BOOLEAN DEFAULT false,
  first_seen TIMESTAMPTZ DEFAULT NOW(),
  last_seen TIMESTAMPTZ DEFAULT NOW(),
  visit_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_known_locations_device ON known_locations(device_id);
CREATE INDEX IF NOT EXISTS idx_known_locations_ip ON known_locations(ip_address);

-- ============================================
-- 7. PRODUCTIVITY SCORES (Daily Aggregates)
-- ============================================
CREATE TABLE IF NOT EXISTS productivity_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  productive_seconds INTEGER DEFAULT 0,
  unproductive_seconds INTEGER DEFAULT 0,
  neutral_seconds INTEGER DEFAULT 0,
  idle_seconds INTEGER DEFAULT 0,
  total_active_seconds INTEGER DEFAULT 0,
  productivity_score DECIMAL(5,2), -- 0.00 to 100.00
  login_count INTEGER DEFAULT 0,
  first_login TIME,
  last_activity TIME,
  top_apps JSONB DEFAULT '[]', -- [{app_name, duration_seconds, category}]
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(device_id, date)
);

CREATE INDEX IF NOT EXISTS idx_productivity_device_date ON productivity_scores(device_id, date DESC);

-- ============================================
-- 8. APP CATEGORIES (Productivity Classification)
-- ============================================
CREATE TABLE IF NOT EXISTS app_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- NULL for global defaults
  bundle_id TEXT NOT NULL,
  app_name TEXT,
  category TEXT DEFAULT 'neutral' CHECK (category IN ('productive', 'unproductive', 'neutral', 'communication')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::UUID), bundle_id)
);

-- Insert default app categories
INSERT INTO app_categories (bundle_id, app_name, category) VALUES
  ('com.apple.dt.Xcode', 'Xcode', 'productive'),
  ('com.microsoft.VSCode', 'VS Code', 'productive'),
  ('com.apple.Terminal', 'Terminal', 'productive'),
  ('com.googlecode.iterm2', 'iTerm', 'productive'),
  ('com.figma.Desktop', 'Figma', 'productive'),
  ('com.sketch', 'Sketch', 'productive'),
  ('com.spotify.client', 'Spotify', 'unproductive'),
  ('com.netflix.Netflix', 'Netflix', 'unproductive'),
  ('tv.twitch.TwitchClient', 'Twitch', 'unproductive'),
  ('com.apple.Safari', 'Safari', 'neutral'),
  ('com.google.Chrome', 'Chrome', 'neutral'),
  ('com.apple.finder', 'Finder', 'neutral'),
  ('com.tinyspeck.slackmacgap', 'Slack', 'communication'),
  ('com.microsoft.teams', 'Teams', 'communication'),
  ('us.zoom.xos', 'Zoom', 'communication')
ON CONFLICT DO NOTHING;

-- ============================================
-- 9. SCHEDULED REPORTS
-- ============================================
CREATE TABLE IF NOT EXISTS scheduled_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE, -- NULL for org-wide
  name TEXT NOT NULL,
  report_type TEXT NOT NULL CHECK (report_type IN ('daily', 'weekly', 'monthly')),
  schedule_day INTEGER, -- 0-6 for weekly (Sunday=0), 1-31 for monthly
  schedule_time TIME DEFAULT '09:00',
  recipients TEXT[] NOT NULL, -- Email addresses
  include_sections TEXT[] DEFAULT ARRAY['summary', 'productivity', 'security', 'activity'],
  enabled BOOLEAN DEFAULT true,
  last_sent_at TIMESTAMPTZ,
  next_send_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_reports_org ON scheduled_reports(org_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_next ON scheduled_reports(next_send_at) WHERE enabled = true;

-- ============================================
-- 10. DATA PROTECTION SETTINGS
-- ============================================
CREATE TABLE IF NOT EXISTS data_protection_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE UNIQUE,
  remote_wipe_enabled BOOLEAN DEFAULT false,
  wipe_confirmation_required BOOLEAN DEFAULT true,
  lock_message TEXT DEFAULT 'This device is protected by Login Monitor PRO',
  lock_on_geofence_exit BOOLEAN DEFAULT false,
  wipe_on_theft BOOLEAN DEFAULT false, -- Auto-wipe after N failed logins
  wipe_after_failed_logins INTEGER DEFAULT 10,
  usb_monitoring_enabled BOOLEAN DEFAULT true,
  emergency_contact TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 11. PROTECTION ACTIONS LOG
-- ============================================
CREATE TABLE IF NOT EXISTS protection_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL CHECK (action_type IN (
    'lock', 'wipe', 'disable_usb', 'enable_usb', 'findme', 'alarm', 'message'
  )),
  triggered_by TEXT CHECK (triggered_by IN ('manual', 'geofence', 'threat', 'scheduled', 'policy')),
  triggered_by_user UUID REFERENCES auth.users(id),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executing', 'completed', 'failed')),
  result JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_protection_actions_device ON protection_actions(device_id);
CREATE INDEX IF NOT EXISTS idx_protection_actions_created ON protection_actions(created_at DESC);

-- ============================================
-- 12. ADD ORG_ID TO DEVICES TABLE
-- ============================================
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'devices' AND column_name = 'org_id'
  ) THEN
    ALTER TABLE devices ADD COLUMN org_id UUID REFERENCES organizations(id);
    CREATE INDEX idx_devices_org ON devices(org_id);
  END IF;
END $$;

-- ============================================
-- 13. AUDIT LOGS
-- ============================================
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL, -- 'command.sent', 'device.added', 'user.invited', 'alert.acknowledged'
  target_type TEXT, -- 'device', 'user', 'group', 'alert', 'report'
  target_id TEXT,
  metadata JSONB DEFAULT '{}',
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Enable RLS on new tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE known_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE productivity_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_protection_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE protection_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Organizations: Members can view their org
CREATE POLICY "Members can view their organization" ON organizations
  FOR SELECT USING (
    id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
  );

-- Org members: Users can see members of their org
CREATE POLICY "Members can view org members" ON org_members
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
  );

-- Device groups: Members can view their org's groups
CREATE POLICY "Members can view device groups" ON device_groups
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
  );

-- Security rules: Members can view, admins can modify
CREATE POLICY "Members can view security rules" ON security_rules
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    OR device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

-- Security alerts: Members can view their org's alerts
CREATE POLICY "Members can view security alerts" ON security_alerts
  FOR SELECT USING (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    OR device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

-- Known locations: Users can view their device locations
CREATE POLICY "Users can view known locations" ON known_locations
  FOR SELECT USING (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

-- Productivity scores: Users can view their device scores
CREATE POLICY "Users can view productivity scores" ON productivity_scores
  FOR SELECT USING (
    device_id IN (SELECT id FROM devices WHERE user_id = auth.uid())
  );

-- Audit logs: Admins can view org audit logs
CREATE POLICY "Admins can view audit logs" ON audit_logs
  FOR SELECT USING (
    org_id IN (
      SELECT org_id FROM org_members
      WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    )
  );

-- ============================================
-- REALTIME SUBSCRIPTIONS
-- ============================================
ALTER PUBLICATION supabase_realtime ADD TABLE security_alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE protection_actions;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get user's organizations
CREATE OR REPLACE FUNCTION get_user_organizations(user_uuid UUID)
RETURNS TABLE (
  org_id UUID,
  org_name TEXT,
  role TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT o.id, o.name, m.role
  FROM organizations o
  JOIN org_members m ON o.id = m.org_id
  WHERE m.user_id = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is org admin
CREATE OR REPLACE FUNCTION is_org_admin(user_uuid UUID, organization_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM org_members
    WHERE user_id = user_uuid
    AND org_id = organization_id
    AND role IN ('owner', 'admin')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- GRANTS
-- ============================================
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
