-- Login Monitor PRO - Supabase Database Schema
-- =============================================
-- Run this in Supabase SQL Editor to set up your database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- DEVICES TABLE (Mac computers)
-- =============================================
CREATE TABLE IF NOT EXISTS devices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  hostname TEXT,
  os_version TEXT,
  user_email TEXT,

  -- Pairing
  pairing_code VARCHAR(6),
  pairing_expires_at TIMESTAMP WITH TIME ZONE,

  -- Status
  last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  is_online BOOLEAN DEFAULT false,

  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for pairing code lookup
CREATE INDEX IF NOT EXISTS idx_devices_pairing_code ON devices(pairing_code) WHERE pairing_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_user_email ON devices(user_email);

-- =============================================
-- EVENTS TABLE (login/unlock notifications)
-- =============================================
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,

  -- Event info
  event_type TEXT NOT NULL,  -- Login, Unlock, Wake, Test, FailedLogin
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Device info at time of event
  hostname TEXT,
  username TEXT,
  local_ip TEXT,
  public_ip TEXT,

  -- Rich data (JSONB for flexibility)
  location JSONB,      -- {lat, lon, accuracy, city, country, source}
  battery JSONB,       -- {percentage, charging, status}
  wifi JSONB,          -- {ssid, bssid, signal}
  face_recognition JSONB,  -- {known, name, confidence}
  activity JSONB,      -- {running_apps, browser_tabs, etc}

  -- Media
  photos TEXT[],       -- Array of storage URLs
  audio_url TEXT,      -- Audio recording URL
  screenshot_url TEXT, -- Screenshot URL

  -- Status
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for events
CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);

-- =============================================
-- COMMANDS TABLE (from app to Mac)
-- =============================================
CREATE TABLE IF NOT EXISTS commands (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,

  -- Command info
  command TEXT NOT NULL,  -- photo, location, audio, alarm, lock, status, wifi, battery, screenshot
  args JSONB,             -- {duration: 10, message: "text", count: 3}

  -- Execution
  status TEXT DEFAULT 'pending',  -- pending, executing, completed, failed
  result JSONB,           -- {success: true, data: {...}, error: "..."}
  result_url TEXT,        -- Storage URL for photos/audio/screenshots

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  executed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for commands
CREATE INDEX IF NOT EXISTS idx_commands_device_id ON commands(device_id);
CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status);
CREATE INDEX IF NOT EXISTS idx_commands_created_at ON commands(created_at DESC);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE commands ENABLE ROW LEVEL SECURITY;

-- Devices policies
CREATE POLICY "Users can view own devices" ON devices
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own devices" ON devices
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Anyone can insert devices (for pairing)" ON devices
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can delete own devices" ON devices
  FOR DELETE USING (auth.uid() = user_id);

-- Events policies
CREATE POLICY "Users can view own device events" ON events
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Devices can insert events" ON events
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can update own device events" ON events
  FOR UPDATE USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

-- Commands policies
CREATE POLICY "Users can view own device commands" ON commands
  FOR SELECT USING (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Users can insert commands for own devices" ON commands
  FOR INSERT WITH CHECK (device_id IN (SELECT id FROM devices WHERE user_id = auth.uid()));

CREATE POLICY "Devices can update command status" ON commands
  FOR UPDATE WITH CHECK (true);

-- =============================================
-- STORAGE BUCKETS
-- =============================================

-- Create storage buckets (run in Supabase Dashboard > Storage)
-- Photos bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('photos', 'photos', false)
ON CONFLICT (id) DO NOTHING;

-- Audio bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('audio', 'audio', false)
ON CONFLICT (id) DO NOTHING;

-- Screenshots bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('screenshots', 'screenshots', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies
CREATE POLICY "Authenticated users can upload" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id IN ('photos', 'audio', 'screenshots')
    AND auth.role() = 'authenticated'
  );

CREATE POLICY "Users can view own files" ON storage.objects
  FOR SELECT USING (
    bucket_id IN ('photos', 'audio', 'screenshots')
    AND auth.role() = 'authenticated'
  );

CREATE POLICY "Devices can upload files" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id IN ('photos', 'audio', 'screenshots')
  );

-- =============================================
-- REALTIME SUBSCRIPTIONS
-- =============================================

-- Enable realtime for events (Flutter app listens for new events)
ALTER PUBLICATION supabase_realtime ADD TABLE events;

-- Enable realtime for commands (Mac listens for new commands)
ALTER PUBLICATION supabase_realtime ADD TABLE commands;

-- Enable realtime for devices (status updates)
ALTER PUBLICATION supabase_realtime ADD TABLE devices;

-- =============================================
-- HELPER FUNCTIONS
-- =============================================

-- Function to pair device with user
CREATE OR REPLACE FUNCTION pair_device(
  p_pairing_code VARCHAR(6),
  p_user_id UUID
)
RETURNS UUID AS $$
DECLARE
  v_device_id UUID;
BEGIN
  -- Find device with valid pairing code
  SELECT id INTO v_device_id
  FROM devices
  WHERE pairing_code = p_pairing_code
    AND pairing_expires_at > NOW()
    AND user_id IS NULL;

  IF v_device_id IS NULL THEN
    RAISE EXCEPTION 'Invalid or expired pairing code';
  END IF;

  -- Link device to user
  UPDATE devices
  SET user_id = p_user_id,
      pairing_code = NULL,
      pairing_expires_at = NULL,
      updated_at = NOW()
  WHERE id = v_device_id;

  RETURN v_device_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update device heartbeat
CREATE OR REPLACE FUNCTION update_device_heartbeat(p_device_id UUID)
RETURNS void AS $$
BEGIN
  UPDATE devices
  SET last_seen = NOW(),
      is_online = true,
      updated_at = NOW()
  WHERE id = p_device_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================
-- TRIGGERS
-- =============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER devices_updated_at
  BEFORE UPDATE ON devices
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
