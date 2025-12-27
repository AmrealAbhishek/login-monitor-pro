-- ============================================================================
-- Login Monitor PRO v3.0 - Database Migrations
-- ============================================================================
-- Run these migrations in Supabase SQL Editor
-- ============================================================================

-- 1. Add new event fields for advanced security features
ALTER TABLE events ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0;
ALTER TABLE events ADD COLUMN IF NOT EXISTS geofence_name TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS usb_device JSONB;
ALTER TABLE events ADD COLUMN IF NOT EXISTS network_change JSONB;
ALTER TABLE events ADD COLUMN IF NOT EXISTS motion_data JSONB;

-- 2. Create app_usage table for application tracking
CREATE TABLE IF NOT EXISTS app_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  app_name TEXT NOT NULL,
  bundle_id TEXT,
  launched_at TIMESTAMPTZ NOT NULL,
  terminated_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create reports table for scheduled reports
CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  report_type TEXT NOT NULL, -- 'daily', 'weekly', 'monthly'
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  summary JSONB,
  report_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create backups table for threat-triggered backups
CREATE TABLE IF NOT EXISTS backups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  trigger_event_id UUID REFERENCES events(id),
  backup_type TEXT NOT NULL, -- 'threat', 'scheduled', 'manual'
  file_count INTEGER DEFAULT 0,
  total_size_bytes BIGINT DEFAULT 0,
  storage_url TEXT,
  status TEXT DEFAULT 'pending', -- 'pending', 'uploading', 'completed', 'failed'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create geofences table for location-based alerts
CREATE TABLE IF NOT EXISTS geofences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  radius_meters INTEGER DEFAULT 500,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Create usb_whitelist table for known USB devices
CREATE TABLE IF NOT EXISTS usb_whitelist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  vendor_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  device_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Create wifi_whitelist table for known networks
CREATE TABLE IF NOT EXISTS wifi_whitelist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  ssid TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Enable Row Level Security on new tables
-- ============================================================================

ALTER TABLE app_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE backups ENABLE ROW LEVEL SECURITY;
ALTER TABLE geofences ENABLE ROW LEVEL SECURITY;
ALTER TABLE usb_whitelist ENABLE ROW LEVEL SECURITY;
ALTER TABLE wifi_whitelist ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS Policies - Users can only access data from their own devices
-- ============================================================================

-- app_usage policies
CREATE POLICY "Users can view own app_usage" ON app_usage
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Service can insert app_usage" ON app_usage
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update app_usage" ON app_usage
  FOR UPDATE USING (true);

-- reports policies
CREATE POLICY "Users can view own reports" ON reports
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Service can insert reports" ON reports
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update reports" ON reports
  FOR UPDATE USING (true);

-- backups policies
CREATE POLICY "Users can view own backups" ON backups
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Service can insert backups" ON backups
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update backups" ON backups
  FOR UPDATE USING (true);

-- geofences policies
CREATE POLICY "Users can view own geofences" ON geofences
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Users can manage own geofences" ON geofences
  FOR ALL USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Service can manage geofences" ON geofences
  FOR ALL USING (true);

-- usb_whitelist policies
CREATE POLICY "Users can view own usb_whitelist" ON usb_whitelist
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Service can manage usb_whitelist" ON usb_whitelist
  FOR ALL USING (true);

-- wifi_whitelist policies
CREATE POLICY "Users can view own wifi_whitelist" ON wifi_whitelist
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Service can manage wifi_whitelist" ON wifi_whitelist
  FOR ALL USING (true);

-- ============================================================================
-- Enable Realtime for new tables
-- ============================================================================

ALTER PUBLICATION supabase_realtime ADD TABLE app_usage;
ALTER PUBLICATION supabase_realtime ADD TABLE reports;
ALTER PUBLICATION supabase_realtime ADD TABLE backups;
ALTER PUBLICATION supabase_realtime ADD TABLE geofences;

-- ============================================================================
-- Create indexes for better query performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_app_usage_device_id ON app_usage(device_id);
CREATE INDEX IF NOT EXISTS idx_app_usage_launched_at ON app_usage(launched_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_device_id ON reports(device_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backups_device_id ON backups(device_id);
CREATE INDEX IF NOT EXISTS idx_geofences_device_id ON geofences(device_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);

-- ============================================================================
-- Done! Run this entire script in Supabase SQL Editor
-- ============================================================================
